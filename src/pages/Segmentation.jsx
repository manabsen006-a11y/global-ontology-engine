import { useState, useEffect, useRef } from 'react';
import { C, hexRgb } from '../theme';

/* ════════════════════════════════════════════════════════════════
   INTELLIGENT SEGMENTATION — Booth-level Voter Analytics
   ════════════════════════════════════════════════════════════════ */

const SEGMENTS = [
    { id: 'youth', label: 'Youth (18-35)', color: '#B06BFF', icon: '🎓', pct: 34 },
    { id: 'business', label: 'Businessmen', color: '#FFCC00', icon: '💼', pct: 18 },
    { id: 'farmers', label: 'Farmers', color: '#00E882', icon: '🌾', pct: 22 },
    { id: 'women', label: 'Women', color: '#FF7040', icon: '👩', pct: 26 },
    { id: 'senior', label: 'Senior Citizens', color: '#00C8FF', icon: '🏛️', pct: 15 },
];

const CONSTITUENCIES = [
    'New Delhi', 'Chandni Chowk', 'East Delhi', 'South Delhi', 'North West Delhi'
];

const genBooths = () => {
    const booths = [];
    CONSTITUENCIES.forEach((c, ci) => {
        for (let i = 1; i <= 10; i++) {
            const total = 800 + Math.floor(Math.random() * 1200);
            const segs = {};
            let remaining = total;
            SEGMENTS.forEach((s, si) => {
                if (si === SEGMENTS.length - 1) { segs[s.id] = remaining; }
                else {
                    const v = Math.floor(remaining * (s.pct / 100) * (0.7 + Math.random() * 0.6));
                    segs[s.id] = Math.min(v, remaining);
                    remaining -= segs[s.id];
                }
            });
            const keyVoterScore = Math.floor(40 + Math.random() * 60);
            booths.push({
                id: `${c.replace(/\s/g, '')}-B${i}`,
                name: `Booth ${ci * 10 + i}`,
                constituency: c,
                total,
                segments: segs,
                keyVoterScore,
                turnoutLast: Math.floor(55 + Math.random() * 30),
                swing: (Math.random() * 20 - 10).toFixed(1),
            });
        }
    });
    return booths;
};

const BOOTH_DATA = genBooths();

export default function Segmentation() {
    const [selectedConstituency, setSelectedConstituency] = useState('all');
    const [selectedBooth, setSelectedBooth] = useState(null);
    const [hoveredSeg, setHoveredSeg] = useState(null);
    const canvasRef = useRef(null);

    const filtered = selectedConstituency === 'all'
        ? BOOTH_DATA
        : BOOTH_DATA.filter(b => b.constituency === selectedConstituency);

    const totalVoters = filtered.reduce((s, b) => s + b.total, 0);
    const avgTurnout = (filtered.reduce((s, b) => s + b.turnoutLast, 0) / filtered.length).toFixed(1);
    const avgKeyVoter = (filtered.reduce((s, b) => s + b.keyVoterScore, 0) / filtered.length).toFixed(0);
    const segTotals = {};
    SEGMENTS.forEach(s => { segTotals[s.id] = filtered.reduce((sum, b) => sum + (b.segments[s.id] || 0), 0); });

    // Draw donut
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width = 200;
        const h = canvas.height = 200;
        ctx.clearRect(0, 0, w, h);
        const cx = w / 2, cy = h / 2, r = 70, lineW = 22;
        let startAngle = -Math.PI / 2;
        const total = SEGMENTS.reduce((s, seg) => s + (segTotals[seg.id] || 0), 0);
        SEGMENTS.forEach(seg => {
            const val = segTotals[seg.id] || 0;
            const sweep = (val / total) * Math.PI * 2;
            ctx.beginPath();
            ctx.arc(cx, cy, r, startAngle, startAngle + sweep);
            ctx.strokeStyle = hoveredSeg === seg.id ? seg.color : seg.color + 'BB';
            ctx.lineWidth = hoveredSeg === seg.id ? lineW + 6 : lineW;
            ctx.lineCap = 'butt';
            ctx.stroke();
            startAngle += sweep;
        });
        // Center text
        ctx.fillStyle = C.white;
        ctx.font = "bold 22px 'Rajdhani', sans-serif";
        ctx.textAlign = 'center';
        ctx.fillText(totalVoters.toLocaleString(), cx, cy - 2);
        ctx.fillStyle = C.text;
        ctx.font = "10px 'Share Tech Mono', monospace";
        ctx.fillText('TOTAL VOTERS', cx, cy + 16);
    }, [segTotals, hoveredSeg, totalVoters]);

    return (
        <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Header */}
            <div style={{
                flexShrink: 0, padding: '14px 20px',
                background: C.primary, color: C.white,
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
                <div>
                    <div style={{ fontWeight: 700, fontSize: 16 }}>
                        Intelligent Segmentation
                    </div>
                    <div style={{ fontSize: 12, opacity: 0.9 }}>
                        Booth-level voter analytics · Key voter identification
                    </div>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                    <button
                        onClick={() => { setSelectedConstituency('all'); setSelectedBooth(null); }}
                        style={{
                            padding: '6px 14px', fontSize: 12,
                            background: selectedConstituency === 'all' ? 'rgba(255,255,255,0.2)' : 'transparent',
                            border: `1px solid ${selectedConstituency === 'all' ? C.white : 'rgba(255,255,255,0.5)'}`,
                            color: C.white, borderRadius: 4,
                        }}>All</button>
                    {CONSTITUENCIES.map(c => (
                        <button key={c}
                            onClick={() => { setSelectedConstituency(c); setSelectedBooth(null); }}
                            style={{
                                padding: '6px 14px', fontSize: 12,
                                background: selectedConstituency === c ? 'rgba(255,255,255,0.2)' : 'transparent',
                                border: `1px solid ${selectedConstituency === c ? C.white : 'rgba(255,255,255,0.5)'}`,
                                color: C.white, borderRadius: 4,
                            }}>{c.slice(0, 10)}</button>
                    ))}
                </div>
            </div>

            {/* Body */}
            <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 }}>
                {/* Left: Stats + Donut */}
                <div style={{
                    width: 280, flexShrink: 0, background: C.panel, borderRight: `1px solid ${C.border}`,
                    display: 'flex', flexDirection: 'column', overflowY: 'auto',
                }}>
                    <div className="section-title">DEMOGRAPHIC OVERVIEW</div>
                    <div style={{ padding: 16, display: 'flex', justifyContent: 'center' }}>
                        <canvas ref={canvasRef} style={{ width: 200, height: 200 }} />
                    </div>
                    {/* Segment breakdown */}
                    <div style={{ padding: '0 16px 16px' }}>
                        {SEGMENTS.map(seg => {
                            const val = segTotals[seg.id] || 0;
                            const pct = totalVoters ? ((val / totalVoters) * 100).toFixed(1) : 0;
                            return (
                                <div key={seg.id}
                                    onMouseEnter={() => setHoveredSeg(seg.id)}
                                    onMouseLeave={() => setHoveredSeg(null)}
                                    style={{
                                        padding: '8px 10px', marginBottom: 4, borderRadius: 3,
                                        background: hoveredSeg === seg.id ? `rgba(${hexRgb(seg.color)},.1)` : 'transparent',
                                        border: `1px solid ${hoveredSeg === seg.id ? seg.color + '44' : 'transparent'}`,
                                        cursor: 'pointer', transition: 'all .2s',
                                    }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                        <span style={{ fontSize: 10, color: seg.color }}>{seg.icon} {seg.label}</span>
                                        <span style={{ fontSize: 10, color: C.textBright }}>{val.toLocaleString()} ({pct}%)</span>
                                    </div>
                                    <div className="progress-bar">
                                        <div className="progress-fill" style={{ width: `${pct}%`, background: seg.color }} />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                    {/* Aggregate stats */}
                    <div style={{ padding: '0 16px 16px' }}>
                        <div className="section-title" style={{ border: 'none', padding: '8px 0', marginBottom: 8 }}>KEY METRICS</div>
                        {[
                            { l: 'Total Booths', v: filtered.length, c: C.primary },
                            { l: 'Avg Turnout', v: `${avgTurnout}%`, c: C.green },
                            { l: 'Key Voter Index', v: `${avgKeyVoter}/100`, c: C.gold },
                            { l: 'Total Voters', v: totalVoters.toLocaleString(), c: C.primary },
                        ].map(m => (
                            <div key={m.l} style={{
                                display: 'flex', justifyContent: 'space-between', padding: '6px 0',
                                borderBottom: `1px solid ${C.borderSoft}`,
                            }}>
                                <span style={{ fontSize: 9, color: C.text, }}>{m.l}</span>
                                <span style={{ fontSize: 11, color: m.c, fontWeight: 700 }}>{m.v}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Center: Booth Grid */}
                <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
                    <div style={{ fontSize: 9, color: C.text, marginBottom: 12 }}>
                        BOOTH MATRIX — {filtered.length} BOOTHS · CLICK FOR DETAILS
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10 }}>
                        {filtered.map(booth => {
                            const isSelected = selectedBooth?.id === booth.id;
                            return (
                                <div key={booth.id} onClick={() => setSelectedBooth(isSelected ? null : booth)}
                                    className="card" style={{
                                        padding: 12, cursor: 'pointer',
                                        borderColor: isSelected ? C.primary : undefined,
                                        background: isSelected ? `rgba(0,200,255,.05)` : undefined,
                                        animation: 'slideUp 0.4s ease forwards',
                                    }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                                        <span style={{ fontSize: 11, fontWeight: 700, color: C.textBright }}>
                                            {booth.name}
                                        </span>
                                        <span style={{
                                            fontSize: 8, padding: '1px 6px', borderRadius: 2,
                                            background: booth.keyVoterScore > 75 ? 'rgba(0,232,130,.15)' : booth.keyVoterScore > 50 ? 'rgba(255,204,0,.15)' : 'rgba(255,51,85,.15)',
                                            color: booth.keyVoterScore > 75 ? C.green : booth.keyVoterScore > 50 ? C.gold : C.red,
                                            border: `1px solid ${booth.keyVoterScore > 75 ? C.green : booth.keyVoterScore > 50 ? C.gold : C.red}44`,
                                        }}>KV:{booth.keyVoterScore}</span>
                                    </div>
                                    <div style={{ fontSize: 8, color: C.text, marginBottom: 8, }}>
                                        {booth.constituency} · {booth.total.toLocaleString()} voters
                                    </div>
                                    {/* Mini segment bars */}
                                    <div style={{ display: 'flex', height: 6, borderRadius: 3, overflow: 'hidden', marginBottom: 6 }}>
                                        {SEGMENTS.map(seg => (
                                            <div key={seg.id} style={{
                                                width: `${(booth.segments[seg.id] / booth.total) * 100}%`,
                                                background: seg.color, minWidth: 2,
                                            }} />
                                        ))}
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span style={{ fontSize: 8, color: C.text }}>
                                            Turnout: <span style={{ color: booth.turnoutLast > 70 ? C.green : C.gold }}>{booth.turnoutLast}%</span>
                                        </span>
                                        <span style={{ fontSize: 8, color: parseFloat(booth.swing) > 0 ? C.green : C.red }}>
                                            {parseFloat(booth.swing) > 0 ? '▲' : '▼'} {Math.abs(booth.swing)}%
                                        </span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Right: Booth Detail */}
                <div style={{
                    width: 280, flexShrink: 0, background: C.panel, borderLeft: `1px solid ${C.border}`,
                    display: 'flex', flexDirection: 'column', overflowY: 'auto',
                }}>
                    {selectedBooth ? (
                        <>
                            <div style={{
                                padding: '12px 14px',
                                background: `rgba(0,200,255,.06)`,
                                borderBottom: `1px solid ${C.border}`,
                            }}>
                                <div style={{ fontWeight: 700, fontSize: 16, color: C.textBright }}>
                                    {selectedBooth.name}
                                </div>
                                <div style={{ fontSize: 9, color: C.primary, }}>
                                    {selectedBooth.constituency.toUpperCase()} · ID: {selectedBooth.id}
                                </div>
                            </div>
                            <div style={{ padding: 14 }}>
                                <div style={{ fontSize: 9, color: C.text, marginBottom: 10 }}>SEGMENT BREAKDOWN</div>
                                {SEGMENTS.map(seg => {
                                    const v = selectedBooth.segments[seg.id] || 0;
                                    const pct = ((v / selectedBooth.total) * 100).toFixed(1);
                                    return (
                                        <div key={seg.id} style={{ marginBottom: 10 }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                                                <span style={{ fontSize: 10, color: seg.color }}>{seg.icon} {seg.label}</span>
                                                <span style={{ fontSize: 10, color: C.textBright }}>{v} ({pct}%)</span>
                                            </div>
                                            <div className="progress-bar" style={{ height: 5 }}>
                                                <div className="progress-fill" style={{ width: `${pct}%`, background: seg.color }} />
                                            </div>
                                        </div>
                                    );
                                })}
                                <div style={{ marginTop: 16, padding: 10, background: 'rgba(0,200,255,.05)', border: `1px solid ${C.border}`, borderRadius: 4 }}>
                                    <div style={{ fontSize: 9, color: C.text, marginBottom: 8 }}>KEY VOTER ANALYSIS</div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                                        <div style={{
                                            width: 50, height: 50, borderRadius: '50%',
                                            border: `3px solid ${selectedBooth.keyVoterScore > 75 ? C.green : selectedBooth.keyVoterScore > 50 ? C.gold : C.red}`,
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            fontWeight: 700, fontSize: 18,
                                            color: selectedBooth.keyVoterScore > 75 ? C.green : selectedBooth.keyVoterScore > 50 ? C.gold : C.red,
                                        }}>{selectedBooth.keyVoterScore}</div>
                                        <div>
                                            <div style={{ fontSize: 10, color: C.textBright }}>
                                                {selectedBooth.keyVoterScore > 75 ? 'HIGH PRIORITY' : selectedBooth.keyVoterScore > 50 ? 'MODERATE' : 'LOW PRIORITY'}
                                            </div>
                                            <div style={{ fontSize: 8, color: C.text }}>Key Voter Concentration Index</div>
                                        </div>
                                    </div>
                                    <div style={{ fontSize: 9, color: C.textMid, lineHeight: 1.7 }}>
                                        {selectedBooth.keyVoterScore > 75
                                            ? '⚡ High concentration of swing voters. Priority booth for targeted outreach and resource allocation.'
                                            : selectedBooth.keyVoterScore > 50
                                                ? '📊 Moderate voter engagement potential. Standard campaign coverage recommended.'
                                                : '📋 Stable voting patterns. Maintenance-level engagement sufficient.'}
                                    </div>
                                </div>
                                <div style={{ marginTop: 12, padding: 10, background: 'rgba(0,200,255,.03)', border: `1px solid ${C.borderSoft}`, borderRadius: 4 }}>
                                    <div style={{ fontSize: 9, color: C.text, marginBottom: 6 }}>PERFORMANCE</div>
                                    {[
                                        { l: 'Last Turnout', v: `${selectedBooth.turnoutLast}%`, c: selectedBooth.turnoutLast > 70 ? C.green : C.gold },
                                        { l: 'Swing Factor', v: `${selectedBooth.swing}%`, c: parseFloat(selectedBooth.swing) > 0 ? C.green : C.red },
                                        { l: 'Total Registered', v: selectedBooth.total.toLocaleString(), c: C.primary },
                                    ].map(m => (
                                        <div key={m.l} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: `1px solid ${C.borderSoft}` }}>
                                            <span style={{ fontSize: 9, color: C.text }}>{m.l}</span>
                                            <span style={{ fontSize: 10, color: m.c, fontWeight: 600 }}>{m.v}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </>
                    ) : (
                        <div style={{ padding: 30, textAlign: 'center' }}>
                            <div style={{ fontSize: 40, opacity: .3, marginBottom: 12 }}>🎯</div>
                            <div style={{ fontSize: 10, color: C.text, lineHeight: 1.8 }}>
                                SELECT A BOOTH TO VIEW<br />DETAILED VOTER SEGMENTATION<br />AND KEY VOTER ANALYSIS
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
