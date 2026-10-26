const chatBody = document.getElementById('chatBody');
const input = document.getElementById('input');
const sendBtn = document.getElementById('sendBtn');
const clearBtn = document.getElementById('clearBtn');

const history = [];   // 发送给后端的对话历史（不含欢迎语）
let busy = false;

/* ---------- 工具 ---------- */
function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function now() {
  const d = new Date();
  return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
}

function scrollToBottom() {
  chatBody.scrollTop = chatBody.scrollHeight;
}

/* ---------- Markdown 渲染（轻量、XSS 安全） ---------- */
function renderMarkdown(raw) {
  const codeBlocks = [];
  let text = String(raw).replace(/\r\n/g, '\n');

  // 代码块 ```...```
  text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    codeBlocks.push('<pre><code>' + escapeHtml(code.replace(/\n$/, '')) + '</code></pre>');
    return '\u0000B' + (codeBlocks.length - 1) + '\u0000';
  });

  // 行内代码 `...`
  const inline = [];
  text = text.replace(/`([^`\n]+)`/g, (_, code) => {
    inline.push('<code>' + escapeHtml(code) + '</code>');
    return '\u0001I' + (inline.length - 1) + '\u0001';
  });

  // 转义剩余内容
  text = escapeHtml(text);

  // 加粗 / 斜体
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');

  // 标题
  text = text.replace(/^###\s+(.+)$/gm, '<h4>$1</h4>');
  text = text.replace(/^##\s+(.+)$/gm, '<h3>$1</h3>');
  text = text.replace(/^#\s+(.+)$/gm, '<h2>$1</h2>');

  // 列表（按空行分段处理）
  text = text.split(/\n{2,}/).map(block => {
    if (/^\s*[-*]\s+/.test(block)) {
      const items = block.split('\n').map(l => l.replace(/^\s*[-*]\s+/, '')).filter(Boolean);
      return '<ul>' + items.map(i => '<li>' + i + '</li>').join('') + '</ul>';
    }
    if (/^\s*\d+[.)]\s+/.test(block)) {
      const items = block.split('\n').map(l => l.replace(/^\s*\d+[.)]\s+/, '')).filter(Boolean);
      return '<ol>' + items.map(i => '<li>' + i + '</li>').join('') + '</ol>';
    }
    return block;
  }).join('\n');

  // 换行
  text = text.replace(/\n/g, '<br>');

  // 还原占位符
  text = text.replace(/\u0000B(\d+)\u0000/g, (_, i) => codeBlocks[i]);
  text = text.replace(/\u0001I(\d+)\u0001/g, (_, i) => inline[i]);

  return text;
}

/* ---------- 消息渲染 ---------- */
function createMessageEl(role, content) {
  const msg = document.createElement('div');
  msg.className = 'msg ' + role;

  if (role === 'ai') {
    msg.innerHTML =
      '<div class="avatar">AI</div>' +
      '<div class="bubble">' + renderMarkdown(content) + '</div>' +
      '<div class="time">' + now() + '</div>';
  } else {
    msg.innerHTML =
      '<div class="bubble">' + escapeHtml(content).replace(/\n/g, '<br>') + '</div>' +
      '<div class="time">' + now() + '</div>';
  }
  return msg;
}

function addMessage(role, content) {
  chatBody.appendChild(createMessageEl(role, content));
  scrollToBottom();
}

function showTyping() {
  const el = document.createElement('div');
  el.className = 'msg ai typing';
  el.id = 'typing';
  el.innerHTML =
    '<div class="avatar">AI</div>' +
    '<div class="bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>';
  chatBody.appendChild(el);
  scrollToBottom();
}

function hideTyping() {
  const el = document.getElementById('typing');
  if (el) el.remove();
}

function setBusy(b) {
  busy = b;
  sendBtn.disabled = b;
}

/* ---------- 发送 ---------- */
async function send() {
  const text = input.value.trim();
  if (!text || busy) return;

  input.value = '';
  autoResize();

  addMessage('user', text);
  history.push({ role: 'user', content: text });

  showTyping();
  setBusy(true);
  try {
    const res = await axios.post('/api/chat', { messages: history }, { timeout: 180000 });
    const reply = res.data.reply || '';
    history.push({ role: 'assistant', content: reply });
    hideTyping();
    addMessage('ai', reply);
  } catch (err) {
    hideTyping();
    const msg = (err.response && err.response.data && err.response.data.error)
      || err.message || '请求失败，请稍后重试';
    addMessage('ai', '⚠️ ' + msg);
  } finally {
    setBusy(false);
    input.focus();
  }
}

/* ---------- 输入框 ---------- */
function autoResize() {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 160) + 'px';
}

input.addEventListener('input', autoResize);
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    send();
  }
});
sendBtn.addEventListener('click', send);

/* ---------- 清空对话 ---------- */
clearBtn.addEventListener('click', () => {
  if (busy) return;
  history.length = 0;
  chatBody.innerHTML = '';
  welcome();
});

/* ---------- 欢迎语 ---------- */
function welcome() {
  addMessage('ai',
    '你好，我是 **AI 助手** 👋\n\n' +
    '我可以帮你回答问题、写代码、翻译、创作文案等。\n\n' +
    '直接输入消息开始聊天吧～');
}

welcome();
input.focus();
