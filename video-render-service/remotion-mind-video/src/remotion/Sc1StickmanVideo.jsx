import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig
} from 'remotion';

const FPS = 30;
const WIDTH = 1920;
const HEIGHT = 1080;
const FLOOR_Y = 835;
const FONT = '"Noto Sans CJK SC", "Source Han Sans SC", "PingFang SC", "Microsoft YaHei", Arial, sans-serif';

const colors = ['#c51cff', '#75421e', '#e02525', '#2458e6', '#f3d21b', '#21c928', '#111111', '#8a6b45'];

const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
const clean = (value) => String(value || '').replace(/\s+/g, ' ').trim();

const splitLines = (value, max = 20, limit = 2) => {
  const text = clean(value).replace(/\s+/g, '');
  if (!text) return [];
  const lines = [];
  for (let cursor = 0; cursor < text.length && lines.length < limit; cursor += max) {
    lines.push(text.slice(cursor, lines.length === limit - 1 ? undefined : cursor + max));
  }
  return lines;
};

const splitEnglishLines = (value, max = 58, limit = 2) => {
  const words = clean(value).split(/\s+/).filter(Boolean);
  if (!words.length) return [];
  const lines = [];
  let line = '';
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (next.length > max && line && lines.length < limit - 1) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines.slice(0, limit);
};

const sceneDurationFrames = (scene, audioScene) => {
  if (Number(scene.durationFrames) > 0) return Number(scene.durationFrames);
  if (Number(audioScene?.durationInFrames) > 0) return Number(audioScene.durationInFrames);
  const text = clean(scene.voiceText || scene.subtitleText || scene.text);
  return Math.max(84, Math.min(210, 78 + Math.round(text.length * 2.1)));
};

const fallbackSegmentTexts = (subtitleText) => {
  const source = clean(subtitleText);
  if (!source) return [''];
  const separators = /[。！？!?；;]+/;
  const parts = source.split(separators).map(clean).filter(Boolean);
  if (parts.length >= 2) return [parts[0], parts.slice(1).join(' ')];
  if (source.length <= 18) return [source];
  const midpoint = Math.ceil(source.length / 2);
  return [source.slice(0, midpoint), source.slice(midpoint)].map(clean).filter(Boolean);
};

const splitCaptionCueTexts = (value) => {
  const source = clean(value);
  if (!source) return [];
  const parts = source
    .split(/(?<=[，。！？；、,!?;])\s*/)
    .map((item) => item.replace(/[，。！？；、,!?;]+$/g, '').trim())
    .filter(Boolean);
  const chunks = parts.length ? parts : [source];
  const cues = [];
  for (const chunk of chunks) {
    if (chunk.length <= 24) {
      cues.push(chunk);
      continue;
    }
    for (let cursor = 0; cursor < chunk.length; cursor += 20) {
      cues.push(chunk.slice(cursor, cursor + 20));
    }
  }
  return cues.length ? cues : [source];
};

const splitEnglishCueTexts = (value, count) => {
  const words = clean(value).split(/\s+/).filter(Boolean);
  if (!words.length || count <= 0) return [];
  if (count === 1) return [words.join(' ')];
  const per = Math.max(1, Math.ceil(words.length / count));
  const result = [];
  for (let index = 0; index < count; index++) {
    result.push(words.slice(index * per, (index + 1) * per).join(' '));
  }
  return result;
};

const buildCaptionCues = (segment, startFrame, endFrame) => {
  const rawCues = Array.isArray(segment.captionCues) && segment.captionCues.length
    ? segment.captionCues.map((cue) => ({
        text: clean(cue.text || cue.subtitleText),
        englishText: clean(cue.englishText || cue.english)
      })).filter((cue) => cue.text)
    : splitCaptionCueTexts(segment.subtitleText || segment.text).map((text) => ({text, englishText: ''}));
  const duration = Math.max(1, endFrame - startFrame);
  const englishParts = splitEnglishCueTexts(segment.englishText, rawCues.length);
  const totalWeight = rawCues.reduce((sum, cue) => sum + Math.max(4, cue.text.length), 0) || rawCues.length || 1;
  let cursor = startFrame;
  return rawCues.map((cue, index) => {
    const isLast = index === rawCues.length - 1;
    const next = isLast ? endFrame : Math.max(cursor + 12, startFrame + Math.round(duration * rawCues.slice(0, index + 1).reduce((sum, item) => sum + Math.max(4, item.text.length), 0) / totalWeight));
    const result = {
      startFrame: cursor,
      endFrame: next,
      text: cue.text,
      englishText: cue.englishText || englishParts[index] || segment.englishText || ''
    };
    cursor = next;
    return result;
  });
};

const normalizeSceneSegments = (scene, subtitleText, englishText, keywords, durationFrames, sceneIndex) => {
  const images = Array.isArray(scene.assetImages) ? scene.assetImages.filter((item) => item?.src).slice(0, 2) : [];
  const layoutMode = clean(scene.layoutMode || scene.sceneLayoutMode || (sceneIndex % 2 === 0 ? 'pair_left_right' : 'center_shift_pair'));
  const providedSegments = Array.isArray(scene.segments) && scene.segments.length ? scene.segments : [];
  const source = providedSegments.length
    ? providedSegments.slice(0, 2)
    : [{
        text: subtitleText,
        subtitleText,
        englishText,
        summaryLabel: keywords[0] || subtitleText,
        layoutMode,
        startRatio: 0,
        endRatio: 1
      }];
  return source.map((segment, index) => {
    const startRatio = clamp(Number(segment.startRatio ?? index / source.length), 0, 0.98);
    const endRatio = clamp(Number(segment.endRatio ?? (index + 1) / source.length), startRatio + 0.01, 1);
    const startFrame = Math.round(startRatio * durationFrames);
    const endFrame = index === source.length - 1 ? durationFrames : Math.max(startFrame + 1, Math.round(endRatio * durationFrames));
    const text = clean(segment.subtitleText || segment.text || subtitleText);
    return {
      ...segment,
      index,
      startFrame,
      endFrame,
      text,
      subtitleText: text,
      englishText: clean(segment.englishText || englishText),
      summaryLabel: clean(segment.summaryLabel || keywords[index] || keywords[0] || text),
      layoutMode: clean(segment.layoutMode || layoutMode),
      assetImages: images,
      captionCues: buildCaptionCues({...segment, subtitleText: text, text, englishText: clean(segment.englishText || englishText)}, startFrame, endFrame)
    };
  });
};

const segmentAtLocal = (scene, local) => {
  const segments = Array.isArray(scene.segments) ? scene.segments : [];
  return segments.find((segment) => local >= segment.startFrame && local < segment.endFrame) || segments[segments.length - 1] || null;
};

const captionAtLocal = (segment, local) => {
  const cues = Array.isArray(segment?.captionCues) ? segment.captionCues : [];
  return cues.find((cue) => local >= cue.startFrame && local < cue.endFrame) || cues[cues.length - 1] || null;
};

export const buildSc1StickmanStory = ({
  title = '',
  scenes: providedScenes = [],
  audioScenes = [],
  fps = FPS
} = {}) => {
  const sourceScenes = Array.isArray(providedScenes) && providedScenes.length
    ? providedScenes
    : [
        {title: 'Challenge', subtitleText: 'Come and challenge the degree of your asset-mindedness', voiceText: 'Come and challenge the degree of your asset-mindedness', keywords: ['law', 'mindset'], mode: 'judge'},
        {title: 'Question', subtitleText: 'What kind of behavior is it to feed crescent to police dogs?', voiceText: 'What kind of behavior is it to feed crescent to police dogs?', keywords: ['dogs', 'behavior'], mode: 'wolf'},
        {title: 'Answer', subtitleText: 'This only applies under special circumstances.', voiceText: 'This only applies under special circumstances.', keywords: ['case', 'answer'], mode: 'police'}
      ];

  let cursor = 0;
  const scenes = sourceScenes.map((scene, index) => {
    const audioScene = audioScenes.find((item) => Number(item.index) === index);
    const durationFrames = sceneDurationFrames(scene, audioScene);
    const startFrame = cursor;
    cursor += durationFrames;
    const voiceText = clean(scene.voiceText || scene.text || scene.subtitleText);
    const subtitleText = clean(scene.subtitleText || scene.displayText || voiceText);
    const englishText = clean(scene.englishText || scene.en || scene.english || '');
    const keywords = Array.isArray(scene.keywords) && scene.keywords.length ? scene.keywords.slice(0, 3).map(clean).filter(Boolean) : splitLines(subtitleText, 4, 2);
    return {
      ...scene,
      id: scene.id || `sc1-${index + 1}`,
      index,
      startFrame,
      durationFrames,
      endFrame: cursor,
      title: clean(scene.title || scene.headline || `Scene ${index + 1}`),
      voiceText,
      subtitleText,
      englishText,
      keywords,
      segments: normalizeSceneSegments(scene, subtitleText, englishText, keywords, durationFrames, index),
      mode: clean(scene.mode || scene.sceneType || scene.visualType || ['judge', 'wolf', 'chase', 'police', 'execution', 'casefile', 'desk'][index % 7]),
      audioSrc: clean(scene.audioSrc || scene.audio?.src || audioScene?.src || '')
    };
  });

  return {
    fps,
    width: WIDTH,
    height: HEIGHT,
    title: clean(title || scenes[0]?.title || 'SC1 Stickman Workflow'),
    scenes,
    durationInFrames: Math.max(1, cursor)
  };
};

const useActiveScene = (story) => {
  const frame = useCurrentFrame();
  const active = story.scenes.find((scene) => frame >= scene.startFrame && frame < scene.endFrame) || story.scenes[story.scenes.length - 1];
  const local = Math.max(0, frame - active.startFrame);
  const progress = clamp(local / active.durationFrames, 0, 1);
  const segment = segmentAtLocal(active, local);
  return {active, local, progress, frame, segment};
};

const AudioTrack = ({story, bgmSrc = null}) => (
  <>
    {story.scenes.map((scene) => scene.audioSrc ? (
      <Sequence key={`audio-${scene.id}`} from={scene.startFrame} durationInFrames={scene.durationFrames}>
        <Audio src={staticFile(scene.audioSrc)} startFrom={0} endAt={scene.durationFrames} volume={1} />
      </Sequence>
    ) : null)}
    {bgmSrc ? <Audio src={staticFile(String(bgmSrc).replace(/^\/+/, ''))} volume={0.08} /> : null}
  </>
);

const Paper = () => (
  <AbsoluteFill style={{background: '#ffffff'}}>
    <div style={{
      position: 'absolute',
      inset: 0,
      background: 'radial-gradient(circle at 18% 12%, rgba(0,0,0,.018), transparent 26%), radial-gradient(circle at 76% 78%, rgba(0,0,0,.018), transparent 30%)'
    }} />
    <div style={{
      position: 'absolute',
      left: -10,
      right: -10,
      top: FLOOR_Y,
      height: 4,
      background: '#202020',
      borderRadius: 6
    }} />
  </AbsoluteFill>
);

const Header = ({title}) => (
  <div style={{position: 'absolute', left: 30, top: 25, display: 'flex', alignItems: 'center', gap: 10, color: '#111', fontSize: 27, fontWeight: 900}}>
    <div style={{width: 28, height: 28, borderRadius: '50%', border: '4px solid #62a9df', display: 'grid', placeItems: 'center'}}>
      <div style={{width: 10, height: 10, borderRadius: '50%', background: '#62a9df'}} />
    </div>
    <span>{title}</span>
  </div>
);

const KeywordLabels = ({scene, segment, local}) => {
  const label = clean(segment?.summaryLabel || scene.keywords?.[0] || scene.title);
  if (!label) return null;
  const localInSegment = Math.max(0, local - Number(segment?.startFrame || 0));
  const enter = interpolate(localInSegment, [0, 14], [0, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const exitStart = Math.max(16, Number(segment?.endFrame || scene.durationFrames) - Number(segment?.startFrame || 0) - 12);
  const exit = interpolate(localInSegment, [exitStart, exitStart + 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.cubic)});
  const opacity = clamp(enter * (1 - exit), 0, 1);
  return (
    <div style={{position: 'absolute', left: 575, right: 160, top: 160, display: 'flex', gap: 30, alignItems: 'center', justifyContent: 'center', height: 52, overflow: 'hidden'}}>
      <div key={`${scene.id}-${segment?.index || 0}-${label}`} style={{display: 'flex', alignItems: 'center', gap: 10, opacity, transform: `translateY(${(1 - enter) * 18 - exit * 10}px)`, fontSize: 32, lineHeight: 1, fontWeight: 900, color: '#111', whiteSpace: 'nowrap', maxWidth: 520, overflow: 'hidden', textOverflow: 'ellipsis'}}>
        <span style={{width: 24, height: 24, background: colors[(scene.index + Number(segment?.index || 0)) % colors.length], display: 'inline-block', borderRadius: 2, flex: '0 0 auto'}} />
        <span>{label}</span>
      </div>
    </div>
  );
};

const Head = ({x, y, scale = 1}) => (
  <div style={{position: 'absolute', left: x, top: y, width: 82 * scale, height: 82 * scale, borderRadius: '50%', background: '#111'}} />
);

const Body = ({x, y, scale = 1, lean = 0}) => (
  <>
    <div style={{position: 'absolute', left: x + 38 * scale, top: y + 78 * scale, width: 12 * scale, height: 145 * scale, background: '#111', borderRadius: 10, transform: `rotate(${lean}deg)`, transformOrigin: 'top'}} />
    <div style={{position: 'absolute', left: x + 42 * scale, top: y + 112 * scale, width: 12 * scale, height: 105 * scale, background: '#111', borderRadius: 10, transform: `rotate(${48 + lean}deg)`, transformOrigin: 'top'}} />
    <div style={{position: 'absolute', left: x + 42 * scale, top: y + 112 * scale, width: 12 * scale, height: 105 * scale, background: '#111', borderRadius: 10, transform: `rotate(${-48 + lean}deg)`, transformOrigin: 'top'}} />
    <div style={{position: 'absolute', left: x + 44 * scale, top: y + 214 * scale, width: 12 * scale, height: 128 * scale, background: '#111', borderRadius: 10, transform: `rotate(${26 + lean}deg)`, transformOrigin: 'top'}} />
    <div style={{position: 'absolute', left: x + 44 * scale, top: y + 214 * scale, width: 12 * scale, height: 128 * scale, background: '#111', borderRadius: 10, transform: `rotate(${-28 + lean}deg)`, transformOrigin: 'top'}} />
  </>
);

const StickPerson = ({x, y, scale = 1, lean = 0}) => (
  <div style={{position: 'absolute', left: x, top: y}}>
    <Head x={0} y={0} scale={scale} />
    <Body x={0} y={0} scale={scale} lean={lean} />
  </div>
);

const JudgeDesk = ({x = 760, y = 310, scale = 1}) => (
  <div style={{position: 'absolute', left: x, top: y, transform: `scale(${scale})`, transformOrigin: 'top left'}}>
    <StickPerson x={62} y={0} scale={0.72} lean={-5} />
    <div style={{position: 'absolute', left: 0, top: 165, width: 210, height: 180, background: '#111'}} />
    <div style={{position: 'absolute', left: 18, top: 190, width: 54, height: 122, border: '4px solid #fff'}} />
    <div style={{position: 'absolute', left: 84, top: 190, width: 54, height: 122, border: '4px solid #fff'}} />
  </div>
);

const Wolf = ({x = 1280, y = 300, scale = 1}) => (
  <div style={{position: 'absolute', left: x, top: y, transform: `scale(${scale})`, transformOrigin: 'top left'}}>
    <div style={{position: 'absolute', left: 110, top: 130, width: 330, height: 120, background: '#111', borderRadius: '55% 48% 42% 48%'}} />
    <div style={{position: 'absolute', left: 28, top: 82, width: 145, height: 120, background: '#111', clipPath: 'polygon(0 50%, 85% 0, 100% 82%, 35% 100%)'}} />
    <div style={{position: 'absolute', left: 58, top: 66, width: 58, height: 70, background: '#111', clipPath: 'polygon(20% 100%, 45% 0, 100% 100%)'}} />
    {[140, 220, 310, 390].map((lx, index) => (
      <div key={lx} style={{position: 'absolute', left: lx, top: 230, width: 22, height: 120, background: '#111', transform: `rotate(${index % 2 ? -14 : 12}deg)`, transformOrigin: 'top'}} />
    ))}
    <div style={{position: 'absolute', right: -16, top: 116, width: 150, height: 28, background: '#111', transform: 'rotate(-24deg)', borderRadius: 30}} />
  </div>
);

const PolicePair = ({x = 810, y = 360, scale = 1}) => (
  <div style={{position: 'absolute', left: x, top: y, transform: `scale(${scale})`, transformOrigin: 'top left'}}>
    <StickPerson x={0} y={0} scale={1.25} />
    <div style={{position: 'absolute', left: 25, top: -20, width: 95, height: 22, background: '#111', borderRadius: 8}} />
    <StickPerson x={170} y={28} scale={1.05} lean={10} />
    <div style={{position: 'absolute', left: 218, top: 138, width: 95, height: 18, background: '#fff', border: '5px solid #111', borderRadius: 18}} />
  </div>
);

const Chase = ({local}) => (
  <>
    <StickPerson x={350 - Math.sin(local / 8) * 22} y={390} scale={1.05} lean={-22} />
    <StickPerson x={760 + Math.sin(local / 8) * 20} y={375} scale={1.1} lean={-36} />
    <StickPerson x={930 + Math.cos(local / 9) * 16} y={350} scale={1.0} lean={32} />
    <div style={{position: 'absolute', left: 298, top: 472, fontSize: 36, fontWeight: 900, transform: 'rotate(12deg)'}}>Help...</div>
    <div style={{position: 'absolute', left: 1015, top: 428, fontSize: 38, fontWeight: 900, transform: 'rotate(18deg)'}}>aah</div>
  </>
);

const Execution = () => (
  <>
    <StickPerson x={280} y={475} scale={0.65} />
    <div style={{position: 'absolute', left: 310, top: 375, fontSize: 64, fontWeight: 900}}>?</div>
    <StickPerson x={1180} y={390} scale={1.2} />
    <div style={{position: 'absolute', left: 1320, top: 450, width: 160, height: 160, borderRadius: '50%', border: '18px solid #111', display: 'grid', placeItems: 'center', fontSize: 92, fontWeight: 1000}}>x</div>
  </>
);

const CaseFile = () => (
  <>
    <StickPerson x={1020} y={410} scale={1.05} />
    <div style={{position: 'absolute', left: 1220, top: 480, width: 360, height: 180, border: '5px solid #111', transform: 'rotate(-8deg)'}}>
      <div style={{position: 'absolute', left: 15, top: 14, right: 15, height: 26, background: '#111'}} />
      <div style={{position: 'absolute', left: 35, top: 68, width: 120, height: 55, borderRadius: '50%', background: '#111'}} />
      <div style={{position: 'absolute', left: 200, top: 78, width: 115, height: 16, background: '#111'}} />
      <div style={{position: 'absolute', left: 200, top: 112, width: 86, height: 16, background: '#111'}} />
    </div>
  </>
);

const DeskScene = ({local}) => (
  <>
    <div style={{position: 'absolute', left: 320, top: 605, width: 350, height: 150, background: '#111'}} />
    <StickPerson x={250} y={410} scale={0.78} lean={12} />
    <div style={{position: 'absolute', left: 420, top: 415, width: 120, height: 120, borderRadius: '50%', background: '#111', transform: `translateY(${Math.sin(local / 10) * 10}px)`}} />
    <StickPerson x={960} y={430} scale={1.0} lean={-25} />
    <StickPerson x={1210} y={430} scale={1.0} lean={22} />
    <div style={{position: 'absolute', left: 1080, top: 630, width: 220, height: 35, background: '#111', transform: 'rotate(-14deg)'}} />
  </>
);

const OptionalImage = ({src}) => {
  if (!src) return null;
  const source = String(src);
  const image = /^(https?:|file:)\/\//i.test(source)
    ? <img src={source} alt="" crossOrigin="anonymous" referrerPolicy="no-referrer" style={{width: '100%', height: '100%', objectFit: 'contain', filter: 'grayscale(1) contrast(2.2)', mixBlendMode: 'multiply'}} />
    : <Img src={staticFile(source.replace(/^\/+/, ''))} style={{width: '100%', height: '100%', objectFit: 'contain', filter: 'grayscale(1) contrast(2.2)', mixBlendMode: 'multiply'}} />;
  return (
    <div style={{position: 'absolute', left: 390, top: 250, width: 1140, height: 555, display: 'grid', placeItems: 'center', overflow: 'hidden'}}>
      {image}
    </div>
  );
};

const lerp = (a, b, t) => a + (b - a) * t;

const interpolateBox = (from, to, t) => ({
  left: lerp(from.left, to.left, t),
  top: lerp(from.top, to.top, t),
  width: lerp(from.width, to.width, t),
  height: lerp(from.height, to.height, t),
});

const SceneImage = ({item, box, progress, start = 0, direction = 'left'}) => {
  const src = item?.src;
  if (!src) return null;
  const localProgress = clamp((progress - start) / Math.max(0.0001, 1 - start), 0, 1);
  const enter = interpolate(localProgress, [0, 0.16], [0, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const exit = interpolate(progress, [0.9, 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.cubic)});
  const travel = {
    left: {x: -180, y: 0},
    right: {x: 180, y: 0},
    top: {x: 0, y: -120},
    bottom: {x: 0, y: 120},
    center: {x: 0, y: 0}
  }[direction] || {x: 0, y: 0};
  const opacity = clamp(enter * (1 - exit), 0, 1);
  const shared = {
    width: '100%',
    height: '100%',
    objectFit: 'contain',
    filter: 'grayscale(1) contrast(2.25)',
    mixBlendMode: 'multiply',
    transform: `scale(${item?.scale || 1.18})`,
  };
  const source = String(src);
  const image = /^(https?:|file:)\/\//i.test(source)
    ? <img src={source} alt="" crossOrigin="anonymous" referrerPolicy="no-referrer" style={shared} />
    : <Img src={staticFile(source.replace(/^\/+/, ''))} style={shared} />;
  return (
    <div style={{
      position: 'absolute',
      left: box.left,
      top: box.top,
      width: box.width,
      height: box.height,
      opacity,
      transform: `translate(${(1 - enter) * travel.x}px, ${(1 - enter) * travel.y}px)`,
      overflow: 'hidden',
      display: 'grid',
      placeItems: 'center'
    }}>
      {image}
    </div>
  );
};

const MaterialSceneImages = ({scene, segment, local}) => {
  const images = Array.isArray(scene.assetImages) ? scene.assetImages.filter((item) => item?.src).slice(0, 2) : [];
  if (!images.length) return null;
  const segmentStart = Number(segment?.startFrame || 0);
  const segmentDuration = Math.max(1, Number(segment?.endFrame || scene.durationFrames) - segmentStart);
  const progress = clamp((local - segmentStart) / segmentDuration, 0, 1);
  const layoutMode = clean(segment?.layoutMode || scene.layoutMode || 'pair_left_right');
  const secondStart = layoutMode === 'center_shift_pair' ? 0.42 : 0.36;
  const leftBox = {left: 220, top: 275, width: 660, height: 500};
  const rightBox = {left: 1040, top: 275, width: 660, height: 500};
  const centerBox = {left: 400, top: 250, width: 1120, height: 560};
  const firstBox = layoutMode === 'center_shift_pair'
    ? (progress < secondStart ? centerBox : interpolateBox(centerBox, leftBox, clamp((progress - secondStart) / 0.18, 0, 1)))
    : leftBox;
  const firstDirection = layoutMode === 'center_shift_pair' ? 'center' : (images[0]?.enterDirection || 'left');
  const secondDirection = images[1]?.enterDirection || 'right';
  return (
    <div style={{position: 'absolute', left: 0, right: 0, top: 220, height: 600, overflow: 'hidden'}}>
      <SceneImage item={images[0]} box={firstBox} progress={progress} start={0} direction={firstDirection} />
      {images[1] ? <SceneImage item={images[1]} box={rightBox} progress={progress} start={secondStart} direction={secondDirection} /> : null}
    </div>
  );
};

const SceneVisual = ({scene, local, segment}) => {
  if (Array.isArray(scene.assetImages) && scene.assetImages.length) return <MaterialSceneImages scene={scene} segment={segment} local={local} />;
  const mediaSrc = scene.media?.src || scene.imageSrc || scene.assetSrc;
  if (mediaSrc) return <OptionalImage src={mediaSrc} />;
  const mode = scene.mode;
  if (mode.includes('wolf') || mode.includes('dog')) return <><JudgeDesk x={760} y={300} scale={1.1} /><Wolf x={1250} y={290} scale={1} /></>;
  if (mode.includes('chase') || mode.includes('crime')) return <Chase local={local} />;
  if (mode.includes('police') || mode.includes('handcuff')) return <PolicePair x={785} y={350} scale={1} />;
  if (mode.includes('execution') || mode.includes('forbid')) return <Execution />;
  if (mode.includes('case') || mode.includes('gun')) return <CaseFile />;
  if (mode.includes('desk') || mode.includes('debate')) return <DeskScene local={local} />;
  return <JudgeDesk x={760} y={300} scale={1.1} />;
};

const SceneLayer = ({scene, local}) => {
  const enter = interpolate(local, [0, 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const exit = interpolate(local, [scene.durationFrames - 18, scene.durationFrames], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.cubic)});
  const slideX = (1 - enter) * 140 - exit * 120;
  const opacity = clamp(enter * (1 - exit), 0, 1);
  return (
    <div style={{position: 'absolute', inset: 0, opacity, transform: `translateX(${slideX}px)`}}>
      <SceneVisual scene={scene} local={local} segment={segmentAtLocal(scene, local)} />
    </div>
  );
};

const Subtitle = ({scene, segment, local}) => {
  const cue = captionAtLocal(segment, local);
  const zhText = cue?.text || segment?.subtitleText || scene.subtitleText || scene.voiceText;
  const enText = cue?.englishText || segment?.englishText || scene.englishText;
  const zhLines = splitLines(zhText, 23, 2);
  const enLines = splitEnglishLines(enText, 58, 2);
  return (
    <div style={{position: 'absolute', left: 0, right: 0, top: 845, height: 155, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start', textAlign: 'center', paddingTop: 10, overflow: 'hidden'}}>
      <div style={{fontSize: zhLines.join('').length > 24 ? 42 : 48, lineHeight: 1.08, fontWeight: 1000, color: '#111'}}>
        {zhLines.map((line) => <div key={line}>{line}</div>)}
      </div>
      {enLines.length ? (
        <div style={{marginTop: 7, fontSize: 18, lineHeight: 1.05, fontWeight: 700, color: '#333', fontStyle: 'italic'}}>
          {enLines.map((line) => <div key={line}>{line}</div>)}
        </div>
      ) : null}
    </div>
  );
};

const Progress = ({frame, durationInFrames}) => (
  <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 10, background: '#050505'}}>
    <div style={{height: '100%', width: `${clamp(frame / durationInFrames, 0, 1) * 100}%`, background: '#111'}} />
  </div>
);

export const Sc1StickmanVideo = (props) => {
  const story = buildSc1StickmanStory(props);
  const {active, local, frame, segment} = useActiveScene(story);
  const title = clean(props.brandTitle || props.watermark || story.title);

  return (
    <AbsoluteFill style={{fontFamily: FONT, background: '#fff', overflow: 'hidden'}}>
      <Paper />
      <Header title={title} />
      <KeywordLabels scene={active} segment={segment} local={local} />
      <SceneLayer scene={active} local={local} />
      <Subtitle scene={active} segment={segment} local={local} />
      <AudioTrack story={story} bgmSrc={props.bgmSrc} />
      <Progress frame={frame} durationInFrames={story.durationInFrames} />
    </AbsoluteFill>
  );
};
