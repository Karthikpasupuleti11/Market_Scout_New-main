import {
    HiOutlineSparkles,
    HiOutlineChartBar,
    HiOutlineDocumentText,
    HiOutlineClock,
    HiOutlineShieldCheck,
    HiOutlineChip,
    HiOutlineLightningBolt,
    HiOutlineSearch,
    HiOutlineDatabase,
    HiOutlineCheckCircle,
    HiOutlineGlobeAlt,
    HiOutlineCog,
    HiOutlineTrendingUp,
    HiOutlineCube,
    HiOutlineArrowRight,
    HiOutlineOfficeBuilding,
    HiOutlineDocumentReport,
    HiOutlineAnnotation
} from 'react-icons/hi';
import './About.css';

const capabilities = [
    {
        icon: <HiOutlineSparkles />,
        title: 'Intelligence Pipeline',
        text: 'Run automated market intelligence workflows to collect, process, and organize key company signals.'
    },
    {
        icon: <HiOutlineChartBar />,
        title: 'Analysis Workspace',
        text: 'Review structured insights, confidence cues, and trend-level interpretation for faster strategic decisions.'
    },
    {
        icon: <HiOutlineDocumentText />,
        title: 'Reporting Layer',
        text: 'Generate readable outputs and track findings in a consistent format that is easy to share with stakeholders.'
    },
    {
        icon: <HiOutlineClock />,
        title: 'Automation',
        text: 'Schedule recurring analysis runs and receive updates automatically without repeating manual work.'
    }
];

const principles = [
    'Clear intelligence workflow from collection to decision support',
    'Lightweight, readable interface optimized for daily monitoring',
    'Consistent data views for teams working across strategy and product',
    'Scalable structure for adding new market modules over time'
];

const flow = [
    {
        icon: <HiOutlineSearch />,
        title: 'Discover',
        text: 'Collect market signals from public sources and validate source quality before processing.'
    },
    {
        icon: <HiOutlineDatabase />,
        title: 'Structure',
        text: 'Normalize findings into comparable intelligence objects with categories, confidence, and context.'
    },
    {
        icon: <HiOutlineChartBar />,
        title: 'Analyze',
        text: 'Compare companies and timelines to identify patterns, strategic moves, and high-impact signals.'
    },
    {
        icon: <HiOutlineDocumentText />,
        title: 'Report',
        text: 'Generate clear executive-ready summaries with evidence, insights, and recommended focus areas.'
    },
    {
        icon: <HiOutlineClock />,
        title: 'Automate',
        text: 'Schedule recurring runs to maintain a living intelligence layer that stays up to date.'
    }
];

const valueProps = [
    {
        icon: <HiOutlineOfficeBuilding />,
        title: 'Enterprise-ready structure',
        text: 'Clear modules for intelligence, analysis, reporting, watchlist, and automation across teams.'
    },
    {
        icon: <HiOutlineDocumentReport />,
        title: 'Decision-grade reporting',
        text: 'Evidence-backed summaries with confidence context to support product and strategy decisions.'
    },
    {
        icon: <HiOutlineAnnotation />,
        title: 'Operational clarity',
        text: 'Consistent UI patterns and workflows reduce friction for daily intelligence monitoring.'
    }
];

export default function About() {
    return (
        <div className="about-page fade-in">
            <div className="page-header">
                <h1>About Market Scout</h1>
                <p>
                    Market Scout is an intelligence platform designed to help teams monitor companies, analyze movement in the
                    market, and turn raw updates into practical insights.
                </p>
            </div>

            <section className="about-visual-strip fade-in-up">
                <div className="about-orb orb-1" />
                <div className="about-orb orb-2" />
                <div className="about-orb orb-3" />
                <div className="about-strip-content">
                    <h2>Market Intelligence. Structured for action.</h2>
                    <p>
                        From discovery to reporting, every stage is designed to turn noisy market activity into usable,
                        decision-ready intelligence.
                    </p>
                </div>
            </section>

            <section className="card about-hero-card fade-in-up stagger">
                <div className="about-hero-text">
                    <div className="about-hero-tags">
                        <span><HiOutlineGlobeAlt /> Live market signals</span>
                        <span><HiOutlineTrendingUp /> Strategy-grade insights</span>
                    </div>
                    <h2>Built for intelligence teams that move fast</h2>
                    <p>
                        Market Scout combines monitoring, analysis, reporting, and automation into a single operating layer for
                        product, strategy, and leadership teams.
                    </p>
                </div>
                <div className="about-hero-stats">
                    <div className="about-stat">
                        <i><HiOutlineCube /></i>
                        <span>Core modules</span>
                        <strong>6</strong>
                    </div>
                    <div className="about-stat">
                        <i><HiOutlineCog /></i>
                        <span>Pipeline depth</span>
                        <strong>11 stages</strong>
                    </div>
                    <div className="about-stat">
                        <i><HiOutlineClock /></i>
                        <span>Automation</span>
                        <strong>Recurring schedules</strong>
                    </div>
                </div>
            </section>

            <section className="about-value-grid">
                {valueProps.map((item, idx) => (
                    <article className="card about-value-card fade-in-up" key={item.title} style={{ animationDelay: `${idx * 0.08}s` }}>
                        <div className="about-value-icon">{item.icon}</div>
                        <h3>{item.title}</h3>
                        <p>{item.text}</p>
                    </article>
                ))}
            </section>

            <section className="card about-flow-card fade-in-up">
                <div className="about-section-head">
                    <h3>
                        <HiOutlineLightningBolt />
                        Intelligence flow
                    </h3>
                    <p>How information moves from raw signal to decision-ready output.</p>
                </div>
                <div className="about-flow-track">
                    {flow.map((step, i) => (
                        <article className="flow-step" key={step.title} style={{ animationDelay: `${i * 0.08}s` }}>
                            <div className="flow-step-icon">{step.icon}</div>
                            <div className="flow-step-content">
                                <div className="flow-step-title-row">
                                    <span className="flow-step-index">{String(i + 1).padStart(2, '0')}</span>
                                    <h4>{step.title}</h4>
                                </div>
                                <p>{step.text}</p>
                            </div>
                            <HiOutlineArrowRight className="flow-step-arrow" />
                            {i < flow.length - 1 && <span className="flow-link" />}
                        </article>
                    ))}
                </div>
            </section>

            <section className="about-capabilities">
                {capabilities.map((item, index) => (
                    <article className="card capability-card fade-in-up" key={item.title} style={{ animationDelay: `${0.06 * index}s` }}>
                        <div className="capability-icon">{item.icon}</div>
                        <h3>{item.title}</h3>
                        <p>{item.text}</p>
                        <div className="capability-foot">
                            <span>Core capability</span>
                            <HiOutlineArrowRight />
                        </div>
                    </article>
                ))}
            </section>

            <section className="card about-details-card fade-in-up">
                <div className="about-detail-block">
                    <h3>
                        <HiOutlineShieldCheck />
                        Product principles
                    </h3>
                    <ul>
                        {principles.map((point) => (
                            <li key={point}>{point}</li>
                        ))}
                    </ul>
                </div>

                <div className="about-detail-block">
                    <h3>
                        <HiOutlineChip />
                        Platform snapshot
                    </h3>
                    <p>
                        Built as a modular intelligence dashboard with dedicated pages for overview, pipeline execution, analysis,
                        reports, watchlist tracking, and scheduled automation.
                    </p>
                    <p>
                        Version: <strong>v2.0</strong>
                    </p>
                    <div className="about-trust-row">
                        <span><HiOutlineCheckCircle /> Evidence-backed insights</span>
                        <span><HiOutlineCheckCircle /> Cross-page consistency</span>
                    </div>
                </div>
            </section>
        </div>
    );
}
