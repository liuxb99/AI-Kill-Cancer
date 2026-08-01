from src.backend.api.v1.ptc_reports import _report_payload, render_ptc_report_html


def _answer():
    return {
        "case_id": "TCGA-REPORT-001",
        "question": "Summarize BRAF V600E evidence",
        "selected_gene": "BRAF",
        "answer": "BRAF V600E is linked to the MAPK pathway and persisted research evidence.",
        "case_facts": {
            "source_dataset": "TCGA-THCA",
            "pathologic_stage": "Stage I",
            "vital_status": "Alive",
            "variants": [
                {
                    "variant_id": "v1",
                    "gene": "BRAF",
                    "protein_change": "p.V600E",
                    "classification": "Missense_Mutation",
                }
            ],
        },
        "pathway": {
            "pathway": "MAPK / ERK",
            "protein_domain": "Serine/threonine kinase domain",
        },
        "therapies": [
            {
                "therapy_key": "openfda:dabrafenib",
                "name": "Dabrafenib",
                "approval_status": "FDA label available",
                "source": "openFDA",
            }
        ],
        "evidence": [
            {
                "evidence_key": "e1",
                "source": "PubMed",
                "title": "BRAF V600E PTC study",
                "level": "published_literature",
                "summary": "Study summary",
                "url": "https://pubmed.ncbi.nlm.nih.gov/1/",
                "figures": [{"id": "fig1"}],
                "tables": [{"id": "tbl1"}],
            }
        ],
        "trials": [
            {
                "nct_id": "NCT00000001",
                "title": "BRAF thyroid trial",
                "status": "RECRUITING",
            }
        ],
        "trace": [
            {"step": 1, "name": "resolve_case", "records": 1},
            {"step": 2, "name": "resolve_gene_and_variants", "records": 1},
        ],
        "actions": [{"type": "open_3d", "gene": "BRAF"}],
        "disclaimer": "For research and education only.",
    }


def test_report_payload_preserves_auditable_chain():
    report = _report_payload(_answer())

    assert report["schema_version"] == "ptc-research-report-v1"
    assert report["case_id"] == "TCGA-REPORT-001"
    assert report["selected_gene"] == "BRAF"
    assert report["case_facts"]["variants"][0]["protein_change"] == "p.V600E"
    assert report["therapies"][0]["name"] == "Dabrafenib"
    assert report["trials"][0]["nct_id"] == "NCT00000001"
    assert report["assets"] == {"figures": 1, "tables": 1}
    assert report["trace"][0]["name"] == "resolve_case"
    assert len(report["limitations"]) >= 4


def test_printable_html_contains_report_sections_and_embedded_json():
    report = _report_payload(_answer())
    rendered = render_ptc_report_html(report)

    assert "Print / Save PDF" in rendered
    assert "TCGA-REPORT-001" in rendered
    assert "BRAF" in rendered
    assert "p.V600E" in rendered
    assert "Dabrafenib" in rendered
    assert "BRAF V600E PTC study" in rendered
    assert "NCT00000001" in rendered
    assert "Calculation trace" in rendered
    assert 'id="ptc-report-data"' in rendered
    assert "@media print" in rendered
