import path from 'node:path';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {selectComposition, renderMedia, renderStill} from '@remotion/renderer';
import {browserExecutable} from '../browser.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, '..');
const propsPath = path.join(projectRoot, 'public/workflow-assets/knowledge-ip-test/remotion_props.json');
const inputProps = JSON.parse(await fs.readFile(propsPath, 'utf8'));
inputProps.sourceVideo = inputProps.sourceVideo || 'workflow-inputs/knowledge-ip-test-cfr.mp4';
inputProps.materialTrackSrc = inputProps.materialTrackSrc || 'workflow-assets/knowledge-ip-test/material_track.mp4';
inputProps.baseVideoSrc = inputProps.baseVideoSrc || 'workflow-assets/knowledge-ip-test/base_track.mp4';
inputProps.durationMs = inputProps.durationMs || 172352;

console.log(`[knowledge-ip] mode=${process.argv[2] || 'render'}`);
console.log(`[knowledge-ip] props=${JSON.stringify({
  sourceVideo: inputProps.sourceVideo,
  materialTrackSrc: inputProps.materialTrackSrc,
  baseVideoSrc: inputProps.baseVideoSrc,
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

const mode = process.argv[2] || 'render';
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

const outputLocation = path.join(projectRoot, 'renders', `knowledge-ip-package-remotion-${Date.now()}.mp4`);
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
