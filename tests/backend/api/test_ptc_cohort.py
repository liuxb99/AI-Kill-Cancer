from src.backend.api.v1.ptc_cohort import compare_cases
from src.backend.domain.ptc_research import PTCResearchCaseModel, PTCVariantModel


def make_case(case_id: str, *, stage: str, gene: str, protein: str, t: str = "T1", n: str = "N0"):
    case = PTCResearchCaseModel(
        case_id=case_id,
        source_dataset="TCGA-THCA",
        source_project="TCGA-THCA",
        disease="papillary_thyroid_carcinoma",
        pathologic_stage=stage,
        t_status=t,
        n_status=n,
        m_status="M0",
        sex="female",
        age_range="40-49",
        vital_status="Alive",
    )
    case.variants = [
        PTCVariantModel(
            variant_id=f"{case_id}:{gene}:{protein}",
            case_id=case_id,
            source_dataset="TCGA-THCA",
            gene=gene,
            protein_change=protein,
            classification="Missense_Mutation",
        )
    ]
    case.outcomes = []
    return case


def test_identical_molecular_case_scores_higher_than_different_case():
    anchor = make_case("A", stage="Stage I", gene="BRAF", protein="p.V600E")
    close = make_case("B", stage="Stage I", gene="BRAF", protein="p.V600E")
    distant = make_case("C", stage="Stage IV", gene="RET", protein="fusion", t="T4", n="N1")

    close_result = compare_cases(anchor, close)
    distant_result = compare_cases(anchor, distant)

    assert close_result["score"] == 100.0
    assert close_result["shared_genes"] == ["BRAF"]
    assert close_result["shared_protein_variants"] == ["BRAF:P.V600E"]
    assert close_result["components"]["genes"] == 40.0
    assert close_result["components"]["protein_variants"] == 20.0
    assert close_result["score"] > distant_result["score"]


def test_missing_fields_do_not_create_false_similarity():
    anchor = make_case("A", stage="Stage I", gene="BRAF", protein="p.V600E")
    candidate = make_case("B", stage="Stage I", gene="BRAF", protein="p.V600E")
    candidate.age_range = None
    candidate.sex = None
    candidate.vital_status = None

    result = compare_cases(anchor, candidate)

    assert result["components"]["age_range"] == 0.0
    assert result["components"]["sex"] == 0.0
    assert result["components"]["vital_status"] == 0.0
    assert result["score"] == 85.0
