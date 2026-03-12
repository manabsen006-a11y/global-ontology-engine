import { useState, useEffect, useCallback } from 'react';
import { C, DOMAINS, SEV } from '../theme';
import { fetchCorrelations, fetchSignals } from '../services/intelApi';

/* ── helpers ─────────────────────────────────────── */
const domainMeta = (d) => DOMAINS[d] || { label: d, color: '#64748b', icon: '📌', short: d.slice(0, 3).toUpperCase() };
const sevColor = (s) => SEV[s] || '#64748b';
const trustPct = (t) => Math.round((t || 0) * 100);
const fmtDate = (s) => { try { return new Date(s).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }); } catch { return s || '—'; } };

/* ── tiny badge components ───────────────────────── */
const Badge = ({ text, bg, color = '#fff', style }) => (
  <span style={{
    display: 'inline-block', padding: '2px 8px', borderRadius: 4, fontSize: 10,
    fontWeight: 700, background: bg, color, letterSpacing: 0.5, ...style,
  }}>{text}</span>
);

const DomainBadge = ({ domain }) => {
  const m = domainMeta(domain);
  return <Badge text={`${m.icon} ${m.short}`} bg={`${m.color}18`} color={m.color} style={{ marginRight: 4, marginBottom: 4 }} />;
};

const SevBadge = ({ sev }) => (
  <Badge text={sev} bg={sevColor(sev)} style={{ marginRight: 6 }} />
);

/* ── trust gauge (mini arc) ──────────────────────── */
const TrustGauge = ({ score, size = 64 }) => {
  const pct = trustPct(score);
  const r = (size - 8) / 2;
  const circumference = Math.PI * r;
  const offset = circumference - (circumference * pct) / 100;
  const gaugeColor = pct >= 70 ? '#16a34a' : pct >= 45 ? '#d97706' : '#dc2626';
  return (
    <div style={{ position: 'relative', width: size, height: size / 2 + 12, display: 'flex', alignItems: 'flex-end', justifyContent: 'center' }}>
      <svg width={size} height={size / 2 + 4} viewBox={`0 0 ${size} ${size / 2 + 4}`}>
        <path d={`M 4 ${size / 2} A ${r} ${r} 0 0 1 ${size - 4} ${size / 2}`}
          fill="none" stroke="#e2e8f0" strokeWidth={6} strokeLinecap="round" />
        <path d={`M 4 ${size / 2} A ${r} ${r} 0 0 1 ${size - 4} ${size / 2}`}
          fill="none" stroke={gaugeColor} strokeWidth={6} strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.8s ease' }} />
      </svg>
      <span style={{ position: 'absolute', bottom: 0, fontSize: 13, fontWeight: 800, color: gaugeColor }}>{pct}%</span>
    </div>
  );
};

/* ── entity pill ─────────────────────────────────── */
const EntityPill = ({ name, active, onClick }) => (
  <button onClick={onClick} style={{
    display: 'inline-flex', alignItems: 'center', gap: 4,
    padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 600,
    border: `1px solid ${active ? C.accent : C.border}`,
    background: active ? `${C.accent}12` : C.white,
    color: active ? C.accent : C.text, cursor: 'pointer',
    transition: 'all .15s', margin: '0 4px 4px 0',
  }}>{name}</button>
);

/* ── Signal card (left panel) ────────────────────── */
const SignalCard = ({ signal, style }) => {
  const m = domainMeta(signal.domain);
  return (
    <div style={{
      background: C.white, borderRadius: 8, padding: '10px 12px',
      borderLeft: `3px solid ${m.color}`, marginBottom: 8,
      boxShadow: '0 1px 3px rgba(0,0,0,0.06)', ...style,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <DomainBadge domain={signal.domain} />
        {signal.event_types?.slice(0, 2).map((e, i) => (
          <Badge key={i} text={e.replace(/_/g, ' ')} bg="#f1f5f9" color={C.text} />
        ))}
      </div>
      <div style={{ fontSize: 12, fontWeight: 600, color: C.textBright, lineHeight: 1.4, marginBottom: 4 }}>
        {signal.title?.slice(0, 120) || 'Untitled signal'}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10, color: C.textMuted }}>
        <span>{signal.source}</span>
        <span>•</span>
        <span>{fmtDate(signal.timestamp)}</span>
        <span style={{ marginLeft: 'auto', fontWeight: 700, color: signal.trust_base >= 0.8 ? '#16a34a' : '#d97706' }}>
          ★ {trustPct(signal.trust_base)}%
        </span>
      </div>
      {/* entity tags */}
      <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 2 }}>
        {[...(signal.entities?.countries || []), ...(signal.entities?.organizations || [])].slice(0, 5).map((e, i) => (
          <span key={i} style={{ fontSize: 9, padding: '1px 6px', borderRadius: 4, background: '#f8fafc', color: C.textMid, border: `1px solid ${C.borderSoft}` }}>{e}</span>
        ))}
      </div>
    </div>
  );
};

/* ── Intel Report card (center panel) ────────────── */
const ReportCard = ({ report }) => (
  <div style={{
    background: C.white, borderRadius: 10, padding: 16, marginBottom: 12,
    border: `1px solid ${C.border}`, boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
    transition: 'box-shadow .2s',
  }}>
    {/* header row */}
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 10 }}>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
          <SevBadge sev={report.severity} />
          <Badge text={report.template_name || 'Analysis'} bg="#f1f5f9" color={C.accent} />
        </div>
        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: C.textBright, lineHeight: 1.35 }}>
          {report.title}
        </h3>
      </div>
      <TrustGauge score={report.trust_score} />
    </div>

    {/* hypothesis */}
    <div style={{
      background: '#fffbeb', borderLeft: '3px solid #d97706', borderRadius: 6,
      padding: '10px 12px', fontSize: 12, color: '#92400e', lineHeight: 1.55, marginBottom: 12,
    }}>
      <strong style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>Hypothesis</strong>
      <div style={{ marginTop: 4 }}>{report.hypothesis}</div>
    </div>

    {/* evidence chain */}
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: C.textMuted, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>
        Evidence Chain
      </div>
      {report.evidence_chain?.map((ev, i) => {
        const m = domainMeta(ev.domain);
        return (
          <div key={i} style={{
            display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 6,
            paddingLeft: 12, borderLeft: `2px solid ${m.color}40`,
          }}>
            <span style={{ fontSize: 10, fontWeight: 700, color: m.color, minWidth: 40 }}>{m.short}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: C.textBright }}>
                {ev.signal_title?.slice(0, 100) || ev.event}
              </div>
              <div style={{ fontSize: 10, color: C.textMuted, marginTop: 2 }}>
                {ev.signal_source} {ev.signal_timestamp ? `• ${fmtDate(ev.signal_timestamp)}` : ''}
              </div>
            </div>
            <Badge text={ev.event?.replace(/_/g, ' ')} bg={`${m.color}14`} color={m.color} />
          </div>
        );
      })}
    </div>

    {/* domains + entities row */}
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 8 }}>
      {report.domains_spanned?.map((d, i) => <DomainBadge key={i} domain={d} />)}
    </div>
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
      {report.entities?.slice(0, 8).map((e, i) => (
        <span key={i} style={{ fontSize: 10, padding: '2px 7px', borderRadius: 4, background: '#f1f5f9', color: C.text, fontWeight: 500 }}>{e}</span>
      ))}
    </div>
  </div>
);

/* ── Entity network mini-graph (right panel) ─────── */
const EntityNetwork = ({ reports, signals, activeEntity, setActiveEntity }) => {
  // Build entity → domain map from signals
  const entityDomains = {};
  signals.forEach(s => {
    const allEnts = [...(s.entities?.countries || []), ...(s.entities?.organizations || []), ...(s.entities?.people || [])];
    allEnts.forEach(e => {
      if (!entityDomains[e]) entityDomains[e] = new Set();
      entityDomains[e].add(s.domain);
    });
  });

  // Sort entities by number of domain connections (most connected first)
  const sorted = Object.entries(entityDomains)
    .map(([name, domains]) => ({ name, domains: [...domains], count: domains.size }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 25);

  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color: C.textMuted, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 10 }}>
        Entity Network ({sorted.length})
      </div>
      {sorted.map((ent, i) => (
        <div key={i} onClick={() => setActiveEntity(activeEntity === ent.name ? null : ent.name)}
          style={{
            padding: '8px 10px', borderRadius: 8, marginBottom: 4,
            background: activeEntity === ent.name ? `${C.accent}10` : C.white,
            border: `1px solid ${activeEntity === ent.name ? C.accent : C.borderSoft}`,
            cursor: 'pointer', transition: 'all .15s',
          }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: activeEntity === ent.name ? C.accent : C.textBright, marginBottom: 4 }}>
            {ent.name}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
            {ent.domains.map((d, j) => <DomainBadge key={j} domain={d} />)}
          </div>
          <div style={{ fontSize: 9, color: C.textMuted, marginTop: 3 }}>
            {ent.count} domain{ent.count > 1 ? 's' : ''} connected
          </div>
        </div>
      ))}
      {sorted.length === 0 && (
        <div style={{ fontSize: 12, color: C.textMuted, padding: 20, textAlign: 'center' }}>
          No entities extracted yet
        </div>
      )}
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   MAIN PAGE
   ═══════════════════════════════════════════════════ */
export default function IntelNexus() {
  const [reports, setReports] = useState([]);
  const [signals, setSignals] = useState([]);
  const [meta, setMeta] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeEntity, setActiveEntity] = useState(null);
  const [domainFilter, setDomainFilter] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [corrData, sigData] = await Promise.all([fetchCorrelations(), fetchSignals()]);
      setReports(corrData.reports || []);
      setMeta(corrData.metadata || {});
      setSignals(sigData.signals || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Filtering
  const filteredSignals = signals.filter(s => {
    if (domainFilter && s.domain !== domainFilter) return false;
    if (activeEntity) {
      const allEnts = [...(s.entities?.countries || []), ...(s.entities?.organizations || []), ...(s.entities?.people || []), ...(s.entities?.resources || [])];
      if (!allEnts.includes(activeEntity)) return false;
    }
    return true;
  });

  const filteredReports = reports.filter(r => {
    if (activeEntity && !r.entities?.includes(activeEntity)) return false;
    if (domainFilter && !r.domains_spanned?.includes(domainFilter)) return false;
    return true;
  });

  const allDomains = ['geopolitics', 'economics', 'defense', 'technology', 'climate', 'society'];

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: C.bg, overflow: 'hidden' }}>
      {/* ── TOPBAR ─────────────────────────────────── */}
      <header style={{
        padding: '12px 20px', background: C.white, borderBottom: `1px solid ${C.border}`,
        display: 'flex', alignItems: 'center', gap: 16, flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 24 }}>🔗</span>
          <div>
            <h1 style={{ margin: 0, fontSize: 17, fontWeight: 800, color: C.textBright, letterSpacing: -0.3 }}>
              Intel Nexus
            </h1>
            <div style={{ fontSize: 11, color: C.textMuted }}>Cross-Domain Intelligence Correlation</div>
          </div>
        </div>

        {/* stats */}
        <div style={{ display: 'flex', gap: 16, marginLeft: 'auto', alignItems: 'center' }}>
          {loading ? (
            <div style={{ fontSize: 12, color: C.textMuted }}>
              <span style={{ display: 'inline-block', animation: 'spin 1s linear infinite', marginRight: 6 }}>⏳</span>
              Analyzing feeds…
            </div>
          ) : (
            <>
              <StatBox label="Signals" value={meta.signals_analyzed || 0} color={C.accent} />
              <StatBox label="Correlations" value={meta.correlations_found || 0} color="#d97706" />
              <StatBox label="Template Hits" value={meta.template_matches || 0} color="#b91c1c" />
              <StatBox label="Entities" value={meta.entities_extracted || 0} color="#6d28d9" />
            </>
          )}
          <button onClick={load} style={{
            padding: '6px 14px', borderRadius: 6, fontSize: 11, fontWeight: 700,
            background: C.accent, color: '#fff', border: 'none', cursor: 'pointer',
          }}>↻ Refresh</button>
        </div>
      </header>

      {/* ── DOMAIN FILTER BAR ────────────────────────── */}
      <div style={{
        padding: '8px 20px', background: C.white, borderBottom: `1px solid ${C.borderSoft}`,
        display: 'flex', gap: 6, alignItems: 'center', flexShrink: 0,
      }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: C.textMuted, marginRight: 6 }}>FILTER:</span>
        <button onClick={() => { setDomainFilter(null); setActiveEntity(null); }} style={{
          padding: '4px 10px', borderRadius: 5, fontSize: 10, fontWeight: 600,
          border: `1px solid ${!domainFilter ? C.accent : C.border}`,
          background: !domainFilter ? `${C.accent}12` : 'transparent',
          color: !domainFilter ? C.accent : C.textMid, cursor: 'pointer',
        }}>All</button>
        {allDomains.map(d => {
          const m = domainMeta(d);
          const isActive = domainFilter === d;
          return (
            <button key={d} onClick={() => setDomainFilter(isActive ? null : d)} style={{
              padding: '4px 10px', borderRadius: 5, fontSize: 10, fontWeight: 600,
              border: `1px solid ${isActive ? m.color : C.border}`,
              background: isActive ? `${m.color}14` : 'transparent',
              color: isActive ? m.color : C.textMid, cursor: 'pointer',
              transition: 'all .15s',
            }}>{m.icon} {m.short}</button>
          );
        })}
        {activeEntity && (
          <span style={{ marginLeft: 12, fontSize: 11, color: C.accent, fontWeight: 600 }}>
            Entity: {activeEntity}
            <button onClick={() => setActiveEntity(null)} style={{
              marginLeft: 6, background: 'none', border: 'none', color: C.red, cursor: 'pointer', fontWeight: 700, fontSize: 12,
            }}>✕</button>
          </span>
        )}
      </div>

      {/* ── ERROR STATE ──────────────────────────────── */}
      {error && (
        <div style={{ padding: '12px 20px', background: '#fef2f2', color: '#991b1b', fontSize: 12, borderBottom: '1px solid #fecaca' }}>
          ⚠ {error}
          <button onClick={load} style={{ marginLeft: 12, fontSize: 11, color: C.accent, background: 'none', border: 'none', cursor: 'pointer', fontWeight: 700 }}>Retry</button>
        </div>
      )}

      {/* ── THREE-PANEL LAYOUT ───────────────────────── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', gap: 0 }}>

        {/* LEFT — Signal Timeline */}
        <div style={{
          width: 310, flexShrink: 0, borderRight: `1px solid ${C.border}`,
          overflowY: 'auto', padding: 12, background: '#fafbfc',
        }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: C.textMuted, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 10 }}>
            Signal Timeline ({filteredSignals.length})
          </div>
          {loading ? (
            <LoadingPulse count={6} />
          ) : filteredSignals.length === 0 ? (
            <div style={{ padding: 20, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>No signals match filters</div>
          ) : (
            filteredSignals.map((s, i) => <SignalCard key={s.id || i} signal={s} />)
          )}
        </div>

        {/* CENTER — Intel Reports */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: C.textMuted, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 12 }}>
            Intelligence Reports ({filteredReports.length})
          </div>
          {loading ? (
            <LoadingPulse count={3} height={200} />
          ) : filteredReports.length === 0 ? (
            <EmptyState />
          ) : (
            filteredReports.map((r, i) => <ReportCard key={r.id || i} report={r} />)
          )}
        </div>

        {/* RIGHT — Entity Network */}
        <div style={{
          width: 260, flexShrink: 0, borderLeft: `1px solid ${C.border}`,
          overflowY: 'auto', padding: 12, background: '#fafbfc',
        }}>
          {loading ? (
            <LoadingPulse count={8} height={50} />
          ) : (
            <EntityNetwork
              reports={reports} signals={signals}
              activeEntity={activeEntity} setActiveEntity={setActiveEntity}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/* ── micro-components ────────────────────────────── */
const StatBox = ({ label, value, color }) => (
  <div style={{ textAlign: 'center' }}>
    <div style={{ fontSize: 18, fontWeight: 800, color, lineHeight: 1 }}>{value}</div>
    <div style={{ fontSize: 9, color: C.textMuted, fontWeight: 600, marginTop: 2 }}>{label}</div>
  </div>
);

const LoadingPulse = ({ count = 4, height = 80 }) => (
  <>
    {Array.from({ length: count }).map((_, i) => (
      <div key={i} style={{
        height, borderRadius: 8, marginBottom: 8,
        background: 'linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%)',
        backgroundSize: '200% 100%', animation: 'shimmer 1.5s infinite',
      }} />
    ))}
    <style>{`@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }`}</style>
  </>
);

const EmptyState = () => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 60, color: C.textMuted }}>
    <span style={{ fontSize: 48, marginBottom: 12, opacity: 0.4 }}>🔗</span>
    <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>No correlations detected</div>
    <div style={{ fontSize: 12, textAlign: 'center', maxWidth: 300 }}>
      The engine analyzes signals across domains to find hidden connections.
      Try refreshing to pull the latest feeds.
    </div>
  </div>
);
