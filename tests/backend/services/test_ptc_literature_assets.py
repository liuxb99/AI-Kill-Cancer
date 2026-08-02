from src.backend.services.ptc_literature_service import parse_pmc_fulltext_xml, parse_pubmed_xml

PUBMED_XML = """
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>BRAF V600E in papillary thyroid carcinoma</ArticleTitle>
        <Abstract><AbstractText>BRAF V600E activates MAPK signaling.</AbstractText></Abstract>
        <Journal><JournalIssue><PubDate><Year>2026</Year></PubDate></JournalIssue><Title>PTC Journal</Title></Journal>
        <AuthorList><Author><ForeName>Ada</ForeName><LastName>Lovelace</LastName></Author></AuthorList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">12345678</ArticleId>
        <ArticleId IdType="pmc">PMC9999999</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""

PMC_XML = """
<pmc-articleset xmlns:xlink="http://www.w3.org/1999/xlink">
  <article>
    <front><article-meta><article-id pub-id-type="pmcid">PMC9999999</article-id></article-meta></front>
    <body>
      <fig id="F1">
        <label>Figure 1</label>
        <caption><p>BRAF pathway response.</p></caption>
        <graphic xlink:href="figure1.jpg" />
      </fig>
      <table-wrap id="T1">
        <label>Table 1</label>
        <caption><p>Observed variants.</p></caption>
        <table>
          <thead><tr><th>Gene</th><th>Variant</th></tr></thead>
          <tbody>
            <tr><td>BRAF</td><td>V600E</td></tr>
            <tr><td>RET</td><td>Fusion</td></tr>
          </tbody>
        </table>
      </table-wrap>
    </body>
  </article>
</pmc-articleset>
"""


def test_parse_pubmed_xml_includes_pmcid_and_gene():
    rows = parse_pubmed_xml(PUBMED_XML)

    assert len(rows) == 1
    assert rows[0]["pmid"] == "12345678"
    assert rows[0]["pmcid"] == "PMC9999999"
    assert rows[0]["genes"] == ["BRAF"]
    assert rows[0]["authors"] == ["Ada Lovelace"]


def test_parse_pmc_fulltext_extracts_bounded_figures_and_tables():
    assets = parse_pmc_fulltext_xml(PMC_XML)["PMC9999999"]

    assert assets["full_text_url"].endswith("/articles/PMC9999999/")
    assert assets["figures"] == [
        {
            "figure_id": "F1",
            "label": "Figure 1",
            "caption": "BRAF pathway response.",
            "image_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9999999/bin/figure1.jpg",
            "source_href": "figure1.jpg",
        }
    ]
    assert assets["tables"][0]["headers"] == ["Gene", "Variant"]
    assert assets["tables"][0]["rows"] == [["BRAF", "V600E"], ["RET", "Fusion"]]
    assert assets["tables"][0]["row_count"] == 2
