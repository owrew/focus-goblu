import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const manifest = JSON.parse(fs.readFileSync('extension/manifest.json', 'utf8'));
assert.equal(manifest.manifest_version, 3);
for (const file of ['icon.png', manifest.background.service_worker, manifest.action.default_popup]) {
  assert.ok(fs.statSync('extension/' + file).size > 0);
}

let session;
let receive;
let alarm;
let notified = 0;
const chrome = {
  storage: { local: {
    get: async () => ({ session }),
    set: async data => { session = data.session; },
    remove: async () => { session = undefined; }
  }},
  alarms: {
    onAlarm: { addListener: callback => { alarm = callback; } },
    create: async () => {},
    clear: async () => {}
  },
  notifications: { create: async () => { notified++; } },
  runtime: {
    onStartup: { addListener() {} },
    onMessage: { addListener: callback => { receive = callback; } }
  }
};
vm.runInNewContext(fs.readFileSync('extension/worker.js', 'utf8'), { chrome, console });
const send = (action, data = {}) => new Promise(resolve => receive({ action, ...data }, {}, resolve));

await send('start', { minutes: 1, task: 'Read one chapter' });
assert.ok(session.endsAt > Date.now());
await send('pause');
assert.ok(session.remaining > 0 && session.endsAt === null);
await send('resume');
assert.ok(session.endsAt > Date.now());
session.endsAt = Date.now() - 1;
alarm({ name: 'focus-session' });
await send('get');
assert.equal(session.complete, true);
assert.equal(notified, 1);
await send('reset');
assert.equal(session, undefined);
console.log('Extension timer lifecycle passed with simulated browser APIs.');
