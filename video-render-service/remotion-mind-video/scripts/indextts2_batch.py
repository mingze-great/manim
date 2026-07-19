import argparse
import json
from pathlib import Path


def load_indextts2(model_dir: str):
    try:
        from indextts.infer_v2 import IndexTTS2
    except Exception as exc:
        raise RuntimeError(
            "Cannot import IndexTTS2. Install the IndexTTS repo environment, "
            "or set SC1_INDEXTTS2_PYTHON to that environment's python."
        ) from exc

    model_path = Path(model_dir)
    cfg_path = model_path / "config.yaml"
    kwargs = {
        "model_dir": str(model_path),
        "cfg_path": str(cfg_path) if cfg_path.exists() else None,
    }
    kwargs = {key: value for key, value in kwargs.items() if value}

    try:
        return IndexTTS2(**kwargs)
    except TypeError:
        if cfg_path.exists():
            return IndexTTS2(str(cfg_path), str(model_path))
        return IndexTTS2(str(model_path))


def infer_one(tts, reference_audio: str, text: str, output_path: str) -> None:
    candidates = [
        {
            "spk_audio_prompt": reference_audio,
            "text": text,
            "output_path": output_path,
            "emo_audio_prompt": None,
            "emo_alpha": 0.8,
            "use_emo_text": True,
            "use_random": False,
            "verbose": False,
            "max_text_tokens_per_segment": 120,
        },
        {
            "audio_prompt": reference_audio,
            "text": text,
            "output_path": output_path,
        },
        {
            "prompt_audio": reference_audio,
            "text": text,
            "output_path": output_path,
        },
    ]
    last_error = None
    for kwargs in candidates:
        try:
            tts.infer(**kwargs)
            return
        except TypeError as exc:
            last_error = exc
            continue
    try:
        tts.infer(reference_audio, text, output_path)
    except Exception as exc:
        raise RuntimeError(f"IndexTTS2 inference failed for {output_path}: {exc}") from (last_error or exc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    reference_audio = str(Path(manifest["referenceAudio"]))
    tts = load_indextts2(str(manifest["modelDir"]))

    for job in manifest["jobs"]:
        output_path = Path(job["outputPath"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[indextts2] {job.get('label', output_path.name)}")
        infer_one(tts, reference_audio, str(job["text"]), str(output_path))
        if not output_path.exists():
            raise RuntimeError(f"IndexTTS2 did not create output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
