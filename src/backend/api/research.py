import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.session import get_db
from src.backend.database import create_research_paper, search_research_papers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/research", tags=["research"])


# --- Schemas ---

class PaperSubmitRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    authors: str = Field(..., min_length=1)
    journal: str | None = None
    year: int | None = Field(None, ge=1900, le=2100)
    doi: str | None = None
    abstract: str | None = None
    keywords: str | None = None


class PaperSubmitResponse(BaseModel):
    paper_id: str
    title: str
    status: str
    submitted_at: str


class SandboxRunRequest(BaseModel):
    model: str = Field(..., description="Model identifier to run")
    payload: dict = Field(default_factory=dict, description="Input parameters")


class SandboxRunResponse(BaseModel):
    run_id: str
    model: str
    output: dict
    latency_ms: int
    status: str


class DataUploadResponse(BaseModel):
    file_id: str
    file_name: str
    file_size: int
    status: str
    uploaded_at: str


class SandboxHistoryItem(BaseModel):
    run_id: str
    model: str
    summary: str
    latency_ms: int
    created_at: str


class SandboxHistoryResponse(BaseModel):
    runs: list[SandboxHistoryItem]


# --- In-memory stores (sandbox / uploads remain in-memory; papers use DB) ---

_sandbox_runs: list[dict] = []
_uploads: list[dict] = []


# --- Paper Endpoints (DB-backed) ---

@router.post("/papers", response_model=PaperSubmitResponse)
async def submit_paper(body: PaperSubmitRequest, db: AsyncSession = Depends(get_db)):
    try:
        authors_list = [a.strip() for a in body.authors.split(",") if a.strip()]
        keywords_list = [kw.strip() for kw in (body.keywords or "").split(",") if kw.strip()]
        paper = await create_research_paper(
            db=db,
            title=body.title,
            authors=authors_list,
            journal=body.journal,
            year=body.year,
            doi=body.doi,
            abstract=body.abstract,
            keywords=keywords_list,
        )
        logger.info("Paper submitted: %s (%s)", body.title, paper.id)
        return PaperSubmitResponse(
            paper_id=str(paper.id),
            title=paper.title,
            status="pending_review",
            submitted_at=paper.created_at.isoformat(),
        )
    except Exception as e:
        logger.exception("Paper submission failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/papers", response_model=list[PaperSubmitResponse])
async def list_papers(
    query: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    try:
        papers = await search_research_papers(
            db=db,
            query=query,
            year_from=year_from,
            year_to=year_to,
            skip=skip,
            limit=limit,
        )
        return [
            PaperSubmitResponse(
                paper_id=str(p.id),
                title=p.title,
                status="pending_review",
                submitted_at=p.created_at.isoformat(),
            )
            for p in papers
        ]
    except Exception as e:
        logger.exception("List papers failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


# --- Data Upload Endpoints (in-memory) ---

@router.post("/uploads", response_model=DataUploadResponse)
async def upload_file(file: UploadFile = File(...), description: str = Form("")):
    try:
        content = await file.read()
        file_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        record = {
            "file_id": file_id,
            "file_name": file.filename,
            "file_size": len(content),
            "content_type": file.content_type,
            "description": description,
            "status": "uploaded",
            "uploaded_at": now,
        }
        _uploads.append(record)
        logger.info("File uploaded: %s (%d bytes)", file.filename, len(content))
        return DataUploadResponse(
            file_id=file_id,
            file_name=file.filename or "unknown",
            file_size=len(content),
            status="uploaded",
            uploaded_at=now,
        )
    except Exception as e:
        logger.exception("File upload failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/uploads", response_model=list[DataUploadResponse])
async def list_uploads():
    return [
        DataUploadResponse(
            file_id=u["file_id"],
            file_name=u["file_name"],
            file_size=u["file_size"],
            status=u["status"],
            uploaded_at=u["uploaded_at"],
        )
        for u in _uploads
    ]


# --- Sandbox Endpoints (in-memory) ---

@router.post("/sandbox/run", response_model=SandboxRunResponse)
async def sandbox_run(body: SandboxRunRequest):
    try:
        run_id = str(uuid.uuid4())
        import time, random
        start = time.monotonic()

        model_registry = {
            "cancer_classifier": _mock_classifier,
            "drug_response": _mock_drug_response,
            "mutation_impact": _mock_mutation,
        }

        runner = model_registry.get(body.model)
        if runner is None:
            raise HTTPException(status_code=404, detail=f"Unknown model: {body.model}")

        output = runner(body.payload)
        latency = int((time.monotonic() - start) * 1000)

        record = {
            "run_id": run_id,
            "model": body.model,
            "summary": str(output),
            "latency_ms": latency,
            "created_at": datetime.utcnow().isoformat(),
        }
        _sandbox_runs.append(record)

        return SandboxRunResponse(
            run_id=run_id,
            model=body.model,
            output=output,
            latency_ms=latency,
            status="completed",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Sandbox run failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sandbox/history", response_model=SandboxHistoryResponse)
async def sandbox_history():
    return SandboxHistoryResponse(
        runs=[
            SandboxHistoryItem(**r)
            for r in _sandbox_runs[-50:]
        ]
    )


# --- Mock model runners ---

def _mock_classifier(payload: dict) -> dict:
    biomarkers = payload.get("biomarkers", {})
    age = payload.get("age", 50)
    if any(v > 50 for v in biomarkers.values()):
        return {"cancer_type": "Breast Cancer", "probability": 0.94, "risk_level": "High"}
    if age > 60:
        return {"cancer_type": "Lung Cancer", "probability": 0.76, "risk_level": "Moderate"}
    return {"cancer_type": "Unknown", "probability": 0.12, "risk_level": "Low"}


def _mock_drug_response(payload: dict) -> dict:
    drug = payload.get("drug", "unknown")
    return {
        "drug": drug,
        "IC50": round(0.042, 3),
        "unit": "\u00b5M",
        "classification": "sensitive",
    }


def _mock_mutation(payload: dict) -> dict:
    variant = payload.get("variant", "unknown")
    return {
        "variant": variant,
        "pathogenicity_score": round(0.98, 2),
        "classification": "Pathogenic",
    }
