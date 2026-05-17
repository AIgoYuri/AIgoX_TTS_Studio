from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))

from api import API_HOST, default_model, list_models
import F1_Clone


WEB_PORT = 9188


def page() -> str:
    default_clone_model = default_model()
    clone_models = [key for key in list_models() if key.endswith("_base") and key.startswith("qwen3_tts")]
    models = "\n".join(
        f'<option value="{key}"{" selected" if key == default_clone_model else ""}>{key}</option>'
        for key in clone_models
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>AIgoX_TTS_Studio</title>
  <style>
    :root {{
      --bg:#0a0f16; --panel:#111923; --panel2:#0f1620; --ink:#e8eef6; --muted:#98a6b8;
      --line:#263242; --brand:#18b6a4; --brand2:#4f8cff; --warn:#d9a441; --field:#0c131c;
      --field2:#141f2b; --ok:#12352f;
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0; min-height:100vh; color:var(--ink);
      background:linear-gradient(135deg,#0a0f16 0%,#101923 48%,#0b1119 100%);
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;
    }}
    body::before {{
      content:""; position:fixed; inset:0; pointer-events:none;
      background:linear-gradient(90deg,rgba(24,182,164,.08),transparent 34%,rgba(79,140,255,.08));
    }}
    header {{ border-bottom:1px solid rgba(255,255,255,.08); background:rgba(10,15,22,.78); backdrop-filter:blur(18px); }}
    .top {{ max-width:1180px; margin:0 auto; padding:18px 22px; display:flex; justify-content:space-between; align-items:center; gap:18px; position:relative; }}
    .brand {{ display:flex; align-items:center; gap:12px; min-width:0; }}
    .mark {{ width:44px; height:44px; border-radius:10px; display:grid; place-items:center; color:#061018; font-weight:900; background:linear-gradient(135deg,var(--brand),var(--brand2)); box-shadow:0 14px 34px rgba(24,182,164,.24); }}
    h1 {{ margin:0; font-size:22px; line-height:1.2; letter-spacing:0; }}
    .sub {{ margin-top:4px; color:var(--muted); font-size:13px; }}
    .credit {{ color:var(--muted); font-size:13px; white-space:nowrap; }}
    .lang-toggle {{ width:auto; margin:0; padding:9px 12px; background:#172433; font-size:13px; border:1px solid #2c3b4d; }}
    .right-tools {{ display:flex; align-items:center; gap:12px; }}
    main {{ max-width:1180px; margin:0 auto; padding:26px 22px 34px; display:grid; gap:16px; position:relative; }}
    .modules {{ display:grid; grid-template-columns:minmax(820px, 1060px); gap:16px; align-items:start; justify-content:center; }}
    section {{ background:linear-gradient(180deg,rgba(17,25,35,.96),rgba(12,19,28,.98)); border:1px solid rgba(255,255,255,.1); border-radius:14px; padding:20px; box-shadow:0 24px 70px rgba(0,0,0,.34); }}
    .module-head {{ display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom:16px; }}
    h2 {{ margin:0; font-size:18px; }}
    .module-desc {{ margin-top:6px; color:var(--muted); font-size:13px; }}
    .badge {{ padding:7px 10px; border:1px solid #315264; border-radius:999px; color:#9ee8dd; background:#0b2830; font-size:12px; white-space:nowrap; }}
    label {{ display:block; margin:0 0 7px; font-weight:800; font-size:12px; color:#cbd6e2; }}
    textarea,input,select {{
      width:100%; height:42px; border:1px solid #2a384a; border-radius:9px; padding:10px 11px;
      font:inherit; background:var(--field); color:var(--ink); outline:none;
    }}
    textarea:focus,input:focus,select:focus {{ border-color:var(--brand); box-shadow:0 0 0 3px rgba(24,182,164,.14); }}
    textarea {{ height:auto; min-height:132px; resize:vertical; line-height:1.55; }}
    .grid {{ display:grid; grid-template-columns:repeat(12, minmax(0, 1fr)); gap:14px; align-items:start; }}
    .field {{ min-width:0; }}
    .span-12 {{ grid-column:span 12; }}
    .span-6 {{ grid-column:span 6; }}
    .span-4 {{ grid-column:span 4; }}
    .hint {{ color:var(--muted); font-size:12px; line-height:1.5; }}
    .inline-hint {{ align-self:end; min-height:42px; display:flex; align-items:center; padding:0 2px; }}
    details {{ margin-top:16px; border:1px solid var(--line); border-radius:12px; background:#0d151f; overflow:hidden; }}
    summary {{ cursor:pointer; font-weight:900; color:#dbe6f0; padding:13px 14px; background:#111c28; }}
    .param-grid {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:12px; padding:14px; }}
    .param-card {{ min-height:132px; border:1px solid #263242; border-radius:10px; padding:11px; background:#0b121b; }}
    .note {{ color:var(--muted); font-size:12px; line-height:1.45; margin-top:7px; }}
    button {{ width:100%; margin-top:16px; padding:12px 14px; border:0; border-radius:10px; background:linear-gradient(135deg,var(--brand),var(--brand2)); color:#061018; font-weight:900; cursor:pointer; }}
    button:disabled {{ opacity:.65; cursor:wait; }}
    .result {{ display:none; margin-top:14px; padding:13px; background:var(--ok); border:1px solid #23695d; border-radius:10px; }}
    .download {{ display:inline-block; margin-top:10px; padding:9px 12px; border-radius:9px; background:#d9a441; color:#14100a; text-decoration:none; font-weight:900; }}
    audio {{ width:100%; margin-top:10px; }}
    .status-wrap {{ margin-top:14px; border:1px solid var(--line); border-radius:12px; background:#090f16; overflow:hidden; }}
    .status-title {{ padding:10px 12px; border-bottom:1px solid var(--line); color:#cbd6e2; font-weight:900; font-size:12px; }}
    pre {{ margin:0; white-space:pre-wrap; min-height:126px; background:#090f16; color:#b8dcff; padding:12px; overflow:auto; font-size:12px; }}
    @media(max-width:980px) {{ .top {{ align-items:flex-start; flex-direction:column; }} .modules {{ grid-template-columns:1fr; }} .span-4,.span-6,.span-12 {{ grid-column:span 12; }} .param-grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <header>
    <div class="top">
      <div class="brand">
        <div class="mark">AY</div>
        <div>
          <h1>AIgoX_TTS_Studio</h1>
          <div class="sub">输入路径和参数后生成可下载音频</div>
        </div>
      </div>
      <div class="right-tools">
        <button class="lang-toggle" onclick="toggleLang()">中文 / EN</button>
        <div class="credit">Created by AIgoYuri</div>
      </div>
    </div>
  </header>
  <main>
    <div class="modules">
      <section>
        <div class="module-head">
          <div>
            <h2 data-i18n="moduleTitle">声音克隆</h2>
            <div class="module-desc" data-i18n="moduleDesc">所有路径都可以在下面直接修改。</div>
          </div>
          <div class="badge">Qwen3-TTS Base</div>
        </div>
        <div class="grid">
          <div class="field span-6"><label data-i18n="model">模型</label><select id="clone_model">{models}</select></div>
          <div class="field span-6"><label data-i18n="language">语言</label><select id="language"><option>Chinese</option><option>English</option><option>Japanese</option><option>Korean</option><option>French</option><option>German</option><option>Spanish</option><option>Russian</option><option>Portuguese</option><option>Italian</option></select></div>
          <div class="field span-12"><label data-i18n="modelPath">模型路径</label><input id="model_path" value="{F1_Clone.DEFAULT_CLONE_MODEL_PATH}"></div>
          <div class="field span-6"><label data-i18n="refAudio">目标声音音频路径</label><input id="ref_audio" value="{F1_Clone.DEFAULT_CLONE_REF_AUDIO}"></div>
          <div class="field span-6"><label data-i18n="textFile">克隆文本文件路径</label><input id="text_file" value="{F1_Clone.DEFAULT_CLONE_TEXT_FILE}"></div>
          <div class="field span-12"><label data-i18n="output">输出路径</label><input id="clone_output" value="{F1_Clone.DEFAULT_CLONE_OUTPUT}" data-placeholder-zh="留空自动输出到 output/clone_1/" data-placeholder-en="Auto output under output/clone_1/" placeholder="留空自动输出到 output/clone_1/"></div>
          <div class="field span-12"><label data-i18n="text">克隆内容</label><textarea id="clone_text" data-placeholder-zh="可直接输入文本；留空则读取上面的文本文件路径" data-placeholder-en="Type text here, or leave empty to read the text file path above" placeholder="可直接输入文本；留空则读取上面的文本文件路径"></textarea></div>
          <div class="field span-12"><label data-i18n="refText">参考音频对应文本</label><input id="ref_text" value="{F1_Clone.DEFAULT_CLONE_REF_TEXT}"></div>
          <div class="field span-12 hint" data-i18n="mainHint">默认输入在 input，默认输出在 output。网页端可以直接修改模型路径、目标声音音频路径、文本文件路径和输出路径。</div>
        </div>
        <details>
          <summary data-i18n="params">生成参数</summary>
          <div class="param-grid">
            <div class="param-card"><label>分段长度</label><input id="max_chars" type="number" min="20" max="800" value="80"><div class="note">长文本按字数切段。默认 80，越大越容易占显存。</div></div>
            <div class="param-card"><label>随机种子</label><input id="seed" type="number" placeholder="留空随机"><div class="note">固定后更容易复现相似结果，但 CUDA 不保证完全一致。</div></div>
            <div class="param-card"><label>temperature</label><input id="temperature" type="number" step="0.05" min="0.1" max="2" value="0.9"><div class="note">控制随机性。越高变化越大，越低更稳定。</div></div>
            <div class="param-card"><label>top_p</label><input id="top_p" type="number" step="0.05" min="0.1" max="1" value="1.0"><div class="note">核采样范围。降低会更保守。</div></div>
            <div class="param-card"><label>top_k</label><input id="top_k" type="number" min="1" max="200" value="20"><div class="note">每步只从前 K 个候选采样。</div></div>
            <div class="param-card"><label>repetition_penalty</label><input id="repetition_penalty" type="number" step="0.05" min="0.8" max="2" value="1.1"><div class="note">抑制重复。过高可能影响自然度。</div></div>
            <div class="param-card"><label>max_new_tokens</label><input id="max_new_tokens" type="number" placeholder="留空默认"><div class="note">限制生成长度。通常留空。</div></div>
            <div class="param-card"><label>do_sample</label><select id="do_sample"><option value="true">true</option><option value="false">false</option></select><div class="note">是否启用采样。true 更自然，false 更确定。</div></div>
            <div class="param-card"><label>x_vector_only_mode</label><select id="x_vector_only_mode"><option value="false">false</option><option value="true">true</option></select><div class="note">true 只用声纹特征；false 会结合参考文本和音频上下文。</div></div>
            <div class="param-card"><label>non_streaming_mode</label><select id="non_streaming_mode"><option value="false">false</option><option value="true">true</option></select><div class="note">Qwen 内部生成模式。默认 false。</div></div>
          </div>
        </details>
        <div class="hint" data-i18n="backendHint">当前可用后端：Qwen3-TTS Base。CustomVoice 和 VoiceDesign 不属于参考音频克隆链路。</div>
        <button id="run_btn" onclick="runClone()" data-i18n="run">生成音频</button>
        <div id="result_box" class="result">
          <b data-i18n="done">生成完成</b>
          <audio id="player" controls></audio>
          <a id="download" class="download" href="#" data-i18n="download">下载音频</a>
        </div>
        <div class="status-wrap">
          <div class="status-title" data-i18n="status">运行状态</div>
          <pre id="result">等待运行...</pre>
        </div>
      </section>
    </div>
  </main>
  <script>
    let uiLang = "zh";
    const dict = {{
      zh: {{
        moduleTitle:"声音克隆", moduleDesc:"所有路径都可以在下面直接修改。", model:"模型", modelPath:"模型路径", textFile:"克隆文本文件路径", language:"语言", output:"输出路径", text:"克隆内容",
        refAudio:"目标声音音频路径", refText:"参考音频对应文本", params:"生成参数", run:"生成音频",
        done:"生成完成", download:"下载音频", status:"运行状态", waiting:"等待运行...", running:"生成中...",
        mainHint:"默认输入在 input，默认输出在 output。网页端可以直接修改模型路径、目标声音音频路径、文本文件路径和输出路径。",
        backendHint:"当前可用后端：Qwen3-TTS Base。CustomVoice 和 VoiceDesign 不属于参考音频克隆链路。"
      }},
      en: {{
        moduleTitle:"Voice Clone", moduleDesc:"All paths can be edited below.", model:"Model", modelPath:"Model Path", textFile:"Text File Path", language:"Language", output:"Output Path", text:"Text to Speak",
        refAudio:"Reference Audio Path", refText:"Reference Audio Transcript", params:"Generation Parameters", run:"Generate Audio",
        done:"Done", download:"Download Audio", status:"Run Status", waiting:"Waiting...", running:"Generating...",
        mainHint:"Default input stays under input, and output stays under output. You can edit model path, reference audio path, text file path, and output path in the web UI.",
        backendHint:"Available backend: Qwen3-TTS Base. CustomVoice and VoiceDesign are not reference-audio clone models."
      }}
    }};
    function applyLang() {{
      document.querySelectorAll("[data-i18n]").forEach(el => el.textContent = dict[uiLang][el.dataset.i18n]);
      document.getElementById("clone_output").placeholder = uiLang === "zh" ? document.getElementById("clone_output").dataset.placeholderZh : document.getElementById("clone_output").dataset.placeholderEn;
      document.getElementById("clone_text").placeholder = uiLang === "zh" ? document.getElementById("clone_text").dataset.placeholderZh : document.getElementById("clone_text").dataset.placeholderEn;
      if (document.getElementById("result").textContent === dict[uiLang === "zh" ? "en" : "zh"].waiting) document.getElementById("result").textContent = dict[uiLang].waiting;
    }}
    function toggleLang() {{
      uiLang = uiLang === "zh" ? "en" : "zh";
      applyLang();
    }}
    async function post(url, payload) {{
      const btn = document.getElementById("run_btn");
      btn.disabled = true;
      btn.textContent = dict[uiLang].running;
      document.getElementById("result_box").style.display = "none";
      const res = await fetch(url, {{method:"POST", headers:{{"Content-Type":"application/json"}}, body:JSON.stringify(payload)}});
      const data = await res.json();
      document.getElementById("result").textContent = JSON.stringify(data, null, 2);
      if (data.ok && data.output) {{
        const link = "/download?path=" + encodeURIComponent(data.output);
        document.getElementById("player").src = link;
        document.getElementById("download").href = link;
        document.getElementById("download").download = data.output.split("/").pop();
        document.getElementById("result_box").style.display = "block";
      }}
      btn.disabled = false;
      btn.textContent = dict[uiLang].run;
    }}
    function runClone() {{
      const payload = {{
        model: document.getElementById("clone_model").value,
        model_path: document.getElementById("model_path").value,
        text: document.getElementById("clone_text").value,
        text_file: document.getElementById("text_file").value,
        ref_audio: document.getElementById("ref_audio").value,
        ref_text: document.getElementById("ref_text").value,
        language: document.getElementById("language").value,
        max_chars: document.getElementById("max_chars").value,
        seed: document.getElementById("seed").value,
        temperature: document.getElementById("temperature").value,
        top_p: document.getElementById("top_p").value,
        top_k: document.getElementById("top_k").value,
        repetition_penalty: document.getElementById("repetition_penalty").value,
        max_new_tokens: document.getElementById("max_new_tokens").value,
        do_sample: document.getElementById("do_sample").value,
        x_vector_only_mode: document.getElementById("x_vector_only_mode").value,
        non_streaming_mode: document.getElementById("non_streaming_mode").value,
        output: document.getElementById("clone_output").value
      }};
      post("/api/clone", payload);
    }}
  </script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            body = page().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/models":
            self.send_json({"ok": True, "models": list_models()})
        elif path == "/download":
            self.send_file(parse_qs(parsed.query).get("path", [""])[0])
        else:
            self.send_json({"ok": False, "error": "not found"}, 404)

    def send_file(self, value: str) -> None:
        try:
            target = Path(value)
            if not target.is_absolute():
                target = ROOT / target
            target = target.resolve()
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
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, 500)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            if path == "/api/clone":
                self.send_json(F1_Clone.run(payload))
            else:
                self.send_json({"ok": False, "error": "not found"}, 404)
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc), "traceback": traceback.format_exc()}, 500)


def run_web() -> None:
    host = API_HOST
    port = WEB_PORT
    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}"
    print(f"Open Voice Clone TTS: {url}")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Open Voice Clone TTS")
    parser.add_argument("--web", choices=["on", "off"], default="on", help="on 打开总控网页；off 直接运行当前 F1")
    parser.add_argument("--text", default="")
    parser.add_argument("--text-file", default="")
    parser.add_argument("--ref-audio", default="")
    parser.add_argument("--ref-text", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    if args.web == "on":
        run_web()
    else:
        payload = {
            "text": Path(args.text_file).read_text(encoding="utf-8").strip() if args.text_file else args.text,
            "ref_audio": args.ref_audio,
            "ref_text": args.ref_text,
            "output": args.output,
        }
        print(json.dumps(F1_Clone.run(payload), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
