import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig
} from 'remotion';
import {scriptToStory} from '../story.js';

const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

const getSceneTiming = (story, frame) => {
  let cursor = 0;
  for (const scene of story.scenes) {
    if (frame < cursor + scene.duration) {
      return {scene, start: cursor, local: frame - cursor, progress: clamp((frame - cursor) / scene.duration, 0, 1)};
    }
    cursor += scene.duration;
  }
  const last = story.scenes[story.scenes.length - 1];
  return {scene: last, start: cursor - last.duration, local: last.duration, progress: 1};
};

const SceneAudio = ({story}) => {
  let cursor = 0;
  return (
    <>
      {story.scenes.map((scene) => {
        const start = cursor;
        cursor += scene.duration;
        if (!scene.audioSrc) return null;
        return (
          <Sequence key={scene.id} from={start} durationInFrames={scene.duration}>
            <Audio src={staticFile(scene.audioSrc)} startFrom={0} endAt={scene.duration} volume={1} />
          </Sequence>
        );
      })}
      {story.bgmSrc ? <Audio src={staticFile(story.bgmSrc)} volume={0.13} /> : null}
    </>
  );
};

const FrameChrome = ({story, scene, palette, progress}) => (
  <>
    <div style={{position: 'absolute', inset: 38, border: `1px solid ${palette.line}`, borderRadius: 24}} />
    <div style={{
      position: 'absolute',
      left: 72,
      top: 58,
      right: 72,
      display: 'flex',
      justifyContent: 'space-between',
      color: palette.muted,
      fontSize: 18
    }}>
      <span>{story.contentType.toUpperCase()} / {scene.mode}</span>
      <span>{String(scene.index + 1).padStart(2, '0')} / {String(story.scenes.length).padStart(2, '0')}</span>
    </div>
    <div style={{
      position: 'absolute',
      left: 72,
      bottom: 54,
      height: 4,
      width: `${1080 * progress}px`,
      borderRadius: 99,
      background: `linear-gradient(90deg, ${palette.accent}, ${palette.accent2}, ${palette.accent3})`,
      boxShadow: `0 0 28px ${palette.accent}`
    }} />
  </>
);

const Particles = ({palette, count = 34}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      {Array.from({length: count}).map((_, index) => {
        const x = (index * 103) % 1280;
        const y = (index * 61) % 720;
        return (
          <div key={index} style={{
            position: 'absolute',
            left: x + Math.sin((frame + index * 9) / 38) * 18,
            top: y + Math.cos((frame + index * 13) / 46) * 14,
            width: 2 + (index % 3),
            height: 2 + (index % 3),
            borderRadius: 99,
            background: index % 3 ? palette.accent : palette.accent2,
            boxShadow: `0 0 22px ${index % 3 ? palette.accent : palette.accent2}`,
            opacity: 0.16 + (index % 5) * 0.04
          }} />
        );
      })}
    </AbsoluteFill>
  );
};

const KeywordRail = ({scene, palette, local, vertical = false}) => (
  <div style={{display: 'flex', flexDirection: vertical ? 'column' : 'row', gap: 12, flexWrap: 'wrap'}}>
    {(scene.keywords || []).slice(0, 4).map((keyword, index) => {
      const lift = spring({frame: local - index * 7, fps: 30, config: {damping: 18, stiffness: 120}});
      return (
        <span key={`${keyword}-${index}`} style={{
          transform: `translateY(${(1 - lift) * 16}px)`,
          opacity: clamp(lift, 0, 1),
          color: index % 2 ? palette.accent2 : palette.accent,
          border: `1px solid ${index % 2 ? palette.accent2 : palette.accent}`,
          padding: '9px 13px',
          borderRadius: 999,
          fontSize: 20,
          lineHeight: 1
        }}>{keyword}</span>
      );
    })}
  </div>
);

const MediaBackdrop = ({scene, palette, local, progress, intensity = 1}) => {
  const src = scene.media?.src;
  const zoom = 1.04 + progress * 0.08 * intensity;
  const drift = Math.sin(local / 34) * 18 * intensity;
  if (!src) {
    return (
      <AbsoluteFill style={{
        background:
          `radial-gradient(circle at ${28 + progress * 40}% 24%, ${palette.accent}33 0, transparent 28%), ` +
          `linear-gradient(135deg, ${palette.bg}, ${palette.panel})`
      }} />
    );
  }
  return (
    <AbsoluteFill>
      <Img
        src={src}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${zoom}) translate(${drift}px, ${-drift * 0.45}px)`,
          filter: scene.media?.blend === 'soft' ? 'saturate(0.9) contrast(0.92)' : 'saturate(0.82) contrast(1.08) brightness(0.62)',
          opacity: scene.media?.blend === 'soft' ? 0.58 : 0.48
        }}
      />
      <AbsoluteFill style={{
        background:
          `linear-gradient(90deg, ${palette.bg}ee 0%, ${palette.bg}aa 42%, transparent 100%), ` +
          `radial-gradient(circle at 72% 22%, ${palette.accent}44 0, transparent 32%)`
      }} />
    </AbsoluteFill>
  );
};

const TransitionLayer = ({scene, palette, local}) => {
  const {fps} = useVideoConfig();
  const enter = spring({frame: local, fps, config: {damping: 18, stiffness: 130}});
  const wipe = interpolate(local, [0, 18], [-100, 110], {extrapolateRight: 'clamp'});
  if (scene.transition === 'flash') {
    const opacity = interpolate(local, [0, 5, 14], [0.85, 0.18, 0], {extrapolateRight: 'clamp'});
    return <AbsoluteFill style={{background: palette.accent2, opacity, mixBlendMode: 'screen'}} />;
  }
  if (scene.transition === 'wipe') {
    return <div style={{position: 'absolute', top: 0, bottom: 0, left: `${wipe}%`, width: 220, background: `linear-gradient(90deg, transparent, ${palette.accent}, transparent)`, transform: 'skewX(-12deg)', opacity: 0.78}} />;
  }
  return <AbsoluteFill style={{opacity: 1 - enter, background: palette.bg, transform: `scale(${1 + (1 - enter) * 0.08})`}} />;
};

const BigType = ({scene, palette, local, progress}) => {
  const {fps} = useVideoConfig();
  const enter = spring({frame: local, fps, config: {damping: 16, stiffness: 90}});
  return (
    <AbsoluteFill style={{padding: 90, justifyContent: 'center'}}>
      <MediaBackdrop scene={scene} palette={palette} local={local} progress={progress} intensity={0.8} />
      <div style={{maxWidth: 880, transform: `translateY(${(1 - enter) * 32}px)`, opacity: enter}}>
        <div style={{fontSize: 28, color: palette.accent, marginBottom: 22}}>{scene.title}</div>
        <h1 style={{fontSize: scene.body.length > 24 ? 70 : 92, lineHeight: 0.98, margin: 0, color: palette.ink}}>
          {scene.body}
        </h1>
        <div style={{marginTop: 28}}><KeywordRail scene={scene} palette={palette} local={local} /></div>
      </div>
      <div style={{
        position: 'absolute',
        right: 92,
        top: 160,
        width: 250,
        height: 250,
        borderRadius: '50%',
        background: `conic-gradient(from ${progress * 360}deg, ${palette.accent}, ${palette.accent2}, ${palette.accent3}, ${palette.accent})`,
        opacity: 0.9
      }} />
    </AbsoluteFill>
  );
};

const CommerceScene = ({scene, palette, local}) => {
  const {fps} = useVideoConfig();
  const pop = spring({frame: local, fps, config: {damping: 12, stiffness: 150}});
  const progress = clamp(local / Math.max(scene.duration, 1), 0, 1);
  return (
    <AbsoluteFill style={{padding: 82}}>
      <MediaBackdrop scene={scene} palette={palette} local={local} progress={progress} />
      <div style={{position: 'absolute', right: 78, top: 98, width: 360, height: 470, borderRadius: 22, background: palette.panel, border: `2px solid ${palette.accent}`, transform: `scale(${0.92 + pop * 0.08})`, boxShadow: `0 0 70px ${palette.accent}44`}}>
        <div style={{padding: 30, color: palette.ink}}>
          <div style={{fontSize: 24, color: palette.accent2}}>SELLING POINT</div>
          <div style={{fontSize: 78, lineHeight: 1, marginTop: 80, color: palette.accent}}>{scene.keywords?.[0] || '卖点'}</div>
          <div style={{fontSize: 24, marginTop: 24, color: palette.muted}}>{scene.cta || '立即行动'}</div>
        </div>
      </div>
      <div style={{position: 'absolute', left: 84, top: 160, width: 690}}>
        <div style={{fontSize: 28, color: palette.accent}}>{scene.title}</div>
        <h1 style={{fontSize: 76, lineHeight: 1.02, margin: '18px 0', color: palette.ink}}>{scene.body}</h1>
        <KeywordRail scene={scene} palette={palette} local={local} />
      </div>
    </AbsoluteFill>
  );
};

const TeachingScene = ({scene, palette, local}) => (
  <AbsoluteFill style={{background: '#f6f3ea', color: '#111', padding: 82}}>
    <MediaBackdrop scene={scene} palette={{...palette, bg: '#f6f3ea', panel: '#fff', accent: '#ff6b2c', accent2: '#2f80ed'}} local={local} progress={clamp(local / Math.max(scene.duration, 1), 0, 1)} intensity={0.35} />
    <div style={{position: 'absolute', inset: 54, background: '#fff', border: '2px solid #111', borderRadius: 8}} />
    <div style={{position: 'relative', zIndex: 1}}>
      <div style={{fontSize: 24, color: '#ff6b2c'}}>STEP {scene.index + 1}</div>
      <h1 style={{fontSize: 64, margin: '18px 0 28px'}}>{scene.title}</h1>
      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24}}>
        <div style={{fontSize: 42, lineHeight: 1.25}}>{scene.body}</div>
        <div style={{display: 'grid', gap: 18}}>
          {(scene.keywords || []).map((k, i) => (
            <div key={k} style={{padding: 18, border: '2px solid #111', borderRadius: 8, transform: `translateX(${Math.max(0, 1 - (local - i * 8) / 18) * 50}px)`, background: i % 2 ? '#fff6e8' : '#e9f3ff', fontSize: 28}}>
              {i + 1}. {k}
            </div>
          ))}
        </div>
      </div>
    </div>
  </AbsoluteFill>
);

const BlueprintScene = ({scene, palette, local}) => (
  <AbsoluteFill style={{background: palette.bg, color: palette.ink}}>
    <svg width="1280" height="720" style={{position: 'absolute', inset: 0}}>
      <defs>
        <pattern id="grid" width="42" height="42" patternUnits="userSpaceOnUse">
          <path d="M 42 0 L 0 0 0 42" fill="none" stroke={palette.line} strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="1280" height="720" fill="url(#grid)" />
      {(scene.keywords || []).map((keyword, index) => {
        const x = 220 + index * 220;
        const y = 430 + Math.sin((local + index * 12) / 20) * 22;
        return (
          <g key={keyword}>
            <circle cx={x} cy={y} r="56" fill="none" stroke={palette.accent} strokeWidth="3" />
            <text x={x} y={y + 8} textAnchor="middle" fill={palette.ink} fontSize="24">{keyword}</text>
            {index > 0 ? <line x1={x - 164} y1={y} x2={x - 60} y2={y} stroke={palette.accent2} strokeWidth="3" /> : null}
          </g>
        );
      })}
    </svg>
    <div style={{position: 'absolute', left: 82, top: 94, width: 760}}>
      <div style={{fontSize: 22, color: palette.accent}}>BLUEPRINT</div>
      <h1 style={{fontSize: 68, margin: '16px 0', lineHeight: 1}}>{scene.title}</h1>
      <p style={{fontSize: 34, lineHeight: 1.35}}>{scene.body}</p>
    </div>
  </AbsoluteFill>
);

const MagazineScene = ({scene, palette, local}) => (
  <AbsoluteFill style={{background: '#11100e', color: '#f4eee2', padding: 72}}>
    <MediaBackdrop scene={scene} palette={palette} local={local} progress={clamp(local / Math.max(scene.duration, 1), 0, 1)} intensity={0.7} />
    <div style={{position: 'absolute', right: 92, top: 74, width: 390, height: 520, background: '#f4eee2', color: '#11100e', borderRadius: 8, padding: 34}}>
      <div style={{fontSize: 18}}>LIFESTYLE NOTES</div>
      <div style={{fontSize: 92, lineHeight: 0.9, marginTop: 130}}>{scene.keywords?.[0] || '日常'}</div>
    </div>
    <div style={{width: 650, marginTop: 74}}>
      <div style={{fontSize: 22, color: palette.accent}}>ISSUE 0{scene.index + 1}</div>
      <h1 style={{fontSize: 80, lineHeight: 0.98, margin: '22px 0'}}>{scene.title}</h1>
      <p style={{fontSize: 34, lineHeight: 1.45, color: '#e7d7bd'}}>{scene.body}</p>
    </div>
  </AbsoluteFill>
);

const DataScene = ({scene, palette, local}) => (
  <AbsoluteFill style={{background: palette.bg, color: palette.ink, padding: 82}}>
    <MediaBackdrop scene={scene} palette={palette} local={local} progress={clamp(local / Math.max(scene.duration, 1), 0, 1)} intensity={0.42} />
    <div style={{fontSize: 22, color: palette.accent}}>DATA VIEW</div>
    <h1 style={{fontSize: 66, margin: '16px 0 28px'}}>{scene.title}</h1>
    <div style={{display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 18}}>
      {(scene.keywords || []).slice(0, 4).map((keyword, index) => {
        const h = 130 + ((local * (index + 1)) % 180);
        return (
          <div key={keyword} style={{height: 360, display: 'flex', alignItems: 'end', border: `1px solid ${palette.line}`, padding: 16}}>
            <div style={{width: '100%'}}>
              <div style={{height: h, background: `linear-gradient(180deg, ${palette.accent2}, ${palette.accent})`, borderRadius: 8}} />
              <div style={{fontSize: 24, marginTop: 14}}>{keyword}</div>
            </div>
          </div>
        );
      })}
    </div>
    <p style={{fontSize: 30, marginTop: 26, color: palette.muted}}>{scene.body}</p>
  </AbsoluteFill>
);

const TimelineScene = ({scene, palette, local}) => (
  <AbsoluteFill style={{background: `linear-gradient(135deg, ${palette.bg}, ${palette.panel})`, color: palette.ink, padding: 82}}>
    <MediaBackdrop scene={scene} palette={palette} local={local} progress={clamp(local / Math.max(scene.duration, 1), 0, 1)} intensity={0.5} />
    <h1 style={{fontSize: 70, margin: '30px 0 70px'}}>{scene.title}</h1>
    <div style={{height: 4, background: palette.line, position: 'relative'}}>
      {(scene.keywords || []).slice(0, 4).map((keyword, index) => {
        const left = 8 + index * 28;
        return (
          <div key={keyword} style={{position: 'absolute', left: `${left}%`, top: -28, transform: `translateY(${Math.sin((local + index * 10) / 18) * 8}px)`}}>
            <div style={{width: 56, height: 56, borderRadius: 999, background: palette.accent, display: 'grid', placeItems: 'center', color: palette.bg, fontWeight: 900}}>{index + 1}</div>
            <div style={{fontSize: 26, marginTop: 22, width: 170}}>{keyword}</div>
          </div>
        );
      })}
    </div>
    <p style={{fontSize: 36, lineHeight: 1.35, marginTop: 150, width: 850}}>{scene.body}</p>
  </AbsoluteFill>
);

const sceneGroups = {
  commerce_hook: CommerceScene,
  compare_split: CommerceScene,
  benefit_stack: CommerceScene,
  use_case: CommerceScene,
  cta_burst: CommerceScene,
  question_board: TeachingScene,
  step_board: TeachingScene,
  diagram_flow: BlueprintScene,
  example_card: TeachingScene,
  summary_cards: TeachingScene,
  hud_map: BlueprintScene,
  signal_flow: BlueprintScene,
  data_nodes: BlueprintScene,
  magazine_cover: MagazineScene,
  photo_strip: MagazineScene,
  soft_caption: MagazineScene,
  detail_moment: MagazineScene,
  gentle_close: MagazineScene,
  soft_quote: MagazineScene,
  breathing_cards: MagazineScene,
  emotion_wave: MagazineScene,
  breaking_headline: BigType,
  timeline: TimelineScene,
  conflict_map: TimelineScene,
  data_report: DataScene,
  discussion_prompt: BigType,
  metric_wall: DataScene,
  trend_line: DataScene,
  insight_card: BigType,
  case_context: TimelineScene,
  decision_map: BlueprintScene,
  method_card: TeachingScene,
  editorial_title: BigType,
  quote_wall: BigType,
  contrast_cards: TimelineScene,
  punchline: BigType,
  hook_flash: BigType,
  creator_caption: BigType,
  experience_card: TimelineScene,
  big_subtitle: BigType,
  follow_prompt: BigType
};

const SceneRenderer = ({story, scene, palette, local, progress}) => {
  const Component = sceneGroups[scene.mode] || BigType;
  return <Component story={story} scene={scene} palette={palette} local={local} progress={progress} />;
};

export const MindVideo = ({
  script = '',
  style = 'dark_editorial',
  density = 1,
  scenes = [],
  audioScenes = [],
  bgmSrc = null,
  contentType = 'insight',
  pace = 'medium',
  tone = 'professional',
  targetPlatform = 'douyin',
  goal = ''
}) => {
  const frame = useCurrentFrame();
  const story = scriptToStory({script, style, density, scenes, audioScenes, bgmSrc, contentType, pace, tone, targetPlatform, goal});
  const {scene, local, progress} = getSceneTiming(story, frame);
  const palette = story.palette;

  return (
    <AbsoluteFill style={{
      background:
        `radial-gradient(circle at 18% 14%, ${palette.accent2}22 0, transparent 26%), ` +
        `radial-gradient(circle at 86% 18%, ${palette.accent}22 0, transparent 28%), ` +
        `linear-gradient(135deg, ${palette.bg}, #050506)`,
      color: palette.ink,
      fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      overflow: 'hidden'
    }}>
      <SceneAudio story={story} />
      <Particles palette={palette} count={story.style === 'clean_explainer' ? 0 : 34} />
      <SceneRenderer story={story} scene={scene} palette={palette} local={local} progress={progress} />
      <TransitionLayer scene={scene} palette={palette} local={local} />
      <FrameChrome story={story} scene={scene} palette={palette} progress={frame / Math.max(story.durationInFrames, 1)} />
    </AbsoluteFill>
  );
};
