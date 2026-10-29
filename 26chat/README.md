# AI 女友对话机器人 💗

一个可以「注册登录 + 自定义性格 + 起名字」的 AI 女友聊天机器人，聊天记录永久保存。前端使用 HTML / CSS / JavaScript / axios，后端使用 Python（**零第三方依赖，仅标准库**），对接**智谱 BigModel 的 GLM 大模型**。

## 功能

- 注册 / 登录：用户名 + 密码存入本地 SQLite（密码加盐哈希，不存明文）
- 聊天记录持久化：按「**登录用户名 + 女友性格 + 女友名字**」三键归档，三键完全一致才加载历史记录，否则从零开始
- 启动时选择女友性格（10 种：敏感细腻 / 直球爽快 / 独立清醒 / 软萌粘人 / 慢热内敛 / 理性冷静 / 小傲娇嘴硬 / 乐观乐天 / 缺乏安全感 / 强势主导）
- 自定义女友名字，AI 全程扮演设定好的女友与你对话
- 多轮对话上下文、Markdown 渲染、打字动画、刷新页面自动恢复聊天、清空对话（同步清库）、退出登录
- 后端零依赖，无需 `pip install`

## 目录结构

```
.
├── server.py          # 后端（Python 标准库：静态托管 + 注册登录 + 聊天持久化 + 对接智谱 GLM）
├── ai_girlfriend.db   # SQLite 数据库（首次启动自动创建，请勿手动删除）
├── .env               # API Key 配置（请勿提交到版本库）
└── static/
    ├── index.html     # 登录/注册页 + 设定页 + 聊天页
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

4. 第一次使用先切到「注册」创建账号，之后登录即可继续上次的对话。

## 接口一览

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/register` | POST | 注册，用户名 2~20 字符，密码 6~64 字符；重复用户名返回 409 |
| `/api/login` | POST | 登录校验；用户不存在 404（代码 401 返回），密码错误 401 |
| `/api/history` | GET | 按 `username + personality + name` 三键查询历史，不一致返回空数组 |
| `/api/chat` | POST | 聊天；每轮自动把「用户消息 + 女友回复」写入数据库 |
| `/api/clear` | POST | 清空某个三键组合的聊天记录 |

## 数据库说明

- 文件位置：项目根目录下的 `ai_girlfriend.db`，使用 Python 自带 `sqlite3`，无需安装任何东西。
- `users` 表：注册的 `username` + `password`（pbkdf2 加盐哈希，格式 `盐$摘要`），永久保存。
- `chat_history` 表：`username + personality + gf_name + role + content + created_at`，按三键建了索引。

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
- 登录态保存在浏览器 localStorage，仅适合本机自用，**请勿直接部署到公网**。
