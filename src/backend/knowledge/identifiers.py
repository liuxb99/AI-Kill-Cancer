"""
Cross-source identifier mapping for oncology knowledge entities.

Provides stable ID mapping between:
- HGNC (gene symbols)
- NCBI Gene ID
- ClinVar Variation ID
- dbSNP rsID
- HGVS notation
- DOID (Disease Ontology)
- MONDO (Mondo Disease Ontology)
- OncoTree code
- DrugBank ID
- ChEMBL ID
- RxNorm
- NCT ID (ClinicalTrials.gov)
- PMID
- DOI
"""

from __future__ import annotations

import re
from typing import Optional


class IdentifierMapping:
    """A single identifier mapping between two systems."""
    def __init__(self, source_system: str, source_id: str,
                 target_system: str, target_id: str,
                 confidence: str = "exact"):
        self.source_system = source_system
        self.source_id = source_id
        self.target_system = target_system
        self.target_id = target_id
        self.confidence = confidence


def normalize_hgvs(hgvs: str) -> str:
    """Normalize HGVS notation to a canonical form."""
    hgvs = hgvs.strip()
    hgvs = re.sub(r'\s+', '', hgvs)
    hgvs = hgvs.upper()
    return hgvs


def normalize_gene_symbol(symbol: str) -> str:
    """Normalize gene symbol to standard HUGO form."""
    return symbol.strip().upper()


class IdentifierMapper:
    """
    Maps identifiers between different knowledge source systems.
    Uses built-in lookup tables and pattern-based detection.
    """

    # Common gene symbol -> NCBI Gene ID mapping (key genes)
    GENE_TO_NCBI: dict[str, str] = {
        "BRAF": "673", "EGFR": "1956", "KRAS": "3845", "NRAS": "4893",
        "PIK3CA": "5290", "TP53": "7157", "ERBB2": "2064", "ALK": "238",
        "ROS1": "6098", "RET": "5979", "MET": "4233", "NTRK1": "4914",
        "IDH1": "3417", "IDH2": "3418", "BRCA1": "672", "BRCA2": "675",
        "KIT": "3815", "PDGFRA": "5156", "FGFR1": "2260", "FGFR2": "2263",
        "FGFR3": "2261", "AR": "367", "ESR1": "2099", "MYC": "4609",
        "CTNNB1": "1499", "CDKN2A": "1029", "PTEN": "5728", "NF1": "4763",
        "RB1": "5925", "SMAD4": "4089", "STK11": "6794", "TERT": "7015",
        "AKT1": "207", "JAK2": "3717", "JAK3": "3718", "ABL1": "25",
        "FLT3": "2322", "NPM1": "4869", "DNMT3A": "1788", "RUNX1": "861",
        "CEBPA": "1050", "ASXL1": "171023", "EZH2": "2146", "BCR": "613",
        "MPL": "4352", "CALR": "811", "PTPN11": "5781", "WT1": "7490",
        "NOTCH1": "4851", "SF3B1": "23451", "U2AF1": "7307",
        "MAP2K1": "5604", "MAP2K2": "5605", "GATA3": "2625",
        "FOXA1": "3169", "CTCF": "10664", "ATRX": "546", "DAXX": "1616",
        "MEN1": "4221", "VHL": "7428", "PBRM1": "55193", "SETD2": "29072",
        "BAP1": "8314", "ARID1A": "8289", "ARID2": "196528",
    }

    # NCBI Gene ID -> HGNC symbol reverse map
    NCBI_TO_GENE: dict[str, str] = {v: k for k, v in GENE_TO_NCBI.items()}

    # Common OncoTree codes
    ONCOTREE_MAP: dict[str, str] = {
        "MEL": "Melanoma", "LUAD": "Lung Adenocarcinoma", "LUSC": "Lung Squamous Cell Carcinoma",
        "BRCA": "Breast Invasive Carcinoma", "COAD": "Colon Adenocarcinoma", "READ": "Rectal Adenocarcinoma",
        "THCA": "Thyroid Carcinoma", "PTC": "Papillary Thyroid Carcinoma", "FTC": "Follicular Thyroid Carcinoma",
        "MTC": "Medullary Thyroid Carcinoma", "ATC": "Anaplastic Thyroid Carcinoma",
        "GBM": "Glioblastoma", "LGG": "Low-Grade Glioma",
        "OV": "Ovarian Serous Carcinoma", "PAAD": "Pancreatic Adenocarcinoma",
        "PRAD": "Prostate Adenocarcinoma", "LIHC": "Liver Hepatocellular Carcinoma",
        "STAD": "Stomach Adenocarcinoma", "BLCA": "Bladder Urothelial Carcinoma",
        "CESC": "Cervical Squamous Cell Carcinoma", "HNSC": "Head and Neck Squamous Cell Carcinoma",
        "KIRC": "Kidney Clear Cell Carcinoma", "KIRP": "Kidney Papillary Cell Carcinoma",
        "LAML": "Acute Myeloid Leukemia", "SARC": "Sarcoma",
    }

    # DOID -> Disease name (common ones)
    DOID_MAP: dict[str, str] = {
        "DOID:1909": "Melanoma", "DOID:1324": "Lung Cancer", "DOID:1612": "Breast Cancer",
        "DOID:9256": "Colorectal Cancer", "DOID:3963": "Thyroid Carcinoma",
        "DOID:3068": "Glioblastoma", "DOID:1793": "Pancreatic Cancer",
        "DOID:10283": "Prostate Cancer", "DOID:3571": "Liver Cancer",
        "DOID:11054": "Bladder Cancer", "DOID:863": "Acute Myeloid Leukemia",
        "DOID:3905": "Lung Adenocarcinoma", "DOID:3907": "Lung Squamous Cell Carcinoma",
        "DOID:0050903": "Ovarian Cancer", "DOID:10158": "Head and Neck Cancer",
    }

    def map_gene_to_ncbi(self, symbol: str) -> Optional[str]:
        """Map HGNC gene symbol to NCBI Gene ID."""
        return self.GENE_TO_NCBI.get(normalize_gene_symbol(symbol))

    def map_ncbi_to_gene(self, ncbi_id: str) -> Optional[str]:
        """Map NCBI Gene ID to HGNC symbol."""
        return self.NCBI_TO_GENE.get(ncbi_id)

    def detect_identifier_type(self, identifier: str) -> str:
        """Detect the type of an identifier from its format."""
        if not identifier:
            return "unknown"

        # PMID: numeric, 1-8 digits
        if re.match(r'^\d{1,8}$', identifier):
            return "pmid"

        # NCT ID: NCT plus 8 digits
        if re.match(r'^NCT\d{8}$', identifier, re.IGNORECASE):
            return "nct"

        # DOI: 10.xxxx/xxxx
        if re.match(r'^10\.\d{4,}/', identifier):
            return "doi"

        # dbSNP rsID
        if re.match(r'^rs\d+$', identifier, re.IGNORECASE):
            return "dbsnp"

        # HGVS: pattern like NM_xxxx:c.xxx
        if re.match(r'^(NM_|NC_|NG_|NP_|ENST|ENSP)\d+\.\d+:', identifier):
            return "hgvs"

        # ClinVar Variation ID: just digits, typically 5+ digits
        if re.match(r'^\d{5,}$', identifier):
            return "clinvar_variation"

        # OncoTree code: 2-8 uppercase letters
        if re.match(r'^[A-Z]{2,8}$', identifier):
            return "oncotree"

        # DOID: DOID:xxxxxx
        if re.match(r'^DOID:\d+$', identifier, re.IGNORECASE):
            return "doid"

        # MONDO: MONDO:xxxxxx
        if re.match(r'^MONDO:\d+$', identifier, re.IGNORECASE):
            return "mondo"

        # DrugBank: DBxxxxx
        if re.match(r'^DB\d{5,}$', identifier, re.IGNORECASE):
            return "drugbank"

        # ChEMBL: CHEMBLxxxxx
        if re.match(r'^CHEMBL\d+$', identifier, re.IGNORECASE):
            return "chembl"

        # RxNorm: xxxxx (numeric, 1-7 digits)
        if re.match(r'^\d{1,7}$', identifier):
            return "rxnorm"

        # Gene symbol: 1-16 alpha chars
        if re.match(r'^[A-Z][A-Z0-9]{1,15}$', identifier, re.IGNORECASE):
            return "gene_symbol"

        return "unknown"

    def map_oncotree_to_disease(self, code: str) -> Optional[str]:
        """Map OncoTree code to disease name."""
        return self.ONCOTREE_MAP.get(code.upper())

    def map_doid_to_disease(self, doid: str) -> Optional[str]:
        """Map DOID to disease name."""
        return self.DOID_MAP.get(doid)

    def get_all_identifiers(self, gene_symbol: str) -> dict[str, str]:
        """Get all known identifiers for a gene symbol."""
        result: dict[str, str] = {
            "hgnc": gene_symbol.upper(),
        }
        ncbi = self.map_gene_to_ncbi(gene_symbol)
        if ncbi:
            result["ncbi_gene"] = ncbi
        return result
