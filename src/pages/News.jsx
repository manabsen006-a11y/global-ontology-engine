import { useState, useEffect, useCallback } from 'react';
import { fetchTopHeadlines, searchNews, checkHealth } from '../services/newsApi';
import { C } from '../theme';

const DEMO_ARTICLES = [
  { title: 'Government launches new digital initiatives for citizen services', source: { name: 'Press Bureau' }, publishedAt: new Date().toISOString(), url: '#', description: 'New integrated portal to streamline access to government schemes.' },
  { title: 'Economic survey highlights growth in key sectors', source: { name: 'Ministry of Finance' }, publishedAt: new Date(Date.now() - 3600000).toISOString(), url: '#', description: 'Latest economic indicators show positive trajectory.' },
  { title: 'National health mission achieves vaccination targets', source: { name: 'Health Ministry' }, publishedAt: new Date(Date.now() - 7200000).toISOString(), url: '#', description: 'Over 95% coverage reported in targeted regions.' },
  { title: 'Education reforms focus on skill development', source: { name: 'Education Dept' }, publishedAt: new Date(Date.now() - 10800000).toISOString(), url: '#', description: 'New curriculum to align with industry requirements.' },
  { title: 'Infrastructure projects get green light in budget allocation', source: { name: 'Planning Commission' }, publishedAt: new Date(Date.now() - 14400000).toISOString(), url: '#', description: 'Major roads, railways and urban development approved.' },
];

const COUNTRIES = [
  { code: 'in', name: 'India' },
  { code: 'us', name: 'United States' },
  { code: 'gb', name: 'United Kingdom' },
  { code: 'au', name: 'Australia' },
  { code: 'ca', name: 'Canada' },
  { code: 'sg', name: 'Singapore' },
];

const LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'hi', name: 'Hindi' },
  { code: 'ta', name: 'Tamil' },
  { code: 'te', name: 'Telugu' },
  { code: 'bn', name: 'Bengali' },
];

const REFRESH_INTERVALS = [
  { value: 0, label: 'Manual refresh only' },
  { value: 5, label: 'Every 5 minutes' },
  { value: 10, label: 'Every 10 minutes' },
  { value: 15, label: 'Every 15 minutes' },
];

const SEGMENTS = [
  { id: 'all', label: 'All Segments', query: '' },
  { id: 'geopolitics', label: 'Geopolitics', query: 'geopolitics OR diplomacy OR foreign policy OR treaty' },
  { id: 'economics', label: 'Economics', query: 'economy OR inflation OR trade OR gdp OR markets' },
  { id: 'defense', label: 'Defense', query: 'defense OR military OR armed forces OR missile OR naval' },
  { id: 'technology', label: 'Technology', query: 'technology OR AI OR semiconductor OR startup OR cyber' },
  { id: 'climate', label: 'Climate', query: 'climate OR emissions OR renewable OR weather OR drought' },
  { id: 'society', label: 'Society', query: 'health OR education OR migration OR welfare OR jobs' },
];

const SEGMENT_KEYWORDS = {
  geopolitics: ['diplomacy', 'treaty', 'foreign policy', 'summit', 'embassy', 'border'],
  economics: ['economy', 'inflation', 'gdp', 'market', 'trade', 'fiscal'],
  defense: ['defense', 'military', 'army', 'navy', 'air force', 'missile', 'war'],
  technology: ['ai', 'technology', 'semiconductor', 'startup', 'software', 'cyber'],
  climate: ['climate', 'emissions', 'renewable', 'flood', 'heatwave', 'drought'],
  society: ['education', 'health', 'welfare', 'migration', 'jobs', 'public'],
};

function filterBySegment(items, segmentId) {
  if (!items?.length || segmentId === 'all') return items || [];
  const keywords = SEGMENT_KEYWORDS[segmentId] || [];
  return items.filter((item) => {
    const text = `${item?.title || ''} ${item?.description || ''}`.toLowerCase();
    return keywords.some((keyword) => text.includes(keyword));
  });
}

function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return 'Just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)} min ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
  return d.toLocaleDateString();
}

export default function News() {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [apiReady, setApiReady] = useState(false);
  const [country, setCountry] = useState('in');
  const [lang, setLang] = useState('en');
  const [segment, setSegment] = useState('all');
  const [refreshInterval, setRefreshInterval] = useState(5);

  const loadHeadlines = useCallback(async () => {
    setLoading(true);
    setError(null);
    if (!apiReady) {
      setArticles(filterBySegment(DEMO_ARTICLES, segment));
      setLoading(false);
      return;
    }
    try {
      const segmentQuery = SEGMENTS.find((s) => s.id === segment)?.query || '';
      const data = segment === 'all'
        ? await fetchTopHeadlines({ country, lang })
        : await searchNews(segmentQuery, { lang, max: 25 });

      const filteredArticles = filterBySegment(data?.articles || [], segment);
      if (data?.articles) {
        setArticles(filteredArticles);
        setLastUpdated(new Date());
      } else setArticles(filterBySegment(DEMO_ARTICLES, segment));
    } catch (e) {
      setError(e.message);
      setArticles(filterBySegment(DEMO_ARTICLES, segment));
    } finally {
      setLoading(false);
    }
  }, [apiReady, country, lang, segment]);

  useEffect(() => {
    checkHealth().then(setApiReady);
  }, []);

  useEffect(() => {
    loadHeadlines();
  }, [loadHeadlines]);

  useEffect(() => {
    if (searchResults) setSearchResults(null);
  }, [country, lang, segment]);

  useEffect(() => {
    if (!apiReady || refreshInterval <= 0 || searchResults) return;
    const id = setInterval(loadHeadlines, refreshInterval * 60 * 1000);
    return () => clearInterval(id);
  }, [apiReady, refreshInterval, searchResults, loadHeadlines]);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setError(null);
    if (!apiReady) {
      const q = query.toLowerCase();
      const filtered = DEMO_ARTICLES.filter(
        (a) => a.title.toLowerCase().includes(q) || (a.description?.toLowerCase().includes(q))
      );
      setSearchResults({ articles: filterBySegment(filtered.length ? filtered : DEMO_ARTICLES, segment) });
      setSearching(false);
      return;
    }
    try {
      const segmentQuery = SEGMENTS.find((s) => s.id === segment)?.query || '';
      const combinedQuery = segment === 'all' ? query.trim() : `${query.trim()} ${segmentQuery}`;
      const data = await searchNews(combinedQuery, { lang });
      setSearchResults({ articles: filterBySegment(data?.articles || [], segment) });
      setLastUpdated(new Date());
    } catch (e) {
      setError(e.message);
      setSearchResults({ articles: [] });
    } finally {
      setSearching(false);
    }
  };

  const clearSearch = () => {
    setSearchResults(null);
    setQuery('');
  };

  const displayArticles = searchResults?.articles ?? articles;

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: C.bg }}>
      {/* Official Header */}
      <header style={{ flexShrink: 0, background: C.primary, color: C.white, padding: '24px 32px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 6, }}>
            News &amp; Information Service
          </h1>
          <p style={{ fontSize: 14, opacity: 0.92 }}>
            Official real-time news updates. Submit an enquiry to search by topic, or view latest headlines.
          </p>
        </div>
      </header>

      {/* Official Options Panel */}
      <div style={{ flexShrink: 0, padding: '20px 32px', background: C.panel, borderBottom: `2px solid ${C.primary}`, boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: C.primary, marginBottom: 16, }}>
            FILTER OPTIONS
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 20 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 6 }}>Country / Region</label>
              <select
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                style={{ width: '100%', padding: '10px 12px', fontSize: 14, border: `1px solid ${C.border}`, borderRadius: 6, background: C.white }}
              >
                {COUNTRIES.map((c) => (
                  <option key={c.code} value={c.code}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 6 }}>Language</label>
              <select
                value={lang}
                onChange={(e) => setLang(e.target.value)}
                style={{ width: '100%', padding: '10px 12px', fontSize: 14, border: `1px solid ${C.border}`, borderRadius: 6, background: C.white }}
              >
                {LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>{l.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 6 }}>Segment</label>
              <select
                value={segment}
                onChange={(e) => setSegment(e.target.value)}
                style={{ width: '100%', padding: '10px 12px', fontSize: 14, border: `1px solid ${C.border}`, borderRadius: 6, background: C.white }}
              >
                {SEGMENTS.map((s) => (
                  <option key={s.id} value={s.id}>{s.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 6 }}>Auto-refresh (Live)</label>
              <select
                value={refreshInterval}
                onChange={(e) => setRefreshInterval(Number(e.target.value))}
                style={{ width: '100%', padding: '10px 12px', fontSize: 14, border: `1px solid ${C.border}`, borderRadius: 6, background: C.white }}
              >
                {REFRESH_INTERVALS.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Enquiry / Search */}
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div style={{ flex: 1, minWidth: 280 }}>
              <label htmlFor="news-enquiry" style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 6 }}>
                Submit Enquiry (Search by topic)
              </label>
              <input
                id="news-enquiry"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="e.g., budget, education, health, infrastructure, policy"
                style={{ width: '100%', padding: '12px 16px', fontSize: 15, border: `2px solid ${C.border}`, borderRadius: 6 }}
              />
            </div>
            <button onClick={handleSearch} disabled={searching}
              style={{ padding: '12px 24px', background: C.primary, color: C.white, border: 'none', borderRadius: 6, fontSize: 15, fontWeight: 600 }}>
              {searching ? 'Searching…' : 'Search'}
            </button>
            {searchResults && (
              <button onClick={clearSearch}
                style={{ padding: '12px 20px', background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 6, fontSize: 14 }}>
                Clear &amp; Show Headlines
              </button>
            )}
            <button onClick={loadHeadlines} disabled={loading}
              style={{ padding: '12px 20px', background: C.green, color: C.textBright, border: 'none', borderRadius: 6, fontSize: 14, fontWeight: 600 }}>
              Refresh Now
            </button>
          </div>

          <div style={{ marginTop: 12, fontSize: 12, color: C.textMuted, display: 'flex', alignItems: 'center', gap: 16 }}>
            {lastUpdated && (
              <span>Last updated: {lastUpdated.toLocaleTimeString()}</span>
            )}
            {apiReady ? (
              <span style={{ color: C.green }}>● Live API connected</span>
            ) : (
              <span>Demo mode — Start backend with <code style={{ background: C.bg, padding: '2px 6px', borderRadius: 4 }}>npm run dev:all</code> and set GNEWS_API_KEY for live news</span>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <main style={{ flex: 1, overflow: 'auto', padding: '24px 32px' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          {error && (
            <div style={{ padding: '12px 16px', background: '#fed7d7', color: C.red, borderRadius: 6, marginBottom: 20 }}>
              {error}
            </div>
          )}

          <h2 style={{ fontSize: 16, fontWeight: 600, color: C.text, marginBottom: 16 }}>
            {searchResults
              ? `Search results for "${query}"${segment !== 'all' ? ` in ${SEGMENTS.find((s) => s.id === segment)?.label}` : ''}`
              : `${segment === 'all' ? 'Latest Headlines' : `${SEGMENTS.find((s) => s.id === segment)?.label} Headlines`}`}
          </h2>

          {loading && !searchResults ? (
            <div style={{ textAlign: 'center', padding: 60, color: C.textMuted, fontSize: 15 }}>
              Loading news…
            </div>
          ) : displayArticles.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 60, color: C.textMuted, fontSize: 15 }}>
              No articles found. Try a different search or filter.
            </div>
          ) : (
            <ul style={{ listStyle: 'none' }}>
              {displayArticles.map((a, i) => (
                <li key={i} style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 6, padding: 20, marginBottom: 12, boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
                  <a href={a.url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none', color: C.primary, fontSize: 16, fontWeight: 600, lineHeight: 1.4, display: 'block', marginBottom: 6 }}>
                    {a.title}
                  </a>
                  {a.description && (
                    <p style={{ fontSize: 14, color: C.textMid, lineHeight: 1.6, marginBottom: 8 }}>{a.description}</p>
                  )}
                  <div style={{ fontSize: 12, color: C.textMuted }}>
                    {a.source?.name || 'Unknown'} · {formatDate(a.publishedAt)}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
