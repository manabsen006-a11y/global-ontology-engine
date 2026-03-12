import { useState, useEffect, useRef, useCallback } from "react";
import * as d3 from "d3";
import { searchNews } from "../services/newsApi";
import { C, hexRgb, DOMAINS, SEV } from "../theme";

/* ════════════════════════════════════════════════════════════════
   GLOBAL ONTOLOGY ENGINE  —  Strategic Intelligence System v4.2
   ════════════════════════════════════════════════════════════════ */

// ── Entity Graph Data ────────────────────────────────────────────
const NODES = [
    {
        id: 'india', label: 'India', domain: 'geopolitics', r: 26,
        intel: 'World\'s largest democracy (1.44B). Fastest-growing G20 economy at 7%+. Aspirant UNSC permanent seat. G20 host 2023. Indo-Pacific linchpin. Strategic autonomy doctrine balancing USA, Russia, China.',
        tags: ['Nation', 'G20', 'QUAD', 'BRICS', 'SCO', 'Nuclear'], power: 78, risk: 'Medium'
    },
    {
        id: 'china', label: 'China', domain: 'geopolitics', r: 24,
        intel: 'World #2 economy ($18T). Rare earth dominance (70%+ processing). PLA modernization at $225B/yr. Belt & Road across 140+ nations. Taiwan flashpoint intensifying. Demographic headwinds emerging.',
        tags: ['Nation', 'P5', 'BRICS', 'SCO', 'Nuclear'], power: 89, risk: 'High'
    },
    {
        id: 'usa', label: 'USA', domain: 'geopolitics', r: 24,
        intel: 'Global reserve currency. NATO anchor. CHIPS Act $52B for semiconductor reshoring. AI frontier with GPT-5, Claude 4. Deepening India partnership via iCET. Debt $34T—fiscal pressure rising.',
        tags: ['Nation', 'P5', 'NATO', 'QUAD', 'G7', 'Nuclear'], power: 95, risk: 'Medium'
    },
    {
        id: 'russia', label: 'Russia', domain: 'geopolitics', r: 18,
        intel: 'Ukraine war year 3+. Energy weaponization via Nord Stream leverage. Pivot East—China+India trade. Nuclear doctrine posture shifts. Wagner fallout destabilizing Africa ops.',
        tags: ['Nation', 'P5', 'BRICS', 'SCO', 'Nuclear'], power: 72, risk: 'Critical'
    },
    {
        id: 'eu', label: 'EU', domain: 'geopolitics', r: 20,
        intel: 'Strategic autonomy doctrine under von der Leyen. World-first AI Act (2024). Carbon Border Adjustment Mechanism. Ukraine + Moldova enlargement track. Defence spending under pressure.',
        tags: ['Bloc', 'NATO', 'G7'], power: 75, risk: 'Medium'
    },
    {
        id: 'pakistan', label: 'Pakistan', domain: 'geopolitics', r: 13,
        intel: 'IMF dependency ($7B bailout). CPEC stalled at $25B. Nuclear arsenal expansion (170+ warheads). Military-civil tension chronic. Kashmir proxy operations ongoing.',
        tags: ['Nation', 'SCO', 'Nuclear'], power: 42, risk: 'High'
    },
    {
        id: 'japan', label: 'Japan', domain: 'geopolitics', r: 16,
        intel: 'Defense budget doubling to 2% GDP ($80B). QUAD member. TSMC Kumamoto fab operational. Demographic crisis (-700K/yr). Leading semiconductor equipment maker.',
        tags: ['Nation', 'G7', 'QUAD'], power: 65, risk: 'Medium'
    },
    {
        id: 'australia', label: 'Australia', domain: 'geopolitics', r: 14,
        intel: 'AUKUS nuclear submarine deal ($368B). World\'s largest critical minerals exporter. Five Eyes intelligence anchor. Reduced China trade dependency post-sanctions.',
        tags: ['Nation', 'QUAD', 'AUKUS'], power: 55, risk: 'Low'
    },
    {
        id: 'quad', label: 'QUAD', domain: 'defense', r: 19,
        intel: 'India-USA-Japan-Australia strategic dialogue. Evolved from maritime to tech+supply chain resilience. Annual summits. Indo-Pacific Maritime Domain Awareness sharing. Counter-BRI narrative.',
        tags: ['Alliance'], power: 85, risk: 'Low'
    },
    {
        id: 'brics', label: 'BRICS+', domain: 'economics', r: 19,
        intel: 'Expanded 2024: 9 nations including Saudi Arabia, UAE, Ethiopia, Iran, Egypt. 37% global GDP (PPP). New Development Bank $32B lent. De-dollarization agenda gaining traction.',
        tags: ['Bloc'], power: 76, risk: 'Medium'
    },
    {
        id: 'sco', label: 'SCO', domain: 'geopolitics', r: 15,
        intel: 'Shanghai Cooperation Organisation—Eurasian security+economic bloc. India+Pakistan both members creating strategic tension. China-Russia at core. Counter-terrorism mandate.',
        tags: ['Bloc'], power: 68, risk: 'Medium'
    },
    {
        id: 'nato', label: 'NATO', domain: 'defense', r: 19,
        intel: '32 members post-Sweden (2024). Combined defense $1.2T+. Eastern flank: 300K+ rapid response. Cyber and space as operational domains. Sweden-Finland accession reshapes Arctic.',
        tags: ['Alliance'], power: 92, risk: 'Low'
    },
    {
        id: 'ai', label: 'AI / LLM', domain: 'technology', r: 22,
        intel: 'AGI race: OpenAI GPT-5, Anthropic Claude 4, Google Gemini Ultra. Agentic AI in production deployment. Defense: autonomous targeting, ISR. India National AI Mission ₹10,372Cr. 300M jobs disruption risk.',
        tags: ['Technology', 'Dual-use', 'Strategic'], power: 92, risk: 'High'
    },
    {
        id: 'semiconductor', label: 'Chips', domain: 'technology', r: 19,
        intel: 'TSMC 2nm production 2025. CHIPS Act: 5 US fab projects. India fab mission $10B incentives. Netherlands ASML EUV export controls. Strategic chokepoint: TSMC produces 90% advanced chips.',
        tags: ['Technology', 'Resource', 'Strategic'], power: 88, risk: 'High'
    },
    {
        id: 'quantum', label: 'Quantum', domain: 'technology', r: 14,
        intel: 'Q-Day estimate: cryptographic break in 2030s. India National Quantum Mission ₹6,003Cr. Google 1M qubit roadmap. Post-quantum migration: NIST PQC standards finalised 2024.',
        tags: ['Technology', 'Defense', 'Emerging'], power: 72, risk: 'High'
    },
    {
        id: 'space', label: 'Space', domain: 'technology', r: 16,
        intel: 'Chandrayaan-3 south pole success 2023—India #4 lunar power. Gaganyaan crewed flight 2025. ISRO commercialization via IN-SPACe. Artemis vs Chinese lunar program resource race.',
        tags: ['Technology', 'Prestige', 'Defense'], power: 72, risk: 'Low'
    },
    {
        id: 'cyber', label: 'Cyber', domain: 'defense', r: 14,
        intel: 'Nation-state APT proliferation: Volt Typhoon (China), APT29 (Russia). AI-powered malware at scale. Critical infrastructure attacks +300% since 2020. India CERT-In 24hr reporting mandate.',
        tags: ['Defense', 'Technology', 'Threat'], power: 75, risk: 'Critical'
    },
    {
        id: 'bri', label: 'Belt & Road', domain: 'economics', r: 16,
        intel: '$900B+ committed across 140 nations. Debt trap vs connectivity debate. CPEC ($62B) stalled. Sri Lanka Hambantota controversy. Counter: India\'s IMEC (India-Middle East-Europe) corridor.',
        tags: ['Initiative', 'Economics', 'Geopolitics'], power: 72, risk: 'Medium'
    },
    {
        id: 'oil', label: 'Energy', domain: 'economics', r: 16,
        intel: 'Petrodollar challenged by BRICS. India buys Russian Urals at $15 discount—$40B savings. OPEC+ production cuts geopolitically driven. India 85% oil import dependent—strategic vulnerability.',
        tags: ['Resource', 'Economics', 'Strategic'], power: 82, risk: 'High'
    },
    {
        id: 'rare_earth', label: 'Rare Earth', domain: 'economics', r: 14,
        intel: 'China controls 70%+ processing of 17 critical metals. Essential for EVs, defense systems, AI chips. India: 6% global reserves (largely untapped). India-Australia critical minerals pact 2023.',
        tags: ['Resource', 'Strategic', 'Technology'], power: 78, risk: 'High'
    },
    {
        id: 'climate', label: 'Climate', domain: 'climate', r: 20,
        intel: '1.5°C threshold breach by 2026 (WMO). Loss & Damage Fund: $700M (insufficient vs $400B need). India #3 emitter but lowest per capita. 500GW renewables target 2030—on track at 190GW.',
        tags: ['Global', 'Existential'], power: 62, risk: 'Critical'
    },
    {
        id: 'food', label: 'Food Security', domain: 'climate', r: 14,
        intel: '735M chronically hungry globally. India wheat export ban 2022-ongoing. Ukraine war disrupted Black Sea grain corridor. AI precision agriculture adoption: 30% yield improvement potential.',
        tags: ['Resource', 'Social', 'Climate'], power: 65, risk: 'High'
    },
    {
        id: 'migration', label: 'Migration', domain: 'society', r: 14,
        intel: '110M forcibly displaced globally (UNHCR record). Climate-induced migration: 1.2B by 2050 (World Bank). India diaspora: 32M strong, $125.7B remittances 2024—world\'s largest recipient.',
        tags: ['Social', 'Humanitarian', 'Demographics'], power: 42, risk: 'Medium'
    },
];

const EDGES = [
    { s: 'india', t: 'usa', type: 'alliance', w: 0.8, label: 'iCET+Defense' },
    { s: 'india', t: 'quad', type: 'alliance', w: 0.9, label: 'Core Member' },
    { s: 'india', t: 'brics', type: 'member', w: 0.7, label: 'Founding Member' },
    { s: 'india', t: 'china', type: 'tension', w: 0.75, label: 'LAC Border Dispute' },
    { s: 'india', t: 'russia', type: 'trade', w: 0.6, label: 'Oil + Arms Trade' },
    { s: 'india', t: 'pakistan', type: 'conflict', w: 0.9, label: 'Strategic Rivalry' },
    { s: 'india', t: 'ai', type: 'invest', w: 0.7, label: 'NationalAI ₹10kCr' },
    { s: 'india', t: 'space', type: 'lead', w: 0.9, label: 'Chandrayaan / ISRO' },
    { s: 'india', t: 'climate', type: 'commit', w: 0.6, label: 'Net Zero 2070' },
    { s: 'india', t: 'semiconductor', type: 'invest', w: 0.7, label: '$10B Fab Mission' },
    { s: 'india', t: 'sco', type: 'member', w: 0.5, label: 'Member' },
    { s: 'india', t: 'rare_earth', type: 'interest', w: 0.6, label: '6% Untapped Reserves' },
    { s: 'india', t: 'oil', type: 'depend', w: 0.7, label: '85% Import Dependent' },
    { s: 'china', t: 'usa', type: 'rivalry', w: 0.9, label: 'Great Power Competition' },
    { s: 'china', t: 'bri', type: 'lead', w: 0.9, label: 'Initiative Lead' },
    { s: 'china', t: 'rare_earth', type: 'dominate', w: 0.95, label: '70% Global Control' },
    { s: 'china', t: 'semiconductor', type: 'rivalry', w: 0.8, label: 'Chip War' },
    { s: 'china', t: 'brics', type: 'lead', w: 0.8 },
    { s: 'china', t: 'russia', type: 'alliance', w: 0.8, label: 'No-Limits Partnership' },
    { s: 'china', t: 'pakistan', type: 'alliance', w: 0.85, label: 'CPEC + FATF Shield' },
    { s: 'china', t: 'sco', type: 'lead', w: 0.8 },
    { s: 'usa', t: 'nato', type: 'lead', w: 0.9 },
    { s: 'usa', t: 'quad', type: 'lead', w: 0.9 },
    { s: 'usa', t: 'semiconductor', type: 'control', w: 0.9, label: 'CHIPS Act + ASML' },
    { s: 'usa', t: 'ai', type: 'lead', w: 0.9, label: 'Frontier AI Leader' },
    { s: 'russia', t: 'oil', type: 'control', w: 0.9, label: 'Energy Weapon' },
    { s: 'russia', t: 'nato', type: 'conflict', w: 0.9, label: 'Ukraine War' },
    { s: 'russia', t: 'sco', type: 'member', w: 0.7 },
    { s: 'russia', t: 'brics', type: 'member', w: 0.7 },
    { s: 'quad', t: 'japan', type: 'member', w: 0.8 },
    { s: 'quad', t: 'australia', type: 'member', w: 0.8 },
    { s: 'eu', t: 'nato', type: 'overlap', w: 0.7 },
    { s: 'eu', t: 'russia', type: 'conflict', w: 0.7, label: 'Sanctions Regime' },
    { s: 'eu', t: 'ai', type: 'regulate', w: 0.7, label: 'AI Act 2024' },
    { s: 'ai', t: 'semiconductor', type: 'require', w: 0.95, label: 'Requires Advanced Chips' },
    { s: 'ai', t: 'quantum', type: 'synergy', w: 0.6 },
    { s: 'ai', t: 'cyber', type: 'amplify', w: 0.75 },
    { s: 'climate', t: 'food', type: 'threat', w: 0.8, label: 'Yield Gap Risk' },
    { s: 'climate', t: 'migration', type: 'cause', w: 0.75, label: 'Climate Displacement' },
    { s: 'oil', t: 'climate', type: 'impact', w: 0.8, label: 'Carbon Emissions' },
    { s: 'japan', t: 'semiconductor', type: 'invest', w: 0.7, label: 'TSMC Japan Fab' },
    { s: 'australia', t: 'rare_earth', type: 'supply', w: 0.7, label: 'Strategic Deposits' },
    { s: 'bri', t: 'pakistan', type: 'project', w: 0.85, label: 'CPEC Flagship' },
    { s: 'quantum', t: 'cyber', type: 'threat', w: 0.7, label: 'Q-Day Cryptobreak' },
];

// ── Live Feed Configuration ───────────────────────────────────────────────
const DOMAIN_QUERIES = {
    geopolitics: 'geopolitics OR diplomacy OR foreign policy OR border security OR treaty',
    economics: 'economy OR trade OR inflation OR gdp OR sanctions OR manufacturing',
    defense: 'defense OR military OR armed forces OR naval exercise OR missile OR cyber warfare',
    technology: 'ai OR semiconductor OR quantum OR space technology OR cyber security startup',
    climate: 'climate change OR extreme weather OR renewable energy OR emissions OR adaptation',
    society: 'public health OR education policy OR migration OR jobs OR social welfare',
};

const DOMAIN_KEYWORDS = {
    geopolitics: ['diplomacy', 'border', 'embassy', 'treaty', 'foreign policy', 'summit', 'minister'],
    economics: ['economy', 'trade', 'gdp', 'inflation', 'market', 'fiscal', 'rupee', 'export', 'import'],
    defense: ['defense', 'military', 'army', 'navy', 'air force', 'missile', 'drone', 'war', 'cyberattack'],
    technology: ['ai', 'artificial intelligence', 'llm', 'chip', 'semiconductor', 'quantum', 'startup', 'software'],
    climate: ['climate', 'emissions', 'renewable', 'solar', 'heatwave', 'flood', 'drought', 'weather'],
    society: ['education', 'health', 'hospital', 'jobs', 'welfare', 'migration', 'demography', 'culture'],
};

const SEVERITY_KEYWORDS = {
    CRIT: ['war', 'invasion', 'terror', 'critical', 'missile strike', 'cyberattack', 'outbreak'],
    HIGH: ['attack', 'sanction', 'conflict', 'crisis', 'risk', 'threat', 'alert'],
    MED: ['talks', 'deal', 'policy', 'update', 'review', 'summit', 'exercise'],
};

const SOURCE_TRUST_BASE = {
    reuters: 92,
    bloomberg: 90,
    associatedpress: 88,
    bbc: 87,
    theguardian: 84,
    gnews: 78,
    reddit: 58,
};

const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

const scoreDomain = (text, domain) => {
    const keywords = DOMAIN_KEYWORDS[domain] || [];
    return keywords.reduce((score, keyword) => score + (text.includes(keyword) ? 1 : 0), 0);
};

const classifyDomain = (article) => {
    const text = `${article?.title || ''} ${article?.description || ''} ${article?.content || ''}`.toLowerCase();
    let bestDomain = 'unknown';
    let bestScore = 0;

    Object.keys(DOMAIN_KEYWORDS).forEach((domain) => {
        const score = scoreDomain(text, domain);
        if (score > bestScore) {
            bestScore = score;
            bestDomain = domain;
        }
    });

    return { domain: bestDomain, confidence: bestScore, text };
};

const inferSeverity = (text) => {
    if (SEVERITY_KEYWORDS.CRIT.some((term) => text.includes(term))) return 'CRIT';
    if (SEVERITY_KEYWORDS.HIGH.some((term) => text.includes(term))) return 'HIGH';
    if (SEVERITY_KEYWORDS.MED.some((term) => text.includes(term))) return 'MED';
    return 'LOW';
};

const dedupeFeeds = (items) => {
    const seen = new Set();
    return items.filter((item) => {
        const key = (item.url || item.text || '').toLowerCase().trim();
        if (!key || seen.has(key)) return false;
        seen.add(key);
        return true;
    });
};

const sortFeeds = (items) => [...items].sort((a, b) => new Date(b.time) - new Date(a.time));

const inferTrustScore = (sourceName, confidence) => {
    const normalized = (sourceName || '').toLowerCase().replace(/\s+/g, '');
    const base = SOURCE_TRUST_BASE[normalized] || 72;
    return clamp(base + confidence * 3, 45, 98);
};

const mapArticleToFeed = (article, requestedDomain) => {
    const { domain: predictedDomain, confidence, text } = classifyDomain(article);
    const requestedDomainScore = scoreDomain(text, requestedDomain);
    const isRelevantToRequested = requestedDomainScore > 0 || predictedDomain === requestedDomain;
    const finalDomain = predictedDomain === 'unknown' ? requestedDomain : predictedDomain;
    const source = article.source?.name || 'Unknown';

    return {
        sev: inferSeverity(text),
        text: article.title,
        domain: finalDomain,
        requestedDomain,
        confidence,
        isRelevantToRequested,
        time: new Date(article.publishedAt || Date.now()),
        source,
        trustScore: inferTrustScore(source, confidence),
        url: article.url || '',
    };
};

const EDGE_COLOR = (type) => ({
    alliance: '#00C8FF', conflict: '#FF3355', rivalry: '#FF8C00', tension: '#FF8C00',
    trade: '#FFCC00', member: '#6090C0', invest: '#B06BFF', lead: '#00E882',
    dominate: '#FF3355', control: '#FF8C00', require: '#B06BFF', threat: '#FF3355',
    cause: '#FF8C00', impact: '#FF8C00', amplify: '#B06BFF', synergy: '#00E882',
    commit: '#00E882', regulate: '#B06BFF', overlap: '#6090C0', interest: '#FFCC00',
    supply: '#00E882', project: '#FFCC00', depend: '#FF8C00',
}[type] || '#1A4A6A');



export default function OntologyEngine() {
    const svgRef = useRef(null);
    const [selectedNode, setSelectedNode] = useState(null);
    const [activeDomain, setActiveDomain] = useState('all');
    const [feeds, setFeeds] = useState([]);
    const [stats, setStats] = useState({ updates: 0, threats: 7, intel: 247 });
    const pollingIndexRef = useRef(0);

    useEffect(() => {
        let mounted = true;

        const loadInitialFeeds = async () => {
            const all = [];
            const entries = Object.entries(DOMAIN_QUERIES);
            for (let i = 0; i < entries.length; i++) {
                const [domain, domainQuery] = entries[i];
                try {
                    // Stagger calls by 600ms to avoid quota flooding
                    if (i > 0) await new Promise(r => setTimeout(r, 600));
                    const data = await searchNews(domainQuery, { max: 8 });
                    if (data?.articles?.length) {
                        const mapped = data.articles
                            .map((article) => mapArticleToFeed(article, domain))
                            .filter((feedItem) => feedItem.isRelevantToRequested)
                            .slice(0, 4);
                        all.push(...mapped);
                    }
                } catch (e) {
                    console.error(`Failed to load feeds for ${domain}`, e);
                }
            }
            // Fallback: if all domain queries returned empty, try one broad query
            if (all.length === 0) {
                try {
                    const data = await searchNews('india geopolitics defense economy technology climate', { max: 20 });
                    if (data?.articles?.length) {
                        const mapped = data.articles.map((article) => {
                            const { domain: predicted } = classifyDomain(article);
                            const fallbackDomain = predicted === 'unknown' ? 'geopolitics' : predicted;
                            return mapArticleToFeed(article, fallbackDomain);
                        });
                        all.push(...mapped);
                    }
                } catch (e) {
                    console.error('Fallback feed query failed', e);
                }
            }
            if (mounted) {
                setFeeds(sortFeeds(dedupeFeeds(all)).slice(0, 24));
            }
        };

        loadInitialFeeds();

        return () => {
            mounted = false;
        }
    }, []);

    useEffect(() => {
        let mounted = true;
        const domains = Object.keys(DOMAIN_QUERIES);

        const pollLatestFeed = async () => {
            const domain = activeDomain === 'all'
                ? domains[pollingIndexRef.current % domains.length]
                : activeDomain;
            pollingIndexRef.current += 1;

            try {
                const data = await searchNews(DOMAIN_QUERIES[domain], { max: 6 });
                if (!mounted || !data?.articles?.length) return;

                const candidates = data.articles
                    .map((article) => mapArticleToFeed(article, domain))
                    .filter((feedItem) => feedItem.isRelevantToRequested);

                if (!candidates.length) return;

                const freshest = sortFeeds(candidates)[0];
                setFeeds((prev) => sortFeeds(dedupeFeeds([{ ...freshest, fresh: true }, ...prev])).slice(0, 20));
                setStats((prev) => ({ ...prev, updates: prev.updates + 1 }));
            } catch (e) {
                // Ignore silent errors on interval
            }
        };

        const id = setInterval(pollLatestFeed, 30000); // 30s to avoid rate limits
        return () => {
            mounted = false;
            clearInterval(id);
        };
    }, [activeDomain]);

    useEffect(() => {
        if (!feeds.length) return;
        const threats = feeds.filter((item) => item.sev === 'CRIT' || item.sev === 'HIGH').length;
        setStats((prev) => ({ ...prev, threats, intel: feeds.length }));
    }, [feeds]);

    useEffect(() => {
        if (!svgRef.current) return;
        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();
        const w = svgRef.current.clientWidth || 600;
        const h = svgRef.current.clientHeight || 500;
        const filtNodes = activeDomain === 'all' ? NODES : NODES.filter(n => n.domain === activeDomain);
        const filtIds = new Set(filtNodes.map(n => n.id));
        const filtEdges = EDGES.filter(e => filtIds.has(e.s) && filtIds.has(e.t));
        const nodes = filtNodes.map(n => ({ ...n }));
        const links = filtEdges.map(e => ({ ...e, source: e.s, target: e.t }));

        const g0 = svg.append('g');
        const gs = 48;
        for (let x = 0; x <= w; x += gs)
            g0.append('line').attr('x1', x).attr('y1', 0).attr('x2', x).attr('y2', h).attr('stroke', '#e2e8f0').attr('stroke-width', 0.5);
        for (let y = 0; y <= h; y += gs)
            g0.append('line').attr('x1', 0).attr('y1', y).attr('x2', w).attr('y2', y).attr('stroke', '#e2e8f0').attr('stroke-width', 0.5);

        const linkG = svg.append('g');
        const link = linkG.selectAll('line').data(links).join('line')
            .attr('stroke', d => EDGE_COLOR(d.type))
            .attr('stroke-opacity', 0.35)
            .attr('stroke-width', d => d.w * 1.8);

        const linkLabelG = svg.append('g');
        const linkLabel = linkLabelG.selectAll('text').data(links.filter(d => d.label)).join('text')
            .attr('fill', d => EDGE_COLOR(d.type))
            .attr('font-size', '10px')
            .attr('text-anchor', 'middle')
            .attr('opacity', 0.7)
            .text(d => d.label || '');

        const nodeG = svg.append('g');
        const nodeEl = nodeG.selectAll('g').data(nodes).join('g')
            .attr('cursor', 'pointer')
            .call(d3.drag()
                .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
                .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
                .on('end', (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
            )
            .on('click', (e, d) => { e.stopPropagation(); setSelectedNode(prev => prev?.id === d.id ? null : d); });

        nodeEl.filter(d => d.id === 'india').append('circle')
            .attr('r', d => d.r + 14).attr('fill', 'none')
            .attr('stroke', C.saffron).attr('stroke-width', 2)
            .attr('stroke-dasharray', '5,4').attr('stroke-opacity', 0.6);

        nodeEl.append('circle').attr('class', 'main-circle')
            .attr('r', d => d.r)
            .attr('fill', d => `rgba(${hexRgb(DOMAINS[d.domain]?.color || C.primary)}, 0.12)`)
            .attr('stroke', d => DOMAINS[d.domain]?.color || C.primary)
            .attr('stroke-width', d => d.id === 'india' ? 2.5 : 1.5);

        nodeEl.append('text')
            .attr('text-anchor', 'middle').attr('dominant-baseline', 'central')
            .attr('font-size', d => `${Math.max(10, d.r * 0.75)}px`)
            .text(d => DOMAINS[d.domain]?.icon || '●');

        nodeEl.append('text')
            .attr('text-anchor', 'middle').attr('dy', d => d.r + 15)
            .attr('fill', d => DOMAINS[d.domain]?.color || C.primary)
            .attr('font-size', d => d.r >= 20 ? '10.5px' : '9px')
            .attr('font-weight', d => d.id === 'india' ? 'bold' : 'normal')
            .attr('opacity', 0.95).text(d => d.label);

        const sim = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(d => 90 + (1 - d.w) * 70))
            .force('charge', d3.forceManyBody().strength(-450))
            .force('center', d3.forceCenter(w / 2, h / 2))
            .force('collision', d3.forceCollide().radius(d => d.r + 22))
            .on('tick', () => {
                link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
                linkLabel.attr('x', d => (d.source.x + d.target.x) / 2).attr('y', d => (d.source.y + d.target.y) / 2);
                nodeEl.attr('transform', d => `translate(${d.x},${d.y})`);
            });

        svg.on('click', () => setSelectedNode(null));
        return () => sim.stop();
    }, [activeDomain]);

    useEffect(() => {
        if (!svgRef.current) return;
        d3.select(svgRef.current).selectAll('.main-circle')
            .attr('fill', d => {
                const base = hexRgb(DOMAINS[d.domain]?.color || C.primary);
                return `rgba(${base}, ${selectedNode?.id === d.id ? 0.35 : 0.1})`;
            })
            .attr('stroke-width', d => selectedNode?.id === d.id ? 3.5 : (d.id === 'india' ? 2.8 : 1.8));
    }, [selectedNode]);


    const visibleFeeds = activeDomain === 'all' ? feeds : feeds.filter(f => f.domain === activeDomain);

    return (
        <div style={{
            width: '100%', height: '100%',
            display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}>
            {/* HEADER — Government style: solid bar */}
            <div style={{
                flexShrink: 0, minHeight: 52,
                background: C.primary, color: C.white,
                display: 'flex', alignItems: 'center', gap: 16, padding: '0 20px',
            }}>
                <div style={{ minWidth: 220, flexShrink: 0 }}>
                    <div style={{ fontSize: 15, fontWeight: 700, }}>
                        Global Ontology Engine
                    </div>
                    <div style={{ fontSize: 12, opacity: 0.9 }}>
                        Strategic Intelligence System v4.2
                    </div>
                </div>

                <div style={{ display: 'flex', gap: 6, flex: 1, justifyContent: 'center', flexWrap: 'wrap' }}>
                    {[['all', 'All Domains', C.white], ...Object.entries(DOMAINS).map(([k, v]) => [k, `${v.icon} ${v.label}`, 'rgba(255,255,255,0.9)'])].map(([key, label, color]) => {
                        const isActive = key === 'all' ? activeDomain === 'all' : activeDomain === key;
                        return (
                            <button key={key}
                                onClick={() => setActiveDomain(isActive && key !== 'all' ? 'all' : key)}
                                style={{
                                    padding: '6px 12px', fontSize: 13,
                                    background: isActive ? 'rgba(255,255,255,0.2)' : 'transparent',
                                    border: `1px solid ${isActive ? C.white : 'rgba(255,255,255,0.4)'}`,
                                    color: C.white, borderRadius: 4,
                                }}>
                                {label}
                            </button>
                        );
                    })}
                </div>

                <div style={{ display: 'flex', gap: 20, flexShrink: 0, alignItems: 'center' }}>
                    {[
                        { l: 'Entities', v: activeDomain === 'all' ? NODES.length : NODES.filter(n => n.domain === activeDomain).length },
                        { l: 'Relations', v: EDGES.length },
                        { l: 'Updates', v: stats.updates },
                        { l: 'Alerts', v: stats.threats },
                    ].map(s => (
                        <div key={s.l} style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: 16, fontWeight: 700 }}>{s.v}</div>
                            <div style={{ fontSize: 11, opacity: 0.85 }}>{s.l}</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* BODY */}
            <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 }}>
                {/* LEFT: Live Intel Feed */}
                <div style={{
                    width: 260, flexShrink: 0,
                    background: C.panel, borderRight: `1px solid ${C.border}`,
                    display: 'flex', flexDirection: 'column', overflow: 'hidden',
                }}>
                    <div style={{
                        padding: '10px 14px', borderBottom: `2px solid ${C.primary}`,
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        background: '#f8fafc',
                    }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: C.text }}>Live Intel Feed</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div style={{ width: 6, height: 6, borderRadius: '50%', background: C.green }} />
                            <span style={{ fontSize: 11, color: C.textMuted }}>Active</span>
                        </div>
                    </div>
                    <div style={{ overflowY: 'auto', flex: 1, padding: 10 }}>
                        {visibleFeeds.map((f, i) => (
                            <div key={i} className={f.fresh ? 'feed-new' : ''} style={{
                                marginBottom: 8, padding: '10px 12px',
                                background: f.fresh ? `rgba(${hexRgb(DOMAINS[f.domain]?.color || C.primary)}, 0.06)` : C.bg,
                                border: `1px solid ${C.border}`,
                                borderLeft: `4px solid ${SEV[f.sev] || C.text}`,
                                borderRadius: 4,
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                    <span style={{ fontSize: 10, color: SEV[f.sev], fontWeight: 600 }}>{f.sev}</span>
                                    <span style={{ fontSize: 10, color: C.textMuted }}>{DOMAINS[f.domain]?.short}</span>
                                </div>
                                <div style={{ fontSize: 12, color: C.text, lineHeight: 1.5 }}>{f.text}</div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, fontSize: 10, color: C.textMuted }}>
                                    <span>{f.source || 'Unknown source'}</span>
                                    <span>Trust {f.trustScore || 0}</span>
                                </div>
                                <div style={{ fontSize: 11, color: C.textMuted, marginTop: 4 }}>{f.time?.toLocaleTimeString?.() || '-'}</div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* CENTER: Knowledge Graph */}
                <div style={{ flex: 1, position: 'relative', overflow: 'hidden', background: C.bg }}>
                    <svg ref={svgRef} style={{ width: '100%', height: '100%', display: 'block' }} />
                    <div style={{ position: 'absolute', top: 12, left: 12, fontSize: 11, color: C.textMuted, zIndex: 2 }}>
                        Drag nodes · Click to analyze
                    </div>
                    <div style={{
                        position: 'absolute', top: 12, right: 12, zIndex: 2,
                        display: 'flex', flexDirection: 'column', gap: 4,
                        background: C.panel, padding: '10px 12px',
                        border: `1px solid ${C.border}`, borderRadius: 4,
                        boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                    }}>
                        {Object.entries(DOMAINS).map(([k, v]) => (
                            <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <div style={{ width: 8, height: 8, borderRadius: '50%', background: v.color }} />
                                <span style={{ fontSize: 11, color: C.text }}>{v.label}</span>
                            </div>
                        ))}
                    </div>
                    <div style={{
                        position: 'absolute', bottom: 12, left: '50%', transform: 'translateX(-50%)',
                        fontSize: 11, color: C.textMuted, zIndex: 2,
                        background: C.panel, padding: '6px 16px',
                        border: `1px solid ${C.border}`, borderRadius: 4,
                    }}>
                        {NODES.length} entities · {EDGES.length} relationships
                    </div>
                </div>

                {/* RIGHT: Entity Intel + AI Query */}
                <div style={{
                    width: 305, flexShrink: 0,
                    background: C.panel, borderLeft: `1px solid ${C.border}`,
                    display: 'flex', flexDirection: 'column', overflow: 'hidden',
                }}>
                    <div style={{ flexShrink: 0, borderBottom: `1px solid ${C.border}` }}>
                        {selectedNode ? (
                            <>
                                <div style={{
                                    padding: '10px 14px',
                                    background: `rgba(${hexRgb(DOMAINS[selectedNode.domain]?.color || C.primary)}, 0.08)`,
                                    borderBottom: `1px solid ${C.border}`,
                                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <span style={{ fontSize: 20 }}>{DOMAINS[selectedNode.domain]?.icon}</span>
                                        <div>
                                            <div style={{ fontWeight: 700, fontSize: 14, color: C.text, lineHeight: 1.1 }}>
                                                {selectedNode.label}
                                            </div>
                                            <div style={{ fontSize: 11, color: C.textMuted }}>
                                                {DOMAINS[selectedNode.domain]?.label}
                                            </div>
                                        </div>
                                    </div>
                                    <div style={{
                                        padding: '3px 8px', fontSize: 11, fontWeight: 600, borderRadius: 4,
                                        border: `1px solid ${selectedNode.risk === 'Critical' ? C.red : selectedNode.risk === 'High' ? C.orange : C.gold}`,
                                        color: selectedNode.risk === 'Critical' ? C.red : selectedNode.risk === 'High' ? C.orange : C.gold,
                                    }}>{selectedNode.risk}</div>
                                </div>
                                <div style={{ padding: '12px 14px', maxHeight: 220, overflowY: 'auto' }}>
                                    <div style={{ fontSize: 12, color: C.text, lineHeight: 1.6, marginBottom: 12 }}>
                                        {selectedNode.intel}
                                    </div>
                                    <div style={{ marginBottom: 12 }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                            <span style={{ fontSize: 11, color: C.textMuted }}>Power Index</span>
                                            <span style={{ fontSize: 12, fontWeight: 600, color: C.primary }}>{selectedNode.power} / 100</span>
                                        </div>
                                        <div style={{ height: 3, background: C.borderSoft, borderRadius: 2 }}>
                                            <div style={{
                                                height: '100%', borderRadius: 2, width: `${selectedNode.power}%`,
                                                background: `linear-gradient(90deg, ${DOMAINS[selectedNode.domain]?.color || C.primary}, ${C.primary})`,
                                                transition: 'width .6s ease',
                                            }} />
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 10 }}>
                                        {(selectedNode.tags || []).map(t => (
                                            <span key={t} style={{
                                                fontSize: 11, padding: '4px 8px',
                                                border: `1px solid ${C.border}`, color: C.text, borderRadius: 4,
                                            }}>{t}</span>
                                        ))}
                                    </div>
                                    <div style={{ fontSize: 11, fontWeight: 600, color: C.text, marginBottom: 6 }}>Connected Entities</div>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                        {EDGES.filter(e => e.s === selectedNode.id || e.t === selectedNode.id).slice(0, 10).map(e => {
                                            const oid = e.s === selectedNode.id ? e.t : e.s;
                                            const other = NODES.find(n => n.id === oid);
                                            if (!other) return null;
                                            return (
                                                <button key={oid} onClick={() => setSelectedNode(other)} style={{
                                                    fontSize: 11, padding: '4px 8px',
                                                    background: `rgba(${hexRgb(DOMAINS[other.domain]?.color || C.primary)}, 0.1)`,
                                                    border: `1px solid ${C.border}`,
                                                    color: DOMAINS[other.domain]?.color || C.primary,
                                                    borderRadius: 4,
                                                }}>{other.label}</button>
                                            );
                                        })}
                                    </div>
                                </div>
                            </>
                        ) : (
                            <div style={{ padding: '24px 14px', textAlign: 'center', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                                <div style={{ fontSize: 32, opacity: 0.4, marginBottom: 10 }}>🕸️</div>
                                <div style={{ fontSize: 12, color: C.textMuted, lineHeight: 1.7 }}>
                                    Click any node to view<br />entity intelligence brief
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}


