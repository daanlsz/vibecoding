# AI 女友对话机器人 💗

一个可以「自定义性格 + 起名字」的 AI 女友聊天机器人。前端使用 HTML / CSS / JavaScript / axios，后端使用 Python（**零第三方依赖，仅标准库**），对接**智谱 BigModel 的 GLM 大模型**。

## 功能

- 启动时选择女友性格（10 种：敏感细腻 / 直球爽快 / 独立清醒 / 软萌粘人 / 慢热内敛 / 理性冷静 / 小傲娇嘴硬 / 乐观乐天 / 缺乏安全感 / 强势主导）
- 自定义女友名字
- 进入聊天后，AI 全程扮演设定好的女友与你对话
- 多轮对话上下文、Markdown 渲染、打字动画、清空对话、随时重新设定女友
- 后端零依赖，无需 `pip install`

## 目录结构

```
.
├── server.py          # 后端（Python 标准库，对接智谱 GLM）
├── .env               # API Key 配置（请勿提交到版本库）
└── static/
    ├── index.html     # 设定页 + 聊天页
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
ZHIPU_API_KEY=你的智谱 API Key
GLM_MODEL=glm-5.3
GLM_REASONING_EFFORT=low   # 思考强度：low（快） / medium / high（深）
GLM_TEMPERATURE=0.95       # 回复活泼度，越大越灵动，越小越稳定
GLM_TOP_P=0.95             # 采样范围，配合 temperature 使用
```

也可以通过环境变量设置（优先级更高）：

- Windows PowerShell：`$env:ZHIPU_API_KEY="你的Key"`
- macOS / Linux：`export ZHIPU_API_KEY="你的Key"`

## 说明

- 接口地址：`https://open.bigmodel.cn/api/paas/v4/chat/completions`（OpenAI 兼容格式，使用 `Authorization: Bearer <key>` 鉴权）。
- 模型名可通过 `GLM_MODEL` 环境变量修改（默认 `glm-5.3`）。
- `glm-5.3` 是「始终思考」的推理模型，无法关闭思考，但可用 `GLM_REASONING_EFFORT` 控制思考强度（`low` 时响应约 2~3 秒，`high` 更慢但更深入）。若想完全去掉推理延迟，可换成 `glm-4-flash` 这类非推理模型。
- 前端的性格卡片与后端的人设描述通过相同的 `id`（如 `sensitive`、`tsundere` 等）对应。
