/* ═══════════════════════════════════════════════════════════════════
   TOUR STEPS — All key pages covered
   ═══════════════════════════════════════════════════════════════════ */

export const TOUR_STEPS = [

  // ── 1. WELCOME ──────────────────────────────────────────────────
  {
    page: '/',
    target: '.overview-hero-surface',
    title: 'Welcome to Market Scout',
    description: 'Your AI-powered competitive intelligence platform. Let\'s walk through the key features — it only takes a minute.',
    position: 'bottom',
  },

  // ── 2. RUN ANALYSIS ─────────────────────────────────────────────
  {
    page: '/intelligence',
    target: '.intel-input-section',
    title: 'Run Intelligence Analysis',
    description: 'Enter any company name and click Analyze. Our 11-stage pipeline will scan sources, verify signals, and generate a full intelligence report.',
    position: 'bottom',
  },

  // ── 3. COMPARE ANALYSIS ─────────────────────────────────────────
  {
    page: '/analysis',
    target: '.page-header',
    title: 'Compare Analysis',
    description: 'Dive deeper into analysis results. Compare signals across companies and explore trends in their competitive landscape.',
    position: 'bottom',
  },

  // ── 4. REPORTS ──────────────────────────────────────────────────
  {
    page: '/reports',
    target: '.page-header',
    title: 'Intelligence Reports',
    description: 'All past analyses are stored here. Search by company name, view executive summaries, signal breakdowns, and download PDFs.',
    position: 'bottom',
  },

  // ── 5. WATCHLIST ────────────────────────────────────────────────
  {
    page: '/watchlist',
    target: '.page-header',
    title: 'Competitive Watchlist',
    description: 'Companies you analyze are tracked here. View signal strength, insights at a glance, and re-run analysis anytime.',
    position: 'bottom',
  },

  // ── 5. RAG — Upload & Query ─────────────────────────────────────
  {
    page: '/rag',
    target: '.rag-upload-card',
    title: 'Ask Your Report (AI Q&A)',
    description: 'Upload a generated report and interact with it using AI. Instead of reading long PDFs, ask direct questions and get instant answers.',
    position: 'bottom',
  },
  {
    page: '/rag',
    target: '.rag-input-row',
    title: 'Ask Questions Instantly',
    description: 'Type any question about the report. The system retrieves relevant sections and answers with source references.',
    position: 'top',
  },

  // ── 6. AUTOMATION ───────────────────────────────────────────────
  {
    page: '/schedule',
    target: '.page-header',
    title: 'Scheduled Automation',
    description: 'Set up automated analysis runs — schedule reports to generate at specific times and get them delivered to your inbox.',
    position: 'bottom',
  },

  // ── 7. MONITORING (Prometheus + Grafana) ────────────────────────
  {
    page: '/',
    target: '.sidebar-nav .nav-section:last-child',
    title: 'Monitoring & Observability',
    description: 'Prometheus tracks pipeline metrics and performance. Grafana provides real-time dashboards. Access both from these sidebar links.',
    position: 'right',
  },

  // ── 8. SETTINGS ─────────────────────────────────────────────────
  {
    page: '/',
    target: '#settings-btn',
    title: 'Settings',
    description: 'Customize analysis depth, confidence thresholds, report formats, watchlist behavior, and more. Preferences save automatically.',
    position: 'right',
  },

  // ── 9. HELP BUTTON ──────────────────────────────────────────────
  {
    page: '/',
    target: '.tour-help-btn',
    title: 'That\'s It!',
    description: 'You\'re all set. Click this "?" button anytime to replay this walkthrough. Happy analyzing!',
    position: 'bottom',
  },
];
