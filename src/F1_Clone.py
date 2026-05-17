from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from api import DEFAULT_REF_AUDIO, DEFAULT_REF_TEXT, DEFAULT_TEXT, clone_tts, default_model, read_text, short_model_name, timestamp_name


INFO = {"id": "F1_Clone", "name": "声音克隆"}

# =============================================================================
# F1 声音克隆模块
# =============================================================================
#
# 这个文件是“声音克隆功能层”，可以被三种方式调用：
#
# 1. 被 run.py 总控网页调用
#    python run.py --web on
#
# 2. 自己打开 F1 页面
#    python src/F1_Clone.py --web on
#
# 3. 不开网页，直接命令行生成音频
#
#    最小可复制命令：只要准备好 ref.wav，就可以直接运行。
#    如果不写 --output，会自动输出到 output/clone_1/qwen_YYYY_M_D_HHMM.mp3。
#
#    python src/F1_Clone.py \
#      --text "你好，这是声音克隆测试。" \
#      --ref-audio "input/clone_1/ref.wav" \
#      --ref-text "参考音频对应文本"
#
#    完整可复制命令：适合需要指定输出、语言、模型和生成参数时使用。
#
#    python src/F1_Clone.py \
#      --web off \
#      --text "你好，这是声音克隆测试。" \
#      --ref-audio "input/clone_1/ref.wav" \
#      --ref-text "参考音频对应文本" \
#      --model "qwen3_tts_1_7b_base" \
#      --language "Chinese" \
#      --output "output/clone_1/demo.mp3" \
#      --max-chars 80 \
#      --seed 1234
#
#    模型选择说明：
#    --model 填的是“模型名”，不是模型文件夹路径。
#    当前可用模型名：
#      qwen3_tts_1_7b_base
#      qwen3_tts_0_6b_base
#
#    模型实际存放路径写在 src/api.py 的 MODELS 里。
#    相对路径示例：
#      models/Qwen/Qwen3-TTS-12Hz-1.7B-Base
#      models/Qwen/Qwen3-TTS-12Hz-0.6B-Base
#
#    绝对路径示例，给别人部署时参考，默认不用写进命令：
#      /workspace/projects/Project/prometheus/TMP/OmniAudio/AIgoX_TTS_Studio/models/Qwen/Qwen3-TTS-12Hz-1.7B-Base
#      /workspace/projects/Project/prometheus/TMP/OmniAudio/AIgoX_TTS_Studio/models/Qwen/Qwen3-TTS-12Hz-0.6B-Base
#
#    目标声音音频路径示例：
#    相对路径，推荐项目内直接运行：
#      --ref-audio "input/clone_1/ref.wav"
#
#    绝对路径，给别人跨目录调用时参考，默认注释掉即可：
#      --ref-audio "/workspace/projects/Project/prometheus/TMP/OmniAudio/AIgoX_TTS_Studio/input/clone_1/ref.wav"
#
#    从文本文件读取朗读内容：
#
#    python src/F1_Clone.py \
#      --text-file "input/clone_1/text.txt" \
#      --ref-audio "input/clone_1/ref.wav" \
#      --ref-text "参考音频对应文本" \
#      --output "output/clone_1/demo.mp3"
#
# 输入：
# - --text：要让目标声音朗读的内容；适合短文本。
# - --text-file：文本文件路径；适合长文本。写了它就优先读取文件。
# - --ref-audio：目标声音音频，也就是要克隆的音色。建议使用 wav。
#   相对路径示例：input/clone_1/ref.wav
#   绝对路径示例：/workspace/projects/Project/prometheus/TMP/OmniAudio/AIgoX_TTS_Studio/input/clone_1/ref.wav
# - --ref-text：目标声音音频对应的文字，建议填写，克隆更稳定。
# - --model：TTS 模型名，默认 qwen3_tts_1_7b_base。
#   注意这里填模型名，不填模型目录。
#   模型目录在 src/api.py 的 MODELS 里配置。
# - --language：文本语言，默认 Chinese；英文可写 English。
# - --max-chars：长文本分段长度，默认 80，太大更容易占显存。
# - --seed：随机种子；不写就是随机，写了更容易复现相似结果。
#
# 输出：
# - --output：生成音频路径。
# - 不写 --output 时，默认输出到：
#   output/clone_1/qwen_YYYY_M_D_HHMM.mp3
# - 输出格式由后缀决定，推荐 .mp3，也可以写 .wav。
#
# 运行条件：
# - 已创建并激活 conda 环境 qwen3-audio。
# - 已下载 Qwen3-TTS Base 模型到 models/Qwen/。
# - ref-audio 指向一个真实存在的 wav/mp3/flac/m4a 音频文件。
#
# Web 开关：
# - --web on：打开网页。
# - --web off：不打开网页，直接生成音频。默认 off。
#
# 注意：
# - 这里不直接写模型推理细节。
# - 真正的模型加载、分段、推理、音频转换在 api.py。
# - 这样 F1 可以保持清晰，后续 F2/F3 也能按同样结构扩展。


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """声音克隆任务。

    F1 是独立功能层：接收页面/API/命令行参数，整理默认值后调用 api.clone_tts。

    Args:
        payload:
            text: 克隆要朗读的内容。
            ref_audio/file: 目标声音音频路径。
            ref_text: 目标声音音频对应文本。
            output: 输出音频路径，可为空。
            model: 模型名，可为空。
            language: 语言，可为空。
            max_chars: 长文本分段长度。
            seed/top_k/top_p/temperature 等：生成参数。

    Returns:
        dict: api.clone_tts 返回的结果，包含 ok/model/output/chunks 等字段。
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
    """生成默认输出路径。

    示例：
        output/clone_1/qwen_2026_5_16_1030.mp3
    """
    return f"output/{input_name}/{short_model_name(model)}_{timestamp_name()}.mp3"


def _optional_int(value: Any) -> int | None:
    """把可选整数字段转换为 int。

    Web 表单里的空字符串表示“不设置”，这里统一转成 None。
    """
    if value in (None, ""):
        return None
    return int(value)


def _as_bool(value: Any) -> bool:
    """把 Web/API 传入的布尔值统一转成 Python bool。"""
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="F1 声音克隆：可独立运行，也可启动网页",
        epilog=(
            "Example:\n"
            "  python src/F1_Clone.py --web on\n"
            "  python src/F1_Clone.py --text \"你好\" --ref-audio input/clone_1/ref.wav --ref-text \"参考音频文本\"\n"
            "  python src/F1_Clone.py --text-file input/clone_1/text.txt --ref-audio input/clone_1/ref.wav --output output/clone_1/demo.mp3\n\n"
            "Model names:\n"
            "  qwen3_tts_1_7b_base\n"
            "  qwen3_tts_0_6b_base\n\n"
            "Model paths are configured in src/api.py MODELS:\n"
            "  models/Qwen/Qwen3-TTS-12Hz-1.7B-Base\n"
            "  models/Qwen/Qwen3-TTS-12Hz-0.6B-Base\n\n"
            "Reference audio path examples:\n"
            "  input/clone_1/ref.wav\n"
            "  /workspace/projects/Project/prometheus/TMP/OmniAudio/AIgoX_TTS_Studio/input/clone_1/ref.wav"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--web", choices=["on", "off"], default="off", help="是否启动网页：on 打开页面；off 直接生成音频。默认 off。")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="要朗读的文本。")
    parser.add_argument("--text-file", default="", help="文本文件路径；填写后优先读取文件内容。")
    parser.add_argument("--ref-audio", default=DEFAULT_REF_AUDIO, help="目标声音音频路径，也就是要克隆的音色。")
    parser.add_argument("--ref-text", default=DEFAULT_REF_TEXT, help="目标声音音频对应文本，建议填写。")
    parser.add_argument("--model", default=default_model(), help="模型名，默认 qwen3_tts_1_7b_base。")
    parser.add_argument("--language", default="Chinese", help="文本语言，例如 Chinese 或 English。")
    parser.add_argument("--output", default="", help="输出音频路径；留空则自动生成到 output/clone_1/。")
    parser.add_argument("--max-chars", type=int, default=80, help="长文本分段长度，默认 80。")
    parser.add_argument("--seed", type=int, default=None, help="随机种子；留空表示随机。")
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
