"""
Academic Pipeline: SCAMPER Defixation, Novelty Scoring, & Outline Generator
===========================================================================

Self-contained module for the moxywolf-plugins academic-pipeline. Stdlib only.

Capabilities:
1. Literature Deconstruction: Parses literature baseline claims, frameworks, methodologies, and implicit assumptions.
2. Defixation Prompting: Generates structured SCAMPER prompts across all 7 operators (Substitute, Combine, Adapt, Modify, Put to another use, Eliminate, Reverse).
3. Automated Semantic Distance Scoring: Computes cosine distance against baseline literature vectors to assign an objective 0.0 - 10.0 Novelty Score.
4. Tiered Classification: Categorizes candidate research theses into Paradigm Shift, Moderate Reframing, or Incremental Extension.
5. Direct Paper Outline Integration: Takes the top-ranked SCAMPER candidate thesis and generates a publication-ready academic paper outline.
6. Flexible Output: Renders structured JSON for automated downstream pipeline stages or formatted Markdown for human review.

Programmatic entry point: run_scamper_pipeline(baseline_data, generate_outline=True)
CLI: python3 plugins/academic-pipeline/scripts/scamper.py --topic "..." --generate-outline
"""

import json
import argparse
import math
import re
from collections import Counter
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Callable, Sequence, Tuple


class ScamperOperator(str, Enum):
    SUBSTITUTE = "substitute"
    COMBINE = "combine"
    ADAPT = "adapt"
    MODIFY = "modify"
    PUT_TO_ANOTHER_USE = "put_to_another_use"
    ELIMINATE = "eliminate"
    REVERSE = "reverse"


@dataclass
class LiteratureBaseline:
    """Represents the deconstructed baseline of existing literature on a research topic."""
    topic: str
    consensus_claims: List[str] = field(default_factory=list)
    theoretical_frameworks: List[str] = field(default_factory=list)
    methodologies: List[str] = field(default_factory=list)
    implicit_assumptions: List[str] = field(default_factory=list)

    def get_all_baseline_texts(self) -> List[str]:
        """Combines all baseline elements into a list of reference text strings."""
        combined = []
        if self.topic:
            combined.append(f"Research Topic: {self.topic}")
        combined.extend([f"Consensus Claim: {c}" for c in self.consensus_claims])
        combined.extend([f"Theoretical Framework: {f}" for f in self.theoretical_frameworks])
        combined.extend([f"Methodology: {m}" for m in self.methodologies])
        combined.extend([f"Implicit Assumption: {a}" for a in self.implicit_assumptions])
        return combined

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LiteratureBaseline":
        return cls(
            topic=data.get("topic", ""),
            consensus_claims=data.get("consensus_claims", []),
            theoretical_frameworks=data.get("theoretical_frameworks", []),
            methodologies=data.get("methodologies", []),
            implicit_assumptions=data.get("implicit_assumptions", [])
        )


@dataclass
class ScamperCandidateThesis:
    """A candidate research thesis generated via SCAMPER and scored for semantic novelty."""
    operator: ScamperOperator
    operator_label: str
    target_element: str
    novel_angle: str
    proposed_thesis: str
    rationale: str
    baseline_similarity: float = 0.0
    semantic_distance: float = 0.0
    novelty_score: float = 0.0  # 0.0 - 10.0 scale
    ranking_tier: str = "Unscored"


@dataclass
class PaperOutlineSection:
    """Represents a section in the generated academic paper outline."""
    section_number: str
    section_title: str
    core_objective: str
    key_subsections: List[str] = field(default_factory=list)
    baseline_contrast_notes: str = ""


@dataclass
class AcademicPaperOutline:
    """Represents a publication-ready academic paper outline derived from a SCAMPER thesis."""
    working_title: str
    target_journal_or_conference: str
    abstract_sketch: str
    core_thesis_statement: str
    scamper_operator_used: str
    sections: List[PaperOutlineSection] = field(default_factory=list)
    novelty_score: float = 0.0


# ponytail: stdlib TF-IDF replaces sklearn+numpy (not installed on the host); swap in a custom_embedder for dense vectors
_STOP_WORDS = frozenset(
    "a an and are as at be by for from has have in into is it its of on or that the this to was were will with we our".split()
)


def _tokens(text: str) -> List[str]:
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP_WORDS]
    return words + [f"{a} {b}" for a, b in zip(words, words[1:])]  # unigrams + bigrams


def _tfidf_unit_vectors(corpus: List[str]) -> List[Dict[str, float]]:
    """Sublinear-tf, smoothed-idf, L2-normalized sparse vectors (sklearn TfidfVectorizer defaults)."""
    docs = [Counter(_tokens(t)) for t in corpus]
    df: Counter = Counter()
    for d in docs:
        df.update(d.keys())
    n = len(docs)
    idf = {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}
    vectors = []
    for d in docs:
        v = {t: (1 + math.log(tf)) * idf[t] for t, tf in d.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vectors.append({t: x / norm for t, x in v.items()})
    return vectors


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) + 1e-9
    nb = math.sqrt(sum(y * y for y in b)) + 1e-9
    return dot / (na * nb)


class SemanticDistanceScorer:
    """
    Quantitative novelty scorer for candidate research theses.
    Calculates semantic distance against baseline literature vectors.
    """

    def __init__(self, custom_embedder: Optional[Callable[[List[str]], Sequence[Sequence[float]]]] = None):
        """
        :param custom_embedder: Optional function taking List[str] and returning an N x D matrix (list of vectors).
        """
        self.custom_embedder = custom_embedder

    def score_thesis(
        self,
        candidate_thesis: str,
        baseline: LiteratureBaseline
    ) -> Tuple[float, float, float, str]:
        """
        Computes semantic similarity, distance, 0-10 novelty score, and ranking tier.

        Returns:
            (baseline_similarity, semantic_distance, novelty_score, ranking_tier)
        """
        baseline_texts = baseline.get_all_baseline_texts()
        if not baseline_texts:
            return 0.0, 1.0, 10.0, "High Novelty / Paradigm Shift"

        if self.custom_embedder is not None:
            similarity, distance = self._score_with_custom_embedder(candidate_thesis, baseline_texts)
        else:
            similarity, distance = self._score_with_tfidf(candidate_thesis, baseline_texts)

        # Scale semantic distance (0.0 to 1.0) to a 0.0 - 10.0 Novelty Score
        novelty_score = round(distance * 10.0, 2)

        # Determine ranking tier based on semantic distance thresholds
        if distance >= 0.75:
            tier = "High Novelty / Paradigm Shift"
        elif distance >= 0.45:
            tier = "Moderate Reframing / Hybrid Concept"
        else:
            tier = "Incremental Extension / High Fixation"

        return round(similarity, 4), round(distance, 4), novelty_score, tier

    def _score_with_tfidf(self, candidate_text: str, baseline_texts: List[str]) -> Tuple[float, float]:
        """Calculates cosine similarity and distance using n-gram TF-IDF vectorization."""
        vectors = _tfidf_unit_vectors([candidate_text] + baseline_texts)
        cand, base = vectors[0], vectors[1:]
        similarities = [sum(w * b.get(t, 0.0) for t, w in cand.items()) for b in base]
        max_similarity = max(similarities) if similarities else 0.0
        # Distance is 1 - max similarity (how far it is from the closest existing baseline idea)
        distance = max(0.0, 1.0 - max_similarity)
        return max_similarity, distance

    def _score_with_custom_embedder(self, candidate_text: str, baseline_texts: List[str]) -> Tuple[float, float]:
        """Calculates cosine distance using external dense sentence embeddings."""
        embeddings = self.custom_embedder([candidate_text] + baseline_texts)
        cand, base = embeddings[0], embeddings[1:]
        max_similarity = max(_cosine(cand, b) for b in base)
        distance = max(0.0, 1.0 - max_similarity)
        return max_similarity, distance


class ScamperPromptTemplates:
    """Prompt templates for applying SCAMPER defixation to academic literature baselines."""

    OPERATOR_PROMPTS: Dict[ScamperOperator, str] = {
        ScamperOperator.SUBSTITUTE: (
            "Target: Substitute core frameworks, variables, or datasets in existing research.\n"
            "Question: What standard theoretical model, baseline dataset, or core variable in this literature "
            "can be substituted with a non-obvious alternative?\n"
            "Task: Formulate a novel paper thesis where substituting this element reveals hidden insights or challenges the consensus."
        ),
        ScamperOperator.COMBINE: (
            "Target: Combine disparate research paradigms, fields, or methodologies.\n"
            "Question: Which two previously isolated research streams, conflicting paradigms, or distinct methodological tools "
            "can be merged to address this problem?\n"
            "Task: Formulate a novel paper thesis that synthesizes these elements into an integrative framework."
        ),
        ScamperOperator.ADAPT: (
            "Target: Adapt cross-domain solutions, models, or algorithms.\n"
            "Question: What proven model, heuristic, or framework from an entirely different discipline "
            "(e.g., computational biology, physics, ecology, game design) can be adapted to this problem?\n"
            "Task: Formulate a novel paper thesis showing how adapting this cross-domain lens solves a persistent gap."
        ),
        ScamperOperator.MODIFY: (
            "Target: Modify, Magnify, or Minify scale, granularity, or variables.\n"
            "Question: What happens if we magnify a neglected micro-variable to make it the central driver, "
            "or minify a dominant macro-generalization to an edge case?\n"
            "Task: Formulate a novel paper thesis based on radically altering the scale or weight of key variables."
        ),
        ScamperOperator.PUT_TO_ANOTHER_USE: (
            "Target: Repurpose tools, empirical datasets, or models for new domains.\n"
            "Question: How can a model, analytical tool, or dataset developed for a completely different purpose "
            "be put to use to investigate an unexamined aspect of this research topic?\n"
            "Task: Formulate a novel paper thesis demonstrating the repurposed utility of this method/dataset."
        ),
        ScamperOperator.ELIMINATE: (
            "Target: Eliminate legacy assumptions, redundant constraints, or complex parameters.\n"
            "Question: What long-standing assumption, parameter, or procedural constraint can be removed entirely?\n"
            "Task: Formulate a novel paper thesis proving that the current consensus is merely an artifact of an unnecessary assumption."
        ),
        ScamperOperator.REVERSE: (
            "Target: Reverse or Rearrange causal direction, operational sequence, or roles.\n"
            "Question: What if the established causal direction (A -> B) is reversed (B -> A), or the sequence of steps is flipped?\n"
            "Task: Formulate a novel paper thesis that turns the traditional causal or structural narrative upside down."
        )
    }

    @classmethod
    def build_system_prompt(cls) -> str:
        return (
            "You are an expert academic strategist and creative defixation engine. "
            "Your task is to analyze existing academic literature on a topic, break mental fixations, "
            "and propose highly original, defensible research theses for new academic papers using the SCAMPER methodology."
        )

    @classmethod
    def build_user_prompt(cls, baseline: LiteratureBaseline, operator: ScamperOperator) -> str:
        operator_instructions = cls.OPERATOR_PROMPTS[operator]

        prompt = (
            f"=== RESEARCH TOPIC ===\n{baseline.topic}\n\n"
            "=== LITERATURE BASELINE DECONSTRUCTION ===\n"
            f"1. Consensus Claims: {json.dumps(baseline.consensus_claims, indent=2)}\n"
            f"2. Theoretical Frameworks: {json.dumps(baseline.theoretical_frameworks, indent=2)}\n"
            f"3. Common Methodologies: {json.dumps(baseline.methodologies, indent=2)}\n"
            f"4. Implicit Assumptions: {json.dumps(baseline.implicit_assumptions, indent=2)}\n\n"
            f"=== SCAMPER OPERATOR: {operator.value.upper()} ===\n"
            f"{operator_instructions}\n\n"
            "=== OUTPUT INSTRUCTIONS ===\n"
            "Provide 2 distinct candidate paper directions in valid JSON format as a list of objects containing:\n"
            "  - 'target_element': Specific baseline item targeted\n"
            "  - 'novel_angle': Short description of the assumption-breaking move\n"
            "  - 'proposed_thesis': Clear 1-2 sentence thesis statement for a paper\n"
            "  - 'rationale': Why this thesis is academically significant and publishable\n"
        )
        return prompt


class PaperOutlinePromptTemplates:
    """Prompt templates for converting a SCAMPER-selected thesis into a structured academic paper outline."""

    @classmethod
    def build_system_prompt(cls) -> str:
        return (
            "You are an expert academic editor and principal research strategist. "
            "Your task is to take a high-novelty research thesis statement generated via SCAMPER defixation "
            "and build a rigorous, publication-ready academic paper outline that directly contrasts "
            "the new proposed angle against the existing baseline literature."
        )

    @classmethod
    def build_user_prompt(cls, thesis: ScamperCandidateThesis, baseline: LiteratureBaseline) -> str:
        prompt = (
            f"=== RESEARCH TOPIC ===\n{baseline.topic}\n\n"
            "=== LITERATURE BASELINE ===\n"
            f"- Consensus Claims: {json.dumps(baseline.consensus_claims)}\n"
            f"- Theoretical Frameworks: {json.dumps(baseline.theoretical_frameworks)}\n"
            f"- Methodologies: {json.dumps(baseline.methodologies)}\n"
            f"- Implicit Assumptions: {json.dumps(baseline.implicit_assumptions)}\n\n"
            f"=== CHOSEN NOVEL THESIS (SCAMPER OPERATOR: {thesis.operator_label}) ===\n"
            f"- Target Element: {thesis.target_element}\n"
            f"- Novel Angle: {thesis.novel_angle}\n"
            f"- Proposed Thesis: {thesis.proposed_thesis}\n"
            f"- Academic Rationale: {thesis.rationale}\n"
            f"- Novelty Score: {thesis.novelty_score}/10 ({thesis.ranking_tier})\n\n"
            "=== TASK ===\n"
            "Generate a publication-ready academic paper outline in valid JSON format matching this schema:\n"
            "{\n"
            '  "working_title": "Compelling, rigorous academic paper title",\n'
            '  "target_journal_or_conference": "e.g., IEEE / ACM / Nature / MIS Quarterly / ArXiv",\n'
            '  "abstract_sketch": "150-200 word abstract sketch highlighting the gap, SCAMPER intervention, method, and contribution",\n'
            '  "sections": [\n'
            "    {\n"
            '      "section_number": "1",\n'
            '      "section_title": "Introduction",\n'
            '      "core_objective": "Main goal of this section",\n'
            '      "key_subsections": ["1.1 Context & Baseline Fixation", "1.2 The SCAMPER Pivot", "1.3 Research Questions & Contributions"],\n'
            '      "baseline_contrast_notes": "How this section explicitly breaks from consensus"\n'
            "    }\n"
            "  ]\n"
            "}\n"
        )
        return prompt


class PaperOutlineGenerator:
    """Generates structured academic paper outlines from SCAMPER candidate theses."""

    def __init__(self, llm_client: Optional[Any] = None):
        self.llm_client = llm_client

    def generate_outline(
        self,
        thesis: ScamperCandidateThesis,
        baseline: LiteratureBaseline
    ) -> AcademicPaperOutline:
        """Invokes LLM (or mock generator) to convert a SCAMPER thesis into a paper outline."""
        user_prompt = PaperOutlinePromptTemplates.build_user_prompt(thesis, baseline)

        if self.llm_client:
            response = self.llm_client.complete(
                system_prompt=PaperOutlinePromptTemplates.build_system_prompt(),
                prompt=user_prompt
            )
            raw_data = json.loads(response)
        else:
            raw_data = self._mock_outline_response(thesis, baseline)

        sections = [
            PaperOutlineSection(
                section_number=s.get("section_number", ""),
                section_title=s.get("section_title", ""),
                core_objective=s.get("core_objective", ""),
                key_subsections=s.get("key_subsections", []),
                baseline_contrast_notes=s.get("baseline_contrast_notes", "")
            )
            for s in raw_data.get("sections", [])
        ]

        return AcademicPaperOutline(
            working_title=raw_data.get("working_title", f"Reframing {baseline.topic} via {thesis.operator_label}"),
            target_journal_or_conference=raw_data.get("target_journal_or_conference", "Target Academic Journal"),
            abstract_sketch=raw_data.get("abstract_sketch", ""),
            core_thesis_statement=thesis.proposed_thesis,
            scamper_operator_used=thesis.operator_label,
            sections=sections,
            novelty_score=thesis.novelty_score
        )

    def _mock_outline_response(
        self,
        thesis: ScamperCandidateThesis,
        baseline: LiteratureBaseline
    ) -> Dict[str, Any]:
        """Provides a structured fallback outline for dry-runs and automated tests."""
        return {
            "working_title": f"Beyond Cognitive Fixation: {thesis.novel_angle} in {baseline.topic}",
            "target_journal_or_conference": "Journal of Automated Scientific Discovery & AI Research",
            "abstract_sketch": (
                f"Existing literature on {baseline.topic} predominantly relies on standard paradigms such as "
                f"{', '.join(baseline.theoretical_frameworks[:1]) if baseline.theoretical_frameworks else 'conventional models'}. "
                f"However, this approach suffers from implicit fixation on the assumption that {baseline.implicit_assumptions[0] if baseline.implicit_assumptions else 'the status quo holds'}. "
                f"Applying the SCAMPER operator ({thesis.operator_label}), this paper proposes a paradigm shift: "
                f"{thesis.proposed_thesis} We formalize this theoretical model, evaluate its semantic distance against baseline literature, "
                "and demonstrate its capacity to unlock unexamined research vectors."
            ),
            "sections": [
                {
                    "section_number": "1",
                    "section_title": "Introduction & Motivation",
                    "core_objective": f"Establish the baseline literature consensus on {baseline.topic} and expose the fixation bottleneck.",
                    "key_subsections": [
                        "1.1 Current State of Literature & The Fixation Plateau",
                        f"1.2 The SCAMPER Interventional Move: {thesis.operator_label}",
                        "1.3 Summary of Contributions & Paper Organization"
                    ],
                    "baseline_contrast_notes": f"Exposes that consensus claims rely on unexamined assumptions regarding {thesis.target_element}."
                },
                {
                    "section_number": "2",
                    "section_title": "Literature Baseline & Defixation Framework",
                    "core_objective": "Deconstruct standard models and introduce the SCAMPER transformation model.",
                    "key_subsections": [
                        "2.1 Deconstruction of Baseline Claims and Assumptions",
                        f"2.2 Operational Mechanics of {thesis.operator_label} in Academic Contexts",
                        "2.3 Theoretical Justification & Rationale"
                    ],
                    "baseline_contrast_notes": f"Directly contrasts {thesis.novel_angle} against standard theoretical lenses."
                },
                {
                    "section_number": "3",
                    "section_title": "Proposed Methodology & System Architecture",
                    "core_objective": "Formulate the formal model and experimental or analytical apparatus.",
                    "key_subsections": [
                        "3.1 Formal Model Specification",
                        "3.2 Dataset Selection / Algorithmic Pipeline",
                        "3.3 Quantitative Evaluation Protocols (Semantic Distance & Validation)"
                    ],
                    "baseline_contrast_notes": f"Replaces traditional methods with the proposed {thesis.operator_label} architecture."
                },
                {
                    "section_number": "4",
                    "section_title": "Results & Comparative Analysis",
                    "core_objective": "Demonstrate the superiority, coverage, or explanatory power of the new thesis.",
                    "key_subsections": [
                        "4.1 Quantitative Novelty & Coverage Benchmarks",
                        "4.2 Qualitative Case Studies & Ablation Analysis",
                        "4.3 Sensitivity Analysis across Boundary Conditions"
                    ],
                    "baseline_contrast_notes": "Shows superior performance and divergence from baseline benchmarks."
                },
                {
                    "section_number": "5",
                    "section_title": "Discussion & Theoretical Implications",
                    "core_objective": "Address broader impacts, paradigm shifts, and future research directions.",
                    "key_subsections": [
                        "5.1 Paradigm Shifts in Meta-Research and Discovery",
                        "5.2 Limitations & Threats to Validity",
                        "5.3 Future Extensions for Automated Scientific Pipelines"
                    ],
                    "baseline_contrast_notes": "Outlines how future literature should adjust to the eliminated/transformed assumption."
                },
                {
                    "section_number": "6",
                    "section_title": "Conclusion",
                    "core_objective": "Summarize key findings and re-affirm the core thesis.",
                    "key_subsections": [
                        "6.1 Summary of Core Contributions",
                        "6.2 Closing Remarks for the Field"
                    ],
                    "baseline_contrast_notes": "Re-iterates the paradigm shift over status-quo literature."
                }
            ]
        }


class ScamperAcademicPipelineCommand:
    """Core command class for integrating SCAMPER into the Academic Pipeline with Novelty Scoring and Outline Generation."""

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        custom_embedder: Optional[Callable[[List[str]], Sequence[Sequence[float]]]] = None
    ):
        self.llm_client = llm_client
        self.scorer = SemanticDistanceScorer(custom_embedder=custom_embedder)
        self.outline_generator = PaperOutlineGenerator(llm_client=llm_client)

    def run_operator(self, baseline: LiteratureBaseline, operator: ScamperOperator) -> List[ScamperCandidateThesis]:
        """Runs a single SCAMPER operator against the baseline and scores generated theses."""
        user_prompt = ScamperPromptTemplates.build_user_prompt(baseline, operator)

        if self.llm_client:
            response = self.llm_client.complete(
                system_prompt=ScamperPromptTemplates.build_system_prompt(),
                prompt=user_prompt
            )
            raw_results = json.loads(response)
        else:
            raw_results = self._mock_llm_response(baseline, operator)

        candidates = []
        for item in raw_results:
            thesis_text = item.get("proposed_thesis", "")
            sim, dist, nov_score, tier = self.scorer.score_thesis(thesis_text, baseline)

            candidates.append(ScamperCandidateThesis(
                operator=operator,
                operator_label=operator.value.upper(),
                target_element=item.get("target_element", ""),
                novel_angle=item.get("novel_angle", ""),
                proposed_thesis=thesis_text,
                rationale=item.get("rationale", ""),
                baseline_similarity=sim,
                semantic_distance=dist,
                novelty_score=nov_score,
                ranking_tier=tier
            ))
        return candidates

    def run_full_scamper(self, baseline: LiteratureBaseline, rank_by_novelty: bool = True) -> Dict[str, Any]:
        """Executes all 7 SCAMPER operators, scores all generated candidates, and ranks them."""
        all_candidates: List[ScamperCandidateThesis] = []

        for operator in ScamperOperator:
            candidates = self.run_operator(baseline, operator)
            all_candidates.extend(candidates)

        if rank_by_novelty:
            all_candidates.sort(key=lambda c: c.semantic_distance, reverse=True)

        return {
            "topic": baseline.topic,
            "total_candidates_generated": len(all_candidates),
            "candidates_ranked": [asdict(c) for c in all_candidates],
            "top_paradigm_shift_thesis": asdict(all_candidates[0]) if all_candidates else None
        }

    def generate_paper_outline(
        self,
        baseline: LiteratureBaseline,
        selected_thesis: Optional[ScamperCandidateThesis] = None
    ) -> AcademicPaperOutline:
        """Generates a full academic paper outline for a specific SCAMPER thesis or auto-selected top thesis."""
        if selected_thesis is None:
            scamper_results = self.run_full_scamper(baseline, rank_by_novelty=True)
            top_dict = scamper_results["top_paradigm_shift_thesis"]
            if not top_dict:
                raise ValueError("No SCAMPER candidate theses could be generated from the baseline.")
            selected_thesis = _thesis_from_dict(top_dict)

        return self.outline_generator.generate_outline(selected_thesis, baseline)

    def _mock_llm_response(self, baseline: LiteratureBaseline, operator: ScamperOperator) -> List[Dict[str, str]]:
        """Mock fallback generator for demonstration and testing without active API key."""
        target_f = baseline.theoretical_frameworks[0] if baseline.theoretical_frameworks else "Standard Model"
        target_a = baseline.implicit_assumptions[0] if baseline.implicit_assumptions else "Default Assumption"

        mock_map = {
            ScamperOperator.SUBSTITUTE: [
                {
                    "target_element": target_f,
                    "novel_angle": f"Substitute {target_f} with Information Foraging Theory",
                    "proposed_thesis": f"By substituting {target_f} with Information Foraging Theory, we demonstrate that researcher cognitive fixation is driven by energy-minimization heuristics rather than analytical limitations.",
                    "rationale": "Challenges the foundational paradigm and offers a quantitative behavioral alternative."
                }
            ],
            ScamperOperator.COMBINE: [
                {
                    "target_element": "Methodology + Literature Parsing",
                    "novel_angle": "Combine Vector Embedding Distances with SCAMPER Prompts",
                    "proposed_thesis": "Combining semantic embedding distances with SCAMPER operators enables automated real-time novelty scoring of generated research hypotheses.",
                    "rationale": "Creates a hybrid computational-creativity framework for automated scientific discovery."
                }
            ],
            ScamperOperator.ADAPT: [
                {
                    "target_element": "Literature Search Heuristics",
                    "novel_angle": "Adapt Evolutionary Genetic Algorithms",
                    "proposed_thesis": "We adapt genetic recombination algorithms to 'breed' academic hypotheses across distant literature clusters, bypassing human confirmation bias.",
                    "rationale": "Imports a proven optimization technique from biology into automated meta-research."
                }
            ],
            ScamperOperator.MODIFY: [
                {
                    "target_element": "Publication Volume Variable",
                    "novel_angle": "Magnify micro-outliers over macro-consensus",
                    "proposed_thesis": "Magnifying 1% citation-outlier papers over median consensus studies reveals that disruptive breakthroughs systematically originate from rejected methodologies.",
                    "rationale": "Inverts the standard systematic literature review weighting model."
                }
            ],
            ScamperOperator.PUT_TO_ANOTHER_USE: [
                {
                    "target_element": "Bibliometric VOSviewer Networks",
                    "novel_angle": "Repurpose keyword co-occurrence for gap detection",
                    "proposed_thesis": "We put bibliometric co-occurrence maps to another use by treating sparse network gaps as quantitative blueprints for unwritten papers.",
                    "rationale": "Transforms passive descriptive bibliometrics into a predictive hypothesis engine."
                }
            ],
            ScamperOperator.ELIMINATE: [
                {
                    "target_element": target_a,
                    "novel_angle": f"Eliminate assumption: '{target_a}'",
                    "proposed_thesis": f"Eliminating the long-standing assumption that '{target_a}' proves that current empirical models suffer from systemic over-fitting.",
                    "rationale": "High-impact subtraction that reframes existing empirical data."
                }
            ],
            ScamperOperator.REVERSE: [
                {
                    "target_element": "Causal Sequence in Consensus Claims",
                    "novel_angle": "Reverse cause and effect relationship",
                    "proposed_thesis": "We reverse the accepted causal arrow, establishing that variable Y precedes and induces variable X in experimental setups.",
                    "rationale": "Radical reversal that forces the field to re-evaluate legacy experimental designs."
                }
            ]
        }
        return mock_map.get(operator, [])


def _thesis_from_dict(d: Dict[str, Any]) -> ScamperCandidateThesis:
    return ScamperCandidateThesis(
        operator=ScamperOperator(d["operator"]),
        operator_label=d["operator_label"],
        target_element=d["target_element"],
        novel_angle=d["novel_angle"],
        proposed_thesis=d["proposed_thesis"],
        rationale=d["rationale"],
        baseline_similarity=d["baseline_similarity"],
        semantic_distance=d["semantic_distance"],
        novelty_score=d["novelty_score"],
        ranking_tier=d["ranking_tier"],
    )


def run_scamper_pipeline(
    baseline_data: Any,
    generate_outline: bool = True,
    llm_client: Optional[Any] = None,
    custom_embedder: Optional[Callable[[List[str]], Sequence[Sequence[float]]]] = None,
) -> Dict[str, Any]:
    """
    Programmatic entry point. Ingests a literature baseline (dict, LiteratureBaseline, or path to a JSON file),
    runs all 7 SCAMPER operators ranked by novelty, and passes the top-ranked thesis into generate_paper_outline().

    Returns {"scamper": <run_full_scamper result>, "outline": <AcademicPaperOutline as dict> | None}.
    """
    if isinstance(baseline_data, LiteratureBaseline):
        baseline = baseline_data
    elif isinstance(baseline_data, str):
        with open(baseline_data, "r") as f:
            baseline = LiteratureBaseline.from_dict(json.load(f))
    else:
        baseline = LiteratureBaseline.from_dict(baseline_data)

    command = ScamperAcademicPipelineCommand(llm_client=llm_client, custom_embedder=custom_embedder)
    scamper = command.run_full_scamper(baseline, rank_by_novelty=True)

    outline = None
    if generate_outline and scamper["top_paradigm_shift_thesis"]:
        top = _thesis_from_dict(scamper["top_paradigm_shift_thesis"])
        outline = asdict(command.generate_paper_outline(baseline, selected_thesis=top))

    return {"scamper": scamper, "outline": outline}


def _demo_baseline(topic: str) -> LiteratureBaseline:
    return LiteratureBaseline(
        topic=topic,
        consensus_claims=[
            "LLMs increase idea volume but exhibit cognitive fixation and output homogenization.",
            "Structured prompting improves individual creative fluency."
        ],
        theoretical_frameworks=[
            "Cognitive Load Theory",
            "Divergent Thinking Frameworks (Torrance / Guilford)"
        ],
        methodologies=[
            "Semantic Cosine Distance on Sentence Embeddings",
            "Human Subject Pre-test/Post-test Evaluation"
        ],
        implicit_assumptions=[
            "Ideation and evaluation must occur in separate sequential steps.",
            "Human researchers must manually formulate the initial paper thesis."
        ]
    )


def _print_outline_markdown(outline: Dict[str, Any]) -> None:
    print(f"# Academic Paper Outline: {outline['working_title']}\n")
    print(f"**Target Journal/Conference**: {outline['target_journal_or_conference']}")
    print(f"**Core Thesis Statement**: {outline['core_thesis_statement']}")
    print(f"**SCAMPER Strategy**: {outline['scamper_operator_used']} | **Novelty Score**: {outline['novelty_score']}/10\n")
    print(f"### Abstract Sketch\n{outline['abstract_sketch']}\n")
    print("---\n### Paper Structure & Sections\n")
    for sec in outline["sections"]:
        print(f"#### {sec['section_number']}. {sec['section_title']}")
        print(f"- **Core Objective**: {sec['core_objective']}")
        print("- **Key Subsections**:")
        for sub in sec["key_subsections"]:
            print(f"  - {sub}")
        print(f"- **Baseline Contrast**: {sec['baseline_contrast_notes']}\n")


def _print_candidates_markdown(topic: str, candidates: List[Dict[str, Any]]) -> None:
    print(f"# SCAMPER Analysis & Automated Novelty Scoring\n**Topic**: {topic}\n")
    print("| Rank | Operator | Novelty Score (0-10) | Distance | Ranking Tier | Proposed Thesis |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for idx, c in enumerate(candidates, 1):
        print(f"| {idx} | **{c['operator_label']}** | **{c['novelty_score']}/10** | {c['semantic_distance']} | {c['ranking_tier']} | {c['proposed_thesis']} |")
    print("\n---\n### Thesis Details & Rationale\n")
    for idx, c in enumerate(candidates, 1):
        print(f"#### {idx}. [{c['operator_label']}] {c['novel_angle']}")
        print(f"- **Target Element**: {c['target_element']}")
        print(f"- **Proposed Thesis**: {c['proposed_thesis']}")
        print(f"- **Rationale**: {c['rationale']}")
        print(f"- **Baseline Similarity**: {c['baseline_similarity']} | **Semantic Distance**: {c['semantic_distance']} | **Tier**: {c['ranking_tier']}\n")


def main():
    parser = argparse.ArgumentParser(description="Academic Pipeline SCAMPER Command CLI (with Novelty Scoring & Outline Generator)")
    parser.add_argument("--topic", type=str, default="Automated Academic Hypothesis Generation", help="Research topic")
    parser.add_argument("--baseline-json", type=str, default=None, help="Path to JSON file containing LiteratureBaseline")
    parser.add_argument("--operator", type=str, choices=[op.value for op in ScamperOperator] + ["all"], default="all", help="SCAMPER operator to run")
    parser.add_argument("--generate-outline", action="store_true", help="Generate a full academic paper outline for the top-ranked thesis")
    parser.add_argument("--output", type=str, default="markdown", choices=["json", "markdown"], help="Output format")

    args = parser.parse_args()

    if args.baseline_json:
        with open(args.baseline_json, "r") as f:
            baseline = LiteratureBaseline.from_dict(json.load(f))
    else:
        baseline = _demo_baseline(args.topic)

    if args.operator == "all":
        result = run_scamper_pipeline(baseline, generate_outline=args.generate_outline)
        if args.output == "json":
            print(json.dumps(result if args.generate_outline else result["scamper"], indent=2))
        elif args.generate_outline:
            _print_outline_markdown(result["outline"])
        else:
            _print_candidates_markdown(baseline.topic, result["scamper"]["candidates_ranked"])
        return

    op = ScamperOperator(args.operator)
    candidates = ScamperAcademicPipelineCommand().run_operator(baseline, op)
    results = {"topic": baseline.topic, "operator": op.value, "candidates_ranked": [asdict(c) for c in candidates]}
    if args.output == "json":
        print(json.dumps(results, indent=2))
    else:
        _print_candidates_markdown(baseline.topic, results["candidates_ranked"])


if __name__ == "__main__":
    main()
