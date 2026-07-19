import argparse
import logging
import os
import sys

import numpy as np
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse


logging.getLogger("matplotlib").setLevel(logging.WARNING)


def build_app(cosyvoice):
    from cosyvoice.utils.file_utils import load_wav

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def generate_data(model_output):
        for item in model_output:
            audio = (item["tts_speech"].numpy() * (2**15)).astype(np.int16).tobytes()
            yield audio

    @app.get("/health")
    def health():
        return {"ok": True, "sampleRate": cosyvoice.sample_rate, "speakers": cosyvoice.list_available_spks()}

    @app.get("/inference_sft")
    @app.post("/inference_sft")
    async def inference_sft(tts_text: str = Form(), spk_id: str = Form()):
        return StreamingResponse(generate_data(cosyvoice.inference_sft(tts_text, spk_id)))

    @app.get("/inference_zero_shot")
    @app.post("/inference_zero_shot")
    async def inference_zero_shot(tts_text: str = Form(), prompt_text: str = Form(), prompt_wav: UploadFile = File()):
        prompt_speech_16k = load_wav(prompt_wav.file, 16000)
        return StreamingResponse(generate_data(cosyvoice.inference_zero_shot(tts_text, prompt_text, prompt_speech_16k)))

    @app.get("/inference_cross_lingual")
    @app.post("/inference_cross_lingual")
    async def inference_cross_lingual(tts_text: str = Form(), prompt_wav: UploadFile = File()):
        prompt_speech_16k = load_wav(prompt_wav.file, 16000)
        return StreamingResponse(generate_data(cosyvoice.inference_cross_lingual(tts_text, prompt_speech_16k)))

    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50000)
    parser.add_argument("--model_dir", required=True)
    parser.add_argument("--root_dir", default=None)
    args = parser.parse_args()

    root_dir = args.root_dir or os.getcwd()
    sys.path.insert(0, root_dir)
    sys.path.append(os.path.join(root_dir, "third_party", "Matcha-TTS"))

    from cosyvoice.cli.cosyvoice import AutoModel

    cosyvoice = AutoModel(model_dir=args.model_dir)
    uvicorn.run(build_app(cosyvoice), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
