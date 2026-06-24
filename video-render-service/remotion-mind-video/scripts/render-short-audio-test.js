import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {scriptToStory} from '../src/story.js';
import {browserExecutable} from '../browser.js';
import {ensureAudioDirs, prepareAudioForStory} from '../audio.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, '..');
const baseProps = {
  script: '第一句介绍问题。\n第二句解释原因。\n第三句给出行动。',
  style: 'signal',
  density: 1
};

await ensureAudioDirs();
const baseStory = scriptToStory(baseProps);
const audio = await prepareAudioForStory({
  story: baseStory,
  style: baseProps.style,
  speechRate: 0,
  withBgm: false
});
const inputProps = {
  ...baseProps,
  audioScenes: audio.audioScenes,
  bgmSrc: audio.bgmSrc
};
const story = scriptToStory(inputProps);

console.log(JSON.stringify({
  audioScenes: audio.audioScenes,
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
  outputLocation: path.join(root, 'renders', 'short-audio-test.mp4'),
  inputProps,
  concurrency: 2,
  browserExecutable
});

console.log('Rendered renders/short-audio-test.mp4');
