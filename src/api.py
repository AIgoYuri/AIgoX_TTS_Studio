from __future__ import annotations

import json
import argparse
import random
import shutil
import subprocess
import tempfile
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
_MODEL_CACHE: dict[tuple[str, str], Any] = {}

# 默认配置写在代码里，api.py 可以独立运行，不依赖 config.json。
API_HOST = "127.0.0.1"
API_PORT = 9190
DEVICE = "cuda:0"
DTYPE = "bfloat16"
DEFAULT_MODEL = "qwen3_tts_1_7b_base"
DEFAULT_TEXT = "你好，这是默认声音克隆测试。"
DEFAULT_REF_AUDIO = "input/clone_1/ref.wav"
DEFAULT_REF_TEXT = ""
DEFAULT_OUTPUT_DIR = "output/clone_1"
MODELS: dict[str, dict[str, str]] = {
    "qwen3_tts_1_7b_base": {
        "path": "models/Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "note": "Qwen3-TTS Base，当前声音克隆主模型，支持 ref_audio + ref_text。",
    },
    "qwen3_tts_0_6b_base": {
        "path": "models/Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        "note": "小参数 Base 克隆模型；本地有权重后可直接切换。",
    },
}


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def model_path(model: str) -> Path:
    if model not in MODELS:
        raise KeyError(f"未知模型: {model}")
    return resolve_path(MODELS[model]["path"])


def list_models() -> dict[str, Any]:
    """返回代码中登记的模型。后续接新 TTS 模型，先在 MODELS 里新增路径。"""
    return MODELS


def default_model() -> str:
    """默认声音克隆模型。克隆必须用支持 ref_audio 的 Base 类模型。"""
    return DEFAULT_MODEL


def model_backend(model: str, backend: str | None = None) -> str:
    """根据模型名自动判断后端；也允许用户手动传 backend 覆盖。"""
    if backend:
        return backend
    if model.startswith("qwen3_tts"):
        return "qwen"
    if model.startswith("cosyvoice"):
        return "cosyvoice"
    if model.startswith("voxcpm"):
        return "voxcpm"
    if model.startswith("mimo"):
        return "mimo"
    raise ValueError(f"无法判断模型后端，请显式传 backend: {model}")


def short_model_name(model: str) -> str:
    if model.startswith("qwen3_tts"):
        return "qwen"
    if model.startswith("cosyvoice"):
        return "cosyvoice"
    if model.startswith("voxcpm"):
        return "voxcpm"
    return model.replace("/", "_").replace("-", "_")


def timestamp_name() -> str:
    now = datetime.now()
    return f"{now.year}_{now.month}_{now.day}_{now.hour:02d}{now.minute:02d}"


def read_text(value: str | Path) -> str:
    path = resolve_path(value)
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return str(value).strip()


def split_text(text: str, max_chars: int = 180) -> list[str]:
    """长文本自动分段。优先在中英文标点和换行处分段，避免一次生成过长。"""
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    current = ""
    stops = "。！？!?；;\n"
    for char in text:
        current += char
        if len(current) >= max_chars or char in stops:
            if current.strip():
                chunks.append(current.strip())
            current = ""
    if current.strip():
        chunks.append(current.strip())
    return chunks


def convert_audio(input_audio: Path, output_audio: Path) -> None:
    """统一输出格式。mp3 通过 ffmpeg 转换；wav 直接保留。"""
    output_audio.parent.mkdir(parents=True, exist_ok=True)
    if output_audio.suffix.lower() == ".wav":
        shutil.copyfile(input_audio, output_audio)
        return
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(input_audio), str(output_audio)],
        check=True,
    )


def concat_audio(inputs: list[Path], output_audio: Path) -> None:
    """多段音频合并成一个输出文件。"""
    output_audio.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        list_file = Path(tmp) / "concat.txt"
        list_file.write_text(
            "\n".join(f"file '{p.as_posix()}'" for p in inputs),
            encoding="utf-8",
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                str(output_audio),
            ],
            check=True,
        )


def clone_tts(
    *,
    text: str,
    ref_audio: str | Path,
    output: str | Path,
    model: str = "qwen3_tts_1_7b_base",
    ref_text: str = "",
    language: str = "Chinese",
    backend: str | None = None,
    max_chars: int = 80,
    seed: int | None = None,
    do_sample: bool = True,
    top_k: int = 20,
    top_p: float = 1.0,
    temperature: float = 0.9,
    repetition_penalty: float = 1.1,
    max_new_tokens: int | None = None,
    x_vector_only_mode: bool = False,
    non_streaming_mode: bool = False,
) -> dict[str, Any]:
    """声音克隆统一入口。

    用户只需要理解三个输入：
    1. text：让目标声音朗读的内容。
    2. ref_audio：目标声音样本。
    3. model：要使用的 TTS 模型，可在本文件 MODELS 常量里切换/新增。
    """
    if model in {"qwen3_tts_1_7b_custom_voice", "qwen3_tts_0_6b_custom_voice", "qwen3_tts_1_7b_voice_design"}:
        raise ValueError(
            f"{model} 不是参考音频克隆模型。声音克隆请使用 qwen3_tts_1_7b_base；"
            "声音设计不属于当前克隆链路。"
        )

    if seed is not None:
        set_seed(seed)

    chunks = split_text(text, max_chars=max_chars)
    if not chunks:
        raise ValueError("text 为空，无法生成语音")

    output_path = resolve_path(output)
    selected_backend = model_backend(model, backend)
    with tempfile.TemporaryDirectory() as tmp:
        wav_parts = []
        for index, chunk in enumerate(chunks, 1):
            part = Path(tmp) / f"part_{index:04d}.wav"
            if selected_backend == "qwen":
                _clone_with_qwen(
                    chunk,
                    ref_audio,
                    ref_text,
                    part,
                    model,
                    language,
                    do_sample=do_sample,
                    top_k=top_k,
                    top_p=top_p,
                    temperature=temperature,
                    repetition_penalty=repetition_penalty,
                    max_new_tokens=max_new_tokens,
                    x_vector_only_mode=x_vector_only_mode,
                    non_streaming_mode=non_streaming_mode,
                )
            elif selected_backend == "cosyvoice":
                _clone_with_cosyvoice(chunk, ref_audio, ref_text, part, model)
            elif selected_backend == "voxcpm":
                _clone_with_voxcpm(chunk, ref_audio, ref_text, part, model)
            elif selected_backend == "mimo":
                _clone_with_mimo(chunk, part, model)
            else:
                raise ValueError(f"不支持的后端: {selected_backend}")
            wav_parts.append(part)

        if len(wav_parts) == 1:
            convert_audio(wav_parts[0], output_path)
        else:
            concat_audio(wav_parts, output_path)

    return {
        "ok": True,
        "task": "clone",
        "backend": selected_backend,
        "model": model,
        "chunks": len(chunks),
        "output": str(output_path),
    }


def set_seed(seed: int) -> None:
    """设置随机种子。TTS 仍可能受 CUDA 算子影响，不能保证完全逐 bit 一致。"""
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def voice_design_tts(
    *,
    text: str,
    prompt: str,
    output: str | Path,
    model: str = "qwen3_tts_1_7b_voice_design",
    language: str = "Chinese",
) -> dict[str, Any]:
    """声音设计入口：不需要参考音频，用文字描述生成声音。"""
    return _voice_design_with_qwen(text, prompt, output, model, language)


def _clone_with_qwen(
    text: str,
    ref_audio: str | Path,
    ref_text: str,
    output_wav: Path,
    model: str,
    language: str,
    **generate_kwargs: Any,
) -> None:
    """Qwen3-TTS 克隆后端。当前项目主链路，已验证模型为 qwen3_tts_1_7b_base。"""
    import soundfile as sf

    tts = _load_qwen_model(model)
    qwen_kwargs = {k: v for k, v in generate_kwargs.items() if v is not None}
    if hasattr(tts, "create_voice_clone_prompt"):
        prompt = tts.create_voice_clone_prompt(
            ref_audio=str(resolve_path(ref_audio)),
            ref_text=ref_text,
            x_vector_only_mode=bool(qwen_kwargs.pop("x_vector_only_mode", False)),
        )
        wavs, sr = tts.generate_voice_clone(text=text, language=language, voice_clone_prompt=prompt, **qwen_kwargs)
    else:
        wavs, sr = tts.generate_voice_clone(
            text=text,
            language=language,
            ref_audio=str(resolve_path(ref_audio)),
            ref_text=ref_text,
            **qwen_kwargs,
        )
    sf.write(str(output_wav), wavs[0], sr)


def _voice_design_with_qwen(text: str, prompt: str, output: str | Path, model: str, language: str) -> dict[str, Any]:
    """Qwen3-TTS 声音设计后端。"""
    import soundfile as sf

    output_path = resolve_path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tts = _load_qwen_model(model)
    if hasattr(tts, "generate_voice_design"):
        wavs, sr = tts.generate_voice_design(text=text, voice_design_prompt=prompt, language=language)
    else:
        wavs, sr = tts.generate(text=f"{prompt}\n{text}", language=language)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "voice_design.wav"
        sf.write(str(wav), wavs[0], sr)
        convert_audio(wav, output_path)
    return {"ok": True, "task": "voice_design", "model": model, "output": str(output_path)}


def _load_qwen_model(model: str) -> Any:
    """加载并缓存 Qwen 模型，长文本分段时不会重复加载权重。"""
    import torch
    from qwen_tts import Qwen3TTSModel

    cache_key = (model, DEVICE)
    if cache_key in _MODEL_CACHE:
        return _MODEL_CACHE[cache_key]
    dtype = torch.bfloat16 if DTYPE == "bfloat16" else torch.float16
    tts = Qwen3TTSModel.from_pretrained(
        str(model_path(model)),
        device_map=DEVICE,
        dtype=dtype,
        trust_remote_code=True,
    )
    _MODEL_CACHE[cache_key] = tts
    return tts


def _clone_with_cosyvoice(text: str, ref_audio: str | Path, ref_text: str, output_wav: Path, model: str) -> None:
    """CosyVoice 后端占位：模型很多，后续补齐依赖和权重后在这里接入。"""
    raise NotImplementedError(f"CosyVoice 后端尚未接入完整推理链路: {model}, text={text[:20]}, ref={ref_audio}, ref_text={ref_text[:20]}")


def _clone_with_voxcpm(text: str, ref_audio: str | Path, ref_text: str, output_wav: Path, model: str) -> None:
    """VoxCPM/VoxCPM2 后端占位：建议使用独立 env/tts-voxcpm2 环境后再接入。"""
    raise NotImplementedError(f"VoxCPM 后端尚未接入完整推理链路: {model}, text={text[:20]}, ref={ref_audio}, ref_text={ref_text[:20]}")


def _clone_with_mimo(text: str, output_wav: Path, model: str) -> None:
    """Mimo 是云 API，不属于本地开源模型；如需保留可在这里接 HTTP API。"""
    raise NotImplementedError(f"Mimo 云 API 后端尚未启用: {model}, text={text[:20]}")


def default_output(model: str = DEFAULT_MODEL) -> str:
    return f"{DEFAULT_OUTPUT_DIR}/{short_model_name(model)}_{timestamp_name()}.mp3"


def default_payload() -> dict[str, Any]:
    """api.py 独立服务的默认请求参数。"""
    return {
        "text": DEFAULT_TEXT,
        "ref_audio": DEFAULT_REF_AUDIO,
        "ref_text": DEFAULT_REF_TEXT,
        "model": DEFAULT_MODEL,
        "language": "Chinese",
        "max_chars": 80,
        "output": default_output(DEFAULT_MODEL),
    }


def normalize_clone_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """清洗 HTTP 请求参数，避免外部传入未知字段或字符串类型参数。"""
    merged = {**default_payload(), **payload}
    if not merged.get("output"):
        merged["output"] = default_output(merged.get("model", DEFAULT_MODEL))
    return {
        "text": merged.get("text") or DEFAULT_TEXT,
        "ref_audio": merged.get("ref_audio") or DEFAULT_REF_AUDIO,
        "output": merged["output"],
        "model": merged.get("model") or DEFAULT_MODEL,
        "ref_text": merged.get("ref_text", DEFAULT_REF_TEXT),
        "language": merged.get("language", "Chinese"),
        "backend": merged.get("backend"),
        "max_chars": int(merged.get("max_chars", 80)),
        "seed": _optional_int(merged.get("seed")),
        "do_sample": _as_bool(merged.get("do_sample", True)),
        "top_k": int(merged.get("top_k", 20)),
        "top_p": float(merged.get("top_p", 1.0)),
        "temperature": float(merged.get("temperature", 0.9)),
        "repetition_penalty": float(merged.get("repetition_penalty", 1.1)),
        "max_new_tokens": _optional_int(merged.get("max_new_tokens")),
        "x_vector_only_mode": _as_bool(merged.get("x_vector_only_mode", False)),
        "non_streaming_mode": _as_bool(merged.get("non_streaming_mode", False)),
    }


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


class APIHandler(BaseHTTPRequestHandler):
    def send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self.send_json({"ok": True, "service": "qwen3-tts-api"})
        elif parsed.path == "/models":
            self.send_json({"ok": True, "default_model": DEFAULT_MODEL, "models": MODELS})
        elif parsed.path == "/download":
            self.send_file(parse_qs(parsed.query).get("path", [""])[0])
        else:
            self.send_json({"ok": False, "error": "not found"}, 404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/clone":
            self.send_json({"ok": False, "error": "not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = normalize_clone_payload(json.loads(self.rfile.read(length).decode("utf-8") or "{}"))
            result = clone_tts(**payload)
            self.send_json(result)
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc), "traceback": traceback.format_exc()}, 500)

    def send_file(self, value: str) -> None:
        target = resolve_path(value).resolve()
        output_root = (ROOT / "output").resolve()
        if output_root not in target.parents or not target.is_file():
            self.send_json({"ok": False, "error": "file not found"}, 404)
            return
        data = target.read_bytes()
        content_type = "audio/mpeg" if target.suffix.lower() == ".mp3" else "audio/wav"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{target.name}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve_api(host: str = API_HOST, port: int = API_PORT) -> None:
    server = ThreadingHTTPServer((host, port), APIHandler)
    print(f"Qwen3-TTS API: http://{host}:{port}")
    print("POST /clone, GET /models, GET /health")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Qwen3-TTS clone API")
    parser.add_argument("--host", default=API_HOST)
    parser.add_argument("--port", type=int, default=API_PORT)
    args = parser.parse_args()
    serve_api(args.host, args.port)


if __name__ == "__main__":
    main()
