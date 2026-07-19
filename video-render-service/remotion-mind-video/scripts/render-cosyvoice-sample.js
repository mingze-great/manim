import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {defaultScript, scriptToStory} from '../src/story.js';
import {browserExecutable} from '../browser.js';
import {ensureAudioDirs, prepareAudioForStory} from '../audio.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, '..');
const baseProps = {
  script: defaultScript,
  style: 'aurora',
  density: 1.15
};

await ensureAudioDirs();
const baseStory = scriptToStory(baseProps);
const audio = await prepareAudioForStory({
  story: baseStory,
  style: baseProps.style,
  speechRate: 0,
  withBgm: true,
  provider: 'cosyvoice',
  cosyVoiceSpeaker: '中文女'
});

const inputProps = {
  ...baseProps,
  audioScenes: audio.audioScenes,
  bgmSrc: audio.bgmSrc
};
const story = scriptToStory(inputProps);

console.log(JSON.stringify({
  provider: audio.provider,
  audioScenes: audio.audioScenes.map((scene) => ({
    index: scene.index,
    seconds: scene.seconds,
    durationInFrames: scene.durationInFrames,
    provider: scene.provider
  })),
  durationInFrames: story.durationInFrames,
  seconds: story.durationInFrames / story.fps
}, null, 2));

const serveUrl = await bundle({
  entryPoint: path.join(root, 'src', 'main.jsx')
});

const composition = await selectComposition({
  serveUrl,
  id: 'MindVideo',
  inputProps,
  browserExecutable
});

await renderMedia({
  composition,
  serveUrl,
  codec: 'h264',
  outputLocation: path.join(root, 'renders', 'cosyvoice-sample.mp4'),
  inputProps,
  concurrency: 2,
  browserExecutable
});

console.log('Rendered renders/cosyvoice-sample.mp4');
