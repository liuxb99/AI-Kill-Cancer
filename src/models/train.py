import os
import json
import time
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)

from .cancer_classifier import CancerClassifier, CancerClassifierConfig


@dataclass
class TrainingConfig:
    batch_size: int = 64
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    num_epochs: int = 100
    early_stop_patience: int = 10
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    save_dir: str = "checkpoints"
    log_interval: int = 10
    loss_weights: dict = field(default_factory=lambda: {
        "cancer_type": 1.0,
        "subtype": 1.0,
        "stage": 0.5,
    })


class GeneExpressionDataset(Dataset):

    def __init__(self, X: np.ndarray, y_cancer: np.ndarray,
                 y_subtype: np.ndarray, y_stage: np.ndarray):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y_cancer = torch.tensor(y_cancer, dtype=torch.long)
        self.y_subtype = torch.tensor(y_subtype, dtype=torch.long)
        self.y_stage = torch.tensor(y_stage, dtype=torch.long)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return {
            "input": self.X[idx],
            "cancer_type": self.y_cancer[idx],
            "subtype": self.y_subtype[idx],
            "stage": self.y_stage[idx],
        }


class Trainer:

    def __init__(self, model: CancerClassifier, config: TrainingConfig):
        self.model = model
        self.config = config
        self.device = torch.device(config.device)
        self.model.to(self.device)

        self.optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=config.learning_rate,
            weight_decay=config.weight_decay,
        )
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode="min", factor=0.5, patience=5
        )
        self.criterion = nn.CrossEntropyLoss()
        self.best_val_loss = float("inf")
        self.early_stop_counter = 0
        self.history = {"train_loss": [], "val_loss": [], "val_metrics": []}

    def _compute_loss(self, outputs: dict, targets: dict) -> torch.Tensor:
        w = self.config.loss_weights
        loss = 0.0
        for key in ["cancer_type", "subtype", "stage"]:
            loss += w[key] * self.criterion(outputs[key], targets[key])
        return loss

    def _train_epoch(self, loader: DataLoader) -> float:
        self.model.train()
        total_loss = 0.0
        for batch_idx, batch in enumerate(loader):
            x = batch["input"].to(self.device)
            targets = {
                "cancer_type": batch["cancer_type"].to(self.device),
                "subtype": batch["subtype"].to(self.device),
                "stage": batch["stage"].to(self.device),
            }

            self.optimizer.zero_grad()
            outputs = self.model(x)
            loss = self._compute_loss(outputs, targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 5.0)
            self.optimizer.step()

            total_loss += loss.item()
        return total_loss / len(loader)

    @torch.no_grad()
    def _validate(self, loader: DataLoader) -> tuple[float, dict]:
        self.model.eval()
        total_loss = 0.0
        all_preds = {"cancer_type": [], "subtype": [], "stage": []}
        all_labels = {"cancer_type": [], "subtype": [], "stage": []}
        all_probs = {"cancer_type": [], "subtype": [], "stage": []}

        for batch in loader:
            x = batch["input"].to(self.device)
            targets = {
                "cancer_type": batch["cancer_type"].to(self.device),
                "subtype": batch["subtype"].to(self.device),
                "stage": batch["stage"].to(self.device),
            }

            outputs = self.model(x)
            loss = self._compute_loss(outputs, targets)
            total_loss += loss.item()
            probs = {
                k: F.softmax(outputs[k], dim=1).cpu()
                for k in outputs
            }

            for key in all_preds:
                all_preds[key].append(probs[key].argmax(dim=1))
                all_labels[key].append(targets[key].cpu())
                all_probs[key].append(probs[key])

        avg_loss = total_loss / len(loader)
        metrics = {}
        for key in all_preds:
            y_true = torch.cat(all_labels[key]).numpy()
            y_pred = torch.cat(all_preds[key]).numpy()
            y_prob = torch.cat(all_probs[key]).numpy()

            n_classes = y_prob.shape[1]
            try:
                if n_classes > 2:
                    auc = roc_auc_score(
                        y_true, y_prob, multi_class="ovr", average="weighted"
                    )
                else:
                    auc = roc_auc_score(y_true, y_prob[:, 1])
            except ValueError:
                auc = 0.0

            metrics[key] = {
                "accuracy": accuracy_score(y_true, y_pred),
                "precision": precision_score(
                    y_true, y_pred, average="weighted", zero_division=0
                ),
                "recall": recall_score(
                    y_true, y_pred, average="weighted", zero_division=0
                ),
                "f1": f1_score(
                    y_true, y_pred, average="weighted", zero_division=0
                ),
                "auc_roc": float(auc),
            }

        return avg_loss, metrics

    def fit(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
    ):
        os.makedirs(self.config.save_dir, exist_ok=True)

        for epoch in range(1, self.config.num_epochs + 1):
            train_loss = self._train_epoch(train_loader)
            val_loss, val_metrics = self._validate(val_loader)

            self.scheduler.step(val_loss)
            self.history["train_loss"].append(train_loss)
            self.history["val_loss"].append(val_loss)
            self.history["val_metrics"].append(val_metrics)

            if epoch % self.config.log_interval == 0 or epoch == 1:
                ct = val_metrics["cancer_type"]
                print(
                    f"Epoch {epoch:3d}/{self.config.num_epochs} | "
                    f"Train Loss: {train_loss:.4f} | "
                    f"Val Loss: {val_loss:.4f} | "
                    f"Acc: {ct['accuracy']:.4f} | "
                    f"F1: {ct['f1']:.4f} | "
                    f"AUC: {ct['auc_roc']:.4f}"
                )

            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.early_stop_counter = 0
                self._save_checkpoint(epoch, val_loss, val_metrics)
            else:
                self.early_stop_counter += 1
                if self.early_stop_counter >= self.config.early_stop_patience:
                    print(f"Early stopping at epoch {epoch}")
                    break

        self._save_history()
        return self.history

    def _save_checkpoint(self, epoch: int, val_loss: float, metrics: dict):
        path = os.path.join(self.config.save_dir, "best_model.pt")
        torch.save({
            "epoch": epoch,
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "val_loss": val_loss,
            "metrics": metrics,
            "config": self.model.config,
        }, path)

    def _save_history(self):
        path = os.path.join(self.config.save_dir, "training_history.json")
        serializable = {
            "train_loss": self.history["train_loss"],
            "val_loss": self.history["val_loss"],
            "val_metrics": self.history["val_metrics"],
        }
        with open(path, "w") as f:
            json.dump(serializable, f, indent=2, default=str)
