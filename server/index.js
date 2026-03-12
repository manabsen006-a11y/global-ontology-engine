/**
 * Backend API Server
 * Proxies news requests to GNews API (avoids CORS in production)
 * Set GNEWS_API_KEY in environment
 */
import express from 'express';
import cors from 'cors';

const app = express();
const PORT = process.env.PORT || 3001;
const GNEWS_KEY = process.env.GNEWS_API_KEY || process.env.VITE_GNEWS_API_KEY;
const GNEWS_BASE = 'https://gnews.io/api/v4';

app.use(cors());
app.use(express.json());

app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    newsApi: !!GNEWS_KEY,
    timestamp: new Date().toISOString(),
  });
});

app.get('/api/news/headlines', async (req, res) => {
  if (!GNEWS_KEY) {
    return res.status(503).json({
      error: 'News API not configured',
      message: 'Set GNEWS_API_KEY in environment. Get a free key at https://gnews.io',
    });
  }
  try {
    const { country = 'in', lang = 'en', max = 20 } = req.query;
    const url = `${GNEWS_BASE}/top-headlines?apikey=${GNEWS_KEY}&country=${country}&lang=${lang}&max=${max}`;
    const resp = await fetch(url);
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.message || 'News API error');
    res.json(data);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/news/search', async (req, res) => {
  if (!GNEWS_KEY) {
    return res.status(503).json({
      error: 'News API not configured',
      message: 'Set GNEWS_API_KEY in environment. Get a free key at https://gnews.io',
    });
  }
  try {
    const { q = '', max = 20, lang = 'en' } = req.query;
    if (!q.trim()) {
      return res.status(400).json({ error: 'Query parameter "q" is required' });
    }
    const url = `${GNEWS_BASE}/search?apikey=${GNEWS_KEY}&q=${encodeURIComponent(q)}&lang=${lang}&max=${max}`;
    const resp = await fetch(url);
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.message || 'News API error');
    res.json(data);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.listen(PORT, () => {
  console.log(`Backend API: http://localhost:${PORT}`);
  if (!GNEWS_KEY) console.warn('GNEWS_API_KEY not set. News endpoints will return 503.');
});
