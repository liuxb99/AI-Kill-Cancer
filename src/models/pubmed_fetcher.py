import time
import json
import logging
import hashlib
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime, timedelta
from xml.etree import ElementTree

import requests

logger = logging.getLogger(__name__)


CANCER_KW_MAP = {
    "肺癌": ["lung cancer", "lung carcinoma", "non-small cell lung", "NSCLC", "SCLC"],
    "乳腺癌": ["breast cancer", "breast carcinoma", "HER2+", "triple negative"],
    "大腸癌": ["colorectal cancer", "colon cancer", "rectal cancer", "CRC"],
    "肝癌": ["liver cancer", "hepatocellular carcinoma", "HCC"],
    "胃癌": ["gastric cancer", "stomach cancer"],
    "前列腺癌": ["prostate cancer"],
    "胰腺癌": ["pancreatic cancer"],
    "白血病": ["leukemia", "acute myeloid leukemia", "AML", "CML"],
    "淋巴瘤": ["lymphoma", "Hodgkin", "non-Hodgkin", "DLBCL"],
    "黑色素瘤": ["melanoma"],
    "卵巢癌": ["ovarian cancer"],
    "腦癌": ["brain cancer", "glioblastoma", "GBM"],
}


@dataclass
class Article:
    pmid: str
    title: str
    abstract: str
    authors: list[str] = field(default_factory=list)
    journal: str = ""
    year: int = 0
    doi: str = ""
    keywords: list[str] = field(default_factory=list)
    mesh_terms: list[str] = field(default_factory=list)
    pub_date: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def truncated_abstract(self, max_len: int = 512) -> str:
        return self.abstract[:max_len] if len(self.abstract) > max_len else self.abstract


@dataclass
class PubMedFetcherConfig:
    email: str = "research@example.com"
    tool_name: str = "AI_Kill_Cancer"
    base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    cache_dir: str = ".pubmed_cache"
    cache_ttl_days: int = 7
    retry_count: int = 3
    retry_delay: float = 1.0
    max_results: int = 100


class PubMedFetcher:

    def __init__(self, config: Optional[PubMedFetcherConfig] = None):
        self.config = config or PubMedFetcherConfig()
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": f"{self.config.tool_name}/{self.config.email}",
        })
        self._cache_dir = Path(self.config.cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, key: str) -> Path:
        h = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self._cache_dir / f"{h}.json"

    def _is_cache_valid(self, path: Path) -> bool:
        if not path.exists():
            return False
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return (datetime.now() - mtime) < timedelta(days=self.config.cache_ttl_days)

    def _read_cache(self, key: str) -> Optional[list[Article]]:
        path = self._cache_path(key)
        if self._is_cache_valid(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return [Article(**a) for a in data]
            except Exception as e:
                logger.warning("快取讀取失敗: %s", e)
        return None

    def _write_cache(self, key: str, articles: list[Article]):
        try:
            path = self._cache_path(key)
            with open(path, "w", encoding="utf-8") as f:
                json.dump([a.to_dict() for a in articles], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("快取寫入失敗: %s", e)

    def _eutils_get(self, endpoint: str, params: dict) -> dict:
        url = self.config.base_url + endpoint
        params["tool"] = self.config.tool_name
        params["email"] = self.config.email

        for attempt in range(self.config.retry_count):
            try:
                resp = self._session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                return resp.json() if endpoint.endswith(".fcgi") else resp.json()
            except requests.RequestException as e:
                logger.warning("E-utilities 請求失敗 (嘗試 %d/%d): %s",
                               attempt + 1, self.config.retry_count, e)
                if attempt < self.config.retry_count - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    raise

    def _eutils_post(self, endpoint: str, params: dict) -> str:
        url = self.config.base_url + endpoint
        params["tool"] = self.config.tool_name
        params["email"] = self.config.email

        for attempt in range(self.config.retry_count):
            try:
                resp = self._session.get(url, params=params, timeout=60)
                resp.raise_for_status()
                return resp.text
            except requests.RequestException as e:
                logger.warning("E-utilities POST 失敗 (嘗試 %d/%d): %s",
                               attempt + 1, self.config.retry_count, e)
                if attempt < self.config.retry_count - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    raise

    def search_ids(self, query: str, max_results: Optional[int] = None,
                   sort: str = "relevance") -> list[str]:
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results or self.config.max_results,
            "retmode": "json",
            "sort": sort,
        }
        data = self._eutils_get("esearch.fcgi", params)
        return data.get("esearchresult", {}).get("idlist", [])

    def fetch_details(self, pmids: list[str]) -> list[Article]:
        if not pmids:
            return []

        cache_key = ",".join(sorted(pmids))
        cached = self._read_cache(cache_key)
        if cached is not None:
            logger.info("從快取載入 %d 篇文章", len(cached))
            return cached

        xml_text = self._eutils_post("efetch.fcgi", {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
        })

        articles = self._parse_articles(xml_text)
        self._write_cache(cache_key, articles)
        return articles

    def search(self, query: str, max_results: Optional[int] = None,
               sort: str = "relevance") -> list[Article]:
        pmids = self.search_ids(query, max_results, sort)
        if not pmids:
            return []
        return self.fetch_details(pmids)

    def _parse_articles(self, xml_text: str) -> list[Article]:
        articles = []
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as e:
            logger.error("XML 解析錯誤: %s", e)
            return []

        for article_elem in root.findall(".//PubmedArticle"):
            try:
                article = self._parse_single_article(article_elem)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.warning("文章解析失敗: %s", e)
                continue

        return articles

    def _parse_single_article(self, elem: ElementTree.Element) -> Optional[Article]:
        medline = elem.find(".//MedlineCitation")
        if medline is None:
            return None

        pmid = medline.findtext("PMID", "")
        article_data = medline.find(".//Article")
        if article_data is None:
            return None

        title = article_data.findtext("ArticleTitle", "")
        abstract_parts = article_data.findall(".//AbstractText")
        abstract = " ".join(
            (ap.text or "") for ap in abstract_parts
        ) if abstract_parts else ""

        author_list = article_data.find(".//AuthorList")
        authors = []
        if author_list is not None:
            for author in author_list.findall("Author"):
                last = author.findtext("LastName", "")
                fore = author.findtext("ForeName", "")
                if last:
                    authors.append(f"{last} {fore}" if fore else last)

        journal_elem = article_data.find(".//Journal")
        journal = ""
        if journal_elem is not None:
            journal = journal_elem.findtext("Title", "") or journal_elem.findtext("ISOAbbreviation", "")

        year = 0
        pub_date_elem = article_data.find(".//Journal/JournalIssue/PubDate")
        if pub_date_elem is not None:
            year_str = pub_date_elem.findtext("Year", "")
            if year_str:
                try:
                    year = int(year_str)
                except ValueError:
                    pass

        pub_date_str = ""
        if pub_date_elem is not None:
            parts = []
            for tag in ("Year", "Month", "Day"):
                v = pub_date_elem.findtext(tag, "")
                if v:
                    parts.append(v)
            pub_date_str = " ".join(parts)

        doi = ""
        for eid in article_data.findall(".//ELocationID"):
            if eid.get("EIdType") == "doi":
                doi = eid.text or ""
                break

        kw_elem = article_data.find(".//KeywordList")
        keywords = []
        if kw_elem is not None:
            keywords = [kw.text for kw in kw_elem.findall("Keyword") if kw.text]

        mesh_list = medline.find(".//MeshHeadingList")
        mesh_terms = []
        if mesh_list is not None:
            for mh in mesh_list.findall("MeshHeading"):
                desc = mh.find("DescriptorName")
                if desc is not None and desc.text:
                    mesh_terms.append(desc.text)

        return Article(
            pmid=pmid,
            title=title,
            abstract=abstract,
            authors=authors,
            journal=journal,
            year=year,
            doi=doi,
            keywords=keywords,
            mesh_terms=mesh_terms,
            pub_date=pub_date_str,
        )

    def search_cancer(self, cancer_type: str, additional_terms: str = "",
                      max_results: int = 50) -> list[Article]:
        keywords = CANCER_KW_MAP.get(cancer_type, [cancer_type])
        query = "(" + " OR ".join(f'"{kw}"[Title/Abstract]' for kw in keywords) + ")"
        if additional_terms:
            query += f" AND ({additional_terms})"
        query += " AND English[Language]"
        return self.search(query, max_results=max_results, sort="date")

    def search_by_pmid(self, pmid: str) -> Optional[Article]:
        articles = self.fetch_details([pmid])
        return articles[0] if articles else None

    def clear_cache(self, older_than_days: Optional[int] = None):
        for cache_file in self._cache_dir.glob("*.json"):
            if older_than_days is not None:
                mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if (datetime.now() - mtime).days < older_than_days:
                    continue
            cache_file.unlink()
        logger.info("快取清理完成")

    def get_stats(self) -> dict:
        cache_files = list(self._cache_dir.glob("*.json"))
        total_articles = 0
        for cf in cache_files:
            try:
                with open(cf, "r", encoding="utf-8") as f:
                    total_articles += len(json.load(f))
            except Exception:
                pass
        return {
            "cache_files": len(cache_files),
            "total_cached_articles": total_articles,
            "cache_dir": str(self._cache_dir),
        }
