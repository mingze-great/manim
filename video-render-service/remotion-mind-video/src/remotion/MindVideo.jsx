import React from 'react';
import {
  AbsoluteFill,
  Audio,
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
      return {
        scene,
        start: cursor,
        local: frame - cursor,
        progress: clamp((frame - cursor) / scene.duration, 0, 1)
      };
    }
    cursor += scene.duration;
  }
  const last = story.scenes[story.scenes.length - 1];
  return {scene: last, start: cursor - last.duration, local: last.duration, progress: 1};
};

const pointFor = (index, total, radius, phase = 0) => {
  const angle = (Math.PI * 2 * index) / Math.max(total, 1) - Math.PI / 2 + phase;
  return {
    x: 640 + Math.cos(angle) * radius,
    y: 360 + Math.sin(angle) * radius * 0.62
  };
};

const ParticleField = ({palette}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      {Array.from({length: 44}).map((_, index) => {
        const x = (index * 97) % 1280;
        const y = (index * 53) % 720;
        const drift = Math.sin((frame + index * 11) / 40) * 18;
        const opacity = 0.16 + ((index % 5) * 0.035);
        return (
          <div
            key={index}
            style={{
              position: 'absolute',
              left: x + drift,
              top: y + Math.cos((frame + index * 7) / 46) * 16,
              width: 2 + (index % 3),
              height: 2 + (index % 3),
              borderRadius: 99,
              background: index % 4 === 0 ? palette.accent2 : palette.accent,
              boxShadow: `0 0 ${16 + (index % 6) * 4}px currentColor`,
              color: index % 4 === 0 ? palette.accent2 : palette.accent,
              opacity
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

const Network = ({story, activeIndex, palette}) => {
  const frame = useCurrentFrame();
  const shownScenes = story.scenes.slice(0, activeIndex + 1);
  const phase = Math.sin(frame / 120) * 0.08;
  const center = {x: 640, y: 340};

  return (
    <svg width="1280" height="720" style={{position: 'absolute', inset: 0}}>
      <defs>
        <filter id="glow">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={palette.accent} />
          <stop offset="48%" stopColor={palette.accent2} />
          <stop offset="100%" stopColor={palette.accent3} />
        </linearGradient>
      </defs>
      {shownScenes.map((scene, index) => {
        const p = pointFor(index, story.scenes.length, 210 + (index % 2) * 42, phase);
        const appear = spring({
          frame: frame - index * 18,
          fps: 30,
          config: {damping: 16, stiffness: 90}
        });
        const dash = interpolate(frame % 90, [0, 90], [0, -36]);
        return (
          <g key={scene.id} opacity={clamp(appear, 0, 1)}>
            <path
              d={`M ${center.x} ${center.y} C ${(center.x + p.x) / 2} ${center.y - 120}, ${(center.x + p.x) / 2} ${p.y + 80}, ${p.x} ${p.y}`}
              stroke="url(#lineGradient)"
              strokeWidth={index === activeIndex ? 4 : 2}
              strokeLinecap="round"
              strokeDasharray="10 18"
              strokeDashoffset={dash}
              fill="none"
              opacity={index === activeIndex ? 0.88 : 0.34}
              filter="url(#glow)"
            />
            <circle
              cx={p.x}
              cy={p.y}
              r={index === activeIndex ? 15 : 10}
              fill={index === activeIndex ? palette.accent3 : palette.accent}
              opacity={0.95}
              filter="url(#glow)"
            />
            <circle
              cx={p.x}
              cy={p.y}
              r={index === activeIndex ? 38 + Math.sin(frame / 9) * 4 : 24}
              fill="none"
              stroke={index === activeIndex ? palette.accent3 : palette.accent}
              strokeWidth="1.5"
              opacity={index === activeIndex ? 0.4 : 0.18}
            />
          </g>
        );
      })}
    </svg>
  );
};

const KeywordRail = ({scene, palette, local}) => (
  <div style={{display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 24}}>
    {scene.keywords.map((keyword, index) => {
      const lift = spring({
        frame: local - index * 8,
        fps: 30,
        config: {damping: 18, stiffness: 120}
      });
      return (
        <span
          key={keyword}
          style={{
            transform: `translateY(${(1 - lift) * 16}px)`,
            opacity: clamp(lift, 0, 1),
            color: index % 2 ? palette.accent2 : palette.accent,
            border: `1px solid ${index % 2 ? palette.accent2 : palette.accent}`,
            boxShadow: `0 0 24px ${index % 2 ? palette.accent2 : palette.accent}33`,
            padding: '8px 12px',
            borderRadius: 999,
            fontSize: 19,
            lineHeight: 1
          }}
        >
          {keyword}
        </span>
      );
    })}
  </div>
);

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
            <Audio
              src={staticFile(scene.audioSrc)}
              startFrom={0}
              endAt={scene.duration}
              volume={1}
            />
          </Sequence>
        );
      })}
      {story.bgmSrc ? <Audio src={staticFile(story.bgmSrc)} volume={0.13} /> : null}
    </>
  );
};

export const MindVideo = ({script = '', style = 'aurora', density = 1, audioScenes = [], bgmSrc = null}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const story = scriptToStory({script, style, density, audioScenes, bgmSrc});
  const {scene, local, progress} = getSceneTiming(story, frame);
  const palette = story.palette;
  const titleIn = spring({frame: local, fps, config: {damping: 17, stiffness: 85}});
  const activeIndex = scene.index;

  return (
    <AbsoluteFill
      style={{
        background:
          `radial-gradient(circle at 20% 18%, ${palette.accent2}33 0, transparent 28%), ` +
          `radial-gradient(circle at 82% 24%, ${palette.accent}2b 0, transparent 30%), ` +
          `linear-gradient(135deg, ${palette.bg}, #10131b 58%, #050506)`,
        color: palette.ink,
        fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
      }}
    >
      <SceneAudio story={story} />
      <ParticleField palette={palette} />
      <Network story={story} activeIndex={activeIndex} palette={palette} />
      <div
        style={{
          position: 'absolute',
          inset: 42,
          border: `1px solid ${palette.line}`,
          borderRadius: 28,
          boxShadow: `inset 0 0 70px ${palette.accent}10`,
          pointerEvents: 'none'
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 86,
          top: 70,
          right: 86,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          color: palette.muted,
          fontSize: 19,
          letterSpacing: 0
        }}
      >
        <span>MINDFILM STUDIO</span>
        <span>{String(activeIndex + 1).padStart(2, '0')} / {String(story.scenes.length).padStart(2, '0')}</span>
      </div>
      <div
        style={{
          position: 'absolute',
          left: 86,
          bottom: 70,
          width: `${interpolate(frame, [0, story.durationInFrames], [0, 1108], {extrapolateRight: 'clamp'})}px`,
          height: 3,
          background: `linear-gradient(90deg, ${palette.accent}, ${palette.accent2}, ${palette.accent3})`,
          boxShadow: `0 0 24px ${palette.accent}`,
          borderRadius: 99
        }}
      />
      <main
        style={{
          position: 'absolute',
          left: 92,
          top: 150,
          width: 520,
          transform: `translateY(${(1 - titleIn) * 26}px)`,
          opacity: clamp(titleIn, 0, 1)
        }}
      >
        <div
          style={{
            color: palette.accent,
            fontSize: 22,
            marginBottom: 18,
            textTransform: 'uppercase'
          }}
        >
          {scene.mode}
        </div>
        <h1
          style={{
            margin: 0,
            fontSize: scene.title.length > 8 ? 56 : 68,
            lineHeight: 0.96,
            letterSpacing: 0,
            textShadow: `0 0 42px ${palette.accent2}44`
          }}
        >
          {scene.title}
        </h1>
        <p
          style={{
            margin: '28px 0 0',
            color: palette.ink,
            fontSize: 30,
            lineHeight: 1.35,
            maxWidth: 600,
            textShadow: '0 8px 24px rgba(0,0,0,0.48)'
          }}
        >
          {scene.body}
        </p>
        <KeywordRail scene={scene} palette={palette} local={local} />
      </main>
      <div
        style={{
          position: 'absolute',
          right: 112,
          top: 184,
          width: 280,
          height: 280,
          borderRadius: '50%',
          display: 'grid',
          placeItems: 'center',
          color: palette.bg,
          background: `conic-gradient(from ${progress * 360}deg, ${palette.accent}, ${palette.accent2}, ${palette.accent3}, ${palette.accent})`,
          boxShadow: `0 0 80px ${palette.accent2}55`,
          transform: `rotate(${Math.sin(frame / 80) * 4}deg)`
        }}
      >
        <div
          style={{
            width: 226,
            height: 226,
            borderRadius: '50%',
            background: `${palette.bg}ee`,
            color: palette.ink,
            display: 'grid',
            placeItems: 'center',
            textAlign: 'center',
            padding: 26,
            fontSize: 26,
            lineHeight: 1.16
          }}
        >
          {scene.keywords[0]}
        </div>
      </div>
    </AbsoluteFill>
  );
};
