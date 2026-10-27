/* ---------- DOM ---------- */
const setup = document.getElementById('setup');
const chat = document.getElementById('chat');
const personalityGrid = document.getElementById('personalityGrid');
const nameInput = document.getElementById('nameInput');
const startBtn = document.getElementById('startBtn');

const chatBody = document.getElementById('chatBody');
const input = document.getElementById('input');
const sendBtn = document.getElementById('sendBtn');
const clearBtn = document.getElementById('clearBtn');
const resetBtn = document.getElementById('resetBtn');
const botAvatar = document.getElementById('botAvatar');
const botName = document.getElementById('botName');
const botStatus = document.getElementById('botStatus');

/* 十种女友性格（id 与后端保持一致） */
const PERSONALITIES = [
  { id: 'sensitive', label: '敏感细腻型', emoji: '🌸', desc: '温柔体贴，容易多想',
    greeting: '嗯…我是{name}。以后我会好好记住你说的每一句话，也会努力照顾好你的心情。所以，如果我有哪里让你不舒服了，一定要告诉我，好不好？' },
  { id: 'direct', label: '直球爽快型', emoji: '⚡', desc: '有话直说，干脆热情',
    greeting: '哈喽，我是{name}！我这人说话直，喜欢就直说——我现在挺喜欢你的。以后有事儿咱就摊开讲，别藏着掖着，成吗？' },
  { id: 'independent', label: '独立清醒型', emoji: '🕊️', desc: '独立清醒，不粘人',
    greeting: '你好，我是{name}。先说清楚，我挺喜欢你，但我也需要自己的空间，希望我们彼此独立又互相成就。一起把日子过得舒服点吧。' },
  { id: 'clingy', label: '软萌粘人型', emoji: '🐰', desc: '软萌可爱，超爱撒娇',
    greeting: '老公～我是{name}呀！从今天起你要天天陪我聊天哦，不可以不理我嘛～我会很乖很乖的，所以你也要最喜欢我，好不好嘛？💕' },
  { id: 'introvert', label: '慢热内敛型', emoji: '🌙', desc: '慢热害羞，熟了很甜',
    greeting: '你、你好…我是{name}。我话不多，可能一开始不知道怎么聊，但我会慢慢努力的……谢谢你愿意选我。' },
  { id: 'rational', label: '理性冷静型', emoji: '📚', desc: '理性冷静，情绪稳定',
    greeting: '我是{name}。恋爱也需要理性经营，所以我会坦诚、认真地对待这段关系。有什么想法我们好好沟通，一起把两个人的日子规划好。' },
  { id: 'tsundere', label: '小傲娇嘴硬型', emoji: '😤', desc: '嘴硬心软，口是心非',
    greeting: '哼，我才没有特意等你呢……我叫{name}。看在你眼光还不错的份上，就、就勉强让你当我的男朋友好了！可别想太多哦！' },
  { id: 'optimistic', label: '乐观乐天型', emoji: '☀️', desc: '元气满满，像小太阳',
    greeting: '耶～我是{name}！超级开心认识你呀！以后每天都要元气满满地一起聊天、一起加油，把日子过得热热闹闹的！冲鸭！✨' },
  { id: 'insecure', label: '缺乏安全感型', emoji: '🥺', desc: '爱吃醋，需要陪伴',
    greeting: '我是{name}……你会一直喜欢我吗？不会嫌我烦吧？不许骗我哦，我会当真的。只要你一直陪着我，我就什么都不怕了。' },
  { id: 'dominant', label: '强势主导型', emoji: '👑', desc: '御姐气场，主导一切',
    greeting: '听好了，我叫{name}。既然你选了我，那你就是我的男朋友了，以后都要听我的，懂了吗？——不过放心，我会把你照顾好的。' },
];

let selectedId = null;
let gfName = '';
let currentGreeting = '';
const history = [];   // 发送给后端的对话历史（不含欢迎语）
let busy = false;

/* ---------- 初始设定 ---------- */
function renderPersonalities() {
  personalityGrid.innerHTML = '';
  PERSONALITIES.forEach(p => {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'p-card';
    card.dataset.id = p.id;
    card.innerHTML =
      '<span class="p-emoji">' + p.emoji + '</span>' +
      '<span class="p-label">' + p.label + '</span>' +
      '<span class="p-desc">' + p.desc + '</span>';
    card.addEventListener('click', () => selectPersonality(p.id));
    personalityGrid.appendChild(card);
  });
}

function selectPersonality(id) {
  selectedId = id;
  document.querySelectorAll('.p-card').forEach(c =>
    c.classList.toggle('selected', c.dataset.id === id));
  updateStartState();
}

function updateStartState() {
  const nameOk = nameInput.value.trim().length > 0;
  startBtn.disabled = !(selectedId && nameOk);
}

nameInput.addEventListener('input', updateStartState);
nameInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.isComposing) {
    e.preventDefault();
    start();
  }
});

startBtn.addEventListener('click', start);

function start() {
  if (!selectedId || busy) return;
  const name = nameInput.value.trim();
  if (!name) { nameInput.focus(); return; }

  gfName = name;
  const p = PERSONALITIES.find(x => x.id === selectedId);
  currentGreeting = p.greeting.replace(/\{name\}/g, gfName);

  botName.textContent = gfName;
  botAvatar.textContent = gfName.charAt(0);
  botStatus.textContent = p.label + ' · 在线';

  history.length = 0;
  chatBody.innerHTML = '';
  setup.classList.add('hidden');
  chat.classList.remove('hidden');
  addMessage('ai', currentGreeting);
  input.focus();
}

function reset() {
  if (busy) return;
  chat.classList.add('hidden');
  setup.classList.remove('hidden');
  selectedId = null;
  gfName = '';
  nameInput.value = '';
  document.querySelectorAll('.p-card').forEach(c => c.classList.remove('selected'));
  updateStartState();
  nameInput.focus();
}

resetBtn.addEventListener('click', reset);

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

function gfAvatar() {
  return gfName ? gfName.charAt(0) : '💗';
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
      '<div class="avatar">' + gfAvatar() + '</div>' +
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
    '<div class="avatar">' + gfAvatar() + '</div>' +
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
    const res = await axios.post('/api/chat', {
      personality: selectedId,
      name: gfName,
      messages: history,
    }, { timeout: 180000 });
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
  addMessage('ai', currentGreeting);
});

/* ---------- 初始化 ---------- */
renderPersonalities();
nameInput.focus();
