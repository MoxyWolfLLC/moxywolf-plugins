"""XE-011 criterion 2: every outcome the dispatcher can emit is a vocabulary id, and the enums and
shapes it enforces are the vocabulary's. A literal outside the vocabulary fails here, and at
runtime ReviewError refuses it.

ponytail: an AST walk over peer_review.py for the three places an outcome is written: a
ReviewError's first argument, an assignment to `outcome`, and an "outcome" key or subscript.
"""
import ast
import unittest
from pathlib import Path

import peer_review as pr

SRC = Path(pr.__file__).read_text()


def _nodes_outside_selftests(tree):
    """The selftest builds packets whose "outcome" is the user-facing sentence, a different term
    that shares the key; skip it rather than count a fixture as an emitted outcome."""
    stack = [tree]
    while stack:
        node = stack.pop()
        if isinstance(node, ast.FunctionDef) and "selftest" in node.name:
            continue
        yield node
        stack.extend(ast.iter_child_nodes(node))


def emitted_outcomes():
    found = set()
    for node in _nodes_outside_selftests(ast.parse(SRC)):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "ReviewError" and node.args:
            if isinstance(node.args[0], ast.Constant):
                found.add(node.args[0].value)
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "outcome" for t in node.targets):
            found |= {c.value for c in ast.walk(node.value) if isinstance(c, ast.Constant) and isinstance(c.value, str)}
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == "outcome" and isinstance(v, ast.Constant):
                    found.add(v.value)
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Subscript) and \
                isinstance(node.left.slice, ast.Constant) and node.left.slice.value == "outcome":
            found |= {c.value for c in ast.walk(node) if isinstance(c, ast.Constant) and isinstance(c.value, str) and c.value != "outcome"}
    return found


class Vocabulary(unittest.TestCase):
    def test_every_emitted_outcome_is_a_vocabulary_id(self):
        found = emitted_outcomes()
        print(f"examined {len(found)} outcome literals in peer_review.py")
        self.assertGreater(len(found), 20, "the scan found almost nothing; it is broken, not clean")
        self.assertEqual(sorted(found - pr.OUTCOMES), [])

    def test_review_error_refuses_an_undefined_outcome(self):
        with self.assertRaises(ValueError):
            pr.ReviewError("made_up_outcome", "x")
        self.assertEqual(pr.ReviewError("stale_link", "x").outcome, "stale_link")

    def test_enforced_enums_are_the_vocabularys(self):
        enum = lambda *path: set(__import__("functools").reduce(lambda d, k: d[k], path, pr.OUTPUT_SCHEMA))
        self.assertEqual(enum("properties", "verdict", "enum"), pr.vocab_ids("round_outcome") & pr.VERDICTS)
        self.assertEqual(enum("properties", "findings", "items", "properties", "severity", "enum"), pr.vocab_ids("severity"))
        self.assertEqual(pr.PACKET_FIELDS, pr.vocab_shape("packet")["required"])

    def test_every_concept_is_skos_shaped_and_unique(self):
        ids = [c["id"] for c in pr.VOCAB["concepts"]]
        self.assertEqual(len(ids), len(set(ids)))
        for c in pr.VOCAB["concepts"]:
            for k in ("skos:prefLabel", "skos:definition", "skos:inScheme", "group"):
                self.assertTrue(c.get(k), f"{c['id']} lacks {k}")
        self.assertTrue(pr.VOCAB_VERSION)


class DesignUsesTheVocabulary(unittest.TestCase):
    def test_design_and_contracts_pass_vocab_check(self):
        """XE-011 criterion 4: every status line in DESIGN.md is a vocabulary status, checked in CI."""
        import vocab_check
        repo = Path(pr.__file__).resolve().parents[3]
        r = vocab_check.check(vocab_check.default_files(repo), pr.VOCAB)
        print(f"examined {r['files']} files, {r['status_lines']} status lines, {r['term_uses']} term uses")
        self.assertEqual(r["failures"], [])
        self.assertGreater(r["status_lines"], 20)


if __name__ == "__main__":
    unittest.main()
