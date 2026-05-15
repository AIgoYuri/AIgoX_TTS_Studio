from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import snapshot_download


PROJECT_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = PROJECT_DIR / "models"

# 这里只下载 Qwen3-TTS Base 模型，因为当前项目做的是“参考音频声音克隆”。
# 1.7B 和 0.6B 二选一即可：
# - 1.7B：默认推荐，音质和相似度通常更好，但显存占用更高、下载更大。
# - 0.6B：轻量版本，适合显存较小或只想快速测试的机器。
#
# 如果 Hugging Face 下载慢，可以去 ModelScope、魔方或其他镜像手动下载同名模型，
# 然后把模型文件放到 local_dir 对应目录即可。
#
# Users only need one of the two Base models:
# - 1.7B: recommended default, better quality, larger VRAM/storage requirement.
# - 0.6B: smaller and faster to test, lower quality than 1.7B.
# You may edit repo_id/local_dir below if you use another mirror.
MODEL_REPOS = {
    "1.7b": {
        "repo_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "local_dir": MODELS_DIR / "Qwen" / "Qwen3-TTS-12Hz-1.7B-Base",
    },
    "0.6b": {
        "repo_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        "local_dir": MODELS_DIR / "Qwen" / "Qwen3-TTS-12Hz-0.6B-Base",
    },
}


def download_one(key: str) -> None:
    """下载单个模型。key 只能是 1.7b 或 0.6b。"""
    item = MODEL_REPOS[key]
    local_dir = Path(item["local_dir"])
    local_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(MODELS_DIR / ".cache" / "huggingface"))
    print(f"Downloading {item['repo_id']} -> {local_dir}")
    snapshot_download(
        repo_id=item["repo_id"],
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
    )
    print(f"Done: {local_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Qwen3-TTS Base models")
    parser.add_argument(
        "model",
        nargs="?",
        default="1.7b",
        choices=["1.7b", "0.6b", "all"],
        help="Choose one model to download. 1.7b is recommended; 0.6b is smaller. Default: 1.7b",
    )
    args = parser.parse_args()

    if args.model == "all":
        for key in ("1.7b", "0.6b"):
            download_one(key)
    else:
        download_one(args.model)


if __name__ == "__main__":
    main()
