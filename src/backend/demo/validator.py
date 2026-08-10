from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DemoValidationResult:
    ok: bool
    errors: list[str]
    counts: dict[str, int]


_REQUIRED_COLUMNS: dict[str, set[str]] = {
    "patients.csv": {"demo_patient_key", "display_name"},
    "cancer_cases.csv": {"demo_case_key", "demo_patient_key", "cancer_type"},
    "specimens.csv": {"demo_specimen_key", "demo_case_key", "specimen_type"},
    "sequencing_tests.csv": {"demo_sequencing_key", "demo_specimen_key", "assay_name"},
    "variants.csv": {"demo_variant_key", "demo_sequencing_key", "gene_symbol", "variant_type"},
    "drugs.csv": {"demo_drug_key", "name"},
    "publications.csv": {"demo_publication_key", "title"},
    "clinical_trials.csv": {"demo_trial_key", "title"},
    "evidence.csv": {"demo_evidence_key", "demo_variant_key", "demo_drug_key", "demo_publication_key", "demo_trial_key", "evidence_level"},
}

_KEY_COLUMNS = {
    "patients.csv": "demo_patient_key",
    "cancer_cases.csv": "demo_case_key",
    "specimens.csv": "demo_specimen_key",
    "sequencing_tests.csv": "demo_sequencing_key",
    "variants.csv": "demo_variant_key",
    "drugs.csv": "demo_drug_key",
    "publications.csv": "demo_publication_key",
    "clinical_trials.csv": "demo_trial_key",
    "evidence.csv": "demo_evidence_key",
}

# Demo files are executable fixtures, not loose examples.  Keep the most
# failure-prone categorical fields constrained so a shifted CSV row or typo is
# rejected before bootstrap reaches the ORM layer.
_VALUE_DOMAINS: dict[str, dict[str, set[str]]] = {
    "variants.csv": {
        "variant_type": {"SNV", "indel", "fusion", "CNV", "SV"},
        "origin": {"somatic", "germline", "unknown"},
        "driver_status": {"driver", "likely_driver", "passenger", "unknown"},
        "zygosity": {"heterozygous", "homozygous", "hemizygous", "unknown"},
        "normalization_status": {"pending", "completed", "failed"},
        "data_mode": {"synthetic"},
    },
    "evidence.csv": {
        "data_mode": {"synthetic"},
    },
}


def _read(path: Path) -> tuple[list[dict[str, str]], set[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), set(reader.fieldnames or [])


def validate_demo_dataset(data_dir: str | Path) -> DemoValidationResult:
    root = Path(data_dir)
    errors: list[str] = []
    counts: dict[str, int] = {}
    rows: dict[str, list[dict[str, str]]] = {}
    keys: dict[str, set[str]] = {}

    for filename, required in _REQUIRED_COLUMNS.items():
        path = root / filename
        if not path.is_file():
            errors.append(f"missing file: {filename}")
            continue
        file_rows, columns = _read(path)
        rows[filename] = file_rows
        counts[filename.removesuffix('.csv')] = len(file_rows)
        missing = sorted(required - columns)
        if missing:
            errors.append(f"{filename}: missing columns: {', '.join(missing)}")

        for index, row in enumerate(file_rows, start=2):
            extras = row.get(None)
            if extras:
                errors.append(f"{filename}:{index}: extra CSV fields: {extras}")
            for column, allowed in _VALUE_DOMAINS.get(filename, {}).items():
                value = (row.get(column) or '').strip()
                if value and value not in allowed:
                    errors.append(
                        f"{filename}:{index}: invalid {column}={value!r}; "
                        f"expected one of {', '.join(sorted(allowed))}"
                    )

        key_column = _KEY_COLUMNS[filename]
        values = [(row.get(key_column) or '').strip() for row in file_rows]
        blank = [index + 2 for index, value in enumerate(values) if not value]
        if blank:
            errors.append(f"{filename}: blank {key_column} at rows {blank}")
        duplicates = sorted({value for value in values if value and values.count(value) > 1})
        if duplicates:
            errors.append(f"{filename}: duplicate {key_column}: {', '.join(duplicates)}")
        keys[filename] = {value for value in values if value}

    def check_ref(filename: str, column: str, target_file: str) -> None:
        if filename not in rows or target_file not in keys:
            return
        for index, row in enumerate(rows[filename], start=2):
            value = (row.get(column) or '').strip()
            if value and value not in keys[target_file]:
                errors.append(f"{filename}:{index}: broken {column} -> {value}")

    check_ref("cancer_cases.csv", "demo_patient_key", "patients.csv")
    check_ref("specimens.csv", "demo_case_key", "cancer_cases.csv")
    check_ref("sequencing_tests.csv", "demo_specimen_key", "specimens.csv")
    check_ref("variants.csv", "demo_sequencing_key", "sequencing_tests.csv")
    check_ref("evidence.csv", "demo_variant_key", "variants.csv")
    check_ref("evidence.csv", "demo_drug_key", "drugs.csv")
    check_ref("evidence.csv", "demo_publication_key", "publications.csv")
    check_ref("evidence.csv", "demo_trial_key", "clinical_trials.csv")

    return DemoValidationResult(ok=not errors, errors=errors, counts=counts)
