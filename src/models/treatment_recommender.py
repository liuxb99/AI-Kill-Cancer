import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass, field
from typing import Optional


CANCER_DRUG_DB = {
    "肺癌": {
        "化疗": [
            {"name": "順鉑+培美曲塞", "indication": "肺腺癌一線", "avg_response": 0.45},
            {"name": "卡鉑+紫杉醇", "indication": "肺鱗癌一線", "avg_response": 0.42},
            {"name": "多西他賽", "indication": "二線治療", "avg_response": 0.28},
        ],
        "標靶": [
            {"name": "吉非替尼", "indication": "EGFR突變", "avg_response": 0.72},
            {"name": "奧希替尼", "indication": "EGFR T790M", "avg_response": 0.78},
            {"name": "克唑替尼", "indication": "ALK融合", "avg_response": 0.74},
            {"name": "阿來替尼", "indication": "ALK融合一線", "avg_response": 0.82},
        ],
        "免疫": [
            {"name": "帕博利珠單抗", "indication": "PD-L1≥50%", "avg_response": 0.58},
            {"name": "納武利尤單抗", "indication": "PD-L1≥1%", "avg_response": 0.44},
            {"name": "阿替利珠單抗", "indication": "一線聯合化療", "avg_response": 0.52},
        ],
    },
    "乳腺癌": {
        "化疗": [
            {"name": "阿黴素+環磷醯胺", "indication": "一線化療", "avg_response": 0.55},
            {"name": "紫杉醇", "indication": "輔助化療", "avg_response": 0.48},
        ],
        "標靶": [
            {"name": "曲妥珠單抗", "indication": "HER2+", "avg_response": 0.80},
            {"name": "帕妥珠單抗", "indication": "HER2+聯合", "avg_response": 0.76},
            {"name": "拉帕替尼", "indication": "HER2+二線", "avg_response": 0.55},
            {"name": "帕博西尼", "indication": "HR+/HER2-", "avg_response": 0.62},
        ],
        "免疫": [
            {"name": "阿替利珠單抗", "indication": "三陰性PD-L1+", "avg_response": 0.50},
        ],
    },
    "大腸癌": {
        "化疗": [
            {"name": "FOLFOX", "indication": "一線治療", "avg_response": 0.56},
            {"name": "FOLFIRI", "indication": "一線/二線", "avg_response": 0.50},
            {"name": "卡培他濱", "indication": "輔助治療", "avg_response": 0.40},
        ],
        "標靶": [
            {"name": "西妥昔單抗", "indication": "RAS野生型", "avg_response": 0.65},
            {"name": "貝伐珠單抗", "indication": "VEGF抑制", "avg_response": 0.58},
            {"name": "帕尼單抗", "indication": "RAS野生型", "avg_response": 0.60},
        ],
        "免疫": [
            {"name": "帕博利珠單抗", "indication": "MSI-H", "avg_response": 0.65},
            {"name": "納武利尤單抗", "indication": "MSI-H", "avg_response": 0.60},
        ],
    },
}


@dataclass
class TreatmentRecommenderConfig:
    input_dim: int = 20500
    clinical_dim: int = 20
    hidden_dims: tuple = (512, 256, 128)
    dropout: float = 0.3
    num_drug_classes: int = 64
    top_k: int = 5
    use_batch_norm: bool = True


class TreatmentRecommender(nn.Module):

    def __init__(self, config: TreatmentRecommenderConfig):
        super().__init__()
        self.config = config

        fusion_dim = config.input_dim + config.clinical_dim
        layers = []
        prev = fusion_dim
        for h in config.hidden_dims:
            layers.append(nn.Linear(prev, h))
            if config.use_batch_norm:
                layers.append(nn.BatchNorm1d(h))
            layers.append(nn.ReLU(inplace=True))
            layers.append(nn.Dropout(config.dropout))
            prev = h

        self.fusion_encoder = nn.Sequential(*layers)
        self.response_head = nn.Linear(prev, config.num_drug_classes)

    def forward(self, gene_expr: torch.Tensor, clinical: torch.Tensor) -> torch.Tensor:
        x = torch.cat([gene_expr, clinical], dim=1)
        features = self.fusion_encoder(x)
        return self.response_head(features)

    def recommend(
        self,
        gene_expr: torch.Tensor,
        clinical: torch.Tensor,
        cancer_type: str,
        top_k: Optional[int] = None,
    ) -> list[dict]:
        k = top_k or self.config.top_k
        logits = self.forward(gene_expr, clinical)
        drug_probs = torch.sigmoid(logits)

        db = CANCER_DRUG_DB.get(cancer_type, {})
        flat_drugs = []
        for category, drugs in db.items():
            for drug in drugs:
                flat_drugs.append({**drug, "category": category})

        scored = []
        for i, drug in enumerate(flat_drugs):
            pred_prob = float(drug_probs[0, i].item()) if i < drug_probs.shape[1] else 0.5
            blended = 0.7 * pred_prob + 0.3 * drug["avg_response"]
            scored.append({
                "rank": 0,
                "drug_name": drug["name"],
                "category": drug["category"],
                "indication": drug["indication"],
                "predicted_efficacy": round(blended, 4),
                "model_confidence": round(pred_prob, 4),
                "population_avg_response": drug["avg_response"],
            })

        scored.sort(key=lambda x: x["predicted_efficacy"], reverse=True)
        for rank, item in enumerate(scored, 1):
            item["rank"] = rank

        return scored[:k]

    @torch.no_grad()
    def recommend_from_numpy(
        self,
        gene_expr: np.ndarray,
        clinical: np.ndarray,
        cancer_type: str,
        top_k: Optional[int] = None,
    ) -> list[dict]:
        ge = torch.tensor(gene_expr, dtype=torch.float32)
        cl = torch.tensor(clinical, dtype=torch.float32)
        if ge.ndim == 1:
            ge = ge.unsqueeze(0)
        if cl.ndim == 1:
            cl = cl.unsqueeze(0)
        return self.recommend(ge, cl, cancer_type, top_k)


def lookup_drug_knowledge(cancer_type: str, category: Optional[str] = None) -> list[dict]:
    db = CANCER_DRUG_DB.get(cancer_type, {})
    if category:
        return [
            {**d, "category": category}
            for d in db.get(category, [])
        ]
    result = []
    for cat, drugs in db.items():
        for d in drugs:
            result.append({**d, "category": cat})
    return result


def list_available_cancers() -> list[str]:
    return list(CANCER_DRUG_DB.keys())
