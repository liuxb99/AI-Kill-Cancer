import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass
from typing import Optional


@dataclass
class CancerClassifierConfig:
    input_dim: int = 20500
    hidden_dims: tuple = (1024, 512, 256, 128)
    dropout: float = 0.3
    num_cancer_types: int = 3
    num_subtypes: int = 6
    num_stages: int = 4
    use_batch_norm: bool = True


class CancerClassifier(nn.Module):

    def __init__(self, config: CancerClassifierConfig):
        super().__init__()
        self.config = config

        layers = []
        prev_dim = config.input_dim
        for i, h_dim in enumerate(config.hidden_dims):
            layers.append(nn.Linear(prev_dim, h_dim))
            if config.use_batch_norm:
                layers.append(nn.BatchNorm1d(h_dim))
            layers.append(nn.ReLU(inplace=True))
            layers.append(nn.Dropout(config.dropout))
            prev_dim = h_dim

        self.encoder = nn.Sequential(*layers)

        self.cancer_type_head = nn.Linear(prev_dim, config.num_cancer_types)
        self.subtype_head = nn.Linear(prev_dim, config.num_subtypes)
        self.stage_head = nn.Linear(prev_dim, config.num_stages)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        features = self.encoder(x)
        return {
            "cancer_type": self.cancer_type_head(features),
            "subtype": self.subtype_head(features),
            "stage": self.stage_head(features),
        }

    def predict_proba(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        logits = self.forward(x)
        return {
            "cancer_type": F.softmax(logits["cancer_type"], dim=1),
            "subtype": F.softmax(logits["subtype"], dim=1),
            "stage": F.softmax(logits["stage"], dim=1),
        }

    def predict(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        probs = self.predict_proba(x)
        return {
            "cancer_type": probs["cancer_type"].argmax(dim=1),
            "subtype": probs["subtype"].argmax(dim=1),
            "stage": probs["stage"].argmax(dim=1),
        }
