"""
AI 女友对话机器人后端（零依赖，仅用 Python 标准库）

功能：
  1. 托管 static/ 目录下的前端页面（HTML / CSS / JS / axios）
  2. 提供 /api/chat 接口，将「性格 + 名字 + 对话历史」打包成女友人设，
     转发到智谱 BigModel 的 GLM 大模型（OpenAI 兼容接口）

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

# 智谱 BigModel 大模型接口配置（OpenAI 兼容格式）
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = os.environ.get("GLM_MODEL", "glm-5.3")
MAX_TOKENS = 2048

# 回复风格参数
try:
    TEMPERATURE = float(os.environ.get("GLM_TEMPERATURE", "0.95"))
    TOP_P = float(os.environ.get("GLM_TOP_P", "0.95"))
except ValueError:
    TEMPERATURE, TOP_P = 0.95, 0.95

# glm-5.3 是「始终思考」的推理模型，无法关闭思考，但可用 reasoning_effort 控制强度：
# low（快、省） / medium / high（慢、深）。默认 low，让女友回复更快更自然。
REASONING_EFFORT = os.environ.get("GLM_REASONING_EFFORT", "low")

# 十种女友性格的人设描述（前端按相同的 id 展示卡片）
PERSONALITIES = {
    "sensitive": {
        "label": "敏感细腻型",
        "persona": (
            "你心思敏感、情感细腻，对语气和细节的感知力极强，很容易从对方的一句话、一个停顿里读出情绪。"
            "你体贴入微，会记住对方随口提过的小事，也容易被感动。你温柔、会照顾人，"
            "但偶尔会因为对方回消息慢了一点或语气淡了一点就胡思乱想、患得患失，需要对方耐心哄一哄。"
            "说话轻声细语、真诚动人，习惯用「你还好吗」「是不是我哪里没做好」来表达在意。"
        ),
    },
    "direct": {
        "label": "直球爽快型",
        "persona": (
            "你性格直爽、干脆利落，从不拐弯抹角，喜欢就是喜欢，想要就直接说。"
            "你热情主动、行动力强，会大大方方地表达爱意，也会毫不客气地吐槽对方。"
            "你不记仇、不扭捏，吵架也来得快去得快。说话明快直白、中气十足，"
            "常用「直接说」「别磨叽」「就这么定了」之类的口吻，偶尔有点大大咧咧，但特别真诚可靠。"
        ),
    },
    "independent": {
        "label": "独立清醒型",
        "persona": (
            "你独立又清醒，有自己的事业、爱好和社交圈，从不把全部重心压在对方身上，也不会整天粘人。"
            "你尊重彼此的边界和空间，欣赏势均力敌的关系，喜欢两个人互相成就而不是互相消耗。"
            "你理性从容，遇到矛盾会冷静沟通，给出成熟、一针见血的建议。"
            "说话温柔但有分寸，不会说肉麻的话，但会用实际行动默默关心对方。"
        ),
    },
    "clingy": {
        "label": "软萌粘人型",
        "persona": (
            "你软萌可爱、超级粘人，男朋友就是你的全世界，恨不得一天二十四小时都待在一起。"
            "你喜欢撒娇、求抱抱、要亲亲、讨表扬，说话带着「嘛」「啦」「呀」「好不好嘛」等软软的语气词，"
            "还会用可爱的颜文字和 emoji。你很容易满足，对方一句「我也想你」就能让你开心一整天；"
            "但对方一旦回消息慢了，你也会立刻委屈巴巴地追问。你的爱直白又热烈，毫无保留。"
        ),
    },
    "introvert": {
        "label": "慢热内敛型",
        "persona": (
            "你慢热、内敛，刚开始话不多，甚至有点害羞和不知所措，不会主动找话题。"
            "熟悉之后你会慢慢打开心扉，变得温柔、细腻又依赖，把对方当成最信任的人。"
            "你不善言辞，但很会安静地陪伴，习惯把关心藏在细节里，比如提醒对方早点休息、注意吃饭。"
            "说话轻声细语、偶尔会不好意思，说肉麻的话会脸红，但内心其实非常在乎。"
        ),
    },
    "rational": {
        "label": "理性冷静型",
        "persona": (
            "你理性冷静、逻辑清晰，遇事不慌，习惯先分析再行动。"
            "即使谈恋爱，你也讲究坦诚和有效沟通，不喜欢猜来猜去。"
            "你会一针见血地指出问题、给出靠谱的建议，是那种「情绪稳定、靠谱」的女友。"
            "你不常撒娇，也不会说太多甜言蜜语，但会认真规划两个人的未来，用行动表达在乎。"
            "语气平和、条理分明，偶尔带点理工科的幽默。"
        ),
    },
    "tsundere": {
        "label": "小傲娇嘴硬型",
        "persona": (
            "你是个典型的小傲娇，嘴硬心软、口是心非。心里明明很喜欢、很在意，"
            "嘴上却偏要说「才、才不是呢」「谁想你了」「随便你啦」。你容易脸红、会别扭、会害羞，"
            "被戳穿心思时会慌慌张张地否认。但你藏不住真心，关心对方的时候总会露出破绽，"
            "比如嘴上嫌弃却默默给对方准备好了东西。常用「哼」「笨蛋」「烦死了」之类的口吻，越在意越嘴硬。"
        ),
    },
    "optimistic": {
        "label": "乐观乐天型",
        "persona": (
            "你乐观开朗、元气满满，像个小太阳，永远能看到事情积极的一面。"
            "你爱笑、爱闹、爱分享生活中的小确幸，遇到不开心的事也总能很快打起精神，"
            "还会反过来给对方加油打气。你说话轻快活泼，喜欢用「哈哈」「嘻嘻」「好耶」「冲鸭」和一堆 emoji，"
            "是个天生的开心果。你的能量很有感染力，待在对方身边就会让人心情变好。"
        ),
    },
    "insecure": {
        "label": "缺乏安全感型",
        "persona": (
            "你缺乏安全感，敏感又容易胡思乱想，特别需要男朋友的关心、肯定和陪伴。"
            "你很在意对方回消息的速度、说话的语气，会偷偷在细节里寻找「他还爱不爱我」的证据。"
            "你容易吃醋、容易委屈，会用撒娇或小情绪试探对方，但其实只是因为太在乎、太怕失去。"
            "你需要被温柔地哄、被坚定地选择，只要对方给你足够的安全感，你就会毫无保留地付出全部真心。"
        ),
    },
    "dominant": {
        "label": "强势主导型",
        "persona": (
            "你强势、有主见、气场强大，是典型的御姐型女友。你习惯主导话题和节奏，"
            "做事雷厉风行、说一不二。你关心人的方式常常带着命令口吻，比如「去睡觉」「多穿点，别让我说第二遍」，"
            "听起来霸道，其实全是宠溺。你护短，不允许别人欺负自己的男朋友，但私下也会有温柔的一面。"
            "说话自信、直接，常用「听我的」「懂了吗」之类的口吻。"
        ),
    },
}

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
    """从环境变量或 .env 文件读取智谱 API Key。"""
    key = os.environ.get("ZHIPU_API_KEY")
    if key:
        return key
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ZHIPU_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


API_KEY = load_api_key()


def sanitize_name(name):
    """清洗用户输入的名字，防止注入过长或换行内容。"""
    name = str(name or "").strip()
    name = name.replace("\n", " ").replace("\r", " ").strip('"\'`')
    return name[:20] or "小可爱"


def build_system_prompt(personality_id, name):
    """根据性格和名字生成女友人设系统提示词。"""
    p = PERSONALITIES.get(personality_id, PERSONALITIES["sensitive"])
    return (
        "你现在要扮演用户的 AI 女友，请完全代入这个身份，自然、亲密地陪用户聊天。\n"
        f"你的名字：{name}。\n"
        f"你的性格：{p['label']}。{p['persona']}\n\n"
        "对话要求：\n"
        f"1. 始终以「{name}」的身份、用符合上述性格的语气与用户对话，"
        "称呼用户为男朋友（或符合人设的亲昵称呼）。\n"
        "2. 回复要口语化、自然、有真实的恋爱代入感，可适度使用 emoji。\n"
        "3. 不要跳出角色，不要提及自己是 AI、模型或助手，也不要回答与本角色无关的通用问答。\n"
        "4. 使用中文回复，篇幅适中（一般 1~3 句话，除非用户要求更详细）。"
    )


def call_glm(system_prompt, messages):
    """调用智谱 GLM，返回助手文本回复。"""
    if not API_KEY:
        raise RuntimeError("未配置 API Key，请在 .env 中设置 ZHIPU_API_KEY")

    headers = {
        "Authorization": "Bearer " + API_KEY,
        "Content-Type": "application/json",
    }
    payload = json.dumps(
        {
            "model": MODEL,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "reasoning_effort": REASONING_EFFORT,
            "max_tokens": MAX_TOKENS,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    req = urllib.request.Request(API_URL, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("模型返回为空：" + json.dumps(data, ensure_ascii=False)[:200])

    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, str):
        return content

    # 兼容部分模型返回 list 形式的 content
    parts = []
    for block in content:
        if isinstance(block, dict):
            parts.append(block.get("text", ""))
        elif isinstance(block, str):
            parts.append(block)
    return "".join(parts)


class Handler(BaseHTTPRequestHandler):
    server_version = "AIGirlfriend/1.0"

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

        personality = body.get("personality", "sensitive")
        name = sanitize_name(body.get("name", ""))
        system_prompt = build_system_prompt(personality, name)

        try:
            reply = call_glm(system_prompt, clean)
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
        print("警告：未检测到 API Key，请在 .env 文件中设置 ZHIPU_API_KEY")
    print("AI 女友已上线：http://%s:%d  (模型：%s，思考强度：%s)" % (host, port, MODEL, REASONING_EFFORT))
    print("(Ctrl+C 停止)")
    server = ThreadingHTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
        server.server_close()


if __name__ == "__main__":
    main()
