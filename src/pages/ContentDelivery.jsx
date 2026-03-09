import { useState } from 'react';
import { C, hexRgb } from '../theme';

/* ════════════════════════════════════════════════════════════════
   HYPER-LOCAL CONTENT DELIVERY — Precision Messaging Engine
   ════════════════════════════════════════════════════════════════ */

const VOTER_SEGMENTS = [
    { id: 'youth', label: 'Youth (18-35)', color: '#B06BFF', icon: '🎓', size: 34200 },
    { id: 'business', label: 'Businessmen', color: '#FFCC00', icon: '💼', size: 18400 },
    { id: 'farmers', label: 'Farmers', color: '#00E882', icon: '🌾', size: 22100 },
    { id: 'women', label: 'Women', color: '#FF7040', icon: '👩', size: 26800 },
    { id: 'senior', label: 'Senior Citizens', color: '#00C8FF', icon: '🏛️', size: 15500 },
];

const CHANNELS = [
    { id: 'whatsapp', label: 'WhatsApp', icon: '💬', color: '#25D366' },
    { id: 'sms', label: 'SMS', icon: '📱', color: '#00C8FF' },
    { id: 'push', label: 'Push', icon: '🔔', color: '#FF7040' },
    { id: 'email', label: 'Email', icon: '📧', color: '#B06BFF' },
    { id: 'ivr', label: 'IVR Call', icon: '📞', color: '#FFCC00' },
];

const CONTENT_TEMPLATES = [
    {
        segment: 'youth', title: 'Startup India Schemes',
        preview: '🚀 Attention Young Entrepreneurs! PM Startup India offers ₹10L seed funding, tax benefits for 3 years, and free mentorship. Apply now at startupindia.gov.in. Your dream startup is one click away!',
        channels: ['whatsapp', 'push', 'email'],
        sent: 12400, delivered: 11800, read: 7200, ctr: 38,
    },
    {
        segment: 'farmers', title: 'PM-KISAN Credit Update',
        preview: '🌾 किसान भाइयों! PM-KISAN की अगली किश्त ₹2,000 आपके खाते में 15 मार्च तक आ जाएगी। अपना eKYC पूरा करें: pmkisan.gov.in। हेल्पलाइन: 155261',
        channels: ['sms', 'ivr', 'whatsapp'],
        sent: 18200, delivered: 17800, read: 12400, ctr: 45,
    },
    {
        segment: 'women', title: 'Ujjwala Free Refill Offer',
        preview: '👩 बहनों! उज्ज्वला योजना के तहत अब पहला रिफिल FREE! अपना आवेदन नजदीकी गैस एजेंसी में दें। दस्तावेज: आधार + राशन कार्ड। हेल्पलाइन: 1800-233-3555',
        channels: ['sms', 'whatsapp', 'ivr'],
        sent: 15600, delivered: 15200, read: 10800, ctr: 42,
    },
    {
        segment: 'business', title: 'MSME Tax Benefits 2026',
        preview: '💼 Dear Business Owner, GST simplified for MSMEs: Quarterly filing, reduced rate at 1%, and instant refund within 48hrs. Register under Udyam: udyamregistration.gov.in. Deadline: March 31.',
        channels: ['email', 'whatsapp', 'sms'],
        sent: 8400, delivered: 8200, read: 5600, ctr: 52,
    },
    {
        segment: 'senior', title: 'PM Pension Yojana Update',
        preview: '🏛️ वरिष्ठ नागरिकों! PM वय वंदना योजना: ₹3,000 मासिक पेंशन। नजदीकी CSC केंद्र पर पंजीकरण करें। दस्तावेज: आधार + बैंक पासबुक। आयु: 60+ वर्ष।',
        channels: ['ivr', 'sms', 'whatsapp'],
        sent: 10200, delivered: 9800, read: 7600, ctr: 35,
    },
    {
        segment: 'youth', title: 'Skill India Digital Course',
        preview: '📚 Free Digital Skills! Learn AI, Data Science, Cloud Computing through Skill India Digital. 50+ courses, industry certificates, job placement support. Enroll: skillindia.gov.in 🎯',
        channels: ['push', 'whatsapp', 'email'],
        sent: 14800, delivered: 14200, read: 9800, ctr: 41,
    },
    {
        segment: 'farmers', title: 'Crop Insurance Deadline',
        preview: '⚠️ PM Fasal Bima Yojana: रबी सीजन का अंतिम तारीख 20 मार्च! ₹2/- प्रति एकड़ प्रीमियम पर पूरी फसल बीमा। अपनी बैंक शाखा या CSC पर करें आवेदन।',
        channels: ['sms', 'ivr'],
        sent: 16400, delivered: 16000, read: 11200, ctr: 48,
    },
    {
        segment: 'women', title: 'Lakhpati Didi SHG Program',
        preview: '👩‍👩‍👧 लखपति दीदी कार्यक्रम! SHG सदस्यों को ₹1 लाख+ वार्षिक आय का लक्ष्य। प्रशिक्षण, बाजार लिंकेज, और माइक्रो-क्रेडिट। अपने ब्लॉक कार्यालय में संपर्क करें।',
        channels: ['whatsapp', 'sms'],
        sent: 11200, delivered: 10800, read: 7400, ctr: 39,
    },
];

const SCHEDULED_CAMPAIGNS = [
    { title: 'Youth Tech Rally Invite', date: '2026-03-12', time: '09:00', segment: 'youth', channel: 'push', status: 'scheduled' },
    { title: 'Farmer Subsidy Reminder', date: '2026-03-15', time: '06:00', segment: 'farmers', channel: 'sms', status: 'scheduled' },
    { title: 'Women Safety Helpline', date: '2026-03-10', time: '10:00', segment: 'women', channel: 'whatsapp', status: 'sent' },
    { title: 'Senior Health Camp', date: '2026-03-18', time: '08:00', segment: 'senior', channel: 'ivr', status: 'scheduled' },
    { title: 'MSME Webinar Invite', date: '2026-03-20', time: '14:00', segment: 'business', channel: 'email', status: 'draft' },
];

export default function ContentDelivery() {
    const [selectedTemplate, setSelectedTemplate] = useState(null);
    const [filterSegment, setFilterSegment] = useState('all');
    const [tab, setTab] = useState('campaigns');

    const filtered = filterSegment === 'all'
        ? CONTENT_TEMPLATES
        : CONTENT_TEMPLATES.filter(t => t.segment === filterSegment);

    const totalSent = CONTENT_TEMPLATES.reduce((s, t) => s + t.sent, 0);
    const totalDelivered = CONTENT_TEMPLATES.reduce((s, t) => s + t.delivered, 0);
    const totalRead = CONTENT_TEMPLATES.reduce((s, t) => s + t.read, 0);
    const avgCTR = (CONTENT_TEMPLATES.reduce((s, t) => s + t.ctr, 0) / CONTENT_TEMPLATES.length).toFixed(0);

    return (
        <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Header */}
            <div style={{ flexShrink: 0, padding: '10px 20px', background: 'linear-gradient(180deg,#021020,#010C18)', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                    <div style={{ fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, fontSize: 16, color: C.primary, letterSpacing: '2px' }}>
                        📡 HYPER-LOCAL CONTENT DELIVERY
                    </div>
                    <div style={{ fontSize: 9, color: C.text, letterSpacing: '2px' }}>
                        PRECISION MESSAGING · SEGMENT-TARGETED · MULTI-CHANNEL
                    </div>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                    {['campaigns', 'scheduler', 'analytics'].map(t => (
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
                    { l: 'MESSAGES SENT', v: totalSent.toLocaleString(), c: C.primary, icon: '📤' },
                    { l: 'DELIVERED', v: totalDelivered.toLocaleString(), c: C.green, icon: '✉️' },
                    { l: 'READ', v: totalRead.toLocaleString(), c: C.purple, icon: '👁️' },
                    { l: 'AVG CTR', v: `${avgCTR}%`, c: C.gold, icon: '🎯' },
                    { l: 'ACTIVE SEGMENTS', v: VOTER_SEGMENTS.length, c: C.primary, icon: '👥' },
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
                {tab === 'campaigns' && (
                    <>
                        {/* Segment Filter sidebar */}
                        <div style={{ width: 200, flexShrink: 0, background: C.panel, borderRight: `1px solid ${C.border}`, overflowY: 'auto' }}>
                            <div className="section-title">TARGET SEGMENTS</div>
                            <div style={{ padding: 10 }}>
                                <button onClick={() => setFilterSegment('all')} style={{
                                    width: '100%', padding: '8px 10px', fontSize: 9, textAlign: 'left',
                                    background: filterSegment === 'all' ? C.primaryGlow : 'transparent',
                                    border: `1px solid ${filterSegment === 'all' ? C.primary : C.borderSoft}`,
                                    color: filterSegment === 'all' ? C.primary : C.text,
                                    borderRadius: 3, fontFamily: "'Share Tech Mono',monospace", marginBottom: 4,
                                }}>
                                    ALL SEGMENTS
                                </button>
                                {VOTER_SEGMENTS.map(seg => (
                                    <button key={seg.id} onClick={() => setFilterSegment(seg.id)} style={{
                                        width: '100%', padding: '8px 10px', fontSize: 9, textAlign: 'left',
                                        background: filterSegment === seg.id ? `rgba(${hexRgb(seg.color)},.12)` : 'transparent',
                                        border: `1px solid ${filterSegment === seg.id ? seg.color : C.borderSoft}`,
                                        color: filterSegment === seg.id ? seg.color : C.text,
                                        borderRadius: 3, fontFamily: "'Share Tech Mono',monospace", marginBottom: 4,
                                        display: 'flex', justifyContent: 'space-between',
                                    }}>
                                        <span>{seg.icon} {seg.label}</span>
                                        <span style={{ fontSize: 8, color: C.text }}>{(seg.size / 1000).toFixed(1)}K</span>
                                    </button>
                                ))}
                            </div>

                            <div className="section-title">CHANNELS</div>
                            <div style={{ padding: 10 }}>
                                {CHANNELS.map(ch => (
                                    <div key={ch.id} style={{
                                        display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', marginBottom: 4,
                                        borderRadius: 3, border: `1px solid ${C.borderSoft}`,
                                    }}>
                                        <span style={{ fontSize: 14 }}>{ch.icon}</span>
                                        <span style={{ fontSize: 9, color: C.textBright }}>{ch.label}</span>
                                        <div style={{ flex: 1 }} />
                                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: ch.color, opacity: .7 }} />
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Campaign Cards */}
                        <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
                            <div style={{ fontSize: 9, color: C.text, letterSpacing: '2px', marginBottom: 12 }}>
                                {filtered.length} CONTENT CAMPAIGNS
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
                                {filtered.map((t, i) => {
                                    const seg = VOTER_SEGMENTS.find(s => s.id === t.segment);
                                    const isSelected = selectedTemplate === i;
                                    return (
                                        <div key={i} onClick={() => setSelectedTemplate(isSelected ? null : i)}
                                            className="card" style={{
                                                padding: 14, cursor: 'pointer',
                                                borderColor: isSelected ? seg?.color : undefined,
                                                animation: 'slideUp 0.4s ease forwards',
                                            }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                                                <div style={{ fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, fontSize: 13, color: C.white }}>
                                                    {t.title}
                                                </div>
                                                <span className="tag" style={{ borderColor: seg?.color + '55', color: seg?.color }}>
                                                    {seg?.icon} {seg?.label}
                                                </span>
                                            </div>
                                            <div style={{
                                                padding: 10, background: 'rgba(0,200,255,.03)', border: `1px solid ${C.borderSoft}`,
                                                borderRadius: 3, marginBottom: 10, fontSize: 10, color: C.textMid, lineHeight: 1.7,
                                            }}>{t.preview}</div>
                                            <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
                                                {t.channels.map(chId => {
                                                    const ch = CHANNELS.find(c => c.id === chId);
                                                    return ch && (
                                                        <span key={chId} style={{
                                                            fontSize: 14, filter: 'saturate(0.8)', opacity: .8,
                                                        }} title={ch.label}>{ch.icon}</span>
                                                    );
                                                })}
                                            </div>
                                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, fontSize: 9 }}>
                                                {[
                                                    { l: 'Sent', v: t.sent.toLocaleString(), c: C.primary },
                                                    { l: 'Delivered', v: t.delivered.toLocaleString(), c: C.green },
                                                    { l: 'Read', v: t.read.toLocaleString(), c: C.purple },
                                                    { l: 'CTR', v: `${t.ctr}%`, c: C.gold },
                                                ].map(m => (
                                                    <div key={m.l} style={{ textAlign: 'center' }}>
                                                        <div style={{ fontSize: 13, fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, color: m.c }}>{m.v}</div>
                                                        <div style={{ fontSize: 7, color: C.text, letterSpacing: '1px' }}>{m.l}</div>
                                                    </div>
                                                ))}
                                            </div>
                                            {/* Delivery progress */}
                                            <div style={{ display: 'flex', gap: 2, height: 4, borderRadius: 2, overflow: 'hidden', marginTop: 8 }}>
                                                <div style={{ width: `${(t.read / t.sent) * 100}%`, background: C.purple }} />
                                                <div style={{ width: `${((t.delivered - t.read) / t.sent) * 100}%`, background: C.green }} />
                                                <div style={{ width: `${((t.sent - t.delivered) / t.sent) * 100}%`, background: C.borderSoft }} />
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </>
                )}

                {tab === 'scheduler' && (
                    <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
                        <div style={{ fontSize: 9, color: C.text, letterSpacing: '2px', marginBottom: 16 }}>
                            📅 CAMPAIGN SCHEDULER
                        </div>
                        <div style={{ display: 'grid', gap: 10 }}>
                            {SCHEDULED_CAMPAIGNS.map((c, i) => {
                                const seg = VOTER_SEGMENTS.find(s => s.id === c.segment);
                                const ch = CHANNELS.find(ch => ch.id === c.channel);
                                return (
                                    <div key={i} className="card" style={{
                                        padding: 14, display: 'flex', alignItems: 'center', gap: 14,
                                        animation: `slideUp ${0.2 + i * 0.08}s ease forwards`,
                                    }}>
                                        <div style={{
                                            width: 50, textAlign: 'center', flexShrink: 0,
                                        }}>
                                            <div style={{ fontSize: 14, fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, color: C.white }}>
                                                {c.date.split('-')[2]}
                                            </div>
                                            <div style={{ fontSize: 8, color: C.text }}>MAR</div>
                                            <div style={{ fontSize: 8, color: C.primary }}>{c.time}</div>
                                        </div>
                                        <div style={{ flex: 1 }}>
                                            <div style={{ fontSize: 12, color: C.white, fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, marginBottom: 4 }}>
                                                {c.title}
                                            </div>
                                            <div style={{ display: 'flex', gap: 6 }}>
                                                <span className="tag" style={{ borderColor: seg?.color + '55', color: seg?.color }}>
                                                    {seg?.icon} {seg?.label}
                                                </span>
                                                <span className="tag">{ch?.icon} {ch?.label}</span>
                                            </div>
                                        </div>
                                        <span style={{
                                            fontSize: 8, padding: '3px 10px', borderRadius: 10,
                                            background: c.status === 'sent' ? 'rgba(0,232,130,.12)' : c.status === 'scheduled' ? 'rgba(0,200,255,.12)' : 'rgba(255,204,0,.12)',
                                            color: c.status === 'sent' ? C.green : c.status === 'scheduled' ? C.primary : C.gold,
                                            letterSpacing: '1px',
                                        }}>{c.status.toUpperCase()}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {tab === 'analytics' && (
                    <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
                        <div style={{ fontSize: 9, color: C.text, letterSpacing: '2px', marginBottom: 16 }}>
                            📊 DELIVERY ANALYTICS BY SEGMENT
                        </div>
                        <div style={{ display: 'grid', gap: 12 }}>
                            {VOTER_SEGMENTS.map(seg => {
                                const segTemplates = CONTENT_TEMPLATES.filter(t => t.segment === seg.id);
                                const sent = segTemplates.reduce((s, t) => s + t.sent, 0);
                                const delivered = segTemplates.reduce((s, t) => s + t.delivered, 0);
                                const read = segTemplates.reduce((s, t) => s + t.read, 0);
                                return (
                                    <div key={seg.id} className="card" style={{ padding: 16 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                                            <div style={{
                                                width: 40, height: 40, borderRadius: 8,
                                                background: `rgba(${hexRgb(seg.color)},.12)`,
                                                border: `1px solid ${seg.color}33`,
                                                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20,
                                            }}>{seg.icon}</div>
                                            <div style={{ flex: 1 }}>
                                                <div style={{ fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, fontSize: 14, color: C.white }}>
                                                    {seg.label}
                                                </div>
                                                <div style={{ fontSize: 8, color: C.text }}>{seg.size.toLocaleString()} voters in segment</div>
                                            </div>
                                            <div style={{ textAlign: 'right' }}>
                                                <div style={{ fontSize: 8, color: C.text }}>Campaigns</div>
                                                <div style={{ fontSize: 16, fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, color: seg.color }}>{segTemplates.length}</div>
                                            </div>
                                        </div>
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                                            {[
                                                { l: 'Sent', v: sent.toLocaleString(), c: C.primary },
                                                { l: 'Delivered', v: delivered.toLocaleString(), c: C.green },
                                                { l: 'Read', v: read.toLocaleString(), c: C.purple },
                                            ].map(m => (
                                                <div key={m.l} style={{ textAlign: 'center' }}>
                                                    <div style={{ fontSize: 16, fontFamily: "'Rajdhani',sans-serif", fontWeight: 700, color: m.c }}>{m.v}</div>
                                                    <div style={{ fontSize: 8, color: C.text, letterSpacing: '1px' }}>{m.l}</div>
                                                </div>
                                            ))}
                                        </div>
                                        <div style={{ display: 'flex', gap: 2, height: 5, borderRadius: 3, overflow: 'hidden', marginTop: 10 }}>
                                            <div style={{ width: sent ? `${(read / sent) * 100}%` : '0%', background: C.purple, transition: 'width .8s' }} />
                                            <div style={{ width: sent ? `${((delivered - read) / sent) * 100}%` : '0%', background: C.green, transition: 'width .8s' }} />
                                            <div style={{ width: sent ? `${((sent - delivered) / sent) * 100}%` : '0%', background: C.borderSoft, transition: 'width .8s' }} />
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'center', gap: 12, marginTop: 6 }}>
                                            <span style={{ fontSize: 7, color: C.purple, display: 'flex', alignItems: 'center', gap: 3 }}><div style={{ width: 6, height: 6, borderRadius: 1, background: C.purple }} /> Read</span>
                                            <span style={{ fontSize: 7, color: C.green, display: 'flex', alignItems: 'center', gap: 3 }}><div style={{ width: 6, height: 6, borderRadius: 1, background: C.green }} /> Delivered</span>
                                            <span style={{ fontSize: 7, color: C.text, display: 'flex', alignItems: 'center', gap: 3 }}><div style={{ width: 6, height: 6, borderRadius: 1, background: C.borderSoft }} /> Undelivered</span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
