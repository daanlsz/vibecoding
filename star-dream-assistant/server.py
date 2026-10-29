"""星梦智能助手 · Flask 后端服务

启动：python server.py
访问：http://localhost:5000
"""

import re
import sqlite3
import sys

import requests
from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS

import db
from config import (
    ANTHROPIC_AUTH_TOKEN,
    ANTHROPIC_BASE_URL,
    ANTHROPIC_MODEL,
    DEBUG,
    HOST,
    PORT,
    REQUEST_TIMEOUT,
    SECRET_KEY,
)

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)  # 允许前端跨域请求
app.secret_key = SECRET_KEY  # 登录 session 签名密钥

# 启动时建库建表（幂等）
db.init_db()


# ---------- 系统提示词 ----------

HOROSCOPE_SYSTEM_PROMPT = """你是一位专业的星座分析师和命理顾问，拥有多年的星座研究经验。请根据用户提供的个人信息，进行详细的星座分析。

分析要求：
1. 首先分析该用户所属星座的基本性格特征（3-5 个要点）
2. 结合用户的出生日期，分析更精确的星座能量和行星影响
3. 如果用户提出了具体问题，请针对性地给出建议和分析
4. 最后给出近期运势概览（事业、感情、财运、健康各 1-2 句话）

回复风格：
- 语言温暖、专业、有深度
- 使用清晰的分段结构
- 适当使用 emoji 增加可读性
- 总字数控制在 500-800 字之间
- 在末尾加上免责声明："以上分析仅供娱乐参考，人生重大决策请理性判断。"
"""

DREAM_SYSTEM_PROMPT = """你是一位精通周公解梦的梦境解析大师，同时了解现代心理学对梦境的研究。请根据用户描述的梦境内容进行深入解析。

解析要求：
1. 梦境概述：简要概括梦境的核心元素和场景
2. 象征解读：分析梦境中关键元素的象征意义（如：飞翔代表渴望自由，蝴蝶象征蜕变等）
3. 心理映射：从心理学角度分析这个梦境可能反映的内心状态或情绪
4. 传统解梦：参考周公解梦的传统说法，给出对应解释
5. 生活建议：根据梦境分析，给出 2-3 条生活建议
6. 幸运提示：给出与该梦境相关的幸运数字（1-2 个）和幸运颜色

回复风格：
- 语言温和、有洞察力
- 使用清晰的分段结构，每段有小标题
- 适当使用 emoji 增加可读性
- 总字数控制在 400-700 字之间
- 在末尾加上免责声明："以上解梦仅供娱乐参考，请理性看待。"

输出格式（重要）：
- 正文按上述结构输出，Markdown 分段
- 全文最后一行必须单独输出关键词行，格式严格为：关键词：词1、词2、词3、词4（4-6 个概括梦境核心的关键词）
"""


# ---------- 大模型调用 ----------

class LlmError(Exception):
    """大模型调用异常；status 为返回给前端的 HTTP 状态码"""

    def __init__(self, message, status=500):
        super().__init__(message)
        self.status = status


def call_llm(system_prompt, user_message):
    """调用智谱 GLM（Anthropic 兼容端点），返回生成的文本"""
    if not ANTHROPIC_AUTH_TOKEN:
        raise LlmError("服务未配置：缺少大模型 API Key")

    url = f"{ANTHROPIC_BASE_URL.rstrip('/')}/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_AUTH_TOKEN,
        "Authorization": f"Bearer {ANTHROPIC_AUTH_TOKEN}",
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 2048,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.Timeout:
        raise LlmError("大模型 API 请求超时，请稍后重试", 504)
    except requests.exceptions.RequestException as exc:
        print(f"[LLM] 连接大模型服务失败: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise LlmError("无法连接大模型服务，请稍后重试", 502)

    if resp.status_code != 200:
        detail = ""
        try:
            detail = resp.json().get("error", {}).get("message", "")
        except ValueError:
            pass
        message = f"大模型 API 返回异常（{resp.status_code}）"
        if detail:
            message += f":{detail}"
        raise LlmError(message, 502)

    data = resp.json()
    text = "".join(
        block.get("text", "")
        for block in data.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    ).strip()
    if not text:
        raise LlmError("大模型返回内容为空", 502)
    return text


KEYWORD_LINE_RE = re.compile(r"^关键词\s*[:：]\s*(.+)$", re.MULTILINE)


def extract_keywords(text):
    """从 AI 文本末尾提取关键词行，返回 (正文, 关键词列表)"""
    match = KEYWORD_LINE_RE.search(text)
    if not match:
        return text, []
    keywords = [kw.strip() for kw in re.split(r"[、,，;；]", match.group(1)) if kw.strip()][:8]
    body = KEYWORD_LINE_RE.sub("", text).rstrip()
    return body, keywords


# ---------- 工具 ----------

def error_response(message, status):
    return jsonify({"success": False, "error": message}), status


# ---------- 登录态 ----------

def current_user():
    """获取当前登录用户（dict）；未登录或用户已不存在时返回 None"""
    username = session.get("username")
    if not username:
        return None
    return db.get_user_by_name(username)


# ---------- API：注册 ----------

@app.post("/api/register")
def register():
    body = request.get_json(silent=True) or {}
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))

    if not (2 <= len(username) <= 20):
        return error_response("用户名长度需在 2-20 个字符之间", 400)
    if not (6 <= len(password) <= 32):
        return error_response("密码长度需在 6-32 个字符之间", 400)

    try:
        db.create_user(username, password)
    except ValueError as exc:
        return error_response(str(exc), 409)

    # 注册成功即自动登录
    session["username"] = username
    return jsonify({"success": True, "data": {"username": username}})


# ---------- API：登录 ----------

@app.post("/api/login")
def login():
    body = request.get_json(silent=True) or {}
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))

    user = db.get_user_by_name(username) if username else None
    if not user or not db.verify_password(password, user["salt"], user["password_hash"]):
        # 用户名或密码不一致：拒绝登录，不加载任何历史记录
        return error_response("用户名或密码错误", 401)

    session["username"] = user["username"]
    return jsonify({"success": True, "data": {"username": user["username"]}})


# ---------- API：退出登录 ----------

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"success": True})


# ---------- API：登录状态查询 ----------

@app.get("/api/session")
def session_info():
    logged_in = "username" in session
    return jsonify({
        "success": True,
        "data": {"logged_in": logged_in, "username": session.get("username")},
    })


# ---------- API：历史解析记录 ----------

@app.get("/api/history")
def history_list():
    user = current_user()
    if not user:
        return error_response("未登录或登录已过期", 401)

    record_type = request.args.get("type", "")
    if record_type not in ("horoscope", "dream"):
        return error_response("type 参数需为 horoscope 或 dream", 400)

    records = db.list_records(user["id"], record_type)
    return jsonify({"success": True, "data": {"records": records}})


@app.get("/api/history/<int:record_id>")
def history_detail(record_id):
    user = current_user()
    if not user:
        return error_response("未登录或登录已过期", 401)

    record = db.get_record(user["id"], record_id)
    if not record:
        return error_response("记录不存在", 404)
    return jsonify({"success": True, "data": record})


# ---------- 页面路由 ----------

@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ---------- API：星座分析测算 ----------

@app.post("/api/horoscope")
def horoscope():
    user = current_user()
    if not user:
        return error_response("请先登录后再使用", 401)

    body = request.get_json(silent=True) or {}
    name = str(body.get("name", "")).strip()
    zodiac = str(body.get("zodiac", "")).strip()
    birthday = str(body.get("birthday", "")).strip()
    question = str(body.get("question", "")).strip()

    missing = [label for label, value in (
        ("name", name), ("zodiac", zodiac), ("birthday", birthday)
    ) if not value]
    if missing:
        return error_response(f"缺少必填字段：{'、'.join(missing)}", 400)

    user_message = (
        "用户信息：\n"
        f"- 姓名：{name}\n"
        f"- 星座：{zodiac}\n"
        f"- 出生日期：{birthday}\n"
        f"- 咨询问题：{question or '无'}"
    )

    try:
        result = call_llm(HOROSCOPE_SYSTEM_PROMPT, user_message)
    except LlmError as exc:
        return error_response(str(exc), exc.status)

    # 解析结果持久化到当前用户名下（入库失败不影响本次结果返回）
    record = None
    try:
        record = db.add_record(
            user["id"],
            "horoscope",
            title=f"{zodiac} · {name}",
            input_data={"name": name, "zodiac": zodiac, "birthday": birthday, "question": question},
            result=result,
            keywords=[],
        )
    except sqlite3.Error as exc:
        print(f"[DB] 保存星座分析记录失败: {exc}", file=sys.stderr, flush=True)

    return jsonify({
        "success": True,
        "data": {"result": result, "zodiac": zodiac, "name": name, "record": record},
    })


# ---------- API：周公解梦 ----------

@app.post("/api/dream")
def dream():
    user = current_user()
    if not user:
        return error_response("请先登录后再使用", 401)

    body = request.get_json(silent=True) or {}
    dream_content = str(body.get("dream_content", "")).strip()
    dream_tags = body.get("dream_tags") or []
    dream_time = str(body.get("dream_time", "")).strip()

    if not dream_content:
        return error_response("缺少必填字段：dream_content", 400)
    if len(dream_content) < 10:
        return error_response("梦境描述至少需要 10 个字符", 400)
    if not isinstance(dream_tags, list):
        return error_response("dream_tags 应为字符串数组", 400)

    user_message = (
        "我的梦境描述：\n"
        f"{dream_content}\n\n"
        f"梦境类型标签：{'、'.join(str(t) for t in dream_tags) if dream_tags else '无'}\n"
        f"做梦时间：{dream_time or '未提供'}"
    )

    try:
        text = call_llm(DREAM_SYSTEM_PROMPT, user_message)
    except LlmError as exc:
        return error_response(str(exc), exc.status)

    result, keywords = extract_keywords(text)

    # 解析结果持久化到当前用户名下（入库失败不影响本次结果返回）
    # 列表标题取梦境描述前 50 个字符（按码点截取，避免切坏 emoji）
    chars = list(dream_content)
    title = "".join(chars[:50]) + ("..." if len(chars) > 50 else "")
    record = None
    try:
        record = db.add_record(
            user["id"],
            "dream",
            title=title,
            input_data={
                "dream_content": dream_content,
                "dream_tags": [str(t) for t in dream_tags],
                "dream_time": dream_time,
            },
            result=result,
            keywords=keywords,
        )
    except sqlite3.Error as exc:
        print(f"[DB] 保存解梦记录失败: {exc}", file=sys.stderr, flush=True)

    return jsonify({
        "success": True,
        "data": {"result": result, "keywords": keywords, "record": record},
    })


if __name__ == "__main__":
    print("=" * 44)
    print("星梦智能助手服务已启动")
    print(f"访问地址：http://localhost:{PORT}")
    print("=" * 44)
    app.run(host=HOST, port=PORT, debug=DEBUG)
