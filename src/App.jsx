import { Routes, Route, NavLink, useLocation } from 'react-router-dom';
import { C } from './theme';
import OntologyEngine from './pages/OntologyEngine';
import Segmentation from './pages/Segmentation';
import SentimentAnalysis from './pages/SentimentAnalysis';
import WorkerManagement from './pages/WorkerManagement';
import Accountability from './pages/Accountability';
import Beneficiaries from './pages/Beneficiaries';
import ContentDelivery from './pages/ContentDelivery';
import News from './pages/News';
import IntelNexus from './pages/IntelNexus';

const NAV = [
  { path: '/', icon: '🕸️', label: 'Ontology Engine', short: 'GOE' },
  { path: '/news', icon: '📰', label: 'News & Enquiry', short: 'NEWS' },
  { path: '/segmentation', icon: '🎯', label: 'Segmentation', short: 'SEG' },
  { path: '/sentiment', icon: '📊', label: 'Sentiment', short: 'SNT' },
  { path: '/workers', icon: '👷', label: 'Workers', short: 'WRK' },
  { path: '/accountability', icon: '📷', label: 'Accountability', short: 'ACC' },
  { path: '/beneficiaries', icon: '🏥', label: 'Beneficiaries', short: 'BEN' },
  { path: '/content', icon: '📡', label: 'Content', short: 'CDN' },
  { path: '/intel', icon: '🔗', label: 'Intel Nexus', short: 'INTL' },
];

export default function App() {
  const location = useLocation();

  return (
    <div style={{
      width: '100%', minHeight: '100vh',
      display: 'flex', overflow: 'hidden',
      background: C.bg,
    }}>
      {/* Government-style sidebar — clean, accessible, formal */}
      <nav style={{
        width: 80, flexShrink: 0,
        background: C.white,
        borderRight: `1px solid ${C.border}`,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', padding: '16px 0',
        zIndex: 50,
      }}>
        <div style={{
          width: 48, height: 48, borderRadius: 8,
          background: C.bg,
          border: `1px solid ${C.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 22, marginBottom: 8, color: C.primary,
        }}>🏛️</div>
        <div style={{
          fontSize: 10, color: C.text, fontWeight: 700,
          textAlign: 'center', marginBottom: 16,
        }}>GOV.IN</div>

        <div style={{ width: '60%', height: 1, background: C.borderSoft, marginBottom: 12 }} />

        {NAV.map(item => {
          const active = item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path);
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className="nav-item"
              style={{
                position: 'relative',
                width: 60, height: 60,
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                borderRadius: 8,
                marginBottom: 4,
                textDecoration: 'none',
                background: active ? '#f1f5f9' : 'transparent',
                color: active ? C.accent : C.textMid,
                border: active ? `1px solid #e2e8f0` : '1px solid transparent',
                transition: 'all 0.15s',
              }}
            >
              <span style={{ fontSize: 20 }}>{item.icon}</span>
              <span style={{ fontSize: 9, marginTop: 4, fontWeight: active ? 600 : 500 }}>{item.short}</span>
              <div className="nav-tooltip">{item.label}</div>
            </NavLink>
          );
        })}
        <div style={{ flex: 1 }} />
      </nav>

      <main style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <Routes>
          <Route path="/" element={<OntologyEngine />} />
          <Route path="/news" element={<News />} />
          <Route path="/segmentation" element={<Segmentation />} />
          <Route path="/sentiment" element={<SentimentAnalysis />} />
          <Route path="/workers" element={<WorkerManagement />} />
          <Route path="/accountability" element={<Accountability />} />
          <Route path="/beneficiaries" element={<Beneficiaries />} />
          <Route path="/content" element={<ContentDelivery />} />
          <Route path="/intel" element={<IntelNexus />} />
        </Routes>
      </main>
    </div>
  );
}
