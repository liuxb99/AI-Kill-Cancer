"""Preserve compatibility with existing GDC downloader test doubles/subclasses."""

from pathlib import Path

path = Path("src/backend/importers/ptc_tcga/downloader.py")
text = path.read_text(encoding="utf-8")
if "import inspect\n" not in text:
    text = text.replace("import json\n", "import inspect\nimport json\n", 1)
old = (
    "            grouped = parse_maf_bytes(\n"
    "                self.download_public_file(str(file_id), expected_md5=item.get(\"md5sum\"))\n"
    "            )\n"
)
new = (
    "            downloader = self.download_public_file\n"
    "            if \"expected_md5\" in inspect.signature(downloader).parameters:\n"
    "                raw_payload = downloader(str(file_id), expected_md5=item.get(\"md5sum\"))\n"
    "            else:  # Backward-compatible adapter/test-double contract.\n"
    "                raw_payload = downloader(str(file_id))\n"
    "            grouped = parse_maf_bytes(raw_payload)\n"
)
if old in text:
    text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
