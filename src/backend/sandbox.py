import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SandboxConfig:
    max_input_size: int = 10_000
    max_latency_ms: int = 30_000
    allowed_models: list[str] = field(default_factory=lambda: [
        "cancer_classifier",
        "drug_response",
        "mutation_impact",
        "treatment_recommender",
    ])


@dataclass
class SandboxResult:
    run_id: str
    model: str
    input_summary: str
    output: dict[str, Any]
    latency_ms: int
    error: str | None = None


class ModelSandbox:
    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        self.history: list[SandboxResult] = []
        self._registry: dict[str, callable] = {
            "cancer_classifier": self._classify,
            "drug_response": self._predict_drug_response,
            "mutation_impact": self._assess_mutation,
            "treatment_recommender": self._recommend_treatment,
        }

    def register_model(self, name: str, fn: callable):
        self._registry[name] = fn
        if name not in self.config.allowed_models:
            self.config.allowed_models.append(name)

    def run(self, model: str, payload: dict) -> SandboxResult:
        run_id = str(uuid.uuid4())
        start = time.monotonic()

        if model not in self.config.allowed_models:
            return self._error_result(run_id, model, f"Model '{model}' not allowed")

        if model not in self._registry:
            return self._error_result(run_id, model, f"Model '{model}' not registered")

        input_str = str(payload)
        if len(input_str) > self.config.max_input_size:
            return self._error_result(run_id, model, "Input payload too large")

        try:
            output = self._registry[model](payload)
            latency = int((time.monotonic() - start) * 1000)

            if latency > self.config.max_latency_ms:
                logger.warning("Run %s exceeded latency limit: %dms", run_id, latency)

            result = SandboxResult(
                run_id=run_id,
                model=model,
                input_summary=input_str[:120],
                output=output,
                latency_ms=latency,
            )
        except Exception as e:
            logger.exception("Sandbox run %s failed", run_id)
            latency = int((time.monotonic() - start) * 1000)
            result = SandboxResult(
                run_id=run_id,
                model=model,
                input_summary=input_str[:120],
                output={},
                latency_ms=latency,
                error=str(e),
            )

        self.history.append(result)
        if len(self.history) > 1000:
            self.history = self.history[-500:]

        return result

    def get_history(self, limit: int = 50) -> list[SandboxResult]:
        return self.history[-limit:]

    def clear_history(self):
        self.history.clear()

    # --- Built-in mock models ---

    def _classify(self, payload: dict) -> dict:
        biomarkers = payload.get("biomarkers", {})
        age = payload.get("age", 50)
        family_history = payload.get("family_history", [])

        if any(v > 50 for v in biomarkers.values()):
            return {
                "predictions": [
                    {"cancer_type": "Breast Cancer", "probability": 0.94, "risk": "High"},
                    {"cancer_type": "Ovarian Cancer", "probability": 0.23, "risk": "Low"},
                ],
                "top_match": "Breast Cancer",
            }
        if age > 60:
            return {
                "predictions": [
                    {"cancer_type": "Lung Cancer", "probability": 0.76, "risk": "Moderate"},
                    {"cancer_type": "Colorectal Cancer", "probability": 0.31, "risk": "Low"},
                ],
                "top_match": "Lung Cancer",
            }
        if family_history:
            fh = family_history[0]
            return {
                "predictions": [
                    {"cancer_type": fh, "probability": 0.62, "risk": "Moderate"},
                ],
                "top_match": fh,
            }
        return {
            "predictions": [
                {"cancer_type": "Unknown", "probability": 0.12, "risk": "Low"},
            ],
            "top_match": "Unknown",
        }

    def _predict_drug_response(self, payload: dict) -> dict:
        drug = payload.get("drug", "unknown")
        cell_line = payload.get("cell_line", "default")

        responses = {
            "Trastuzumab": {"IC50": 0.042, "classification": "sensitive", "mechanism": "HER2 inhibitor"},
            "Tamoxifen": {"IC50": 1.230, "classification": "resistant", "mechanism": "ER antagonist"},
            "Cisplatin": {"IC50": 0.510, "classification": "intermediate", "mechanism": "DNA crosslinker"},
            "Paclitaxel": {"IC50": 0.089, "classification": "sensitive", "mechanism": "Microtubule stabilizer"},
        }

        result = responses.get(drug, {"IC50": 99.0, "classification": "unknown", "mechanism": "unknown"})
        return {
            "drug": drug,
            "cell_line": cell_line,
            "IC50": result["IC50"],
            "unit": "µM",
            "classification": result["classification"],
            "mechanism": result["mechanism"],
        }

    def _assess_mutation(self, payload: dict) -> dict:
        variant = payload.get("variant", "")
        gene = payload.get("gene", "")

        known_variants = {
            "BRCA1 c.5266dupC": {"score": 0.98, "class": "Pathogenic", "impact": "Protein truncation"},
            "EGFR L858R": {"score": 0.87, "class": "Pathogenic", "impact": "Kinase activation"},
            "BRAF V600E": {"score": 0.95, "class": "Pathogenic", "impact": "MAPK pathway hyperactivation"},
            "TP53 R175H": {"score": 0.91, "class": "Pathogenic", "impact": "DNA binding domain disruption"},
            "KRAS G12C": {"score": 0.93, "class": "Pathogenic", "impact": "GTPase inactivation"},
        }

        result = known_variants.get(variant, {"score": 0.50, "class": "VUS", "impact": "Unknown significance"})
        return {
            "variant": variant,
            "gene": gene or variant.split(" ")[0] if " " in variant else gene,
            "pathogenicity_score": result["score"],
            "classification": result["class"],
            "functional_impact": result["impact"],
        }

    def _recommend_treatment(self, payload: dict) -> dict:
        cancer_type = payload.get("cancer_type", "")
        stage = int(payload.get("stage", 2))
        biomarkers = payload.get("biomarkers", {})

        her2 = biomarkers.get("HER2", 0)
        er = biomarkers.get("ER", 0)

        options = []
        if stage <= 2:
            options.append({
                "name": f"{cancer_type} Stage {stage} Standard Protocol",
                "success_rate": 0.85,
                "side_effects": ["Fatigue", "Nausea", "Hair loss"],
            })
            if her2 > 2.0:
                options.append({
                    "name": "Targeted Therapy (HER2 inhibitors)",
                    "success_rate": 0.78,
                    "side_effects": ["Skin rash", "Diarrhea", "Cardiotoxicity"],
                })
            if er > 1.0:
                options.append({
                    "name": "Endocrine Therapy (ER antagonists)",
                    "success_rate": 0.72,
                    "side_effects": ["Hot flashes", "Joint pain", "Fatigue"],
                })
        else:
            options.append({
                "name": f"{cancer_type} Stage {stage} Aggressive Protocol",
                "success_rate": 0.45,
                "side_effects": ["Immunosuppression", "Organ toxicity", "Severe fatigue"],
            })
            options.append({
                "name": "Immunotherapy (PD-1/PD-L1)",
                "success_rate": 0.38,
                "side_effects": ["Immune-related adverse events", "Fatigue", "Rash"],
            })
            options.append({
                "name": "Clinical Trial (Experimental)",
                "success_rate": 0.30,
                "side_effects": ["Varies by protocol", "Unknown long-term effects"],
                "cost": "$0 (sponsored)",
            })

        return {
            "cancer_type": cancer_type,
            "stage": str(stage),
            "treatment_options": options,
            "recommendation": options[0]["name"] if options else None,
        }

    def _error_result(self, run_id: str, model: str, message: str) -> SandboxResult:
        result = SandboxResult(
            run_id=run_id,
            model=model,
            input_summary="",
            output={},
            latency_ms=0,
            error=message,
        )
        self.history.append(result)
        return result


# Module-level singleton
sandbox = ModelSandbox()
