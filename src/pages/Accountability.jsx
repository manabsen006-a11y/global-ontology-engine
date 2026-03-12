import { useState } from 'react';
import { C, hexRgb } from '../theme';

/* ════════════════════════════════════════════════════════════════
   MICRO-ACCOUNTABILITY MAPPING — Before/After Infrastructure
   ════════════════════════════════════════════════════════════════ */

const CATEGORIES = [
    { id: 'roads', label: 'Roads', color: '#FF7040', icon: '🛣️' },
    { id: 'streetlights', label: 'Streetlights', color: '#FFCC00', icon: '💡' },
    { id: 'water', label: 'Water Supply', color: '#00C8FF', icon: '💧' },
    { id: 'drainage', label: 'Drainage', color: '#B06BFF', icon: '🔧' },
    { id: 'parks', label: 'Parks', color: '#00E882', icon: '🌳' },
    { id: 'sanitation', label: 'Sanitation', color: '#FF3355', icon: '🧹' },
];

const WARDS_LIST = ['Karol Bagh', 'Rajouri Garden', 'Dwarka', 'Rohini', 'Saket', 'Laxmi Nagar', 'Pitampura', 'Model Town'];
const STREETS = ['Shanti Gali', 'MG Road', 'Nehru Marg', 'Gandhi Chowk', 'Patel Lane', 'Tagore Street', 'Bose Nagar', 'Vivekananda Path', 'Ambedkar Avenue', 'Kalam Road'];

const STATUS_MAP = {
    planned: { color: '#FFCC00', label: 'PLANNED' },
    inprogress: { color: '#00C8FF', label: 'IN PROGRESS' },
    completed: { color: '#00E882', label: 'COMPLETED' },
    verified: { color: '#B06BFF', label: 'VERIFIED' },
};

const genProjects = () => {
    const projects = [];
    for (let i = 0; i < 30; i++) {
        const cat = CATEGORIES[Math.floor(Math.random() * CATEGORIES.length)];
        const ward = WARDS_LIST[Math.floor(Math.random() * WARDS_LIST.length)];
        const street = STREETS[Math.floor(Math.random() * STREETS.length)];
        const statuses = ['planned', 'inprogress', 'completed', 'verified'];
        const status = statuses[Math.floor(Math.random() * statuses.length)];
        const budget = (5 + Math.floor(Math.random() * 45)) + ' Lakhs';
        const residents = 50 + Math.floor(Math.random() * 400);
        projects.push({
            id: i + 1,
            title: `${cat.icon} ${cat.label} — ${street}`,
            category: cat.id,
            categoryObj: cat,
            ward,
            street,
            status,
            budget,
            residents,
            startDate: `2026-0${1 + Math.floor(Math.random() * 3)}-${10 + Math.floor(Math.random() * 18)}`,
            completionDate: status === 'completed' || status === 'verified'
                ? `2026-0${2 + Math.floor(Math.random() * 2)}-${10 + Math.floor(Math.random() * 18)}`
                : null,
            notified: status === 'completed' || status === 'verified',
            beforeDesc: `Damaged/deteriorated ${cat.label.toLowerCase()} condition. Multiple complaints from residents of ${street}.`,
            afterDesc: status === 'completed' || status === 'verified'
                ? `Fully reconstructed/improved ${cat.label.toLowerCase()}. Quality verified by ward inspector.`
                : null,
        });
    }
    return projects;
};

const PROJECTS = genProjects();

export default function Accountability() {
    const [selectedProject, setSelectedProject] = useState(null);
    const [filterCat, setFilterCat] = useState('all');
    const [filterStatus, setFilterStatus] = useState('all');
    const [filterWard, setFilterWard] = useState('all');
    const [sliderPos, setSliderPos] = useState(50);

    const filtered = PROJECTS.filter(p =>
        (filterCat === 'all' || p.category === filterCat) &&
        (filterStatus === 'all' || p.status === filterStatus) &&
        (filterWard === 'all' || p.ward === filterWard)
    );

    const completedCount = PROJECTS.filter(p => p.status === 'completed' || p.status === 'verified').length;
    const inProgressCount = PROJECTS.filter(p => p.status === 'inprogress').length;
    const notifiedResidents = PROJECTS.filter(p => p.notified).reduce((s, p) => s + p.residents, 0);

    // Ward stats for ring chart
    const wardStats = WARDS_LIST.map(w => {
        const wp = PROJECTS.filter(p => p.ward === w);
        const done = wp.filter(p => p.status === 'completed' || p.status === 'verified').length;
        return { ward: w, total: wp.length, done, pct: wp.length ? ((done / wp.length) * 100).toFixed(0) : 0 };
    });

    return (
        <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Header */}
            <div style={{ flexShrink: 0, padding: '14px 20px', background: C.primary, color: C.white, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                    <div style={{ fontWeight: 700, fontSize: 16 }}>
                        Micro-Accountability Mapping
                    </div>
                    <div style={{ fontSize: 12, opacity: 0.9 }}>
                        Street-level infrastructure · Before/after proof · Citizen notifications
                    </div>
                </div>
                <div style={{ display: 'flex', gap: 18, alignItems: 'center' }}>
                    {[
                        { l: 'Projects', v: PROJECTS.length },
                        { l: 'Completed', v: completedCount },
                        { l: 'In Progress', v: inProgressCount },
                        { l: 'Notified', v: notifiedResidents.toLocaleString() },
                    ].map(s => (
                        <div key={s.l} style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: 16, fontWeight: 700 }}>{s.v}</div>
                            <div style={{ fontSize: 10, opacity: 0.85 }}>{s.l}</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Body */}
            <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 }}>
                {/* Left: Filters + Ward Stats */}
                <div style={{ width: 250, flexShrink: 0, background: C.panel, borderRight: `1px solid ${C.border}`, display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
                    <div className="section-title">FILTERS</div>
                    <div style={{ padding: 12 }}>
                        <div style={{ fontSize: 8, color: C.text, marginBottom: 6 }}>CATEGORY</div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 12 }}>
                            <button onClick={() => setFilterCat('all')} style={{
                                fontSize: 8, padding: '4px 8px', background: filterCat === 'all' ? C.primaryGlow : 'transparent',
                                border: `1px solid ${filterCat === 'all' ? C.primary : C.border}`,
                                color: filterCat === 'all' ? C.primary : C.text, borderRadius: 2, }}>ALL</button>
                            {CATEGORIES.map(cat => (
                                <button key={cat.id} onClick={() => setFilterCat(cat.id)} style={{
                                    fontSize: 8, padding: '4px 8px',
                                    background: filterCat === cat.id ? `rgba(${hexRgb(cat.color)},.15)` : 'transparent',
                                    border: `1px solid ${filterCat === cat.id ? cat.color : C.border}`,
                                    color: filterCat === cat.id ? cat.color : C.text, borderRadius: 2, }}>{cat.icon} {cat.label}</button>
                            ))}
                        </div>
                        <div style={{ fontSize: 8, color: C.text, marginBottom: 6 }}>STATUS</div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 12 }}>
                            <button onClick={() => setFilterStatus('all')} style={{
                                fontSize: 8, padding: '4px 8px', background: filterStatus === 'all' ? C.primaryGlow : 'transparent',
                                border: `1px solid ${filterStatus === 'all' ? C.primary : C.border}`,
                                color: filterStatus === 'all' ? C.primary : C.text, borderRadius: 2, }}>ALL</button>
                            {Object.entries(STATUS_MAP).map(([k, v]) => (
                                <button key={k} onClick={() => setFilterStatus(k)} style={{
                                    fontSize: 8, padding: '4px 8px',
                                    background: filterStatus === k ? `rgba(${hexRgb(v.color)},.15)` : 'transparent',
                                    border: `1px solid ${filterStatus === k ? v.color : C.border}`,
                                    color: filterStatus === k ? v.color : C.text, borderRadius: 2, }}>{v.label}</button>
                            ))}
                        </div>
                        <div style={{ fontSize: 8, color: C.text, marginBottom: 6 }}>WARD</div>
                        <select value={filterWard} onChange={e => setFilterWard(e.target.value)} style={{
                            width: '100%', padding: '5px 10px', fontSize: 9, background: C.surface, border: `1px solid ${C.border}`,
                            color: C.white, borderRadius: 3, }}>
                            <option value="all">ALL WARDS</option>
                            {WARDS_LIST.map(w => <option key={w} value={w}>{w}</option>)}
                        </select>
                    </div>

                    <div className="section-title">WARD COMPLETION RATES</div>
                    <div style={{ padding: 12 }}>
                        {wardStats.map(ws => (
                            <div key={ws.ward} style={{ marginBottom: 8 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                                    <span style={{ fontSize: 9, color: C.textBright }}>{ws.ward}</span>
                                    <span style={{ fontSize: 9, color: parseInt(ws.pct) > 60 ? C.green : C.gold }}>{ws.pct}%</span>
                                </div>
                                <div className="progress-bar">
                                    <div className="progress-fill" style={{
                                        width: `${ws.pct}%`,
                                        background: parseInt(ws.pct) > 60 ? C.green : parseInt(ws.pct) > 30 ? C.gold : C.red,
                                    }} />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Center: Project List */}
                <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
                    <div style={{ fontSize: 9, color: C.text, marginBottom: 12 }}>
                        {filtered.length} PROJECTS · CLICK FOR DETAILS
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
                        {filtered.map(p => {
                            const isSelected = selectedProject?.id === p.id;
                            return (
                                <div key={p.id} onClick={() => setSelectedProject(isSelected ? null : p)}
                                    className="card" style={{
                                        padding: 12, cursor: 'pointer',
                                        borderColor: isSelected ? C.primary : undefined,
                                        animation: 'slideUp 0.4s ease forwards',
                                    }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                                        <span style={{ fontSize: 11, fontWeight: 700, color: C.textBright }}>
                                            {p.title}
                                        </span>
                                    </div>
                                    <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
                                        <span className="tag" style={{ borderColor: STATUS_MAP[p.status].color + '55', color: STATUS_MAP[p.status].color }}>
                                            {STATUS_MAP[p.status].label}
                                        </span>
                                        <span className="tag">{p.ward}</span>
                                        <span className="tag">{p.street}</span>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9 }}>
                                        <span style={{ color: C.text }}>💰 ₹{p.budget}</span>
                                        <span style={{ color: C.text }}>👥 {p.residents} residents</span>
                                    </div>
                                    {p.notified && (
                                        <div style={{
                                            marginTop: 8, padding: '4px 8px', borderRadius: 3,
                                            background: 'rgba(176,107,255,.08)', border: `1px solid ${C.purple}33`,
                                            fontSize: 8, color: C.purple, display: 'flex', alignItems: 'center', gap: 4,
                                        }}>
                                            📣 Notification sent to {p.residents} residents
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Right: Project Detail + Before/After */}
                <div style={{ width: 300, flexShrink: 0, background: C.panel, borderLeft: `1px solid ${C.border}`, overflowY: 'auto' }}>
                    {selectedProject ? (
                        <div>
                            <div style={{
                                padding: '14px', background: `rgba(${hexRgb(selectedProject.categoryObj.color)},.06)`,
                                borderBottom: `1px solid ${C.border}`,
                            }}>
                                <div style={{ fontSize: 24, marginBottom: 6 }}>{selectedProject.categoryObj.icon}</div>
                                <div style={{ fontWeight: 700, fontSize: 15, color: C.textBright }}>
                                    {selectedProject.categoryObj.label} Improvement
                                </div>
                                <div style={{ fontSize: 9, color: selectedProject.categoryObj.color, }}>
                                    {selectedProject.street} · {selectedProject.ward}
                                </div>
                            </div>

                            {/* Before / After Comparison */}
                            <div style={{ padding: 14 }}>
                                <div style={{ fontSize: 9, color: C.text, marginBottom: 10 }}>BEFORE / AFTER COMPARISON</div>
                                <div style={{ position: 'relative', height: 160, borderRadius: 4, overflow: 'hidden', border: `1px solid ${C.border}`, marginBottom: 12 }}>
                                    {/* Before side */}
                                    <div style={{
                                        position: 'absolute', left: 0, top: 0, width: `${sliderPos}%`, height: '100%',
                                        background: `linear-gradient(135deg, rgba(255,51,85,.2), rgba(255,140,0,.15))`,
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        overflow: 'hidden',
                                    }}>
                                        <div style={{ textAlign: 'center' }}>
                                            <div style={{ fontSize: 30, marginBottom: 4 }}>⚠️</div>
                                            <div style={{ fontSize: 10, color: C.red, fontWeight: 'bold' }}>BEFORE</div>
                                            <div style={{ fontSize: 8, color: C.text, padding: '0 10px', marginTop: 4 }}>
                                                {selectedProject.beforeDesc}
                                            </div>
                                        </div>
                                    </div>
                                    {/* After side */}
                                    <div style={{
                                        position: 'absolute', right: 0, top: 0, width: `${100 - sliderPos}%`, height: '100%',
                                        background: `linear-gradient(135deg, rgba(0,232,130,.15), rgba(0,200,255,.1))`,
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        overflow: 'hidden',
                                    }}>
                                        <div style={{ textAlign: 'center' }}>
                                            <div style={{ fontSize: 30, marginBottom: 4 }}>✅</div>
                                            <div style={{ fontSize: 10, color: C.green, fontWeight: 'bold' }}>AFTER</div>
                                            <div style={{ fontSize: 8, color: C.text, padding: '0 10px', marginTop: 4 }}>
                                                {selectedProject.afterDesc || 'Work in progress...'}
                                            </div>
                                        </div>
                                    </div>
                                    {/* Slider line */}
                                    <div style={{
                                        position: 'absolute', left: `${sliderPos}%`, top: 0, bottom: 0,
                                        width: 3, background: C.white, zIndex: 2, cursor: 'ew-resize',
                                        transform: 'translateX(-50%)',
                                    }} />
                                </div>
                                <input type="range" min="5" max="95" value={sliderPos} onChange={e => setSliderPos(e.target.value)}
                                    style={{ width: '100%', marginBottom: 14 }}
                                />

                                {/* Timeline */}
                                <div style={{ fontSize: 9, color: C.text, marginBottom: 10 }}>PROJECT TIMELINE</div>
                                <div style={{ borderLeft: `2px solid ${C.border}`, paddingLeft: 14, marginLeft: 6 }}>
                                    {[
                                        { label: 'Project Initiated', date: selectedProject.startDate, done: true },
                                        { label: 'Work Commenced', date: selectedProject.status !== 'planned' ? selectedProject.startDate : '—', done: selectedProject.status !== 'planned' },
                                        { label: 'Completion', date: selectedProject.completionDate || 'Pending', done: selectedProject.status === 'completed' || selectedProject.status === 'verified' },
                                        { label: 'Notification Sent', date: selectedProject.notified ? 'Done' : 'Pending', done: selectedProject.notified },
                                    ].map((step, i) => (
                                        <div key={i} style={{ marginBottom: 14, position: 'relative' }}>
                                            <div style={{
                                                position: 'absolute', left: -20, top: 2,
                                                width: 10, height: 10, borderRadius: '50%',
                                                background: step.done ? C.green : C.borderSoft,
                                                border: `2px solid ${step.done ? C.green : C.border}`,
                                            }} />
                                            <div style={{ fontSize: 10, color: step.done ? C.textBright : C.text }}>{step.label}</div>
                                            <div style={{ fontSize: 8, color: step.done ? C.green : C.text }}>{step.date}</div>
                                        </div>
                                    ))}
                                </div>

                                {/* Notification Preview */}
                                {selectedProject.notified && (
                                    <div style={{
                                        padding: 12, background: 'rgba(176,107,255,.06)', border: `1px solid ${C.purple}33`,
                                        borderRadius: 4, marginTop: 10,
                                    }}>
                                        <div style={{ fontSize: 9, color: C.purple, marginBottom: 6 }}>📣 NOTIFICATION SENT</div>
                                        <div style={{ fontSize: 9, color: C.textBright, lineHeight: 1.6 }}>
                                            "New {selectedProject.categoryObj.label.toLowerCase()} improvement on {selectedProject.street}! Your area has been upgraded.
                                            Verified by ward inspector. View before/after proof in the app."
                                        </div>
                                        <div style={{ fontSize: 8, color: C.text, marginTop: 6 }}>
                                            Sent to {selectedProject.residents} residents of {selectedProject.street}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div style={{ padding: 30, textAlign: 'center' }}>
                            <div style={{ fontSize: 40, opacity: .3, marginBottom: 12 }}>📷</div>
                            <div style={{ fontSize: 10, color: C.text, lineHeight: 1.8 }}>
                                SELECT A PROJECT TO VIEW<br />BEFORE/AFTER COMPARISON<br />AND NOTIFICATION STATUS
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
