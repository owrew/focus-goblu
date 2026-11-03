const alarmName = 'focus-session';
let queue = Promise.resolve();

async function finish() {
  const { session } = await chrome.storage.local.get('session');
  if (!session?.endsAt || session.endsAt > Date.now()) return;
  await chrome.storage.local.set({ session: { ...session, endsAt: null, remaining: 0, complete: true } });
  await chrome.notifications.create({ type: 'basic', iconUrl: 'icon.png', title: 'Focus session complete', message: session.task || 'Time to take a break.' });
}

function enqueue(operation) {
  const result = queue.then(operation);
  queue = result.catch(console.error);
  return result;
}

chrome.alarms.onAlarm.addListener(alarm => {
  if (alarm.name === alarmName) enqueue(finish);
});

chrome.runtime.onStartup.addListener(() => enqueue(async () => {
  const { session } = await chrome.storage.local.get('session');
  if (session?.endsAt > Date.now()) await chrome.alarms.create(alarmName, { when: session.endsAt });
  else await finish();
}));

chrome.runtime.onMessage.addListener((message, sender, reply) => {
  enqueue(async () => {
    await finish();
    const { session } = await chrome.storage.local.get('session');
    if (message.action === 'get') return session;
    let next;
    if (message.action === 'start' && Number.isInteger(message.minutes) && message.minutes >= 1 && message.minutes <= 180) {
      next = { task: String(message.task || '').trim().slice(0, 120), minutes: message.minutes, endsAt: Date.now() + message.minutes * 60000 };
    } else if (message.action === 'pause' && session?.endsAt) {
      next = { ...session, endsAt: null, remaining: Math.max(0, session.endsAt - Date.now()) };
    } else if (message.action === 'resume' && session?.remaining > 0) {
      next = { ...session, endsAt: Date.now() + session.remaining, remaining: null };
    } else if (message.action === 'reset') {
      await chrome.alarms.clear(alarmName);
      await chrome.storage.local.remove('session');
      return null;
    } else return session;
    await chrome.storage.local.set({ session: next });
    if (next.endsAt) await chrome.alarms.create(alarmName, { when: next.endsAt });
    else await chrome.alarms.clear(alarmName);
    return next;
  }).then(session => reply({ session }), error => reply({ error: error.message }));
  return true;
});
