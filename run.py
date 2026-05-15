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
  <title>TTS_Studio</title>
  <style>
    :root {{ --bg:#f4f6f8; --panel:#ffffff; --ink:#182230; --muted:#667085; --line:#d9e0ea; --brand:#0f766e; --brand2:#2563eb; --soft:#ecfdf5; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif; }}
    header {{ border-bottom:1px solid var(--line); background:#fff; }}
    .top {{ max-width:1180px; margin:0 auto; padding:18px 22px; display:flex; justify-content:space-between; align-items:center; gap:18px; }}
    .brand {{ display:flex; align-items:center; gap:12px; min-width:0; }}
    .mark {{ width:42px; height:42px; border-radius:8px; display:grid; place-items:center; color:#fff; font-weight:800; background:linear-gradient(135deg,var(--brand),var(--brand2)); }}
    h1 {{ margin:0; font-size:21px; line-height:1.2; }}
    .sub {{ margin-top:4px; color:var(--muted); font-size:13px; }}
    .credit {{ color:var(--muted); font-size:13px; white-space:nowrap; }}
    .lang-toggle {{ width:auto; margin:0; padding:8px 11px; background:#182230; font-size:13px; }}
    .right-tools {{ display:flex; align-items:center; gap:12px; }}
    main {{ max-width:1180px; margin:0 auto; padding:22px; display:grid; gap:14px; }}
    .modules {{ display:grid; grid-template-columns:minmax(720px, 980px); gap:14px; align-items:start; justify-content:center; }}
    section {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:18px; }}
    h2 {{ margin:0 0 14px; font-size:17px; }}
    label {{ display:block; margin:12px 0 6px; font-weight:700; font-size:13px; color:#344054; }}
    textarea,input,select {{ width:100%; border:1px solid #cfd6e2; border-radius:7px; padding:10px 11px; font:inherit; background:#fff; color:var(--ink); }}
    textarea {{ min-height:126px; resize:vertical; line-height:1.55; }}
    .grid {{ display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:12px; align-items:end; }}
    .grid.two {{ grid-template-columns:1.35fr 1fr; }}
    .grid.three {{ grid-template-columns:repeat(3, minmax(0, 1fr)); }}
    .span-all {{ grid-column:1 / -1; }}
    .full {{ grid-column:1 / -1; }}
    .hint {{ color:var(--muted); font-size:12px; margin-top:6px; }}
    details {{ margin-top:14px; border:1px solid var(--line); border-radius:8px; background:#fbfcfe; padding:12px; }}
    summary {{ cursor:pointer; font-weight:800; color:#344054; }}
    .note {{ color:var(--muted); font-size:12px; line-height:1.45; margin-top:5px; }}
    button {{ width:100%; margin-top:16px; padding:11px 14px; border:0; border-radius:7px; background:var(--brand); color:#fff; font-weight:700; cursor:pointer; }}
    button:disabled {{ opacity:.65; cursor:wait; }}
    .result {{ display:none; margin-top:14px; padding:12px; background:var(--soft); border:1px solid #bbf7d0; border-radius:8px; }}
    .download {{ display:inline-block; margin-top:10px; padding:9px 12px; border-radius:7px; background:#182230; color:#fff; text-decoration:none; font-weight:700; }}
    audio {{ width:100%; margin-top:10px; }}
    pre {{ white-space:pre-wrap; min-height:120px; background:#101828; color:#dbeafe; border-radius:8px; padding:12px; overflow:auto; font-size:12px; }}
    @media(max-width:900px) {{ .top {{ align-items:flex-start; flex-direction:column; }} .modules,.grid,.grid.two,.grid.three {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <header>
    <div class="top">
      <div class="brand">
        <div class="mark">AY</div>
        <div>
          <h1>TTS_Studio</h1>
          <div class="sub">目标声音 + 克隆文本，一键生成可下载音频</div>
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
        <h2 data-i18n="moduleTitle">声音克隆</h2>
        <div class="grid">
          <div><label data-i18n="model">模型</label><select id="clone_model">{models}</select></div>
          <div><label data-i18n="language">语言</label><select id="language"><option>Chinese</option><option>English</option><option>Japanese</option><option>Korean</option><option>French</option><option>German</option><option>Spanish</option><option>Russian</option><option>Portuguese</option><option>Italian</option></select></div>
          <div><label data-i18n="output">输出路径</label><input id="clone_output" data-placeholder-zh="留空自动输出" data-placeholder-en="Auto output when empty" placeholder="留空自动输出"></div>
          <div class="span-all"><label data-i18n="text">克隆内容</label><textarea id="clone_text">你好，这是默认声音克隆测试。</textarea></div>
          <label data-i18n="refAudio">目标声音音频</label><input id="ref_audio" value="input/clone_1/ref.wav">
          <label data-i18n="refText">目标声音文本</label><input id="ref_text" value="">
          <div class="hint" data-i18n="mainHint">目标声音音频就是参考音色文件路径。目标声音文本是这段音频对应的文字，填写后克隆更稳。</div>
        </div>
        <details>
          <summary data-i18n="params">生成参数</summary>
          <div class="grid">
            <div><label>分段长度</label><input id="max_chars" type="number" min="20" max="800" value="80"><div class="note">长文本按字数切段。默认 80，越大越容易占显存。</div></div>
            <div><label>随机种子</label><input id="seed" type="number" placeholder="留空随机"><div class="note">固定后更容易复现相似结果，但 CUDA 不保证完全一致。</div></div>
            <div><label>temperature</label><input id="temperature" type="number" step="0.05" min="0.1" max="2" value="0.9"><div class="note">控制随机性。越高变化越大，越低更稳定。</div></div>
            <div><label>top_p</label><input id="top_p" type="number" step="0.05" min="0.1" max="1" value="1.0"><div class="note">核采样范围。降低会更保守。</div></div>
            <div><label>top_k</label><input id="top_k" type="number" min="1" max="200" value="20"><div class="note">每步只从前 K 个候选采样。</div></div>
            <div><label>repetition_penalty</label><input id="repetition_penalty" type="number" step="0.05" min="0.8" max="2" value="1.1"><div class="note">抑制重复。过高可能影响自然度。</div></div>
            <div><label>max_new_tokens</label><input id="max_new_tokens" type="number" placeholder="留空默认"><div class="note">限制生成长度。通常留空。</div></div>
            <div><label>do_sample</label><select id="do_sample"><option value="true">true</option><option value="false">false</option></select><div class="note">是否启用采样。true 更自然，false 更确定。</div></div>
            <div><label>x_vector_only_mode</label><select id="x_vector_only_mode"><option value="false">false</option><option value="true">true</option></select><div class="note">true 只用声纹特征；false 会结合参考文本和音频上下文。</div></div>
            <div><label>non_streaming_mode</label><select id="non_streaming_mode"><option value="false">false</option><option value="true">true</option></select><div class="note">Qwen 内部生成模式。默认 false。</div></div>
          </div>
        </details>
        <div class="hint" data-i18n="backendHint">当前可用后端：Qwen3-TTS Base。CustomVoice 和 VoiceDesign 不属于参考音频克隆链路。</div>
        <button id="run_btn" onclick="runClone()" data-i18n="run">生成音频</button>
        <div id="result_box" class="result">
          <b data-i18n="done">生成完成</b>
          <audio id="player" controls></audio>
          <a id="download" class="download" href="#" data-i18n="download">下载音频</a>
        </div>
        <label data-i18n="status">运行状态</label>
        <pre id="result">等待运行...</pre>
      </section>
    </div>
  </main>
  <script>
    let uiLang = "zh";
    const dict = {{
      zh: {{
        moduleTitle:"声音克隆", model:"模型", language:"语言", output:"输出路径", text:"克隆内容",
        refAudio:"目标声音音频", refText:"目标声音文本", params:"生成参数", run:"生成音频",
        done:"生成完成", download:"下载音频", status:"运行状态", waiting:"等待运行...", running:"生成中...",
        mainHint:"目标声音音频就是参考音色文件路径。目标声音文本是这段音频对应的文字，填写后克隆更稳。",
        backendHint:"当前可用后端：Qwen3-TTS Base。CustomVoice 和 VoiceDesign 不属于参考音频克隆链路。"
      }},
      en: {{
        moduleTitle:"Voice Clone", model:"Model", language:"Language", output:"Output Path", text:"Text to Speak",
        refAudio:"Reference Audio", refText:"Reference Text", params:"Generation Parameters", run:"Generate Audio",
        done:"Done", download:"Download Audio", status:"Run Status", waiting:"Waiting...", running:"Generating...",
        mainHint:"Reference audio is the target voice file. Reference text should match that audio for more stable cloning.",
        backendHint:"Available backend: Qwen3-TTS Base. CustomVoice and VoiceDesign are not reference-audio clone models."
      }}
    }};
    function applyLang() {{
      document.querySelectorAll("[data-i18n]").forEach(el => el.textContent = dict[uiLang][el.dataset.i18n]);
      document.getElementById("clone_output").placeholder = uiLang === "zh" ? document.getElementById("clone_output").dataset.placeholderZh : document.getElementById("clone_output").dataset.placeholderEn;
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
        text: document.getElementById("clone_text").value,
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
