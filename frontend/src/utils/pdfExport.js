/**
 * generateReportPDF
 *
 * Builds a professionally formatted A4 PDF from a report object using
 * jsPDF's built-in text API (no canvas capture). This gives crisp,
 * searchable text with perfect layout control.
 *
 * @param {Object} report  – the report object from the API response
 * @param {string} companyName – fallback company name
 */
import jsPDF from 'jspdf';

// ── Palette ───────────────────────────────────────────────────────────
const COLORS = {
    brand:       [46,  125, 50],    // app accent green
    brandDark:   [27,  94,  32],
    brandSoft:   [232, 245, 233],
    dark:        [15,  23,  42],    // slate-900
    heading:     [30,  41,  59],    // slate-800
    body:        [71,  85,  105],   // slate-600
    muted:       [148, 163, 184],   // slate-400
    success:     [34,  197, 94],    // green-500
    warning:     [234, 179, 8],     // yellow-500
    danger:      [239, 68,  68],    // red-500
    white:       [255, 255, 255],
    rule:        [226, 232, 240],   // slate-200
    banner:      [241, 248, 241],   // green-50
    bannerBorder:[187, 229, 192],   // green-200
    featureBg:   [248, 250, 252],   // slate-50
};

// ── Layout constants (mm) ─────────────────────────────────────────────
const MARGIN  = 18;
const PW      = 210;          // A4 width
const CONTENT = PW - MARGIN * 2;  // usable width

// ── Helper: set fill + text colour ───────────────────────────────────
function rgb(doc, [r, g, b]) { doc.setTextColor(r, g, b); }
function fill(doc, [r, g, b]) { doc.setFillColor(r, g, b); }
function stroke(doc, [r, g, b]) { doc.setDrawColor(r, g, b); }

// ── Helper: wrapped text → returns new Y ─────────────────────────────
function text(doc, str, x, y, opts = {}) {
    doc.text(String(str || ''), x, y, { maxWidth: opts.maxWidth || CONTENT, ...opts });
}

function normalizeParagraph(str) {
    return String(str || '').replace(/\s+/g, ' ').trim();
}

// ── Helper: draw a horizontal rule ───────────────────────────────────
function rule(doc, y, colour = COLORS.rule) {
    stroke(doc, colour);
    doc.setLineWidth(0.3);
    doc.line(MARGIN, y, PW - MARGIN, y);
}

// ── Helper: check if new page needed ─────────────────────────────────
function ensureSpace(doc, y, needed, addPage) {
    if (y + needed > 275) { addPage(); return 20; }
    return y;
}

// ── Confidence badge colour ───────────────────────────────────────────
function confColour(score) {
    if (score >= 0.7) return COLORS.success;
    if (score >= 0.4) return COLORS.warning;
    return COLORS.danger;
}

// ── Main export ───────────────────────────────────────────────────────
export function generateReportPDF(report, companyFallback = '') {
    const doc = new jsPDF({ unit: 'mm', format: 'a4', compress: true });

    const companyName   = report.company_name || companyFallback || 'Company';
    const generatedAt   = report.generated_at
        ? new Date(report.generated_at).toLocaleString()
        : new Date().toLocaleString();
    const features      = Array.isArray(report.features) ? report.features : [];
    const sources       = Array.isArray(report.all_sources) ? report.all_sources : [];
    const totalSources  = report.total_sources_analysed ?? report.total_sources ?? sources.length;
    const totalFeatures = report.total_features_verified ?? report.total_features ?? features.length;
    const avgConfidence = features.length
        ? features
            .map(f => f.confidence_score ?? f.confidence)
            .filter(s => s != null)
            .reduce((a, b, _, arr) => a + b / arr.length, 0)
        : 0;

    let pageNum = 1;
    const addPage = () => {
        doc.addPage();
        pageNum++;
        drawPageFooter(doc, pageNum, companyName);
    };

    // ── Cover / Title Block ───────────────────────────────────────────
    fill(doc, COLORS.brand);
    doc.rect(0, 0, PW, 52, 'F');
    fill(doc, COLORS.brandDark);
    doc.rect(0, 0, PW, 7, 'F');

    // Watermark label
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(7);
    rgb(doc, COLORS.brandSoft);
    text(doc, 'MARKET INTELLIGENCE SCOUT', MARGIN, 12);

    // Company name
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(22);
    rgb(doc, COLORS.white);
    // Truncate long names
    const displayName = companyName.length > 30
        ? companyName.slice(0, 28) + '…'
        : companyName;
    text(doc, displayName, MARGIN, 28);

    // Subtitle
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    rgb(doc, COLORS.brandSoft);
    text(doc, 'Intelligence Report  |  ' + generatedAt, MARGIN, 38);

    // Stats strip
    fill(doc, COLORS.banner);
    stroke(doc, COLORS.bannerBorder);
    doc.setLineWidth(0.3);
    doc.rect(0, 52, PW, 18, 'FD');

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    rgb(doc, COLORS.brand);
    const stats = [
        `${totalFeatures} Features Verified`,
        `${totalSources} Sources Analysed`,
        `${Math.round(avgConfidence * 100)}% Avg Confidence`,
    ];
    stats.forEach((s, i) => text(doc, s, MARGIN + i * 58, 63));

    let y = 82;

    // ── Executive Summary ─────────────────────────────────────────────
    if (report.executive_summary) {
        // Section label
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(11);
        rgb(doc, COLORS.brand);
        text(doc, 'EXECUTIVE SUMMARY', MARGIN, y);
        y += 2;
        rule(doc, y, COLORS.brand);
        y += 6;

        doc.setFont('helvetica', 'normal');
        doc.setFontSize(9.5);
        rgb(doc, COLORS.body);

        const summaryLines = doc.splitTextToSize(report.executive_summary, CONTENT);
        summaryLines.forEach(line => {
            y = ensureSpace(doc, y, 6, addPage);
            text(doc, line, MARGIN, y);
            y += 5.5;
        });
        y += 4;
    }

    // ── Features ──────────────────────────────────────────────────────
    if (features.length > 0) {
        y = ensureSpace(doc, y, 20, addPage);

        doc.setFont('helvetica', 'bold');
        doc.setFontSize(11);
        rgb(doc, COLORS.brand);
        text(doc, 'DISCOVERED SIGNALS', MARGIN, y);
        y += 2;
        rule(doc, y, COLORS.brand);
        y += 6;

        features.forEach((f, idx) => {
            y = ensureSpace(doc, y, 30, addPage);

            const title       = f.title || f.feature_title || `Feature ${idx + 1}`;
            const description = normalizeParagraph(f.description || f.feature_summary || '');
            const category    = f.category || '';
            const score       = f.confidence_score ?? f.confidence;
            const sourceCount = f.source_count;
            const url         = f.source_url || f.primary_url || '';
            const metrics     = Array.isArray(f.key_metrics) ? f.key_metrics : [];
            const impact      = normalizeParagraph(f.impact_assessment || '');

            // Feature card background
            fill(doc, COLORS.featureBg);
            stroke(doc, COLORS.rule);
            doc.setLineWidth(0.25);

            // Calculate card height roughly
            const descLines = doc.splitTextToSize(description, CONTENT - 10);
            const impactLines = impact ? doc.splitTextToSize(`Impact: ${impact}`, CONTENT - 10) : [];
            const descLineH = 6.2;
            const impactLineH = 5.9;
            const cardH = 16 +
                descLines.length * descLineH +
                (impact ? impactLines.length * impactLineH + 6 : 0) +
                (metrics.length > 0 ? 8 : 0) +
                (url ? 8 : 0) + 6;

            // Clamp card to avoid overflow
            const safeCardH = Math.min(cardH, 268 - y);
            doc.roundedRect(MARGIN - 2, y - 4, CONTENT + 4, safeCardH, 2, 2, 'FD');

            // Rank bubble
            fill(doc, COLORS.brand);
            doc.circle(MARGIN + 4, y + 1.5, 4, 'F');
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(7.5);
            rgb(doc, COLORS.white);
            doc.text(String(f.rank || idx + 1), MARGIN + 4, y + 2.8, { align: 'center' });

            // Title
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(10);
            rgb(doc, COLORS.heading);
            const titleText = title.length > 76 ? title.slice(0, 74) + '...' : title;
            text(doc, titleText, MARGIN + 12, y + 2);

            // Confidence badge (top-right)
            if (score != null) {
                const pct  = Math.round(score * 100);
                const col  = confColour(score);
                const bw   = 14;
                const bx   = PW - MARGIN - bw;

                fill(doc, col.map(c => Math.min(255, c + 200)));
                stroke(doc, col);
                doc.setLineWidth(0.3);
                doc.roundedRect(bx, y - 3, bw, 8, 1.5, 1.5, 'FD');

                doc.setFont('helvetica', 'bold');
                doc.setFontSize(7);
                rgb(doc, col);
                doc.text(`${pct}%`, bx + bw / 2, y + 1.5, { align: 'center' });
            }

            // Category pill
            if (category) {
                fill(doc, COLORS.brandSoft);
                stroke(doc, COLORS.bannerBorder);
                doc.setLineWidth(0.2);
                const tw = MARGIN + 12;
                const pillW = doc.getStringUnitWidth(category) * 8 * 0.35 + 8;
                doc.roundedRect(tw, y + 5, pillW, 5.5, 1.5, 1.5, 'FD');
                doc.setFont('helvetica', 'normal');
                doc.setFontSize(6.5);
                rgb(doc, COLORS.brand);
                text(doc, category, tw + 3, y + 9);
            }

            y += 14.5;

            // Description
            if (description) {
                doc.setFont('helvetica', 'normal');
                doc.setFontSize(8.5);
                rgb(doc, COLORS.body);
                y = ensureSpace(doc, y, descLines.length * descLineH + 3, addPage);
                doc.text(descLines, MARGIN + 2, y, { maxWidth: CONTENT - 4, lineHeightFactor: 1.42 });
                y += descLines.length * descLineH + 1.8;
            }

            // Impact assessment
            if (impact) {
                doc.setFont('helvetica', 'italic');
                doc.setFontSize(8);
                rgb(doc, COLORS.muted);
                y = ensureSpace(doc, y, impactLines.length * impactLineH + 3, addPage);
                doc.text(impactLines, MARGIN + 2, y, { maxWidth: CONTENT - 4, lineHeightFactor: 1.38 });
                y += impactLines.length * impactLineH + 1.6;
            }

            // Metrics chips
            if (metrics.length > 0) {
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(7);
                rgb(doc, COLORS.success);
                let mx = MARGIN + 2;
                metrics.forEach(m => {
                    const mw = doc.getStringUnitWidth(m) * 7 * 0.35 + 8;
                    if (mx + mw > PW - MARGIN) {
                        mx = MARGIN + 2;
                        y += 5.2;
                    }
                    fill(doc, [220, 252, 231]);
                    stroke(doc, [134, 239, 172]);
                    doc.setLineWidth(0.2);
                    doc.roundedRect(mx, y - 3, mw, 5, 1.5, 1.5, 'FD');
                    rgb(doc, [22, 163, 74]);
                    doc.text(m, mx + mw / 2, y + 0.5, { align: 'center' });
                    mx += mw + 3;
                });
                y += 7.2;
            }

            // Source info row
            if (url || sourceCount) {
                doc.setFont('helvetica', 'normal');
                doc.setFontSize(7.5);
                rgb(doc, COLORS.muted);
                const sourceStr = [
                    sourceCount ? `${sourceCount} source${sourceCount > 1 ? 's' : ''}` : null,
                    url ? (url.length > 74 ? url.slice(0, 72) + '...' : url) : null,
                ].filter(Boolean).join('  |  ');
                text(doc, sourceStr, MARGIN + 2, y, { maxWidth: CONTENT - 4 });
                y += 6.2;
            }

            y += 4; // gap between cards
        });
    }

    // ── Sources Section ───────────────────────────────────────────────
    if (sources.length > 0) {
        y = ensureSpace(doc, y, 20, addPage);

        doc.setFont('helvetica', 'bold');
        doc.setFontSize(11);
        rgb(doc, COLORS.brand);
        text(doc, 'SOURCE INDEX', MARGIN, y);
        y += 2;
        rule(doc, y, COLORS.brand);
        y += 6;

        sources.forEach((url, i) => {
            y = ensureSpace(doc, y, 7, addPage);
            doc.setFont('helvetica', 'normal');
            doc.setFontSize(7.5);
            rgb(doc, COLORS.body);
            const display = url.length > 102 ? url.slice(0, 99) + '...' : url;
            text(doc, `${i + 1}.  ${display}`, MARGIN, y, { maxWidth: CONTENT });
            y += 5;
        });
        y += 4;
    }

    // ── Metadata footer line ──────────────────────────────────────────
    y = ensureSpace(doc, y, 14, addPage);
    rule(doc, y);
    y += 5;
    doc.setFont('helvetica', 'italic');
    doc.setFontSize(7);
    rgb(doc, COLORS.muted);
    const meta = report.metadata || {};
    const metaStr = [
        `Pipeline v${meta.pipeline_version || '2.1'}`,
        meta.model ? `Model: ${meta.model}` : null,
        `Window: ${meta.date_window_days || 7} days`,
        `Generated: ${generatedAt}`,
    ].filter(Boolean).join('  ·  ');
    text(doc, metaStr, MARGIN, y);

    // ── First page footer ─────────────────────────────────────────────
    drawPageFooter(doc, 1, companyName);

    // ── Save ──────────────────────────────────────────────────────────
    const safeName = companyName.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    doc.save(`market_intelligence_${safeName}_${Date.now()}.pdf`);
}

// ── Page footer (repeated on every page) ─────────────────────────────
function drawPageFooter(doc, page, company) {
    const y = 292;
    stroke(doc, COLORS.rule);
    doc.setLineWidth(0.25);
    doc.line(MARGIN, y - 3, PW - MARGIN, y - 3);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(6.5);
    rgb(doc, COLORS.muted);
    doc.text('Market Intelligence Scout  ·  Confidential', MARGIN, y);
    doc.text(`Page ${page}`, PW - MARGIN, y, { align: 'right' });
    doc.text(company, PW / 2, y, { align: 'center' });
}
