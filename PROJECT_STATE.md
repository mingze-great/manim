# Project State

## Current Task
Keep the SC1 psychology stickman workflow aligned with the reference video and make the 3003 deployment reproducible.

## Current Focus
- Keep the deploy baseline reproducible from branch `codex/3003-standalone-stickman-workflow-20260712`.
- Keep the `dayun_tools_manbo_tts_test.mp3` prompt voice as the reference tone.
- Keep the scene image smaller, centered, and fully visible above the floor line.
- Keep subtitle timing, voice, scene image, and summary keywords aligned on the same cue.

## Current Fixes
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
- Local HEAD: `332baf8294b8d5190e818f0b370558076a932775`
- Commit time: `2026-07-20 23:49:12 +0800`
- Snapshot subject: `fix: align sc1 stickman render sync`
- Remote deploy root: `/opt/manim-v2-3003-snapshot`
- Latest confirmed remote source commit before this sync: `8dc9992dd`
- State updated before sync: `2026-07-20 23:49:26 +08:00`
- Current local worktree commit `332baf8294b8d5190e818f0b370558076a932775` is the source intended for the next 3003 deployment sync.

## Files Changed This Round
- `backend/app/services/ai_video.py`
- `backend/app/api/stickman_workflow.py`
- `frontend/src/pages/StickmanWorkflow/index.tsx`
- `video-render-service/remotion-mind-video/src/remotion/Sc1StickmanVideo.jsx`
- `docs/心理学火柴人视频复刻文档.md`
- `PROJECT_STATE.md`

## Next Step
Sync the current fixes to `/opt/manim-v2-3003-snapshot`, restart the 3003 backend, worker, and render services, then run a fresh platform generation and compare rendered frames against the reference video, with special attention to cue timing and scene image framing.
