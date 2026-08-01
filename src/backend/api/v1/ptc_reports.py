"""On-demand traceable PTC research report exports.

Reports are generated from the same deterministic evidence-grounded assistant
used by the PTC research workbench. They contain de-identified public research
records only and are not clinical reports or prescribing documents.
"""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.v1.ptc_assistant import PTCAssistantRequest, ask_ptc_assistant
from src.backend.database.session import get_db

router = APIRouter(prefix="/ptc-reports", tags=["ptc-reports"])

DEFAULT_QUESTION = (
    "Summarize this de-identified PTC research case, its molecular variants, "
    "candidate research therapies, evidence, clinical trials, and open-full-text assets."
)


def _safe(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _report_payload(answer: dict[str, Any]) -> dict[str, Any]:
    figures = sum(len(item.get("figures") or []) for item in answer.get("evidence", []))
    tables = sum(len(item.get("tables") or []) for item in answer.get("evidence", []))
    return {
        "schema_version": "ptc-research-report-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "report_type": "deidentified_public_research",
        "case_id": answer["case_id"],
        "selected_gene": answer.get("selected_gene"),
        "question": answer.get("question"),
        "executive_summary": answer.get("answer"),
        "case_facts": answer.get("case_facts", {}),
        "pathway": answer.get("pathway", {}),
        "therapies": answer.get("therapies", []),
        "evidence": answer.get("evidence", []),
        "trials": answer.get("trials", []),
        "assets": {"figures": figures, "tables": tables},
        "trace": answer.get("trace", []),
        "source_actions": answer.get("actions", []),
        "limitations": [
            "This report uses de-identified public research records and does not represent a clinical patient record.",
            "Candidate therapies and trials are research links, not treatment recommendations or eligibility determinations.",
            "Cell-level 3D is a scientific illustration; protein coordinates are public reference structures.",
            answer.get("disclaimer", "For research and education only."),
        ],
    }


def render_ptc_report_html(report: dict[str, Any]) -> str:
    facts = report.get("case_facts", {})
    pathway = report.get("pathway", {})
    assets = report.get("assets", {})
    variants = facts.get("variants", [])
    therapies = report.get("therapies", [])
    evidence = report.get("evidence", [])
    trials = report.get("trials", [])
    trace = report.get("trace", [])

    variant_rows = "".join(
        f"<tr><td>{_safe(item.get('gene'))}</td>"
        f"<td>{_safe(item.get('protein_change') or item.get('variant_id'))}</td>"
        f"<td>{_safe(item.get('classification'))}</td></tr>"
        for item in variants
    ) or '<tr><td colspan="3">No imported variants</td></tr>'
    therapy_rows = "".join(
        f"<tr><td>{_safe(item.get('name'))}</td>"
        f"<td>{_safe(item.get('approval_status'))}</td>"
        f"<td>{_safe(item.get('source'))}</td></tr>"
        for item in therapies
    ) or '<tr><td colspan="3">No persisted therapy records</td></tr>'
    trial_rows = "".join(
        f"<tr><td>{_safe(item.get('nct_id'))}</td>"
        f"<td>{_safe(item.get('title'))}</td>"
        f"<td>{_safe(item.get('status'))}</td></tr>"
        for item in trials
    ) or '<tr><td colspan="3">No matching trials</td></tr>'
    evidence_cards = "".join(
        "<article class='evidence'>"
        f"<h4>{_safe(item.get('title') or item.get('evidence_key'))}</h4>"
        f"<p><strong>{_safe(item.get('source'))}</strong> · {_safe(item.get('level'))}</p>"
        f"<p>{_safe(item.get('summary'))}</p>"
        f"<p>Figures: {len(item.get('figures') or [])} · Tables: {len(item.get('tables') or [])}</p>"
        f"<p><a href='{_safe(item.get('url'))}'>Source</a></p>"
        "</article>"
        for item in evidence
    ) or "<p>No linked evidence records.</p>"
    trace_rows = "".join(
        f"<tr><td>{_safe(item.get('step'))}</td>"
        f"<td>{_safe(item.get('name'))}</td>"
        f"<td>{_safe(item.get('records'))}</td></tr>"
        for item in trace
    )
    limitations = "".join(f"<li>{_safe(item)}</li>" for item in report.get("limitations", []))
    report_json = json.dumps(report, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PTC Research Report {_safe(report.get('case_id'))}</title>
<style>
:root{{--ink:#172033;--muted:#657087;--line:#d9dfeb;--accent:#5b21b6;--paper:#fff}}
*{{box-sizing:border-box}} body{{margin:0;background:#eef2f7;color:var(--ink);font:15px/1.55 Arial,sans-serif}}
main{{max-width:1040px;margin:24px auto;background:var(--paper);padding:42px;box-shadow:0 12px 45px #1f293720}}
h1,h2,h3,h4{{line-height:1.2}} h1{{margin:0;font-size:30px}} h2{{margin-top:32px;border-bottom:2px solid var(--accent);padding-bottom:8px}}
.meta{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:22px 0}} .card,.evidence{{border:1px solid var(--line);border-radius:10px;padding:14px}}
table{{width:100%;border-collapse:collapse}} th,td{{border:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}} th{{background:#f4f1ff}}
.notice{{background:#fff7ed;border:1px solid #fdba74;padding:14px;border-radius:10px}} .actions{{position:sticky;top:0;background:white;padding:10px 0;text-align:right}}
button{{border:0;border-radius:7px;padding:9px 14px;background:var(--accent);color:white;cursor:pointer}} a{{color:#4f46e5}}
@media print{{body{{background:white}} main{{margin:0;max-width:none;box-shadow:none;padding:16mm}} .actions{{display:none}} a{{color:inherit;text-decoration:none}}}}
</style></head><body><main>
<div class="actions"><button onclick="window.print()">Print / Save PDF</button></div>
<p>AI-Kill-Cancer · PTC Research Report</p><h1>{_safe(report.get('case_id'))}</h1>
<div class="meta"><div class="card"><small>Generated</small><br>{_safe(report.get('generated_at'))}</div><div class="card"><small>Gene</small><br>{_safe(report.get('selected_gene') or 'All')}</div><div class="card"><small>Figures</small><br>{_safe(assets.get('figures'))}</div><div class="card"><small>Tables</small><br>{_safe(assets.get('tables'))}</div></div>
<section><h2>Executive summary</h2><p>{_safe(report.get('executive_summary'))}</p></section>
<section><h2>Research case facts</h2><p>Source: {_safe(facts.get('source_dataset'))} · Stage: {_safe(facts.get('pathologic_stage'))} · Vital status: {_safe(facts.get('vital_status'))}</p>
<table><thead><tr><th>Gene</th><th>Variant</th><th>Classification</th></tr></thead><tbody>{variant_rows}</tbody></table></section>
<section><h2>Molecular pathway</h2><div class="card"><strong>{_safe(report.get('selected_gene'))}</strong> · {_safe(pathway.get('pathway'))}<br>{_safe(pathway.get('protein_domain'))}</div></section>
<section><h2>Candidate research therapies</h2><table><thead><tr><th>Therapy</th><th>Status</th><th>Source</th></tr></thead><tbody>{therapy_rows}</tbody></table></section>
<section><h2>Evidence and open-full-text assets</h2>{evidence_cards}</section>
<section><h2>Clinical trials</h2><table><thead><tr><th>NCT</th><th>Title</th><th>Status</th></tr></thead><tbody>{trial_rows}</tbody></table></section>
<section><h2>Calculation trace</h2><table><thead><tr><th>Step</th><th>Operation</th><th>Records</th></tr></thead><tbody>{trace_rows}</tbody></table></section>
<section class="notice"><h2>Limitations</h2><ul>{limitations}</ul></section>
<script type="application/json" id="ptc-report-data">{report_json}</script>
</main></body></html>"""


async def _build(case_id: str, gene: str | None, question: str | None, db: AsyncSession) -> dict[str, Any]:
    answer = await ask_ptc_assistant(
        PTCAssistantRequest(case_id=case_id, gene=gene, question=question or DEFAULT_QUESTION),
        db,
    )
    return _report_payload(answer)


@router.get("/case/{case_id}/json")
async def get_ptc_report_json(
    case_id: str,
    gene: str | None = Query(default=None, max_length=32),
    question: str | None = Query(default=None, max_length=2000),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    return JSONResponse(content=await _build(case_id, gene, question, db))


@router.get("/case/{case_id}/html")
async def get_ptc_report_html(
    case_id: str,
    gene: str | None = Query(default=None, max_length=32),
    question: str | None = Query(default=None, max_length=2000),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    report = await _build(case_id, gene, question, db)
    return HTMLResponse(content=render_ptc_report_html(report))


__all__ = ["router", "render_ptc_report_html"]
