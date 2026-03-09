import { useState, useEffect, useRef } from 'react';
import { C, hexRgb } from '../theme';

/* ════════════════════════════════════════════════════════════════
   SENTIMENT ANALYSIS ENGINE — Multi-language AI Tracking
   ════════════════════════════════════════════════════════════════ */

const LANGUAGES = ['Hindi', 'English', 'Tamil', 'Bengali', 'Marathi'];
const SENTIMENTS = { positive: '#00E882', negative: '#FF3355', neutral: '#FFCC00' };
const ISSUES = [
    { topic: 'Unemployment', score: 87, trend: 'rising', sentiment: 'negative' },
    { topic: 'Infrastructure', score: 72, trend: 'stable', sentiment: 'positive' },
    { topic: 'Education', score: 68, trend: 'rising', sentiment: 'positive' },
    { topic: 'Water Supply', score: 65, trend: 'rising', sentiment: 'negative' },
    { topic: 'Healthcare', score: 61, trend: 'falling', sentiment: 'neutral' },
    { topic: 'Road Safety', score: 58, trend: 'stable', sentiment: 'negative' },
    { topic: 'Digital Services', score: 54, trend: 'rising', sentiment: 'positive' },
    { topic: 'Corruption', score: 52, trend: 'falling', sentiment: 'negative' },
    { topic: 'Green Energy', score: 48, trend: 'rising', sentiment: 'positive' },
    { topic: 'Public Transport', score: 45, trend: 'stable', sentiment: 'neutral' },
];

const WARDS = [
    'Karol Bagh', 'Rajouri Garden', 'Patel Nagar', 'Tilak Nagar', 'Janakpuri',
    'Dwarka', 'Rohini', 'Pitampura', 'Shalimar Bagh', 'Model Town',
    'Laxmi Nagar', 'Preet Vihar', 'Mayur Vihar', 'Shahdara', 'Geeta Colony',
    'Saket', 'Mehrauli', 'Vasant Kunj', 'Hauz Khas', 'Malviya Nagar',
];

const genHeatData = () => WARDS.map(w => ({
    ward: w,
    positive: 20 + Math.floor(Math.random() * 50),
    negative: 10 + Math.floor(Math.random() * 40),
    neutral: 15 + Math.floor(Math.random() * 30),
    overall: (Math.random() * 2 - 1).toFixed(2),
}));

const genFeed = () => {
    const templates = [
        { text: 'सरकार ने नई योजना शुरू की - बहुत अच्छा कदम!', lang: 'Hindi', sentiment: 'positive', source: 'Twitter/X' },
        { text: 'Roads in my area are terrible, no improvement since 2 years', lang: 'English', sentiment: 'negative', source: 'Facebook' },
        { text: 'புதிய பேருந்து சேவை மிகவும் நல்லது', lang: 'Tamil', sentiment: 'positive', source: 'Twitter/X' },
        { text: 'পানীয় জলের সমস্যা এখনও সমাধান হয়নি', lang: 'Bengali', sentiment: 'negative', source: 'WhatsApp' },
        { text: 'नवीन रुग्णालय उघडण्यात आले - चांगली बातमी', lang: 'Marathi', sentiment: 'positive', source: 'News' },
        { text: 'बिजली कटौती से परेशान हैं लोग, कोई सुनवाई नहीं', lang: 'Hindi', sentiment: 'negative', source: 'Ground' },
        { text: 'Smart city project is progressing well, visible changes!', lang: 'English', sentiment: 'positive', source: 'Survey' },
        { text: 'পার্কের অবস্থা খুব খারাপ, পরিষ্কার করা দরকার', lang: 'Bengali', sentiment: 'negative', source: 'Facebook' },
        { text: 'PM scheme helped my family get free healthcare', lang: 'English', sentiment: 'positive', source: 'Survey' },
        { text: 'मेट्रो विस्तार बहुत जरूरी है, ट्रैफिक बर्दाश्त से बाहर', lang: 'Hindi', sentiment: 'neutral', source: 'Twitter/X' },
        { text: 'New school building inaugurated in our ward - great!', lang: 'English', sentiment: 'positive', source: 'News' },
        { text: 'கழிவுநீர் பிரச்சனை தீர்க்கப்படவில்லை', lang: 'Tamil', sentiment: 'negative', source: 'Ground' },
    ];
    return templates.sort(() => Math.random() - 0.5).map((t, i) => ({ ...t, id: i, time: new Date(Date.now() - Math.random() * 3600000) }));
};

const TREND_DATA = Array.from({ length: 24 }, (_, i) => ({
    hour: `${i}:00`,
    positive: 30 + Math.floor(Math.random() * 40),
    negative: 15 + Math.floor(Math.random() * 30),
    neutral: 10 + Math.floor(Math.random() * 20),
}));

export default function SentimentAnalysis() {
    const [feeds, setFeeds] = useState(genFeed());
    const [heatData] = useState(genHeatData());
    const [view, setView] = useState('constituency');
    const [selectedWard, setSelectedWard] = useState(null);
    const trendRef = useRef(null);
    const gaugeRef = useRef(null);

    // Overall sentiment
    const totalP = feeds.filter(f => f.sentiment === 'positive').length;
    const totalN = feeds.filter(f => f.sentiment === 'negative').length;
    const totalNt = feeds.filter(f => f.sentiment === 'neutral').length;
    const total = feeds.length;
    const overallScore = ((totalP - totalN) / total * 100).toFixed(0);

    // Draw gauge
    useEffect(() => {
        const canvas = gaugeRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width = 180;
        const h = canvas.height = 100;
        ctx.clearRect(0, 0, w, h);
        const cx = w / 2, cy = h - 10;
        const startAngle = Math.PI;
        const endAngle = 2 * Math.PI;
        // Background arc
        ctx.beginPath();
        ctx.arc(cx, cy, 65, startAngle, endAngle);
        ctx.strokeStyle = C.borderSoft;
        ctx.lineWidth = 16;
        ctx.lineCap = 'butt';
        ctx.stroke();
        // Colored segments
        const segments = [
            { pct: totalN / total, color: SENTIMENTS.negative },
            { pct: totalNt / total, color: SENTIMENTS.neutral },
            { pct: totalP / total, color: SENTIMENTS.positive },
        ];
        let currentAngle = startAngle;
        segments.forEach(seg => {
            const sweep = seg.pct * Math.PI;
            ctx.beginPath();
            ctx.arc(cx, cy, 65, currentAngle, currentAngle + sweep);
            ctx.strokeStyle = seg.color;
            ctx.lineWidth = 16;
            ctx.stroke();
            currentAngle += sweep;
        });
        // Needle
        const normalized = (parseInt(overallScore) + 100) / 200;
        const needleAngle = startAngle + normalized * Math.PI;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(needleAngle) * 50, cy + Math.sin(needleAngle) * 50);
        ctx.strokeStyle = C.white;
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(cx, cy, 5, 0, Math.PI * 2);
        ctx.fillStyle = C.white;
        ctx.fill();
    }, [totalP, totalN, totalNt, total, overallScore]);

    // Draw trend chart
    useEffect(() => {
        const canvas = trendRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width = canvas.parentElement.clientWidth || 600;
        const h = canvas.height = 160;
        ctx.clearRect(0, 0, w, h);
        const padL = 30, padR = 10, padT = 10, padB = 25;
        const chartW = w - padL - padR, chartH = h - padT - padB;
        const maxVal = Math.max(...TREND_DATA.map(d => Math.max(d.positive, d.negative, d.neutral)));
        // Grid
        ctx.strokeStyle = '#082A42';
        ctx.lineWidth = 0.5;
        for (let i = 0; i <= 4; i++) {
            const y = padT + (chartH / 4) * i;
            ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(w - padR, y); ctx.stroke();
        }
        // Lines
        const drawLine = (key, color) => {
            ctx.beginPath();
            ctx.strokeStyle = color;
            ctx.lineWidth = 1.5;
            TREND_DATA.forEach((d, i) => {
                const x = padL + (i / (TREND_DATA.length - 1)) * chartW;
                const y = padT + chartH - (d[key] / maxVal) * chartH;
                i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            });
            ctx.stroke();
            // Gradient fill
            ctx.globalAlpha = 0.08;
            ctx.lineTo(padL + chartW, padT + chartH);
            ctx.lineTo(padL, padT + chartH);
            ctx.fillStyle = color;
            ctx.fill();
            ctx.globalAlpha = 1;
        };
        drawLine('positive', SENTIMENTS.positive);
        drawLine('negative', SENTIMENTS.negative);
        drawLine('neutral', SENTIMENTS.neutral);
        // X labels
        ctx.fillStyle = C.text;
        ctx.font = "8px 'Share Tech Mono', monospace";
        ctx.textAlign = 'center';
        [0, 6, 12, 18, 23].forEach(i => {
            const x = padL + (i / (TREND_DATA.length - 1)) * chartW;
            ctx.fillText(TREND_DATA[i].hour, x, h - 5);
        });
    }, []);

    // Simulate live feed
    useEffect(() => {
        const id = setInterval(() => {
            const templates = genFeed();
            const newItem = templates[Math.floor(Math.random() * templates.length)];
            setFeeds(prev => [{ ...newItem, id: Date.now(), time: new Date(), fresh: true }, ...prev.slice(0, 20)]);
        }, 4000);
        return () => clearInterval(id);
    }, []);

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
                        📊 AI SENTIMENT ANALYSIS ENGINE
                    </div>
                    <div style={{ fontSize: 9, color: C.text, letterSpacing: '2px' }}>
                        MULTI-LANGUAGE · REAL-TIME · BOOTH + CONSTITUENCY DASHBOARDS
                    </div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                    {['constituency', 'booth'].map(v => (
                        <button key={v} onClick={() => setView(v)} style={{
                            padding: '5px 14px', fontSize: 9, letterSpacing: '1.5px',
                            background: view === v ? C.primaryGlow : 'transparent',
                            border: `1px solid ${view === v ? C.primary : C.border}`,
                            color: view === v ? C.primary : C.text,
                            borderRadius: 3, fontFamily: "'Share Tech Mono',monospace",
                            textTransform: 'uppercase',
                        }}>{v}</button>
                    ))}
                </div>
            </div>

            {/* Body */}
            <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 }}>
                {/* Left: Live Feed */}
                <div style={{
                    width: 290, flexShrink: 0, background: C.panel, borderRight: `1px solid ${C.border}`,
                    display: 'flex', flexDirection: 'column', overflow: 'hidden',
                }}>
                    <div style={{
                        padding: '7px 12px', borderBottom: `1px solid ${C.border}`,
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    }}>
                        <span style={{ fontSize: 9, letterSpacing: '2px', color: C.text }}>LIVE SENTIMENT FEED</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                            <div style={{ width: 6, height: 6, borderRadius: '50%', background: C.green, animation: 'pulse 1.5s infinite' }} />
                            <span style={{ fontSize: 8, color: C.green, letterSpacing: '1px' }}>ANALYZING</span>
                        </div>
                    </div>
                    <div style={{ overflowY: 'auto', flex: 1, padding: 8 }}>
                        {feeds.map((f, i) => (
                            <div key={f.id + '-' + i} className={f.fresh ? 'feed-new' : ''} style={{
                                marginBottom: 5, padding: '8px 10px',
                                background: `rgba(${hexRgb(SENTIMENTS[f.sentiment])}, 0.04)`,
                                border: `1px solid ${SENTIMENTS[f.sentiment]}22`,
                                borderLeft: `3px solid ${SENTIMENTS[f.sentiment]}`,
                                borderRadius: 3,
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                                        <span style={{ fontSize: 8, color: SENTIMENTS[f.sentiment], fontWeight: 'bold', letterSpacing: '1px' }}>
                                            {f.sentiment.toUpperCase()}
                                        </span>
                                        <span className="tag">{f.lang}</span>
                                    </div>
                                    <span style={{ fontSize: 8, color: C.text }}>{f.source}</span>
                                </div>
                                <div style={{ fontSize: 10, color: C.textBright, lineHeight: 1.6, marginBottom: 4 }}>{f.text}</div>
                                <div style={{ fontSize: 8, color: C.text }}>{f.time?.toLocaleTimeString?.() || '—'}</div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Center: Heatmap + Trends */}
                <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
                    {/* Top stats row */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 180px', gap: 12, marginBottom: 16 }}>
                        {[
                            { l: 'POSITIVE', v: `${((totalP / total) * 100).toFixed(0)}%`, count: totalP, c: SENTIMENTS.positive },
                            { l: 'NEGATIVE', v: `${((totalN / total) * 100).toFixed(0)}%`, count: totalN, c: SENTIMENTS.negative },
                            { l: 'NEUTRAL', v: `${((totalNt / total) * 100).toFixed(0)}%`, count: totalNt, c: SENTIMENTS.neutral },
                        ].map(s => (
                            <div key={s.l} className="stat-card">
                                <div style={{ fontSize: 24, fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, color: s.c }}>{s.v}</div>
                                <div style={{ fontSize: 9, color: C.text, letterSpacing: '1.5px' }}>{s.l}</div>
                                <div style={{ fontSize: 8, color: C.textMid, marginTop: 2 }}>{s.count} mentions</div>
                            </div>
                        ))}
                        <div className="stat-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                            <canvas ref={gaugeRef} style={{ width: 180, height: 100 }} />
                            <div style={{ fontSize: 18, fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, color: parseInt(overallScore) > 0 ? C.green : C.red, marginTop: -8 }}>
                                {overallScore > 0 ? '+' : ''}{overallScore}
                            </div>
                            <div style={{ fontSize: 8, color: C.text, letterSpacing: '1px' }}>OVERALL INDEX</div>
                        </div>
                    </div>

                    {/* Trend Chart */}
                    <div className="card" style={{ padding: 14, marginBottom: 16 }}>
                        <div style={{ fontSize: 9, color: C.text, letterSpacing: '2px', marginBottom: 10, display: 'flex', justifyContent: 'space-between' }}>
                            <span>24-HOUR SENTIMENT TREND</span>
                            <div style={{ display: 'flex', gap: 12 }}>
                                {Object.entries(SENTIMENTS).map(([k, c]) => (
                                    <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                        <div style={{ width: 10, height: 2, background: c }} />
                                        <span style={{ fontSize: 8, color: C.text, textTransform: 'capitalize' }}>{k}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <canvas ref={trendRef} style={{ width: '100%', height: 160 }} />
                    </div>

                    {/* Heatmap */}
                    <div className="card" style={{ padding: 14 }}>
                        <div style={{ fontSize: 9, color: C.text, letterSpacing: '2px', marginBottom: 12 }}>
                            WARD-WISE SENTIMENT HEATMAP — CLICK TO INSPECT
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6 }}>
                            {heatData.map(d => {
                                const sentiment = parseFloat(d.overall);
                                const bg = sentiment > 0.3 ? SENTIMENTS.positive
                                    : sentiment < -0.3 ? SENTIMENTS.negative
                                        : SENTIMENTS.neutral;
                                const intensity = Math.abs(sentiment);
                                const isSelected = selectedWard?.ward === d.ward;
                                return (
                                    <div key={d.ward} className="heat-cell"
                                        onClick={() => setSelectedWard(isSelected ? null : d)}
                                        style={{
                                            padding: '10px 8px', textAlign: 'center',
                                            background: `rgba(${hexRgb(bg)}, ${0.08 + intensity * 0.2})`,
                                            border: `1px solid ${isSelected ? bg : bg + '33'}`,
                                            cursor: 'pointer',
                                        }}>
                                        <div style={{ fontSize: 9, color: C.textBright, marginBottom: 4 }}>{d.ward}</div>
                                        <div style={{ fontSize: 14, fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, color: bg }}>
                                            {sentiment > 0 ? '+' : ''}{d.overall}
                                        </div>
                                        <div style={{ display: 'flex', gap: 2, marginTop: 6, justifyContent: 'center' }}>
                                            <span style={{ fontSize: 7, color: SENTIMENTS.positive }}>+{d.positive}</span>
                                            <span style={{ fontSize: 7, color: C.text }}>·</span>
                                            <span style={{ fontSize: 7, color: SENTIMENTS.negative }}>-{d.negative}</span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {/* Right: Issues + Alerts */}
                <div style={{
                    width: 260, flexShrink: 0, background: C.panel, borderLeft: `1px solid ${C.border}`,
                    display: 'flex', flexDirection: 'column', overflow: 'hidden',
                }}>
                    <div className="section-title">🔥 TRENDING ISSUES</div>
                    <div style={{ overflowY: 'auto', flex: 1, padding: 10 }}>
                        {ISSUES.map((issue, i) => (
                            <div key={issue.topic} className="card" style={{
                                padding: '10px 12px', marginBottom: 6,
                                animation: `slideUp ${0.3 + i * 0.08}s ease forwards`,
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                                    <span style={{ fontSize: 10, color: C.textBright, fontWeight: 'bold' }}>
                                        #{i + 1} {issue.topic}
                                    </span>
                                    <span style={{
                                        fontSize: 8, padding: '1px 6px', borderRadius: 2,
                                        color: SENTIMENTS[issue.sentiment],
                                        border: `1px solid ${SENTIMENTS[issue.sentiment]}44`,
                                    }}>{issue.sentiment.toUpperCase()}</span>
                                </div>
                                <div className="progress-bar" style={{ marginBottom: 4 }}>
                                    <div className="progress-fill" style={{
                                        width: `${issue.score}%`,
                                        background: SENTIMENTS[issue.sentiment],
                                    }} />
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span style={{ fontSize: 8, color: C.text }}>Score: {issue.score}</span>
                                    <span style={{
                                        fontSize: 8,
                                        color: issue.trend === 'rising' ? C.red : issue.trend === 'falling' ? C.green : C.gold,
                                    }}>
                                        {issue.trend === 'rising' ? '▲' : issue.trend === 'falling' ? '▼' : '●'} {issue.trend}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                    {/* Alerts */}
                    <div style={{ flexShrink: 0, borderTop: `1px solid ${C.border}` }}>
                        <div className="section-title">⚠️ SENTIMENT ALERTS</div>
                        <div style={{ padding: 10 }}>
                            {[
                                { text: 'Sharp negative spike in Karol Bagh ward — water supply complaints +340%', sev: 'HIGH' },
                                { text: 'Positive surge in Dwarka — new metro line appreciation trending', sev: 'LOW' },
                                { text: 'Unemployment sentiment crossing critical threshold in 8 wards', sev: 'CRIT' },
                            ].map((a, i) => (
                                <div key={i} style={{
                                    padding: '8px 10px', marginBottom: 4,
                                    borderLeft: `3px solid ${a.sev === 'CRIT' ? C.red : a.sev === 'HIGH' ? C.orange : C.green}`,
                                    background: `rgba(${hexRgb(a.sev === 'CRIT' ? C.red : a.sev === 'HIGH' ? C.orange : C.green)}, 0.05)`,
                                    borderRadius: '0 3px 3px 0',
                                }}>
                                    <span style={{ fontSize: 8, color: a.sev === 'CRIT' ? C.red : a.sev === 'HIGH' ? C.orange : C.green, fontWeight: 'bold', letterSpacing: '1px' }}>
                                        {a.sev}
                                    </span>
                                    <div style={{ fontSize: 9, color: C.textBright, lineHeight: 1.5, marginTop: 3 }}>{a.text}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
