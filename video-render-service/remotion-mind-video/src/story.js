const paletteSets = {
  aurora: {
    name: 'Aurora Graph',
    bg: '#080a12',
    ink: '#f7fbff',
    muted: '#9fb0c8',
    accent: '#27f4d2',
    accent2: '#ff4fd8',
    accent3: '#ffe76a',
    line: 'rgba(39,244,210,0.36)'
  },
  prism: {
    name: 'Prism Logic',
    bg: '#07070a',
    ink: '#fbf7ff',
    muted: '#aea7bd',
    accent: '#8cff5f',
    accent2: '#62a8ff',
    accent3: '#ff705d',
    line: 'rgba(140,255,95,0.32)'
  },
  signal: {
    name: 'Signal Room',
    bg: '#05080b',
    ink: '#f6fff9',
    muted: '#97aaa3',
    accent: '#00d1ff',
    accent2: '#ffcc33',
    accent3: '#ff4f6d',
    line: 'rgba(0,209,255,0.34)'
  }
};

const titleWords = ['核心', '为什么', '如何', '关键', '系统', '认知', '路径', '结构', '增长', '选择'];

export const styleOptions = Object.entries(paletteSets).map(([id, value]) => ({
  id,
  name: value.name
}));

export const defaultScript = `真正厉害的学习，不是把信息塞进脑子，而是建立一张可以不断生长的知识网络。

第一步，先抓住一个中心问题：我到底想解释什么？问题越清晰，后面的材料越容易自动归位。

第二步，把概念之间的关系画出来。因果、对比、递进、循环，这些关系会让知识从碎片变成结构。

最后，用一个具体场景检验它。能解释现实，能指导行动，才算真正被理解。`;

const sentenceSplit = /(?<=[。！？!?；;])\s*|\n+/g;

const clean = (value) => value.replace(/\s+/g, ' ').trim();

const pickTitle = (sentence, index) => {
  const cleaned = clean(sentence).replace(/[。！？!?；;,.，]/g, '');
  const parts = cleaned.split(/[:：,，、\s]/).filter(Boolean);
  const notable = parts.find((part) => titleWords.some((word) => part.includes(word)));
  if (notable) return notable.slice(0, 12);
  if (parts[0]) return parts[0].slice(0, 12);
  return `观点 ${index + 1}`;
};

const getKeywords = (sentence) => {
  const words = clean(sentence)
    .replace(/[。！？!?；;,.，:：]/g, ' ')
    .split(/\s+|、/)
    .filter((word) => word.length >= 2);
  const scored = [...new Set(words)]
    .sort((a, b) => b.length - a.length)
    .slice(0, 4);
  return scored.length ? scored : ['结构', '连接', '行动'];
};

export const scriptToStory = ({script, style = 'aurora', density = 1, audioScenes = [], bgmSrc = null}) => {
  const sentences = script
    .split(sentenceSplit)
    .map(clean)
    .filter(Boolean)
    .slice(0, 9);

  const safeSentences = sentences.length ? sentences : defaultScript.split(sentenceSplit).map(clean).filter(Boolean);
  const scenes = safeSentences.map((sentence, index) => {
    const audioScene = audioScenes.find((item) => item.index === index);
    const duration = audioScene?.durationInFrames ?? Math.max(95, Math.round((120 + sentence.length * 1.8) / density));
    return {
      id: `scene-${index + 1}`,
      index,
      title: pickTitle(sentence, index),
      body: sentence,
      keywords: getKeywords(sentence),
      duration,
      audioSrc: audioScene?.src ?? null,
      audioSeconds: audioScene?.seconds ?? null,
      mode: index === 0 ? 'origin' : index === safeSentences.length - 1 ? 'synthesis' : index % 3 === 1 ? 'branch' : 'flow'
    };
  });

  return {
    fps: 30,
    width: 1280,
    height: 720,
    style,
    palette: paletteSets[style] ?? paletteSets.aurora,
    title: scenes[0]?.title ?? 'MindFilm',
    scenes,
    bgmSrc,
    durationInFrames: scenes.reduce((total, scene) => total + scene.duration, 0)
  };
};
