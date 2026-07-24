"""
HTML Report Generator — produces a self-contained, printable, responsive
HTML drug recommendation report from a ``RecommendationResponse``.

The report includes patient info, evidence summary, ranked drug table,
detailed reason breakdown, warnings, calculation trace, and engine metadata.

All styling is inline CSS — no external dependencies.  Collapsible sections
use pure HTML/CSS (``<details>/<summary>``), no JavaScript required.
"""

from __future__ import annotations

import html as html_lib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.api.v1.recommendation import (
        RecommendationDrugItem,
        RecommendationResponse,
    )

# ── CSS (inline, self-contained) ─────────────────────────────────────────────

_CSS = """
/* ═══════════════════════════════════════════════════════════════════════════
   Drug Recommendation Report — Inline Styles
   ═══════════════════════════════════════════════════════════════════════════ */

*, *::before, *::after { box-sizing: border-box; }

:root {
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-primary: #2563eb;
  --color-primary-dark: #1d4ed8;
  --color-text: #1e293b;
  --color-text-muted: #64748b;
  --color-border: #e2e8f0;
  --color-success: #16a34a;
  --color-warning: #d97706;
  --color-danger: #dc2626;
  --color-rank-1: #f59e0b;
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: "SFMono-Regular", Menlo, Monaco, Consolas, monospace;
}

body {
  margin: 0;
  padding: 0;
  background: var(--color-bg);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text);
}

/* ── Layout ────────────────────────────────────────────────────────────── */

.container {
  max-width: 1024px;
  margin: 0 auto;
  padding: 24px 16px;
}

/* ── Header ────────────────────────────────────────────────────────────── */

.report-header {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: #fff;
  padding: 32px 24px;
  border-radius: 12px;
  margin-bottom: 24px;
}

.report-header h1 {
  margin: 0 0 8px;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.report-header .meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px 32px;
  font-size: 13px;
  opacity: 0.9;
}

.report-header .meta dt {
  font-weight: 600;
  display: inline;
}

.report-header .meta dd {
  display: inline;
  margin: 0;
}

/* ── Cards ─────────────────────────────────────────────────────────────── */

.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 20px 24px;
  margin-bottom: 20px;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 16px;
  color: var(--color-text);
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title .badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--color-primary);
  color: #fff;
}

/* ── Patient Section ───────────────────────────────────────────────────── */

.patient-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 8px 24px;
}

.patient-info dt {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
}

.patient-info dd {
  margin: 2px 0 12px;
  font-size: 15px;
  font-weight: 500;
}

.variant-list {
  list-style: none;
  padding: 0;
  margin: 8px 0 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.variant-list li {
  background: #eff6ff;
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: 13px;
  padding: 4px 12px;
  border-radius: 6px;
  font-weight: 500;
}

/* ── Evidence Summary ──────────────────────────────────────────────────── */

.evidence-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.evidence-stat {
  text-align: center;
  padding: 12px 8px;
  background: #f1f5f9;
  border-radius: 8px;
}

.evidence-stat .value {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-primary);
  line-height: 1.2;
}

.evidence-stat .label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
  margin-top: 4px;
}

.distribution-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  margin: 12px 0 0;
  font-size: 13px;
}

.distribution-list dt {
  font-weight: 600;
  display: inline;
}

.distribution-list dd {
  display: inline;
  margin: 0;
}

/* ── Ranking Table ─────────────────────────────────────────────────────── */

.ranking-table-wrap {
  overflow-x: auto;
}

.ranking-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.ranking-table thead th {
  background: #f1f5f9;
  padding: 10px 12px;
  text-align: left;
  font-weight: 700;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
  border-bottom: 2px solid var(--color-border);
  white-space: nowrap;
}

.ranking-table tbody td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}

.ranking-table tbody tr:hover {
  background: #f8fafc;
}

.ranking-table .rank-cell {
  font-weight: 700;
  text-align: center;
  width: 48px;
}

.ranking-table .rank-1 {
  color: var(--color-rank-1);
}

.ranking-table .drug-name-cell {
  font-weight: 600;
}

.ranking-table .score-cell {
  font-family: var(--font-mono);
  font-size: 12px;
  text-align: right;
  white-space: nowrap;
}

.ranking-table .score-positive {
  color: var(--color-success);
}

.ranking-table .score-negative {
  color: var(--color-danger);
}

.ranking-table .score-neutral {
  color: var(--color-text-muted);
}

/* ── Reason Breakdown ──────────────────────────────────────────────────── */

.drug-breakdown {
  margin-bottom: 24px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  overflow: hidden;
}

.drug-breakdown-header {
  background: #f1f5f9;
  padding: 14px 20px;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
}

.drug-breakdown-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}

.drug-breakdown-header .drug-sub-scores {
  font-size: 12px;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
}

.drug-breakdown-body {
  padding: 16px 20px;
}

.reason-group {
  margin-bottom: 16px;
}

.reason-group:last-child {
  margin-bottom: 0;
}

.reason-group-title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
  margin-bottom: 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--color-border);
}

.reason-item {
  display: flex;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
  line-height: 1.5;
}

.reason-item .reason-impact {
  font-family: var(--font-mono);
  font-size: 12px;
  white-space: nowrap;
  min-width: 60px;
  text-align: right;
  flex-shrink: 0;
}

.reason-item .reason-impact.positive {
  color: var(--color-success);
}

.reason-item .reason-impact.negative {
  color: var(--color-danger);
}

.reason-item .reason-impact.zero {
  color: var(--color-text-muted);
}

.reason-item .reason-detail {
  flex: 1;
}

.reason-item .reason-source {
  font-size: 11px;
  color: var(--color-text-muted);
  flex-shrink: 0;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Warnings ──────────────────────────────────────────────────────────── */

.warning-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.warning-list li {
  padding: 10px 14px;
  margin-bottom: 8px;
  border-radius: 8px;
  font-size: 13px;
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.warning-list .warning-high {
  background: #fef2f2;
  border-left: 4px solid var(--color-danger);
  color: #991b1b;
}

.warning-list .warning-medium {
  background: #fffbeb;
  border-left: 4px solid var(--color-warning);
  color: #92400e;
}

.warning-list .warning-low {
  background: #f0fdf4;
  border-left: 4px solid var(--color-success);
  color: #166534;
}

.warning-list .warning-icon {
  font-size: 16px;
  flex-shrink: 0;
  width: 20px;
  text-align: center;
}

/* ── Trace (collapsible) ───────────────────────────────────────────────── */

details.trace-details {
  margin-bottom: 20px;
}

details.trace-details summary {
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  padding: 12px 16px;
  background: #f1f5f9;
  border-radius: 8px;
  user-select: none;
}

details.trace-details summary:hover {
  background: #e2e8f0;
}

details.trace-details[open] summary {
  border-radius: 8px 8px 0 0;
}

.trace-content {
  padding: 16px 20px;
  border: 1px solid var(--color-border);
  border-top: none;
  border-radius: 0 0 8px 8px;
}

.trace-step {
  padding: 8px 0;
  border-bottom: 1px solid #f1f5f9;
  font-size: 13px;
}

.trace-step:last-child {
  border-bottom: none;
}

.trace-step .step-header {
  font-weight: 600;
  display: flex;
  gap: 12px;
}

.trace-step .step-type {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 1px 8px;
  border-radius: 4px;
  background: #e2e8f0;
  color: var(--color-text-muted);
}

.trace-step .step-data {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
  margin: 4px 0 0 4px;
  white-space: pre-wrap;
  word-break: break-all;
}

/* ── Footer ────────────────────────────────────────────────────────────── */

.report-footer {
  text-align: center;
  padding: 24px;
  font-size: 12px;
  color: var(--color-text-muted);
  border-top: 1px solid var(--color-border);
  margin-top: 8px;
}

.report-footer .disclaimer {
  margin-top: 8px;
  padding: 12px 16px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  font-size: 12px;
  color: #92400e;
  text-align: left;
}

.report-footer .version {
  font-family: var(--font-mono);
  font-size: 11px;
}

/* ── Print styles ──────────────────────────────────────────────────────── */

@media print {
  body { background: #fff; }
  .container { max-width: 100%; padding: 0; }
  .card { break-inside: avoid; border: 1px solid #ddd; box-shadow: none; }
  .report-header { background: var(--color-primary) !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .evidence-stat { background: #f1f5f9 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .warning-list .warning-high { background: #fef2f2 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .warning-list .warning-medium { background: #fffbeb !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .warning-list .warning-low { background: #f0fdf4 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .ranking-table thead th { background: #f1f5f9 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .drug-breakdown-header { background: #f1f5f9 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  details.trace-details summary { background: #f1f5f9 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .variant-list li { background: #eff6ff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}

/* ── Responsive ────────────────────────────────────────────────────────── */

@media (max-width: 640px) {
  .container { padding: 12px 8px; }
  .report-header { padding: 20px 16px; }
  .report-header h1 { font-size: 20px; }
  .card { padding: 14px 16px; }
  .patient-info { grid-template-columns: 1fr; }
  .evidence-grid { grid-template-columns: repeat(2, 1fr); }
  .ranking-table { font-size: 12px; }
  .ranking-table thead th,
  .ranking-table tbody td { padding: 6px 8px; }
  .drug-breakdown-body { padding: 12px 14px; }
  .reason-item { flex-wrap: wrap; gap: 2px 8px; }
  .reason-item .reason-impact { min-width: 48px; }
  .reason-item .reason-source { max-width: 100%; }
}
"""


# ─── ReportGenerator ──────────────────────────────────────────────────────────


class ReportGenerator:
    """Generates a self-contained HTML drug recommendation report.

    The report is a single complete HTML page with embedded CSS, suitable
    for viewing in a browser, printing to PDF, or sharing as a standalone
    document.
    """

    def generate(
        self,
        recommendation: RecommendationResponse,
        *,
        variants: list[str] | None = None,
        evidence_count: int = 0,
        rules_evaluated: int = 0,
        rules_fired: int = 0,
        trace_steps: list[dict[str, Any]] | None = None,
    ) -> str:
        """Produce a complete HTML report page.

        Parameters
        ----------
        recommendation : RecommendationResponse
            The structured recommendation response from the pipeline.
        variants : list[str], optional
            List of variant strings (e.g. ``["EGFR L858R", "KRAS G12C"]``).
        evidence_count : int, optional
            Total number of evidence items collected.
        rules_evaluated : int, optional
            Number of recommendation rules evaluated.
        rules_fired : int, optional
            Number of recommendation rules that fired.
        trace_steps : list[dict], optional
            Ordered list of trace steps for the calculation trace section.
            Each dict should have keys ``step_name``, ``step_type``,
            ``input_data``, ``output_data``, and optionally ``timestamp``
            and ``duration_ms``.

        Returns
        -------
        str
            A complete HTML5 document as a string.
        """
        # ── Derive supplementary data from the response ────────────────────
        drugs = recommendation.recommendations
        has_conflicts_or_resistance = any(
            d.resistance_score > 0.2 or d.conflict_score > 0.2
            for d in drugs
        )

        # ── Assemble sections ──────────────────────────────────────────────
        sections = [
            self._render_header(recommendation),
            self._render_patient_section(recommendation, variants or []),
            self._render_evidence_summary(recommendation, evidence_count),
            self._render_ranking_table(drugs),
            self._render_reason_breakdown(drugs),
            self._render_warnings(drugs) if has_conflicts_or_resistance else "",
            self._render_trace_section(
                recommendation.trace_id,
                trace_steps or [],
                rules_evaluated,
                rules_fired,
            ),
            self._render_footer(recommendation),
        ]

        body_html = "\n".join(s.strip() for s in sections if s)

        return self._wrap_html(body_html)

    # ── HTML wrappers ──────────────────────────────────────────────────────

    def _wrap_html(self, body: str) -> str:
        """Wrap *body* in a full HTML5 document."""
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            "<title>Drug Recommendation Report</title>\n"
            f"<style>\n{_CSS.strip()}\n</style>\n"
            "</head>\n"
            "<body>\n"
            f'<div class="container">\n'
            f"{body}\n"
            f'</div>\n'
            "</body>\n"
            "</html>"
        )

    # ── Section: Header ────────────────────────────────────────────────────

    def _render_header(self, rec: RecommendationResponse) -> str:
        """Render the report header with title and metadata."""
        created = rec.created_at
        # Format ISO timestamp to a friendlier form
        try:
            dt = datetime.fromisoformat(created)
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except (ValueError, TypeError):
            formatted_time = created

        return f"""\
<div class="report-header">
  <h1>🧬 Drug Recommendation Report</h1>
  <dl class="meta">
    <dt>Report ID:</dt> <dd>{html_lib.escape(rec.recommendation_id)}</dd>
    <dt>Generated:</dt> <dd>{html_lib.escape(formatted_time)}</dd>
    <dt>Engine:</dt> <dd>v{html_lib.escape(rec.engine_version)}</dd>
  </dl>
</div>"""

    # ── Section: Patient ───────────────────────────────────────────────────

    def _render_patient_section(self, rec: RecommendationResponse, variants: list[str]) -> str:
        """Render the patient information section."""
        variants_html = ""
        if variants:
            items = "".join(
                f"<li>{html_lib.escape(v)}</li>" for v in variants
            )
            variants_html = f"<ul class=\"variant-list\">{items}</ul>"

        return f"""\
<div class="card">
  <div class="card-title">👤 Patient Information</div>
  <dl class="patient-info">
    <dt>Patient ID</dt>
    <dd>{html_lib.escape(rec.patient_id)}</dd>
    <dt>Variants</dt>
    <dd>{variants_html or '<span style="color:var(--color-text-muted)">None provided</span>'}</dd>
  </dl>
</div>"""

    # ── Section: Evidence Summary ─────────────────────────────────────────

    def _render_evidence_summary(self, rec: RecommendationResponse, evidence_count: int) -> str:
        """Render the evidence summary card.

        Computes source and tier distributions from the explanation data
        embedded in each drug item.
        """
        # Gather source and tier info from explanation entries
        source_set: dict[str, int] = {}
        tier_set: dict[str, int] = {}
        for drug in rec.recommendations:
            for expl in drug.explanations:
                src = expl.get("source", "unknown")
                source_set[src] = source_set.get(src, 0) + 1
                # Category can serve as a proxy for tier-like grouping
                cat = expl.get("category", "unknown")
                tier_set[cat] = tier_set.get(cat, 0) + 1

        source_dist = "".join(
            f"<dt>{html_lib.escape(k)}</dt><dd>{v}</dd>"
            for k, v in sorted(source_set.items(), key=lambda x: -x[1])
        )
        tier_dist = "".join(
            f"<dt>{html_lib.escape(k)}</dt><dd>{v}</dd>"
            for k, v in sorted(tier_set.items(), key=lambda x: -x[1])
        )

        return f"""\
<div class="card">
  <div class="card-title">📊 Evidence Summary <span class="badge">{evidence_count} total items</span></div>
  <div class="evidence-grid">
    <div class="evidence-stat">
      <div class="value">{evidence_count}</div>
      <div class="label">Evidence Items</div>
    </div>
    <div class="evidence-stat">
      <div class="value">{len(rec.recommendations)}</div>
      <div class="label">Drugs Ranked</div>
    </div>
    <div class="evidence-stat">
      <div class="value">{len(source_set)}</div>
      <div class="label">Sources</div>
    </div>
    <div class="evidence-stat">
      <div class="value">{len(tier_set)}</div>
      <div class="label">Reason Categories</div>
    </div>
  </div>
  <div style="margin-top:12px; display:grid; grid-template-columns:1fr 1fr; gap:16px;">
    <div>
      <div style="font-size:12px;font-weight:700;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.04em;margin-bottom:4px;">Source Distribution</div>
      <dl class="distribution-list">{source_dist or '<span style="color:var(--color-text-muted);font-size:12px;">N/A</span>'}</dl>
    </div>
    <div>
      <div style="font-size:12px;font-weight:700;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.04em;margin-bottom:4px;">Category Distribution</div>
      <dl class="distribution-list">{tier_dist or '<span style="color:var(--color-text-muted);font-size:12px;">N/A</span>'}</dl>
    </div>
  </div>
</div>"""

    # ── Section: Ranking Table ────────────────────────────────────────────

    def _render_ranking_table(self, drugs: list[RecommendationDrugItem]) -> str:
        """Render the top drugs ranking table."""
        if not drugs:
            return ""

        rows = ""
        for d in drugs:
            rank_class = "rank-1" if d.rank == 1 else ""
            score_cls = self._score_class(d.overall_score)
            rows += (
                f"<tr>"
                f'<td class="rank-cell {rank_class}">#{d.rank}</td>'
                f'<td class="drug-name-cell">{html_lib.escape(d.drug_name)}</td>'
                f'<td class="score-cell {score_cls}">{d.overall_score:.4f}</td>'
                f'<td class="score-cell">{d.evidence_score:.4f}</td>'
                f'<td class="score-cell {self._score_class(d.sensitivity_score)}">{d.sensitivity_score:.4f}</td>'
                f'<td class="score-cell {self._score_class(-d.resistance_score)}">{d.resistance_score:.4f}</td>'
                f'<td class="score-cell {self._score_class(-d.conflict_score)}">{d.conflict_score:.4f}</td>'
                f"</tr>\n"
            )

        return f"""\
<div class="card">
  <div class="card-title">🏆 Top Drug Rankings</div>
  <div class="ranking-table-wrap">
    <table class="ranking-table">
      <thead>
        <tr>
          <th>Rank</th>
          <th>Drug Name</th>
          <th style="text-align:right">Overall Score</th>
          <th style="text-align:right">Evidence</th>
          <th style="text-align:right">Sensitivity</th>
          <th style="text-align:right">Resistance</th>
          <th style="text-align:right">Conflict</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
  </div>
</div>"""

    # ── Section: Reason Breakdown ─────────────────────────────────────────

    def _render_reason_breakdown(self, drugs: list[RecommendationDrugItem]) -> str:
        """Render detailed reason breakdown for each drug."""
        if not drugs:
            return ""

        breakdowns = ""
        for d in drugs:
            # Group explanations by category
            grouped: dict[str, list[dict[str, Any]]] = {}
            for expl in d.explanations:
                cat = expl.get("category", "other")
                grouped.setdefault(cat, []).append(expl)

            groups_html = ""
            category_labels = {
                "evidence_support": "📚 Evidence Support",
                "sensitivity": "✅ Sensitivity",
                "resistance": "⚠️ Resistance",
                "conflict": "⚡ Conflict",
                "rule": "📐 Ranking Rules",
            }
            for cat, items in grouped.items():
                label = category_labels.get(cat, cat.replace("_", " ").title())
                items_html = ""
                for item in items:
                    impact = item.get("score_impact", 0.0)
                    impact_str = f"{impact:+.4f}" if impact != 0.0 else "  0.0000"
                    impact_cls = (
                        "positive" if impact > 0 else ("negative" if impact < 0 else "zero")
                    )
                    detail = html_lib.escape(str(item.get("detail", "")))
                    source = html_lib.escape(str(item.get("source", "")))
                    items_html += (
                        f'<div class="reason-item">'
                        f'<span class="reason-impact {impact_cls}">{impact_str}</span>'
                        f'<span class="reason-detail">{detail}</span>'
                        f'<span class="reason-source">{source}</span>'
                        f"</div>\n"
                    )

                groups_html += f"""\
<div class="reason-group">
  <div class="reason-group-title">{html_lib.escape(label)}</div>
  {items_html}
</div>"""

            sub_scores = (
                f"Overall: {d.overall_score:.4f} | "
                f"Evidence: {d.evidence_score:.4f} | "
                f"Sensitivity: {d.sensitivity_score:.4f} | "
                f"Resistance: {d.resistance_score:.4f} | "
                f"Conflict: {d.conflict_score:.4f}"
            )

            breakdowns += f"""\
<div class="drug-breakdown">
  <div class="drug-breakdown-header">
    <h3>#{d.rank} — {html_lib.escape(d.drug_name)}</h3>
    <span class="drug-sub-scores">{html_lib.escape(sub_scores)}</span>
  </div>
  <div class="drug-breakdown-body">
    {groups_html or '<div style="color:var(--color-text-muted);font-size:13px;">No detailed reasons available.</div>'}
  </div>
</div>"""

        return f"""\
<div class="card">
  <div class="card-title">🔬 Reason Breakdown</div>
  {breakdowns}
</div>"""

    # ── Section: Warnings ─────────────────────────────────────────────────

    def _render_warnings(self, drugs: list[RecommendationDrugItem]) -> str:
        """Render warnings for resistance and conflict items."""
        warnings: list[tuple[str, str, str]] = []  # (severity, icon, message)

        for d in drugs:
            if d.resistance_score > 0.5:
                warnings.append((
                    "high",
                    "🛑",
                    f"<strong>{html_lib.escape(d.drug_name)}</strong> has a "
                    f"high resistance score ({d.resistance_score:.2f}). "
                    f"Clinical caution is advised — the tumour may be resistant "
                    f"to this agent.",
                ))
            elif d.resistance_score > 0.2:
                warnings.append((
                    "medium",
                    "⚠️",
                    f"<strong>{html_lib.escape(d.drug_name)}</strong> shows "
                    f"moderate resistance evidence ({d.resistance_score:.2f}). "
                    f"Consider reviewing resistance details before prescribing.",
                ))

            if d.conflict_score > 0.5:
                warnings.append((
                    "high",
                    "⚡",
                    f"<strong>{html_lib.escape(d.drug_name)}</strong> has "
                    f"strongly conflicting evidence ({d.conflict_score:.2f}). "
                    f"Different sources disagree on the direction of effect.",
                ))
            elif d.conflict_score > 0.2:
                warnings.append((
                    "medium",
                    "⚡",
                    f"<strong>{html_lib.escape(d.drug_name)}</strong> has "
                    f"conflicting evidence ({d.conflict_score:.2f}). "
                    f"Review source details for context.",
                ))

            # Check explanations for specific resistance/conflict items
            for expl in d.explanations:
                cat = expl.get("category", "")
                detail = str(expl.get("detail", ""))
                if cat == "resistance" and "resistance" in detail.lower():
                    warnings.append((
                        "low",
                        "ℹ️",
                        f"<strong>{html_lib.escape(d.drug_name)}</strong>: "
                        f"{html_lib.escape(detail[:200])}",
                    ))
                if cat == "conflict" and "conflict" in detail.lower():
                    warnings.append((
                        "low",
                        "ℹ️",
                        f"<strong>{html_lib.escape(d.drug_name)}</strong>: "
                        f"{html_lib.escape(detail[:200])}",
                    ))

        if not warnings:
            return ""

        items_html = "".join(
            f'<li class="warning-{sev}"><span class="warning-icon">{icon}</span>'
            f"<span>{msg}</span></li>\n"
            for sev, icon, msg in warnings
        )

        return f"""\
<div class="card">
  <div class="card-title">⚠️ Clinical Warnings</div>
  <ul class="warning-list">
    {items_html}
  </ul>
</div>"""

    # ── Section: Trace (collapsible) ──────────────────────────────────────

    def _render_trace_section(
        self,
        trace_id: str,
        steps: list[dict[str, Any]],
        rules_evaluated: int,
        rules_fired: int,
    ) -> str:
        """Render a collapsible calculation trace section."""
        if not steps and not trace_id:
            return ""

        steps_html = ""
        for s in steps:
            name = html_lib.escape(str(s.get("step_name", "")))
            stype = html_lib.escape(str(s.get("step_type", "")))
            inp = s.get("input_data", {})
            out = s.get("output_data", {})
            inp_str = html_lib.escape(self._format_trace_data(inp))
            out_str = html_lib.escape(self._format_trace_data(out))
            ts = s.get("timestamp", "")
            dur = s.get("duration_ms")
            dur_str = f" | {dur:.0f}ms" if dur is not None else ""

            steps_html += f"""\
<div class="trace-step">
  <div class="step-header">
    <span class="step-type">{stype}</span>
    <span>{name}{dur_str}</span>
  </div>
  {f'<div class="step-data">→ Input: {inp_str}</div>' if inp_str else ''}
  {f'<div class="step-data">← Output: {out_str}</div>' if out_str else ''}
</div>"""

        rules_info = (
            f"Rules evaluated: {rules_evaluated}, fired: {rules_fired}"
            if rules_evaluated
            else ""
        )

        return f"""\
<details class="trace-details">
  <summary>🔍 Calculation Trace {f'— {trace_id[:16]}…' if trace_id else ''}</summary>
  <div class="trace-content">
    {f'<div style="font-size:12px;color:var(--color-text-muted);margin-bottom:8px;">Trace ID: {html_lib.escape(trace_id)} | {html_lib.escape(rules_info)}</div>' if trace_id else ''}
    {steps_html or '<div style="color:var(--color-text-muted);font-size:13px;">No trace steps recorded.</div>'}
  </div>
</details>"""

    # ── Section: Footer ───────────────────────────────────────────────────

    def _render_footer(self, rec: RecommendationResponse) -> str:
        """Render the report footer with version and disclaimer."""
        return f"""\
<div class="report-footer">
  <div class="version">Engine v{html_lib.escape(rec.engine_version)} — Trace: {html_lib.escape(rec.trace_id)}</div>
  <div class="disclaimer">
    <strong>⚠️ Disclaimer:</strong> This report is generated by an evidence-based
    drug recommendation engine for <strong>research and informational purposes only</strong>.
    It does <strong>not</strong> constitute medical advice. All clinical decisions
    must be made by qualified healthcare professionals based on the full clinical
    context, patient history, and the latest guidelines. The ranking scores are
    derived from aggregated public evidence sources and may not reflect all
    available clinical data.
  </div>
</div>"""

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _score_class(value: float) -> str:
        """Return a CSS class for a numeric score value."""
        if value > 0.05:
            return "score-positive"
        if value < -0.05:
            return "score-negative"
        return "score-neutral"

    @staticmethod
    def _format_trace_data(data: dict[str, Any]) -> str:
        """Format trace data dict into a compact string representation."""
        if not data:
            return ""
        parts: list[str] = []
        for k, v in data.items():
            if isinstance(v, (list, dict)):
                v_str = str(v)
                if len(v_str) > 120:
                    v_str = v_str[:120] + "…"
            else:
                v_str = str(v)
            parts.append(f"{k}: {v_str}")
        return " | ".join(parts)


__all__ = [
    "ReportGenerator",
]
