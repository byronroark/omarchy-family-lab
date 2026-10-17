// No graphical session, shell IPC or network: validate only the local UI contract.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const model = {};
const source = fs.readFileSync(path.join(__dirname, '../plugin/UiModel.js'), 'utf8').replace(/^\.pragma library\s*/, '');
vm.createContext(model);
vm.runInContext(source, model);
const id = 'a'.repeat(32);
const data = {version: 1, enabled: true, paused: false, requests: [{id, peer: 'learner-a', via: '',
    message: '<b>literal</b> $(nothing)', expires: 1000,
    actions: [{kind: 'open', label: 'Open terminal'}, {kind: 'forward', label: 'Ask Mom', target: 'mom'}, {kind: 'dismiss', label: 'Dismiss'}]}]};
assert.equal(model.parse(JSON.stringify(data)).requests[0].message, data.requests[0].message);
assert.equal(JSON.stringify(model.commandFor('/fixed/family-lab', id, 'forward', 'mom')),
             JSON.stringify(['/fixed/family-lab', 'ui-action', id, 'forward', 'mom']));
for (const kind of ['allow-control', 'control', 'exec', 'sudo', 'ask', 'install'])
    assert.equal(model.commandFor('/fixed/family-lab', id, kind, ''), null);
assert.equal(model.commandFor('family-lab', '../escape', 'open', ''), null);
assert.equal(model.commandFor('family-lab', id, 'open', 'mom'), null);
assert.equal(model.commandFor('family-lab', id, 'forward', 'mom;echo bad'), null);
assert.equal(model.parse(JSON.stringify({...data, paused: true})).requests.length, 0);
assert.equal(model.parse(JSON.stringify({...data, enabled: false})).requests.length, 0);
for (const change of [{version: 2}, {enabled: 'true'}, {paused: null}, {requests: Array(21).fill(data.requests[0])}])
    assert.throws(() => model.parse(JSON.stringify({...data, ...change})));
assert.throws(() => model.parse(JSON.stringify({...data, requests: [{...data.requests[0], actions: [{kind: 'control', label: 'Approve'}]}]})));
console.log('PASS: UI schema, fixed argv actions, no approval/admin/exec actions, bad targets and paused/disabled states');

assert.equal(model.parse(JSON.stringify({...data, requests: [{...data.requests[0], name: 'Alex Rivera (learner-a)'}]})).requests[0].name, 'Alex Rivera (learner-a)');
assert.throws(() => model.parse(JSON.stringify({...data, requests: [{...data.requests[0], name: 123}]})));
