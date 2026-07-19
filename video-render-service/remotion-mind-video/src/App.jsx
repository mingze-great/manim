import React, {useEffect, useMemo, useState} from 'react';
import {Player} from '@remotion/player';
import {AnimatePresence, motion} from 'framer-motion';
import {
  BrainCircuit,
  Clapperboard,
  Download,
  Film,
  Gauge,
  Loader2,
  Mic2,
  Music2,
  Play,
  Sparkles,
  Wand2
} from 'lucide-react';
import {MindVideo} from './remotion/MindVideo.jsx';
import {defaultScript, scriptToStory, styleOptions} from './story.js';
import './styles.css';

const examples = [
  {
    title: '学习网络',
    text: defaultScript
  },
  {
    title: '创业判断',
    text: `一个创业想法值不值得做，不是先看它酷不酷，而是看它是否卡住了真实的高频痛点。

先找到人群，再观察他们反复绕不过去的问题。痛点越具体，产品越容易形成清晰入口。

然后验证付费意愿。愿意花时间、花钱、迁移习惯，才说明需求不是礼貌性的赞同。

最后把复杂方案压缩成一个最小闭环。能跑通一次，就有机会放大成系统。`
  },
  {
    title: '认知升级',
    text: `认知升级不是知道更多名词，而是改变自己解释世界的模型。

旧模型会把问题看成孤立事件，新模型会看到背后的结构、反馈和边界条件。

真正的突破通常来自一个新问题：如果我原来的假设是错的，世界会呈现出什么证据？

当你能主动更新假设，行动就不再只是努力，而是越来越接近真相。`
  }
];

const postJson = async (url, body) => {
  const response = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.message ?? 'Request failed');
  return data;
};

export default function App() {
  const [script, setScript] = useState(defaultScript);
  const [style, setStyle] = useState('aurora');
  const [density, setDensity] = useState(1);
  const [voice, setVoice] = useState('');
  const [voices, setVoices] = useState([]);
  const [provider, setProvider] = useState('auto');
  const [cosyVoiceSpeaker, setCosyVoiceSpeaker] = useState('中文女');
  const [ttsStatus, setTtsStatus] = useState(null);
  const [speechRate, setSpeechRate] = useState(0);
  const [withBgm, setWithBgm] = useState(true);
  const [rendering, setRendering] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const story = useMemo(() => scriptToStory({script, style, density}), [script, style, density]);
  const seconds = Math.round((story.durationInFrames / story.fps) * 10) / 10;

  useEffect(() => {
    let mounted = true;
    fetch('/api/voices')
      .then((response) => response.json())
      .then((data) => {
        if (!mounted) return;
        setVoices(data.voices ?? []);
      })
      .catch(() => {
        if (mounted) setVoices([]);
      });
    fetch('/api/tts/status')
      .then((response) => response.json())
      .then((data) => {
        if (mounted) setTtsStatus(data.cosyVoice ?? null);
      })
      .catch(() => {
        if (mounted) setTtsStatus(null);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const renderVideo = async () => {
    setRendering(true);
    setError('');
    setResult(null);
    try {
      const data = await postJson('/api/render', {
        script,
        style,
        density,
        provider,
        cosyVoiceSpeaker,
        voice,
        speechRate,
        withBgm
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Render failed');
    } finally {
      setRendering(false);
    }
  };

  return (
    <div className="app-shell">
      <div className="ambient-grid" />
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">
            <BrainCircuit size={24} />
          </div>
          <div>
            <strong>MindFilm Studio</strong>
            <span>Text to narrated Remotion video</span>
          </div>
        </div>
        <div className="status-strip">
          <span><Sparkles size={16} /> Remotion pipeline online</span>
          <span><Mic2 size={16} /> TTS enabled</span>
          <span><Film size={16} /> {result?.seconds ?? seconds}s</span>
        </div>
      </header>

      <main className="studio-grid">
        <section className="script-panel">
          <div className="panel-heading">
            <div>
              <p>01 Script</p>
              <h1>把文案变成带配音的思维可视化视频</h1>
            </div>
            <Wand2 size={28} />
          </div>

          <textarea
            value={script}
            onChange={(event) => setScript(event.target.value)}
            spellCheck={false}
            aria-label="视频文案"
          />

          <div className="example-row">
            {examples.map((example) => (
              <button key={example.title} type="button" onClick={() => setScript(example.text)}>
                {example.title}
              </button>
            ))}
          </div>

          <div className="control-block">
            <div className="control-title">
              <Clapperboard size={18} />
              <span>Visual System</span>
            </div>
            <div className="style-grid">
              {styleOptions.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className={style === option.id ? 'active' : ''}
                  onClick={() => setStyle(option.id)}
                >
                  <span className={`swatch ${option.id}`} />
                  {option.name}
                </button>
              ))}
            </div>
          </div>

          <div className="control-block">
            <label className="slider-label" htmlFor="density">
              <span><Gauge size={18} /> 预览节奏</span>
              <strong>{density.toFixed(1)}x</strong>
            </label>
            <input
              id="density"
              type="range"
              min="0.75"
              max="1.35"
              step="0.05"
              value={density}
              onChange={(event) => setDensity(Number(event.target.value))}
            />
          </div>

          <div className="control-block">
            <div className="control-title">
              <Mic2 size={18} />
              <span>Narration</span>
            </div>
            <label className="field-label" htmlFor="provider">
              配音引擎
            </label>
            <select id="provider" value={provider} onChange={(event) => setProvider(event.target.value)}>
              <option value="auto">Auto · 优先 CosyVoice，失败回退系统声音</option>
              <option value="cosyvoice">CosyVoice · 高质量中文服务</option>
              <option value="sapi">Windows SAPI · 本机系统声音</option>
            </select>
            <div className={ttsStatus?.ok ? 'status-note online' : 'status-note'}>
              CosyVoice: {ttsStatus?.ok ? `online · ${ttsStatus.baseUrl}` : `offline · ${ttsStatus?.baseUrl ?? 'http://127.0.0.1:50000'}`}
            </div>

            {provider !== 'sapi' && (
              <>
                <label className="field-label spaced" htmlFor="cosyVoiceSpeaker">
                  CosyVoice speaker
                </label>
                <input
                  id="cosyVoiceSpeaker"
                  className="text-input"
                  value={cosyVoiceSpeaker}
                  onChange={(event) => setCosyVoiceSpeaker(event.target.value)}
                  placeholder="中文女"
                />
              </>
            )}

            <label className="field-label" htmlFor="voice">
              系统声音 fallback
            </label>
            <select id="voice" value={voice} onChange={(event) => setVoice(event.target.value)}>
              <option value="">默认声音</option>
              {voices.map((item) => (
                <option key={`${item.name}-${item.culture}`} value={item.name}>
                  {item.name} · {item.culture}
                </option>
              ))}
            </select>

            <label className="slider-label compact" htmlFor="speechRate">
              <span>语速</span>
              <strong>{speechRate > 0 ? `+${speechRate}` : speechRate}</strong>
            </label>
            <input
              id="speechRate"
              type="range"
              min="-3"
              max="3"
              step="1"
              value={speechRate}
              onChange={(event) => setSpeechRate(Number(event.target.value))}
            />

            <label className="toggle-row">
              <input
                type="checkbox"
                checked={withBgm}
                onChange={(event) => setWithBgm(event.target.checked)}
              />
              <span><Music2 size={17} /> 生成背景氛围音</span>
            </label>
          </div>
        </section>

        <section className="preview-zone">
          <div className="preview-frame">
            <Player
              key={`${style}-${density}-${story.durationInFrames}`}
              component={MindVideo}
              durationInFrames={story.durationInFrames}
              fps={story.fps}
              compositionWidth={story.width}
              compositionHeight={story.height}
              controls
              autoPlay
              loop
              inputProps={{script, style, density}}
              style={{width: '100%', aspectRatio: '16 / 9'}}
            />
          </div>

          <div className="action-row">
            <button className="render-button" type="button" onClick={renderVideo} disabled={rendering}>
              {rendering ? <Loader2 className="spin" size={20} /> : <Play size={20} />}
              {rendering ? '正在生成配音并渲染 MP4' : '生成带声音视频'}
            </button>
            <AnimatePresence mode="wait">
              {result && (
                <motion.a
                  key={result.url}
                  initial={{opacity: 0, y: 8}}
                  animate={{opacity: 1, y: 0}}
                  exit={{opacity: 0, y: -8}}
                  className="download-link"
                  href={result.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Download size={18} />
                  打开 MP4
                </motion.a>
              )}
            </AnimatePresence>
          </div>

          {result && (
            <div className="result-box">
              <strong>已生成带声音视频</strong>
              <span>{result.seconds}s · {result.provider} · audio job {result.audioJobId}</span>
            </div>
          )}
          {error && <div className="error-box">{error}</div>}

          <div className="story-board">
            <div className="board-heading">
              <p>02 Timeline</p>
              <span>{story.scenes.length} scenes</span>
            </div>
            <div className="scene-list">
              {story.scenes.map((scene) => (
                <article key={scene.id}>
                  <div className="scene-index">{String(scene.index + 1).padStart(2, '0')}</div>
                  <div>
                    <h3>{scene.title}</h3>
                    <p>{scene.body}</p>
                    <div className="keyword-line">
                      {scene.keywords.map((keyword) => (
                        <span key={keyword}>{keyword}</span>
                      ))}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
