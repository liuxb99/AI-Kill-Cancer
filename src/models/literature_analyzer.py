import re
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional
from collections import Counter, defaultdict
from datetime import datetime

import numpy as np
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    AutoModelForSeq2SeqLM,
    pipeline,
)

from .pubmed_fetcher import Article, PubMedFetcher, PubMedFetcherConfig, CANCER_KW_MAP

logger = logging.getLogger(__name__)


CANCER_ENTITY_KEYWORDS = {
    "cancer_type": {
        "肺癌", "肺腺癌", "肺鱗癌", "小細胞肺癌", "非小細胞肺癌",
        "乳腺癌", "三陰性乳腺癌", "HER2陽性乳腺癌",
        "大腸癌", "結直腸癌", "直腸癌",
        "肝癌", "肝細胞癌",
        "胃癌",
        "前列腺癌",
        "胰腺癌",
        "白血病", "急性髓系白血病", "慢性粒細胞白血病",
        "淋巴瘤", "彌漫性大B細胞淋巴瘤",
        "黑色素瘤",
        "卵巢癌",
        "腦癌", "膠質母細胞瘤",
        "lung cancer", "NSCLC", "SCLC", "adenocarcinoma",
        "breast cancer", "triple-negative breast", "HER2-positive",
        "colorectal cancer", "CRC", "colon cancer",
        "hepatocellular carcinoma", "HCC",
        "gastric cancer",
        "prostate cancer",
        "pancreatic cancer",
        "leukemia", "AML", "CML",
        "lymphoma", "DLBCL",
        "melanoma",
        "ovarian cancer",
        "glioblastoma", "GBM",
    },
    "drug": {
        "順鉑", "卡鉑", "紫杉醇", "培美曲塞", "多西他賽",
        "吉非替尼", "奧希替尼", "克唑替尼", "阿來替尼", "拉帕替尼",
        "曲妥珠單抗", "帕妥珠單抗", "帕博西尼",
        "帕博利珠單抗", "納武利尤單抗", "阿替利珠單抗",
        "西妥昔單抗", "貝伐珠單抗", "帕尼單抗",
        "阿黴素", "環磷醯胺", "卡培他濱",
        "cisplatin", "carboplatin", "paclitaxel", "pemetrexed", "docetaxel",
        "gefitinib", "osimertinib", "crizotinib", "alectinib", "lapatinib",
        "trastuzumab", "pertuzumab", "palbociclib",
        "pembrolizumab", "nivolumab", "atezolizumab",
        "cetuximab", "bevacizumab", "panitumumab",
        "doxorubicin", "cyclophosphamide", "capecitabine",
        "FOLFOX", "FOLFIRI",
    },
    "gene": {
        "EGFR", "ALK", "KRAS", "NRAS", "BRAF", "HER2", "ERBB2",
        "PD-L1", "CD274", "PD-1", "PDCD1", "CTLA-4",
        "TP53", "BRCA1", "BRCA2", "PIK3CA", "PTEN",
        "MYC", "MET", "ROS1", "RET", "NTRK",
        "MSI", "MMR", "MLH1", "MSH2", "MSH6", "PMS2",
        "AR", "ESR1", "ER", "PR",
        "VEGF", "VEGFR", "KIT", "PDGFRA",
    },
    "treatment": {
        "化療", "放療", "免疫治療", "標靶治療", "激素治療",
        "化學治療", "放射治療", "免疫療法",
        "手術切除", "微創手術", "達文西手術",
        "car-t", "CAR-T", "細胞治療",
        "化療方案",
        "chemotherapy", "radiotherapy", "immunotherapy",
        "targeted therapy", "hormone therapy",
        "surgery", "resection",
        "combination therapy", "adjuvant", "neoadjuvant",
        "FOLFOX", "FOLFIRI",
    },
}


@dataclass
class EntityMention:
    text: str
    label: str
    start: int
    end: int
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AnalyzedArticle:
    pmid: str
    title: str
    abstract: str
    summary: str = ""
    entities: list[EntityMention] = field(default_factory=list)
    cancer_types: list[str] = field(default_factory=list)
    drugs: list[str] = field(default_factory=list)
    genes: list[str] = field(default_factory=list)
    treatments: list[str] = field(default_factory=list)
    mesh_terms: list[str] = field(default_factory=list)
    year: int = 0
    journal: str = ""
    doi: str = ""

    def to_dict(self) -> dict:
        return {
            "pmid": self.pmid,
            "title": self.title,
            "abstract": self.abstract,
            "summary": self.summary,
            "entities": [e.to_dict() for e in self.entities],
            "cancer_types": self.cancer_types,
            "drugs": self.drugs,
            "genes": self.genes,
            "treatments": self.treatments,
            "mesh_terms": self.mesh_terms,
            "year": self.year,
            "journal": self.journal,
            "doi": self.doi,
        }


@dataclass
class TrendReport:
    query: str
    total_articles: int
    date_range: tuple[str, str]
    cancer_type_freq: dict[str, int]
    drug_freq: dict[str, int]
    gene_freq: dict[str, int]
    treatment_freq: dict[str, int]
    yearly_distribution: dict[str, int]
    top_journals: list[tuple[str, int]]
    key_findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LiteratureAnalyzerConfig:
    biobert_model: str = "dmis-lab/biobert-v1.1"
    pubmedbert_model: str = "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"
    summarization_model: str = "philschmid/bart-large-cnn-samsum"
    device: int = -1
    max_abstract_len: int = 1024
    max_summary_len: int = 150
    min_summary_len: int = 40
    entity_confidence_threshold: float = 0.5
    batch_size: int = 8


class LiteratureAnalyzer:

    def __init__(self, config: Optional[LiteratureAnalyzerConfig] = None):
        self.config = config or LiteratureAnalyzerConfig()
        self.device = torch.device("cuda") if self.config.device >= 0 and torch.cuda.is_available() else torch.device("cpu")
        self._tokenizer = None
        self._ner_model = None
        self._summarizer = None
        self._pubmed_fetcher: Optional[PubMedFetcher] = None
        logger.info("LiteratureAnalyzer 初始化完成 (device=%s)", self.device)

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            self._tokenizer = AutoTokenizer.from_pretrained(self.config.pubmedbert_model)
        return self._tokenizer

    @property
    def summarizer(self):
        if self._summarizer is None:
            logger.info("載入摘要模型: %s", self.config.summarization_model)
            self._summarizer = pipeline(
                "summarization",
                model=self.config.summarization_model,
                device=self.config.device,
            )
        return self._summarizer

    @property
    def ner_pipeline(self):
        if self._ner_model is None:
            try:
                logger.info("載入 BioBERT NER 模型: %s", self.config.biobert_model)
                self._ner_model = pipeline(
                    "token-classification",
                    model=self.config.biobert_model,
                    tokenizer=self.config.biobert_model,
                    aggregation_strategy="simple",
                    device=self.config.device,
                )
            except Exception as e:
                logger.warning("BioBERT NER 載入失敗，使用關鍵字為基礎的方法: %s", e)
                self._ner_model = "fallback"
        return self._ner_model

    @property
    def pubmed_fetcher(self) -> PubMedFetcher:
        if self._pubmed_fetcher is None:
            self._pubmed_fetcher = PubMedFetcher()
        return self._pubmed_fetcher

    def summarize_abstract(self, text: str) -> str:
        if not text or len(text.strip()) < 50:
            return text or ""

        try:
            cleaned = re.sub(r"\s+", " ", text).strip()
            truncated = cleaned[:self.config.max_abstract_len]
            result = self.summarizer(
                truncated,
                max_length=self.config.max_summary_len,
                min_length=self.config.min_summary_len,
                do_sample=False,
            )
            return result[0]["summary_text"]
        except Exception as e:
            logger.warning("摘要生成失敗: %s", e)
            return text[:self.config.max_summary_len] + "..."

    def extract_entities_ner(self, text: str) -> list[EntityMention]:
        if not text:
            return []

        entities = []
        try:
            if self.ner_pipeline == "fallback":
                return self._extract_entities_keyword(text)

            ner_results = self.ner_pipeline(text[:self.config.max_abstract_len])
            for ent in ner_results:
                if ent.get("score", 1.0) >= self.config.entity_confidence_threshold:
                    label = self._map_ner_label(ent.get("entity_group", ""))
                    entities.append(EntityMention(
                        text=ent["word"],
                        label=label,
                        start=ent["start"],
                        end=ent["end"],
                        confidence=ent.get("score", 1.0),
                    ))
        except Exception as e:
            logger.warning("NER 提取失敗，回退至關鍵字法: %s", e)
            return self._extract_entities_keyword(text)

        kw_entities = self._extract_entities_keyword(text)
        seen_spans = {(e.start, e.end) for e in entities}
        for ke in kw_entities:
            if (ke.start, ke.end) not in seen_spans:
                entities.append(ke)
                seen_spans.add((ke.start, ke.end))

        entities.sort(key=lambda e: e.start)
        return entities

    def _map_ner_label(self, label: str) -> str:
        mapping = {
            "DISEASE": "cancer_type",
            "CHEMICAL": "drug",
            "GENE": "gene",
            "GENE_PROTEIN": "gene",
            "CELL_LINE": "gene",
            "TREATMENT": "treatment",
            "PROCEDURE": "treatment",
            "MEDICATION": "drug",
            "BIO_PROCESS": "treatment",
        }
        return mapping.get(label.upper(), label.lower())

    def _extract_entities_keyword(self, text: str) -> list[EntityMention]:
        entities = []
        seen: set[tuple[str, str]] = set()

        lower_text = text.lower()
        for label, keywords in CANCER_ENTITY_KEYWORDS.items():
            for kw in sorted(keywords, key=len, reverse=True):
                for m in re.finditer(re.escape(kw), text, re.IGNORECASE):
                    key = (m.group(), label)
                    if key not in seen:
                        entities.append(EntityMention(
                            text=m.group(), label=label,
                            start=m.start(), end=m.end(),
                        ))
                        seen.add(key)
        entities.sort(key=lambda e: e.start)
        return entities

    def _categorize_entities(self, entities: list[EntityMention]) -> tuple[list[str], list[str], list[str], list[str]]:
        cancer_types = list(dict.fromkeys(e.text for e in entities if e.label == "cancer_type"))
        drugs = list(dict.fromkeys(e.text for e in entities if e.label == "drug"))
        genes = list(dict.fromkeys(e.text for e in entities if e.label == "gene"))
        treatments = list(dict.fromkeys(e.text for e in entities if e.label == "treatment"))
        return cancer_types, drugs, genes, treatments

    def analyze_article(self, article: Article) -> AnalyzedArticle:
        text = f"{article.title}. {article.abstract}"
        entities = self.extract_entities(text)
        summary = self.summarize_abstract(article.abstract)
        cancer_types, drugs, genes, treatments = self._categorize_entities(entities)

        return AnalyzedArticle(
            pmid=article.pmid,
            title=article.title,
            abstract=article.abstract,
            summary=summary,
            entities=entities,
            cancer_types=cancer_types,
            drugs=drugs,
            genes=genes,
            treatments=treatments,
            mesh_terms=article.mesh_terms,
            year=article.year,
            journal=article.journal,
            doi=article.doi,
        )

    def extract_entities(self, text: str) -> list[EntityMention]:
        return self.extract_entities_ner(text)

    def analyze_articles(self, articles: list[Article]) -> list[AnalyzedArticle]:
        return [self.analyze_article(a) for a in articles]

    def analyze_from_pubmed(self, query: str, max_results: int = 50) -> list[AnalyzedArticle]:
        articles = self.pubmed_fetcher.search(query, max_results=max_results)
        return self.analyze_articles(articles)

    def trend_analysis(self, analyzed: list[AnalyzedArticle]) -> TrendReport:
        if not analyzed:
            return TrendReport(
                query="", total_articles=0, date_range=("", ""),
                cancer_type_freq={}, drug_freq={}, gene_freq={},
                treatment_freq={}, yearly_distribution={},
                top_journals=[],
            )

        cancer_counter: Counter = Counter()
        drug_counter: Counter = Counter()
        gene_counter: Counter = Counter()
        treatment_counter: Counter = Counter()
        yearly_counter: Counter = Counter()
        journal_counter: Counter = Counter()

        for a in analyzed:
            for ct in a.cancer_types:
                cancer_counter[ct] += 1
            for d in a.drugs:
                drug_counter[d] += 1
            for g in a.genes:
                gene_counter[g] += 1
            for t in a.treatments:
                treatment_counter[t] += 1
            if a.year:
                yearly_counter[str(a.year)] += 1
            if a.journal:
                journal_counter[a.journal] += 1

        years = [a.year for a in analyzed if a.year]
        date_range = (
            str(min(years)) if years else "",
            str(max(years)) if years else "",
        )

        key_findings = self._generate_findings(cancer_counter, drug_counter, gene_counter, treatment_counter)

        return TrendReport(
            query="trend_analysis",
            total_articles=len(analyzed),
            date_range=date_range,
            cancer_type_freq=dict(cancer_counter.most_common()),
            drug_freq=dict(drug_counter.most_common(20)),
            gene_freq=dict(gene_counter.most_common(20)),
            treatment_freq=dict(treatment_counter.most_common()),
            yearly_distribution=dict(sorted(yearly_counter.items())),
            top_journals=journal_counter.most_common(10),
            key_findings=key_findings,
        )

    def _generate_findings(self, cancer_freq: Counter, drug_freq: Counter,
                           gene_freq: Counter, treatment_freq: Counter) -> list[str]:
        findings = []
        if cancer_freq:
            top_cancer = cancer_freq.most_common(3)
            findings.append(f"主要癌種: {', '.join(f'{c}({n}篇)' for c, n in top_cancer)}")
        if drug_freq:
            top_drug = drug_freq.most_common(3)
            findings.append(f"熱門藥物: {', '.join(f'{d}({n}次)' for d, n in top_drug)}")
        if gene_freq:
            top_gene = gene_freq.most_common(3)
            findings.append(f"關鍵基因: {', '.join(f'{g}({n}次)' for g, n in top_gene)}")
        if treatment_freq:
            top_tx = treatment_freq.most_common(3)
            findings.append(f"主要治療方法: {', '.join(f'{t}({n}次)' for t, n in top_tx)}")
        return findings

    def analyze_cancer_type(self, cancer_type: str, additional_terms: str = "",
                            max_results: int = 50) -> tuple[list[AnalyzedArticle], TrendReport]:
        articles = self.pubmed_fetcher.search_cancer(cancer_type, additional_terms, max_results)
        analyzed = self.analyze_articles(articles)
        trend = self.trend_analysis(analyzed)
        trend.query = f"{cancer_type} {additional_terms}"
        return analyzed, trend

    def batch_analyze(self, queries: list[str], max_results_per_query: int = 30) -> dict[str, list[AnalyzedArticle]]:
        return {
            q: self.analyze_from_pubmed(q, max_results_per_query)
            for q in queries
        }
