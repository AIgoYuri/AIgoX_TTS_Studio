from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from api import DEFAULT_REF_AUDIO, DEFAULT_REF_TEXT, DEFAULT_TEXT, clone_tts, default_model, read_text, short_model_name, timestamp_name


INFO = {"id": "F1_Clone", "name": "声音克隆"}


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """声音克隆任务。

    F1 是独立功能层：接收页面/API/命令行参数，整理默认值后调用 api.clone_tts。
    """
    model = payload.get("model") or default_model()
    output = payload.get("output") or _default_output("clone_1", model)
    return clone_tts(
        text=payload.get("text") or DEFAULT_TEXT,
        ref_audio=payload.get("ref_audio") or payload.get("file") or DEFAULT_REF_AUDIO,
        ref_text=payload.get("ref_text") or DEFAULT_REF_TEXT,
        model=model,
        backend=payload.get("backend"),
        language=payload.get("language", "Chinese"),
        max_chars=int(payload.get("max_chars", 80)),
        seed=_optional_int(payload.get("seed")),
        do_sample=_as_bool(payload.get("do_sample", True)),
        top_k=int(payload.get("top_k", 20)),
        top_p=float(payload.get("top_p", 1.0)),
        temperature=float(payload.get("temperature", 0.9)),
        repetition_penalty=float(payload.get("repetition_penalty", 1.1)),
        max_new_tokens=_optional_int(payload.get("max_new_tokens")),
        x_vector_only_mode=_as_bool(payload.get("x_vector_only_mode", False)),
        non_streaming_mode=_as_bool(payload.get("non_streaming_mode", False)),
        output=output,
    )


def _default_output(input_name: str, model: str) -> str:
    return f"output/{input_name}/{short_model_name(model)}_{timestamp_name()}.mp3"


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def main() -> None:
    parser = argparse.ArgumentParser(description="F1 声音克隆：可独立运行")
    parser.add_argument("--web", choices=["on", "off"], default="off", help="on 启动 F1 页面；off 直接生成音频")
    parser.add_argument("--text", default=DEFAULT_TEXT)
    parser.add_argument("--text-file", default="")
    parser.add_argument("--ref-audio", default=DEFAULT_REF_AUDIO)
    parser.add_argument("--ref-text", default=DEFAULT_REF_TEXT)
    parser.add_argument("--model", default=default_model())
    parser.add_argument("--language", default="Chinese")
    parser.add_argument("--output", default="")
    parser.add_argument("--max-chars", type=int, default=80)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    if args.web == "on":
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root))
        from run import run_web

        run_web()
        return
    text = read_text(args.text_file) if args.text_file else args.text
    print(json.dumps(run({
        "text": text,
        "ref_audio": args.ref_audio,
        "ref_text": args.ref_text,
        "model": args.model,
        "language": args.language,
        "output": args.output,
        "max_chars": args.max_chars,
        "seed": args.seed,
    }), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
