const byId = id => document.getElementById(id);
let current;
let busy = false;

function render() {
  const remaining = current?.endsAt ? current.endsAt - Date.now() : current?.remaining ?? Number(byId('minutes').value) * 60000;
  const seconds = Math.max(0, Math.ceil(remaining / 1000));
  byId('clock').textContent = [Math.floor(seconds / 60), seconds % 60].map(value => String(value).padStart(2, '0')).join(':');
  byId('status').textContent = current?.complete ? 'Session complete' : current?.endsAt ? 'Focusing' : current?.remaining ? 'Paused' : 'Ready';
  byId('pause').textContent = current?.endsAt ? 'Pause' : 'Resume';
  byId('pause').disabled = busy || !(current?.endsAt || current?.remaining);
}

async function send(action, data = {}) {
  if (busy) return;
  busy = true;
  byId('start').disabled = true;
  try {
    const response = await chrome.runtime.sendMessage({ action, ...data });
    if (response.error) throw new Error(response.error);
    current = response.session;
    if (action === 'get' && current) {
      byId('task').value = current.task;
      byId('minutes').value = current.minutes;
    }
    render();
  } catch {
    byId('status').textContent = 'Timer unavailable. Reopen the popup to retry.';
  } finally {
    busy = false;
    byId('start').disabled = false;
    byId('pause').disabled = !(current?.endsAt || current?.remaining);
  }
}

byId('session').addEventListener('submit', event => {
  event.preventDefault();
  send('start', { minutes: Number(byId('minutes').value), task: byId('task').value });
});
byId('pause').addEventListener('click', () => send(current?.endsAt ? 'pause' : 'resume'));
byId('reset').addEventListener('click', () => send('reset'));
byId('minutes').addEventListener('input', render);
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.session) { current = changes.session.newValue; render(); }
});
setInterval(() => { if (current?.endsAt) render(); }, 250);
send('get');
