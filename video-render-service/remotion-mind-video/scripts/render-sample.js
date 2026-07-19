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
  provider: 'auto',
  cosyVoiceSpeaker: '中文女'
});
const inputProps = {
  ...baseProps,
  audioScenes: audio.audioScenes,
  bgmSrc: audio.bgmSrc
};

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
  outputLocation: path.join(root, 'renders', 'sample.mp4'),
  inputProps,
  concurrency: 2,
  browserExecutable
});

console.log('Rendered renders/sample.mp4');
