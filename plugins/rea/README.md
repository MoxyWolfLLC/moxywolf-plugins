# rea (pointer)

[REA, Reverse Engineer Anything](https://github.com/morluto/rea) (morluto, MIT) is one MCP server and CLI that inspects shipped software and returns findings with the evidence behind them. Native binaries through Hopper, Ghidra or IDA. Electron and JavaScript trees and ASARs. .NET assemblies, Go binaries, WASM, PE resources, SQLite snapshots, APKs, Flutter, firmware, HAR and SAZ captures, pcaps, Linux core dumps, and live browser, Electron or process observation. Read at `7a6defa` (6.4.0, 2026-10-11).

## Why this is a pointer, not a vendored build

REA's engine is a Node runtime: 1,758 TypeScript source files and 38 runtime dependencies behind a markdown skill. Most of its interesting lanes need a caller-supplied engine on the host (Ghidra, JADX, tshark, pwntools, binwalk). Re-homing it here would ship commands that fail without that stack. That's the same reason understand-anything and claude-mem's runtime aren't re-homed (DR-011). This entry documents and points; it registers nothing.

## The engine split

Two halves, and the free one covers what we'd point it at.

- **No engine needed.** Static JavaScript and Electron analysis, .NET metadata and CIL, Go build metadata, PE resources, SQLite snapshots, package and bundle inventories. Node and npm only.
- **Engine needed.** Native pseudocode and assembly (Hopper, paid; Ghidra, free; IDA, paid). APKs (JADX and a JDK). Firmware, pcaps, crashes and EVM (Linux only).

## Set it up upstream (one line)

```
npx rea-agents setup
```

Pick the agents, review the proposed changes, approve, restart. It registers the MCP server and installs the matching skill. Native lanes need a provider configured first; see REA's installation guide. Registering is per machine. Do it when someone has a binary question, not before.

## When to reach for it vs. what MoxyWolf already has

- **rea**: a shipped artifact, not a source tree. "What does this Electron build actually call over IPC?" "What's in the vendored plugin JS we didn't write?" "Which Go modules and versions are baked into this binary?" REA's own skill says to skip it for ordinary source-repository analysis.
- **graphify**: Obsidian-format knowledge graphs of a source tree, cross-linked with vault notes.
- **understand-anything**: interactive onboarding dashboard over a source tree.
- **github-repo-analyzer**: health, security-classified issue review, reverse-PRD over a repository.
- **security `vulnerability-management`**: the discipline. REA is one of its tools for the "know what you actually ship" question.

## What we took from it

Two ideas, re-expressed in our words, no code copied, declared in `DESIGN.md`:

- **EV-010.** Every result that can carry target-derived text is marked untrusted on the wire, default on, and the agent reports an embedded instruction instead of following it.
- **EV-011.** An unknown is a revisioned record naming the authority that can close it, refused on a stale revision, closed only by evidence of matching authority.

Not taken: the reconstruction obligation ledger (needs typed manifests and verifier authority levels this loop doesn't have) and the tool-shape table (a note for the next `mcp-builder` edit). Fit note: `Taskade/Team Plugins/06 – Engineering/rea-fit-2026-10-13.md`.

## Attribution

REA is MIT, Copyright the morluto contributors. No REA code is in this repository. Commercial engines it can drive (IDA, Hopper, JEB) need their own licenses.
