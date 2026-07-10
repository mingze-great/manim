import path from 'node:path';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {selectComposition, renderMedia, renderStill} from '@remotion/renderer';
import {browserExecutable} from '../browser.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
const mode = args[0] && !args[0].startsWith('--') ? args[0] : 'render';
const previewSecondsArg = args.find((arg, index) => index > 0 && !arg.startsWith('--'));
const previewSeconds = Number(previewSecondsArg || 0);
const propsArg = args.find((arg) => arg.startsWith('--props='));
const jobArg = args.find((arg) => arg.startsWith('--job='));
const jobId = jobArg ? jobArg.split('=').slice(1).join('=').trim() : process.env.KNOWLEDGE_IP_JOB_ID || 'knowledge-ip-test';
const propsPath = propsArg
  ? path.resolve(projectRoot, propsArg.split('=').slice(1).join('='))
  : path.join(projectRoot, `public/workflow-assets/${jobId}/remotion_props.json`);
const inputProps = JSON.parse(await fs.readFile(propsPath, 'utf8'));
inputProps.sourceVideo = inputProps.sourceVideo || `workflow-inputs/${jobId}.mp4`;
inputProps.materialTrackSrc = inputProps.materialTrackSrc || `workflow-assets/${jobId}/material_track.mp4`;
inputProps.durationMs = inputProps.durationMs || 172352;
if (previewSeconds > 0) inputProps.durationMs = previewSeconds * 1000;

console.log(`[knowledge-ip] mode=${mode}`);
console.log(`[knowledge-ip] props=${JSON.stringify({
  propsPath,
  jobId,
  sourceVideo: inputProps.sourceVideo,
  materialTrackSrc: inputProps.materialTrackSrc,
  durationMs: inputProps.durationMs,
  segments: Array.isArray(inputProps.segments) ? inputProps.segments.length : 0,
  captions: Array.isArray(inputProps.captions) ? inputProps.captions.length : 0,
})}`);

console.log('[knowledge-ip] bundling...');
const serveUrl = await bundle({
  entryPoint: path.join(projectRoot, 'src/main.jsx'),
  webpackOverride: (config) => config,
});
console.log(`[knowledge-ip] bundle=${serveUrl}`);

console.log('[knowledge-ip] selecting composition...');
const composition = await selectComposition({
  serveUrl,
  id: 'KnowledgeIpPackage',
  inputProps,
  browserExecutable,
});
console.log(`[knowledge-ip] composition frames=${composition.durationInFrames} fps=${composition.fps}`);

await fs.mkdir(path.join(projectRoot, 'renders'), {recursive: true});
await fs.mkdir(path.join(projectRoot, 'tmp/knowledge-ip-stills'), {recursive: true});

if (mode === 'stills') {
  const frames = [120, 900, 2100, 3900, Math.max(1, composition.durationInFrames - 90)];
  for (const frame of frames) {
    const output = path.join(projectRoot, 'tmp/knowledge-ip-stills', `frame-${frame}.png`);
    console.log(`[knowledge-ip] rendering still frame=${frame}`);
    await renderStill({
      composition,
      serveUrl,
      inputProps,
      frame,
      imageFormat: 'png',
      output,
      browserExecutable,
      chromiumOptions: {gl: 'angle'},
    });
    console.log(`still ${frame} ${output}`);
  }
  process.exit(0);
}

const outputLocation = path.join(projectRoot, 'renders', `${previewSeconds > 0 ? 'knowledge-ip-preview' : 'knowledge-ip-package-remotion'}-${Date.now()}.mp4`);
console.log(`[knowledge-ip] rendering media=${outputLocation}`);
await renderMedia({
  composition,
  serveUrl,
  codec: 'h264',
  audioCodec: 'aac',
  crf: 20,
  enforceAudioTrack: true,
  outputLocation,
  inputProps,
  concurrency: 1,
  browserExecutable,
  chromiumOptions: {gl: 'angle'},
  onProgress: ({progress, renderedFrames, encodedFrames}) => {
    const pct = Math.round(progress * 1000) / 10;
    if (renderedFrames % 90 === 0 || pct === 100) {
      console.log(`progress ${pct}% rendered=${renderedFrames} encoded=${encodedFrames}`);
    }
  },
});

console.log(`output ${outputLocation}`);
