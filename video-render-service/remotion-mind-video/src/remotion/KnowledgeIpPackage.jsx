import React from 'react';
import {
  AbsoluteFill,
  Easing,
  interpolate,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig
} from 'remotion';

const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

const defaultSegments = [
  {
    startMs: 0,
    endMs: 15000,
    tab: '身边的大儒',
    title: '先把问题问准',
    zh: '真正厉害的人，第一步不是急着给答案，而是先把问题问准。',
    en: 'Great thinkers define the problem before chasing the answer.',
    kind: 'arrow'
  },
  {
    startMs: 15000,
    endMs: 33000,
    tab: '古典大儒',
    title: '不要只处理表面',
    zh: '很多人一遇到麻烦，就马上找方案，但这往往只是在处理表面。',
    en: 'Most people solve the surface, not the real structure underneath.',
    kind: 'shell'
  },
  {
    startMs: 33000,
    endMs: 52000,
    tab: '现代大儒',
    title: '借助案例建立认知',
    zh: '真正有价值的案例，会帮你看清问题背后的结构。',
    en: 'A strong case reveals the structure hidden behind the problem.',
    kind: 'phone'
  },
  {
    startMs: 52000,
    endMs: 75000,
    tab: '英雄主义',
    title: '先量化差距',
    zh: '目标是多少，现状是多少，差距有多大，必须先讲清楚。',
    en: 'Measure the target, the current state, and the gap first.',
    kind: 'cards'
  },
  {
    startMs: 75000,
    endMs: 100000,
    tab: '身边的大儒',
    title: '找到问题来源',
    zh: '再判断问题到底出在产品、价格、团队，还是市场变化。',
    en: 'Then trace whether it comes from product, price, team, or market.',
    kind: 'tree'
  },
  {
    startMs: 100000,
    endMs: 126000,
    tab: '古典大儒',
    title: '区分问题等级',
    zh: '断崖式下跌和小幅波动，根本不是同一类问题。',
    en: 'A collapse and a fluctuation are not the same class of problem.',
    kind: 'compare'
  },
  {
    startMs: 126000,
    endMs: 151000,
    tab: '现代大儒',
    title: '匹配不同方案',
    zh: '问题等级不同，解决方法也完全不同。',
    en: 'Different levels of problems require different playbooks.',
    kind: 'paths'
  },
  {
    startMs: 151000,
    endMs: 172400,
    tab: '英雄主义',
    title: '答案自然出现',
    zh: '高手和普通人的区别，是先把问题结构拆清楚。',
    en: 'Ask the right question, and the answer starts to appear.',
    kind: 'door'
  }
];

const ink = '#171717';
const paper = '#f4f0e7';
const warm = '#d7bd86';
const red = '#b93422';
const blue = '#2a5d8f';
const green = '#276b50';

const activeSegment = (segments, currentMs) =>
  segments.find((item) => currentMs >= item.startMs && currentMs < item.endMs) || segments[segments.length - 1];

const activeCaption = (captions, currentMs, fallback) =>
  (captions || []).find((item) => currentMs >= item.startMs && currentMs < item.endMs) || fallback;

const splitTwoLines = (text, maxChars = 20) => {
  const cleanText = String(text || '').replace(/\s+/g, '').trim();
  if (!cleanText) return [];
  if (cleanText.length <= maxChars) return [cleanText];
  if (cleanText.length > maxChars * 2) {
    const lines = [];
    for (let cursor = 0; cursor < cleanText.length && lines.length < 3; cursor += maxChars) {
      lines.push(cleanText.slice(cursor, lines.length === 2 ? undefined : cursor + maxChars));
    }
    return lines.filter(Boolean);
  }
  const target = Math.ceil(cleanText.length / 2);
  const punctBreaks = [...cleanText.matchAll(/[，。！？；,.!?;]/g)].map((match) => match.index + 1);
  const nearestPunct = punctBreaks
    .filter((index) => index >= 8 && index <= cleanText.length - 6)
    .sort((a, b) => Math.abs(a - target) - Math.abs(b - target))[0];
  const firstBreak = nearestPunct || Math.max(8, target);
  const first = cleanText.slice(0, firstBreak);
  const second = cleanText.slice(firstBreak);
  return [first, second].filter(Boolean);
};

const PaperBackground = () => (
  <AbsoluteFill style={{background: paper}}>
    <div style={{
      position: 'absolute',
      inset: 0,
      backgroundImage: [
        'radial-gradient(circle at 20% 12%, rgba(150,122,70,.14), transparent 30%)',
        'radial-gradient(circle at 80% 72%, rgba(60,74,96,.10), transparent 36%)',
        'linear-gradient(90deg, rgba(0,0,0,.035) 1px, transparent 1px)',
        'linear-gradient(rgba(0,0,0,.026) 1px, transparent 1px)'
      ].join(', '),
      backgroundSize: 'auto, auto, 42px 42px, 42px 42px',
      opacity: 0.72
    }} />
    <div style={{
      position: 'absolute',
      inset: 0,
      background: 'repeating-linear-gradient(0deg, rgba(0,0,0,.018), rgba(0,0,0,.018) 1px, transparent 1px, transparent 5px)',
      mixBlendMode: 'multiply',
      opacity: 0.4
    }} />
  </AbsoluteFill>
);

const PhoneStatus = () => (
  <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: 48, color: '#fff', textShadow: '0 1px 6px rgba(0,0,0,.45)', fontSize: 21, fontWeight: 700}}>
    <div style={{position: 'absolute', left: 22, top: 12}}>11:48</div>
    <div style={{position: 'absolute', right: 22, top: 12, display: 'flex', gap: 10, alignItems: 'center'}}>
      <span>4G</span>
      <span style={{width: 42, height: 18, border: '2px solid #fff', borderRadius: 5, display: 'inline-block', position: 'relative'}}>
        <span style={{position: 'absolute', left: 3, top: 3, width: 27, height: 8, borderRadius: 3, background: '#fff'}} />
      </span>
    </div>
  </div>
);

const TopTabs = ({active}) => {
  const title = active.mainTitle || '\u666e\u901a\u4eba\u5982\u4f55\u6293\u4f4f\u65f6\u4ee3\u673a\u4f1a';
  const chapter = active.title || '\u6838\u5fc3\u89c2\u70b9';
  return (
    <div style={{
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      height: 132,
      background: 'rgba(248,245,238,.96)',
      borderBottom: '4px solid #111',
      color: ink,
      fontWeight: 900,
      zIndex: 5
    }}>
      <div style={{
        position: 'absolute',
        left: 42,
        top: 22,
        fontSize: 42,
        fontWeight: 1000,
        letterSpacing: 0,
        color: '#111'
      }}>{title}</div>
      <div style={{
        position: 'absolute',
        right: 42,
        top: 22,
        height: 42,
        padding: '0 20px',
        borderRadius: 999,
        border: '2px solid rgba(17,17,17,.78)',
        display: 'flex',
        alignItems: 'center',
        fontSize: 21,
        fontWeight: 900,
        color: '#111',
        background: 'rgba(215,189,134,.26)'
      }}>\u77e5\u8bc6IP\u5305\u88c5</div>
      <div style={{
        position: 'absolute',
        left: 42,
        right: 42,
        bottom: 17,
        height: 38,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderTop: '2px solid rgba(17,17,17,.28)',
        paddingTop: 12
      }}>
        <div style={{fontSize: 25, fontWeight: 1000, color: '#111'}}>\u5f53\u524d\u7ae0\u8282 / {chapter}</div>
        <div style={{fontSize: 20, fontWeight: 800, color: 'rgba(17,17,17,.72)'}}>\u7d20\u6750\u540c\u6b65 / \u5b57\u5e55\u540c\u6b65 / \u8fdb\u5ea6\u5305\u88c5</div>
      </div>
    </div>
  );
};

const BrushText = ({children, color = '#fff', x = 80, y = 66, size = 76}) => (
  <div style={{
    position: 'absolute',
    left: x,
    top: y,
    fontSize: size,
    fontWeight: 1000,
    color,
    textShadow: '4px 5px 0 rgba(0,0,0,.32), 0 0 20px rgba(255,255,255,.25)',
    transform: 'skew(-4deg) rotate(-2deg)'
  }}>{children}</div>
);

const StickFigure = ({x = 420, y = 230, mood = 'neutral', scale = 1}) => {
  const frame = useCurrentFrame();
  const bob = Math.sin(frame / 8) * 4;
  const mouth = mood === 'shock' ? 'O' : mood === 'sad' ? '︵' : '—';
  return (
    <div style={{position: 'absolute', left: x, top: y + bob, width: 120 * scale, height: 220 * scale}}>
      <div style={{position: 'absolute', left: 33 * scale, top: 0, width: 58 * scale, height: 58 * scale, borderRadius: '50%', background: '#f8f4e9', border: `${5 * scale}px solid #111`}}>
        <div style={{position: 'absolute', left: 13 * scale, top: 18 * scale, width: 8 * scale, height: 8 * scale, borderRadius: 99, background: '#111'}} />
        <div style={{position: 'absolute', right: 13 * scale, top: 18 * scale, width: 8 * scale, height: 8 * scale, borderRadius: 99, background: '#111'}} />
        <div style={{position: 'absolute', left: 21 * scale, top: 34 * scale, fontSize: 16 * scale, fontWeight: 900, color: '#111'}}>{mouth}</div>
      </div>
      <div style={{position: 'absolute', left: 62 * scale, top: 62 * scale, width: 5 * scale, height: 92 * scale, background: '#111', borderRadius: 4}} />
      <div style={{position: 'absolute', left: 38 * scale, top: 84 * scale, width: 5 * scale, height: 70 * scale, background: '#111', transform: 'rotate(34deg)', transformOrigin: 'top'}} />
      <div style={{position: 'absolute', left: 84 * scale, top: 83 * scale, width: 5 * scale, height: 70 * scale, background: '#111', transform: 'rotate(-34deg)', transformOrigin: 'top'}} />
      <div style={{position: 'absolute', left: 60 * scale, top: 150 * scale, width: 5 * scale, height: 76 * scale, background: '#111', transform: 'rotate(22deg)', transformOrigin: 'top'}} />
      <div style={{position: 'absolute', left: 64 * scale, top: 150 * scale, width: 5 * scale, height: 76 * scale, background: '#111', transform: 'rotate(-22deg)', transformOrigin: 'top'}} />
    </div>
  );
};

const MaterialScene = ({active, localFrame, materialTrackSrc}) => {
  const enter = interpolate(localFrame, [0, 15], [0, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const sway = Math.sin(localFrame / 20);
  const common = {
    position: 'absolute',
    left: 0,
    right: 0,
    top: 160,
    height: 520,
    overflow: 'hidden',
    background: '#f5f1e9',
    borderTop: '4px solid #111',
    borderBottom: '4px solid #111'
  };
  const materialSrc = materialTrackSrc || active.materialSrc || active.assetSrc || active.videoSrc || active.media?.src;
  const MaterialClip = () => {
    if (!materialSrc) return null;
    const src = String(materialSrc).startsWith('http') ? materialSrc : staticFile(String(materialSrc).replace(/^\/+/, ''));
    const segmentFrames = Math.max(1, Math.round(((active.endMs || 0) - (active.startMs || 0)) / 1000 * 30));
    return (
      <div style={{...common, background: '#111'}}>
        <OffthreadVideo
          src={src}
          muted
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            filter: 'contrast(1.04) saturate(1.06)',
            transform: materialTrackSrc
              ? 'scale(1.025)'
              : `scale(${1.02 + enter * 0.035 + localFrame / segmentFrames * 0.035}) translate(${Math.sin(localFrame / 32) * 8}px, ${Math.cos(localFrame / 35) * 5}px)`
          }}
        />
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'linear-gradient(180deg, rgba(0,0,0,.08), transparent 45%, rgba(0,0,0,.12))'
        }} />
      </div>
    );
  };

  const landscape = () => {
    const clip = MaterialClip();
    if (clip) return clip;
    switch (active.kind) {
      case 'arrow':
        return (
          <div style={{...common, background: 'linear-gradient(180deg, #91452f, #221916)'}}>
            <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(circle at 70% 40%, rgba(0,0,0,.7), transparent 30%), repeating-linear-gradient(165deg, rgba(0,0,0,.18), rgba(0,0,0,.18) 8px, transparent 8px, transparent 24px)'}} />
            <BrushText color="#f4ffe9" x={86} y={68}>杠精</BrushText>
            <div style={{position: 'absolute', left: 180, top: 260, width: 540, height: 22, background: red, transform: `translateX(${localFrame * 4 % 120 - 60}px) rotate(-8deg)`, boxShadow: '0 0 22px rgba(185,52,34,.6)'}} />
            <div style={{position: 'absolute', right: 120, top: 110, width: 190, height: 310, borderRadius: '48% 52% 42% 58%', background: '#161719', boxShadow: '0 0 0 8px rgba(0,0,0,.2)'}} />
            <StickFigure x={270} y={205} mood="shock" scale={1.08} />
            <div style={{position: 'absolute', left: 555, top: 218, color: '#fff', fontSize: 84, fontWeight: 1000, opacity: 0.9, transform: `scale(${0.8 + enter * 0.2})`}}>×</div>
          </div>
        );
      case 'shell':
        return (
          <div style={{...common, background: 'linear-gradient(180deg, #fffaf0, #eadfcd)'}}>
            <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(circle at 50% 48%, rgba(185,52,34,.16), transparent 28%)'}} />
            {['办法', '借口', '情绪', '甩锅'].map((word, i) => (
              <div key={word} style={{position: 'absolute', left: 150 + i * 200 + Math.sin(localFrame / 12 + i) * 18, top: 122 + (i % 2) * 165 + Math.cos(localFrame / 14 + i) * 16, color: red, fontSize: 42, fontWeight: 1000, transform: `rotate(${[-12, 9, -6, 14][i]}deg)`}}>{word}</div>
            ))}
            <div style={{position: 'absolute', left: 385, top: 158, width: 310, height: 210, borderRadius: '48%', background: '#171717', boxShadow: '0 0 90px rgba(246,199,106,.75)'}}>
              <div style={{position: 'absolute', inset: 30, borderRadius: '50%', background: warm, display: 'grid', placeItems: 'center', fontSize: 48, fontWeight: 1000}}>真实问题</div>
            </div>
          </div>
        );
      case 'phone':
        return (
          <div style={{...common, background: 'linear-gradient(180deg, #dfe9ef, #f4efe3)'}}>
            <div style={{position: 'absolute', left: 315, top: 44, width: 450, height: 420, borderRadius: 44, background: '#101418', border: '12px solid #1e2022', boxShadow: '0 36px 70px rgba(0,0,0,.32)', transform: `translateY(${(1 - enter) * 80}px) scale(${0.92 + enter * 0.08})`}}>
              <div style={{position: 'absolute', left: 26, right: 26, top: 34, color: '#fff', fontSize: 31, fontWeight: 900}}>知乎 · 热门回答</div>
              <div style={{position: 'absolute', left: 28, right: 28, top: 100, height: 78, borderRadius: 18, background: '#fff', color: '#111', fontSize: 25, padding: 18, fontWeight: 800}}>前几天我刷知乎时，偶然看到一篇文章</div>
              <div style={{position: 'absolute', left: 28, right: 28, top: 202, height: 112, borderRadius: 20, background: '#fff4cf', color: '#111', fontSize: 26, lineHeight: 1.25, padding: 18, fontWeight: 900}}>这篇文章系统讲解了分析问题</div>
              <div style={{position: 'absolute', left: 120, right: 120, bottom: 28, height: 9, borderRadius: 99, background: '#fff'}} />
            </div>
          </div>
        );
      case 'cards':
        return (
          <div style={{...common, background: 'linear-gradient(180deg, #f8f4e7, #e5decf)'}}>
            {['目标100万', '现状30万', '差距70万'].map((text, i) => (
              <div key={text} style={{position: 'absolute', left: 92 + i * 320, top: 150 + Math.sin(localFrame / 10 + i) * 9, width: 255, height: 150, borderRadius: 12, background: i === 2 ? '#fae2df' : '#fffdf7', border: `5px solid ${i === 2 ? red : '#111'}`, display: 'grid', placeItems: 'center', color: i === 2 ? red : '#111', fontSize: 42, fontWeight: 1000, boxShadow: '10px 12px 0 rgba(0,0,0,.16)'}}>{text}</div>
            ))}
          </div>
        );
      case 'tree':
        return (
          <div style={{...common, background: 'linear-gradient(180deg, #e8eef1, #f7f1e5)'}}>
            <div style={{position: 'absolute', left: 412, top: 182, width: 260, height: 82, border: '5px solid #111', background: '#fff', display: 'grid', placeItems: 'center', fontSize: 40, fontWeight: 1000}}>70万缺口</div>
            {['产品', '价格', '团队', '市场'].map((word, i) => {
              const pos = [[118, 90], [750, 90], [145, 350], [725, 350]][i];
              return (
                <React.Fragment key={word}>
                  <div style={{position: 'absolute', left: 542, top: 224, width: 250, height: 4, background: '#111', transform: `rotate(${[-28, 28, 25, -25][i]}deg)`, transformOrigin: '0 50%', opacity: enter}} />
                  <div style={{position: 'absolute', left: pos[0], top: pos[1], width: 210, height: 78, border: '4px solid #111', borderRadius: 8, background: '#fffdf7', display: 'grid', placeItems: 'center', fontSize: 38, fontWeight: 1000}}>{word}</div>
                </React.Fragment>
              );
            })}
          </div>
        );
      case 'compare':
        return (
          <div style={{...common, background: 'linear-gradient(180deg, #f5f0e4, #e9e0d0)'}}>
            {[0, 1].map((side) => (
              <div key={side} style={{position: 'absolute', left: side ? 570 : 70, top: 86, width: 430, height: 330, background: '#fffdf8', border: '5px solid #111', padding: 24}}>
                <div style={{fontSize: 38, fontWeight: 1000, color: side ? green : red}}>{side ? '小幅波动' : '断崖下跌'}</div>
                <div style={{position: 'absolute', left: 42, right: 42, bottom: 70, height: 5, background: '#111'}} />
                <div style={{position: 'absolute', left: 58, bottom: side ? 120 : 235, width: 280, height: 10, borderRadius: 99, background: side ? green : red, transform: `rotate(${side ? 8 : 36}deg) scaleX(${enter})`, transformOrigin: '0 50%'}} />
              </div>
            ))}
          </div>
        );
      case 'paths':
        return (
          <div style={{...common, background: 'linear-gradient(180deg, #20282c, #f1e6d0)'}}>
            <BrushText color="#fff4cc" x={92} y={70} size={64}>方案不同</BrushText>
            {['紧急止损', '全面排查', '优化调整', '持续观察'].map((word, i) => (
              <div key={word} style={{position: 'absolute', left: 120 + (i % 2) * 510, top: 170 + Math.floor(i / 2) * 135, width: 350, height: 82, borderRadius: 999, border: `4px solid ${i < 2 ? red : green}`, background: 'rgba(255,255,255,.92)', display: 'grid', placeItems: 'center', fontSize: 38, fontWeight: 1000, transform: `translateX(${(1 - enter) * (i % 2 ? 50 : -50)}px)`}}>{word}</div>
            ))}
          </div>
        );
      default:
        return (
          <div style={{...common, background: 'linear-gradient(180deg, #152033, #eadfcf)'}}>
            <div style={{position: 'absolute', left: 210, top: 95, width: 650, height: 290, border: '7px solid #111', background: '#fffaf0', boxShadow: '14px 16px 0 rgba(0,0,0,.22)', display: 'grid', placeItems: 'center'}}>
              <div style={{fontSize: 58, lineHeight: 1.12, fontWeight: 1000, textAlign: 'center', color: '#111'}}>问题问对了<br />答案自然出现</div>
            </div>
            <div style={{position: 'absolute', left: 476, top: 188, fontSize: 110, color: warm, textShadow: '0 3px 0 #111', transform: `rotate(${sway * 5}deg)`}}>钥</div>
          </div>
        );
    }
  };

  return <Sequence key={`${active.title}-${active.startMs}`}>{landscape()}</Sequence>;
};

const SubtitleBand = ({caption}) => {
  const zh = String(caption?.zh || caption?.text || '').replace(/\s+/g, '').trim();
  const en = caption?.en || '';
  const lines = splitTwoLines(zh, 24).slice(0, 2);
  const charCount = lines.join('').length;
  const fontSize = charCount > 46 ? 40 : charCount > 34 ? 46 : 56;
  return (
  <div style={{
    position: 'absolute',
    top: 680,
    left: 0,
    right: 0,
    height: 260,
    background: 'rgba(248,245,238,.98)',
    borderTop: '4px solid #111',
    borderBottom: '4px solid #111',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'column',
    color: '#111',
    padding: '0 54px',
    textAlign: 'center'
  }}>
    <div style={{fontSize, lineHeight: 1.12, fontWeight: 1000, maxWidth: 990}}>
      {lines.map((line, index) => (
        <div key={`${line}-${index}`} style={{whiteSpace: 'nowrap'}}>{line}</div>
      ))}
    </div>
    {en ? <div style={{fontSize: 24, lineHeight: 1.2, fontWeight: 700, marginTop: 10, color: '#333'}}>{en}</div> : null}
  </div>
  );
};

const SpeakerWindow = ({sourceVideo}) => (
  <div style={{
    position: 'absolute',
    left: 110,
    right: 110,
    top: 1060,
    height: 480,
    borderRadius: 34,
    overflow: 'hidden',
    background: '#000',
    border: `5px solid ${warm}`,
    boxShadow: '0 14px 36px rgba(0,0,0,.25)'
  }}>
    <OffthreadVideo src={staticFile(sourceVideo)} style={{width: '100%', height: '100%', objectFit: 'cover'}} volume={1} />
  </div>
);

const PlayerControls = ({currentMs, durationMs, speed = '1x'}) => {
  const progress = clamp(currentMs / durationMs, 0, 1);
  return (
    <>
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 118, background: '#050505', color: '#fff'}}>
        <div style={{position: 'absolute', left: 34, bottom: 26, width: 66, height: 66, borderRadius: 14, background: '#191919', display: 'grid', placeItems: 'center', fontSize: 34}}>×</div>
        <div style={{position: 'absolute', left: 285, bottom: 32, fontSize: 42}}>↺</div>
        <div style={{position: 'absolute', left: 512, bottom: 30, width: 58, height: 58}}>
          <div style={{position: 'absolute', left: 5, top: 0, width: 16, height: 58, borderRadius: 6, background: '#fff'}} />
          <div style={{position: 'absolute', right: 5, top: 0, width: 16, height: 58, borderRadius: 6, background: '#fff'}} />
        </div>
        <div style={{position: 'absolute', right: 285, bottom: 32, fontSize: 42}}>↻</div>
        <div style={{position: 'absolute', right: 34, bottom: 26, width: 78, height: 66, borderRadius: 14, background: '#191919', display: 'grid', placeItems: 'center', fontSize: 28, fontWeight: 900}}>{speed}</div>
      </div>
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 118, height: 10, background: 'rgba(0,0,0,.18)', overflow: 'hidden'}}>
        <div style={{
          height: '100%',
          width: `${progress * 100}%`,
          background: 'linear-gradient(90deg, #ffffff, #d7bd86)',
          boxShadow: '0 0 12px rgba(215,189,134,.85)',
          transition: 'width 80ms linear'
        }} />
        <div style={{
          position: 'absolute',
          left: `calc(${progress * 100}% - 5px)`,
          top: -4,
          width: 18,
          height: 18,
          borderRadius: 99,
          background: '#fff',
          boxShadow: '0 0 18px rgba(255,255,255,.9)'
        }} />
      </div>
    </>
  );
};

const CleanProgress = ({currentMs, durationMs}) => {
  const progress = clamp(currentMs / durationMs, 0, 1);
  return (
    <div style={{
      position: 'absolute',
      left: 54,
      right: 54,
      bottom: 34,
      height: 8,
      borderRadius: 999,
      background: 'rgba(17,17,17,.10)',
      overflow: 'hidden'
    }}>
      <div style={{
        width: `${progress * 100}%`,
        height: '100%',
        borderRadius: 999,
        background: 'linear-gradient(90deg, #111, #d7bd86)',
        boxShadow: '0 0 16px rgba(215,189,134,.68)'
      }} />
    </div>
  );
};

export const KnowledgeIpPackage = ({
  sourceVideo = 'workflow-inputs/knowledge-ip-test.mp4',
  materialTrackSrc = null,
  baseVideoSrc = null,
  durationMs = 172400,
  segments = defaultSegments,
  captions = []
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const currentMs = (frame / fps) * 1000;
  const active = activeSegment(segments, currentMs);
  const caption = activeCaption(captions, currentMs, active);
  const localFrame = Math.max(0, frame - Math.round(active.startMs / 1000 * fps));

  const baseSrc = baseVideoSrc ? staticFile(String(baseVideoSrc).replace(/^\/+/, '')) : null;

  return (
    <AbsoluteFill style={{fontFamily: 'PingFang SC, Microsoft YaHei, Arial, sans-serif', overflow: 'hidden', background: paper}}>
      {baseSrc ? (
        <OffthreadVideo src={baseSrc} style={{width: '100%', height: '100%', objectFit: 'cover'}} volume={1} />
      ) : (
        <>
          <PaperBackground />
          <MaterialScene active={active} localFrame={localFrame} materialTrackSrc={materialTrackSrc} />
          <SpeakerWindow sourceVideo={sourceVideo} />
        </>
      )}
      <TopTabs active={active} />
      <SubtitleBand caption={caption} />
      {baseSrc ? (
        <div style={{
          position: 'absolute',
          left: 110,
          right: 110,
          top: 1060,
          height: 480,
          borderRadius: 34,
          border: `5px solid ${warm}`,
          boxShadow: '0 14px 36px rgba(0,0,0,.25)',
          pointerEvents: 'none'
        }} />
      ) : null}
      <div style={{position: 'absolute', left: 0, right: 0, top: 1680, height: 180, background: 'linear-gradient(180deg, transparent, rgba(255,255,255,.24))'}} />
      <CleanProgress currentMs={currentMs} durationMs={durationMs} />
    </AbsoluteFill>
  );
};
