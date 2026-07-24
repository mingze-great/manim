# SC1 Psychology Stickman Workflow Spec

## Goal
The 3003 platform must support one-click generation of SC1 psychology stickman videos. A user enters a topic and receives a finished video that matches the reference style closely enough for creator collaboration and promotion.

## Reference
- Reference video: `E:\ai\火柴人工作流\SC1全赛道高级版火柴人\20250901-10a36ef4-5593-478f-a2f6-5b28301f4a7e.mov`
- Local material library: `E:\ai\火柴人工作流\outputs`
- Remote material library: `/opt/manim_assets/sc1-outputs`
- Remote platform: `http://152.136.218.74:3003`
- Remote deploy root: `/opt/manim-v2-3003-snapshot`

## User Flow
1. User opens the 3003 platform.
2. User enters a topic.
3. User optionally selects voice and material library.
4. Platform generates a reference-style viral script from the topic.
5. Platform splits the script into semantic segments and caption cues.
6. Platform matches each segment to SC1 material-library images.
7. Platform synthesizes emotional continuous narration.
8. Platform renders the finished video.
9. Platform shows detailed progress throughout generation.
10. Platform returns a playable MP4 and cover.

## Pipeline Requirements

### Script Generation
- Generate punchy psychology-style copy based on the topic.
- The copy should feel close to the reference video: direct, emotional, and insight-driven.
- Avoid placeholder-only scenes such as `?`.
- Preserve enough script detail for all narration to appear in subtitles.

### Semantic Segmentation
- Segment by meaning, not blindly one scene per sentence.
- One semantic segment may contain 1-3 caption cues.
- A segment may reuse one scene image across 2-3 related caption cues.
- No semantic segment should exceed 3 cues.
- Subtitles still change cue-by-cue even when the scene image stays the same.

### Material Matching
- Use one centered scene image only.
- Use the SC1 material library, not unrelated generated placeholders, unless the selected mode explicitly requests live image generation.
- Match material by semantic meaning of the segment.
- Penalize materials that are half-cut, bottom-clipped, too close-up, or visually likely to look blocked.
- Remove white backgrounds and repack foregrounds into transparent canvases before rendering.

### Layout
- Background is stable white paper style.
- Left-top title stays stable and must not flicker.
- Right-top label is `心理分享 | 认知突破`.
- No `@Sc1火柴人` watermark.
- Scene image stays centered, fully visible, and proportionally smaller than the subtitle area.
- The scene image must not be blocked by the horizontal floor line, subtitle area, masks, panels, or preview crop.
- Scene image entrance should use subtle varied slide/rise effects.
- Do not continuously zoom the scene image after it appears.

### Subtitles
- Chinese subtitles are centered.
- Chinese subtitle cue endings should remove final punctuation.
- English subtitle, when present, follows the same cue timing.
- Subtitles must cover the full narration.
- Subtitles must not lag behind the audio because of TTS silence or scene-level averaging.

### Summary Keywords
- Summary keywords are emotional Chinese labels, usually 2-4 characters.
- They should summarize the currently spoken cue, not copy a substring from it.
- Examples: `内耗`, `别急`, `警报`, `边界`, `自责`, `先看`, `结论`.
- Keywords appear one by one as their cue starts.
- Previous keywords remain visible until the current semantic segment ends.
- Keywords clear together when the segment changes.
- Layout may reveal keywords top-to-bottom, left-to-right, or around the scene image, but the composition must stay balanced and readable.

### Voice And Audio
- Default/reference voice is `dayun_manbo` unless the user selects another voice.
- Audio should be continuous and emotional, not choppy.
- Cue-level TTS audio should be trimmed for excessive leading/trailing silence before concatenation.
- Cue timing must drive audio, subtitle, English subtitle, scene image, and summary keyword sync.
- The final MP4 must contain an audio stream.

### Progress UX
- Progress should expose meaningful stages: script understanding, scene planning, material matching, TTS generation, audio processing, rendering, saving, completed.
- The platform should not stay on a vague progress state when a more precise stage is known.
- Failure messages should name the failed provider or stage, such as TTS, render service, network, or material lookup.

## Acceptance Criteria
- A new platform job completes from topic-only input.
- The result is an MP4 with video and audio streams.
- Representative extracted frames show the scene image fully visible.
- Subtitle text changes at every cue and covers the complete narration.
- Cue timeline shows audio frames and caption frames aligned.
- Summary keywords reveal cumulatively within each segment.
- Right-top label is visible.
- No `@Sc1火柴人` watermark appears.
- Material source is the configured SC1 library.
- `PROJECT_STATE.md` records branch, commit, deploy root, validation job id, and output path before any remote sync or handoff.

## Validation Commands
Use equivalent commands if paths differ.

```powershell
python -m py_compile backend/app/services/ai_video.py
git diff --check
```

Create a platform job through `http://152.136.218.74:3003`, download the output MP4, then inspect:

```powershell
$ff='E:\anaconda3\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe'
& $ff -i outputs\sc1_psychology_stickman_platform_job_<id>.mp4 -hide_banner
& $ff -y -ss 9 -i outputs\sc1_psychology_stickman_platform_job_<id>.mp4 -frames:v 1 outputs\sc1_job_<id>_09s.png
```
