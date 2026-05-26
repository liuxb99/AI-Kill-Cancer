import json
import hashlib
from datetime import datetime
from typing import Any

def generate_id(prefix: str = "") -> str:
    """產生唯一 ID"""
    raw = f"{prefix}{datetime.utcnow().isoformat()}"
    return f"{prefix}{hashlib.md5(raw.encode()).hexdigest()[:12]}"

def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
