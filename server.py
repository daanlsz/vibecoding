"""
AI 聊天机器人后端（零依赖，仅用 Python 标准库）

功能：
  1. 托管 static/ 目录下的前端页面（HTML / CSS / JS / axios）
  2. 提供 /api/chat 接口，转发请求到 DeepSeek 的 Anthropic 兼容 API

启动：
  python server.py
  然后浏览器打开 http://127.0.0.1:5000
"""

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# DeepSeek Anthropic 兼容接口配置
API_URL = "https://api.deepseek.com/anthropic/v1/messages"
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro")
MAX_TOKENS = 4096

SYSTEM_PROMPT = (
    "你是一个友好、专业的 AI 助手。"
    "请用清晰、准确、有条理的中文回答用户的问题，"
    "可以使用 Markdown 格式（标题、列表、代码块等）来组织回答。"
)

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


def load_api_key():
    """从环境变量或 .env 文件读取 API Key。"""
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key:
        return key
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


API_KEY = load_api_key()


def call_deepseek(messages):
    """调用 DeepSeek，返回助手文本回复。"""
    if not API_KEY:
        raise RuntimeError("未配置 API Key，请在 .env 中设置 DEEPSEEK_API_KEY")

    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = json.dumps(
        {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        }
    ).encode("utf-8")

    req = urllib.request.Request(API_URL, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    content = data.get("content", [])
    if isinstance(content, str):
        return content

    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


class Handler(BaseHTTPRequestHandler):
    server_version = "AIChat/1.0"

    # ---------- 通用 ----------
    def _set_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _send_json(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._set_cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, rel_path):
        full = (STATIC_DIR / rel_path).resolve()
        # 防目录穿越
        if not full.is_relative_to(STATIC_DIR.resolve()):
            self.send_error(403)
            return
        if not full.is_file():
            self.send_error(404)
            return
        body = full.read_bytes()
        ctype = MIME_TYPES.get(full.suffix.lower(), "application/octet-stream")
        self.send_response(200)
        self._set_cors()
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---------- GET ----------
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send_static("index.html")
        elif path.startswith("/static/"):
            self._send_static(path[len("/static/"):])
        else:
            self.send_error(404)

    # ---------- POST ----------
    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/chat":
            self._send_json(404, {"error": "接口不存在"})
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._send_json(400, {"error": "请求体不是合法的 JSON"})
            return

        messages = body.get("messages", [])
        clean = [
            {"role": m["role"], "content": m.get("content", "")}
            for m in messages
            if isinstance(m, dict) and m.get("role") in ("user", "assistant")
        ]
        if not clean:
            self._send_json(400, {"error": "缺少 messages 参数"})
            return

        try:
            reply = call_deepseek(clean)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            self._send_json(502, {"error": "模型接口返回错误 %d：%s" % (e.code, detail[:300])})
            return
        except urllib.error.URLError as e:
            self._send_json(502, {"error": "无法连接模型接口：%s" % e.reason})
            return
        except Exception as e:
            self._send_json(500, {"error": "服务器内部错误：%s" % e})
            return

        self._send_json(200, {"reply": reply})

    # ---------- OPTIONS（CORS 预检） ----------
    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def main():
    host = "127.0.0.1"
    port = int(os.environ.get("PORT", "5000"))
    if not API_KEY:
        print("警告：未检测到 API Key，请在 .env 文件中设置 DEEPSEEK_API_KEY")
    print("服务已启动：http://%s:%d  (Ctrl+C 停止)" % (host, port))
    server = ThreadingHTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
        server.server_close()


if __name__ == "__main__":
    main()
