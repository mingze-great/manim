import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
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

const SafeVisualImage = ({src, style}) => {
  if (!src) return null;
  if (/^https?:\/\//i.test(src)) {
    return <img src={src} alt="" style={style} crossOrigin="anonymous" referrerPolicy="no-referrer" />;
  }
  const relativeSrc = src.startsWith('/') ? src.slice(1) : src;
  return <Img src={staticFile(relativeSrc)} style={style} />;
};

const EnergyField = ({scene, palette, local, progress}) => {
  const pattern = scene.energyPattern || 'orbit_rings';
  const opacity = scene.intensity === 'medium' ? 0.42 : 0.68;
  if (pattern === 'shockwave' || pattern === 'prism_rays') {
    return (
      <AbsoluteFill style={{pointerEvents: 'none', opacity, mixBlendMode: 'screen'}}>
        {[0, 1, 2].map((index) => (
          <div key={index} style={{
            position: 'absolute',
            left: 640 - 170 - index * 44,
            top: 360 - 170 - index * 44,
            width: 340 + index * 88,
            height: 340 + index * 88,
            borderRadius: '50%',
            border: `2px solid ${index % 2 ? palette.accent2 : palette.accent}`,
            transform: `scale(${0.55 + progress * 1.25 + index * 0.08}) rotate(${local * (index + 1)}deg)`,
            opacity: 0.58 - index * 0.13
          }} />
        ))}
        <div style={{position: 'absolute', inset: -120, background: `conic-gradient(from ${local * 10}deg, transparent, ${palette.accent}66, transparent, ${palette.accent2}55, transparent)`, transform: `rotate(${local * 1.8}deg)`}} />
      </AbsoluteFill>
    );
  }
  if (pattern === 'glitch_slices') {
    return (
      <AbsoluteFill style={{pointerEvents: 'none', opacity, mixBlendMode: 'screen'}}>
        {Array.from({length: 7}).map((_, index) => (
          <div key={index} style={{
            position: 'absolute',
            left: Math.sin((local + index * 17) / 4) * 42,
            top: 80 + index * 78,
            width: '110%',
            height: 14 + index,
            background: index % 2 ? palette.accent2 : palette.accent,
            transform: `skewX(-18deg) translateX(${Math.sin(local / 5 + index) * 28}px)`
          }} />
        ))}
      </AbsoluteFill>
    );
  }
  if (pattern === 'data_scan' || pattern === 'ticker_bars' || pattern === 'metric_pulse') {
    return (
      <AbsoluteFill style={{pointerEvents: 'none', opacity: 0.5}}>
        {Array.from({length: 12}).map((_, index) => (
          <div key={index} style={{
            position: 'absolute',
            left: 70 + index * 96,
            bottom: 76,
            width: 26,
            height: 80 + ((local * (index + 2)) % 260),
            borderRadius: 6,
            background: `linear-gradient(180deg, ${palette.accent2}, ${palette.accent})`,
            boxShadow: `0 0 24px ${palette.accent}66`
          }} />
        ))}
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity}}>
      {Array.from({length: 10}).map((_, index) => {
        const angle = (index / 10) * Math.PI * 2 + local / 28;
        const radius = 185 + Math.sin((local + index * 9) / 18) * 46;
        return <div key={index} style={{position: 'absolute', left: 640 + Math.cos(angle) * radius, top: 360 + Math.sin(angle) * radius, width: 8 + index % 3 * 6, height: 8 + index % 3 * 6, borderRadius: 99, background: index % 2 ? palette.accent2 : palette.accent, boxShadow: `0 0 28px ${index % 2 ? palette.accent2 : palette.accent}`}} />;
      })}
    </AbsoluteFill>
  );
};

const MediaOrb = ({scene, palette, local, progress, size = 360}) => {
  const src = scene.media?.src;
  const rotate = local * 0.35;
  return (
    <div style={{
      position: 'relative',
      width: size,
      height: size,
      borderRadius: scene.layoutVariant === 'diagonal_split' ? 28 : '50%',
      overflow: 'hidden',
      boxShadow: `0 0 90px ${palette.accent}55`,
      border: `2px solid ${palette.accent2}88`,
      transform: `scale(${0.92 + progress * 0.12}) rotate(${scene.layoutVariant === 'diagonal_split' ? -4 : 0}deg)`
    }}>
      {src ? (
        <SafeVisualImage src={src} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${1.08 + progress * 0.12}) translate(${Math.sin(local / 24) * 14}px, ${Math.cos(local / 30) * 10}px)`, filter: 'saturate(1.08) contrast(1.08)'}} />
      ) : (
        <div style={{width: '100%', height: '100%', background: `radial-gradient(circle at 30% 28%, ${palette.accent2}, transparent 36%), linear-gradient(135deg, ${palette.panel}, ${palette.bg})`}} />
      )}
      <div style={{position: 'absolute', inset: 0, background: `conic-gradient(from ${rotate}deg, transparent, ${palette.accent}55, transparent, ${palette.accent2}44, transparent)`, mixBlendMode: 'screen'}} />
    </div>
  );
};

const KineticTitle = ({scene, palette, local, align = 'left', maxWidth = 820}) => {
  const {fps} = useVideoConfig();
  const enter = spring({frame: local, fps, config: {damping: 14, stiffness: 150}});
  const isOpening = scene.effect === 'opening_impact';
  const titleText = isOpening
    ? String(scene.openingTitle || scene.title || scene.keywords?.slice(0, 2).join(' / ') || scene.body || '').slice(0, 20)
    : String(scene.body || '').slice(0, 18);
  const chars = titleText.split('');
  const fontSize = isOpening ? (titleText.length > 12 ? 92 : 118) : (scene.body.length > 18 ? 72 : 96);
  return (
    <div style={{maxWidth, textAlign: align, transform: `translateY(${(1 - enter) * 40}px)`, opacity: enter}}>
      <div style={{fontSize: 24, color: palette.accent, marginBottom: 18, letterSpacing: 0}}>{isOpening ? 'OPENING THEME' : scene.title}</div>
      <h1 style={{fontSize, lineHeight: 0.94, margin: 0, color: palette.ink}}>
        {isOpening ? (
          <span style={{display: 'inline-block', textShadow: `0 0 36px ${palette.accent}88, 0 0 90px ${palette.accent2}55`, transform: `scale(${0.96 + enter * 0.04})`}}>{titleText}</span>
        ) : chars.map((char, index) => (
            <span key={`${char}-${index}`} style={{display: 'inline-block', transform: `translateY(${Math.sin((local + index * 3) / 8) * 4}px)`, color: index % 5 === 0 ? palette.accent2 : index % 3 === 0 ? palette.accent : palette.ink}}>
              {char}
            </span>
          ))}
      </h1>
      {isOpening && <div style={{marginTop: 22, fontSize: 34, color: palette.muted, lineHeight: 1.2}}>{scene.body}</div>}
      <div style={{marginTop: 28, display: 'flex', justifyContent: align === 'center' ? 'center' : 'flex-start'}}><KeywordRail scene={scene} palette={palette} local={local} /></div>
    </div>
  );
};

const MotionTexture = ({scene, palette, local, progress}) => {
  const scan = interpolate(local, [0, 34], [-18, 118], {extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)});
  const pulse = 0.45 + Math.sin(local / 9) * 0.18;
  const type = scene.transition || scene.mode;

  if (scene.effect === 'opening_impact') {
    const burst = interpolate(local, [0, 8, 30], [1, 0.72, 0], {extrapolateRight: 'clamp'});
    const flash = interpolate(local, [0, 3, 12], [0.9, 0.35, 0], {extrapolateRight: 'clamp'});
    return (
      <AbsoluteFill style={{pointerEvents: 'none', opacity: burst, mixBlendMode: 'screen'}}>
        <AbsoluteFill style={{background: '#fff', opacity: flash}} />
        <div style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          width: 980,
          height: 980,
          marginLeft: -490,
          marginTop: -490,
          borderRadius: '50%',
          background: `radial-gradient(circle, #fff 0%, ${palette.accent2}22 12%, transparent 32%), conic-gradient(from ${local * 18}deg, ${palette.accent}, transparent 18%, ${palette.accent2}, transparent 54%, #fff, transparent 82%)`,
          transform: `scale(${0.22 + progress * 1.7}) rotate(${local * 2.4}deg)`
        }} />
        {[0, 1, 2, 3, 4, 5].map((index) => (
          <div key={index} style={{
            position: 'absolute',
            left: `${-8 + index * 19}%`,
            top: `${10 + index * 11}%`,
            width: 520,
            height: 22,
            background: `linear-gradient(90deg, transparent, ${index % 2 ? palette.accent2 : palette.accent}, transparent)`,
            transform: `translateX(${local * (26 + index * 7)}px) skewX(-20deg)`,
            boxShadow: `0 0 34px ${index % 2 ? palette.accent2 : palette.accent}`
          }} />
        ))}
      </AbsoluteFill>
    );
  }

  if (type === 'scan' || scene.mode?.includes('data')) {
    return (
      <AbsoluteFill style={{opacity: 0.58, pointerEvents: 'none'}}>
        <div style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `linear-gradient(${palette.line} 1px, transparent 1px), linear-gradient(90deg, ${palette.line} 1px, transparent 1px)`,
          backgroundSize: '44px 44px',
          transform: `translateY(${(local % 44) - 44}px)`
        }} />
        <div style={{position: 'absolute', left: 0, right: 0, top: `${scan}%`, height: 96, background: `linear-gradient(180deg, transparent, ${palette.accent2}44, transparent)`, mixBlendMode: 'screen'}} />
        {Array.from({length: 6}).map((_, index) => (
          <div key={index} style={{
            position: 'absolute',
            right: 82 + index * 54,
            bottom: 72,
            width: 28,
            height: 70 + ((local * (index + 2)) % 170),
            borderRadius: 6,
            background: `linear-gradient(180deg, ${palette.accent2}, ${palette.accent})`,
            opacity: 0.45
          }} />
        ))}
      </AbsoluteFill>
    );
  }

  if (type === 'split') {
    return (
      <AbsoluteFill style={{pointerEvents: 'none', opacity: 0.5}}>
        {[0, 1, 2].map((index) => (
          <div key={index} style={{
            position: 'absolute',
            top: 90 + index * 132,
            left: interpolate(local - index * 5, [0, 24], [-360, 80 + index * 70], {extrapolateRight: 'clamp'}),
            width: 520,
            height: 88,
            transform: 'skewX(-18deg)',
            background: `linear-gradient(90deg, transparent, ${index % 2 ? palette.accent2 : palette.accent}66, transparent)`
          }} />
        ))}
      </AbsoluteFill>
    );
  }

  if (type === 'glitch') {
    return (
      <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'screen'}}>
        {[0, 1, 2, 3, 4].map((index) => {
          const y = 86 + index * 104 + Math.sin((local + index * 11) / 5) * 10;
          const x = Math.sin((local + index * 17) / 3) * 28;
          return <div key={index} style={{position: 'absolute', left: x, top: y, width: '100%', height: 18 + index * 2, background: index % 2 ? palette.accent2 : palette.accent, opacity: 0.16}} />;
        })}
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: 0.5}}>
      <div style={{
        position: 'absolute',
        right: 86,
        top: 116,
        width: 230,
        height: 230,
        borderRadius: '50%',
        border: `2px solid ${palette.accent}`,
        transform: `rotate(${progress * 180}deg) scale(${0.9 + pulse * 0.15})`
      }} />
      <div style={{
        position: 'absolute',
        left: 78,
        bottom: 82,
        width: 360,
        height: 4,
        background: `linear-gradient(90deg, ${palette.accent}, ${palette.accent2}, transparent)`,
        boxShadow: `0 0 28px ${palette.accent}`,
        transform: `scaleX(${0.45 + progress * 0.9})`,
        transformOrigin: 'left center'
      }} />
    </AbsoluteFill>
  );
};

const MediaBackdrop = ({scene, palette, local, progress, intensity = 1}) => {
  const src = scene.media?.src;
  const zoom = 1.04 + progress * 0.08 * intensity;
  const drift = Math.sin(local / 34) * 18 * intensity;
  if (!src) {
    const angle = scene.mode?.includes('timeline') ? 90 : scene.mode?.includes('data') ? 0 : 135;
    return (
      <AbsoluteFill>
        <AbsoluteFill style={{
          background:
            `linear-gradient(${angle}deg, ${palette.bg}, ${palette.panel}), ` +
            `radial-gradient(circle at ${28 + progress * 40}% 24%, ${palette.accent}33 0, transparent 28%)`
        }} />
        <svg width="1280" height="720" style={{position: 'absolute', inset: 0, opacity: 0.32}}>
          {Array.from({length: 9}).map((_, index) => {
            const x = 120 + index * 138 + Math.sin((local + index * 12) / 20) * 22;
            const y = 110 + ((index * 97) % 470);
            return <rect key={index} x={x} y={y} width="150" height="38" rx="19" fill="none" stroke={index % 2 ? palette.accent2 : palette.accent} strokeWidth="2" />;
          })}
        </svg>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill>
      <SafeVisualImage
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
      <div style={{
        position: 'absolute',
        inset: 0,
        background: `linear-gradient(${110 + progress * 30}deg, transparent 0%, ${palette.accent}22 42%, transparent 58%, ${palette.accent2}18 100%)`,
        mixBlendMode: 'screen',
        transform: `translateX(${Math.sin(local / 28) * 24}px)`
      }} />
    </AbsoluteFill>
  );
};

const TransitionLayer = ({scene, palette, local}) => {
  const {fps} = useVideoConfig();
  const enter = spring({frame: local, fps, config: {damping: 20, stiffness: 145}});
  const reveal = interpolate(local, [0, 20], [0, 1], {extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)});
  const wipe = interpolate(local, [0, 18], [-100, 110], {extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)});
  if (scene.transition === 'flash') {
    const opacity = interpolate(local, [0, 5, 16], [0.9, 0.24, 0], {extrapolateRight: 'clamp'});
    return (
      <AbsoluteFill style={{opacity, mixBlendMode: 'screen', pointerEvents: 'none'}}>
        <AbsoluteFill style={{background: palette.accent2}} />
        <div style={{position: 'absolute', inset: 0, background: `linear-gradient(110deg, transparent 0%, ${palette.accent} 44%, #fff 50%, transparent 58%)`, transform: `translateX(${(reveal - 0.5) * 900}px)`}} />
      </AbsoluteFill>
    );
  }
  if (scene.transition === 'wipe') {
    return <div style={{position: 'absolute', top: 0, bottom: 0, left: `${wipe}%`, width: 260, background: `linear-gradient(90deg, transparent, ${palette.accent}, ${palette.accent2}, transparent)`, transform: 'skewX(-12deg)', opacity: 0.82, mixBlendMode: 'screen'}} />;
  }
  if (scene.transition === 'glitch') {
    const opacity = interpolate(local, [0, 6, 18], [0.85, 0.5, 0], {extrapolateRight: 'clamp'});
    return (
      <AbsoluteFill style={{opacity, pointerEvents: 'none', mixBlendMode: 'screen'}}>
        {[0, 1, 2, 3].map((index) => (
          <div key={index} style={{position: 'absolute', left: Math.sin(local + index) * 34, top: index * 160, width: '110%', height: 54, background: index % 2 ? palette.accent2 : palette.accent}} />
        ))}
      </AbsoluteFill>
    );
  }
  if (scene.transition === 'split') {
    return (
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        <div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: `${(1 - reveal) * 52}%`, background: palette.bg}} />
        <div style={{position: 'absolute', right: 0, top: 0, bottom: 0, width: `${(1 - reveal) * 52}%`, background: palette.bg}} />
        <div style={{position: 'absolute', left: `${50 + reveal * 58}%`, top: 0, bottom: 0, width: 110, background: `linear-gradient(90deg, transparent, ${palette.accent2}, transparent)`, transform: 'skewX(-10deg)', opacity: 0.6}} />
      </AbsoluteFill>
    );
  }
  if (scene.transition === 'scan') {
    const opacity = interpolate(local, [0, 14, 28], [0.62, 0.3, 0], {extrapolateRight: 'clamp'});
    return <AbsoluteFill style={{opacity, background: `repeating-linear-gradient(0deg, ${palette.accent2}00 0px, ${palette.accent2}00 8px, ${palette.accent2}88 10px)`, mixBlendMode: 'screen', pointerEvents: 'none'}} />;
  }
  if (scene.transition === 'zoom') {
    return <AbsoluteFill style={{opacity: 1 - enter, background: palette.bg, transform: `scale(${0.84 + enter * 0.16})`, pointerEvents: 'none'}} />;
  }
  if (scene.transition === 'prism') {
    return (
      <AbsoluteFill style={{opacity: 1 - reveal, pointerEvents: 'none', mixBlendMode: 'screen'}}>
        <div style={{position: 'absolute', inset: -180, background: `conic-gradient(from ${local * 8}deg, ${palette.accent}, transparent, ${palette.accent2}, transparent, ${palette.accent3})`, transform: `scale(${1.1 + reveal * 0.25}) rotate(${local * 2}deg)`}} />
      </AbsoluteFill>
    );
  }
  return <AbsoluteFill style={{opacity: 1 - enter, background: palette.bg, transform: `translateX(${(1 - enter) * -80}px) scale(${1 + (1 - enter) * 0.08})`, pointerEvents: 'none'}} />;
};

const BigType = ({scene, palette, local, progress}) => {
  const {fps} = useVideoConfig();
  const enter = spring({frame: local, fps, config: {damping: 16, stiffness: 90}});
  const variant = scene.layoutVariant || 'center_burst';
  if (variant === 'center_burst' || variant === 'kinetic_focus' || variant === 'diagonal_impact') {
    return (
      <AbsoluteFill style={{padding: 78, justifyContent: 'center', alignItems: 'center'}}>
        <MediaBackdrop scene={scene} palette={palette} local={local} progress={progress} intensity={1.05} />
        <EnergyField scene={scene} palette={palette} local={local} progress={progress} />
        <div style={{position: 'absolute', inset: 0, background: `radial-gradient(circle at 50% 50%, transparent 0, ${palette.bg}aa 62%)`}} />
        <KineticTitle scene={scene} palette={palette} local={local} align="center" maxWidth={980} />
      </AbsoluteFill>
    );
  }
  if (variant === 'media_hero' || variant === 'text_left_media_right') {
    return (
      <AbsoluteFill style={{padding: 76, display: 'grid', gridTemplateColumns: '0.95fr 1.05fr', gap: 48, alignItems: 'center'}}>
        <MediaBackdrop scene={scene} palette={palette} local={local} progress={progress} intensity={0.85} />
        <KineticTitle scene={scene} palette={palette} local={local} />
        <div style={{display: 'grid', placeItems: 'center'}}>
          <MediaOrb scene={scene} palette={palette} local={local} progress={progress} size={430} />
        </div>
        <EnergyField scene={scene} palette={palette} local={local} progress={progress} />
      </AbsoluteFill>
    );
  }
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
  const variant = scene.layoutVariant || 'media_product';
  if (variant === 'center_burst' || variant === 'floating_tags') {
    return (
      <AbsoluteFill style={{padding: 72, justifyContent: 'center', alignItems: 'center'}}>
        <MediaBackdrop scene={scene} palette={palette} local={local} progress={progress} intensity={1.1} />
        <EnergyField scene={scene} palette={palette} local={local} progress={progress} />
        <KineticTitle scene={scene} palette={palette} local={local} align="center" maxWidth={940} />
        <div style={{position: 'absolute', left: 82, right: 82, bottom: 78, display: 'flex', justifyContent: 'center', gap: 16}}>
          {(scene.keywords || []).slice(0, 4).map((keyword, index) => (
            <div key={keyword} style={{padding: '12px 18px', borderRadius: 999, border: `1px solid ${index % 2 ? palette.accent2 : palette.accent}`, color: index % 2 ? palette.accent2 : palette.accent, background: `${palette.bg}aa`, fontSize: 24, transform: `translateY(${Math.sin((local + index * 10) / 12) * 8}px)`}}>{keyword}</div>
          ))}
        </div>
      </AbsoluteFill>
    );
  }
  if (variant === 'media_product' || variant === 'text_left_media_right') {
    return (
      <AbsoluteFill style={{padding: 78, display: 'grid', gridTemplateColumns: '0.9fr 1.1fr', gap: 44, alignItems: 'center'}}>
        <MediaBackdrop scene={scene} palette={palette} local={local} progress={progress} />
        <div>
          <KineticTitle scene={scene} palette={palette} local={local} maxWidth={680} />
          <div style={{marginTop: 28, fontSize: 28, color: palette.muted}}>{scene.cta || '立即行动'}</div>
        </div>
        <div style={{display: 'grid', placeItems: 'center'}}>
          <MediaOrb scene={scene} palette={palette} local={local} progress={progress} size={450} />
        </div>
        <EnergyField scene={scene} palette={palette} local={local} progress={progress} />
      </AbsoluteFill>
    );
  }
  if (variant === 'diagonal_split') {
    return (
      <AbsoluteFill style={{overflow: 'hidden'}}>
        <MediaBackdrop scene={scene} palette={palette} local={local} progress={progress} />
        <div style={{position: 'absolute', inset: '-12% 46% -12% -12%', background: `${palette.bg}ee`, transform: 'skewX(-13deg)', borderRight: `3px solid ${palette.accent}`}} />
        <div style={{position: 'absolute', left: 82, top: 130, width: 610}}>
          <KineticTitle scene={scene} palette={palette} local={local} maxWidth={610} />
        </div>
        <div style={{position: 'absolute', right: 92, top: 122}}>
          <MediaOrb scene={scene} palette={palette} local={local} progress={progress} size={390} />
        </div>
        <EnergyField scene={scene} palette={palette} local={local} progress={progress} />
      </AbsoluteFill>
    );
  }
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

const TeachingScene = ({scene, palette, local}) => {
  const progress = clamp(local / Math.max(scene.duration, 1), 0, 1);
  const paper = {...palette, bg: '#f6f3ea', panel: '#fff', ink: '#111', accent: '#ff6b2c', accent2: '#2f80ed'};
  if (scene.layoutVariant === 'center_orbit' || scene.layoutVariant === 'diagram_stage') {
    return (
      <AbsoluteFill style={{background: '#f6f3ea', color: '#111', padding: 72, alignItems: 'center', justifyContent: 'center'}}>
        <MediaBackdrop scene={scene} palette={paper} local={local} progress={progress} intensity={0.28} />
        <EnergyField scene={scene} palette={paper} local={local} progress={progress} />
        <KineticTitle scene={scene} palette={paper} local={local} align="center" maxWidth={820} />
        {(scene.keywords || []).slice(0, 4).map((k, i) => {
          const angle = (i / 4) * Math.PI * 2 + local / 42;
          return <div key={k} style={{position: 'absolute', left: 640 + Math.cos(angle) * 390 - 78, top: 360 + Math.sin(angle) * 210 - 28, width: 156, padding: 14, textAlign: 'center', background: i % 2 ? '#fff6e8' : '#e9f3ff', border: '2px solid #111', borderRadius: 8, fontSize: 24}}>{k}</div>;
        })}
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{background: '#f6f3ea', color: '#111', padding: 82}}>
      <MediaBackdrop scene={scene} palette={paper} local={local} progress={progress} intensity={0.35} />
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
};

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

const EvidenceScene = ({scene, palette, local}) => {
  const progress = clamp(local / Math.max(scene.duration, 1), 0, 1);
  const mediaSrc = scene.media?.src;
  return (
    <AbsoluteFill style={{background: palette.bg, color: palette.ink, padding: 72}}>
      <MediaBackdrop scene={scene} palette={palette} local={local} progress={progress} intensity={0.24} />
      <div style={{position: 'absolute', inset: 48, border: `1px solid ${palette.line}`, borderRadius: 28}} />
      <div style={{position: 'relative', zIndex: 1, display: 'grid', gridTemplateColumns: '0.92fr 1.08fr', gap: 40, alignItems: 'center', height: '100%'}}>
        <div style={{maxWidth: 500}}>
          <div style={{fontSize: 22, color: palette.accent, letterSpacing: 0}}>EVIDENCE / {String(scene.index + 1).padStart(2, '0')}</div>
          <h1 style={{fontSize: 66, lineHeight: 1.02, margin: '18px 0 20px', color: palette.ink}}>{scene.title || scene.openingTitle || scene.keywords?.[0] || '证据卡'}</h1>
          <p style={{fontSize: 30, lineHeight: 1.42, margin: 0, color: palette.muted}}>{scene.body}</p>
          <div style={{marginTop: 24}}>
            <KeywordRail scene={scene} palette={palette} local={local} vertical />
          </div>
          <div style={{marginTop: 28, fontSize: 22, color: palette.accent2}}>{scene.cta || '先把问题看清，再谈解决方案'}</div>
        </div>
        <div style={{display: 'grid', placeItems: 'center'}}>
          <div style={{
            width: 360,
            padding: 12,
            borderRadius: 38,
            background: 'rgba(0, 0, 0, 0.38)',
            boxShadow: '0 28px 90px rgba(0, 0, 0, 0.42)',
            border: `1px solid ${palette.line}`,
            transform: `translateY(${Math.sin(local / 16) * 10}px) rotate(-2deg)`
          }}>
            <div style={{
              borderRadius: 30,
              overflow: 'hidden',
              background: '#0b0d12',
              border: `1px solid ${palette.line}`,
              aspectRatio: '9 / 16'
            }}>
              {mediaSrc ? (
                <SafeVisualImage
                  src={mediaSrc}
                  style={{width: '100%', height: '100%', objectFit: 'cover', display: 'block', filter: 'saturate(0.96) contrast(1.04)'}}
                />
              ) : null}
            </div>
          </div>
        </div>
      </div>
      <EnergyField scene={scene} palette={palette} local={local} progress={progress} />
    </AbsoluteFill>
  );
};

const DataScene = ({scene, palette, local}) => {
  const progress = clamp(local / Math.max(scene.duration, 1), 0, 1);
  if (scene.layoutVariant === 'center_orbit' || scene.layoutVariant === 'diagonal_split') {
    return (
      <AbsoluteFill style={{background: palette.bg, color: palette.ink, padding: 78, justifyContent: 'center'}}>
        <MediaBackdrop scene={scene} palette={palette} local={local} progress={progress} intensity={0.5} />
        <EnergyField scene={scene} palette={palette} local={local} progress={progress} />
        <KineticTitle scene={scene} palette={palette} local={local} maxWidth={760} />
        <div style={{position: 'absolute', right: 76, top: 110, width: 380, height: 480, display: 'grid', gap: 12}}>
          {(scene.keywords || []).slice(0, 4).map((keyword, index) => (
            <div key={keyword} style={{border: `1px solid ${palette.line}`, background: `${palette.panel}cc`, padding: 18, fontSize: 28, color: index % 2 ? palette.accent2 : palette.accent, transform: `translateX(${Math.sin((local + index * 9) / 16) * 18}px)`}}>{keyword}</div>
          ))}
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{background: palette.bg, color: palette.ink, padding: 82}}>
      <MediaBackdrop scene={scene} palette={palette} local={local} progress={progress} intensity={0.42} />
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
};

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
  evidence_card: EvidenceScene,
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
  const {fps} = useVideoConfig();
  const enter = spring({frame: local, fps, config: {damping: 24, stiffness: 120}});
  const exit = interpolate(local, [Math.max(0, scene.duration - 16), scene.duration], [1, 0.9], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp'
  });
  const camera = scene.camera || 'cinematic_push';
  const transforms = {
    impact_zoom: `scale(${1.18 - enter * 0.15 + progress * 0.035}) rotate(${(1 - enter) * -2.2}deg)`,
    snap_zoom: `scale(${1.08 - enter * 0.06}) rotate(${(1 - enter) * -1.4}deg)`,
    scan: `translateY(${Math.sin(local / 18) * 8}px) scale(1.015)`,
    slow_pan: `scale(1.035) translate(${Math.sin(local / 52) * 18}px, ${Math.cos(local / 60) * 10}px)`,
    cinematic_push: `scale(${1.03 + progress * 0.035}) translateY(${(1 - enter) * 22}px)`
  };
  return (
    <AbsoluteFill style={{
      transform: transforms[camera] || transforms.cinematic_push,
      opacity: exit,
      filter: camera === 'snap_zoom' || camera === 'impact_zoom' ? `contrast(${1.02 + (1 - enter) * 0.18}) saturate(${1.02 + (1 - enter) * 0.16})` : undefined
    }}>
      <Component story={story} scene={scene} palette={palette} local={local} progress={progress} />
      <MotionTexture scene={scene} palette={palette} local={local} progress={progress} />
    </AbsoluteFill>
  );
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
