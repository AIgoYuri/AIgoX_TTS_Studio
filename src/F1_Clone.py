from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from api import DEFAULT_TEXT, MODELS, clone_tts, read_text, short_model_name, timestamp_name


INFO = {"id": "F1_Clone", "name": "声音克隆"}

# =============================================================================
# F1 声音克隆模块：常改内容在这里
# =============================================================================
#
# 1. 默认模型名：这里填模型名，不填模型目录。
DEFAULT_CLONE_MODEL = "qwen3_tts_1_7b_base"
# DEFAULT_CLONE_MODEL = "qwen3_tts_0_6b_base"

# 2. 默认模型路径：默认用相对路径；需要绝对路径时，注释上一行，取消下一行注释。
DEFAULT_CLONE_MODEL_PATH = "models/Qwen/Qwen3-TTS-12Hz-1.7B-Base"
# DEFAULT_CLONE_MODEL_PATH = "/workspace/projects/Project/prometheus/TMP/OmniAudio/AIgoX_TTS_Studio/models/Qwen/Qwen3-TTS-12Hz-1.7B-Base"

# 3. 输入统一放 input，输出统一放 output。
DEFAULT_CLONE_REF_AUDIO = "input/clone_1/ref.wav"
DEFAULT_CLONE_TEXT_FILE = "input/clone_1/text.txt"
DEFAULT_CLONE_OUTPUT = ""
# DEFAULT_CLONE_OUTPUT = "output/clone_1/demo.mp3"
#
# 4. 参考文本是 ref.wav 里说的话，建议填写，克隆更稳。
DEFAULT_CLONE_REF_TEXT = ""
DEFAULT_CLONE_LANGUAGE = "Chinese"
DEFAULT_CLONE_MAX_CHARS = 80
#
# 常用命令：
#
# 打开网页：
#   python src/F1_Clone.py --web on
#
# 直接生成：
#   python src/F1_Clone.py --text "你好，这是声音克隆测试。"
#
# 读取文本文件生成：
#   python src/F1_Clone.py --text-file input/clone_1/text.txt
#
# 完整参数命令：
#   python src/F1_Clone.py \
#     --web off \
#     --text-file input/clone_1/text.txt \
#     --ref-audio input/clone_1/ref.wav \
#     --ref-text "参考音频对应文本" \
#     --model qwen3_tts_1_7b_base \
#     --language Chinese \
#     --output output/clone_1/demo.mp3 \
#     --max-chars 80 \
#     --seed 1234 \
#     --temperature 0.9 \
#     --top-p 1.0 \
#     --top-k 20 \
#     --repetition-penalty 1.1 \
#     --max-new-tokens "" \
#     --do-sample true \
#     --x-vector-only-mode false \
#     --non-streaming-mode false


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """接收网页或命令行参数，调用 api.clone_tts 生成音频。"""
    # 模型名来自页面/命令行；没传就用顶部 DEFAULT_CLONE_MODEL。
    model = payload.get("model") or DEFAULT_CLONE_MODEL
    if DEFAULT_CLONE_MODEL_PATH and model == DEFAULT_CLONE_MODEL and model in MODELS:
        MODELS[model]["path"] = DEFAULT_CLONE_MODEL_PATH

    # 输出路径没传就用顶部 DEFAULT_CLONE_OUTPUT；仍为空则自动生成。
    output = payload.get("output") or DEFAULT_CLONE_OUTPUT or _default_output("clone_1", model)

    # ref_audio 是要克隆的目标声音；默认路径在文件顶部。
    ref_audio = payload.get("ref_audio") or payload.get("file") or DEFAULT_CLONE_REF_AUDIO

    # ref_text 是目标声音音频对应文字；可空，但填写更稳定。
    ref_text = payload.get("ref_text") or DEFAULT_CLONE_REF_TEXT

    # 这里只整理参数；真正加载模型和生成音频在 api.clone_tts。
    return clone_tts(
        text=payload.get("text") or DEFAULT_TEXT,
        ref_audio=ref_audio,
        ref_text=ref_text,
        model=model,
        backend=payload.get("backend"),
        language=payload.get("language", DEFAULT_CLONE_LANGUAGE),
        max_chars=int(payload.get("max_chars", DEFAULT_CLONE_MAX_CHARS)),
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
    """生成默认输出路径：output/clone_1/qwen_时间.mp3。"""
    return f"output/{input_name}/{short_model_name(model)}_{timestamp_name()}.mp3"


def _optional_int(value: Any) -> int | None:
    """把空字符串转成 None，把数字字符串转成 int。"""
    if value in (None, ""):
        return None
    return int(value)


def _as_bool(value: Any) -> bool:
    """把网页传来的 true false 字符串转成 Python bool。"""
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def _optional_str(value: Any) -> str | None:
    """把命令行空字符串转成 None，避免传给模型。"""
    if value in (None, ""):
        return None
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="F1 声音克隆：可独立运行，也可启动网页",
        epilog=(
            "Example:\n"
            "  python src/F1_Clone.py --web on\n"
            "  python src/F1_Clone.py --text \"你好\" --ref-audio input/clone_1/ref.wav --ref-text \"参考音频文本\"\n\n"
            "Full command:\n"
            "  python src/F1_Clone.py \\\n"
            "    --web off \\\n"
            "    --text-file input/clone_1/text.txt \\\n"
            "    --ref-audio input/clone_1/ref.wav \\\n"
            "    --ref-text \"参考音频对应文本\" \\\n"
            "    --model qwen3_tts_1_7b_base \\\n"
            "    --language Chinese \\\n"
            "    --output output/clone_1/demo.mp3 \\\n"
            "    --max-chars 80 \\\n"
            "    --seed 1234 \\\n"
            "    --temperature 0.9 \\\n"
            "    --top-p 1.0 \\\n"
            "    --top-k 20 \\\n"
            "    --repetition-penalty 1.1 \\\n"
            "    --max-new-tokens \"\" \\\n"
            "    --do-sample true \\\n"
            "    --x-vector-only-mode false \\\n"
            "    --non-streaming-mode false\n\n"
            "Model names:\n"
            "  qwen3_tts_1_7b_base\n"
            "  qwen3_tts_0_6b_base\n\n"
            "Model path examples for src/api.py MODELS:\n"
            "  models/Qwen/Qwen3-TTS-12Hz-1.7B-Base\n"
            "  /workspace/projects/Project/prometheus/TMP/OmniAudio/AIgoX_TTS_Studio/models/Qwen/Qwen3-TTS-12Hz-1.7B-Base\n\n"
            "Audio input stays under input/. Audio output stays under output/."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--web", choices=["on", "off"], default="off", help="是否启动网页：on 打开页面；off 直接生成音频。默认 off。")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="要朗读的文本。")
    parser.add_argument("--text-file", default="", help=f"文本文件路径；示例 {DEFAULT_CLONE_TEXT_FILE}。")
    parser.add_argument("--ref-audio", default=DEFAULT_CLONE_REF_AUDIO, help="目标声音音频路径，也就是要克隆的音色。")
    parser.add_argument("--ref-text", default=DEFAULT_CLONE_REF_TEXT, help="目标声音音频对应文本，建议填写。")
    parser.add_argument("--model", default=DEFAULT_CLONE_MODEL, help="模型名，默认 qwen3_tts_1_7b_base。")
    parser.add_argument("--language", default=DEFAULT_CLONE_LANGUAGE, help="文本语言，例如 Chinese 或 English。")
    parser.add_argument("--output", default=DEFAULT_CLONE_OUTPUT, help="输出音频路径；留空则自动生成到 output/clone_1/。")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_CLONE_MAX_CHARS, help="长文本分段长度，默认 80。")
    parser.add_argument("--seed", type=int, default=None, help="随机种子；留空表示随机。")
    parser.add_argument("--temperature", type=float, default=0.9, help="随机性，越高变化越大，默认 0.9。")
    parser.add_argument("--top-p", type=float, default=1.0, help="核采样范围，默认 1.0。")
    parser.add_argument("--top-k", type=int, default=20, help="每步候选数量，默认 20。")
    parser.add_argument("--repetition-penalty", type=float, default=1.1, help="重复惩罚，默认 1.1。")
    parser.add_argument("--max-new-tokens", default="", help="最大生成 token，通常留空。")
    parser.add_argument("--do-sample", default="true", help="是否采样，true 或 false。")
    parser.add_argument("--x-vector-only-mode", default="false", help="是否只用声纹特征，默认 false。")
    parser.add_argument("--non-streaming-mode", default="false", help="Qwen 内部生成模式，默认 false。")
    args = parser.parse_args()
    if args.web == "on":
        # F1 独立打开页面时，复用 run.py 里的网页实现。
        # run.py 是总控入口，当前只挂 F1，后续可继续挂 F2/F3。
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root))
        from run import run_web

        run_web()
        return

    # 命令行模式：不启动网页，直接生成音频。
    # 传了 --text-file 就读文件，否则使用 --text。
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
        "temperature": args.temperature,
        "top_p": args.top_p,
        "top_k": args.top_k,
        "repetition_penalty": args.repetition_penalty,
        "max_new_tokens": _optional_str(args.max_new_tokens),
        "do_sample": args.do_sample,
        "x_vector_only_mode": args.x_vector_only_mode,
        "non_streaming_mode": args.non_streaming_mode,
    }), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
