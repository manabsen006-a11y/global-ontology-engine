/**
 * Intel Nexus API Service
 * Calls backend correlation engine endpoints.
 */
const INTEL_BASE = '/api/v1/intel';

async function fetchIntelApi(path) {
  const url = `${INTEL_BASE}${path}`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.error || `Intel API error: ${res.status}`);
  }
  return res.json();
}

export async function fetchCorrelations() {
  return fetchIntelApi('/correlations');
}

export async function fetchSignals() {
  return fetchIntelApi('/signals');
}
