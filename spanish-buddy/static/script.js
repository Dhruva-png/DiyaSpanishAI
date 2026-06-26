const thread = document.getElementById('thread');
const composer = document.getElementById('composer');
const input = document.getElementById('messageInput');
const levelRack = document.getElementById('levelRack');
const offlineBanner = document.getElementById('offlineBanner');
const offlineDetail = document.getElementById('offlineDetail');
const statusbar = document.getElementById('statusbar');
const segName = document.getElementById('segName');
const segMode = document.getElementById('segMode');
const segConn = document.getElementById('segConn');

const STORAGE_KEY = 'spanish-buddy-history-v1';
const LEVEL_KEY = 'spanish-buddy-level-v1';
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

let history = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
let level = localStorage.getItem(LEVEL_KEY) || 'intermediate';
let companionName = 'mateo';

const GREETINGS = {
  beginner: "Heyyy! I'm so excited to chat with you. We'll go easy -- mostly English, with little bits of Spanish (espanol) mixed in so it sticks. Listo? (ready?)",
  intermediate: "Ey, que onda! Vamos a chatear como amigos -- I'll mix English and Spanish pretty evenly, so jump in however feels natural.",
  advanced: "Ey, que tal! Hoy vamos a hablar casi todo en espanol, asi que preparate. Cuentame, como va tu dia?",
};

function saveHistory() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

function setActiveLevel() {
  document.querySelectorAll('.level-opt').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.level === level);
  });
  segMode.textContent = `mode: ${level}`;
}

function appendLine(role, content, className = '') {
  const row = document.createElement('div');
  row.className = `line ${role} ${className}`.trim();
  const prompt = document.createElement('span');
  prompt.className = 'prompt';
  prompt.textContent = role === 'me' ? 'you$' : role === 'boot' ? '#' : `${companionName}>`;
  const msg = document.createElement('span');
  msg.className = 'msg';
  msg.textContent = content;
  row.appendChild(prompt);
  row.appendChild(msg);
  thread.appendChild(row);
  thread.scrollTop = thread.scrollHeight;
  return { row, msg };
}

function typeOut(msgEl, fullText) {
  if (reducedMotion) {
    msgEl.textContent = fullText;
    return Promise.resolve();
  }
  return new Promise(resolve => {
    let i = 0;
    const speed = fullText.length > 220 ? 4 : 14; // ms per char, faster for long replies
    const step = () => {
      i += 1;
      msgEl.textContent = fullText.slice(0, i);
      thread.scrollTop = thread.scrollHeight;
      if (i < fullText.length) {
        setTimeout(step, speed);
      } else {
        resolve();
      }
    };
    step();
  });
}

function renderHistoryStatic() {
  if (history.length === 0) {
    history.push({ role: 'assistant', content: GREETINGS[level] });
    saveHistory();
  }
  history.forEach(m => {
    appendLine(m.role === 'user' ? 'me' : 'them', m.content);
  });
}

function showTyping() {
  const { row, msg } = appendLine('them', '', 'typing');
  msg.innerHTML = '<span class="cursor"></span>';
  return row;
}

function setConn(online, detail) {
  if (online) {
    segConn.textContent = '● online';
    statusbar.classList.remove('offline');
    offlineBanner.hidden = true;
  } else {
    segConn.textContent = '● offline';
    statusbar.classList.add('offline');
    offlineDetail.textContent = detail || "couldn't reach the AI service";
    offlineBanner.hidden = false;
  }
}

async function bootSequence() {
  const lines = [
    'booting spanish_buddy.sh ...',
    `loading persona: ${companionName} ...`,
    'connecting to groq api ...',
  ];
  for (const line of lines) {
    appendLine('boot', line, 'boot');
    await new Promise(r => setTimeout(r, reducedMotion ? 0 : 260));
  }
}

async function checkHealth() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    companionName = (data.companion_name || 'mateo').toLowerCase();
    segName.textContent = `${companionName}@spanish-buddy`;
    if (data.api_reachable) {
      appendLine('boot', 'connection established. [ok]', 'boot');
      setConn(true);
    } else {
      appendLine('boot', `connection failed: ${data.error || 'unknown error'}`, 'boot');
      setConn(false, data.error);
    }
  } catch (e) {
    appendLine('boot', 'connection failed: server unreachable', 'boot');
    setConn(false, "couldn't reach the server -- it may be waking up (free hosting sleeps after inactivity), try again in about a minute");
  }
}

async function sendMessage(text) {
  history.push({ role: 'user', content: text });
  appendLine('me', text);
  saveHistory();

  input.value = '';
  input.disabled = true;
  const typingRow = showTyping();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: history, level }),
    });
    const data = await res.json();
    typingRow.remove();

    if (data.reply) {
      history.push({ role: 'assistant', content: data.reply });
      saveHistory();
      const { msg } = appendLine('them', '');
      await typeOut(msg, data.reply);
    } else {
      appendLine('them', `[error] ${data.error || 'something went wrong'}`);
    }
  } catch (e) {
    typingRow.remove();
    appendLine('them', '[error] lost connection to the server');
  } finally {
    input.disabled = false;
    input.focus();
  }
}

levelRack.addEventListener('click', (e) => {
  const btn = e.target.closest('.level-opt');
  if (!btn) return;
  level = btn.dataset.level;
  localStorage.setItem(LEVEL_KEY, level);
  setActiveLevel();
});

document.addEventListener('keydown', (e) => {
  if (document.activeElement === input) return;
  if (e.key === '1') { level = 'beginner'; localStorage.setItem(LEVEL_KEY, level); setActiveLevel(); }
  if (e.key === '2') { level = 'intermediate'; localStorage.setItem(LEVEL_KEY, level); setActiveLevel(); }
  if (e.key === '3') { level = 'advanced'; localStorage.setItem(LEVEL_KEY, level); setActiveLevel(); }
});

composer.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text || input.disabled) return;
  sendMessage(text);
});

(async function init() {
  setActiveLevel();
  await bootSequence();
  await checkHealth();
  renderHistoryStatic();
  input.disabled = false;
  input.focus();
})();
