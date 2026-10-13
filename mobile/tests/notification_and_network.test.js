const test = require('node:test');
const assert = require('node:assert');

// Helper implementing the mobile client's WebSocket URL conversion logic
function buildWebSocketUrl(baseUrl, token) {
  let ws = baseUrl.replace(/^http:\/\//, 'ws://').replace(/^https:\/\//, 'wss://').replace(/\/+$/, '');
  ws += '/ws/notifications';
  if (token && token.trim()) {
    ws += `?token=${encodeURIComponent(token.trim())}`;
  }
  return ws;
}

// Helper implementing the mobile client's HTTP header generation
function buildAuthHeaders(token) {
  const headers = { 'Content-Type': 'application/json' };
  if (token && token.trim()) {
    headers['X-Hub-Token'] = token.trim();
    headers['Authorization'] = `Bearer ${token.trim()}`;
  }
  return headers;
}

// Helper implementing client-side notification deduplication
class NotificationDeduplicator {
  constructor(ttlMs = 60000) {
    this.seen = new Map();
    this.ttlMs = ttlMs;
  }

  isDuplicate(id) {
    const now = Date.now();
    this.cleanup(now);
    if (this.seen.has(id)) {
      return true;
    }
    this.seen.set(id, now);
    return false;
  }

  cleanup(now) {
    for (const [id, timestamp] of this.seen.entries()) {
      if (now - timestamp > this.ttlMs) {
        this.seen.delete(id);
      }
    }
  }
}

test('buildWebSocketUrl transforms HTTP to WS and HTTPS to WSS with encoded token', () => {
  const ws1 = buildWebSocketUrl('http://192.168.1.100:8765', 'mysecret123');
  assert.strictEqual(ws1, 'ws://192.168.1.100:8765/ws/notifications?token=mysecret123');

  const ws2 = buildWebSocketUrl('https://hub.example.com/', 'token with spaces');
  assert.strictEqual(ws2, 'wss://hub.example.com/ws/notifications?token=token%20with%20spaces');

  const wsNoToken = buildWebSocketUrl('http://localhost:8765/', '');
  assert.strictEqual(wsNoToken, 'ws://localhost:8765/ws/notifications');
});

test('buildAuthHeaders includes dual X-Hub-Token and Bearer authorization', () => {
  const headers = buildAuthHeaders('054871eb16964df73d20f8d800788161');
  assert.strictEqual(headers['X-Hub-Token'], '054871eb16964df73d20f8d800788161');
  assert.strictEqual(headers['Authorization'], 'Bearer 054871eb16964df73d20f8d800788161');
  assert.strictEqual(headers['Content-Type'], 'application/json');
});

test('NotificationDeduplicator drops duplicate IDs within retention window', () => {
  const dedup = new NotificationDeduplicator(1000);
  assert.strictEqual(dedup.isDuplicate('notif_1'), false);
  assert.strictEqual(dedup.isDuplicate('notif_1'), true);
  assert.strictEqual(dedup.isDuplicate('notif_2'), false);
});

test('Event filtering differentiates silent qna_updated from alert notifications', () => {
  const payload1 = { event: 'qna_updated', slot_id: 1, count: 5 };
  const payload2 = { id: 'alert_123', title: 'New Question', message: 'Ready to review' };

  function shouldDisplayBanner(msg) {
    if (msg.event === 'qna_updated') return false;
    return Boolean(msg.title && msg.message);
  }

  assert.strictEqual(shouldDisplayBanner(payload1), false);
  assert.strictEqual(shouldDisplayBanner(payload2), true);
});
