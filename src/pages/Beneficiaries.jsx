import { useState } from 'react';
import { C, hexRgb } from '../theme';

/* ════════════════════════════════════════════════════════════════
   BENEFICIARY LINKAGE — Government Scheme Tracking
   ════════════════════════════════════════════════════════════════ */

const SCHEMES = [
    { id: 'ayushman', name: 'Ayushman Bharat', icon: '🏥', color: '#00C8FF', desc: 'Free health coverage up to ₹5L/family', target: 12000, linked: 8940 },
    { id: 'pmkisan', name: 'PM-KISAN', icon: '🌾', color: '#00E882', desc: '₹6,000/year income support to farmers', target: 5400, linked: 4200 },
    { id: 'ujjwala', name: 'Ujjwala Yojana', icon: '🔥', color: '#FF7040', desc: 'Free LPG connections to BPL women', target: 6800, linked: 5100 },
    { id: 'pmay', name: 'PM Awas Yojana', icon: '🏠', color: '#B06BFF', desc: 'Housing for all — affordable homes', target: 4200, linked: 2800 },
    { id: 'mudra', name: 'MUDRA Yojana', icon: '💰', color: '#FFCC00', desc: 'Micro-enterprise loans up to ₹10L', target: 3200, linked: 2100 },
    { id: 'scholarship', name: 'National Scholarship', icon: '📚', color: '#FF3355', desc: 'Merit scholarships for students', target: 2800, linked: 1900 },
    { id: 'pension', name: 'PM Pension Yojana', icon: '👴', color: '#00C8FF', desc: 'Monthly pension of ₹3,000 for 60+ seniors', target: 3800, linked: 2600 },
    { id: 'digital', name: 'Digital India', icon: '📱', color: '#B06BFF', desc: 'Digital literacy & internet access', target: 5000, linked: 3800 },
];

const BOOTHS = ['Booth 1', 'Booth 2', 'Booth 3', 'Booth 4', 'Booth 5', 'Booth 6', 'Booth 7', 'Booth 8', 'Booth 9', 'Booth 10'];

const genBoothSchemeData = () => BOOTHS.map(booth => {
    const data = {};
    SCHEMES.forEach(s => {
        const eligible = 50 + Math.floor(Math.random() * 150);
        const linked = Math.floor(eligible * (0.4 + Math.random() * 0.5));
        data[s.id] = { eligible, linked };
    });
    return { booth, data };
});

const BOOTH_SCHEME_DATA = genBoothSchemeData();

const genBeneficiaries = () => {
    const names = ['Ramesh Kumar', 'Sita Devi', 'Mohan Lal', 'Geeta Bai', 'Sunil Yadav', 'Kamla Devi', 'Raju Singh', 'Meera Kumari',
        'Prakash Jha', 'Anita Roy', 'Brijesh Mishra', 'Sunita Gupta', 'Dinesh Tiwari', 'Rani Devi', 'Mahesh Sharma'];
    return names.map((name, i) => ({
        id: i + 1,
        name,
        aadhaar: `XXXX-XXXX-${1000 + Math.floor(Math.random() * 9000)}`,
        booth: BOOTHS[Math.floor(Math.random() * BOOTHS.length)],
        schemes: SCHEMES.filter(() => Math.random() > 0.5).map(s => s.id),
        eligible: SCHEMES.filter(() => Math.random() > 0.4).map(s => s.id),
        status: Math.random() > 0.3 ? 'linked' : 'pending',
    }));
};

const BENEFICIARIES = genBeneficiaries();

export default function Beneficiaries() {
    const [selectedScheme, setSelectedScheme] = useState(null);
    const [selectedBooth, setSelectedBooth] = useState('all');
    const [tab, setTab] = useState('overview');
    const [searchQuery, setSearchQuery] = useState('');

    const totalTarget = SCHEMES.reduce((s, sc) => s + sc.target, 0);
    const totalLinked = SCHEMES.reduce((s, sc) => s + sc.linked, 0);
    const coveragePct = ((totalLinked / totalTarget) * 100).toFixed(1);

    const filteredBeneficiaries = BENEFICIARIES.filter(b =>
        (selectedBooth === 'all' || b.booth === selectedBooth) &&
        (!searchQuery || b.name.toLowerCase().includes(searchQuery.toLowerCase()))
    );

    return (
        <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Header */}
            <div style={{ flexShrink: 0, padding: '10px 20px', background: 'linear-gradient(180deg,#021020,#010C18)', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                    <div style={{ fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, fontSize: 16, color: C.primary, letterSpacing: '2px' }}>
                        🏥 BENEFICIARY LINKAGE SYSTEM
                    </div>
                    <div style={{ fontSize: 9, color: C.text, letterSpacing: '2px' }}>
                        GOVERNMENT SCHEME TRACKING · BOOTH-WISE MAPPING · CITIZEN BOND
                    </div>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                    {['overview', 'booths', 'lookup'].map(t => (
                        <button key={t} onClick={() => setTab(t)} style={{
                            padding: '5px 14px', fontSize: 9, letterSpacing: '1.5px',
                            background: tab === t ? C.primaryGlow : 'transparent',
                            border: `1px solid ${tab === t ? C.primary : C.border}`,
                            color: tab === t ? C.primary : C.text,
                            borderRadius: 3, fontFamily: "'Share Tech Mono',monospace",
                            textTransform: 'uppercase',
                        }}>{t}</button>
                    ))}
                </div>
            </div>

            {/* Stats Row */}
            <div style={{ flexShrink: 0, display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, padding: '12px 20px', borderBottom: `1px solid ${C.border}` }}>
                {[
                    { l: 'TOTAL SCHEMES', v: SCHEMES.length, c: C.primary, icon: '📋' },
                    { l: 'TARGET BENEFICIARIES', v: totalTarget.toLocaleString(), c: C.gold, icon: '🎯' },
                    { l: 'LINKED', v: totalLinked.toLocaleString(), c: C.green, icon: '🔗' },
                    { l: 'COVERAGE', v: `${coveragePct}%`, c: parseFloat(coveragePct) > 70 ? C.green : C.gold, icon: '📊' },
                ].map(s => (
                    <div key={s.l} className="stat-card" style={{ padding: '10px 12px' }}>
                        <div style={{ fontSize: 10, marginBottom: 4 }}>{s.icon}</div>
                        <div style={{ fontSize: 20, fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, color: s.c }}>{s.v}</div>
                        <div style={{ fontSize: 8, color: C.text, letterSpacing: '1px' }}>{s.l}</div>
                    </div>
                ))}
            </div>

            {/* Body */}
            <div style={{ flex: 1, overflow: 'hidden', display: 'flex', minHeight: 0 }}>
                {tab === 'overview' && (
                    <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                        {/* Scheme Cards */}
                        <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
                            <div style={{ fontSize: 9, color: C.text, letterSpacing: '2px', marginBottom: 12 }}>SCHEME PERFORMANCE MATRIX</div>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
                                {SCHEMES.map(s => {
                                    const pct = ((s.linked / s.target) * 100).toFixed(0);
                                    const isSelected = selectedScheme?.id === s.id;
                                    return (
                                        <div key={s.id} onClick={() => setSelectedScheme(isSelected ? null : s)}
                                            className="card" style={{
                                                padding: 14, cursor: 'pointer',
                                                borderColor: isSelected ? s.color : undefined,
                                                animation: 'slideUp 0.4s ease forwards',
                                            }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                                                <div style={{
                                                    width: 40, height: 40, borderRadius: 8,
                                                    background: `rgba(${hexRgb(s.color)},.12)`,
                                                    border: `1px solid ${s.color}33`,
                                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                    fontSize: 20,
                                                }}>{s.icon}</div>
                                                <div>
                                                    <div style={{ fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, fontSize: 13, color: C.white }}>{s.name}</div>
                                                    <div style={{ fontSize: 8, color: C.text, lineHeight: 1.4 }}>{s.desc}</div>
                                                </div>
                                            </div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                                <span style={{ fontSize: 8, color: C.text }}>Coverage</span>
                                                <span style={{ fontSize: 9, color: s.color }}>{pct}%</span>
                                            </div>
                                            <div className="progress-bar" style={{ height: 6, marginBottom: 8 }}>
                                                <div className="progress-fill" style={{ width: `${pct}%`, background: s.color }} />
                                            </div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9 }}>
                                                <span style={{ color: C.text }}>🎯 {s.target.toLocaleString()}</span>
                                                <span style={{ color: C.green }}>🔗 {s.linked.toLocaleString()}</span>
                                                <span style={{ color: C.red }}>⏳ {(s.target - s.linked).toLocaleString()}</span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Detail panel */}
                        <div style={{ width: 280, flexShrink: 0, background: C.panel, borderLeft: `1px solid ${C.border}`, overflowY: 'auto' }}>
                            {selectedScheme ? (
                                <div>
                                    <div style={{
                                        padding: '16px 14px', textAlign: 'center',
                                        background: `rgba(${hexRgb(selectedScheme.color)},.06)`,
                                        borderBottom: `1px solid ${C.border}`,
                                    }}>
                                        <div style={{ fontSize: 36, marginBottom: 6 }}>{selectedScheme.icon}</div>
                                        <div style={{ fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, fontSize: 15, color: C.white }}>
                                            {selectedScheme.name}
                                        </div>
                                        <div style={{ fontSize: 9, color: selectedScheme.color, marginTop: 4 }}>
                                            {selectedScheme.desc}
                                        </div>
                                    </div>
                                    <div style={{ padding: 14 }}>
                                        {[
                                            { l: 'Target', v: selectedScheme.target.toLocaleString(), c: C.gold },
                                            { l: 'Linked', v: selectedScheme.linked.toLocaleString(), c: C.green },
                                            { l: 'Pending', v: (selectedScheme.target - selectedScheme.linked).toLocaleString(), c: C.red },
                                            { l: 'Coverage %', v: `${((selectedScheme.linked / selectedScheme.target) * 100).toFixed(1)}%`, c: C.primary },
                                        ].map(m => (
                                            <div key={m.l} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${C.borderSoft}` }}>
                                                <span style={{ fontSize: 9, color: C.text }}>{m.l}</span>
                                                <span style={{ fontSize: 12, color: m.c, fontFamily: "'Rajdhani',sans-serif", fontWeight: 700 }}>{m.v}</span>
                                            </div>
                                        ))}
                                        <div style={{ marginTop: 14, fontSize: 9, color: C.text, letterSpacing: '1.5px', marginBottom: 10 }}>
                                            LINKAGE SUGGESTIONS
                                        </div>
                                        <div style={{ padding: 10, background: 'rgba(0,200,255,.04)', border: `1px solid ${C.border}`, borderRadius: 4 }}>
                                            <div style={{ fontSize: 9, color: C.textBright, lineHeight: 1.7 }}>
                                                ⚡ {(selectedScheme.target - selectedScheme.linked).toLocaleString()} eligible citizens remaining<br />
                                                🎯 Priority booths: Booth 3, Booth 7 (lowest linkage)<br />
                                                📱 Suggest outreach campaign via WhatsApp + door-to-door
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div style={{ padding: 30, textAlign: 'center' }}>
                                    <div style={{ fontSize: 40, opacity: .3, marginBottom: 12 }}>🏥</div>
                                    <div style={{ fontSize: 10, color: C.text, letterSpacing: '1px', lineHeight: 1.8 }}>
                                        SELECT A SCHEME<br />TO VIEW DETAILS AND<br />LINKAGE RECOMMENDATIONS
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {tab === 'booths' && (
                    <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
                        <div style={{ fontSize: 9, color: C.text, letterSpacing: '2px', marginBottom: 16 }}>
                            BOOTH-WISE SCHEME COVERAGE MATRIX
                        </div>
                        {/* Horizontal scrollable table */}
                        <div style={{ overflowX: 'auto' }}>
                            <table className="data-table">
                                <thead><tr>
                                    <th>BOOTH</th>
                                    {SCHEMES.map(s => <th key={s.id} style={{ color: s.color, textAlign: 'center' }}>{s.icon} {s.name.split(' ')[0]}</th>)}
                                    <th style={{ textAlign: 'center' }}>OVERALL</th>
                                </tr></thead>
                                <tbody>
                                    {BOOTH_SCHEME_DATA.map(row => {
                                        const totalE = Object.values(row.data).reduce((s, d) => s + d.eligible, 0);
                                        const totalL = Object.values(row.data).reduce((s, d) => s + d.linked, 0);
                                        return (
                                            <tr key={row.booth}>
                                                <td style={{ color: C.white, fontWeight: 'bold' }}>{row.booth}</td>
                                                {SCHEMES.map(s => {
                                                    const d = row.data[s.id];
                                                    const pct = ((d.linked / d.eligible) * 100).toFixed(0);
                                                    return (
                                                        <td key={s.id} style={{ textAlign: 'center' }}>
                                                            <div style={{
                                                                fontSize: 11, fontFamily: "'Rajdhani',sans-serif", fontWeight: 700,
                                                                color: parseInt(pct) > 70 ? C.green : parseInt(pct) > 40 ? C.gold : C.red
                                                            }}>
                                                                {pct}%
                                                            </div>
                                                            <div style={{ fontSize: 7, color: C.text }}>{d.linked}/{d.eligible}</div>
                                                        </td>
                                                    );
                                                })}
                                                <td style={{ textAlign: 'center' }}>
                                                    <div style={{
                                                        fontSize: 12, fontFamily: "'Rajdhani',sans-serif", fontWeight: 700,
                                                        color: ((totalL / totalE) * 100) > 60 ? C.green : C.gold
                                                    }}>
                                                        {((totalL / totalE) * 100).toFixed(0)}%
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {tab === 'lookup' && (
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                        {/* Search bar */}
                        <div style={{ flexShrink: 0, padding: '12px 20px', borderBottom: `1px solid ${C.border}`, display: 'flex', gap: 10 }}>
                            <input
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)}
                                placeholder="Search beneficiary by name..."
                                style={{
                                    flex: 1, padding: '8px 14px', background: C.surface, border: `1px solid ${C.border}`,
                                    color: C.textBright, fontSize: 10, borderRadius: 3,
                                    fontFamily: "'Share Tech Mono',monospace",
                                }}
                            />
                            <select value={selectedBooth} onChange={e => setSelectedBooth(e.target.value)} style={{
                                padding: '8px 14px', background: C.surface, border: `1px solid ${C.border}`,
                                color: C.textBright, fontSize: 10, borderRadius: 3,
                                fontFamily: "'Share Tech Mono',monospace",
                            }}>
                                <option value="all">ALL BOOTHS</option>
                                {BOOTHS.map(b => <option key={b} value={b}>{b}</option>)}
                            </select>
                        </div>
                        <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
                            <div style={{ display: 'grid', gap: 8 }}>
                                {filteredBeneficiaries.map(b => (
                                    <div key={b.id} className="card" style={{ padding: 14, display: 'flex', alignItems: 'center', gap: 14 }}>
                                        <div style={{
                                            width: 40, height: 40, borderRadius: '50%',
                                            background: 'rgba(0,200,255,.08)', border: `1px solid ${C.border}`,
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            fontSize: 18,
                                        }}>👤</div>
                                        <div style={{ flex: 1 }}>
                                            <div style={{ fontSize: 12, color: C.white, fontFamily: "'Rajdhani',sans-serif", fontWeight: 700 }}>{b.name}</div>
                                            <div style={{ fontSize: 8, color: C.text }}>Aadhaar: {b.aadhaar} · {b.booth}</div>
                                            <div style={{ display: 'flex', gap: 4, marginTop: 6, flexWrap: 'wrap' }}>
                                                {b.schemes.map(sid => {
                                                    const scheme = SCHEMES.find(s => s.id === sid);
                                                    return scheme ? (
                                                        <span key={sid} className="tag" style={{ borderColor: scheme.color + '55', color: scheme.color }}>
                                                            {scheme.icon} {scheme.name.split(' ')[0]}
                                                        </span>
                                                    ) : null;
                                                })}
                                            </div>
                                        </div>
                                        <span style={{
                                            fontSize: 8, padding: '3px 10px', borderRadius: 10,
                                            background: b.status === 'linked' ? 'rgba(0,232,130,.12)' : 'rgba(255,204,0,.12)',
                                            color: b.status === 'linked' ? C.green : C.gold,
                                        }}>● {b.status.toUpperCase()}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
