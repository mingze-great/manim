# Vibe Coding Rules

## Purpose
These rules keep fast AI-assisted development useful without letting the project drift. The goal is to move quickly while preserving reproducibility, deploy safety, and the SC1 reference-video quality bar.

## Read Before Editing
- Read `AGENTS.md` and `PROJECT_STATE.md` at the start of a new context.
- Search for existing implementation before creating a new module.
- Prefer modifying the current workflow over building parallel one-off scripts.
- Treat existing user-approved requirements as source of truth, especially video layout, timing, material library, and deployment branch.

## State Discipline
- Update `PROJECT_STATE.md` before remote sync, deployment, or context handoff.
- Record branch, commit, remote deploy root, changed files, validation job id, output file path, and next steps.
- Never rely on chat memory alone for project state.
- If a context is about to be compressed, summarize the current task, completed work, current problem, changed files, next action, decisions, and do-not-repeat items into `PROJECT_STATE.md`.

## Change Scope
- Make the smallest change that fixes the observed issue.
- Do not rewrite the workflow when a localized backend, frontend, or Remotion patch is sufficient.
- Do not touch generated media, storage folders, build caches, or deployment archives unless the task explicitly requires it.
- Do not commit secrets, tokens, passwords, `.env` secrets, or transient generated files.
- Do not mask video defects with hardcoded fallback zeros, placeholder text, or fake success states.

## Video Quality Rules
- Validate video behavior with actual rendered frames.
- Use the platform full flow for final validation whenever the user asks whether 3003 is usable.
- Confirm subtitles, audio, scene image, and summary keywords share the same cue timeline.
- Check first, middle, last, and previously failing cue boundaries.
- Confirm the scene image is centered, fully visible, and not visually blocked by white background remnants, floor lines, subtitle panels, or preview crop.
- Confirm summary keywords are emotional 2-4 character labels and are not repeated subtitle fragments.

## Coding Style
- Follow existing Python, TypeScript, CSS, and Remotion patterns.
- Keep backend orchestration in `backend/app/services/ai_video.py` unless a local pattern clearly supports splitting.
- Keep final render behavior in `Sc1StickmanVideo.jsx`.
- Use clear names that reflect SC1 concepts: `captionCues`, `summaryLabel`, `assetImages`, `durationFrames`, `audioScenes`.
- Add comments only for non-obvious timing, sync, material-cleaning, or deployment decisions.

## Testing And Verification
- Run syntax checks for modified Python files: `python -m py_compile backend/app/services/ai_video.py`.
- Run `git diff --check` before committing.
- For render changes, generate a fresh platform job and extract frames.
- Confirm the MP4 has an audio stream.
- Keep validation artifacts in `outputs/` only when they are user-facing; use `work/` for scratch files.

## Commit And Sync
- Commit after a coherent fix or documentation update.
- Use concise commit messages, such as `fix: align sc1 cue timing` or `docs: add sc1 workflow rules`.
- Before remote deployment, update `PROJECT_STATE.md` first.
- After remote deployment, record the deployed branch, commit, service restart result, job id, and output path.

## When Unsure
- Preserve the reference video requirements.
- Preserve the material library paths.
- Preserve the single centered scene-image design.
- Ask only if the missing answer changes the user-visible output, target deployment, or irreversible operation.
