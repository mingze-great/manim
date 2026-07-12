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
      englishText: clean(scene.englishText || scene.en || scene.english || ''),
      keywords: Array.isArray(scene.keywords) && scene.keywords.length ? scene.keywords.slice(0, 3).map(clean).filter(Boolean) : splitLines(subtitleText, 4, 2),
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
  return {active, local, progress, frame};
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

const KeywordLabels = ({scene, local}) => {
  const labels = (scene.keywords || []).slice(0, 3);
  return (
    <div style={{position: 'absolute', left: 575, right: 160, top: 160, display: 'flex', gap: 30, alignItems: 'center', justifyContent: 'center', height: 52, overflow: 'hidden'}}>
      {labels.map((keyword, index) => {
        const enter = interpolate(local, [index * 5, index * 5 + 14], [0, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
        return (
          <div key={`${keyword}-${index}`} style={{display: 'flex', alignItems: 'center', gap: 8, opacity: enter, transform: `translateY(${(1 - enter) * 16}px)`, fontSize: 30, lineHeight: 1, fontWeight: 900, color: '#111', whiteSpace: 'nowrap', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis'}}>
            <span style={{width: 24, height: 24, background: colors[(scene.index + index) % colors.length], display: 'inline-block', borderRadius: 2}} />
            <span>{keyword}</span>
          </div>
        );
      })}
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

const MaterialImage = ({item, index, count, local}) => {
  const src = item?.src;
  if (!src) return null;
  const slot = count === 1
    ? {left: 500, top: 260, width: 920, height: 540, scale: 1.32}
    : index === 0
      ? {left: 250, top: 275, width: 650, height: 535, scale: 1.45}
      : {left: 1010, top: 275, width: 650, height: 535, scale: 1.45};
  const enter = interpolate(local, [index * 6, index * 6 + 18], [0, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const x = (1 - enter) * (index === 0 ? -80 : 80);
  const shared = {
    width: '100%',
    height: '100%',
    objectFit: 'contain',
    filter: 'grayscale(1) contrast(2.25)',
    mixBlendMode: 'multiply',
    transform: `scale(${slot.scale})`,
  };
  const source = String(src);
  const image = /^(https?:|file:)\/\//i.test(source)
    ? <img src={source} alt="" crossOrigin="anonymous" referrerPolicy="no-referrer" style={shared} />
    : <Img src={staticFile(source.replace(/^\/+/, ''))} style={shared} />;
  return (
    <div style={{
      position: 'absolute',
      left: slot.left,
      top: slot.top,
      width: slot.width,
      height: slot.height,
      opacity: enter,
      transform: `translateX(${x}px)`,
      overflow: 'hidden',
      display: 'grid',
      placeItems: 'center'
    }}>
      {image}
    </div>
  );
};

const MaterialSceneImages = ({scene, local}) => {
  const images = Array.isArray(scene.assetImages) ? scene.assetImages.filter((item) => item?.src).slice(0, 2) : [];
  if (!images.length) return null;
  return (
    <div style={{position: 'absolute', left: 0, right: 0, top: 220, height: 600, overflow: 'hidden'}}>
      {images.map((item, index) => <MaterialImage key={`${item.src}-${index}`} item={item} index={index} count={images.length} local={local} />)}
    </div>
  );
};

const SceneVisual = ({scene, local}) => {
  if (Array.isArray(scene.assetImages) && scene.assetImages.length) return <MaterialSceneImages scene={scene} local={local} />;
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
      <SceneVisual scene={scene} local={local} />
    </div>
  );
};

const Subtitle = ({scene}) => {
  const zhLines = splitLines(scene.subtitleText || scene.voiceText, 23, 2);
  const enLines = splitEnglishLines(scene.englishText, 58, 2);
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
  const {active, local, frame} = useActiveScene(story);
  const title = clean(props.brandTitle || props.watermark || story.title);

  return (
    <AbsoluteFill style={{fontFamily: FONT, background: '#fff', overflow: 'hidden'}}>
      <Paper />
      <Header title={title} />
      <KeywordLabels scene={active} local={local} />
      <SceneLayer scene={active} local={local} />
      <Subtitle scene={active} />
      <AudioTrack story={story} bgmSrc={props.bgmSrc} />
      <Progress frame={frame} durationInFrames={story.durationInFrames} />
    </AbsoluteFill>
  );
};
