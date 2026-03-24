const rtspInput = document.getElementById('rtspInput');
const attachBtn = document.getElementById('attachBtn');
const streamStatus = document.getElementById('streamStatus');
const logsBody = document.getElementById('logsBody');
const actorFilter = document.getElementById('actorFilter');
const scenarioFilter = document.getElementById('scenarioFilter');
const refreshLogs = document.getElementById('refreshLogs');
const seedEvent = document.getElementById('seedEvent');
const chatBox = document.getElementById('chatBox');
const chatInput = document.getElementById('chatInput');
const chatSend = document.getElementById('chatSend');
const player = document.getElementById('player');
const startDetect = document.getElementById('startDetect');
const stopDetect = document.getElementById('stopDetect');
const detectStatus = document.getElementById('detectStatus');

attachBtn.onclick = async () => {
  const url = rtspInput.value.trim();
  if (!url) {
    streamStatus.textContent = 'Please enter a stream URL before attaching.';
    return;
  }

  const res = await fetch('/api/stream/attach', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rtsp_url: url }),
  });
  if (!res.ok) {
    let detail = `Attach failed (${res.status})`;
    try {
      const err = await res.json();
      detail = err?.detail?.[0]?.msg || err?.detail || detail;
    } catch (_e) {
      // no-op
    }
    streamStatus.textContent = detail;
    return;
  }
  const data = await res.json();
  streamStatus.textContent = data.connected ? `Connected: ${data.url}` : `Error: ${data.last_error}`;
  if (data.connected && (data.url.startsWith('http://') || data.url.startsWith('https://'))) {
    player.src = data.url;
  }
};

async function loadLogs() {
  const params = new URLSearchParams();
  if (actorFilter.value) params.set('actor_id', actorFilter.value);
  if (scenarioFilter.value) params.set('scenario', scenarioFilter.value);

  const res = await fetch(`/api/events?${params.toString()}`);
  const logs = await res.json();
  logsBody.innerHTML = logs
    .map(
      (e) => `<tr><td>${e.id}</td><td>${e.timestamp_sec.toFixed(1)}</td><td>${e.actor_id}</td><td>${e.scenario}</td><td>${e.traits.join(', ')}</td></tr>`
    )
    .join('');
}

refreshLogs.onclick = loadLogs;

seedEvent.onclick = async () => {
  const t = Math.round((Date.now() / 1000) % 600);
  await fetch('/api/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      actor_id: `person-${(t % 3) + 1}`,
      scenario: t % 2 ? 'presence' : 'backpack_detected',
      timestamp_sec: t,
      traits: ['blue_shirt', t % 2 ? 'no_helmet' : 'backpack'],
      confidence: 0.88,
      source: 'manual',
      note: 'Demo seeded event',
    }),
  });
  await loadLogs();
};

function appendMessage(role, content, refs = []) {
  const msg = document.createElement('div');
  msg.className = `msg ${role}`;
  const text = document.createElement('div');
  text.textContent = content;
  msg.appendChild(text);

  if (refs.length > 0) {
    const refsDiv = document.createElement('div');
    refs.forEach((ref) => {
      const span = document.createElement('span');
      span.className = 'timestamp-link';
      span.textContent = `#${ref.event_id} @ ${ref.timestamp_sec.toFixed(1)}s`;
      span.onclick = () => {
        player.currentTime = ref.timestamp_sec;
        player.play();
      };
      refsDiv.appendChild(span);
    });
    msg.appendChild(refsDiv);
  }

  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function loadHistory() {
  const res = await fetch('/api/chat/history');
  const history = await res.json();
  history.forEach((m) => appendMessage(m.role, m.content));
}

chatSend.onclick = async () => {
  if (!chatInput.value.trim()) return;
  const q = chatInput.value;
  appendMessage('user', q);
  chatInput.value = '';

  const res = await fetch('/api/chat/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: q }),
  });
  const data = await res.json();
  appendMessage('assistant', data.answer, data.references || []);
};

startDetect.onclick = async () => {
  const source = rtspInput.value.trim();
  if (!source) {
    detectStatus.textContent = 'Set a source URL before starting detection.';
    return;
  }
  const res = await fetch('/api/detection/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_url: source, model_name: 'yolov8n.pt', confidence: 0.35, event_cooldown_sec: 5 }),
  });
  const data = await res.json();
  detectStatus.textContent = data.message || (data.running ? 'Detector running' : 'Detector stopped');
};

stopDetect.onclick = async () => {
  const res = await fetch('/api/detection/stop', { method: 'POST' });
  const data = await res.json();
  detectStatus.textContent = data.message || 'Detector stopped';
};

loadLogs();
loadHistory();
