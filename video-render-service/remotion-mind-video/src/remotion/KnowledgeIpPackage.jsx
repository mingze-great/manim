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
const heitiFont = '"Noto Sans CJK SC", "Source Han Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif';

const activeSegment = (segments, currentMs) =>
  segments.find((item) => currentMs >= item.startMs && currentMs < item.endMs) || segments[segments.length - 1];

const activeCaption = (captions, currentMs) =>
  (captions || []).find((item) => currentMs >= item.startMs && currentMs < item.endMs) || null;

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

const buildTopTabs = (segments = [], providedTabs = []) => {
  if (Array.isArray(providedTabs) && providedTabs.length > 0) {
    return providedTabs.map((tab, index) => ({
      label: String(tab.label || tab.title || tab).trim(),
      startMs: Number(tab.startMs ?? segments[0]?.startMs ?? 0),
      endMs: Number(tab.endMs ?? segments[segments.length - 1]?.endMs ?? 0),
      index
    }));
  }

  const validSegments = segments.filter((segment) => Number.isFinite(Number(segment.startMs)) && Number.isFinite(Number(segment.endMs)));
  if (validSegments.length === 0) {
    return ['核心观点', '关键案例', '解决路径', '行动建议'].map((label, index) => ({label, startMs: index * 1000, endMs: (index + 1) * 1000, index}));
  }

  const groups = 4;
  const size = Math.ceil(validSegments.length / groups);
  return Array.from({length: groups}, (_, index) => {
    const group = validSegments.slice(index * size, (index + 1) * size);
    const fallback = validSegments[Math.min(index * size, validSegments.length - 1)];
    const anchor = group[0] || fallback;
    return {
      label: String(anchor.tabLabel || anchor.summary || anchor.title || `第${index + 1}节`).trim(),
      startMs: Number((group[0] || fallback).startMs),
      endMs: Number((group[group.length - 1] || fallback).endMs),
      index
    };
  });
};

const TopTabs = ({active, segments, currentMs, topTabs}) => {
  const tabs = buildTopTabs(segments, topTabs);
  const title = active.mainTitle || '时代机会';
  return (
    <div style={{
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      height: 178,
      background: 'rgba(248,245,238,.96)',
      borderBottom: '4px solid #111',
      color: ink,
      fontWeight: 900,
      zIndex: 5
    }}>
      <div style={{
        position: 'absolute',
        left: 0,
        right: 0,
        top: 0,
        height: 76,
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        borderBottom: '2px solid #111',
        fontSize: 34,
        lineHeight: 1
      }}>
        {tabs.map((tab) => {
          const isActive = currentMs >= tab.startMs && currentMs < tab.endMs;
          const label = String(tab.label || '').replace(/\s+/g, '').slice(0, 5);
          return (
          <div key={`${tab.label}-${tab.index}`} style={{
            display: 'grid',
            placeItems: 'center',
            borderRight: '2px solid #111',
            background: isActive ? 'rgba(215,189,134,.30)' : 'transparent',
            letterSpacing: 0,
            fontFamily: heitiFont,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'clip',
            padding: '0 8px'
          }}>{label}</div>
          );
        })}
      </div>
      <div style={{
        position: 'absolute',
        left: 0,
        right: 0,
        top: 76,
        height: 102,
        background: 'rgba(248,245,238,.99)',
        overflow: 'hidden'
      }}>
        <div style={{position: 'absolute', left: 22, top: 10, fontSize: 66, lineHeight: 1, fontWeight: 1000, color: '#111', fontFamily: heitiFont}}>《{title}》</div>
        <div style={{position: 'absolute', right: 24, top: 41, fontSize: 22, fontWeight: 850, color: '#222', fontFamily: heitiFont}}>知识分享 · 认知提升</div>
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
    top: 178,
    height: 504,
    overflow: 'hidden',
    background: '#050505',
    borderTop: '6px solid #111',
    borderBottom: '6px solid #111'
  };
  const materialSrc = materialTrackSrc || active.materialSrc || active.assetSrc || active.videoSrc || active.media?.src;
  const MaterialClip = () => {
    if (!materialSrc) return null;
    const src = String(materialSrc).startsWith('http') ? materialSrc : staticFile(String(materialSrc).replace(/^\/+/, ''));
    const segmentFrames = Math.max(1, Math.round(((active.endMs || 0) - (active.startMs || 0)) / 1000 * 30));
    return (
      <div style={{...common, background: '#111'}}>
        <div style={{
          position: 'absolute',
          inset: '22px 0',
          background: '#000',
          overflow: 'hidden'
        }}>
          <OffthreadVideo
            src={src}
            muted
            style={{
              width: '100%',
              height: '100%',
              objectFit: materialTrackSrc ? 'cover' : 'contain',
              background: '#000',
              filter: 'contrast(1.04) saturate(1.06)',
              transform: materialTrackSrc
                ? 'scale(1.015)'
                : `scale(${1.01 + enter * 0.025 + localFrame / segmentFrames * 0.025}) translate(${Math.sin(localFrame / 32) * 8}px, ${Math.cos(localFrame / 35) * 5}px)`
            }}
          />
        </div>
        <div style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          background: 'linear-gradient(180deg, rgba(0,0,0,.28) 0 22px, transparent 22px calc(100% - 22px), rgba(0,0,0,.30) calc(100% - 22px))'
        }} />
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
      case 'phone': {
        const titleLines = splitTwoLines(active.title || active.zh, 12).slice(0, 2);
        const bodyLines = splitTwoLines(active.zh, 15).slice(0, 2);
        return (
          <div style={{...common, background: 'linear-gradient(180deg, #dfe9ef, #f4efe3)'}}>
            <div style={{position: 'absolute', left: 315, top: 44, width: 450, height: 420, borderRadius: 44, background: '#101418', border: '12px solid #1e2022', boxShadow: '0 36px 70px rgba(0,0,0,.32)', transform: `translateY(${(1 - enter) * 80}px) scale(${0.92 + enter * 0.08})`}}>
              <div style={{position: 'absolute', left: 26, right: 26, top: 34, color: '#fff', fontSize: 31, fontWeight: 900}}>内容要点</div>
              <div style={{position: 'absolute', left: 28, right: 28, top: 100, minHeight: 78, borderRadius: 18, background: '#fff', color: '#111', fontSize: 25, padding: 18, fontWeight: 900, lineHeight: 1.18}}>{titleLines.map((line) => <div key={line}>{line}</div>)}</div>
              <div style={{position: 'absolute', left: 28, right: 28, top: 214, minHeight: 112, borderRadius: 20, background: '#fff4cf', color: '#111', fontSize: 26, lineHeight: 1.25, padding: 18, fontWeight: 900}}>{bodyLines.map((line) => <div key={line}>{line}</div>)}</div>
              <div style={{position: 'absolute', left: 120, right: 120, bottom: 28, height: 9, borderRadius: 99, background: '#fff'}} />
            </div>
          </div>
        );
      }
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
  if (!zh) return null;
  const lines = splitTwoLines(zh, 14).slice(0, 2);
  const fontSize = zh.length > 24 ? 50 : 60;
  return (
  <div style={{
    position: 'absolute',
    top: 682,
    left: 0,
    right: 0,
    height: 300,
    background: 'rgba(248,245,238,.98)',
    borderTop: '4px solid #111',
    borderBottom: '4px solid #111',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'column',
    color: '#111',
    padding: '0 78px',
    textAlign: 'center'
  }}>
    <div style={{
      fontSize,
      lineHeight: 1.18,
      fontWeight: 1000,
      maxWidth: 960,
      wordBreak: 'keep-all',
      overflowWrap: 'normal'
    }}>{lines.map((line) => <div key={line}>{line}</div>)}</div>
    {en ? <div style={{fontSize: 28, lineHeight: 1.15, fontWeight: 850, marginTop: 12, color: '#222'}}>{splitTwoLines(en, 42).slice(0, 2).map((line) => <div key={line}>{line}</div>)}</div> : null}
  </div>
  );
};

const SpeakerWindow = ({sourceVideo, crop = {scale: 1.22, y: -4}}) => (
  <div style={{
    position: 'absolute',
    left: 226,
    right: 226,
    top: 1112,
    height: 600,
    borderRadius: 58,
    overflow: 'hidden',
    background: '#000',
    border: `4px solid ${warm}`,
    boxShadow: '0 24px 58px rgba(0,0,0,.22)'
  }}>
    <OffthreadVideo
      src={staticFile(sourceVideo)}
      style={{
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        transform: `translateY(${crop.y || 0}px) scale(${crop.scale || 1})`,
        filter: 'contrast(1.02) saturate(1.02)'
      }}
      volume={1}
    />
    <div style={{
      position: 'absolute',
      inset: 0,
      borderRadius: 58,
      boxShadow: 'inset 0 0 0 1px rgba(255,255,255,.16), inset 0 -24px 54px rgba(0,0,0,.18)',
      pointerEvents: 'none'
    }} />
  </div>
);

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
  captions = [],
  speakerCrop = {scale: 1.22, y: -4},
  topTabs = []
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const currentMs = (frame / fps) * 1000;
  const active = activeSegment(segments, currentMs);
  const caption = activeCaption(captions, currentMs);
  const localFrame = Math.max(0, frame - Math.round(active.startMs / 1000 * fps));

  return (
    <AbsoluteFill style={{fontFamily: heitiFont, overflow: 'hidden', background: paper}}>
      <PaperBackground />
      <MaterialScene active={active} localFrame={localFrame} materialTrackSrc={materialTrackSrc} />
      <SpeakerWindow sourceVideo={sourceVideo} crop={speakerCrop} />
      <TopTabs active={active} segments={segments} currentMs={currentMs} topTabs={topTabs} />
      <SubtitleBand caption={caption} />
      <div style={{position: 'absolute', left: 0, right: 0, top: 982, height: 4, background: '#111'}} />
      <div style={{position: 'absolute', left: 0, right: 0, top: 1738, height: 150, background: 'linear-gradient(180deg, transparent, rgba(255,255,255,.26))'}} />
      <CleanProgress currentMs={currentMs} durationMs={durationMs} />
    </AbsoluteFill>
  );
};
