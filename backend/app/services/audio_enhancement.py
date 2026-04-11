from pydub import AudioSegment
from pydub.silence import detect_nonsilent


def enhance_voice_audio(input_path: str, output_path: str, ffmpeg_path: str | None = None, output_format: str = 'mp3') -> int:
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1)
    try:
        audio = audio.high_pass_filter(80).low_pass_filter(8000)
    except Exception:
        pass
    audio = audio.normalize()

    ranges = detect_nonsilent(audio, min_silence_len=300, silence_thresh=-45)
    if ranges:
        start = max(ranges[0][0] - 80, 0)
        end = min(ranges[-1][1] + 120, len(audio))
        audio = audio[start:end]

    audio = audio.set_frame_rate(24000)
    audio.export(output_path, format=output_format)
    return len(audio)
