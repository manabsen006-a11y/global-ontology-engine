import { useState } from 'react';
import { Routes, Route, NavLink, useLocation } from 'react-router-dom';
import { C, hexRgb } from './theme';
import OntologyEngine from './pages/OntologyEngine';
import Segmentation from './pages/Segmentation';
import SentimentAnalysis from './pages/SentimentAnalysis';
import WorkerManagement from './pages/WorkerManagement';
import Accountability from './pages/Accountability';
import Beneficiaries from './pages/Beneficiaries';
import ContentDelivery from './pages/ContentDelivery';

const NAV = [
    { path: '/', icon: '🕸️', label: 'ONTOLOGY ENGINE', short: 'GOE' },
    { path: '/segmentation', icon: '🎯', label: 'SEGMENTATION', short: 'SEG' },
    { path: '/sentiment', icon: '📊', label: 'SENTIMENT ENGINE', short: 'SNT' },
    { path: '/workers', icon: '👷', label: 'WORKER MGMT', short: 'WRK' },
    { path: '/accountability', icon: '📷', label: 'ACCOUNTABILITY', short: 'ACC' },
    { path: '/beneficiaries', icon: '🏥', label: 'BENEFICIARIES', short: 'BEN' },
    { path: '/content', icon: '📡', label: 'CONTENT DELIVERY', short: 'CDN' },
];

export default function App() {
    const location = useLocation();
    const [time, setTime] = useState(new Date());

    // Update clock
    useState(() => {
        const id = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(id);
    });

    return (
        <div style={{
            width: '100%', height: '100vh',
            display: 'flex', overflow: 'hidden',
            background: C.bg,
        }}>
            {/* ═══ SIDEBAR NAV ═══════════════════════════════════════ */}
            <nav style={{
                width: 58, flexShrink: 0,
                background: 'linear-gradient(180deg, #021020 0%, #010C18 50%, #020F1E 100%)',
                borderRight: `1px solid ${C.border}`,
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', padding: '10px 0',
                zIndex: 50,
            }}>
                {/* Logo */}
                <div style={{
                    width: 36, height: 36, borderRadius: '50%',
                    border: `2px solid ${C.primary}`,
                    background: `radial-gradient(circle, rgba(0,200,255,.18) 0%, transparent 70%)`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 16, boxShadow: `0 0 14px rgba(0,200,255,.4)`,
                    marginBottom: 6,
                }}>🕸️</div>
                <div style={{
                    fontSize: 7, color: C.primary, letterSpacing: '1.5px',
                    fontFamily: "'Rajdhani', sans-serif", fontWeight: 700,
                    lineHeight: 1.2, textAlign: 'center', marginBottom: 14,
                }}>GOE<br />v4.2</div>

                <div style={{
                    width: '70%', height: 1,
                    background: `linear-gradient(90deg, transparent, ${C.border}, transparent)`,
                    marginBottom: 12,
                }} />

                {/* Nav items */}
                {NAV.map(item => {
                    const active = item.path === '/'
                        ? location.pathname === '/'
                        : location.pathname.startsWith(item.path);
                    return (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            className="nav-item"
                            style={{
                                position: 'relative',
                                width: 42, height: 42,
                                display: 'flex', flexDirection: 'column',
                                alignItems: 'center', justifyContent: 'center',
                                borderRadius: 4,
                                marginBottom: 4,
                                textDecoration: 'none',
                                background: active ? `rgba(0,200,255,.12)` : 'transparent',
                                border: `1px solid ${active ? C.primary + '44' : 'transparent'}`,
                                transition: 'all .2s',
                            }}
                        >
                            <span style={{ fontSize: 16, lineHeight: 1 }}>{item.icon}</span>
                            <span style={{
                                fontSize: 6.5, letterSpacing: '1px',
                                color: active ? C.primary : C.text,
                                marginTop: 2,
                                fontFamily: "'Share Tech Mono', monospace",
                            }}>{item.short}</span>
                            <div className="nav-tooltip">{item.label}</div>
                        </NavLink>
                    );
                })}

                <div style={{ flex: 1 }} />

                {/* Status indicator */}
                <div style={{
                    display: 'flex', flexDirection: 'column',
                    alignItems: 'center', gap: 6, paddingBottom: 8,
                }}>
                    <div style={{
                        width: 8, height: 8, borderRadius: '50%',
                        background: C.green,
                        boxShadow: `0 0 8px ${C.green}`,
                        animation: 'pulse 2s ease infinite',
                    }} />
                    <div style={{
                        fontSize: 7, color: C.text, letterSpacing: '1px',
                        writingMode: 'vertical-rl', textOrientation: 'mixed',
                        transform: 'rotate(180deg)',
                    }}>LIVE</div>
                </div>
            </nav>

            {/* ═══ MAIN CONTENT ═════════════════════════════════════ */}
            <main style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <Routes>
                    <Route path="/" element={<OntologyEngine />} />
                    <Route path="/segmentation" element={<Segmentation />} />
                    <Route path="/sentiment" element={<SentimentAnalysis />} />
                    <Route path="/workers" element={<WorkerManagement />} />
                    <Route path="/accountability" element={<Accountability />} />
                    <Route path="/beneficiaries" element={<Beneficiaries />} />
                    <Route path="/content" element={<ContentDelivery />} />
                </Routes>
            </main>
        </div>
    );
}
