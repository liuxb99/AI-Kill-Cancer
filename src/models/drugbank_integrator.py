import json
import pickle
import numpy as np
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from .molecule_utils import (
    validate_smiles, standardize_smiles, morgan_fingerprint,
    compute_descriptors, FingerprintConfig,
)


DRUGBANK_KNOWN_DRUGS = {
    "DB00001": {
        "name": "Hirudin",
        "smiles": "CC[C@H](C)[C@@H](C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)NCC(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CC)",
        "targets": ["F2", "F10"],
        "type": "Biotech",
    },
    "DB00006": {
        "name": "Bivalirudin",
        "smiles": "CC[C@H](C)[C@@H](C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)NCC(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CC)",
        "targets": ["F2"],
        "type": "Biotech",
    },
    "DB00945": {
        "name": "Acetylsalicylic acid",
        "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        "targets": ["PTGS1", "PTGS2"],
        "type": "Small Molecule",
    },
    "DB01050": {
        "name": "Ibuprofen",
        "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
        "targets": ["PTGS1", "PTGS2"],
        "type": "Small Molecule",
    },
    "DB00641": {
        "name": "Simvastatin",
        "smiles": "CC[C@H](C)[C@H](O)C(=O)O[C@@H]1C[C@H](C)C=C2C=C(C)C(=O)[C@H](O)[C@@]12C",
        "targets": ["HMGCR"],
        "type": "Small Molecule",
    },
    "DB00201": {
        "name": "Capecitabine",
        "smiles": "CC1=CN(C(=O)NC1=O)[C@@H]2[C@H]([C@@H]([C@H](O2)CO)O)O",
        "targets": ["TYMS"],
        "type": "Small Molecule",
    },
    "DB00398": {
        "name": "Sorafenib",
        "smiles": "CNC(=O)C1=NC=CC(=C1)OC2=CC=C(C=C2)NC(=O)NC3=CC(=C(C=C3)Cl)C(F)(F)F",
        "targets": ["BRAF", "KDR", "FLT4", "PDGFRA", "KIT"],
        "type": "Small Molecule",
    },
    "DB00546": {
        "name": "Tezacitabine",
        "smiles": "C1=CN(C(=O)N=C1N)[C@@H]2[C@H]([C@@H]([C@H](O2)CO)O)O",
        "targets": ["TYMS"],
        "type": "Small Molecule",
    },
    "DB01262": {
        "name": "Decitabine",
        "smiles": "NC1=NC(=O)N(C=C1)[C@@H]2[C@H]([C@@H]([C@H](O2)CO)O)O",
        "targets": ["DNMT1"],
        "type": "Small Molecule",
    },
    "DB08896": {
        "name": "Regorafenib",
        "smiles": "CNC(=O)C1=NC=CC(=C1)OC2=CC=C(C=C2)NC(=O)NC3=CC(=C(C=C3)Cl)C(F)(F)F",
        "targets": ["KDR", "BRAF", "PDGFRA", "KIT", "RET"],
        "type": "Small Molecule",
    },
    "DB09052": {
        "name": "Osimertinib",
        "smiles": "CNC(=O)C1=NC=CC(=C1)OC2=CC=C(C=C2)NC(=O)NC3=CC(=C(C=C3)Cl)C(F)(F)F",
        "targets": ["EGFR", "ERBB2"],
        "type": "Small Molecule",
    },
}

CHEMBL_KNOWN_TARGETS = {
    "EGFR": {"uniprot": "P00533", "family": "Kinase"},
    "ERBB2": {"uniprot": "P04626", "family": "Kinase"},
    "BRAF": {"uniprot": "P15056", "family": "Kinase"},
    "KDR": {"uniprot": "P35968", "family": "Kinase"},
    "PTGS1": {"uniprot": "P23219", "family": "Oxidoreductase"},
    "PTGS2": {"uniprot": "P35354", "family": "Oxidoreductase"},
    "HMGCR": {"uniprot": "P04035", "family": "Oxidoreductase"},
    "TYMS": {"uniprot": "P04818", "family": "Transferase"},
    "DNMT1": {"uniprot": "P26358", "family": "Transferase"},
    "F2": {"uniprot": "P00734", "family": "Protease"},
    "F10": {"uniprot": "P00742", "family": "Protease"},
    "PDGFRA": {"uniprot": "P16234", "family": "Kinase"},
    "KIT": {"uniprot": "P10721", "family": "Kinase"},
    "RET": {"uniprot": "P07949", "family": "Kinase"},
    "FLT4": {"uniprot": "P35916", "family": "Kinase"},
}

CANCER_RELEVANT_TARGETS = {
    "EGFR", "ERBB2", "BRAF", "KDR", "PDGFRA", "KIT", "RET",
    "FLT4", "TYMS", "DNMT1",
}


@dataclass
class DrugBankConfig:
    data_dir: str = "data/drugbank"
    fingerprint_config: FingerprintConfig = field(default_factory=FingerprintConfig)
    cache_enabled: bool = True
    min_drugs_per_target: int = 2


class DrugBankIntegrator:

    def __init__(self, config: Optional[DrugBankConfig] = None):
        self.config = config or DrugBankConfig()
        self._drug_cache: dict[str, dict] = {}
        self._target_cache: dict[str, dict] = {}
        self._dti_pairs: list[tuple[str, str, str]] = []
        self._loaded = False

    @property
    def known_drugs(self) -> dict:
        return dict(DRUGBANK_KNOWN_DRUGS)

    @property
    def known_targets(self) -> dict:
        return dict(CHEMBL_KNOWN_TARGETS)

    @property
    def cancer_targets(self) -> set:
        return CANCER_RELEVANT_TARGETS

    def load_builtin(self):
        self._drug_cache = dict(DRUGBANK_KNOWN_DRUGS)
        self._target_cache = dict(CHEMBL_KNOWN_TARGETS)
        self._dti_pairs = []
        for drug_id, drug in DRUGBANK_KNOWN_DRUGS.items():
            for target in drug.get("targets", []):
                if target in CHEMBL_KNOWN_TARGETS:
                    self._dti_pairs.append((drug_id, drug["name"], target))
        self._loaded = True

    def load_from_file(self, filepath: str):
        p = Path(filepath)
        if not p.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")
        suffix = p.suffix.lower()
        if suffix == ".json":
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        elif suffix == ".pkl":
            with open(p, "rb") as f:
                data = pickle.load(f)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

        drugs = data.get("drugs", data)
        self._drug_cache = {}
        self._dti_pairs = []
        for drug_id, info in drugs.items():
            self._drug_cache[drug_id] = info
            for target in info.get("targets", []):
                self._dti_pairs.append((drug_id, info.get("name", ""), target))

        targets = data.get("targets", {})
        self._target_cache = dict(targets) if targets else dict(CHEMBL_KNOWN_TARGETS)
        self._loaded = True

    def get_drug(self, drug_id: str) -> Optional[dict]:
        return self._drug_cache.get(drug_id)

    def get_target(self, target_name: str) -> Optional[dict]:
        return self._target_cache.get(target_name)

    def search_drugs_by_name(self, query: str) -> list[dict]:
        q = query.lower()
        results = []
        for drug_id, info in self._drug_cache.items():
            if q in info.get("name", "").lower():
                results.append({"drugbank_id": drug_id, **info})
        return results

    def search_drugs_by_target(self, target: str) -> list[dict]:
        results = []
        for drug_id, info in self._drug_cache.items():
            if target in info.get("targets", []):
                results.append({"drugbank_id": drug_id, **info})
        return results

    def get_dti_pairs(self, cancer_relevant_only: bool = False) -> list[tuple[str, str, str]]:
        if not cancer_relevant_only:
            return list(self._dti_pairs)
        filtered = []
        for drug_id, drug_name, target in self._dti_pairs:
            if target in CANCER_RELEVANT_TARGETS:
                filtered.append((drug_id, drug_name, target))
        return filtered

    def compute_drug_fingerprints(self) -> dict[str, np.ndarray]:
        fps = {}
        for drug_id, info in self._drug_cache.items():
            smiles = info.get("smiles", "")
            if not smiles or not validate_smiles(smiles):
                continue
            fp = morgan_fingerprint(smiles, self.config.fingerprint_config)
            if fp is not None:
                fps[drug_id] = fp
        return fps

    def compute_drug_descriptors(self) -> dict[str, dict]:
        descs = {}
        for drug_id, info in self._drug_cache.items():
            smiles = info.get("smiles", "")
            if not smiles:
                continue
            d = compute_descriptors(smiles)
            if d:
                descs[drug_id] = d
        return descs

    def build_dti_matrix(
        self,
        drug_ids: Optional[list[str]] = None,
        target_names: Optional[list[str]] = None,
    ) -> np.ndarray:
        if not self._loaded:
            self.load_builtin()
        drugs = drug_ids or list(self._drug_cache.keys())
        targets = target_names or list(self._target_cache.keys())
        matrix = np.zeros((len(drugs), len(targets)), dtype=np.float32)
        drug_to_idx = {d: i for i, d in enumerate(drugs)}
        target_to_idx = {t: j for j, t in enumerate(targets)}
        for drug_id, _, target in self._dti_pairs:
            i = drug_to_idx.get(drug_id)
            j = target_to_idx.get(target)
            if i is not None and j is not None:
                matrix[i, j] = 1.0
        return matrix

    def get_statistics(self) -> dict:
        return {
            "num_drugs": len(self._drug_cache),
            "num_targets": len(self._target_cache),
            "num_dti_pairs": len(self._dti_pairs),
            "cancer_relevant_targets": len(CANCER_RELEVANT_TARGETS),
            "cancer_relevant_pairs": len(self.get_dti_pairs(cancer_relevant_only=True)),
        }
