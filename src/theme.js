/* ═══════════════════════════════════════════════════════════
   THEME — Shared design tokens
   ═══════════════════════════════════════════════════════════ */

export const C = {
    bg: '#010C18',
    panel: '#020F1E',
    surface: '#031525',
    border: '#0C3A58',
    borderSoft: '#082A42',
    primary: '#00C8FF',
    primaryDim: '#004A6B',
    primaryGlow: 'rgba(0,200,255,0.15)',
    saffron: '#FF7040',
    gold: '#FFCC00',
    green: '#00E882',
    purple: '#B06BFF',
    red: '#FF3355',
    orange: '#FF8C00',
    text: '#4A8BAA',
    textMid: '#7BBAD5',
    textBright: '#C0E4F5',
    white: '#E8F8FF',
};

export const hexRgb = (h) => {
    const r = parseInt(h.slice(1, 3), 16);
    const g = parseInt(h.slice(3, 5), 16);
    const b = parseInt(h.slice(5, 7), 16);
    return `${r},${g},${b}`;
};

export const DOMAINS = {
    geopolitics: { label: 'Geopolitics', color: '#00C8FF', icon: '🌐', short: 'GEO' },
    economics: { label: 'Economics', color: '#FFCC00', icon: '💹', short: 'ECO' },
    defense: { label: 'Defense', color: '#FF3355', icon: '🛡️', short: 'DEF' },
    technology: { label: 'Technology', color: '#B06BFF', icon: '⚡', short: 'TECH' },
    climate: { label: 'Climate', color: '#00E882', icon: '🌱', short: 'ENV' },
    society: { label: 'Society', color: '#FF7040', icon: '👥', short: 'SOC' },
};

export const SEV = {
    CRIT: '#FF3355',
    HIGH: '#FF8C00',
    MED: '#FFCC00',
    LOW: '#00E882',
};
