# TTS_Studio

Open-source TTS application studio for practical voice cloning.

Created by AIgoYuri.

中文 | [English](#english)

## 中文

TTS_Studio 是一个准备开源的 TTS 实际应用项目。当前稳定主线只做一件事：

```text
目标声音音频 + 目标声音文本 + 要朗读的内容 -> 生成克隆音频
```

当前可用后端：

```text
Qwen3-TTS Base
```

`CustomVoice` 和 `VoiceDesign` 暂不属于当前参考音频克隆链路。

### 目录结构

```text
TTS_Studio/
  README.md
  run.py                         # 总控网页入口；后续用于聚合 F1/F2/F3
  env/
    qwen3-audio.yml              # conda 环境文件
  input/
    clone_1/
      ref.wav                    # 用户自备目标声音音频，不随仓库提交
      ref.txt                    # 可选：ref.wav 对应文本
      text.txt                   # 可选测试文本
  output/                        # 生成音频输出目录
  models/
    download_qwen_tts_base.py    # 下载 Qwen3-TTS Base 1.7B/0.6B
    Qwen/
      Qwen3-TTS-12Hz-1.7B-Base/  # 默认模型目录
      Qwen3-TTS-12Hz-0.6B-Base/  # 可选小模型目录
  src/
    api.py                       # 独立 API 服务，不依赖 config.json
    F1_Clone.py                  # 声音克隆功能模块，可独立运行
```

### 1. 建立 Conda 环境

推荐环境路径：

```text
qwen3-audio
```

创建环境：

```bash
conda env create -f env/qwen3-audio.yml
```

激活环境：

```bash
conda activate qwen3-audio
```

验证环境：

```bash
python - <<'PY'
import torch
import qwen_tts
print('torch:', torch.__version__)
print('cuda:', torch.cuda.is_available())
print('qwen_tts: OK')
PY
```

已验证的关键版本：

```text
Python 3.10
torch 2.10.0+cu128
CUDA 可用
qwen_tts OK
qwen_asr OK
```

### 2. 下载模型

当前只需要 Qwen3-TTS Base 模型。

通常二选一即可：

```text
1.7B Base：推荐默认选择，音质和克隆相似度通常更好，但模型更大、显存占用更高。
0.6B Base：轻量选择，适合显存较小、快速测试或部署成本敏感的场景。
```

下载 1.7B Base，推荐默认模型：

```bash
python models/download_qwen_tts_base.py 1.7b
```

下载 0.6B Base，小模型可选：

```bash
python models/download_qwen_tts_base.py 0.6b
```

全部下载：

```bash
python models/download_qwen_tts_base.py all
```

`all` 不是必须，只是同时下载 1.7B 和 0.6B，方便对比效果。

下载后目录应为：

```text
models/Qwen/Qwen3-TTS-12Hz-1.7B-Base/
models/Qwen/Qwen3-TTS-12Hz-0.6B-Base/
```

如果只下载 1.7B，则只需要存在：

```text
models/Qwen/Qwen3-TTS-12Hz-1.7B-Base/
```

如果 Hugging Face 下载慢，可以去 ModelScope、魔方等镜像平台手动下载同名模型，然后把文件放到上面的目录中。目录名要保持一致。

### 3. 准备输入文件

默认参考音频放在：

```text
input/clone_1/ref.wav
```

网页里可以手动填写任意本地音频路径，例如：

```text
input/my_voice.wav
/data/audio/ref.wav
```

建议同时填写目标声音文本，例如：

```text

```

参考文本越准确，克隆越稳定。

### 4. 运行网页

```bash
python run.py --web on
```

默认地址：

```text
http://127.0.0.1:9188
```

网页提供：

```text
声音克隆表单
生成参数折叠区
音频播放器
下载音频按钮
运行状态 JSON
中文/英文 UI 切换
```

### 5. F1 独立运行

直接生成音频：

```bash
python src/F1_Clone.py \
  --text "你好，这是声音克隆测试。" \
  --ref-audio "input/clone_1/ref.wav" \
  --ref-text ""
```

从文本文件读取要朗读的内容：

```bash
python src/F1_Clone.py \
  --text-file input/clone_1/text.txt \
  --ref-audio "input/clone_1/ref.wav" \
  --ref-text ""
```

F1 也可以单独打开页面：

```bash
python src/F1_Clone.py --web on
```

### 6. 独立 API 服务

`src/api.py` 可以独立运行，方便给其他程序调用：

```bash
python src/api.py --port 9190
```

接口：

```text
GET  /health
GET  /models
POST /clone
GET  /download?path=output/clone_1/xxx.mp3
```

调用示例：

```bash
curl -X POST http://127.0.0.1:9190/clone \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好，这是声音克隆测试。",
    "ref_audio": "input/clone_1/ref.wav",
    "ref_text": "",
    "language": "Chinese"
  }'
```

### 默认路径和修改位置

默认模型、默认参考音频、默认输出目录都写在：

```text
src/api.py
```

常用修改位置：

```text
DEFAULT_MODEL       # 默认模型名
DEFAULT_REF_AUDIO   # 默认目标声音音频
DEFAULT_REF_TEXT    # 默认目标声音文本
DEFAULT_OUTPUT_DIR  # 默认输出目录
MODELS              # 新增或修改模型路径
DEVICE              # cuda:0 / cuda:1 / cpu
DTYPE               # bfloat16 / float16
```

当前默认模型路径：

```text
models/Qwen/Qwen3-TTS-12Hz-1.7B-Base
```

默认输出：

```text
output/clone_1/qwen_YYYY_M_D_HHMM.mp3
```

项目当前运行链路不依赖 `config.json`。

### 参数说明

| 参数 | 默认值 | 说明 |
|---|---:|---|
| `text` | 内置测试文本 | 要让目标声音朗读的内容 |
| `ref_audio` | `input/clone_1/ref.wav` | 目标声音音频路径 |
| `ref_text` | `` | 目标声音音频对应文本，填写后克隆更稳 |
| `language` | `Chinese` | 文本语言 |
| `max_chars` | `80` | 长文本自动分段长度，越大越占显存 |
| `seed` | 空 | 随机种子，便于复现相似结果 |
| `temperature` | `0.9` | 采样随机性，越高变化越大 |
| `top_p` | `1.0` | 核采样范围，降低会更保守 |
| `top_k` | `20` | 每步从前 K 个候选里采样 |
| `repetition_penalty` | `1.1` | 抑制重复，过高会影响自然度 |
| `max_new_tokens` | 空 | 限制生成长度，通常留空 |
| `do_sample` | `true` | 是否启用采样 |
| `x_vector_only_mode` | `false` | true 只用声纹特征；false 结合参考文本和音频上下文 |
| `non_streaming_mode` | `false` | Qwen 内部生成模式，默认 false |

### 设计原则

```text
src/api.py       独立模型 API，可直接作为服务运行
src/F1_Clone.py  声音克隆功能模块，可独立运行
run.py           总控入口，后续聚合多个功能模块
```

---

## English

TTS_Studio is an open-source TTS application studio for practical voice cloning.

Created by AIgoYuri.

The current stable feature is:

```text
reference audio + reference text + target text -> cloned speech
```

Current backend:

```text
Qwen3-TTS Base
```

`CustomVoice` and `VoiceDesign` are not part of the current reference-audio cloning path.

### Project Layout

```text
TTS_Studio/
  README.md
  run.py                         # Main web launcher; future hub for F1/F2/F3
  env/
    qwen3-audio.yml              # Conda environment file
  input/
    clone_1/
      .wav      # Default reference audio
      text.txt                   # Optional sample text
  output/                        # Generated audio
  models/
    download_qwen_tts_base.py    # Download Qwen3-TTS Base 1.7B/0.6B
    Qwen/
      Qwen3-TTS-12Hz-1.7B-Base/  # Default model directory
      Qwen3-TTS-12Hz-0.6B-Base/  # Optional smaller model directory
  src/
    api.py                       # Standalone API service, no config.json required
    F1_Clone.py                  # Voice clone module, runnable on its own
```

### 1. Create Conda Environment

Recommended environment path:

```text
qwen3-audio
```

Create the environment:

```bash
conda env create -f env/qwen3-audio.yml
```

Activate it:

```bash
conda activate qwen3-audio
```

Verify:

```bash
python - <<'PY'
import torch
import qwen_tts
print('torch:', torch.__version__)
print('cuda:', torch.cuda.is_available())
print('qwen_tts: OK')
PY
```

Verified setup:

```text
Python 3.10
torch 2.10.0+cu128
CUDA available
qwen_tts OK
qwen_asr OK
```

### 2. Download Models

Only Qwen3-TTS Base models are needed for the current voice clone path.

You usually only need one of them:

```text
1.7B Base: recommended default, usually better quality and speaker similarity, but larger and more VRAM hungry.
0.6B Base: lightweight option for smaller GPUs, quick tests, or lower-cost deployment.
```

Download 1.7B Base, recommended default:

```bash
python models/download_qwen_tts_base.py 1.7b
```

Download 0.6B Base, optional smaller model:

```bash
python models/download_qwen_tts_base.py 0.6b
```

Download both:

```bash
python models/download_qwen_tts_base.py all
```

`all` is optional. It downloads both 1.7B and 0.6B for comparison.

Expected directories:

```text
models/Qwen/Qwen3-TTS-12Hz-1.7B-Base/
models/Qwen/Qwen3-TTS-12Hz-0.6B-Base/
```

If you only download 1.7B, only this directory is required:

```text
models/Qwen/Qwen3-TTS-12Hz-1.7B-Base/
```

If Hugging Face is slow, manually download the same repositories from ModelScope, Mofang, or another mirror, then place the files into the directories above. Keep the directory names unchanged.

### 3. Prepare Input

Default reference audio:

```text
input/clone_1/ref.wav
```

You can enter any local audio path in the web UI, for example:

```text
input/my_voice.wav
/data/audio/ref.wav
```

It is recommended to provide the exact reference text, for example:

```text

```

More accurate reference text usually gives more stable cloning.

### 4. Run Web UI

```bash
python run.py --web on
```

Default URL:

```text
http://127.0.0.1:9188
```

The web UI includes:

```text
voice clone form
generation parameters panel
audio preview
download button
run status JSON
Chinese/English UI toggle
```

### 5. Run F1 Directly

```bash
python src/F1_Clone.py \
  --text "Hello, this is a voice cloning test." \
  --ref-audio "input/clone_1/ref.wav" \
  --ref-text "" \
  --language English
```

Read target text from a file:

```bash
python src/F1_Clone.py \
  --text-file input/clone_1/text.txt \
  --ref-audio "input/clone_1/ref.wav" \
  --ref-text "" \
  --language English
```

F1 can also launch the web UI:

```bash
python src/F1_Clone.py --web on
```

### 6. Standalone API Service

```bash
python src/api.py --port 9190
```

Endpoints:

```text
GET  /health
GET  /models
POST /clone
GET  /download?path=output/clone_1/xxx.mp3
```

Example:

```bash
curl -X POST http://127.0.0.1:9190/clone \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a voice cloning test.",
    "ref_audio": "input/clone_1/ref.wav",
    "ref_text": "",
    "language": "English"
  }'
```

### Defaults and Where to Modify

Defaults are defined in:

```text
src/api.py
```

Common values to modify:

```text
DEFAULT_MODEL       # default model name
DEFAULT_REF_AUDIO   # default reference audio
DEFAULT_REF_TEXT    # default reference text
DEFAULT_OUTPUT_DIR  # default output directory
MODELS              # add or edit model paths
DEVICE              # cuda:0 / cuda:1 / cpu
DTYPE               # bfloat16 / float16
```

Default model path:

```text
models/Qwen/Qwen3-TTS-12Hz-1.7B-Base
```

Default output:

```text
output/clone_1/qwen_YYYY_M_D_HHMM.mp3
```

The current runtime path does not require `config.json`.

### Parameters

| Parameter | Default | Description |
|---|---:|---|
| `text` | sample text | Text to synthesize |
| `ref_audio` | `input/clone_1/ref.wav` | Reference voice audio |
| `ref_text` | `` | Transcript of the reference audio |
| `language` | `Chinese` | Target text language |
| `max_chars` | `80` | Auto split length for long text |
| `seed` | empty | Random seed for more reproducible results |
| `temperature` | `0.9` | Sampling randomness |
| `top_p` | `1.0` | Nucleus sampling range |
| `top_k` | `20` | Top-k sampling |
| `repetition_penalty` | `1.1` | Repetition penalty |
| `max_new_tokens` | empty | Optional generation length limit |
| `do_sample` | `true` | Enable sampling |
| `x_vector_only_mode` | `false` | Use speaker embedding only when true |
| `non_streaming_mode` | `false` | Internal Qwen generation mode |

### Design

```text
src/api.py       Standalone model API service
src/F1_Clone.py  Independent voice clone module
run.py           Main launcher for future F1/F2/F3 modules
```
