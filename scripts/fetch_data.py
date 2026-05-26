"""
癌症診斷 AI 工具 — 資料下載與預處理管線腳本

使用方式:
    python scripts/fetch_data.py --source tcga --cancer-type BRCA
    python scripts/fetch_data.py --source cbioportal --study acc_2019
    python scripts/fetch_data.py --source geo --dataset GSE10072
"""

import os
import json
import logging
import argparse
import hashlib
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
CACHE_DIR = PROJECT_ROOT / "data" / "cache"

SUPPORTED_SOURCES = ["tcga", "cbioportal", "geo", "xena", "depmap"]


def ensure_dirs():
    for d in [RAW_DATA_DIR, PROCESSED_DATA_DIR, CACHE_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    logger.info(f"資料目錄已確認: {RAW_DATA_DIR}, {PROCESSED_DATA_DIR}, {CACHE_DIR}")


def verify_checksum(filepath: Path, expected_hash: Optional[str] = None) -> bool:
    if expected_hash is None:
        return True
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    actual = sha256.hexdigest()
    if actual != expected_hash:
        logger.error(f"校驗和不符: {actual[:16]}... != {expected_hash[:16]}...")
        return False
    logger.info(f"校驗和驗證通過: {filepath.name}")
    return True


def download_file(url: str, dest: Path, expected_hash: Optional[str] = None) -> bool:
    logger.info(f"正在下載: {url}")
    try:
        resp = requests.get(url, stream=True, timeout=300)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(
            desc=dest.name, total=total, unit="B", unit_scale=True
        ) as pbar:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                pbar.update(len(chunk))
        logger.info(f"下載完成: {dest}")
        if expected_hash:
            return verify_checksum(dest, expected_hash)
        return True
    except requests.RequestException as e:
        logger.error(f"下載失敗: {e}")
        return False


# ─── TCGA via GDC API ────────────────────────────────────────────────────────

GDC_API_BASE = "https://api.gdc.cancer.gov"


def fetch_tcga_manifest(cancer_type: str, data_type: str = "Gene Expression Quantification"):
    filters = {
        "op": "and",
        "content": [
            {"op": "in", "content": {"field": "cases.project.project_id", "value": [f"TCGA-{cancer_type}"]}},
            {"op": "in", "content": {"field": "files.data_type", "value": [data_type]}},
        ],
    }
    params = {"filters": json.dumps(filters), "format": "JSON", "size": 1000, "pretty": True}
    resp = requests.post(f"{GDC_API_BASE}/files", json=params, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    hits = data.get("data", {}).get("hits", [])
    logger.info(f"TCGA-{cancer_type}: 找到 {len(hits)} 個 {data_type} 檔案")
    return hits


def download_tcga(cancer_type: str, data_type: str = "Gene Expression Quantification"):
    ensure_dirs()
    files = fetch_tcga_manifest(cancer_type, data_type)
    if not files:
        logger.warning(f"未找到 TCGA-{cancer_type} 的 {data_type} 數據")
        return

    out_dir = RAW_DATA_DIR / f"tcga_{cancer_type.lower()}"
    out_dir.mkdir(exist_ok=True)

    for f in files[:10]:
        file_id = f["id"]
        file_name = f["file_name"]
        download_url = f["download_url"] if "download_url" in f else f"{GDC_API_BASE}/data/{file_id}"
        dest = out_dir / file_name
        if not dest.exists():
            download_file(download_url, dest)
        else:
            logger.info(f"已存在，跳過: {dest}")
    logger.info(f"TCGA-{cancer_type} 下載完成，檔案存放於: {out_dir}")


# ─── cBioPortal API ──────────────────────────────────────────────────────────

CBIOPORTAL_API = "https://www.cbioportal.org/api"


def list_cbioportal_studies():
    resp = requests.get(f"{CBIOPORTAL_API}/studies", timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_cbioportal_data(study_id: str, gene_list: Optional[list] = None):
    ensure_dirs()
    if gene_list is None:
        gene_list = []
    profile_resp = requests.get(
        f"{CBIOPORTAL_API}/studies/{study_id}/molecular-profiles", timeout=30
    )
    profile_resp.raise_for_status()
    profiles = profile_resp.json()
    logger.info(f"{study_id}: 找到 {len(profiles)} 個分子輪廓")

    out_dir = RAW_DATA_DIR / f"cbioportal_{study_id.replace('_', '-')}"
    out_dir.mkdir(exist_ok=True)
    metadata = {"study_id": study_id, "profiles": len(profiles)}
    with open(out_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"cBioPortal {study_id} 元數據已儲存至: {out_dir}")
    return out_dir


# ─── GEO via GEOparse ────────────────────────────────────────────────────────

def fetch_geo(dataset_id: str):
    ensure_dirs()
    logger.info(f"正在下載 GEO 數據集: {dataset_id}")
    out_dir = RAW_DATA_DIR / f"geo_{dataset_id}"
    out_dir.mkdir(exist_ok=True)

    soft_url = f"https://ftp.ncbi.nlm.nih.gov/geo/series/{dataset_id[:5]}nnn/{dataset_id}/soft/{dataset_id}_family.soft.gz"
    dest = out_dir / f"{dataset_id}_family.soft.gz"
    success = download_file(soft_url, dest)

    if success:
        logger.info(f"GEO {dataset_id} 下載完成: {dest}")
    else:
        logger.error(f"GEO {dataset_id} 下載失敗。請手動到 https://www.ncbi.nlm.nih.gov/geo/ 下載。")
    return out_dir


# ─── UCSC Xena Hub ───────────────────────────────────────────────────────────

XENA_HUB = "https://tcga.xenahubs.net"


def fetch_xena_cohort(cohort: str = "TCGA.BRCA.sampleMap"):
    ensure_dirs()
    logger.info(f"正在查詢 UCSC Xena 隊列: {cohort}")
    url = f"{XENA_HUB}/download/{cohort}/"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        files = resp.text.strip().split("\n")
        logger.info(f"隊列 {cohort} 中有 {len(files)} 個可用檔案")
        out_dir = RAW_DATA_DIR / f"xena_{cohort.replace('.', '_')}"
        out_dir.mkdir(exist_ok=True)
        for fname in files[:5]:
            fname = fname.strip()
            if not fname:
                continue
            file_url = f"{url}{fname}"
            dest = out_dir / fname
            if not dest.exists():
                download_file(file_url, dest)
            else:
                logger.info(f"已存在，跳過: {dest}")
        return out_dir
    except requests.RequestException as e:
        logger.error(f"Xena 查詢失敗: {e}")
        return None


# ─── DepMap ──────────────────────────────────────────────────────────────────

DEPMAP_API = "https://api.depmap.org/portal/api/v1"


def fetch_depmap(release: str = "24Q4"):
    ensure_dirs()
    logger.info(f"正在下載 DepMap 數據 (release={release})")
    out_dir = RAW_DATA_DIR / f"depmap_{release}"
    out_dir.mkdir(exist_ok=True)

    urls = {
        "expression": f"https://depmap.org/portal/download/api/v1/datasets?release_name={release}",
        "crispr": f"https://depmap.org/portal/download/api/v1/datasets?release_name={release}&dataset_type=Crispr",
    }
    for name, url in urls.items():
        dest = out_dir / f"{name}_datasets.json"
        if not dest.exists():
            download_file(url, dest)
        else:
            logger.info(f"已存在，跳過: {dest}")
    logger.info(f"DepMap 數據下載完成: {out_dir}")
    return out_dir


# ─── 主入口 ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="癌症資料下載與預處理管線")
    parser.add_argument("--source", choices=SUPPORTED_SOURCES, required=True, help="數據來源")
    parser.add_argument("--cancer-type", default="BRCA", help="TCGA 癌症類型代碼 (預設: BRCA)")
    parser.add_argument("--study", default=None, help="cBioPortal 或特定研究 ID")
    parser.add_argument("--dataset", default=None, help="GEO 數據集 ID 或 DepMap 版本")
    parser.add_argument("--data-type", default="Gene Expression Quantification", help="TCGA 數據類型")
    args = parser.parse_args()

    logger.info(f"啟動數據下載: source={args.source}")

    if args.source == "tcga":
        download_tcga(args.cancer_type, args.data_type)
    elif args.source == "cbioportal":
        study = args.study or "acc_2019"
        fetch_cbioportal_data(study)
    elif args.source == "geo":
        dataset = args.dataset or "GSE10072"
        fetch_geo(dataset)
    elif args.source == "xena":
        cohort = args.study or "TCGA.BRCA.sampleMap"
        fetch_xena_cohort(cohort)
    elif args.source == "depmap":
        release = args.dataset or "24Q4"
        fetch_depmap(release)

    logger.info(f"來源 {args.source} 的資料下載流程完成。")


if __name__ == "__main__":
    main()
