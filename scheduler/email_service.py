"""
Market Intelligence Scout — Email Service

Sends an HTML email with inline report content + a PDF attachment
via Gmail SMTP (TLS on port 587).
"""
from mcp_server.tools.gmail_tool import send_market_report
import logging
from datetime import datetime, timezone

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

    # Calculate average confidence
    conf_scores = [f.get("confidence_score") or f.get("confidence") or 0
                   for f in features if (f.get("confidence_score") or f.get("confidence")) is not None]
    avg_conf = round((sum(conf_scores) / len(conf_scores)) * 100) if conf_scores else 0

    def conf_color(score):
        if score is None: return "#94a3b8"
        if score >= 0.7:  return "#16a34a"
        if score >= 0.4:  return "#d97706"
        return "#dc2626"

    def conf_bg(score):
        if score is None: return "#f1f5f9"
        if score >= 0.7:  return "#f0fdf4"
        if score >= 0.4:  return "#fffbeb"
        return "#fef2f2"

    # Build feature cards using table layout (email-safe)
    feature_rows = ""
    for i, f in enumerate(features):
        title    = f.get("title") or f.get("feature_title") or f"Feature {i+1}"
        desc     = f.get("description") or f.get("feature_summary") or ""
        category = f.get("category", "")
        score    = f.get("confidence_score") or f.get("confidence")
        pct      = f"{round(score*100)}%" if score is not None else "—"
        col      = conf_color(score)
        bg       = conf_bg(score)
        metrics  = f.get("key_metrics") or []
        src_url  = f.get("source_url") or f.get("primary_url") or ""
        impact   = f.get("impact_assessment") or ""

        metric_chips = "".join(
            f'<span style="display:inline-block;background:#dcfce7;color:#15803d;'
            f'border-radius:4px;padding:3px 10px;font-size:12px;margin:2px 4px 2px 0;'
            f'font-weight:600;">{m}</span>'
            for m in metrics[:5]
        )
        src_html = (
            f'<a href="{src_url}" style="color:#2E7D32;font-size:12px;'
            f'font-weight:600;text-decoration:underline;">View Source →</a>'
            if src_url else ""
        )
        impact_html = (
            f'<tr><td style="padding:8px 0 0;">'
            f'<table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>'
            f'<td style="width:3px;background:#60a5fa;border-radius:2px;"></td>'
            f'<td style="padding:8px 12px;background:#eff6ff;border-radius:0 6px 6px 0;'
            f'font-size:13px;color:#3b82f6;line-height:1.5;font-style:italic;">'
            f'{impact}</td></tr></table></td></tr>'
            if impact else ""
        )
        category_html = (
            f'<span style="display:inline-block;background:#e0f2e9;color:#2E7D32;'
            f'border-radius:4px;padding:3px 10px;font-size:11px;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.5px;">{category}</span>'
            if category else ""
        )

        feature_rows += f"""
        <tr><td style="padding:0 0 16px;">
          <table cellpadding="0" cellspacing="0" border="0" width="100%"
                 style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;
                        overflow:hidden;">
            <tr><td style="padding:20px 24px;">
              <!-- Title Row -->
              <table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>
                <td style="vertical-align:top;width:32px;">
                  <div style="background:#2E7D32;color:#ffffff;border-radius:50%;
                              width:28px;height:28px;text-align:center;line-height:28px;
                              font-size:12px;font-weight:800;">{i+1}</div>
                </td>
                <td style="vertical-align:top;padding:0 12px;">
                  <div style="font-size:15px;font-weight:700;color:#1a1d23;
                              line-height:1.4;margin-bottom:6px;">{title}</div>
                  {category_html}
                </td>
                <td style="vertical-align:top;text-align:right;white-space:nowrap;">
                  <span style="display:inline-block;background:{bg};color:{col};
                              border-radius:20px;padding:5px 14px;font-size:13px;
                              font-weight:800;border:1px solid {col}22;">{pct}</span>
                </td>
              </tr></table>
              <!-- Description -->
              <table cellpadding="0" cellspacing="0" border="0" width="100%">
                <tr><td style="padding:12px 0 0;">
                  <p style="color:#4a5568;font-size:14px;line-height:1.7;margin:0;">
                    {desc}
                  </p>
                </td></tr>
                {impact_html}
                {"<tr><td style='padding:10px 0 0;'>" + metric_chips + "</td></tr>" if metrics else ""}
                {"<tr><td style='padding:10px 0 0;'>" + src_html + "</td></tr>" if src_url else ""}
              </table>
            </td></tr>
          </table>
        </td></tr>"""

    summary_html = ""
    if report.get("executive_summary"):
        summary_html = f"""
        <tr><td style="padding:0 0 28px;">
          <table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>
            <td style="width:4px;background:#2E7D32;border-radius:2px;"></td>
            <td style="padding:16px 20px;background:#f0fdf4;border-radius:0 10px 10px 0;">
              <p style="color:#4a5568;font-size:15px;line-height:1.75;margin:0;">
                {report["executive_summary"]}
              </p>
            </td>
          </tr></table>
        </td></tr>"""

    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>{company} — Intelligence Report</title>
  <!--[if mso]>
  <style>table {{border-collapse:collapse;}} td {{padding:0;}}</style>
  <![endif]-->
  <style>
    @media only screen and (max-width: 640px) {{
      .email-container {{ width: 100% !important; max-width: 100% !important; }}
      .responsive-pad {{ padding-left: 20px !important; padding-right: 20px !important; }}
      .stat-cell {{ display: block !important; width: 100% !important; text-align: center !important;
                    padding: 10px 0 !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background:#f0f4f0;font-family:'Segoe UI',Roboto,Arial,Helvetica,sans-serif;
             -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;">

  <!-- Outer Wrapper -->
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:#f0f4f0;padding:32px 16px;">
    <tr><td align="center">

      <!-- Email Container -->
      <table role="presentation" class="email-container" width="640" cellpadding="0" cellspacing="0" border="0"
             style="max-width:640px;width:100%;background:#ffffff;border-radius:16px;
                    overflow:hidden;box-shadow:0 4px 30px rgba(0,0,0,0.08);">

        <!-- ═══ HEADER ═══ -->
        <tr>
          <td style="background:linear-gradient(135deg,#2E7D32,#1B5E20);padding:36px 36px 32px;"
              class="responsive-pad">
            <table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>
              <td>
                <p style="color:#a5d6a7;font-size:11px;letter-spacing:2.5px;
                          text-transform:uppercase;margin:0 0 10px;font-weight:700;">
                  Market Intelligence Scout
                </p>
                <h1 style="color:#ffffff;margin:0 0 8px;font-size:26px;font-weight:800;
                           letter-spacing:-0.02em;line-height:1.2;">
                  {company}
                </h1>
                <p style="color:#a5d6a7;margin:0;font-size:14px;font-weight:500;">
                  Intelligence Report &nbsp;·&nbsp; {gen_str}
                </p>
              </td>
            </tr></table>
          </td>
        </tr>

        <!-- ═══ STATS STRIP ═══ -->
        <tr>
          <td style="background:#e8f5e9;padding:20px 36px;border-bottom:1px solid #c8e6c9;"
              class="responsive-pad">
            <table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>
              <td class="stat-cell" style="text-align:center;width:33%;">
                <strong style="font-size:28px;color:#2E7D32;font-weight:800;display:block;
                               line-height:1;">{total_feat}</strong>
                <p style="color:#388E3C;font-size:11px;margin:4px 0 0;font-weight:700;
                          text-transform:uppercase;letter-spacing:0.5px;">Signals</p>
              </td>
              <td class="stat-cell" style="text-align:center;width:33%;">
                <strong style="font-size:28px;color:#2E7D32;font-weight:800;display:block;
                               line-height:1;">{total_src}</strong>
                <p style="color:#388E3C;font-size:11px;margin:4px 0 0;font-weight:700;
                          text-transform:uppercase;letter-spacing:0.5px;">Sources</p>
              </td>
              <td class="stat-cell" style="text-align:center;width:34%;">
                <strong style="font-size:28px;color:#2E7D32;font-weight:800;display:block;
                               line-height:1;">{avg_conf}%</strong>
                <p style="color:#388E3C;font-size:11px;margin:4px 0 0;font-weight:700;
                          text-transform:uppercase;letter-spacing:0.5px;">Avg Confidence</p>
              </td>
            </tr></table>
          </td>
        </tr>

        <!-- ═══ BODY ═══ -->
        <tr>
          <td style="padding:32px 36px;" class="responsive-pad">

            <!-- Executive Summary -->
            {"<h2 style='font-size:13px;color:#2E7D32;margin:0 0 16px;text-transform:uppercase;"
             "letter-spacing:1px;font-weight:800;'>Executive Summary</h2>"
             + summary_html if summary_html else ""}

            <!-- Features -->
            {"<h2 style='font-size:13px;color:#2E7D32;margin:0 0 16px;text-transform:uppercase;"
             "letter-spacing:1px;font-weight:800;'>Discovered Signals</h2>"
             "<table cellpadding='0' cellspacing='0' border='0' width='100%'>"
             + feature_rows + "</table>"
             if features else
             "<p style='color:#94a3b8;font-size:14px;font-style:italic;"
             "text-align:center;padding:24px 0;'>"
             "No signals extracted for this report.</p>"}

          </td>
        </tr>

        <!-- ═══ FOOTER ═══ -->
        <tr>
          <td style="background:#f8faf8;padding:24px 36px;border-top:1px solid #e8ede8;
                     text-align:center;" class="responsive-pad">
            <p style="color:#8896a6;font-size:12px;margin:0;line-height:1.6;">
              This report was automatically generated by
              <strong style="color:#2E7D32;">Market Intelligence Scout</strong>.
              <br>A PDF copy is attached to this email.
            </p>
          </td>
        </tr>

      </table>
      <!-- /Email Container -->

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

    # Header — Green brand gradient
    pdf.set_fill_color(46, 125, 50)  # #2E7D32
    pdf.rect(0, 0, 210, 44, "F")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(165, 214, 167)  # #a5d6a7
    pdf.set_xy(18, 10)
    pdf.cell(0, 5, "MARKET INTELLIGENCE SCOUT", ln=True)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(18, 17)
    pdf.cell(0, 10, company[:40], ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(165, 214, 167)
    pdf.set_xy(18, 30)
    pdf.cell(0, 6, f"Intelligence Report  |  {gen_str}", ln=True)

    # Stats strip
    pdf.set_fill_color(232, 245, 233)  # #e8f5e9
    pdf.rect(0, 44, 210, 16, "F")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(46, 125, 50)
    pdf.set_xy(18, 48)
    pdf.cell(85, 8, f"Signals: {total_feat}", align="C")
    pdf.cell(85, 8, f"Sources: {total_src}", align="C")
    pdf.ln(20)

    # Executive Summary
    if report.get("executive_summary"):
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(46, 125, 50)
        pdf.cell(0, 7, "EXECUTIVE SUMMARY", ln=True)
        pdf.set_draw_color(46, 125, 50)
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
        pdf.set_text_color(46, 125, 50)
        pdf.cell(0, 7, "DISCOVERED SIGNALS", ln=True)
        pdf.set_draw_color(46, 125, 50)
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
            pdf.set_fill_color(46, 125, 50)  # #2E7D32
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
                pdf.set_text_color(46, 125, 50)
                pdf.set_xy(162, card_y + 1)
                pdf.cell(28, 5, pct, align="R")

            pdf.ln(8)

            # Category
            if category:
                pdf.set_font("Helvetica", "", 7)
                pdf.set_text_color(46, 125, 50)
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
                pdf.set_text_color(46, 125, 50)
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

    logger.info(
        "EMAIL — Report sent to %s for company '%s'",
        recipient_email,
        company
    )