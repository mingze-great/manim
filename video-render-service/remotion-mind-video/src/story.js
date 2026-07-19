export const paletteSets = {
  dark_editorial: {
    name: 'Dark Editorial',
    bg: '#030303',
    panel: '#14110f',
    ink: '#f7f2e8',
    muted: '#8d8d8d',
    accent: '#ff4a1c',
    accent2: '#f7f2e8',
    accent3: '#54ffa9',
    line: 'rgba(255,74,28,0.34)'
  },
  clean_explainer: {
    name: 'Clean Explainer',
    bg: '#f6f3ea',
    panel: '#ffffff',
    ink: '#111111',
    muted: '#5f6368',
    accent: '#111111',
    accent2: '#ff6b2c',
    accent3: '#2f80ed',
    line: 'rgba(17,17,17,0.22)'
  },
  tech_blueprint: {
    name: 'Tech Blueprint',
    bg: '#031019',
    panel: '#071c2a',
    ink: '#eaffff',
    muted: '#88a8b8',
    accent: '#00d1ff',
    accent2: '#54ffa9',
    accent3: '#ffcc33',
    line: 'rgba(0,209,255,0.36)'
  },
  commerce_boost: {
    name: 'Commerce Boost',
    bg: '#090604',
    panel: '#1a0f09',
    ink: '#fff5e8',
    muted: '#c5a99a',
    accent: '#ff4a1c',
    accent2: '#ffd166',
    accent3: '#ffffff',
    line: 'rgba(255,74,28,0.38)'
  },
  lifestyle_magazine: {
    name: 'Lifestyle Magazine',
    bg: '#11100e',
    panel: '#f4eee2',
    ink: '#f4eee2',
    muted: '#a69d90',
    accent: '#e7d7bd',
    accent2: '#ffffff',
    accent3: '#b8ffdf',
    line: 'rgba(231,215,189,0.28)'
  },
  warm_healing: {
    name: 'Warm Healing',
    bg: '#120d0b',
    panel: '#241813',
    ink: '#fff3e4',
    muted: '#c6a795',
    accent: '#ffb38a',
    accent2: '#ffd9c7',
    accent3: '#f8e7a1',
    line: 'rgba(255,179,138,0.3)'
  },
  viral_pop: {
    name: 'Viral Pop',
    bg: '#050505',
    panel: '#161616',
    ink: '#ffffff',
    muted: '#b7b7b7',
    accent: '#ff2d55',
    accent2: '#ffe600',
    accent3: '#00f5ff',
    line: 'rgba(255,45,85,0.34)'
  },
  data_report: {
    name: 'Data Report',
    bg: '#06110d',
    panel: '#0d1c15',
    ink: '#effff7',
    muted: '#8ab2a0',
    accent: '#54ffa9',
    accent2: '#9cfffa',
    accent3: '#ffcc33',
    line: 'rgba(84,255,169,0.32)'
  },
  news_flash: {
    name: 'News Flash',
    bg: '#09090b',
    panel: '#171717',
    ink: '#ffffff',
    muted: '#b8b8b8',
    accent: '#ff1f3d',
    accent2: '#2f80ed',
    accent3: '#ffffff',
    line: 'rgba(255,31,61,0.38)'
  },
  premium_black_gold: {
    name: 'Premium Black Gold',
    bg: '#050403',
    panel: '#18110a',
    ink: '#fff7e6',
    muted: '#b89d6a',
    accent: '#d7a948',
    accent2: '#fff0b7',
    accent3: '#ffffff',
    line: 'rgba(215,169,72,0.36)'
  },
  aurora: {
    name: 'Aurora Graph',
    bg: '#080a12',
    panel: '#111827',
    ink: '#f7fbff',
    muted: '#9fb0c8',
    accent: '#27f4d2',
    accent2: '#ff4fd8',
    accent3: '#ffe76a',
    line: 'rgba(39,244,210,0.36)'
  }
};

const typeModes = {
  product_seed: ['commerce_hook', 'compare_split', 'benefit_stack', 'use_case', 'cta_burst'],
  teaching: ['question_board', 'step_board', 'diagram_flow', 'example_card', 'summary_cards'],
  insight: ['editorial_title', 'quote_wall', 'contrast_cards', 'insight_card', 'punchline'],
  lifestyle: ['magazine_cover', 'photo_strip', 'soft_caption', 'detail_moment', 'gentle_close'],
  mood: ['soft_quote', 'breathing_cards', 'emotion_wave', 'gentle_close'],
  briefing: ['breaking_headline', 'timeline', 'conflict_map', 'data_report', 'discussion_prompt'],
  creator_talk: ['hook_flash', 'creator_caption', 'experience_card', 'big_subtitle', 'follow_prompt'],
  case_study: ['case_context', 'decision_map', 'metric_wall', 'method_card', 'summary_cards']
};

const typeKeywords = {
  product_seed: ['痛点', '卖点', '场景', '下单'],
  teaching: ['问题', '原理', '步骤', '总结'],
  insight: ['观点', '逻辑', '案例', '结论'],
  lifestyle: ['日常', '细节', '感受', '分享'],
  mood: ['共鸣', '场景', '情绪', '建议'],
  briefing: ['事件', '矛盾', '判断', '讨论'],
  creator_talk: ['人设', '经验', '观点', '关注'],
  case_study: ['背景', '决策', '结果', '方法']
};

export const styleOptions = Object.entries(paletteSets).map(([id, value]) => ({id, name: value.name}));

export const defaultScript = '把一个复杂想法拆成三个画面。第一步抓住问题，第二步给出方法，第三步留下行动理由。';

const sentenceSplit = /(?<=[。？！?!；;])\s*|\n+/g;
const clean = (value) => String(value || '').replace(/\s+/g, ' ').trim();

const compactDisplayText = (value, fallback = '') => {
  const text = clean(value).replace(/^[，,。！？!、；;：:\s]+|[，,。！？!、；;：:\s]+$/g, '');
  if (!text) return clean(fallback);
  const parts = text
    .split(/[\s，,。！？!、；;：:]+/g)
    .map((item) => item.trim())
    .filter(Boolean);
  const preferred = parts.find((item) => item.length >= 4 && item.length <= 18);
  const source = preferred || parts[0] || text;
  return source.length <= 18 ? source : `${source.slice(0, 18).replace(/[，,。！？!、；;：:\s]+$/g, '')}...`;
};

const getKeywords = (sentence, contentType) => {
  const words = clean(sentence)
    .replace(/[。？！?!；;,.，、：:]/g, ' ')
    .split(/\s+/)
    .filter((word) => word.length >= 2);
  const scored = [...new Set(words.map((word) => word.length > 12 ? word.slice(0, 12) : word))]
    .sort((a, b) => b.length - a.length)
    .slice(0, 4);
  return scored.length ? scored : (typeKeywords[contentType] ?? ['画面', '节奏', '结论']);
};

const getDuration = ({audioScene, sentence, density, pace}) => {
  if (audioScene?.durationInFrames) return audioScene.durationInFrames;
  const paceFactor = pace === 'fast' ? 0.78 : pace === 'slow' ? 1.18 : 1;
  return Math.max(82, Math.round(((120 + sentence.length * 1.9) * paceFactor) / density));
};

const normalizeScene = ({item, index, modes, contentType}) => {
  const voiceText = clean(item.voiceText || item.body || item.text || item.subtitleText || '');
  const displayText = compactDisplayText(item.displayText || item.subtitleText || item.body || item.text || voiceText, voiceText);
  const mode = item.mode || item.sceneType || modes[index % modes.length];
  const keywords = Array.isArray(item.keywords) && item.keywords.length ? item.keywords : getKeywords(displayText || voiceText, contentType);
  return {
    text: voiceText,
    voiceText,
    displayText,
    openingTitle: clean(item.openingTitle || ''),
    title: clean(item.title || item.headline || '') || null,
    mode,
    keywords,
    durationFrames: item.durationFrames || null,
    intent: item.intent || '',
    cta: item.cta || '',
    transition: item.transition || 'cut',
    camera: item.camera || 'cinematic_push',
    layout: item.layout || '',
    layoutVariant: item.layoutVariant || '',
    effect: item.effect || '',
    intensity: item.intensity || 'high',
    energyPattern: item.energyPattern || '',
    assetPrompt: item.assetPrompt || '',
    media: item.media || null,
    audioSrc: item.audioSrc || item.audio?.src || null
  };
};

export const scriptToStory = ({
  script,
  style = 'dark_editorial',
  density = 1,
  scenes: providedScenes = [],
  audioScenes = [],
  bgmSrc = null,
  contentType = 'insight',
  pace = 'medium',
  tone = 'professional',
  targetPlatform = 'douyin',
  goal = ''
}) => {
  const modes = typeModes[contentType] ?? typeModes.insight;
  const normalizedScenes = Array.isArray(providedScenes) && providedScenes.length
    ? providedScenes.map((item, index) => normalizeScene({item, index, modes, contentType})).filter((item) => item.text)
    : [];

  const sentences = normalizedScenes.length ? [] : clean(script)
    .split(sentenceSplit)
    .map(clean)
    .filter(Boolean)
    .slice(0, targetPlatform === 'bilibili' ? 8 : 5);

  const safeSentences = normalizedScenes.length
    ? normalizedScenes
    : (sentences.length ? sentences : defaultScript.split(sentenceSplit).map(clean).filter(Boolean));

  const scenes = safeSentences.map((sceneInput, index) => {
    const fromBackend = typeof sceneInput === 'object';
    const sentence = fromBackend ? (sceneInput.voiceText || sceneInput.text) : sceneInput;
    const displayText = fromBackend
      ? compactDisplayText(sceneInput.displayText || sceneInput.subtitleText || sceneInput.title || sentence, sentence)
      : sentence;
    const audioScene = audioScenes.find((item) => item.index === index);
    const duration = fromBackend && sceneInput.durationFrames
      ? sceneInput.durationFrames
      : getDuration({audioScene, sentence, density, pace});
    const mode = fromBackend && sceneInput.mode ? sceneInput.mode : modes[index % modes.length];
    return {
      id: `scene-${index + 1}`,
      index,
      title: fromBackend && sceneInput.title ? sceneInput.title : (typeKeywords[contentType]?.[index] ?? `Scene ${index + 1}`),
      openingTitle: fromBackend ? (sceneInput.openingTitle || '') : '',
      body: displayText,
      voiceText: sentence,
      subtitleText: displayText,
      keywords: fromBackend && sceneInput.keywords ? sceneInput.keywords : getKeywords(displayText, contentType),
      duration,
      audioSrc: audioScene?.src ?? (fromBackend ? sceneInput.audioSrc : null),
      audioSeconds: audioScene?.seconds ?? null,
      mode,
      intent: fromBackend ? sceneInput.intent : '',
      cta: fromBackend ? sceneInput.cta : '',
      transition: fromBackend ? sceneInput.transition : 'cut',
      camera: fromBackend ? sceneInput.camera : 'cinematic_push',
      layout: fromBackend ? sceneInput.layout : style,
      layoutVariant: fromBackend ? sceneInput.layoutVariant : '',
      effect: fromBackend ? sceneInput.effect : '',
      intensity: fromBackend ? (sceneInput.intensity || 'high') : 'high',
      energyPattern: fromBackend ? sceneInput.energyPattern : '',
      assetPrompt: fromBackend ? sceneInput.assetPrompt : '',
      media: fromBackend ? sceneInput.media : null
    };
  });

  return {
    fps: 30,
    width: 1280,
    height: 720,
    style,
    contentType,
    tone,
    targetPlatform,
    goal,
    palette: paletteSets[style] ?? paletteSets.dark_editorial,
    title: scenes[0]?.title ?? 'AI Video Studio',
    scenes,
    bgmSrc,
    durationInFrames: scenes.reduce((total, scene) => total + scene.duration, 0)
  };
};
