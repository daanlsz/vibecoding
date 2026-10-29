"""星梦智能助手 · 配置文件"""

import os

# 大模型 API 配置（智谱 GLM · Anthropic 兼容端点）
# 支持通过环境变量覆盖，避免密钥硬编码进版本库；strip() 防止复制时带入的空白字符破坏请求头
ANTHROPIC_AUTH_TOKEN = os.getenv(
    "ANTHROPIC_AUTH_TOKEN",
    "1661b81254cd46c6be1f9b56f104597d.hvOubx9lym0Y6uy6",
).strip()
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://open.bigmodel.cn/api/anthropic")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "GLM-5.3-Flash")

# 服务配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("DEBUG", "1") == "1"  # 开发模式：debug + 自动重载

# 大模型请求超时（秒）
# 注：生成 500-800 字中文分析 + 模型思考耗时，实测超过 30 秒，故设为 90 秒
REQUEST_TIMEOUT = 90
