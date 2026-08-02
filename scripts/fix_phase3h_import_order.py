"""Normalize imports produced by the temporary Phase 3H integration helper."""

from pathlib import Path

path = Path("src/backend/services/ptc_knowledge_service.py")
text = path.read_text(encoding="utf-8")
old = (
    "from src.backend.sync.public_data_store import PublicDataStore\n\n"
    "from src.backend.domain.ptc_knowledge import (\n"
)
new = "from src.backend.domain.ptc_knowledge import (\n"
if old in text:
    text = text.replace(old, new, 1)
    closing = "    PTCTherapyTargetModel,\n)\n"
    text = text.replace(
        closing,
        closing + "from src.backend.sync.public_data_store import PublicDataStore\n",
        1,
    )
path.write_text(text, encoding="utf-8")
