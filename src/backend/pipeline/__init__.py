"""
Pipeline package — variant normalization, VEP annotation, and analysis jobs.
"""
from src.backend.pipeline.normalization import BcftoolsAdapter, normalize_minimal_representation, NormalizationResult
from src.backend.pipeline.vep_adapter import VEPAdapter
from src.backend.pipeline.opencravat_adapter import OpenCRAVATAdapter
from src.backend.pipeline.analysis_job import AnalysisJob, create_and_run_job, get_cached_job, load_job_from_db
