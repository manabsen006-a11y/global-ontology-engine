/* Government-style design tokens — clean, professional, institutional */

export const C = {
  bg: '#f8fafc',          // Brighter, softer background
  bgAlt: '#ffffff',
  panel: '#ffffff',
  surface: '#ffffff',
  border: '#cbd5e1',      // Softer borders
  borderSoft: '#f1f5f9',
  primary: '#0f172a',     // Deep authoritative blue/slate
  primaryHover: '#1e293b',
  primaryGlow: 'rgba(15, 23, 42, 0.05)', 
  saffron: '#ea580c',
  accent: '#2563eb',      // Trust blue
  gold: '#d97706',
  green: '#15803d',
  greenLight: '#22c55e',
  purple: '#6d28d9',
  red: '#dc2626',
  orange: '#ea580c',
  text: '#334155',        // Softer text
  textMid: '#64748b',
  textBright: '#0f172a',  // High contrast text
  textMuted: '#94a3b8',
  white: '#ffffff',
};

export const hexRgb = (h) => {
  const r = parseInt(h.slice(1, 3), 16);
  const g = parseInt(h.slice(3, 5), 16);
  const b = parseInt(h.slice(5, 7), 16);
  return `${r},${g},${b}`;
};

export const DOMAINS = {
  geopolitics: { label: 'Geopolitics', color: '#2563eb', icon: '🌐', short: 'GEO' },
  economics: { label: 'Economics', color: '#b45309', icon: '💹', short: 'ECO' },
  defense: { label: 'Defense', color: '#b91c1c', icon: '🛡️', short: 'DEF' },
  technology: { label: 'Technology', color: '#5b21b6', icon: '⚡', short: 'TECH' },
  climate: { label: 'Climate', color: '#166534', icon: '🌱', short: 'ENV' },
  society: { label: 'Society', color: '#c2410c', icon: '👥', short: 'SOC' },
};

export const SEV = {
  CRIT: '#b91c1c',
  HIGH: '#c2410c',
  MED: '#b45309',
  LOW: '#166534',
};
