# AI 聊天机器人

一个简洁美观的 AI 聊天机器人，前端使用 HTML / CSS / JavaScript / axios，后端使用 Python（**零第三方依赖，仅标准库**）。

## 功能

- 美观的聊天界面，支持 Markdown 渲染、打字动画、清空对话
- 对接 DeepSeek 大模型（Anthropic 兼容接口）
- 多轮对话上下文
- 后端零依赖，无需 `pip install`

## 目录结构

```
.
├── server.py          # 后端（Python 标准库）
├── .env               # API Key 配置（请勿提交到版本库）
└── static/
    ├── index.html
    ├── style.css
    ├── script.js
    └── axios.min.js   # 本地化的 axios，离线可用
```

## 运行

1. 确认已安装 Python 3.8+：
   ```
   python --version
   ```

2. 启动服务：
   ```
   python server.py
   ```

3. 浏览器打开：<http://127.0.0.1:5000>

## 配置

API Key 默认从项目根目录的 `.env` 文件读取：

```
DEEPSEEK_API_KEY=sk-xxxx
```

也可以通过环境变量设置（优先级更高）：

- Windows PowerShell：`$env:DEEPSEEK_API_KEY="sk-xxxx"`
- macOS / Linux：`export DEEPSEEK_API_KEY=sk-xxxx`

模型名称可通过 `DEEPSEEK_MODEL` 环境变量修改（默认 `deepseek-v4-pro`）。

## 说明

- 接口地址：`https://api.deepseek.com/anthropic/v1/messages`（Anthropic 兼容格式，使用 `x-api-key` 鉴权）。
