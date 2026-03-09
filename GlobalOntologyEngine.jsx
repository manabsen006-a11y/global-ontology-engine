import { useState, useEffect, useRef, useCallback } from "react";
import * as d3 from "d3";

/* ════════════════════════════════════════════════════════════════
   GLOBAL ONTOLOGY ENGINE  —  Strategic Intelligence System v4.2
   AI-powered knowledge graph for geopolitical, economic, defense,
   technology, climate & societal analysis  |  India + World focus
   ════════════════════════════════════════════════════════════════ */

const C = {
  bg: '#010C18', panel: '#020F1E', surface: '#031525',
  border: '#0C3A58', borderSoft: '#082A42',
  primary: '#00C8FF', primaryDim: '#004A6B', primaryGlow: 'rgba(0,200,255,0.15)',
  saffron: '#FF7040', gold: '#FFCC00', green: '#00E882',
  purple: '#B06BFF', red: '#FF3355', orange: '#FF8C00',
  text: '#4A8BAA', textMid: '#7BBAD5', textBright: '#C0E4F5', white: '#E8F8FF',
};

const hexRgb = (h) => {
  const r = parseInt(h.slice(1, 3), 16);
  const g = parseInt(h.slice(3, 5), 16);
  const b = parseInt(h.slice(5, 7), 16);
  return `${r},${g},${b}`;
};

const DOMAINS = {
  geopolitics: { label: 'Geopolitics', color: '#00C8FF', icon: '🌐', short: 'GEO' },
  economics:   { label: 'Economics',   color: '#FFCC00', icon: '💹', short: 'ECO' },
  defense:     { label: 'Defense',     color: '#FF3355', icon: '🛡️', short: 'DEF' },
  technology:  { label: 'Technology',  color: '#B06BFF', icon: '⚡', short: 'TECH' },
  climate:     { label: 'Climate',     color: '#00E882', icon: '🌱', short: 'ENV' },
  society:     { label: 'Society',     color: '#FF7040', icon: '👥', short: 'SOC' },
};

const SEV = { CRIT: '#FF3355', HIGH: '#FF8C00', MED: '#FFCC00', LOW: '#00E882' };

// ── Entity Graph Data ────────────────────────────────────────────
const NODES = [
  { id:'india',        label:'India',         domain:'geopolitics', r:26,
    intel:'World\'s largest democracy (1.44B). Fastest-growing G20 economy at 7%+. Aspirant UNSC permanent seat. G20 host 2023. Indo-Pacific linchpin. Strategic autonomy doctrine balancing USA, Russia, China.',
    tags:['Nation','G20','QUAD','BRICS','SCO','Nuclear'], power:78, risk:'Medium' },
  { id:'china',        label:'China',         domain:'geopolitics', r:24,
    intel:'World #2 economy ($18T). Rare earth dominance (70%+ processing). PLA modernization at $225B/yr. Belt & Road across 140+ nations. Taiwan flashpoint intensifying. Demographic headwinds emerging.',
    tags:['Nation','P5','BRICS','SCO','Nuclear'], power:89, risk:'High' },
  { id:'usa',          label:'USA',           domain:'geopolitics', r:24,
    intel:'Global reserve currency. NATO anchor. CHIPS Act $52B for semiconductor reshoring. AI frontier with GPT-5, Claude 4. Deepening India partnership via iCET. Debt $34T—fiscal pressure rising.',
    tags:['Nation','P5','NATO','QUAD','G7','Nuclear'], power:95, risk:'Medium' },
  { id:'russia',       label:'Russia',        domain:'geopolitics', r:18,
    intel:'Ukraine war year 3+. Energy weaponization via Nord Stream leverage. Pivot East—China+India trade. Nuclear doctrine posture shifts. Wagner fallout destabilizing Africa ops.',
    tags:['Nation','P5','BRICS','SCO','Nuclear'], power:72, risk:'Critical' },
  { id:'eu',           label:'EU',            domain:'geopolitics', r:20,
    intel:'Strategic autonomy doctrine under von der Leyen. World-first AI Act (2024). Carbon Border Adjustment Mechanism. Ukraine + Moldova enlargement track. Defence spending under pressure.',
    tags:['Bloc','NATO','G7'], power:75, risk:'Medium' },
  { id:'pakistan',     label:'Pakistan',      domain:'geopolitics', r:13,
    intel:'IMF dependency ($7B bailout). CPEC stalled at $25B. Nuclear arsenal expansion (170+ warheads). Military-civil tension chronic. Kashmir proxy operations ongoing.',
    tags:['Nation','SCO','Nuclear'], power:42, risk:'High' },
  { id:'japan',        label:'Japan',         domain:'geopolitics', r:16,
    intel:'Defense budget doubling to 2% GDP ($80B). QUAD member. TSMC Kumamoto fab operational. Demographic crisis (-700K/yr). Leading semiconductor equipment maker.',
    tags:['Nation','G7','QUAD'], power:65, risk:'Medium' },
  { id:'australia',    label:'Australia',     domain:'geopolitics', r:14,
    intel:'AUKUS nuclear submarine deal ($368B). World\'s largest critical minerals exporter. Five Eyes intelligence anchor. Reduced China trade dependency post-sanctions.',
    tags:['Nation','QUAD','AUKUS'], power:55, risk:'Low' },
  { id:'quad',         label:'QUAD',          domain:'defense',     r:19,
    intel:'India-USA-Japan-Australia strategic dialogue. Evolved from maritime to tech+supply chain resilience. Annual summits. Indo-Pacific Maritime Domain Awareness sharing. Counter-BRI narrative.',
    tags:['Alliance'], power:85, risk:'Low' },
  { id:'brics',        label:'BRICS+',        domain:'economics',   r:19,
    intel:'Expanded 2024: 9 nations including Saudi Arabia, UAE, Ethiopia, Iran, Egypt. 37% global GDP (PPP). New Development Bank $32B lent. De-dollarization agenda gaining traction.',
    tags:['Bloc'], power:76, risk:'Medium' },
  { id:'sco',          label:'SCO',           domain:'geopolitics', r:15,
    intel:'Shanghai Cooperation Organisation—Eurasian security+economic bloc. India+Pakistan both members creating strategic tension. China-Russia at core. Counter-terrorism mandate.',
    tags:['Bloc'], power:68, risk:'Medium' },
  { id:'nato',         label:'NATO',          domain:'defense',     r:19,
    intel:'32 members post-Sweden (2024). Combined defense $1.2T+. Eastern flank: 300K+ rapid response. Cyber and space as operational domains. Sweden-Finland accession reshapes Arctic.',
    tags:['Alliance'], power:92, risk:'Low' },
  { id:'ai',           label:'AI / LLM',      domain:'technology',  r:22,
    intel:'AGI race: OpenAI GPT-5, Anthropic Claude 4, Google Gemini Ultra. Agentic AI in production deployment. Defense: autonomous targeting, ISR. India National AI Mission ₹10,372Cr. 300M jobs disruption risk.',
    tags:['Technology','Dual-use','Strategic'], power:92, risk:'High' },
  { id:'semiconductor',label:'Chips',         domain:'technology',  r:19,
    intel:'TSMC 2nm production 2025. CHIPS Act: 5 US fab projects. India fab mission $10B incentives. Netherlands ASML EUV export controls. Strategic chokepoint: TSMC produces 90% advanced chips.',
    tags:['Technology','Resource','Strategic'], power:88, risk:'High' },
  { id:'quantum',      label:'Quantum',       domain:'technology',  r:14,
    intel:'Q-Day estimate: cryptographic break in 2030s. India National Quantum Mission ₹6,003Cr. Google 1M qubit roadmap. Post-quantum migration: NIST PQC standards finalised 2024.',
    tags:['Technology','Defense','Emerging'], power:72, risk:'High' },
  { id:'space',        label:'Space',         domain:'technology',  r:16,
    intel:'Chandrayaan-3 south pole success 2023—India #4 lunar power. Gaganyaan crewed flight 2025. ISRO commercialization via IN-SPACe. Artemis vs Chinese lunar program resource race.',
    tags:['Technology','Prestige','Defense'], power:72, risk:'Low' },
  { id:'cyber',        label:'Cyber',         domain:'defense',     r:14,
    intel:'Nation-state APT proliferation: Volt Typhoon (China), APT29 (Russia). AI-powered malware at scale. Critical infrastructure attacks +300% since 2020. India CERT-In 24hr reporting mandate.',
    tags:['Defense','Technology','Threat'], power:75, risk:'Critical' },
  { id:'bri',          label:'Belt & Road',   domain:'economics',   r:16,
    intel:'$900B+ committed across 140 nations. Debt trap vs connectivity debate. CPEC ($62B) stalled. Sri Lanka Hambantota controversy. Counter: India\'s IMEC (India-Middle East-Europe) corridor.',
    tags:['Initiative','Economics','Geopolitics'], power:72, risk:'Medium' },
  { id:'oil',          label:'Energy',        domain:'economics',   r:16,
    intel:'Petrodollar challenged by BRICS. India buys Russian Urals at $15 discount—$40B savings. OPEC+ production cuts geopolitically driven. India 85% oil import dependent—strategic vulnerability.',
    tags:['Resource','Economics','Strategic'], power:82, risk:'High' },
  { id:'rare_earth',   label:'Rare Earth',    domain:'economics',   r:14,
    intel:'China controls 70%+ processing of 17 critical metals. Essential for EVs, defense systems, AI chips. India: 6% global reserves (largely untapped). India-Australia critical minerals pact 2023.',
    tags:['Resource','Strategic','Technology'], power:78, risk:'High' },
  { id:'climate',      label:'Climate',       domain:'climate',     r:20,
    intel:'1.5°C threshold breach by 2026 (WMO). Loss & Damage Fund: $700M (insufficient vs $400B need). India #3 emitter but lowest per capita. 500GW renewables target 2030—on track at 190GW.',
    tags:['Global','Existential'], power:62, risk:'Critical' },
  { id:'food',         label:'Food Security', domain:'climate',     r:14,
    intel:'735M chronically hungry globally. India wheat export ban 2022-ongoing. Ukraine war disrupted Black Sea grain corridor. AI precision agriculture adoption: 30% yield improvement potential.',
    tags:['Resource','Social','Climate'], power:65, risk:'High' },
  { id:'migration',    label:'Migration',     domain:'society',     r:14,
    intel:'110M forcibly displaced globally (UNHCR record). Climate-induced migration: 1.2B by 2050 (World Bank). India diaspora: 32M strong, $125.7B remittances 2024—world\'s largest recipient.',
    tags:['Social','Humanitarian','Demographics'], power:42, risk:'Medium' },
];

const EDGES = [
  { s:'india', t:'usa',          type:'alliance',  w:0.8, label:'iCET+Defense' },
  { s:'india', t:'quad',         type:'alliance',  w:0.9, label:'Core Member' },
  { s:'india', t:'brics',        type:'member',    w:0.7, label:'Founding Member' },
  { s:'india', t:'china',        type:'tension',   w:0.75, label:'LAC Border Dispute' },
  { s:'india', t:'russia',       type:'trade',     w:0.6, label:'Oil + Arms Trade' },
  { s:'india', t:'pakistan',     type:'conflict',  w:0.9, label:'Strategic Rivalry' },
  { s:'india', t:'ai',           type:'invest',    w:0.7, label:'NationalAI ₹10kCr' },
  { s:'india', t:'space',        type:'lead',      w:0.9, label:'Chandrayaan / ISRO' },
  { s:'india', t:'climate',      type:'commit',    w:0.6, label:'Net Zero 2070' },
  { s:'india', t:'semiconductor',type:'invest',    w:0.7, label:'$10B Fab Mission' },
  { s:'india', t:'sco',          type:'member',    w:0.5, label:'Member' },
  { s:'india', t:'rare_earth',   type:'interest',  w:0.6, label:'6% Untapped Reserves' },
  { s:'india', t:'oil',          type:'depend',    w:0.7, label:'85% Import Dependent' },
  { s:'china', t:'usa',          type:'rivalry',   w:0.9, label:'Great Power Competition' },
  { s:'china', t:'bri',          type:'lead',      w:0.9, label:'Initiative Lead' },
  { s:'china', t:'rare_earth',   type:'dominate',  w:0.95, label:'70% Global Control' },
  { s:'china', t:'semiconductor',type:'rivalry',   w:0.8, label:'Chip War' },
  { s:'china', t:'brics',        type:'lead',      w:0.8 },
  { s:'china', t:'russia',       type:'alliance',  w:0.8, label:'No-Limits Partnership' },
  { s:'china', t:'pakistan',     type:'alliance',  w:0.85, label:'CPEC + FATF Shield' },
  { s:'china', t:'sco',          type:'lead',      w:0.8 },
  { s:'usa',   t:'nato',         type:'lead',      w:0.9 },
  { s:'usa',   t:'quad',         type:'lead',      w:0.9 },
  { s:'usa',   t:'semiconductor',type:'control',   w:0.9, label:'CHIPS Act + ASML' },
  { s:'usa',   t:'ai',           type:'lead',      w:0.9, label:'Frontier AI Leader' },
  { s:'russia',t:'oil',          type:'control',   w:0.9, label:'Energy Weapon' },
  { s:'russia',t:'nato',         type:'conflict',  w:0.9, label:'Ukraine War' },
  { s:'russia',t:'sco',          type:'member',    w:0.7 },
  { s:'russia',t:'brics',        type:'member',    w:0.7 },
  { s:'quad',  t:'japan',        type:'member',    w:0.8 },
  { s:'quad',  t:'australia',    type:'member',    w:0.8 },
  { s:'eu',    t:'nato',         type:'overlap',   w:0.7 },
  { s:'eu',    t:'russia',       type:'conflict',  w:0.7, label:'Sanctions Regime' },
  { s:'eu',    t:'ai',           type:'regulate',  w:0.7, label:'AI Act 2024' },
  { s:'ai',    t:'semiconductor',type:'require',   w:0.95, label:'Requires Advanced Chips' },
  { s:'ai',    t:'quantum',      type:'synergy',   w:0.6 },
  { s:'ai',    t:'cyber',        type:'amplify',   w:0.75 },
  { s:'climate',t:'food',        type:'threat',    w:0.8, label:'Yield Gap Risk' },
  { s:'climate',t:'migration',   type:'cause',     w:0.75, label:'Climate Displacement' },
  { s:'oil',   t:'climate',      type:'impact',    w:0.8, label:'Carbon Emissions' },
  { s:'japan', t:'semiconductor',type:'invest',    w:0.7, label:'TSMC Japan Fab' },
  { s:'australia',t:'rare_earth',type:'supply',    w:0.7, label:'Strategic Deposits' },
  { s:'bri',   t:'pakistan',     type:'project',   w:0.85, label:'CPEC Flagship' },
  { s:'quantum',t:'cyber',       type:'threat',    w:0.7, label:'Q-Day Cryptobreak' },
];

// ── Live Feed Data ───────────────────────────────────────────────
const FEEDS = {
  geopolitics: [
    { sev:'HIGH', text:'India-China LAC: partial disengagement completed at Depsang; patrolling rights partially restored after 4-year standoff' },
    { sev:'HIGH', text:'QUAD foreign ministers convene emergency virtual session on PLAN activity around Senkaku Islands and contested atolls' },
    { sev:'CRIT', text:'Pakistan Shaheen-3 MRBM test: range 2,750km—full Indian subcontinent coverage; launched from undisclosed site' },
    { sev:'MED',  text:'India Chabahar port: US waiver extended 18 months enabling unimpeded Iranian port access for Central Asia connectivity' },
    { sev:'MED',  text:'BRICS+ finance ministers meeting: alternative SWIFT mechanism for bilateral trade pilot—India, China, Russia trilateral channel' },
  ],
  economics: [
    { sev:'MED',  text:'India nominal GDP reaches $3.73T—overtakes UK to become world\'s 4th largest economy ahead of 2027 forecast' },
    { sev:'HIGH', text:'China cuts rare earth export quotas 18%—chip supply chain red alert; TSMC announces 6-month buffer stock emergency build' },
    { sev:'LOW',  text:'IMF raises India FY2026 growth forecast to 7.2%—fastest major economy for 3rd consecutive year' },
    { sev:'MED',  text:'Rupee settlement mechanism live in 22 nations; SWIFT bypassed in 6 corridors; ₹ trade share hits 4.7% of India external trade' },
    { sev:'HIGH', text:'India PLI scheme: ₹2.1L Cr investment committed across 14 sectors; 8.5 lakh manufacturing jobs created in 36 months' },
  ],
  defense: [
    { sev:'CRIT', text:'DRDO Hypersonic Technology Demonstrator Vehicle (HSTDV-2): Mach 6.5 achieved in 32-sec scramjet burn—India joins hypersonic club' },
    { sev:'HIGH', text:'INS Arighat completes first credible nuclear deterrence patrol: K-4 SLBM (3,500km range) carried; second-strike capability confirmed' },
    { sev:'CRIT', text:'Cyber: Indian power grid attack attributed to APT41 (China state); CERT-In declares Tier-1 incident; 3 states affected for 4 hours' },
    { sev:'MED',  text:'INDUS-X milestone: 11 India-US co-development projects approved including AI targeting pod, counter-drone system, GaN radar' },
    { sev:'HIGH', text:'BrahMos-NG flight trial success: 450km range, Mach 3.5; Philippines deploys 3rd regiment; 14 nations in procurement pipeline' },
  ],
  technology: [
    { sev:'MED',  text:'IndiaAI Mission: ₹2,000Cr compute cluster tender awarded—10,000 H100-equivalent GPUs by Q3 2025; 3 sites in Pune, Hyderabad, Chennai' },
    { sev:'HIGH', text:'India AI startup funding Q1 2026: $4.2B—world #3 behind USA and China; 47 unicorns in AI-adjacent sectors' },
    { sev:'MED',  text:'ISRO Gaganyaan: Crew Module Integration Review cleared; Vyom Mitra humanoid robot final calibration; launch window Q4 2025' },
    { sev:'LOW',  text:'India Quantum: Delhi-Agra QKD fiber link operational (400km); DRDO classifies for strategic communications by 2026' },
    { sev:'MED',  text:'Tata Electronics: iPhone manufacturing capacity reaches 30% of Apple India target; $2.5B expansion announced for Tamil Nadu facility' },
  ],
  climate: [
    { sev:'HIGH', text:'India solar capacity: 94 GW cumulative—world #3; 2030 target 500 GW on track; manufacturing PLI drives domestic cell production' },
    { sev:'CRIT', text:'GLOF risk: 189 high-risk glacial lake outburst sites mapped in Himalayan region; Sikkim GLOF 2024 caused $1B damage—early warning gaps' },
    { sev:'HIGH', text:'Western Ghats: 3rd consecutive extreme monsoon season—148% of normal rainfall; landslides displace 400K in Maharashtra, Goa, Kerala' },
    { sev:'MED',  text:'India Green Hydrogen Mission Phase II: $500M disbursed; 12 electrolyzer manufacturers announced capacity of 5 GW/year by 2027' },
    { sev:'LOW',  text:'India-UAE climate finance pact: $75B green infrastructure pipeline by 2030; solar, green hydrogen, water tech corridors defined' },
  ],
  society: [
    { sev:'LOW',  text:'UPI January 2026: 15.6B transactions, ₹21.3L Cr value—47% of global real-time payment volume; DPI model adopted by 12 nations' },
    { sev:'MED',  text:'India GII 2025 rank: 39 (all-time high); patents filed up 31% YoY; startup ecosystem: 1.4L+ registered, 120 unicorns' },
    { sev:'LOW',  text:'e-Rupee CBDC cross-border pilot: India-UAE-Singapore corridor live; 3 lakh transactions processed; retail+wholesale pilots ongoing' },
    { sev:'MED',  text:'India diaspora remittances: $125.7B in 2024—world\'s largest recipient for 6th consecutive year; Gulf + USA major corridors' },
    { sev:'MED',  text:'India Demographic Dividend: 600M under 25; Skill India Mission targets 30M/year; AI literacy mandated in NEP 3.0 K-12 curriculum' },
  ],
};

const EDGE_COLOR = (type) => ({
  alliance:'#00C8FF', conflict:'#FF3355', rivalry:'#FF8C00', tension:'#FF8C00',
  trade:'#FFCC00', member:'#6090C0', invest:'#B06BFF', lead:'#00E882',
  dominate:'#FF3355', control:'#FF8C00', require:'#B06BFF', threat:'#FF3355',
  cause:'#FF8C00', impact:'#FF8C00', amplify:'#B06BFF', synergy:'#00E882',
  commit:'#00E882', regulate:'#B06BFF', overlap:'#6090C0', interest:'#FFCC00',
  supply:'#00E882', project:'#FFCC00', depend:'#FF8C00',
}[type] || '#1A4A6A');

const QUICK_QUERIES = [
  "India's semiconductor strategy & geopolitical leverage",
  "India-China conflict probability and deterrence",
  "QUAD effectiveness vs China's BRI in Indo-Pacific",
  "Path to India becoming AI superpower by 2030",
  "Climate risks threatening India's growth trajectory",
  "De-dollarization: BRICS impact on India's trade",
  "India's nuclear doctrine vs Pakistan & China threats",
  "Critical minerals strategy for India's tech future",
];

/* ════════════════════════════════════════════════════════════════
   COMPONENT
   ════════════════════════════════════════════════════════════════ */
export default function GlobalOntologyEngine() {
  const svgRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [activeDomain, setActiveDomain] = useState('all');
  const [feeds, setFeeds] = useState([]);
  const [query, setQuery] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [isQuerying, setIsQuerying] = useState(false);
  const [stats, setStats] = useState({ updates: 0, threats: 7, intel: 247 });
  const selectedRef = useRef(null);

  // Flatten feeds on mount
  useEffect(() => {
    const all = [];
    Object.entries(FEEDS).forEach(([domain, items]) =>
      items.forEach(item => all.push({ ...item, domain, time: new Date() })));
    setFeeds(all.sort(() => Math.random() - 0.5).slice(0, 16));
  }, []);

  // Live feed simulation
  useEffect(() => {
    const id = setInterval(() => {
      const domains = Object.keys(FEEDS);
      const domain = domains[Math.floor(Math.random() * domains.length)];
      const pool = FEEDS[domain];
      const item = pool[Math.floor(Math.random() * pool.length)];
      setFeeds(prev => [{ ...item, domain, time: new Date(), fresh: true }, ...prev.slice(0, 18)]);
      setStats(prev => ({ ...prev, updates: prev.updates + 1 }));
    }, 5000);
    return () => clearInterval(id);
  }, []);

  // Keep selectedRef in sync for use inside d3 closures
  useEffect(() => { selectedRef.current = selectedNode; }, [selectedNode]);

  // D3 force graph — re-init when domain filter changes
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const w = svgRef.current.clientWidth || 600;
    const h = svgRef.current.clientHeight || 500;

    const filtNodes = activeDomain === 'all'
      ? NODES : NODES.filter(n => n.domain === activeDomain);
    const filtIds = new Set(filtNodes.map(n => n.id));
    const filtEdges = EDGES.filter(e => filtIds.has(e.s) && filtIds.has(e.t));

    const nodes = filtNodes.map(n => ({ ...n }));
    const links = filtEdges.map(e => ({ ...e, source: e.s, target: e.t }));

    // Defs
    const defs = svg.append('defs');
    Object.entries(DOMAINS).forEach(([key, dom]) => {
      const f = defs.append('filter').attr('id', `glow-${key}`).attr('x','-50%').attr('y','-50%').attr('width','200%').attr('height','200%');
      f.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
      const m = f.append('feMerge');
      m.append('feMergeNode').attr('in', 'blur');
      m.append('feMergeNode').attr('in', 'SourceGraphic');
    });

    // Background grid
    const g0 = svg.append('g');
    const gs = 44;
    for (let x = 0; x <= w; x += gs)
      g0.append('line').attr('x1',x).attr('y1',0).attr('x2',x).attr('y2',h).attr('stroke','#051D30').attr('stroke-width',0.5);
    for (let y = 0; y <= h; y += gs)
      g0.append('line').attr('x1',0).attr('y1',y).attr('x2',w).attr('y2',y).attr('stroke','#051D30').attr('stroke-width',0.5);

    // Links
    const linkG = svg.append('g');
    const link = linkG.selectAll('line').data(links).join('line')
      .attr('stroke', d => EDGE_COLOR(d.type))
      .attr('stroke-opacity', 0.35)
      .attr('stroke-width', d => d.w * 1.8);

    // Link labels (on hover conceptually — static on render)
    const linkLabelG = svg.append('g');
    const linkLabel = linkLabelG.selectAll('text').data(links.filter(d => d.label)).join('text')
      .attr('fill', d => EDGE_COLOR(d.type))
      .attr('font-size', '7.5px')
      .attr('font-family', "'Share Tech Mono', monospace")
      .attr('text-anchor', 'middle')
      .attr('opacity', 0.55)
      .text(d => d.label || '');

    // Node groups
    const nodeG = svg.append('g');
    const nodeEl = nodeG.selectAll('g').data(nodes).join('g')
      .attr('cursor', 'pointer')
      .call(d3.drag()
        .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
        .on('end', (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
      )
      .on('click', (e, d) => { e.stopPropagation(); setSelectedNode(prev => prev?.id === d.id ? null : d); });

    // Outer pulse ring
    nodeEl.append('circle')
      .attr('r', d => d.r + 10)
      .attr('fill', 'none')
      .attr('stroke', d => DOMAINS[d.domain]?.color || C.primary)
      .attr('stroke-opacity', 0.15)
      .attr('stroke-width', 1.5)
      .attr('class', 'pulse');

    // India special dashed ring
    nodeEl.filter(d => d.id === 'india').append('circle')
      .attr('r', d => d.r + 18)
      .attr('fill', 'none')
      .attr('stroke', C.saffron)
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '5,4')
      .attr('stroke-opacity', 0.7);

    // Main circle
    nodeEl.append('circle')
      .attr('class', 'main-circle')
      .attr('r', d => d.r)
      .attr('fill', d => `rgba(${hexRgb(DOMAINS[d.domain]?.color || C.primary)}, 0.1)`)
      .attr('stroke', d => DOMAINS[d.domain]?.color || C.primary)
      .attr('stroke-width', d => d.id === 'india' ? 2.8 : 1.8)
      .attr('filter', d => `url(#glow-${d.domain})`);

    // Icon
    nodeEl.append('text')
      .attr('text-anchor', 'middle').attr('dominant-baseline', 'central')
      .attr('font-size', d => `${Math.max(10, d.r * 0.75)}px`)
      .text(d => DOMAINS[d.domain]?.icon || '●');

    // Label
    nodeEl.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', d => d.r + 15)
      .attr('fill', d => DOMAINS[d.domain]?.color || C.primary)
      .attr('font-size', d => d.r >= 20 ? '10.5px' : '9px')
      .attr('font-family', "'Share Tech Mono', monospace")
      .attr('font-weight', d => d.id === 'india' ? 'bold' : 'normal')
      .attr('opacity', 0.9)
      .text(d => d.label);

    // Force simulation
    const sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(d => 90 + (1 - d.w) * 70))
      .force('charge', d3.forceManyBody().strength(-450))
      .force('center', d3.forceCenter(w / 2, h / 2))
      .force('collision', d3.forceCollide().radius(d => d.r + 22))
      .on('tick', () => {
        link
          .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
          .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
        linkLabel
          .attr('x', d => (d.source.x + d.target.x) / 2)
          .attr('y', d => (d.source.y + d.target.y) / 2);
        nodeEl.attr('transform', d => `translate(${d.x},${d.y})`);
      });

    // Click background to deselect
    svg.on('click', () => setSelectedNode(null));

    return () => sim.stop();
  }, [activeDomain]);

  // Highlight selected node
  useEffect(() => {
    if (!svgRef.current) return;
    d3.select(svgRef.current).selectAll('.main-circle')
      .attr('fill', d => {
        const base = hexRgb(DOMAINS[d.domain]?.color || C.primary);
        const sel = selectedNode?.id === d.id;
        return `rgba(${base}, ${sel ? 0.35 : 0.1})`;
      })
      .attr('stroke-width', d => {
        const sel = selectedNode?.id === d.id;
        return sel ? 3.5 : (d.id === 'india' ? 2.8 : 1.8);
      });
  }, [selectedNode]);

  // AI Query
  const handleQuery = useCallback(async () => {
    if (!query.trim() || isQuerying) return;
    setIsQuerying(true);
    setAiResponse('');
    const ctx = selectedNode
      ? `Active entity focus: ${selectedNode.label} (${DOMAINS[selectedNode.domain]?.label}). Classified intel: ${selectedNode.intel}. Tags: ${selectedNode.tags?.join(', ')}. Power Index: ${selectedNode.power}. Risk Level: ${selectedNode.risk}.`
      : `Full global ontology active: ${NODES.length} entities, ${EDGES.length} relationships spanning 6 strategic domains.`;
    try {
      const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1000,
          system: `You are the Global Ontology Engine (GOE)—a classified AI strategic intelligence system operated for India's national security and global strategic analysis. You process interconnected geopolitical, economic, defense, technology, climate, and societal data from a live knowledge graph.

Current context: ${ctx}

Respond ONLY in this exact structured format—no preamble, no markdown headers:

▸ ASSESSMENT
[2-3 sentence strategic summary with precise factual grounding]

▸ KEY VECTORS
• [Factor 1 with specific data]
• [Factor 2 with specific data]
• [Factor 3 with specific data]
• [Factor 4 if needed]

▸ INDIA ANGLE
[2-3 sentences on specific implications, opportunities, and risks for India]

▸ THREAT LEVEL: [CRITICAL / HIGH / MEDIUM / LOW]
[One-line justification]

▸ STRATEGIC RECOMMENDATION
[1-2 concrete, actionable steps with timeline]

Be information-dense, precise, and intelligence-grade. No hedging language.`,
          messages: [{ role: "user", content: query }]
        })
      });
      const data = await res.json();
      const text = data.content?.map(b => b.text || '').join('') || 'No intelligence available.';
      setAiResponse(text);
    } catch {
      setAiResponse('⚠ GOE SYSTEM ERROR\nUnable to connect to intelligence network.\nVerify clearance level and retry.');
    }
    setIsQuerying(false);
  }, [query, isQuerying, selectedNode]);

  const visibleFeeds = activeDomain === 'all' ? feeds : feeds.filter(f => f.domain === activeDomain);

  /* ── RENDER ─────────────────────────────────────────────────── */
  return (
    <div style={{
      width: '100%', height: '100vh', background: C.bg,
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
      fontFamily: "'Share Tech Mono', monospace", color: C.textBright,
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@500;600;700&display=swap');
        *{box-sizing:border-box;margin:0;padding:0;}
        ::-webkit-scrollbar{width:3px;}
        ::-webkit-scrollbar-track{background:#010C18;}
        ::-webkit-scrollbar-thumb{background:#0C3A58;border-radius:2px;}
        @keyframes pulse{0%,100%{opacity:.25;transform:scale(1);}50%{opacity:.7;transform:scale(1.18);}}
        @keyframes blink{0%,49%{opacity:1;}50%,100%{opacity:0;}}
        @keyframes fadeslide{from{opacity:0;transform:translateY(6px);}to{opacity:1;transform:none;}}
        @keyframes spin{to{transform:rotate(360deg);}}
        .pulse{animation:pulse 3s ease-in-out infinite;}
        .blink{animation:blink 1s step-end infinite;}
        .feed-new{animation:fadeslide 0.5s ease forwards;}
        .goe-btn:hover{opacity:1!important;border-color:rgba(0,200,255,.5)!important;}
        .qbtn:hover{background:rgba(0,200,255,.08)!important;border-color:#0C3A58!important;color:#7BBAD5!important;}
        textarea{resize:none;}
        textarea:focus,input:focus{outline:none;}
        button{cursor:pointer;transition:all .18s;}
      `}</style>

      {/* ══ HEADER ═══════════════════════════════════════════════ */}
      <div style={{
        flexShrink: 0, minHeight: 54,
        background: 'linear-gradient(180deg,#021020 0%,#010C18 100%)',
        borderBottom: `1px solid ${C.border}`,
        display: 'flex', alignItems: 'center', gap: 14, padding: '0 16px',
      }}>
        {/* Logo */}
        <div style={{ display:'flex', alignItems:'center', gap:10, minWidth:210, flexShrink:0 }}>
          <div style={{
            width:38, height:38, borderRadius:'50%',
            border:`2px solid ${C.primary}`,
            background:`radial-gradient(circle, rgba(0,200,255,.18) 0%, transparent 70%)`,
            display:'flex', alignItems:'center', justifyContent:'center',
            fontSize:17, boxShadow:`0 0 14px rgba(0,200,255,.4)`,
            flexShrink:0,
          }}>🕸️</div>
          <div>
            <div style={{ fontFamily:"'Rajdhani',sans-serif", fontWeight:700, fontSize:13,
              color:C.primary, letterSpacing:'2.5px', lineHeight:1.1 }}>
              GLOBAL ONTOLOGY ENGINE
            </div>
            <div style={{ fontSize:8, color:C.text, letterSpacing:'2.5px', lineHeight:1.5 }}>
              STRATEGIC INTELLIGENCE SYSTEM v4.2 · CLASSIFIED
            </div>
          </div>
        </div>

        {/* Domain filters */}
        <div style={{ display:'flex', gap:5, flex:1, justifyContent:'center', flexWrap:'wrap' }}>
          {[['all', 'ALL DOMAINS', C.primary, ''], ...Object.entries(DOMAINS).map(([k,v]) => [k, `${v.icon} ${v.short}`, v.color, k])].map(([key, label, color]) => {
            const active = activeDomain === key || (key === 'all' && activeDomain === 'all');
            const isActive = key === 'all' ? activeDomain === 'all' : activeDomain === key;
            return (
              <button key={key}
                className="goe-btn"
                onClick={() => setActiveDomain(isActive && key !== 'all' ? 'all' : key)}
                style={{
                  padding:'4px 11px', fontSize:9, letterSpacing:'1.2px',
                  background: isActive ? `rgba(${hexRgb(color)},0.18)` : 'transparent',
                  border: `1px solid ${isActive ? color : C.border}`,
                  color: isActive ? color : C.text,
                  borderRadius:2, fontFamily:"'Share Tech Mono',monospace",
                  opacity: isActive ? 1 : 0.6,
                }}>
                {label}
              </button>
            );
          })}
        </div>

        {/* System stats */}
        <div style={{ display:'flex', gap:18, flexShrink:0, alignItems:'center' }}>
          {[
            { l:'ENTITIES', v: activeDomain === 'all' ? NODES.length : NODES.filter(n=>n.domain===activeDomain).length },
            { l:'RELATIONS', v: EDGES.length },
            { l:'LIVE OPS', v: stats.updates },
            { l:'ALERTS', v: stats.threats, c: C.red },
          ].map(s => (
            <div key={s.l} style={{ textAlign:'center' }}>
              <div style={{ fontSize:16, fontWeight:'bold', color:s.c||C.primary, lineHeight:1, fontFamily:"'Rajdhani',sans-serif" }}>
                {s.v}
              </div>
              <div style={{ fontSize:8, color:C.text, letterSpacing:'1px' }}>{s.l}</div>
            </div>
          ))}
          <div style={{
            width:8, height:8, borderRadius:'50%', background:C.green,
            boxShadow:`0 0 8px ${C.green}`, animation:'pulse 2s ease infinite',
          }}/>
        </div>
      </div>

      {/* ══ BODY ════════════════════════════════════════════════ */}
      <div style={{ flex:1, display:'flex', overflow:'hidden', minHeight:0 }}>

        {/* ── LEFT: Live Intel Feed ──────────────────────────── */}
        <div style={{
          width:255, flexShrink:0,
          background: C.panel, borderRight:`1px solid ${C.border}`,
          display:'flex', flexDirection:'column', overflow:'hidden',
        }}>
          <div style={{
            padding:'7px 12px', borderBottom:`1px solid ${C.border}`,
            display:'flex', alignItems:'center', justifyContent:'space-between',
          }}>
            <span style={{ fontSize:9, letterSpacing:'2px', color:C.text }}>LIVE INTEL FEED</span>
            <div style={{ display:'flex', alignItems:'center', gap:5 }}>
              <div style={{ width:6, height:6, borderRadius:'50%', background:C.green, animation:'pulse 1.5s infinite' }}/>
              <span style={{ fontSize:8, color:C.green, letterSpacing:'1px' }}>STREAMING</span>
            </div>
          </div>
          <div style={{ overflowY:'auto', flex:1, padding:8 }}>
            {visibleFeeds.map((f, i) => (
              <div key={i} className={f.fresh ? 'feed-new' : ''} style={{
                marginBottom:5, padding:'7px 10px',
                background: f.fresh
                  ? `rgba(${hexRgb(DOMAINS[f.domain]?.color||C.primary)}, 0.07)`
                  : 'rgba(2,10,20,.85)',
                border:`1px solid ${f.fresh ? (DOMAINS[f.domain]?.color||C.primary)+'33' : C.borderSoft}`,
                borderLeft:`3px solid ${SEV[f.sev]||C.text}`,
                borderRadius:2,
              }}>
                <div style={{ display:'flex', justifyContent:'space-between', marginBottom:3 }}>
                  <span style={{ fontSize:8, color:SEV[f.sev], letterSpacing:'1px', fontWeight:'bold' }}>
                    {f.sev}
                  </span>
                  <span style={{ fontSize:8, color:DOMAINS[f.domain]?.color, opacity:.75 }}>
                    {DOMAINS[f.domain]?.short}
                  </span>
                </div>
                <div style={{ fontSize:9.5, color:C.textBright, lineHeight:1.55 }}>{f.text}</div>
                <div style={{ fontSize:8, color:C.text, marginTop:4 }}>
                  {f.time?.toLocaleTimeString?.() || '—'}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── CENTER: Knowledge Graph ────────────────────────── */}
        <div style={{ flex:1, position:'relative', overflow:'hidden' }}>
          {/* CRT scanlines */}
          <div style={{
            position:'absolute', inset:0, pointerEvents:'none', zIndex:1,
            background:'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,5,12,.04) 2px, rgba(0,5,12,.04) 4px)',
          }}/>
          <svg ref={svgRef} style={{ width:'100%', height:'100%', display:'block' }}/>
          {/* Corner decorations */}
          <div style={{ position:'absolute', top:10, left:10, fontSize:8, color:C.text, letterSpacing:'1.5px', zIndex:2 }}>
            DRAG NODES · CLICK TO ANALYZE
          </div>
          {/* Legend */}
          <div style={{
            position:'absolute', top:10, right:10, zIndex:2,
            display:'flex', flexDirection:'column', gap:4,
            background:'rgba(1,12,24,.85)', padding:'8px 10px',
            border:`1px solid ${C.border}`, borderRadius:2,
          }}>
            {Object.entries(DOMAINS).map(([k,v]) => (
              <div key={k} style={{ display:'flex', alignItems:'center', gap:6 }}>
                <div style={{ width:7, height:7, borderRadius:'50%', background:v.color, opacity:.85 }}/>
                <span style={{ fontSize:8, color:C.text }}>{v.label}</span>
              </div>
            ))}
          </div>
          {/* Footer label */}
          <div style={{
            position:'absolute', bottom:10, left:'50%', transform:'translateX(-50%)',
            fontSize:8, color:C.text, letterSpacing:'2px', zIndex:2,
            background:'rgba(1,12,24,.85)', padding:'4px 14px',
            border:`1px solid ${C.border}`, borderRadius:2,
          }}>
            GLOBAL ONTOLOGY GRAPH · {NODES.length} ENTITIES · {EDGES.length} RELATIONSHIPS
          </div>
        </div>

        {/* ── RIGHT: Entity Intel + AI Query ───────────────── */}
        <div style={{
          width:305, flexShrink:0,
          background: C.panel, borderLeft:`1px solid ${C.border}`,
          display:'flex', flexDirection:'column', overflow:'hidden',
        }}>
          {/* Entity Panel */}
          <div style={{ flexShrink:0, borderBottom:`1px solid ${C.border}` }}>
            {selectedNode ? (
              <>
                <div style={{
                  padding:'9px 12px',
                  background:`rgba(${hexRgb(DOMAINS[selectedNode.domain]?.color||C.primary)},.1)`,
                  borderBottom:`1px solid ${C.border}`,
                  display:'flex', alignItems:'center', justifyContent:'space-between',
                }}>
                  <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                    <span style={{ fontSize:20 }}>{DOMAINS[selectedNode.domain]?.icon}</span>
                    <div>
                      <div style={{ fontFamily:"'Rajdhani',sans-serif", fontWeight:700, fontSize:14, color:C.white, lineHeight:1.1 }}>
                        {selectedNode.label}
                      </div>
                      <div style={{ fontSize:8, color:DOMAINS[selectedNode.domain]?.color, letterSpacing:'1.5px' }}>
                        {DOMAINS[selectedNode.domain]?.label.toUpperCase()}
                      </div>
                    </div>
                  </div>
                  <div style={{
                    padding:'2px 8px', fontSize:8, letterSpacing:'1px', borderRadius:2,
                    border:`1px solid ${selectedNode.risk==='Critical'?C.red:selectedNode.risk==='High'?C.orange:C.gold}`,
                    color:selectedNode.risk==='Critical'?C.red:selectedNode.risk==='High'?C.orange:C.gold,
                  }}>{selectedNode.risk?.toUpperCase()}</div>
                </div>
                <div style={{ padding:'10px 12px', maxHeight:220, overflowY:'auto' }}>
                  <div style={{ fontSize:9.5, color:C.textBright, lineHeight:1.65, marginBottom:10 }}>
                    {selectedNode.intel}
                  </div>
                  {/* Power bar */}
                  <div style={{ marginBottom:10 }}>
                    <div style={{ display:'flex', justifyContent:'space-between', marginBottom:3 }}>
                      <span style={{ fontSize:8, color:C.text, letterSpacing:'1px' }}>POWER INDEX</span>
                      <span style={{ fontSize:9, color:C.primary }}>{selectedNode.power} / 100</span>
                    </div>
                    <div style={{ height:3, background:C.borderSoft, borderRadius:2 }}>
                      <div style={{
                        height:'100%', borderRadius:2, width:`${selectedNode.power}%`,
                        background:`linear-gradient(90deg, ${DOMAINS[selectedNode.domain]?.color||C.primary}, ${C.primary})`,
                        transition:'width .6s ease',
                      }}/>
                    </div>
                  </div>
                  {/* Tags */}
                  <div style={{ display:'flex', flexWrap:'wrap', gap:4, marginBottom:10 }}>
                    {(selectedNode.tags||[]).map(t => (
                      <span key={t} style={{
                        fontSize:8, padding:'2px 7px',
                        border:`1px solid ${C.border}`, color:C.text, borderRadius:2,
                      }}>{t}</span>
                    ))}
                  </div>
                  {/* Connected nodes */}
                  <div style={{ fontSize:8, color:C.text, letterSpacing:'1px', marginBottom:5 }}>CONNECTED ENTITIES</div>
                  <div style={{ display:'flex', flexWrap:'wrap', gap:4 }}>
                    {EDGES.filter(e => e.s===selectedNode.id||e.t===selectedNode.id).slice(0,10).map(e => {
                      const oid = e.s===selectedNode.id?e.t:e.s;
                      const other = NODES.find(n=>n.id===oid);
                      if(!other) return null;
                      return (
                        <button key={oid} onClick={() => setSelectedNode(other)} style={{
                          fontSize:8, padding:'2px 7px',
                          background:`rgba(${hexRgb(DOMAINS[other.domain]?.color||C.primary)},.1)`,
                          border:`1px solid ${(DOMAINS[other.domain]?.color||C.primary)}44`,
                          color:DOMAINS[other.domain]?.color||C.primary,
                          borderRadius:2, fontFamily:"'Share Tech Mono',monospace",
                        }}>{other.label}</button>
                      );
                    })}
                  </div>
                </div>
              </>
            ) : (
              <div style={{ padding:'18px 12px', textAlign:'center' }}>
                <div style={{ fontSize:28, opacity:.3, marginBottom:8 }}>🕸️</div>
                <div style={{ fontSize:9, color:C.text, letterSpacing:'1px', lineHeight:1.8 }}>
                  CLICK ANY NODE TO VIEW<br/>ENTITY INTELLIGENCE BRIEF
                </div>
              </div>
            )}
          </div>

          {/* AI Strategic Query Panel */}
          <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden', minHeight:0 }}>
            <div style={{
              padding:'7px 12px', borderBottom:`1px solid ${C.border}`,
              display:'flex', alignItems:'center', justifyContent:'space-between', flexShrink:0,
            }}>
              <span style={{ fontSize:9, letterSpacing:'2px', color:C.text }}>AI STRATEGIC QUERY</span>
              <div style={{ fontSize:8, color:C.purple, padding:'1px 7px',
                border:`1px solid ${C.purple}55`, borderRadius:2, letterSpacing:'1px' }}>
                CLAUDE-POWERED
              </div>
            </div>

            {/* Quick query chips */}
            <div style={{ padding:'8px 10px', borderBottom:`1px solid ${C.border}`, flexShrink:0 }}>
              <div style={{ fontSize:8, color:C.text, letterSpacing:'1px', marginBottom:5 }}>QUICK ANALYSIS</div>
              <div style={{ display:'flex', flexWrap:'wrap', gap:4 }}>
                {QUICK_QUERIES.map(q => (
                  <button key={q} onClick={() => setQuery(q)} className="qbtn" style={{
                    fontSize:8, padding:'3px 7px',
                    background:'transparent', border:`1px solid ${C.border}`,
                    color:C.text, borderRadius:2, fontFamily:"'Share Tech Mono',monospace",
                  }}>{q}</button>
                ))}
              </div>
            </div>

            {/* AI Response */}
            <div style={{ flex:1, overflowY:'auto', padding:'10px 12px', minHeight:0 }}>
              {isQuerying ? (
                <div style={{ textAlign:'center', padding:'24px 0' }}>
                  <div style={{ fontSize:20, animation:'spin 1.5s linear infinite', marginBottom:10 }}>◈</div>
                  <div style={{ fontSize:10, color:C.primary, marginBottom:6 }}>
                    PROCESSING INTELLIGENCE QUERY<span className="blink">_</span>
                  </div>
                  <div style={{ fontSize:8.5, color:C.text, lineHeight:1.7 }}>
                    Cross-referencing {NODES.length} ontology entities<br/>
                    Analyzing {EDGES.length} strategic relationships<br/>
                    Generating classified intelligence brief
                  </div>
                </div>
              ) : aiResponse ? (
                <div style={{ fontSize:9.5, color:C.textBright, lineHeight:1.8, whiteSpace:'pre-wrap' }}>
                  {aiResponse}
                </div>
              ) : (
                <div style={{ textAlign:'center', padding:'24px 0' }}>
                  <div style={{ fontSize:22, opacity:.3, marginBottom:8 }}>◈</div>
                  <div style={{ fontSize:10, color:C.textMid, marginBottom:6, letterSpacing:'1px' }}>
                    GOE INTELLIGENCE READY
                  </div>
                  <div style={{ fontSize:8.5, color:C.text, lineHeight:1.8 }}>
                    Select a query chip above or type<br/>
                    your own strategic analysis request.<br/>
                    Click a node first for entity context.
                  </div>
                </div>
              )}
            </div>

            {/* Query Input */}
            <div style={{
              padding:'10px 12px', borderTop:`1px solid ${C.border}`,
              background:'rgba(2,10,20,.95)', flexShrink:0,
            }}>
              <div style={{
                display:'flex', gap:6,
                border:`1px solid ${query.trim() ? C.primary+'66' : C.border}`,
                borderRadius:3, background:'rgba(1,8,16,.9)',
                transition:'border-color .2s',
              }}>
                <textarea
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={e => { if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();handleQuery();}}}
                  placeholder="Query the intelligence graph..."
                  style={{
                    flex:1, padding:'8px 10px', background:'transparent', border:'none',
                    color:C.textBright, fontSize:10,
                    fontFamily:"'Share Tech Mono',monospace",
                    minHeight:54, maxHeight:90, lineHeight:1.6,
                  }}
                />
                <button
                  onClick={handleQuery}
                  disabled={isQuerying||!query.trim()}
                  style={{
                    padding:'8px 12px', margin:'4px',
                    background: isQuerying||!query.trim() ? 'transparent' : C.primaryGlow,
                    border:`1px solid ${isQuerying||!query.trim() ? C.border : C.primary}`,
                    color: isQuerying||!query.trim() ? C.text : C.primary,
                    borderRadius:2, fontSize:14, fontWeight:'bold',
                    fontFamily:"'Share Tech Mono',monospace",
                    alignSelf:'flex-end', cursor: isQuerying||!query.trim() ? 'default':'pointer',
                  }}
                >{isQuerying ? '◌' : '▶'}</button>
              </div>
              <div style={{ fontSize:8, color:C.text, marginTop:4, letterSpacing:'.5px' }}>
                ↵ ENTER to query · SHIFT+ENTER for newline
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
