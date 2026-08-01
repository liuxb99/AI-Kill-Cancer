from src.backend.api.v1.ptc_cohort import OUTCOME_FIELDS_EXCLUDED, WEIGHTS, compare_cases
from src.backend.domain.ptc_research import PTCOutcomeModel, PTCResearchCaseModel, PTCVariantModel


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

    assert sum(WEIGHTS.values()) == 100.0
    assert close_result["score"] == 100.0
    assert close_result["shared_genes"] == ["BRAF"]
    assert close_result["shared_protein_variants"] == ["BRAF:P.V600E"]
    assert close_result["components"]["genes"] == 42.0
    assert close_result["components"]["protein_variants"] == 23.0
    assert "vital_status" not in close_result["components"]
    assert close_result["score"] > distant_result["score"]


def test_missing_pre_outcome_fields_do_not_create_false_similarity():
    anchor = make_case("A", stage="Stage I", gene="BRAF", protein="p.V600E")
    candidate = make_case("B", stage="Stage I", gene="BRAF", protein="p.V600E")
    candidate.age_range = None
    candidate.sex = None

    result = compare_cases(anchor, candidate)

    assert result["components"]["age_range"] == 0.0
    assert result["components"]["sex"] == 0.0
    assert result["score"] == 90.0


def test_outcome_changes_never_change_similarity_score():
    anchor = make_case("A", stage="Stage I", gene="BRAF", protein="p.V600E")
    alive = make_case("B", stage="Stage I", gene="BRAF", protein="p.V600E")
    deceased = make_case("C", stage="Stage I", gene="BRAF", protein="p.V600E")

    alive.vital_status = "Alive"
    alive.days_to_last_follow_up = 2500
    alive.days_to_death = None
    alive.outcomes = [
        PTCOutcomeModel(
            outcome_id="B:OS",
            case_id="B",
            source_dataset="TCGA-THCA",
            outcome_type="overall_survival",
            outcome_value="censored",
        )
    ]

    deceased.vital_status = "Dead"
    deceased.days_to_last_follow_up = 120
    deceased.days_to_death = 150
    deceased.outcomes = [
        PTCOutcomeModel(
            outcome_id="C:OS",
            case_id="C",
            source_dataset="TCGA-THCA",
            outcome_type="overall_survival",
            outcome_value="event",
        )
    ]

    alive_result = compare_cases(anchor, alive)
    deceased_result = compare_cases(anchor, deceased)

    assert alive_result["score"] == deceased_result["score"] == 100.0
    assert alive_result["components"] == deceased_result["components"]
    assert alive_result["case_facts"]["vital_status"] == "Alive"
    assert deceased_result["case_facts"]["vital_status"] == "Dead"
    assert set(OUTCOME_FIELDS_EXCLUDED) == {
        "vital_status",
        "days_to_last_follow_up",
        "days_to_death",
        "outcomes",
    }
