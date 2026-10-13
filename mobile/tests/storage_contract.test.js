const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const kotlinSource = fs.readFileSync(
  path.join(__dirname, '../android/app/src/main/java/com/saurabh/antigravityhub/HubForegroundService.kt'),
  'utf-8'
);

const appSource = fs.readFileSync(
  path.join(__dirname, '../App.js'),
  'utf-8'
);

test('Kotlin service and React Native agree on AsyncStorage keys', () => {
  // Key for Hub URL
  assert.match(appSource, /'antigravity_hub_url'/);
  assert.match(kotlinSource, /"antigravity_hub_url"/);

  // Key for Hub Token
  assert.match(appSource, /'antigravity_hub_token'/);
  assert.match(kotlinSource, /"antigravity_hub_token"/);
});

test('Kotlin service queries internal SQLite Room DB and AsyncStorage fallback', () => {
  // Candidate databases
  assert.match(kotlinSource, /"RKStorage"/);
  assert.match(kotlinSource, /"catalystLocalStorage"/);
  assert.match(kotlinSource, /"AsyncStorage"/);
  assert.match(kotlinSource, /"Storage"/);

  // SQL Query format
  assert.match(kotlinSource, /SELECT value FROM \$tableName WHERE key = \?/);
});

test('Kotlin service falls back to default LAN IP if storage is empty', () => {
  assert.match(kotlinSource, /http:\/\/192\.168\./);
  assert.match(kotlinSource, /:8765/);
});
