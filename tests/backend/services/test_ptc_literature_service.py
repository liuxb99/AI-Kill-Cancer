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
