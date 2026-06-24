import fs from 'node:fs/promises';
import fsSync from 'node:fs';
import path from 'node:path';
import {execFile} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {promisify} from 'node:util';

const execFileAsync = promisify(execFile);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(__dirname, 'public');
const generatedDir = path.join(publicDir, 'generated-audio');
const powershell = 'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe';
const cosyVoiceBaseUrl = process.env.COSYVOICE_URL ?? 'http://127.0.0.1:50000';

const safeSegment = (value) => String(value).replace(/[^a-zA-Z0-9_-]/g, '-');

export const listVoices = async () => {
  try {
    const {stdout} = await execFileAsync(powershell, [
      '-NoProfile',
      '-ExecutionPolicy',
      'Bypass',
      '-File',
      path.join(__dirname, 'scripts', 'list-sapi-voices.ps1')
    ], {encoding: 'utf8', windowsHide: true});
    const parsed = JSON.parse(stdout || '[]');
    return Array.isArray(parsed) ? parsed : [parsed];
  } catch {
    return [];
  }
};

export const getWavDuration = async (filePath) => {
  const buffer = await fs.readFile(filePath);
  if (buffer.toString('ascii', 0, 4) !== 'RIFF' || buffer.toString('ascii', 8, 12) !== 'WAVE') {
    throw new Error(`Not a WAV file: ${filePath}`);
  }

  let offset = 12;
  let byteRate = 0;
  let dataSize = 0;

  while (offset + 8 <= buffer.length) {
    const id = buffer.toString('ascii', offset, offset + 4);
    const size = buffer.readUInt32LE(offset + 4);
    const chunkStart = offset + 8;

    if (id === 'fmt ') {
      byteRate = buffer.readUInt32LE(chunkStart + 8);
    }

    if (id === 'data') {
      dataSize = size;
      break;
    }

    offset = chunkStart + size + (size % 2);
  }

  if (!byteRate || !dataSize) {
    throw new Error(`Could not read WAV duration: ${filePath}`);
  }

  return dataSize / byteRate;
};

const synthesizeScene = async ({text, outPath, textPath, voice, speechRate}) => {
  await fs.writeFile(textPath, text, 'utf8');
  await execFileAsync(powershell, [
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    path.join(__dirname, 'scripts', 'sapi-tts.ps1'),
    '-TextPath',
    textPath,
    '-OutPath',
    outPath,
    '-VoiceName',
    voice ?? '',
    '-Rate',
    String(speechRate ?? 0)
  ], {
    encoding: 'utf8',
    windowsHide: true,
    timeout: 120000
  });
};

const writeUInt16 = (buffer, offset, value) => buffer.writeUInt16LE(value, offset);
const writeUInt32 = (buffer, offset, value) => buffer.writeUInt32LE(value, offset);

const pcmToWav = ({pcm, sampleRate = 22050, channels = 1, bitsPerSample = 16}) => {
  const dataSize = pcm.length;
  const bytesPerSample = bitsPerSample / 8;
  const buffer = Buffer.alloc(44 + dataSize);

  buffer.write('RIFF', 0);
  writeUInt32(buffer, 4, 36 + dataSize);
  buffer.write('WAVE', 8);
  buffer.write('fmt ', 12);
  writeUInt32(buffer, 16, 16);
  writeUInt16(buffer, 20, 1);
  writeUInt16(buffer, 22, channels);
  writeUInt32(buffer, 24, sampleRate);
  writeUInt32(buffer, 28, sampleRate * channels * bytesPerSample);
  writeUInt16(buffer, 32, channels * bytesPerSample);
  writeUInt16(buffer, 34, bitsPerSample);
  buffer.write('data', 36);
  writeUInt32(buffer, 40, dataSize);
  pcm.copy(buffer, 44);

  return buffer;
};

const ensureWavBuffer = (buffer) => {
  const isWav = buffer.toString('ascii', 0, 4) === 'RIFF' && buffer.toString('ascii', 8, 12) === 'WAVE';
  return isWav ? buffer : pcmToWav({pcm: buffer});
};

const synthesizeWithCosyVoice = async ({text, outPath, voice = '中文女'}) => {
  const formData = new FormData();
  formData.append('tts_text', text);
  formData.append('spk_id', voice || '中文女');

  const response = await fetch(`${cosyVoiceBaseUrl.replace(/\/$/, '')}/inference_sft`, {
    method: 'POST',
    body: formData,
    signal: AbortSignal.timeout(120000)
  });

  if (!response.ok) {
    throw new Error(`CosyVoice failed ${response.status}: ${await response.text()}`);
  }

  const audioBuffer = Buffer.from(await response.arrayBuffer());
  await fs.writeFile(outPath, ensureWavBuffer(audioBuffer));
};

export const checkCosyVoice = async () => {
  try {
    const response = await fetch(`${cosyVoiceBaseUrl.replace(/\/$/, '')}/docs`, {
      method: 'GET',
      signal: AbortSignal.timeout(2000)
    });
    return {
      ok: response.ok,
      baseUrl: cosyVoiceBaseUrl
    };
  } catch (error) {
    return {
      ok: false,
      baseUrl: cosyVoiceBaseUrl,
      message: error instanceof Error ? error.message : 'CosyVoice unavailable'
    };
  }
};

export const createBackgroundBed = async ({outPath, durationSeconds, style = 'aurora'}) => {
  const sampleRate = 44100;
  const channels = 2;
  const bitsPerSample = 16;
  const bytesPerSample = bitsPerSample / 8;
  const totalSamples = Math.max(1, Math.ceil(durationSeconds * sampleRate));
  const dataSize = totalSamples * channels * bytesPerSample;
  const buffer = Buffer.alloc(44 + dataSize);
  const presets = {
    aurora: [110, 220, 329.63],
    prism: [98, 196, 293.66],
    signal: [130.81, 261.63, 392]
  };
  const freqs = presets[style] ?? presets.aurora;

  buffer.write('RIFF', 0);
  writeUInt32(buffer, 4, 36 + dataSize);
  buffer.write('WAVE', 8);
  buffer.write('fmt ', 12);
  writeUInt32(buffer, 16, 16);
  writeUInt16(buffer, 20, 1);
  writeUInt16(buffer, 22, channels);
  writeUInt32(buffer, 24, sampleRate);
  writeUInt32(buffer, 28, sampleRate * channels * bytesPerSample);
  writeUInt16(buffer, 32, channels * bytesPerSample);
  writeUInt16(buffer, 34, bitsPerSample);
  buffer.write('data', 36);
  writeUInt32(buffer, 40, dataSize);

  for (let i = 0; i < totalSamples; i += 1) {
    const t = i / sampleRate;
    const fadeIn = Math.min(1, t / 2.2);
    const fadeOut = Math.min(1, (durationSeconds - t) / 2.4);
    const env = Math.max(0, Math.min(fadeIn, fadeOut));
    const pulse = 0.68 + Math.sin(t * Math.PI * 0.5) * 0.12;
    const sample =
      Math.sin(Math.PI * 2 * freqs[0] * t) * 0.28 +
      Math.sin(Math.PI * 2 * freqs[1] * t) * 0.16 +
      Math.sin(Math.PI * 2 * freqs[2] * t) * 0.08;
    const value = Math.max(-1, Math.min(1, sample * env * pulse * 0.22));
    const int = Math.round(value * 32767);
    const pos = 44 + i * channels * bytesPerSample;
    buffer.writeInt16LE(int, pos);
    buffer.writeInt16LE(int, pos + 2);
  }

  await fs.writeFile(outPath, buffer);
};

export const prepareAudioForStory = async ({
  story,
  style,
  voice,
  speechRate = 0,
  withBgm = true,
  provider = 'auto',
  cosyVoiceSpeaker = '中文女'
}) => {
  const jobId = `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  const jobDir = path.join(generatedDir, safeSegment(jobId));
  await fs.mkdir(jobDir, {recursive: true});

  const audioScenes = [];
  for (const scene of story.scenes) {
    const base = `scene-${String(scene.index + 1).padStart(2, '0')}`;
    const textPath = path.join(jobDir, `${base}.txt`);
    const outPath = path.join(jobDir, `${base}.wav`);
    let usedProvider = provider;
    if (provider === 'cosyvoice' || provider === 'auto') {
      try {
        await synthesizeWithCosyVoice({
          text: scene.body,
          outPath,
          voice: cosyVoiceSpeaker
        });
        usedProvider = 'cosyvoice';
      } catch (error) {
        if (provider === 'cosyvoice') {
          throw error;
        }
        usedProvider = 'sapi';
      }
    }

    if (usedProvider === 'sapi') {
      await synthesizeScene({
        text: scene.body,
        outPath,
        textPath,
        voice,
        speechRate
      });
    }

    const seconds = await getWavDuration(outPath);
    audioScenes.push({
      index: scene.index,
      src: `generated-audio/${jobId}/${base}.wav`,
      seconds,
      durationInFrames: Math.max(75, Math.ceil(seconds * story.fps) + 15),
      provider: usedProvider
    });
  }

  const totalSeconds = audioScenes.reduce((sum, scene) => sum + scene.durationInFrames / story.fps, 0);
  let bgmSrc = null;
  if (withBgm) {
    const bgmPath = path.join(jobDir, 'ambient-bed.wav');
    await createBackgroundBed({
      outPath: bgmPath,
      durationSeconds: totalSeconds + 0.8,
      style
    });
    bgmSrc = `generated-audio/${jobId}/ambient-bed.wav`;
  }

  return {
    jobId,
    audioScenes,
    bgmSrc,
    provider: audioScenes[0]?.provider ?? provider
  };
};

export const ensureAudioDirs = async () => {
  if (!fsSync.existsSync(generatedDir)) {
    await fs.mkdir(generatedDir, {recursive: true});
  }
};
