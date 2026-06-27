import path from 'node:path';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import express from 'express';
import {bundle} from '@remotion/bundler';
import {ensureBrowser, renderMedia, selectComposition} from '@remotion/renderer';
import {scriptToStory} from './src/story.js';
import {browserExecutable} from './browser.js';
import {checkCosyVoice, ensureAudioDirs, listVoices, prepareAudioForStory} from './audio.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
const port = Number(process.env.PORT ?? 18787);

app.use(express.json({limit: '20mb'}));
app.use('/renders', express.static(path.join(__dirname, 'renders')));
app.use('/generated-audio', express.static(path.join(__dirname, 'public', 'generated-audio')));

const getBundle = async () => {
  return bundle({
    entryPoint: path.join(__dirname, 'src', 'main.jsx'),
    webpackOverride: (config) => config
  });
};

const renderMindVideo = async ({inputProps, filenamePrefix = 'mindfilm'}) => {
  const story = scriptToStory(inputProps);
  const serveUrl = await getBundle();
  const composition = await selectComposition({
    serveUrl,
    id: 'MindVideo',
    inputProps,
    browserExecutable
  });
  const filename = `${filenamePrefix}-${Date.now()}.mp4`;
  const outputLocation = path.join(__dirname, 'renders', filename);

  await fs.mkdir(path.dirname(outputLocation), {recursive: true});
  await renderMedia({
    composition,
    serveUrl,
    codec: 'h264',
    audioCodec: 'aac',
    enforceAudioTrack: true,
    outputLocation,
    inputProps,
    concurrency: 1,
    chromiumOptions: {
      gl: 'angle'
    },
    browserExecutable
  });

  return {
    url: `/renders/${filename}`,
    filename,
    durationInFrames: story.durationInFrames,
    seconds: Math.round((story.durationInFrames / story.fps) * 10) / 10
  };
};

app.post('/api/story', (req, res) => {
  const story = scriptToStory(req.body ?? {});
  res.json(story);
});

app.get('/api/voices', async (_req, res) => {
  const voices = await listVoices();
  res.json({voices});
});

app.get('/api/tts/status', async (_req, res) => {
  const cosyVoice = await checkCosyVoice();
  res.json({cosyVoice});
});

app.get('/api/health', async (_req, res) => {
  res.json({
    ok: true,
    service: 'remotion-mind-video',
    port,
    browserExecutable,
    requiresExternalAudio: true
  });
});

app.post('/api/browser/ensure', async (_req, res) => {
  try {
    await ensureBrowser({
      browserExecutable,
      chromeMode: 'headless-shell',
      logLevel: 'info'
    });
    res.json({ok: true, browserExecutable});
  } catch (error) {
    res.status(500).json({
      ok: false,
      message: error instanceof Error ? error.message : 'Browser install failed'
    });
  }
});

app.post('/api/render-project', async (req, res) => {
  try {
    const inputProps = {
      script: String(req.body?.script ?? ''),
      style: String(req.body?.style ?? 'dark_editorial'),
      contentType: String(req.body?.contentType ?? 'insight'),
      targetPlatform: String(req.body?.targetPlatform ?? 'douyin'),
      tone: String(req.body?.tone ?? 'professional'),
      pace: String(req.body?.pace ?? 'medium'),
      goal: String(req.body?.goal ?? ''),
      scenes: Array.isArray(req.body?.scenes) ? req.body.scenes : [],
      density: Number(req.body?.density ?? 1),
      audioScenes: Array.isArray(req.body?.audioScenes) ? req.body.audioScenes : [],
      bgmSrc: req.body?.bgmSrc ?? null
    };
    if (!inputProps.audioScenes.length) {
      res.status(400).json({ok: false, message: 'CosyVoice audioScenes are required'});
      return;
    }
    const result = await renderMindVideo({inputProps, filenamePrefix: 'mindfilm-cosyvoice'});
    res.json({
      ok: true,
      ...result,
      provider: 'remotion_external_audio'
    });
  } catch (error) {
    console.error(error);
    res.status(500).json({
      ok: false,
      message: error instanceof Error ? error.message : 'Render failed'
    });
  }
});

app.post('/api/render', async (req, res) => {
  try {
    await ensureAudioDirs();
    const baseProps = {
      script: String(req.body?.script ?? ''),
      style: String(req.body?.style ?? 'dark_editorial'),
      contentType: String(req.body?.contentType ?? 'insight'),
      targetPlatform: String(req.body?.targetPlatform ?? 'douyin'),
      tone: String(req.body?.tone ?? 'professional'),
      pace: String(req.body?.pace ?? 'medium'),
      goal: String(req.body?.goal ?? ''),
      scenes: Array.isArray(req.body?.scenes) ? req.body.scenes : [],
      density: Number(req.body?.density ?? 1)
    };
    const baseStory = scriptToStory(baseProps);
    const audio = await prepareAudioForStory({
      story: baseStory,
      style: baseProps.style,
      voice: String(req.body?.voice ?? ''),
      speechRate: Number(req.body?.speechRate ?? 0),
      withBgm: req.body?.withBgm !== false,
      provider: String(req.body?.provider ?? 'auto'),
      cosyVoiceSpeaker: String(req.body?.cosyVoiceSpeaker ?? '中文女')
    });
    const inputProps = {
      ...baseProps,
      audioScenes: audio.audioScenes,
      bgmSrc: audio.bgmSrc
    };
    const result = await renderMindVideo({inputProps});

    res.json({
      ok: true,
      ...result,
      audioJobId: audio.jobId,
      provider: audio.provider
    });
  } catch (error) {
    console.error(error);
    res.status(500).json({
      ok: false,
      message: error instanceof Error ? error.message : 'Render failed'
    });
  }
});

app.listen(port, '127.0.0.1', () => {
  console.log(`Render API listening on http://127.0.0.1:${port}`);
});
