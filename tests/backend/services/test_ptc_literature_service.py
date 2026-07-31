import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.ptc_knowledge import PTCEvidenceRecordModel
from src.backend.services.ptc_knowledge_service import PTCKnowledgeService
from src.backend.services.ptc_literature_service import parse_pubmed_xml


def test_parse_pubmed_xml_extracts_ptc_evidence():
    payload = """
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>12345678</PMID>
          <Article>
            <ArticleTitle>BRAF V600E in papillary thyroid carcinoma</ArticleTitle>
            <Abstract><AbstractText>RET and BRAF molecular evidence in PTC.</AbstractText></Abstract>
            <Journal>
              <JournalIssue><PubDate><Year>2026</Year></PubDate></JournalIssue>
              <Title>Thyroid Research</Title>
            </Journal>
            <AuthorList><Author><ForeName>Ada</ForeName><LastName>Chen</LastName></Author></AuthorList>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>
    """
    rows = parse_pubmed_xml(payload)
    assert rows[0]["pmid"] == "12345678"
    assert rows[0]["title"].startswith("BRAF")
    assert rows[0]["journal"] == "Thyroid Research"
    assert rows[0]["authors"] == ["Ada Chen"]
    assert "BRAF" in rows[0]["genes"]
    assert "RET" in rows[0]["genes"]


@pytest.mark.asyncio
async def test_same_publication_can_create_multiple_gene_assertions():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        service = PTCKnowledgeService(session)
        for gene in ("BRAF", "RET"):
            await service.create_evidence(
                source_name="PubMed",
                source_record_id="12345678",
                evidence_type="publication",
                title="BRAF and RET evidence",
                gene_symbol=gene,
                publication_id="12345678",
            )
        rows = list(
            (
                await session.execute(
                    select(PTCEvidenceRecordModel).order_by(PTCEvidenceRecordModel.gene_symbol)
                )
            ).scalars()
        )
        assert [row.gene_symbol for row in rows] == ["BRAF", "RET"]
        assert len({row.evidence_key for row in rows}) == 2
    await engine.dispose()
