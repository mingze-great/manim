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
const title = getArg('title', '知识分享');
const durationMsArg = Number(getArg('duration-ms', 0));
const allowRepeat = process.argv.includes('--allow-repeat-materials');

if (!jobId || !sourceVideo || !segmentsPath) {
  console.error('Usage: node scripts/prepare-knowledge-ip-job.js --job=<jobId> --source=<public-relative-video> --segments=<json> [--title=<title>] [--duration-ms=<ms>]');
  process.exit(1);
}

const readJson = async (file) => JSON.parse(await fs.readFile(path.resolve(file), 'utf8'));

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

const captions = segments
  .map((segment) => ({
    startMs: segment.startMs,
    endMs: segment.endMs,
    zh: sentenceSafeCaption(segment),
    text: sentenceSafeCaption(segment),
    en: segment.en || ''
  }))
  .filter((caption) => caption.zh);

const durationMs = durationMsArg || Math.max(...segments.map((segment) => segment.endMs));
const props = {
  sourceVideo,
  materialTrackSrc: getArg('material-track', null),
  durationMs,
  speakerCrop: {
    scale: Number(getArg('speaker-scale', 1.22)),
    y: Number(getArg('speaker-y', -4))
  },
  segments,
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
