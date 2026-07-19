import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, '..');

const getArg = (name, fallback = null) => {
  const hit = process.argv.find((arg) => arg.startsWith(`--${name}=`));
  return hit ? hit.split('=').slice(1).join('=').trim() : fallback;
};

const jobId = getArg('job');
const sourceVideo = getArg('source');
const segmentsPath = getArg('segments');
const transcriptPath = getArg('transcript');
const topTabsPath = getArg('top-tabs');
const captionTranslationsPath = getArg('caption-translations');
const title = getArg('title', '知识分享');
const durationMsArg = Number(getArg('duration-ms', 0));
const allowRepeat = process.argv.includes('--allow-repeat-materials');

if (!jobId || !sourceVideo || !segmentsPath) {
  console.error('Usage: node scripts/prepare-knowledge-ip-job.js --job=<jobId> --source=<public-relative-video> --segments=<json> [--title=<title>] [--duration-ms=<ms>]');
  process.exit(1);
}

const readJson = async (file) => JSON.parse((await fs.readFile(path.resolve(file), 'utf8')).replace(/^\uFEFF/, ''));

const punctuation = /[。！？；.!?;]/;
const normalizeText = (value) => String(value || '').replace(/\s+/g, '').trim();

const sentenceSafeCaption = (segment) => {
  const zh = normalizeText(segment.captionZh || segment.caption || segment.title || segment.zh || segment.text);
  if (!zh) return null;

  // Never cut a no-punctuation sentence in the middle. Long content should be
  // summarized by the upstream script/LLM into captionZh/title instead.
  if (!punctuation.test(zh)) return zh;

  const sentences = zh
    .split(/(?<=[。！？；.!?;])/)
    .map((item) => item.trim())
    .filter(Boolean);
  return normalizeText(sentences.slice(0, 2).join(''));
};

const clampSegment = (item, index, previousEndMs) => {
  const startMs = Number(item.startMs ?? item.start ?? previousEndMs ?? 0);
  const endMs = Number(item.endMs ?? item.end ?? startMs + Number(item.durationMs || 5000));
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs <= startMs) {
    throw new Error(`Invalid segment timing at index ${index}`);
  }

  const captionZh = sentenceSafeCaption(item);
  const segmentTitle = normalizeText(item.title || captionZh || `第${index + 1}节`);
  return {
    id: item.id || `seg_${String(index + 1).padStart(2, '0')}`,
    startMs,
    endMs,
    tab: item.tab || ['身边的大儒', '古典大儒', '现代大儒', '英雄主义'][index % 4],
    title: segmentTitle,
    zh: normalizeText(item.zh || item.text || captionZh),
    en: item.en || item.captionEn || '',
    prompt: item.prompt || '',
    materialSrc: item.materialSrc || item.videoSrc || item.assetSrc || null,
    mainTitle: item.mainTitle || title
  };
};

const captionsFromTranscript = (transcript, translations = []) => {
  const transcripts = transcript?.transcripts || [];
  const sentences = transcripts[0]?.sentences || transcript?.sentences || [];
  const captions = [];
  const endPunctuation = new Set(['，', '。', '？', '！', '；', ',', '.', '?', '!', ';']);

  for (const sentence of sentences) {
    const words = Array.isArray(sentence.words) ? sentence.words : [];
    if (words.length === 0) {
      const text = normalizeText(sentence.text);
      if (text && Number.isFinite(Number(sentence.begin_time)) && Number.isFinite(Number(sentence.end_time))) {
        captions.push({startMs: Number(sentence.begin_time), endMs: Number(sentence.end_time), zh: text, text, en: ''});
      }
      continue;
    }

    let currentText = '';
    let startMs = null;
    let endMs = null;
    let hasPunctuation = false;

    const flush = () => {
      const text = normalizeText(currentText);
      if (text && startMs !== null && endMs !== null) {
        captions.push({startMs, endMs, zh: text, text, en: ''});
      }
      currentText = '';
      startMs = null;
      endMs = null;
      hasPunctuation = false;
    };

    for (const word of words) {
      const wordText = String(word.text || '');
      const punctuationMark = String(word.punctuation || '');
      if (!wordText) continue;
      if (startMs === null) startMs = Number(word.begin_time);
      endMs = Number(word.end_time);
      currentText += `${wordText}${punctuationMark}`;
      if (endPunctuation.has(punctuationMark)) {
        hasPunctuation = true;
        flush();
      }
    }

    // If a sentence has no punctuation, keep it together instead of cutting it
    // in the middle. This matches the "no mid-sentence cut" requirement.
    if (currentText && !hasPunctuation) flush();
  }

  return captions
    .filter((caption) => Number.isFinite(caption.startMs) && Number.isFinite(caption.endMs) && caption.endMs > caption.startMs)
    .sort((a, b) => a.startMs - b.startMs)
    .map((caption, index) => ({...caption, en: String(translations[index]?.en || translations[index] || '').trim()}));
};

const buildTopTabsFromSegments = (segments, providedTabs) => {
  if (Array.isArray(providedTabs) && providedTabs.length > 0) return providedTabs;
  const groups = 4;
  const size = Math.ceil(segments.length / groups);
  return Array.from({length: groups}, (_, index) => {
    const group = segments.slice(index * size, (index + 1) * size);
    const anchor = group[0] || segments[Math.min(index * size, segments.length - 1)];
    return {
      label: normalizeText(anchor?.tabLabel || anchor?.summary || anchor?.title || `第${index + 1}节`).slice(0, 8),
      startMs: Number((group[0] || anchor).startMs),
      endMs: Number((group[group.length - 1] || anchor).endMs)
    };
  });
};

const raw = await readJson(segmentsPath);
const sourceSegments = Array.isArray(raw) ? raw : raw.segments;
if (!Array.isArray(sourceSegments) || sourceSegments.length === 0) {
  throw new Error('Segments JSON must be an array or an object with a segments array.');
}

const segments = [];
let previousEndMs = 0;
for (let index = 0; index < sourceSegments.length; index += 1) {
  const normalized = clampSegment(sourceSegments[index], index, previousEndMs);
  previousEndMs = normalized.endMs;
  segments.push(normalized);
}

const missingMaterials = segments.filter((segment) => !segment.materialSrc);
if (missingMaterials.length > 0 && !allowRepeat) {
  throw new Error(`Missing materialSrc for ${missingMaterials.length} segment(s). Generate one AI material video per semantic group, or pass --allow-repeat-materials only for debugging.`);
}

let captions = [];
if (transcriptPath) {
  const captionTranslations = captionTranslationsPath ? await readJson(captionTranslationsPath) : [];
  captions = captionsFromTranscript(await readJson(transcriptPath), captionTranslations);
}
if (captions.length === 0) {
  captions = segments
    .map((segment) => ({
      startMs: segment.startMs,
      endMs: segment.endMs,
      zh: sentenceSafeCaption(segment),
      text: sentenceSafeCaption(segment),
      en: segment.en || ''
    }))
    .filter((caption) => caption.zh);
}

const durationMs = durationMsArg || Math.max(...segments.map((segment) => segment.endMs));
const providedTopTabs = topTabsPath ? await readJson(topTabsPath) : raw.topTabs;
const props = {
  sourceVideo,
  materialTrackSrc: getArg('material-track', null),
  durationMs,
  speakerCrop: {
    scale: Number(getArg('speaker-scale', 1.22)),
    y: Number(getArg('speaker-y', -4))
  },
  segments,
  topTabs: buildTopTabsFromSegments(segments, providedTopTabs),
  captions
};

const outDir = path.join(projectRoot, 'public/workflow-assets', jobId);
await fs.mkdir(outDir, {recursive: true});
await fs.writeFile(path.join(outDir, 'remotion_props.json'), `${JSON.stringify(props, null, 2)}\n`, 'utf8');

console.log(JSON.stringify({
  ok: true,
  jobId,
  propsPath: path.join(outDir, 'remotion_props.json'),
  segments: segments.length,
  captions: captions.length,
  durationMs
}, null, 2));
