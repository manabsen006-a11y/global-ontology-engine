import { useState } from 'react';
import { C, hexRgb } from '../theme';

/* ════════════════════════════════════════════════════════════════
   PARTY WORKER MANAGEMENT SYSTEM
   ════════════════════════════════════════════════════════════════ */

const ROLES = ['Booth President', 'Sector Incharge', 'Ward Coordinator', 'Volunteer', 'Social Media Lead'];
const AREAS = ['Karol Bagh', 'Rajouri Garden', 'Dwarka', 'Rohini', 'Saket', 'Laxmi Nagar', 'Mayur Vihar', 'Pitampura'];
const NAMES = [
    'Rahul Sharma', 'Priya Patel', 'Amit Kumar', 'Sunita Devi', 'Rajesh Gupta',
    'Meena Kumari', 'Vikram Singh', 'Anita Verma', 'Deepak Joshi', 'Kavita Rao',
    'Manoj Tiwari', 'Pooja Nair', 'Suresh Yadav', 'Neha Agarwal', 'Ravi Shankar',
    'Sonal Mehta', 'Ajay Dubey', 'Rekha Chaudhary', 'Nitin Saxena', 'Geeta Bhandari',
    'Ashok Mishra', 'Pallavi Iyer', 'Sanjay Pandey', 'Usha Rawat', 'Karan Malhotra',
];

const genWorkers = () => NAMES.map((name, i) => ({
    id: i + 1,
    name,
    role: ROLES[Math.floor(Math.random() * ROLES.length)],
    area: AREAS[Math.floor(Math.random() * AREAS.length)],
    phone: `+91 ${9000000000 + Math.floor(Math.random() * 999999999)}`,
    tasksAssigned: 5 + Math.floor(Math.random() * 15),
    tasksCompleted: 0,
    performance: Math.floor(30 + Math.random() * 70),
    lastActive: new Date(Date.now() - Math.random() * 86400000 * 3),
    status: Math.random() > 0.2 ? 'active' : 'inactive',
    avatar: ['👨', '👩', '👨‍💼', '👩‍💼', '🧑'][Math.floor(Math.random() * 5)],
    dailyLog: Array.from({ length: 7 }, (_, d) => ({
        day: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d],
        tasks: Math.floor(Math.random() * 8),
        hours: (2 + Math.random() * 6).toFixed(1),
        contacts: Math.floor(Math.random() * 30),
    })),
}));

const WORKERS = genWorkers().map(w => ({
    ...w,
    tasksCompleted: Math.floor(w.tasksAssigned * (w.performance / 100) * (0.8 + Math.random() * 0.4)),
}));

const CAMPAIGNS = [
    { name: 'Door-to-Door Voter Outreach', status: 'active', progress: 67, workers: 18, deadline: '2026-03-20' },
    { name: 'Social Media Blitz Q1', status: 'active', progress: 82, workers: 8, deadline: '2026-03-15' },
    { name: 'Youth Rally — Dwarka', status: 'upcoming', progress: 25, workers: 12, deadline: '2026-04-05' },
    { name: 'Women Empowerment Drive', status: 'completed', progress: 100, workers: 15, deadline: '2026-02-28' },
    { name: 'Farmer Meet — Rohini', status: 'active', progress: 45, workers: 10, deadline: '2026-03-25' },
];

export default function WorkerManagement() {
    const [selectedWorker, setSelectedWorker] = useState(null);
    const [filterRole, setFilterRole] = useState('all');
    const [filterArea, setFilterArea] = useState('all');
    const [tab, setTab] = useState('workers');

    const filtered = WORKERS.filter(w =>
        (filterRole === 'all' || w.role === filterRole) &&
        (filterArea === 'all' || w.area === filterArea)
    );

    const activeCount = WORKERS.filter(w => w.status === 'active').length;
    const avgPerf = (WORKERS.reduce((s, w) => s + w.performance, 0) / WORKERS.length).toFixed(0);
    const totalTasks = WORKERS.reduce((s, w) => s + w.tasksAssigned, 0);
    const completedTasks = WORKERS.reduce((s, w) => s + w.tasksCompleted, 0);

    return (
        <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Header */}
            <div style={{
                flexShrink: 0, padding: '10px 20px',
                background: 'linear-gradient(180deg,#021020,#010C18)',
                borderBottom: `1px solid ${C.border}`,
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
                <div>
                    <div style={{ fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, fontSize: 16, color: C.primary, letterSpacing: '2px' }}>
                        👷 PARTY WORKER MANAGEMENT SYSTEM
                    </div>
                    <div style={{ fontSize: 9, color: C.text, letterSpacing: '2px' }}>
                        PROFILES · TASKS · PERFORMANCE · CAMPAIGNS
                    </div>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                    {['workers', 'campaigns', 'leaderboard'].map(t => (
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
            <div style={{ flexShrink: 0, display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, padding: '12px 20px', borderBottom: `1px solid ${C.border}` }}>
                {[
                    { l: 'TOTAL WORKERS', v: WORKERS.length, c: C.primary, icon: '👥' },
                    { l: 'ACTIVE NOW', v: activeCount, c: C.green, icon: '🟢' },
                    { l: 'AVG PERFORMANCE', v: `${avgPerf}%`, c: parseInt(avgPerf) > 60 ? C.green : C.gold, icon: '📊' },
                    { l: 'TASKS ASSIGNED', v: totalTasks, c: C.purple, icon: '📋' },
                    { l: 'COMPLETION RATE', v: `${((completedTasks / totalTasks) * 100).toFixed(0)}%`, c: C.green, icon: '✅' },
                ].map(s => (
                    <div key={s.l} className="stat-card" style={{ padding: '10px 12px' }}>
                        <div style={{ fontSize: 10, marginBottom: 4 }}>{s.icon}</div>
                        <div style={{ fontSize: 20, fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, color: s.c }}>{s.v}</div>
                        <div style={{ fontSize: 8, color: C.text, letterSpacing: '1px' }}>{s.l}</div>
                    </div>
                ))}
            </div>

            {/* Body */}
            <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 }}>
                {tab === 'workers' && (
                    <>
                        {/* Filters + Table */}
                        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                            {/* Filters */}
                            <div style={{ flexShrink: 0, display: 'flex', gap: 8, padding: '10px 20px', borderBottom: `1px solid ${C.borderSoft}` }}>
                                <select value={filterRole} onChange={e => setFilterRole(e.target.value)} style={{
                                    padding: '5px 10px', fontSize: 9, background: C.surface, border: `1px solid ${C.border}`,
                                    color: C.textBright, borderRadius: 3, fontFamily: "'Share Tech Mono',monospace",
                                }}>
                                    <option value="all">ALL ROLES</option>
                                    {ROLES.map(r => <option key={r} value={r}>{r.toUpperCase()}</option>)}
                                </select>
                                <select value={filterArea} onChange={e => setFilterArea(e.target.value)} style={{
                                    padding: '5px 10px', fontSize: 9, background: C.surface, border: `1px solid ${C.border}`,
                                    color: C.textBright, borderRadius: 3, fontFamily: "'Share Tech Mono',monospace",
                                }}>
                                    <option value="all">ALL AREAS</option>
                                    {AREAS.map(a => <option key={a} value={a}>{a.toUpperCase()}</option>)}
                                </select>
                                <div style={{ flex: 1 }} />
                                <span style={{ fontSize: 9, color: C.text, alignSelf: 'center' }}>{filtered.length} workers</span>
                            </div>
                            {/* Table */}
                            <div style={{ flex: 1, overflowY: 'auto', padding: '0 20px' }}>
                                <table className="data-table">
                                    <thead><tr>
                                        <th></th><th>NAME</th><th>ROLE</th><th>AREA</th><th>TASKS</th><th>PERF</th><th>STATUS</th>
                                    </tr></thead>
                                    <tbody>
                                        {filtered.map(w => (
                                            <tr key={w.id} onClick={() => setSelectedWorker(w)} style={{
                                                cursor: 'pointer',
                                                background: selectedWorker?.id === w.id ? 'rgba(0,200,255,.05)' : undefined,
                                            }}>
                                                <td style={{ fontSize: 18, width: 30 }}>{w.avatar}</td>
                                                <td style={{ color: C.white, fontWeight: 'bold' }}>{w.name}</td>
                                                <td><span className="tag" style={{ borderColor: C.purple + '66', color: C.purple }}>{w.role}</span></td>
                                                <td>{w.area}</td>
                                                <td>{w.tasksCompleted}/{w.tasksAssigned}</td>
                                                <td>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                        <div className="progress-bar" style={{ width: 50 }}>
                                                            <div className="progress-fill" style={{
                                                                width: `${w.performance}%`,
                                                                background: w.performance > 70 ? C.green : w.performance > 40 ? C.gold : C.red,
                                                            }} />
                                                        </div>
                                                        <span style={{ fontSize: 9, color: w.performance > 70 ? C.green : w.performance > 40 ? C.gold : C.red }}>
                                                            {w.performance}%
                                                        </span>
                                                    </div>
                                                </td>
                                                <td>
                                                    <span style={{
                                                        fontSize: 8, padding: '2px 8px', borderRadius: 10,
                                                        background: w.status === 'active' ? 'rgba(0,232,130,.12)' : 'rgba(255,51,85,.12)',
                                                        color: w.status === 'active' ? C.green : C.red,
                                                    }}>● {w.status.toUpperCase()}</span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        {/* Worker Detail */}
                        <div style={{
                            width: 280, flexShrink: 0, background: C.panel, borderLeft: `1px solid ${C.border}`,
                            overflowY: 'auto',
                        }}>
                            {selectedWorker ? (
                                <div>
                                    <div style={{
                                        padding: '16px 14px', textAlign: 'center',
                                        background: 'rgba(0,200,255,.04)', borderBottom: `1px solid ${C.border}`,
                                    }}>
                                        <div style={{ fontSize: 40, marginBottom: 6 }}>{selectedWorker.avatar}</div>
                                        <div style={{ fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, fontSize: 16, color: C.white }}>
                                            {selectedWorker.name}
                                        </div>
                                        <div className="tag" style={{ marginTop: 4, borderColor: C.purple + '66', color: C.purple }}>
                                            {selectedWorker.role}
                                        </div>
                                    </div>
                                    <div style={{ padding: 14 }}>
                                        {[
                                            { l: 'Area', v: selectedWorker.area },
                                            { l: 'Phone', v: selectedWorker.phone },
                                            { l: 'Last Active', v: selectedWorker.lastActive.toLocaleDateString() },
                                            { l: 'Tasks', v: `${selectedWorker.tasksCompleted}/${selectedWorker.tasksAssigned}` },
                                        ].map(m => (
                                            <div key={m.l} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: `1px solid ${C.borderSoft}` }}>
                                                <span style={{ fontSize: 9, color: C.text }}>{m.l}</span>
                                                <span style={{ fontSize: 10, color: C.textBright }}>{m.v}</span>
                                            </div>
                                        ))}
                                        <div style={{ marginTop: 14 }}>
                                            <div style={{ fontSize: 9, color: C.text, letterSpacing: '1.5px', marginBottom: 8 }}>7-DAY ACTIVITY</div>
                                            <div style={{ display: 'flex', gap: 4 }}>
                                                {selectedWorker.dailyLog.map(d => (
                                                    <div key={d.day} style={{ flex: 1, textAlign: 'center' }}>
                                                        <div style={{
                                                            height: 60, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end',
                                                            marginBottom: 4,
                                                        }}>
                                                            <div style={{
                                                                height: `${(d.tasks / 8) * 100}%`, minHeight: 4,
                                                                background: `linear-gradient(180deg, ${C.primary}, ${C.primaryDim})`,
                                                                borderRadius: '2px 2px 0 0',
                                                            }} />
                                                        </div>
                                                        <div style={{ fontSize: 7, color: C.text }}>{d.day}</div>
                                                        <div style={{ fontSize: 8, color: C.primary }}>{d.tasks}</div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                        <div style={{ marginTop: 14, display: 'flex', gap: 6 }}>
                                            <button style={{
                                                flex: 1, padding: '8px', fontSize: 9,
                                                background: C.primaryGlow, border: `1px solid ${C.primary}`,
                                                color: C.primary, borderRadius: 3, fontFamily: "'Share Tech Mono',monospace",
                                            }}>📱 CONTACT</button>
                                            <button style={{
                                                flex: 1, padding: '8px', fontSize: 9,
                                                background: 'transparent', border: `1px solid ${C.border}`,
                                                color: C.text, borderRadius: 3, fontFamily: "'Share Tech Mono',monospace",
                                            }}>📋 ASSIGN</button>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div style={{ padding: 30, textAlign: 'center' }}>
                                    <div style={{ fontSize: 40, opacity: .3, marginBottom: 12 }}>👷</div>
                                    <div style={{ fontSize: 10, color: C.text, letterSpacing: '1px', lineHeight: 1.8 }}>
                                        SELECT A WORKER<br />TO VIEW PROFILE AND<br />ACTIVITY DETAILS
                                    </div>
                                </div>
                            )}
                        </div>
                    </>
                )}

                {tab === 'campaigns' && (
                    <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
                        <div style={{ fontSize: 9, color: C.text, letterSpacing: '2px', marginBottom: 16 }}>
                            CAMPAIGN TRACKER — {CAMPAIGNS.length} CAMPAIGNS
                        </div>
                        <div style={{ display: 'grid', gap: 12 }}>
                            {CAMPAIGNS.map(c => (
                                <div key={c.name} className="card" style={{ padding: 16 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                                        <div style={{ fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, fontSize: 14, color: C.white }}>
                                            {c.name}
                                        </div>
                                        <span style={{
                                            fontSize: 8, padding: '3px 10px', borderRadius: 10,
                                            background: c.status === 'active' ? 'rgba(0,232,130,.12)' : c.status === 'completed' ? 'rgba(0,200,255,.12)' : 'rgba(255,204,0,.12)',
                                            color: c.status === 'active' ? C.green : c.status === 'completed' ? C.primary : C.gold,
                                            letterSpacing: '1px',
                                        }}>{c.status.toUpperCase()}</span>
                                    </div>
                                    <div className="progress-bar" style={{ height: 6, marginBottom: 10 }}>
                                        <div className="progress-fill" style={{
                                            width: `${c.progress}%`,
                                            background: c.status === 'completed' ? C.primary : c.progress > 60 ? C.green : C.gold,
                                        }} />
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span style={{ fontSize: 9, color: C.text }}>👥 {c.workers} workers</span>
                                        <span style={{ fontSize: 9, color: C.text }}>📊 {c.progress}%</span>
                                        <span style={{ fontSize: 9, color: C.text }}>📅 {c.deadline}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {tab === 'leaderboard' && (
                    <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
                        <div style={{ fontSize: 9, color: C.text, letterSpacing: '2px', marginBottom: 16 }}>
                            🏆 PERFORMANCE LEADERBOARD
                        </div>
                        <div style={{ display: 'grid', gap: 6 }}>
                            {[...WORKERS].sort((a, b) => b.performance - a.performance).map((w, i) => (
                                <div key={w.id} className="card" style={{
                                    padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12,
                                    borderColor: i < 3 ? [C.gold, '#C0C0C0', '#CD7F32'][i] + '44' : undefined,
                                    animation: `slideUp ${0.2 + i * 0.05}s ease forwards`,
                                }}>
                                    <div style={{
                                        width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        fontSize: i < 3 ? 16 : 11,
                                        color: i < 3 ? [C.gold, '#C0C0C0', '#CD7F32'][i] : C.text,
                                        fontFamily: "'Rajdhani',sans-serif", fontWeight: 700,
                                    }}>{i < 3 ? ['🥇', '🥈', '🥉'][i] : `#${i + 1}`}</div>
                                    <div style={{ fontSize: 18 }}>{w.avatar}</div>
                                    <div style={{ flex: 1 }}>
                                        <div style={{ fontSize: 11, color: C.white }}>{w.name}</div>
                                        <div style={{ fontSize: 8, color: C.text }}>{w.role} · {w.area}</div>
                                    </div>
                                    <div style={{ textAlign: 'right' }}>
                                        <div style={{
                                            fontSize: 16, fontFamily: "'Rajdhani',sans-serif", fontWeight: 700,
                                            color: w.performance > 70 ? C.green : w.performance > 40 ? C.gold : C.red
                                        }}>
                                            {w.performance}%
                                        </div>
                                        <div style={{ fontSize: 8, color: C.text }}>{w.tasksCompleted}/{w.tasksAssigned} tasks</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
