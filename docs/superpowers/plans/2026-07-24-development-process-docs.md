# 3003 Development Process Docs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add durable project memory, vibe coding rules, and a formal SC1 workflow spec so future agents can continue without losing the 3003 deployment context.

**Architecture:** Keep durable agent instructions in root `AGENTS.md`, daily coding constraints in `rules/`, product requirements in `specs/`, and evolving execution status in `PROJECT_STATE.md`. This separates stable rules from current state and testable product requirements.

**Tech Stack:** Markdown documentation, existing 3003 Python backend, React frontend, Remotion render service, remote systemd deployment.

## Global Constraints

- Use the SC1 material library at `E:\ai\火柴人工作流\outputs` locally and `/opt/manim_assets/sc1-outputs` remotely.
- Keep one centered scene image only.
- Avoid continuous zoom after the image appears.
- Keep subtitles synchronized to the full narration, not just scene titles.
- Summary keywords must be short emotional Chinese phrases, usually 2-4 characters.
- Update `PROJECT_STATE.md` before every remote sync or context handoff.

---

### Task 1: Add Project Agent Instructions

**Files:**
- Create: `AGENTS.md`

**Interfaces:**
- Consumes: Current user requirements and current `PROJECT_STATE.md`.
- Produces: Root-level instructions that future agents read before changing code.

- [x] **Step 1: Create `AGENTS.md` with project mission and fixed constraints**

Add the SC1 reference-video goal, material paths, one-centered-image constraint, subtitle sync requirements, summary keyword behavior, and remote deployment rules.

- [x] **Step 2: Include context recovery instructions**

Add a sequence telling future agents to read `AGENTS.md`, `PROJECT_STATE.md`, `specs/sc1-stickman-workflow-spec.md`, and `rules/vibe-coding.md` after context reset.

- [x] **Step 3: Verify file exists**

Run: `Test-Path AGENTS.md`
Expected: `True`

### Task 2: Add Vibe Coding Rules

**Files:**
- Create: `rules/vibe-coding.md`

**Interfaces:**
- Consumes: Project constraints in `AGENTS.md`.
- Produces: Day-to-day coding discipline for fast AI-assisted edits.

- [x] **Step 1: Create `rules/vibe-coding.md`**

Document read-before-editing rules, state discipline, change scope, video quality checks, coding style, testing, commits, and remote sync behavior.

- [x] **Step 2: Verify rules are concrete**

Search for forbidden placeholders:

```powershell
$placeholderPattern = 'T' + 'BD|TO' + 'DO|fill in|later'
Select-String -Path rules/vibe-coding.md -Pattern $placeholderPattern
```

Expected: no matches.

### Task 3: Add SC1 Workflow Spec

**Files:**
- Create: `specs/sc1-stickman-workflow-spec.md`

**Interfaces:**
- Consumes: Reference-video requirements and existing platform architecture.
- Produces: Product and technical acceptance criteria for the one-click 3003 SC1 workflow.

- [x] **Step 1: Create the spec**

Include user flow, script generation, semantic segmentation, material matching, layout, subtitles, summary keywords, voice/audio, progress UX, and acceptance criteria.

- [x] **Step 2: Include validation commands**

Add concrete PowerShell examples for `py_compile`, `git diff --check`, ffmpeg stream inspection, and frame extraction.

- [x] **Step 3: Verify spec has acceptance criteria**

Run:

```powershell
Select-String -Path specs/sc1-stickman-workflow-spec.md -Pattern 'Acceptance Criteria'
```

Expected: one match.

### Task 4: Validate Documentation Set

**Files:**
- Read: `AGENTS.md`
- Read: `rules/vibe-coding.md`
- Read: `specs/sc1-stickman-workflow-spec.md`

**Interfaces:**
- Consumes: Completed documentation files.
- Produces: A clean working tree diff ready for review or commit.

- [x] **Step 1: Check the files are discoverable**

Run:

```powershell
rg --files -g AGENTS.md -g "rules/**" -g "specs/**" -g "docs/superpowers/plans/**"
```

Expected: all new documentation files are listed.

- [x] **Step 2: Check markdown diff**

Run:

```powershell
git diff -- AGENTS.md rules specs docs/superpowers/plans
```

Expected: only the intended documentation changes appear.
