import numpy as np
import torch

from .cancer_classifier import CancerClassifier, CancerClassifierConfig


CANCER_TYPE_NAMES = ["肺癌", "乳腺癌", "大腸癌"]
SUBTYPE_NAMES = [
    "肺腺癌", "肺鱗癌", "三陰性乳腺癌",
    "HER2+乳腺癌", "結腸癌", "直腸癌",
]
STAGE_NAMES = ["I期", "II期", "III期", "IV期"]


class Predictor:

    def __init__(self, model_path: str, device: str = "cpu"):
        self.device = torch.device(device)
        checkpoint = torch.load(model_path, map_location=self.device)

        config = checkpoint.get("config", CancerClassifierConfig())
        if isinstance(config, dict):
            config_obj = CancerClassifierConfig(**config)
        else:
            config_obj = config

        self.model = CancerClassifier(config_obj)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()

    def predict(self, X: np.ndarray) -> dict:
        if X.ndim == 1:
            X = X.reshape(1, -1)

        tensor = torch.tensor(X, dtype=torch.float32).to(self.device)

        with torch.no_grad():
            probs = self.model.predict_proba(tensor)
            preds = self.model.predict(tensor)

        results = []
        for i in range(len(tensor)):
            sample = {
                "cancer_type": {
                    "label": int(preds["cancer_type"][i].item()),
                    "name": CANCER_TYPE_NAMES[preds["cancer_type"][i].item()],
                    "probability": float(probs["cancer_type"][i].max().item()),
                    "all_probs": {
                        name: float(probs["cancer_type"][i][j].item())
                        for j, name in enumerate(CANCER_TYPE_NAMES)
                    },
                },
                "subtype": {
                    "label": int(preds["subtype"][i].item()),
                    "name": SUBTYPE_NAMES[preds["subtype"][i].item()],
                    "probability": float(probs["subtype"][i].max().item()),
                },
                "stage": {
                    "label": int(preds["stage"][i].item()),
                    "name": STAGE_NAMES[preds["stage"][i].item()],
                    "probability": float(probs["stage"][i].max().item()),
                },
            }
            results.append(sample)

        return {"samples": results} if len(results) > 1 else {"samples": results[0]}
