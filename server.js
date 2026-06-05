const express = require('express');
const Database = require('better-sqlite3');
const { nanoid } = require('nanoid');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3000;

const dbPath = fs.existsSync('/data') ? '/data/votes.db' : './votes.db';
const db = new Database(dbPath);

db.exec(`
  CREATE TABLE IF NOT EXISTS links (
    id TEXT PRIMARY KEY,
    label TEXT,
    used INTEGER DEFAULT 0,
    created_at TEXT
  );
  CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    q1 INTEGER,
    q2 INTEGER,
    created_at TEXT
  );
  CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
  );
`);

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

function isClosed() {
  const row = db.prepare("SELECT value FROM settings WHERE key='closed'").get();
  return row && row.value === '1';
}

// Admin endpoints
app.post('/api/admin/generate-links', (req, res) => {
  const count = parseInt(req.body.count, 10);
  if (!count || count < 1 || count > 500) return res.status(400).json({ error: 'Geçersiz sayı' });

  db.prepare('DELETE FROM links').run();
  const insert = db.prepare("INSERT INTO links (id, label, used, created_at) VALUES (?, ?, 0, ?)");
  const now = new Date().toISOString();

  const links = [];
  for (let i = 0; i < count; i++) {
    const id = nanoid(10);
    const label = `Katılımcı ${i + 1}`;
    insert.run(id, label, now);
    links.push({ id, label, used: 0, created_at: now });
  }
  res.json({ links });
});

app.get('/api/admin/links', (req, res) => {
  const links = db.prepare('SELECT * FROM links ORDER BY label').all();
  res.json({ links });
});

app.get('/api/admin/status', (req, res) => {
  const totalLinks = db.prepare('SELECT COUNT(*) as n FROM links').get().n;
  const usedLinks = db.prepare('SELECT COUNT(*) as n FROM links WHERE used=1').get().n;
  res.json({ closed: isClosed(), totalLinks, usedLinks });
});

app.post('/api/admin/close', (req, res) => {
  db.prepare("INSERT OR REPLACE INTO settings (key, value) VALUES ('closed', '1')").run();
  res.json({ ok: true });
});

app.post('/api/admin/reset', (req, res) => {
  db.prepare('DELETE FROM links').run();
  db.prepare('DELETE FROM votes').run();
  db.prepare('DELETE FROM settings').run();
  res.json({ ok: true });
});

app.get('/api/admin/results', (req, res) => {
  if (!isClosed()) return res.status(403).json({ error: 'Anket henüz kapalı değil' });
  const votes = db.prepare('SELECT q1, q2 FROM votes').all();
  res.json(buildResults(votes));
});

// Vote endpoints
app.get('/api/vote/:linkId', (req, res) => {
  const link = db.prepare('SELECT * FROM links WHERE id=?').get(req.params.linkId);
  if (!link) return res.json({ valid: false, used: false, closed: isClosed() });
  res.json({ valid: true, used: link.used === 1, closed: isClosed() });
});

app.post('/api/vote/:linkId', (req, res) => {
  const link = db.prepare('SELECT * FROM links WHERE id=?').get(req.params.linkId);
  if (!link) return res.status(404).json({ error: 'Geçersiz link' });
  if (link.used) return res.status(409).json({ error: 'Bu link zaten kullanıldı' });
  if (isClosed()) return res.status(403).json({ error: 'Anket kapalı' });

  const { q1, q2 } = req.body;
  if (
    typeof q1 !== 'number' || typeof q2 !== 'number' ||
    q1 < 0 || q1 > 4 || q2 < 0 || q2 > 4 || q1 === q2
  ) {
    return res.status(400).json({ error: 'Geçersiz oy' });
  }

  db.prepare('UPDATE links SET used=1 WHERE id=?').run(link.id);
  db.prepare('INSERT INTO votes (q1, q2, created_at) VALUES (?, ?, ?)').run(q1, q2, new Date().toISOString());
  res.json({ ok: true });
});

// Public results
app.get('/api/results/public', (req, res) => {
  if (!isClosed()) return res.json({ locked: true });
  const votes = db.prepare('SELECT q1, q2 FROM votes').all();
  res.json({ locked: false, ...buildResults(votes) });
});

function buildResults(votes) {
  const CANDIDATES = ['Begüm', 'Rıza', 'Gilda', 'Erk', 'Ecem'];
  const q1Counts = new Array(5).fill(0);
  const q2Counts = new Array(5).fill(0);
  for (const v of votes) {
    q1Counts[v.q1]++;
    q2Counts[v.q2]++;
  }
  return {
    total: votes.length,
    candidates: CANDIDATES,
    q1: q1Counts,
    q2: q2Counts,
  };
}

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
