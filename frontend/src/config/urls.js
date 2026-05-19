/** API and observability URLs (Vite env in dev/prod, localhost fallbacks). */

export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const DOCS_URL = import.meta.env.VITE_DOCS_URL || `${API_BASE}/docs`;
export const PROMETHEUS_URL = import.meta.env.VITE_PROMETHEUS_URL || 'http://localhost:9090';
export const GRAFANA_URL = import.meta.env.VITE_GRAFANA_URL || 'http://localhost:3000';
export const FLOWER_URL = import.meta.env.VITE_FLOWER_URL || 'http://localhost:5555';
