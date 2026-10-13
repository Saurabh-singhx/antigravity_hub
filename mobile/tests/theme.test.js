const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

// Read theme source directly to test tokens without needing Metro/Babel transformations
const themeSource = fs.readFileSync(
  path.join(__dirname, '../src/theme/neomorphism.js'),
  'utf-8'
);

test('NeoColors defines complete light neomorphic palette', () => {
  assert.match(themeSource, /background:\s*'#e6ecf5'/);
  assert.match(themeSource, /surface:\s*'#e6ecf5'/);
  assert.match(themeSource, /highlight:\s*'#ffffff'/);
  assert.match(themeSource, /shadowDark:\s*'#b4c2d4'/);
  assert.match(themeSource, /primary:\s*'#4338ca'/);
  assert.match(themeSource, /success:\s*'#10b981'/);
  assert.match(themeSource, /warning:\s*'#f59e0b'/);
  assert.match(themeSource, /error:\s*'#ef4444'/);
});

test('NeoStyles defines raised card and button elevation for Android and iOS', () => {
  assert.match(themeSource, /borderRadius:\s*16/);
  assert.match(themeSource, /borderRadius:\s*12/);
  assert.match(themeSource, /elevation:\s*4/);
  assert.match(themeSource, /elevation:\s*3/);
  assert.match(themeSource, /shadowColor:\s*'#96a7be'/);
});

test('NeoStyles defines inset pressed state for active controls', () => {
  assert.match(themeSource, /inset:\s*\{/);
  assert.match(themeSource, /elevation:\s*0/);
});
