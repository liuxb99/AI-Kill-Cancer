import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class DrugResponseConfig:
    gene_input_dim: int = 20500
    drug_embed_dim: int = 128
    hidden_dims: tuple = (512, 256, 64)
    dropout: float = 0.3
    use_batch_norm: bool = True
    drug_vocab_size: int = 100


class DrugResponsePredictor(nn.Module):

    def __init__(self, config: DrugResponseConfig):
        super().__init__()
        self.config = config

        gene_encoder = []
        prev = config.gene_input_dim
        for h in config.hidden_dims:
            gene_encoder.append(nn.Linear(prev, h))
            if config.use_batch_norm:
                gene_encoder.append(nn.BatchNorm1d(h))
            gene_encoder.append(nn.ReLU(inplace=True))
            gene_encoder.append(nn.Dropout(config.dropout))
            prev = h
        self.gene_encoder = nn.Sequential(*gene_encoder)

        self.drug_embedding = nn.Embedding(
            config.drug_vocab_size, config.drug_embed_dim
        )
        self.drug_proj = nn.Linear(config.drug_embed_dim, prev)

        self.fusion = nn.Sequential(
            nn.Linear(prev * 2, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(config.dropout),
            nn.Linear(128, 32),
            nn.ReLU(inplace=True),
            nn.Linear(32, 1),
        )

    def forward(
        self,
        gene_expr: torch.Tensor,
        drug_ids: torch.Tensor,
    ) -> torch.Tensor:
        gene_feat = self.gene_encoder(gene_expr)
        drug_feat = self.drug_proj(self.drug_embedding(drug_ids))
        combined = torch.cat([gene_feat, drug_feat], dim=1)
        return torch.sigmoid(self.fusion(combined)).squeeze(-1)

    @torch.no_grad()
    def predict_response(
        self,
        gene_expr: Union[np.ndarray, torch.Tensor],
        drug_ids: Union[np.ndarray, torch.Tensor],
    ) -> np.ndarray:
        if isinstance(gene_expr, np.ndarray):
            gene_expr = torch.tensor(gene_expr, dtype=torch.float32)
        if isinstance(drug_ids, np.ndarray):
            drug_ids = torch.tensor(drug_ids, dtype=torch.long)
        if gene_expr.ndim == 1:
            gene_expr = gene_expr.unsqueeze(0)
        if drug_ids.ndim == 0:
            drug_ids = drug_ids.unsqueeze(0)

        self.eval()
        probs = self.forward(gene_expr, drug_ids)
        return probs.cpu().numpy()

    @torch.no_grad()
    def rank_drugs(
        self,
        gene_expr: np.ndarray,
        drug_id_list: list[int],
    ) -> list[dict]:
        ge = torch.tensor(gene_expr, dtype=torch.float32)
        if ge.ndim == 1:
            ge = ge.unsqueeze(0)
        ge = ge.expand(len(drug_id_list), -1)
        dids = torch.tensor(drug_id_list, dtype=torch.long)

        probs = self.forward(ge, dids).cpu().numpy()
        results = [
            {"drug_id": did, "response_probability": round(float(p), 4)}
            for did, p in zip(drug_id_list, probs)
        ]
        results.sort(key=lambda x: x["response_probability"], reverse=True)
        for rank, item in enumerate(results, 1):
            item["rank"] = rank
        return results
