"""
API v1 router — aggregates all v1 route modules.
"""
from fastapi import APIRouter

from src.backend.api.v1.patients import router as patients_router
from src.backend.api.v1.cases import router as cases_router
from src.backend.api.v1.specimens import router as specimens_router
from src.backend.api.v1.sequencing import router as sequencing_router
from src.backend.api.v1.uploads import router as uploads_router
from src.backend.api.v1.variants import router as variants_router
from src.backend.api.v1.analyses import router as analyses_router
from src.backend.api.v1.upload_vcf import router as upload_vcf_router
from src.backend.api.v1.evidence import router as evidence_router
from src.backend.api.v1.ranking import router as ranking_router
from src.backend.api.v1.knowledge import router as knowledge_router
from src.backend.api.v1.reasoning import router as reasoning_router
from src.backend.api.v1.reports import router as reports_router
from src.backend.api.v1.workbench import router as workbench_router

router = APIRouter(prefix="/api/v1")

router.include_router(patients_router)
router.include_router(cases_router)
router.include_router(specimens_router)
router.include_router(sequencing_router)
router.include_router(uploads_router)
router.include_router(variants_router)
router.include_router(analyses_router)
router.include_router(upload_vcf_router)
router.include_router(evidence_router)
router.include_router(ranking_router)
router.include_router(knowledge_router)
router.include_router(reasoning_router)
router.include_router(reports_router)
router.include_router(workbench_router)
