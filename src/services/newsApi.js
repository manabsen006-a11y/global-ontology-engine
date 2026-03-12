/**
 * News API Service
 * Calls backend API (proxied in dev) for live news.
 * Backend requires GNEWS_API_KEY in environment.
 */
const API_BASE = '/api/news';

async function fetchApi(path, params = {}) {
  const qs = new URLSearchParams(params).toString();
  const url = `${API_BASE}${path}${qs ? '?' + qs : ''}`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || err.error || `API error: ${res.status}`);
  }
  return res.json();
}

export async function fetchTopHeadlines({ country = 'in', lang = 'en', max = 20 } = {}) {
  return fetchApi('/headlines', { country, lang, max });
}

export async function searchNews(query, { lang = 'en', max = 20 } = {}) {
  if (!query?.trim()) return null;
  return fetchApi('/search', { q: query.trim(), lang, max });
}

export async function checkHealth() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    return data?.newsApi === true;
  } catch {
    return false;
  }
}
