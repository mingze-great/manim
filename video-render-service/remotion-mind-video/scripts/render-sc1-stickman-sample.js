import path from 'node:path';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {selectComposition, renderMedia, renderStill} from '@remotion/renderer';
import {browserExecutable} from '../browser.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
const mode = args[0] || 'stills';
const previewSeconds = Number(args[1] || 0);
const localMaterialDir = process.env.SC1_MATERIAL_LIBRARY_PATH || 'E:\\ai\\cankao\\sucai';
const publicMaterialDir = path.join(projectRoot, 'public', 'sc1-materials');
await fs.mkdir(publicMaterialDir, {recursive: true});
for (const name of ['17.png', '18.png', '24.png', '26.png', '29.png', '31.png', '39.png', '43.png']) {
  await fs.copyFile(path.join(localMaterialDir, name), path.join(publicMaterialDir, name));
}
const materialUrl = (name) => `sc1-materials/${name}`;

const inputProps = {
  title: '\u6c99\u96d5\u6cd5\u5f8b\u7ade\u8d5b\u9898',
  brandTitle: '\u6c99\u96d5\u6cd5\u5f8b\u7ade\u8d5b\u9898',
  scenes: [
    {
      title: '\u5148\u522b\u6025\u7740\u4e0b\u7ed3\u8bba',
      subtitleText: '\u5148\u522b\u6025\u7740\u4e0b\u7ed3\u8bba\uff0c\u771f\u6b63\u5173\u952e\u7684\u662f\u628a\u884c\u4e3a\u3001\u5bf9\u8c61\u548c\u540e\u679c\u5206\u5f00\u770b\u3002',
      englishText: 'Do not rush to a conclusion. Separate the action, the target and the consequence.',
      voiceText: '\u5148\u522b\u6025\u7740\u4e0b\u7ed3\u8bba\uff0c\u771f\u6b63\u5173\u952e\u7684\u662f\u628a\u884c\u4e3a\u3001\u5bf9\u8c61\u548c\u540e\u679c\u5206\u5f00\u770b\u3002',
      keywords: ['\u884c\u4e3a\u6027\u8d28', '\u5bf9\u8c61\u8fb9\u754c'],
      mode: 'judge',
      segments: [
        {
          text: '\u5148\u522b\u6025\u7740\u4e0b\u7ed3\u8bba\uff0c\u771f\u6b63\u5173\u952e\u7684\u662f\u628a\u884c\u4e3a\u5206\u5f00\u770b',
          englishText: 'Do not rush to a conclusion. First separate the action.',
          summaryLabel: '\u884c\u4e3a\u6027\u8d28',
          enterDirection: 'left',
          startRatio: 0,
          endRatio: 0.52,
          captionCues: [
            {text: '\u5148\u522b\u6025\u7740\u4e0b\u7ed3\u8bba', englishText: 'Do not rush to a conclusion.'},
            {text: '\u771f\u6b63\u5173\u952e\u662f\u628a\u884c\u4e3a\u5206\u5f00\u770b', englishText: 'The key is to separate the action.'}
          ]
        },
        {
          text: '\u518d\u628a\u5bf9\u8c61\u548c\u540e\u679c\u5206\u5f00\u770b',
          englishText: 'Then separate the target and the consequence.',
          summaryLabel: '\u5bf9\u8c61\u8fb9\u754c',
          enterDirection: 'right',
          startRatio: 0.52,
          endRatio: 1,
          captionCues: [
            {text: '\u518d\u770b\u5bf9\u8c61\u662f\u8c01', englishText: 'Then check who the target is.'},
            {text: '\u6700\u540e\u770b\u5b83\u9020\u6210\u4ec0\u4e48\u540e\u679c', englishText: 'Finally check what consequence it causes.'}
          ]
        }
      ],
      assetImages: [
        {src: materialUrl('29.png'), fileName: '29.png', segmentIndex: 0, summaryLabel: '\u884c\u4e3a\u6027\u8d28', enterDirection: 'left'},
        {src: materialUrl('43.png'), fileName: '43.png', segmentIndex: 1, summaryLabel: '\u5bf9\u8c61\u8fb9\u754c', enterDirection: 'right'}
      ],
      durationFrames: 150
    },
    {
      title: '\u5224\u65ad\u8981\u770b\u89c4\u5219\u8fb9\u754c',
      subtitleText: '\u5982\u679c\u53ea\u770b\u8868\u9762\uff0c\u4f60\u4f1a\u89c9\u5f97\u8fd9\u53ea\u662f\u4e00\u4e2a\u666e\u901a\u9009\u62e9\uff1b\u4f46\u653e\u5230\u89c4\u5219\u8bed\u5883\u91cc\uff0c\u6027\u8d28\u5c31\u5b8c\u5168\u4e0d\u540c\u3002',
      englishText: 'If you only look at the surface, it seems ordinary. Inside the rule context, the nature changes.',
      voiceText: '\u5982\u679c\u53ea\u770b\u8868\u9762\uff0c\u4f60\u4f1a\u89c9\u5f97\u8fd9\u53ea\u662f\u4e00\u4e2a\u666e\u901a\u9009\u62e9\uff1b\u4f46\u653e\u5230\u89c4\u5219\u8bed\u5883\u91cc\uff0c\u6027\u8d28\u5c31\u5b8c\u5168\u4e0d\u540c\u3002',
      keywords: ['\u8868\u9762\u5224\u65ad', '\u89c4\u5219\u8fb9\u754c'],
      mode: 'casefile',
      assetImages: [
        {src: materialUrl('17.png'), fileName: '17.png', segmentIndex: 0, summaryLabel: '\u8868\u9762\u5224\u65ad', enterDirection: 'top'},
        {src: materialUrl('18.png'), fileName: '18.png', segmentIndex: 1, summaryLabel: '\u89c4\u5219\u8fb9\u754c', enterDirection: 'bottom'}
      ],
      durationFrames: 150
    }
  ]
};

if (previewSeconds > 0) {
  let cursor = 0;
  inputProps.scenes = inputProps.scenes
    .map((scene) => {
      const next = {...scene};
      cursor += next.durationFrames;
      return next;
    })
    .filter(() => cursor / 30 <= previewSeconds + 3);
}

console.log('[sc1] bundling...');
const serveUrl = await bundle({
  entryPoint: path.join(projectRoot, 'src/main.jsx'),
  webpackOverride: (config) => config,
});

const composition = await selectComposition({
  serveUrl,
  id: 'Sc1StickmanVideo',
  inputProps,
  browserExecutable,
});

await fs.mkdir(path.join(projectRoot, 'renders'), {recursive: true});
await fs.mkdir(path.join(projectRoot, 'tmp/sc1-stills'), {recursive: true});

if (mode === 'stills') {
  const frames = [8, 58, 98, 142, Math.max(0, composition.durationInFrames - 24)];
  for (const frame of [...new Set(frames.map((item) => Math.min(item, composition.durationInFrames - 1)))]) {
    const output = path.join(projectRoot, 'tmp/sc1-stills', `frame-${frame}.png`);
    console.log(`[sc1] still frame=${frame} ${output}`);
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
  }
  process.exit(0);
}

const outputLocation = path.join(projectRoot, 'renders', `sc1-stickman-sample-${Date.now()}.mp4`);
console.log(`[sc1] rendering ${outputLocation}`);
await renderMedia({
  composition,
  serveUrl,
  codec: 'h264',
  audioCodec: 'aac',
  inputProps,
  outputLocation,
  browserExecutable,
  chromiumOptions: {gl: 'angle'},
});
console.log(`[sc1] done ${outputLocation}`);
