/**
 * Analysis Charts — Chart.js visualizations for competitive intelligence
 *
 * Provides three chart types:
 *  • RadarChart — Category coverage comparison (spider/radar)
 *  • BarChart   — Signal count + confidence side-by-side
 *  • DoughnutChart — Category distribution per company
 */

import { useMemo } from 'react';
import {
    Chart as ChartJS,
    RadialLinearScale,
    PointElement,
    LineElement,
    Filler,
    CategoryScale,
    LinearScale,
    BarElement,
    ArcElement,
    Tooltip,
    Legend,
} from 'chart.js';
import { Radar, Bar, Doughnut } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
    RadialLinearScale,
    PointElement,
    LineElement,
    Filler,
    CategoryScale,
    LinearScale,
    BarElement,
    ArcElement,
    Tooltip,
    Legend
);

/* ── Color palette (matches Analysis.jsx COLORS) ──────────── */
const CHART_COLORS = [
    { bg: 'rgba(46, 125, 50, 0.15)',  border: '#2E7D32',  solid: '#4ade80' },
    { bg: 'rgba(96, 165, 250, 0.15)', border: '#3b82f6',  solid: '#60a5fa' },
    { bg: 'rgba(167, 139, 250, 0.15)', border: '#8b5cf6', solid: '#a78bfa' },
];

const DOUGHNUT_PALETTE = [
    '#4ade80', '#60a5fa', '#a78bfa', '#fbbf24', '#f472b6',
    '#34d399', '#818cf8', '#fb923c', '#a3e635', '#e879f9',
];

/* ── Shared options ────────────────────────────────────────── */
const FONT_FAMILY = "'Inter', 'system-ui', sans-serif";

const COMMON_LEGEND = {
    position: 'bottom',
    labels: {
        font: { family: FONT_FAMILY, size: 12, weight: 500 },
        color: '#64748b',
        padding: 16,
        usePointStyle: true,
        pointStyleWidth: 10,
    },
};


/* ═════════════════════════════════════════════════════════════
   1. RADAR CHART — Category coverage comparison
   ═════════════════════════════════════════════════════════════ */

export function CategoryRadarChart({ comparisonData }) {
    const chartData = useMemo(() => {
        // Collect all categories across all companies
        const allCats = new Set();
        comparisonData.forEach(c => {
            (c.features || []).forEach(f => allCats.add(f.category || 'General'));
        });
        const labels = [...allCats].sort();
        if (labels.length < 3) return null; // Radar needs at least 3 axes

        const datasets = comparisonData.map((c, i) => {
            const catCounts = {};
            (c.features || []).forEach(f => {
                const cat = f.category || 'General';
                catCounts[cat] = (catCounts[cat] || 0) + 1;
            });
            return {
                label: c.label,
                data: labels.map(cat => catCounts[cat] || 0),
                backgroundColor: CHART_COLORS[i]?.bg || 'rgba(100,100,100,0.1)',
                borderColor: CHART_COLORS[i]?.border || '#666',
                borderWidth: 2,
                pointBackgroundColor: CHART_COLORS[i]?.border || '#666',
                pointRadius: 3,
                pointHoverRadius: 5,
            };
        });

        return { labels, datasets };
    }, [comparisonData]);

    if (!chartData) return null;

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: COMMON_LEGEND,
            tooltip: {
                backgroundColor: '#1e293b',
                titleFont: { family: FONT_FAMILY },
                bodyFont: { family: FONT_FAMILY },
                cornerRadius: 8,
                padding: 10,
            },
        },
        scales: {
            r: {
                beginAtZero: true,
                ticks: {
                    stepSize: 1,
                    font: { family: FONT_FAMILY, size: 10 },
                    color: '#94a3b8',
                    backdropColor: 'transparent',
                },
                pointLabels: {
                    font: { family: FONT_FAMILY, size: 11, weight: 500 },
                    color: '#475569',
                },
                grid: { color: 'rgba(148, 163, 184, 0.15)' },
                angleLines: { color: 'rgba(148, 163, 184, 0.15)' },
            },
        },
    };

    return (
        <div style={{ height: 340 }}>
            <Radar data={chartData} options={options} />
        </div>
    );
}


/* ═════════════════════════════════════════════════════════════
   2. BAR CHART — Signal count + avg confidence
   ═════════════════════════════════════════════════════════════ */

export function SignalBarChart({ comparisonData }) {
    const chartData = useMemo(() => {
        const labels = comparisonData.map(c => c.label);

        return {
            labels,
            datasets: [
                {
                    label: 'Total Signals',
                    data: comparisonData.map(c => c.features?.length || 0),
                    backgroundColor: CHART_COLORS[0].bg,
                    borderColor: CHART_COLORS[0].border,
                    borderWidth: 2,
                    borderRadius: 6,
                    barPercentage: 0.6,
                },
                {
                    label: 'Avg Confidence (%)',
                    data: comparisonData.map(c => {
                        const scores = (c.features || []).map(f => f.confidence_score).filter(Boolean);
                        return scores.length ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 100) : 0;
                    }),
                    backgroundColor: CHART_COLORS[1].bg,
                    borderColor: CHART_COLORS[1].border,
                    borderWidth: 2,
                    borderRadius: 6,
                    barPercentage: 0.6,
                },
            ],
        };
    }, [comparisonData]);

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: COMMON_LEGEND,
            tooltip: {
                backgroundColor: '#1e293b',
                titleFont: { family: FONT_FAMILY },
                bodyFont: { family: FONT_FAMILY },
                cornerRadius: 8,
                padding: 10,
            },
        },
        scales: {
            x: {
                grid: { display: false },
                ticks: {
                    font: { family: FONT_FAMILY, size: 12, weight: 600 },
                    color: '#475569',
                },
            },
            y: {
                beginAtZero: true,
                grid: { color: 'rgba(148, 163, 184, 0.1)' },
                ticks: {
                    font: { family: FONT_FAMILY, size: 11 },
                    color: '#94a3b8',
                },
            },
        },
    };

    return (
        <div style={{ height: 300 }}>
            <Bar data={chartData} options={options} />
        </div>
    );
}


/* ═════════════════════════════════════════════════════════════
   3. DOUGHNUT CHART — Category distribution per company
   ═════════════════════════════════════════════════════════════ */

export function CategoryDoughnutChart({ features, label }) {
    const chartData = useMemo(() => {
        if (!features?.length) return null;

        const counts = {};
        features.forEach(f => {
            const cat = f.category || 'General';
            counts[cat] = (counts[cat] || 0) + 1;
        });

        const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
        const labels = sorted.map(([cat]) => cat);
        const data = sorted.map(([, count]) => count);

        return {
            labels,
            datasets: [{
                data,
                backgroundColor: labels.map((_, i) => DOUGHNUT_PALETTE[i % DOUGHNUT_PALETTE.length]),
                borderColor: '#ffffff',
                borderWidth: 2,
                hoverOffset: 6,
            }],
        };
    }, [features]);

    if (!chartData) return null;

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '62%',
        plugins: {
            legend: {
                position: 'right',
                labels: {
                    font: { family: FONT_FAMILY, size: 11, weight: 500 },
                    color: '#64748b',
                    padding: 8,
                    usePointStyle: true,
                    pointStyleWidth: 8,
                },
            },
            tooltip: {
                backgroundColor: '#1e293b',
                titleFont: { family: FONT_FAMILY },
                bodyFont: { family: FONT_FAMILY },
                cornerRadius: 8,
                padding: 10,
                callbacks: {
                    label: (ctx) => ` ${ctx.label}: ${ctx.raw} signals`,
                },
            },
        },
    };

    return (
        <div style={{ height: 220 }}>
            <Doughnut data={chartData} options={options} />
        </div>
    );
}
