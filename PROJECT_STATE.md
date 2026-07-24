# Project State

## Current Task
Complete local development-process documentation so future Codex sessions can recover the 3003 SC1 workflow context without relying on chat memory.

## Current Focus
- Add a project-level `AGENTS.md` inside the real code worktree.
- Add `rules/vibe-coding.md` with day-to-day AI-assisted coding constraints.
- Add `specs/sc1-stickman-workflow-spec.md` with product and technical acceptance criteria.
- Add an implementation-plan record under `docs/superpowers/plans/`.
- Keep the top-level workspace `AGENTS.md` pointing future sessions to `work/3003-deploy-worktree`.

## Current Fixes
- Development-process docs added locally; no 3003 service restart or remote deployment is required for this documentation-only change.
- The top-level workspace `AGENTS.md` was rewritten in UTF-8 and now points to the active local code project.
- The code-project `AGENTS.md` now records the 3003 mission, SC1 reference video, material paths, non-negotiable output requirements, validation checklist, important files, remote operations, and context recovery steps.
- `rules/vibe-coding.md` now records state discipline, scope control, video validation, coding style, testing, commit, and sync rules.
- `specs/sc1-stickman-workflow-spec.md` now records the one-click SC1 workflow user flow, script generation, semantic segmentation, material matching, layout, subtitles, summary keywords, voice/audio, progress UX, and acceptance criteria.
- `docs/superpowers/plans/2026-07-24-development-process-docs.md` records the plan used for this documentation update.
- Default voice is now `dayun_manbo`.
- Open-source CosyVoice fallback can use `dayun_tools_manbo_tts_test.mp3` as prompt audio.
- SC1 caption cues are now assigned explicit timings from the backend.
- SC1 material images are cleaned for white backgrounds before render sync.
- Scene images are centered smaller and enter with a gentle slide instead of a hard pop.
- Scene text placeholders like `?` now fall back to prompt-based lines before TTS.
- Summary labels avoid directly copying the subtitle when a more emotional 2-4 character label is available, e.g. `想太多` becomes `内耗`.
- Frontend preview video must use `object-fit: contain` so the platform does not crop the 16:9 rendered MP4.
- Scene images are slightly smaller and higher to leave a clearer safety gap above the subtitle floor line.
- Material selection penalizes images whose foreground touches the bottom edge, so half-cut or bottom-clipped figures are less likely to be selected.
- SC1 narration can be synthesized per caption cue and concatenated, so Chinese subtitle, English subtitle, summary labels, and voice timing share the same cue timeline.
- Material staging removes white backgrounds, crops to the actual foreground bbox, and re-pads with transparent margins to avoid a white-mask look inside the scene image.
- Current in-progress fix removes render-time clipping during scene-image slide-in, trims each cue audio before concatenation, preserves all backend semantic segments in Remotion, and repacks material foregrounds into a transparent 500:350 target-ratio canvas.

## Reproducibility Anchor
- Branch: `codex/3003-standalone-stickman-workflow-20260712`
- Local baseline before documentation update: `6deea8beb8c9bedcede09bfb9a9538e9d3ff1fb0`
- Local baseline time: `2026-07-20 23:50:44 +0800`
- Local baseline subject: `chore: record 3003 deploy state`
- Deploy source commit: `207319e98a3d8a1baeeb7bacaabdd185b209d4fa`
- Deploy source commit time: `2026-07-20 23:49:57 +0800`
- Snapshot subject: `fix: align sc1 stickman render sync`
- Remote deploy root: `/opt/manim-v2-3003-snapshot`
- Latest confirmed remote deploy HEAD: `360f19f7bfdc31973f6a097c9fd7132c19765f9b`
- Latest confirmed remote deploy time: `2026-07-20 23:54:24 +0800`
- Latest confirmed remote source commit before this sync: `8dc9992dd`
- State updated for local documentation handoff: `2026-07-24 21:21:55 +08:00`
- This documentation-only update should be committed locally after this state update; it does not change the currently deployed 3003 runtime.

## Files Changed This Round
- `AGENTS.md`
- `rules/vibe-coding.md`
- `specs/sc1-stickman-workflow-spec.md`
- `docs/superpowers/plans/2026-07-24-development-process-docs.md`
- `PROJECT_STATE.md`
- Top-level workspace file: `C:\Users\Administrator\Documents\Codex\2026-07-18\300\AGENTS.md`

## Next Step
For future code or deployment work, first read `AGENTS.md`, `rules/vibe-coding.md`, and `specs/sc1-stickman-workflow-spec.md`, then update `PROJECT_STATE.md` before any remote sync or context handoff.
