# AGENTS.md

## Project Mission
This project maintains the 3003 SC1 psychology stickman workflow. The platform must let a user enter one topic and generate a complete reference-style finished video through the full pipeline: viral script generation, semantic script splitting, material matching, voice synthesis, Remotion rendering, progress reporting, validation, and delivery.

The primary quality bar is the reference video:

- Local reference: `E:\ai\火柴人工作流\SC1全赛道高级版火柴人\20250901-10a36ef4-5593-478f-a2f6-5b28301f4a7e.mov`
- Local material library: `E:\ai\火柴人工作流\outputs`
- Remote material library: `/opt/manim_assets/sc1-outputs`
- Remote 3003 deploy root: `/opt/manim-v2-3003-snapshot`
- Current deploy branch: `codex/3003-standalone-stickman-workflow-20260712`

## Non-Negotiable Output Requirements
- Use exactly one centered scene image at a time.
- The scene image must be fully visible, not covered by subtitles, floor lines, panels, masks, or preview cropping.
- Do not continuously zoom the scene image after it appears.
- Scene image transitions should feel varied and smooth, such as gentle slide-in or rise-in, without looking like hard cuts.
- A semantic segment may share one scene image across 2-3 caption cues, but no segment should cover more than 3 cues.
- Subtitles must change for every caption cue and must cover the full narration.
- Chinese subtitles must be centered; final punctuation inside a cue should be removed.
- English subtitles must stay synchronized with the Chinese cue when present.
- Summary keywords must be 2-4 character emotional Chinese phrases, not copied chunks from subtitles.
- Summary keywords reveal cumulatively within the current semantic segment; earlier keywords remain visible until the segment ends.
- Summary keywords clear together when the semantic segment changes.
- Do not show `@Sc1火柴人`.
- Keep the right-top label: `心理分享 | 认知突破`.
- Use the configured/default reference voice unless the user explicitly selects another voice.
- Audio, Chinese subtitle, English subtitle, scene image, and summary keywords must share the same cue timeline.

## Development Workflow
- Read `PROJECT_STATE.md` before making changes after any context reset.
- Update `PROJECT_STATE.md` before every remote sync, deployment, or context handoff.
- Keep edits scoped to the requested feature or fix.
- Prefer existing backend, frontend, and Remotion patterns over new abstractions.
- Do not commit secrets, API keys, generated storage files, uploaded media, caches, or transient build artifacts.
- Keep documentation changes close to the project root: `AGENTS.md`, `PROJECT_STATE.md`, `rules/`, `specs/`, and relevant `docs/` files.
- Commit small, reviewable changes. A useful commit either improves generation behavior, fixes validation, or updates reproducibility documentation.

## Validation Checklist
Before declaring the video workflow fixed, validate through the platform, not only local scripts:

1. Create a job through `http://152.136.218.74:3003`.
2. Confirm the job reaches `completed`.
3. Download the generated MP4.
4. Confirm the MP4 has both video and audio streams.
5. Extract frames at representative cue boundaries and scene transitions.
6. Check scene image visibility, subtitle centering, summary keyword behavior, right-top label, and absence of watermark.
7. Compare against the reference video for layout, timing, and overall visual feel.
8. Record the validated job id, output path, branch, commit, and deploy time in `PROJECT_STATE.md` before syncing or handing off.

## Important Files
- `backend/app/services/ai_video.py`: script planning, SC1 segmentation, material matching, TTS, audio/cue timing, render payload.
- `backend/app/api/stickman_workflow.py`: one-click workflow API surface and platform job behavior.
- `frontend/src/pages/StickmanWorkflow/index.tsx`: user workflow page and generation UX.
- `frontend/src/pages/StickmanWorkflow/StickmanWorkflow.css`: preview, progress, and workflow styling.
- `video-render-service/remotion-mind-video/src/remotion/Sc1StickmanVideo.jsx`: final video composition, scene image layout, subtitle rendering, keyword reveal, audio playback.
- `docs/心理学火柴人视频复刻文档.md`: user-facing style and replication requirements.
- `rules/vibe-coding.md`: day-to-day coding constraints.
- `specs/sc1-stickman-workflow-spec.md`: product and technical specification.

## Remote Operations
- SSH target: `root@152.136.218.74`.
- Use existing helper scripts in `scripts/` for remote execution and file upload when available.
- Restart only the services that are required for the changed layer:
  - Backend/API changes: `manim-v2-3003-backend.service`
  - Worker/TTS/render orchestration changes: `manim-v2-3003-worker.service`
  - Remotion renderer changes: `manim-v2-3003-ai-video-render.service`
- After deployment, verify service health and generate a fresh platform job.

## Context Recovery
If a future agent loses context:

1. Read this `AGENTS.md`.
2. Read `PROJECT_STATE.md`.
3. Read `specs/sc1-stickman-workflow-spec.md`.
4. Read `rules/vibe-coding.md`.
5. Continue from the latest recorded branch, commit, deploy root, and validation result.
6. Do not restart from scratch unless the user explicitly asks for a redesign.
