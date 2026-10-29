/* ============================================
   星梦智能助手 · 全局脚本
   通过 body[data-page] 分发各页面初始化逻辑
   ============================================ */

/** 12 星座数据 */
const ZODIAC_SIGNS = [
  { symbol: '♈', name: '白羊座' },
  { symbol: '♉', name: '金牛座' },
  { symbol: '♊', name: '双子座' },
  { symbol: '♋', name: '巨蟹座' },
  { symbol: '♌', name: '狮子座' },
  { symbol: '♍', name: '处女座' },
  { symbol: '♎', name: '天秤座' },
  { symbol: '♏', name: '天蝎座' },
  { symbol: '♐', name: '射手座' },
  { symbol: '♑', name: '摩羯座' },
  { symbol: '♒', name: '水瓶座' },
  { symbol: '♓', name: '双鱼座' }
];

/** 梦境类型标签（可多选） */
const DREAM_TAGS = [
  { emoji: '🌊', label: '水/海洋' },
  { emoji: '🏔️', label: '山/高处' },
  { emoji: '🐾', label: '动物' },
  { emoji: '👤', label: '人物/亲人' },
  { emoji: '💀', label: '死亡/离别' },
  { emoji: '💰', label: '金钱/财富' },
  { emoji: '✈️', label: '旅行/飞行' },
  { emoji: '😱', label: '追赶/逃跑' },
  { emoji: '🏠', label: '房屋/建筑' },
  { emoji: '💒', label: '婚礼/喜事' }
];

/** 简写选择器 */
const $ = (selector) => document.querySelector(selector);

/* ---------- 字段错误提示 ---------- */
function showFieldError(key, message) {
  const el = $(`#${key}-error`);
  if (!el) return;
  el.textContent = message;
  el.classList.add('visible');
}

function clearFieldError(key) {
  const el = $(`#${key}-error`);
  if (!el) return;
  el.textContent = '';
  el.classList.remove('visible');
}

/** 结果卡片错误提示（含重试按钮），horoscope / dream 共用 */
function showError(message) {
  const contentEl = $('#result-content');
  const textEl = $('#error-text');
  const boxEl = $('#result-error');
  if (!textEl || !boxEl) return;
  if (contentEl) contentEl.innerHTML = '';
  textEl.textContent = message;
  boxEl.classList.remove('hidden');
}

/** 防 XSS：转义 HTML 特殊字符 */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/* ---------- 页面分发 ---------- */
document.addEventListener('DOMContentLoaded', () => {
  switch (document.body.dataset.page) {
    case 'horoscope':
      initHoroscopePage();
      break;
    case 'dream':
      initDreamPage();
      break;
  }
});

/* ============================================
   星座分析测算页
   ============================================ */
function initHoroscopePage() {
  const form = $('#horoscope-form');
  const nameInput = $('#name');
  const birthdayInput = $('#birthday');
  const questionInput = $('#question');
  const zodiacGrid = $('#zodiac-grid');
  const submitBtn = $('#submit-btn');
  const resultCard = $('#result-card');

  let selectedZodiac = '';

  /* 出生日期：限制不可选未来日期 */
  birthdayInput.max = new Date().toISOString().slice(0, 10);

  /* 生成 12 星座网格 */
  ZODIAC_SIGNS.forEach((sign) => {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'zodiac-item';
    item.setAttribute('aria-pressed', 'false');
    item.innerHTML = `<span class="zodiac-icon">${sign.symbol}</span><span>${sign.name}</span>`;
    item.addEventListener('click', () => {
      zodiacGrid.querySelectorAll('.zodiac-item.selected').forEach((el) => {
        el.classList.remove('selected');
        el.setAttribute('aria-pressed', 'false');
      });
      item.classList.add('selected');
      item.setAttribute('aria-pressed', 'true');
      selectedZodiac = sign.name;
      clearFieldError('zodiac');
      updateSubmitState();
    });
    zodiacGrid.appendChild(item);
  });

  /* 日期占位文字：有值时隐藏 */
  const datePlaceholder = $('#date-placeholder');
  const syncDatePlaceholder = () => {
    datePlaceholder.classList.toggle('hidden', Boolean(birthdayInput.value));
  };
  birthdayInput.addEventListener('change', () => {
    syncDatePlaceholder();
    clearFieldError('birthday');
    updateSubmitState();
  });

  nameInput.addEventListener('input', () => {
    clearFieldError('name');
    updateSubmitState();
  });

  /* 表单完整性 → 提交按钮禁用状态 */
  function updateSubmitState() {
    submitBtn.disabled = !(nameInput.value.trim() && selectedZodiac && birthdayInput.value);
  }

  /* 表单校验：姓名 / 星座 / 出生日期必填 */
  function validateForm() {
    let valid = true;
    if (!nameInput.value.trim()) {
      showFieldError('name', '请输入您的姓名');
      valid = false;
    }
    if (!selectedZodiac) {
      showFieldError('zodiac', '请选择您的星座');
      valid = false;
    }
    if (!birthdayInput.value) {
      showFieldError('birthday', '请选择出生日期');
      valid = false;
    }
    return valid;
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (!validateForm()) return;
    requestAnalysis();
  });

  $('#retry-btn').addEventListener('click', requestAnalysis);

  /* 请求 AI 分析：POST /api/horoscope */
  async function requestAnalysis() {
    const payload = {
      name: nameInput.value.trim(),
      zodiac: selectedZodiac,
      birthday: birthdayInput.value,
      question: questionInput.value.trim()
    };

    submitBtn.disabled = true;
    resultCard.classList.remove('hidden');
    $('#result-summary').innerHTML = '';
    $('#result-content').innerHTML = '';
    $('#result-error').classList.add('hidden');
    $('#loading').classList.remove('hidden');
    resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });

    try {
      const res = await fetch('/api/horoscope', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(`服务返回异常（${res.status}），请稍后重试`);
      const data = await res.json();
      renderResult(payload, data.data ?? data); /* 解包 {success, data:{...}} 包装 */
    } catch (err) {
      showError(err instanceof Error ? err.message : '网络异常，请稍后重试');
    } finally {
      $('#loading').classList.add('hidden');
      updateSubmitState();
    }
  }

  /* 渲染结果：信息摘要 + 多段落分析内容 */
  function renderResult(payload, data) {
    $('#result-summary').innerHTML = `
      <span class="summary-chip">姓名：${escapeHtml(payload.name)}</span>
      <span class="summary-chip">星座：${escapeHtml(payload.zodiac)}</span>
      <span class="summary-chip">生日：${escapeHtml(payload.birthday)}</span>`;

    /* 兼容多种后端返回字段 */
    const text = data.content ?? data.analysis ?? data.result ?? data.message ?? data.text;
    if (typeof text === 'string' && text.trim()) {
      $('#result-content').innerHTML = text
        .split(/\n\s*\n/) /* 空行分段 */
        .filter((p) => p.trim())
        .map((p) => `<p>${escapeHtml(p.trim()).replace(/\n/g, '<br>')}</p>`)
        .join('');
    } else {
      showError('返回数据格式异常，请稍后重试');
    }
  }

}

/* ============================================
   周公解梦页
   ============================================ */
function initDreamPage() {
  const form = $('#dream-form');
  const contentInput = $('#dream-content');
  const tagsBox = $('#dream-tags');
  const submitBtn = $('#submit-btn');
  const resultCard = $('#result-card');

  /* 生成梦境类型标签（多选） */
  DREAM_TAGS.forEach(({ emoji, label }) => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'dream-tag';
    chip.dataset.label = label;
    chip.setAttribute('aria-pressed', 'false');
    chip.textContent = `${emoji} ${label}`;
    chip.addEventListener('click', () => {
      const selected = chip.classList.toggle('selected');
      chip.setAttribute('aria-pressed', String(selected));
    });
    tagsBox.appendChild(chip);
  });

  contentInput.addEventListener('input', () => {
    clearFieldError('dream');
    updateSubmitState();
  });

  /* 梦境描述至少 10 个字符 → 提交按钮可用 */
  function updateSubmitState() {
    submitBtn.disabled = contentInput.value.trim().length < 10;
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (contentInput.value.trim().length < 10) {
      showFieldError('dream', '请至少输入 10 个字符来描述你的梦境');
      return;
    }
    requestInterpretation();
  });

  $('#retry-btn').addEventListener('click', requestInterpretation);

  /* 请求 AI 解梦：POST /api/dream */
  async function requestInterpretation() {
    const selectedTags = [...tagsBox.querySelectorAll('.dream-tag.selected')]
      .map((el) => el.dataset.label);
    const timeChecked = form.querySelector('input[name="dream_time"]:checked');
    const payload = {
      dream_content: contentInput.value.trim(),
      dream_tags: selectedTags,
      dream_time: timeChecked ? timeChecked.value : ''
    };

    submitBtn.disabled = true;
    resultCard.classList.remove('hidden');
    $('#dream-brief').textContent = '';
    $('#dream-brief').classList.add('hidden');
    $('#keyword-tags').innerHTML = '';
    $('#keyword-tags').classList.add('hidden');
    $('#result-content').innerHTML = '';
    $('#result-error').classList.add('hidden');
    $('#loading').classList.remove('hidden');
    resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });

    try {
      const res = await fetch('/api/dream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(`服务返回异常（${res.status}），请稍后重试`);
      const data = await res.json();
      renderResult(payload.dream_content, data.data ?? data); /* 解包 {success, data:{...}} 包装 */
    } catch (err) {
      showError(err instanceof Error ? err.message : '网络异常，请稍后重试');
    } finally {
      $('#loading').classList.add('hidden');
      updateSubmitState();
    }
  }

  /* 渲染结果：梦境摘要 + 关键词标签 + 多段落解析 */
  function renderResult(dreamContent, data) {
    /* 梦境摘要：截取前 50 个字符（按码点截取，避免切坏 emoji） */
    const chars = Array.from(dreamContent);
    const briefEl = $('#dream-brief');
    briefEl.textContent = chars.length > 50 ? `${chars.slice(0, 50).join('')}...` : dreamContent;
    briefEl.classList.remove('hidden');

    /* 关键词标签（后端返回 keywords 数组时展示） */
    if (Array.isArray(data.keywords) && data.keywords.length) {
      const box = $('#keyword-tags');
      box.innerHTML = data.keywords
        .map((k) => `<span class="keyword-tag">${escapeHtml(String(k))}</span>`)
        .join('');
      box.classList.remove('hidden');
    }

    /* 解析内容：兼容多种后端返回字段 */
    const text = data.content ?? data.interpretation ?? data.result ?? data.message ?? data.text;
    if (typeof text === 'string' && text.trim()) {
      $('#result-content').innerHTML = text
        .split(/\n\s*\n/) /* 空行分段 */
        .filter((p) => p.trim())
        .map((p) => `<p>${escapeHtml(p.trim()).replace(/\n/g, '<br>')}</p>`)
        .join('');
    } else {
      showError('返回数据格式异常，请稍后重试');
    }
  }
}
