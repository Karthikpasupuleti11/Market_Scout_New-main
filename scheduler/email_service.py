"""
Market Intelligence Scout — Email Service

Sends an HTML email with inline report content + a PDF attachment
via Gmail SMTP (TLS on port 587).
"""
from mcp_server.tools.gmail_tool import send_market_report
import logging
from datetime            import datetime, timezone

logger = logging.getLogger(__name__)


# ── HTML email template ───────────────────────────────────────────────

def _build_html(report: dict, company: str) -> str:
    features      = report.get("features", [])
    total_feat    = report.get("total_features_verified", len(features))
    total_src     = report.get("total_sources_analysed", 0)
    generated_at  = report.get("generated_at", datetime.now(timezone.utc).isoformat())
    try:
        gen_str = datetime.fromisoformat(generated_at).strftime("%B %d, %Y at %H:%M UTC")
    except Exception:
        gen_str = generated_at

    def conf_color(score):
        if score is None: return "#94a3b8"
        if score >= 0.7:  return "#22c55e"
        if score >= 0.4:  return "#f59e0b"
        return "#ef4444"

    feature_rows = ""
    for i, f in enumerate(features):
        title    = f.get("title") or f.get("feature_title") or f"Feature {i+1}"
        desc     = f.get("description") or f.get("feature_summary") or ""
        category = f.get("category", "")
        score    = f.get("confidence_score") or f.get("confidence")
        pct      = f"{round(score*100)}%" if score is not None else "—"
        col      = conf_color(score)
        metrics  = f.get("key_metrics") or []
        src_url  = f.get("source_url") or f.get("primary_url") or ""
        impact   = f.get("impact_assessment") or ""

        metric_chips = "".join(
            f'<span style="background:#dcfce7;color:#15803d;border-radius:4px;'
            f'padding:2px 8px;font-size:11px;margin-right:4px;">{m}</span>'
            for m in metrics
        )
        src_link = (
            f'<a href="{src_url}" style="color:#6366f1;font-size:12px;">🔗 Source</a>'
            if src_url else ""
        )
        impact_html = (
            f'<p style="color:#94a3b8;font-size:12px;font-style:italic;margin:6px 0 0;">▸ {impact}</p>'
            if impact else ""
        )

        feature_rows += f"""
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;
                    padding:16px 18px;margin-bottom:14px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;
                      flex-wrap:wrap;gap:8px;margin-bottom:8px;">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
              <span style="background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;
                           display:inline-flex;align-items:center;justify-content:center;
                           font-size:11px;font-weight:700;flex-shrink:0;">{i+1}</span>
              <strong style="font-size:14px;color:#1e293b;">{title}</strong>
              {"<span style='background:#e0e7ff;color:#4338ca;border-radius:4px;padding:2px 8px;font-size:11px;'>"
               + category + "</span>" if category else ""}
            </div>
            <span style="background:{col}22;color:{col};border-radius:20px;
                         padding:3px 10px;font-size:12px;font-weight:700;">{pct}</span>
          </div>
          <p style="color:#475569;font-size:13px;line-height:1.6;margin:0 0 8px;">{desc}</p>
          {impact_html}
          <div style="margin-top:10px;display:flex;align-items:center;
                      flex-wrap:wrap;gap:8px;">
            {metric_chips}
            {src_link}
          </div>
        </div>"""

    summary_html = (
        f'<p style="color:#475569;font-size:14px;line-height:1.7;'
        f'background:#f0f9ff;border-left:4px solid #6366f1;padding:14px 18px;'
        f'border-radius:0 8px 8px 0;margin:0;">'
        f'{report.get("executive_summary","")}</p>'
        if report.get("executive_summary") else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#f1f5f9;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;background:#ffffff;border-radius:16px;
                    overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

        <!-- HEADER -->
        <tr>
          <td style="background:linear-gradient(135deg,#6366f1,#4f46e5);
                     padding:32px 32px 28px;">
            <p style="color:#c7d2fe;font-size:11px;letter-spacing:2px;
                      text-transform:uppercase;margin:0 0 8px;">Market Intelligence Scout</p>
            <h1 style="color:#ffffff;margin:0 0 6px;font-size:24px;">{company}</h1>
            <p style="color:#c7d2fe;margin:0;font-size:13px;">
              Intelligence Report &nbsp;·&nbsp; {gen_str}
            </p>
          </td>
        </tr>

        <!-- STATS STRIP -->
        <tr>
          <td style="background:#eef2ff;padding:16px 32px;border-bottom:1px solid #e0e7ff;">
            <table width="100%" cellpadding="0" cellspacing="0"><tr>
              <td style="text-align:center;">
                <strong style="font-size:22px;color:#4338ca;">{total_feat}</strong>
                <p style="color:#6366f1;font-size:11px;margin:2px 0 0;">Features</p>
              </td>
              <td style="text-align:center;">
                <strong style="font-size:22px;color:#4338ca;">{total_src}</strong>
                <p style="color:#6366f1;font-size:11px;margin:2px 0 0;">Sources</p>
              </td>
            </tr></table>
          </td>
        </tr>

        <!-- BODY -->
        <tr><td style="padding:28px 32px;">

          {"<h2 style='font-size:15px;color:#1e293b;margin:0 0 12px;'>Executive Summary</h2>" + summary_html if summary_html else ""}

          {"<h2 style='font-size:15px;color:#1e293b;margin:28px 0 14px;'>🔬 Discovered Features</h2>" + feature_rows if features else
           "<p style='color:#94a3b8;font-style:italic;'>No features extracted for this report.</p>"}

        </td></tr>

        <!-- FOOTER -->
        <tr>
          <td style="background:#f8fafc;padding:20px 32px;border-top:1px solid #e2e8f0;
                     text-align:center;">
            <p style="color:#94a3b8;font-size:11px;margin:0;">
              This report was automatically generated by
              <strong style="color:#6366f1;">Market Intelligence Scout</strong>.
              A PDF copy is attached.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>"""


# ── PDF generation (backend, using fpdf2) ────────────────────────────

def _build_pdf(report: dict, company: str) -> bytes:
    from fpdf import FPDF

    features     = report.get("features", [])
    total_feat   = report.get("total_features_verified", len(features))
    total_src    = report.get("total_sources_analysed", 0)
    generated_at = report.get("generated_at", "")
    try:
        gen_str = datetime.fromisoformat(generated_at).strftime("%B %d, %Y at %H:%M UTC")
    except Exception:
        gen_str = generated_at

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(18, 18, 18)

    # Header
    pdf.set_fill_color(99, 102, 241)
    pdf.rect(0, 0, 210, 44, "F")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(199, 210, 254)
    pdf.set_xy(18, 10)
    pdf.cell(0, 5, "MARKET INTELLIGENCE SCOUT", ln=True)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(18, 17)
    pdf.cell(0, 10, company[:40], ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(199, 210, 254)
    pdf.set_xy(18, 30)
    pdf.cell(0, 6, f"Intelligence Report  |  {gen_str}", ln=True)

    # Stats strip
    pdf.set_fill_color(238, 242, 255)
    pdf.rect(0, 44, 210, 16, "F")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(99, 102, 241)
    pdf.set_xy(18, 48)
    pdf.cell(85, 8, f"Features: {total_feat}", align="C")
    pdf.cell(85, 8, f"Sources: {total_src}", align="C")
    pdf.ln(20)

    # Executive Summary
    if report.get("executive_summary"):
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(0, 7, "EXECUTIVE SUMMARY", ln=True)
        pdf.set_draw_color(99, 102, 241)
        pdf.set_line_width(0.3)
        pdf.line(18, pdf.get_y(), 192, pdf.get_y())
        pdf.ln(4)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(71, 85, 105)
        pdf.multi_cell(0, 5.5, report["executive_summary"])
        pdf.ln(6)

    # Features
    if features:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(0, 7, "DISCOVERED FEATURES", ln=True)
        pdf.set_draw_color(99, 102, 241)
        pdf.line(18, pdf.get_y(), 192, pdf.get_y())
        pdf.ln(5)

        for i, f in enumerate(features):
            title    = f.get("title") or f.get("feature_title") or f"Feature {i+1}"
            desc     = f.get("description") or f.get("feature_summary") or ""
            category = f.get("category", "")
            score    = f.get("confidence_score") or f.get("confidence")
            pct      = f"{round(score*100)}%" if score is not None else ""
            impact   = f.get("impact_assessment") or ""
            metrics  = f.get("key_metrics") or []
            url      = f.get("source_url") or ""

            if pdf.get_y() > 255:
                pdf.add_page()

            # Card bg
            card_y = pdf.get_y()
            pdf.set_fill_color(248, 250, 252)
            pdf.set_draw_color(226, 232, 240)
            pdf.set_line_width(0.25)
            pdf.rect(16, card_y - 2, 178, 4, "FD")  # placeholder, drawn over

            # Rank
            pdf.set_fill_color(99, 102, 241)
            pdf.ellipse(18, card_y, 7, 7, "F")
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_text_color(255, 255, 255)
            pdf.set_xy(18, card_y + 1.5)
            pdf.cell(7, 4, str(i + 1), align="C")

            # Title
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(30, 41, 59)
            pdf.set_xy(28, card_y + 1)
            title_display = title[:70] + ("…" if len(title) > 70 else "")
            pdf.cell(130, 5, title_display)

            # Confidence
            if pct:
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(99, 102, 241)
                pdf.set_xy(162, card_y + 1)
                pdf.cell(28, 5, pct, align="R")

            pdf.ln(8)

            # Category
            if category:
                pdf.set_font("Helvetica", "", 7)
                pdf.set_text_color(67, 56, 202)
                pdf.set_x(28)
                pdf.cell(0, 4, f"[{category}]", ln=True)
                pdf.ln(1)

            # Description
            if desc:
                pdf.set_font("Helvetica", "", 8.5)
                pdf.set_text_color(71, 85, 105)
                pdf.set_x(28)
                pdf.multi_cell(0, 5, desc)

            # Impact
            if impact:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(148, 163, 184)
                pdf.set_x(28)
                pdf.multi_cell(0, 4.5, f"> {impact}")

            # Metrics
            if metrics:
                pdf.set_font("Helvetica", "B", 7)
                pdf.set_text_color(21, 128, 61)
                pdf.set_x(28)
                pdf.cell(0, 5, "  ".join(f"▪ {m}" for m in metrics), ln=True)

            # Source URL
            if url:
                pdf.set_font("Helvetica", "", 7)
                pdf.set_text_color(99, 102, 241)
                pdf.set_x(28)
                display_url = url[:90] + ("…" if len(url) > 90 else "")
                pdf.cell(0, 4, display_url, ln=True)

            pdf.ln(6)

    # Footer
    pdf.set_y(-20)
    pdf.set_draw_color(226, 232, 240)
    pdf.set_line_width(0.25)
    pdf.line(18, pdf.get_y(), 192, pdf.get_y())
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, "Market Intelligence Scout  ·  Automatically generated report", align="C")

    return bytes(pdf.output())


# ── Main send function ────────────────────────────────────────────────

def send_report_email(report: dict, company: str, recipient_email: str) -> None:
    """
    Send the intelligence report as:
    - A rich HTML email body
    - A PDF attachment

    Raises on SMTP failure.
    """
    

    subject = f"📊 Market Intelligence Report — {company}"

    # HTML body
    html_body = _build_html(report, company)

    pdf_bytes = None

    # PDF attachment
    try:
        pdf_bytes = _build_pdf(report, company)
    except Exception as pdf_err:
        logger.warning("EMAIL — PDF generation failed (sending HTML only): %s", pdf_err)

    # Send using Gmail API + MCP

    send_market_report(
        recipient=recipient_email,
        company=company,
        html_body=html_body,
        pdf_bytes=pdf_bytes
    )

    logger.info(
        "EMAIL — Report sent to %s for company '%s'",
        recipient_email,
        company
    )
