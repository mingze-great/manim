import argparse
import io
import os
import sys
import time
import wave
from pathlib import Path

import requests
from pydub import AudioSegment


def configure_ffmpeg() -> None:
    try:
        import imageio_ffmpeg

        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        AudioSegment.converter = ffmpeg_path
        AudioSegment.ffmpeg = ffmpeg_path
        AudioSegment.ffprobe = ffmpeg_path
    except Exception:
        return


def prepare_prompt_wav(source: Path, sample_rate: int, workspace: Path) -> Path:
    if not source.exists():
        raise FileNotFoundError(f"Prompt audio not found: {source}")
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / "prompt.wav"
    audio = AudioSegment.from_file(source).set_channels(1).set_frame_rate(sample_rate)
    if len(audio) > 15000:
        audio = audio[:15000]
    audio.export(target, format="wav")
    return target


def pcm_to_wav(pcm: bytes, output_path: Path, sample_rate: int) -> None:
    if len(pcm) < sample_rate:
        raise RuntimeError("CosyVoice returned implausibly short audio")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)


def synthesize_with_cosyvoice(
    *,
    cosyvoice_url: str,
    text: str,
    prompt_text: str,
    prompt_audio: Path,
    output_path: Path,
    sample_rate: int,
    timeout: int,
) -> None:
    health = requests.get(f"{cosyvoice_url.rstrip('/')}/health", timeout=5)
    health.raise_for_status()
    with prompt_audio.open("rb") as prompt_file:
        response = requests.post(
            f"{cosyvoice_url.rstrip('/')}/inference_zero_shot",
            data={"tts_text": text, "prompt_text": prompt_text},
            files={"prompt_wav": (prompt_audio.name, prompt_file, "audio/wav")},
            timeout=timeout,
        )
    response.raise_for_status()
    pcm_to_wav(response.content, output_path, sample_rate)


def synthesize_with_edge(text: str, output_path: Path, sample_rate: int) -> None:
    import asyncio
    import edge_tts

    async def run() -> None:
        mp3_path = output_path.with_suffix(".edge.mp3")
        communicate = edge_tts.Communicate(text=text, voice="zh-CN-XiaoxiaoNeural")
        await communicate.save(str(mp3_path))
        audio = AudioSegment.from_file(mp3_path).set_channels(1).set_frame_rate(sample_rate)
        audio.export(output_path, format="wav")
        mp3_path.unlink(missing_ok=True)

    asyncio.run(run())


def upload_completion(platform_url: str, token: str, request_id: str, audio_path: Path) -> None:
    with audio_path.open("rb") as audio_file:
        response = requests.post(
            f"{platform_url.rstrip('/')}/api/local-tts/{request_id}/complete",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (audio_path.name, audio_file, "audio/wav")},
            timeout=120,
        )
    response.raise_for_status()


def report_failure(platform_url: str, token: str, request_id: str, error: str) -> None:
    try:
        requests.post(
            f"{platform_url.rstrip('/')}/api/local-tts/{request_id}/fail",
            headers={"Authorization": f"Bearer {token}"},
            data={"error": error[:1000]},
            timeout=30,
        )
    except Exception:
        pass


def run_once(args, prompt_wav: Path, workspace: Path) -> bool:
    response = requests.post(
        f"{args.platform_url.rstrip('/')}/api/local-tts/claim",
        headers={"Authorization": f"Bearer {args.token}"},
        timeout=30,
    )
    response.raise_for_status()
    request = response.json().get("request")
    if not request:
        return False

    request_id = str(request["requestId"])
    text = str(request.get("text") or "").strip()
    prompt_text = str(request.get("promptText") or args.prompt_text).strip() or args.prompt_text
    output_path = workspace / f"{request_id}.wav"
    print(f"[local-tts] claimed {request_id}: {text[:60]}", flush=True)
    try:
        if args.provider == "edge":
            synthesize_with_edge(text, output_path, args.sample_rate)
        else:
            synthesize_with_cosyvoice(
                cosyvoice_url=args.cosyvoice_url,
                text=text,
                prompt_text=prompt_text,
                prompt_audio=prompt_wav,
                output_path=output_path,
                sample_rate=args.sample_rate,
                timeout=args.timeout,
            )
        upload_completion(args.platform_url, args.token, request_id, output_path)
        print(f"[local-tts] completed {request_id}: {output_path}", flush=True)
    except Exception as exc:
        report_failure(args.platform_url, args.token, request_id, str(exc))
        print(f"[local-tts] failed {request_id}: {exc}", file=sys.stderr, flush=True)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll 3004 local TTS jobs, synthesize locally, and upload audio back.")
    parser.add_argument("--platform-url", default=os.getenv("LOCAL_TTS_PLATFORM_URL", "http://152.136.218.74:3004"))
    parser.add_argument("--token", default=os.getenv("LOCAL_TTS_WORKER_TOKEN", ""))
    parser.add_argument("--cosyvoice-url", default=os.getenv("LOCAL_COSYVOICE_URL", "http://127.0.0.1:50000"))
    parser.add_argument("--prompt-audio", default=os.getenv("LOCAL_TTS_PROMPT_AUDIO", r"E:\ai\火柴人工作流\配音\曼波.mp3"))
    parser.add_argument("--prompt-text", default=os.getenv("SC1_COSYVOICE_PROMPT_TEXT", "焦虑不是敌人，它只是先替你把危险放大。"))
    parser.add_argument("--workspace", default=os.getenv("LOCAL_TTS_WORKSPACE", str(Path("outputs") / "local-tts-worker")))
    parser.add_argument("--provider", choices=["cosyvoice", "edge"], default=os.getenv("LOCAL_TTS_PROVIDER", "cosyvoice"))
    parser.add_argument("--sample-rate", type=int, default=int(os.getenv("LOCAL_TTS_SAMPLE_RATE", "22050")))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("LOCAL_TTS_TIMEOUT", "180")))
    parser.add_argument("--poll-interval", type=float, default=float(os.getenv("LOCAL_TTS_POLL_INTERVAL", "2")))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if not args.token:
        raise SystemExit("LOCAL_TTS_WORKER_TOKEN is required")

    workspace = Path(args.workspace).resolve()
    configure_ffmpeg()
    prompt_wav = workspace / "prompt.wav"
    if args.provider == "cosyvoice":
        prompt_wav = prepare_prompt_wav(Path(args.prompt_audio), args.sample_rate, workspace)
    print(f"[local-tts] platform={args.platform_url} provider={args.provider} prompt={prompt_wav}", flush=True)

    while True:
        handled = run_once(args, prompt_wav, workspace)
        if args.once:
            break
        if not handled:
            time.sleep(args.poll_interval)


if __name__ == "__main__":
    main()
