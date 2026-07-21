import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ETLResult:
    source: str
    records_loaded: int
    records_skipped: int
    errors: list[str]


class BaseExtractor(ABC):
    @abstractmethod
    async def extract(self, source_path: Path) -> pd.DataFrame:
        ...


class CSVExtractor(BaseExtractor):
    async def extract(self, source_path: Path) -> pd.DataFrame:
        logger.info(f"從 CSV 提取: {source_path}")
        return pd.read_csv(source_path, low_memory=False)


class JSONExtractor(BaseExtractor):
    async def extract(self, source_path: Path) -> pd.DataFrame:
        logger.info(f"從 JSON 提取: {source_path}")
        return pd.read_json(source_path)


class ExcelExtractor(BaseExtractor):
    async def extract(self, source_path: Path, sheet_name: Optional[str] = None) -> pd.DataFrame:
        logger.info(f"從 Excel 提取: {source_path} sheet={sheet_name}")
        return pd.read_excel(source_path, sheet_name=sheet_name or 0)


class BaseTransformer(ABC):
    @abstractmethod
    async def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        ...


class CancerDataTransformer(BaseTransformer):
    def __init__(self, column_map: Optional[dict[str, str]] = None):
        self.column_map = column_map or {}

    async def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info(f"轉換前 shape: {df.shape}")
        if self.column_map:
            df = df.rename(columns=self.column_map)
        df = self._clean(df)
        logger.info(f"轉換後 shape: {df.shape}")
        return df

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.drop_duplicates()
        df = df.replace({float("nan"): None, float("inf"): None, float("-inf"): None})
        return df


class BaseLoader(ABC):
    @abstractmethod
    async def load(self, df: pd.DataFrame, batch_size: int = 500) -> ETLResult:
        ...


class ETLPipeline:
    def __init__(
        self,
        extractor: BaseExtractor,
        transformer: BaseTransformer,
        loader: BaseLoader,
        name: str = "unnamed",
    ):
        self.extractor = extractor
        self.transformer = transformer
        self.loader = loader
        self.name = name

    async def run(
        self,
        source_path: Path,
        batch_size: int = 500,
    ) -> ETLResult:
        logger.info(f"ETL 管線 [{self.name}] 開始: {source_path}")
        raw = await self.extractor.extract(source_path)
        logger.info(f"提取完成: {len(raw)} 行")
        cleaned = await self.transformer.transform(raw)
        logger.info(f"轉換完成: {len(cleaned)} 行")
        result = await self.loader.load(cleaned, batch_size=batch_size)
        logger.info(f"ETL 管線 [{self.name}] 完成: {result}")
        return result
