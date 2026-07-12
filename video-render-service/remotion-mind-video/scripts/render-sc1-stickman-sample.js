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
for (const name of ['1.png', '10.png', '11.png', '12.png', '13.png', '14.png', '15.png', '16.png', '17.png', '18.png']) {
  await fs.copyFile(path.join(localMaterialDir, name), path.join(publicMaterialDir, name));
}
const materialUrl = (name) => `sc1-materials/${name}`;

const inputProps = {
  title: '沙雕法律竞赛题挑战你脑洞',
  brandTitle: '沙雕法律竞赛题挑战你脑洞',
  scenes: [
    {
      title: '来挑战一下你的脑抽程度吧',
      subtitleText: '来挑战一下你的脑抽程度吧',
      englishText: 'Come and challenge the degree of your asset-mindedness.',
      voiceText: '来挑战一下你的脑抽程度吧',
      keywords: ['法律竞赛', '脑抽挑战'],
      mode: 'judge',
      assetImages: [{src: materialUrl('1.png')}, {src: materialUrl('10.png')}],
      durationFrames: 96
    },
    {
      title: '喂警犬吃狗算什么行为？',
      subtitleText: '喂警犬吃狗算什么行为？',
      englishText: 'What kind of behavior is it to feed dogs to police dogs?',
      voiceText: '喂警犬吃狗算什么行为？',
      keywords: ['法律竞赛', '脑抽挑战', '性质题'],
      mode: 'wolf',
      assetImages: [{src: materialUrl('11.png')}, {src: materialUrl('12.png')}],
      durationFrames: 108
    },
    {
      title: '第二题父子题',
      subtitleText: '第二题父子题',
      englishText: 'The second parent-child question.',
      voiceText: '第二题父子题',
      keywords: ['法律定义', '作死行为'],
      mode: 'chase',
      assetImages: [{src: materialUrl('13.png')}, {src: materialUrl('14.png')}],
      durationFrames: 112
    },
    {
      title: '这只属于一般情况下',
      subtitleText: '这只属于一般情况下',
      englishText: 'This only applies under normal circumstances.',
      voiceText: '这只属于一般情况下',
      keywords: ['把握反抗', '拒捕袭警'],
      mode: 'police',
      assetImages: [{src: materialUrl('15.png')}, {src: materialUrl('16.png')}],
      durationFrames: 108
    },
    {
      title: '执行死刑时',
      subtitleText: '执行死刑时',
      englishText: 'At the time of execution of the death penalty.',
      voiceText: '执行死刑时',
      keywords: ['走位题', '不能要求'],
      mode: 'execution',
      assetImages: [{src: materialUrl('17.png')}, {src: materialUrl('18.png')}],
      durationFrames: 108
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
  const frames = [0, 75, 165, Math.max(0, composition.durationInFrames - 20)];
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
  enforceAudioTrack: true,
  outputLocation,
  inputProps,
  concurrency: 1,
  browserExecutable,
  chromiumOptions: {gl: 'angle'},
});
console.log(`output ${outputLocation}`);
