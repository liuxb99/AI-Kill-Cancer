"""Apply Phase 3H public-data cache integration to existing source adapters.

This helper is idempotent and is removed after CI commits the generated source
changes. It keeps large, previously reviewed service files out of hand-edited
GitHub API payloads.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GDC = ROOT / "src/backend/importers/ptc_tcga/downloader.py"
KNOWLEDGE = ROOT / "src/backend/services/ptc_knowledge_service.py"
LITERATURE = ROOT / "src/backend/services/ptc_literature_service.py"
COMPLETION = ROOT / "src/backend/services/ptc_completion_service.py"
API = ROOT / "src/backend/api/v1/ptc_completion.py"


def replace_once(path: Path, old: str, new: str, marker: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    if old not in text:
        raise RuntimeError(f"Expected block not found in {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_gdc() -> None:
    replace_once(
        GDC,
        "from src.backend.importers.ptc_tcga.maf_parser import merge_variants_into_cases, parse_maf_bytes\n",
        "from src.backend.importers.ptc_tcga.maf_parser import merge_variants_into_cases, parse_maf_bytes\n"
        "from src.backend.sync.public_data_store import PublicDataStore\n",
        "from src.backend.sync.public_data_store import PublicDataStore",
    )
    replace_once(
        GDC,
        "    def __init__(self, base_url: str = GDC_API, timeout: int = 60):\n"
        "        self.base_url = base_url.rstrip(\"/\")\n"
        "        self.timeout = timeout\n",
        "    def __init__(\n"
        "        self,\n"
        "        base_url: str = GDC_API,\n"
        "        timeout: int = 60,\n"
        "        store: PublicDataStore | None = None,\n"
        "        *,\n"
        "        force_refresh: bool = False,\n"
        "    ):\n"
        "        self.base_url = base_url.rstrip(\"/\")\n"
        "        self.timeout = timeout\n"
        "        self.store = store or PublicDataStore(force_refresh=force_refresh)\n",
        "self.store = store or PublicDataStore",
    )
    replace_once(
        GDC,
        "            grouped = parse_maf_bytes(self.download_public_file(str(file_id)))\n",
        "            grouped = parse_maf_bytes(\n"
        "                self.download_public_file(str(file_id), expected_md5=item.get(\"md5sum\"))\n"
        "            )\n",
        "expected_md5=item.get(\"md5sum\")",
    )
    replace_once(
        GDC,
        "    def download_public_file(self, file_id: str) -> bytes:\n"
        "        if not file_id or \"/\" in file_id or \"..\" in file_id:\n"
        "            raise ValueError(\"invalid GDC file id\")\n"
        "        request = Request(\n"
        "            f\"{self.base_url}/data/{file_id}\",\n"
        "            headers={\"Accept\": \"application/octet-stream\", \"User-Agent\": \"AI-Kill-Cancer/ptc-importer\"},\n"
        "        )\n"
        "        with urlopen(request, timeout=self.timeout) as response:  # nosec B310 - fixed HTTPS GDC endpoint\n"
        "            return response.read()\n\n"
        "    def _get_json(self, path: str) -> dict[str, Any]:\n"
        "        request = Request(\n"
        "            f\"{self.base_url}{path}\",\n"
        "            headers={\"Accept\": \"application/json\", \"User-Agent\": \"AI-Kill-Cancer/ptc-importer\"},\n"
        "        )\n"
        "        with urlopen(request, timeout=self.timeout) as response:  # nosec B310 - configured trusted GDC endpoint\n"
        "            return json.loads(response.read().decode(\"utf-8\"))\n",
        "    def download_public_file(\n"
        "        self, file_id: str, *, expected_md5: str | None = None\n"
        "    ) -> bytes:\n"
        "        if not file_id or \"/\" in file_id or \"..\" in file_id:\n"
        "            raise ValueError(\"invalid GDC file id\")\n"
        "        url = f\"{self.base_url}/data/{file_id}\"\n\n"
        "        def fetch() -> bytes:\n"
        "            request = Request(\n"
        "                url,\n"
        "                headers={\"Accept\": \"application/octet-stream\", \"User-Agent\": \"AI-Kill-Cancer/ptc-importer\"},\n"
        "            )\n"
        "            with urlopen(request, timeout=self.timeout) as response:  # nosec B310 - fixed HTTPS GDC endpoint\n"
        "                return response.read()\n\n"
        "        stored = self.store.get_or_fetch(\n"
        "            source=\"gdc\",\n"
        "            identity=self.store.canonical_identity(url),\n"
        "            fetcher=fetch,\n"
        "            expected_md5=expected_md5,\n"
        "            metadata={\"url\": url, \"file_id\": file_id},\n"
        "            suffix=\".maf\",\n"
        "        )\n"
        "        return stored.content\n\n"
        "    def _get_json(self, path: str) -> dict[str, Any]:\n"
        "        url = f\"{self.base_url}{path}\"\n\n"
        "        def fetch() -> bytes:\n"
        "            request = Request(\n"
        "                url,\n"
        "                headers={\"Accept\": \"application/json\", \"User-Agent\": \"AI-Kill-Cancer/ptc-importer\"},\n"
        "            )\n"
        "            with urlopen(request, timeout=self.timeout) as response:  # nosec B310 - configured trusted GDC endpoint\n"
        "                return response.read()\n\n"
        "        stored = self.store.get_or_fetch(\n"
        "            source=\"gdc\",\n"
        "            identity=self.store.canonical_identity(url),\n"
        "            fetcher=fetch,\n"
        "            metadata={\"url\": url, \"media_type\": \"application/json\"},\n"
        "            suffix=\".json\",\n"
        "        )\n"
        "        return json.loads(stored.content.decode(\"utf-8\"))\n",
        "stored = self.store.get_or_fetch",
    )


def patch_knowledge() -> None:
    replace_once(
        KNOWLEDGE,
        "from src.backend.domain.ptc_knowledge import (\n",
        "from src.backend.sync.public_data_store import PublicDataStore\n\n"
        "from src.backend.domain.ptc_knowledge import (\n",
        "from src.backend.sync.public_data_store import PublicDataStore",
    )
    replace_once(
        KNOWLEDGE,
        "    def __init__(self, db: AsyncSession, client: httpx.AsyncClient | None = None):\n"
        "        self.db = db\n"
        "        self.client = client\n",
        "    def __init__(\n"
        "        self,\n"
        "        db: AsyncSession,\n"
        "        client: httpx.AsyncClient | None = None,\n"
        "        store: PublicDataStore | None = None,\n"
        "        *,\n"
        "        force_refresh: bool = False,\n"
        "    ):\n"
        "        self.db = db\n"
        "        self.client = client\n"
        "        self.store = store or PublicDataStore(force_refresh=force_refresh)\n",
        "self.store = store or PublicDataStore",
    )
    replace_once(
        KNOWLEDGE,
        "    async def _http(self) -> httpx.AsyncClient:\n"
        "        if self.client is not None:\n"
        "            return self.client\n"
        "        return httpx.AsyncClient(timeout=45.0, follow_redirects=True)\n",
        "    async def _http(self) -> httpx.AsyncClient:\n"
        "        if self.client is not None:\n"
        "            return self.client\n"
        "        return httpx.AsyncClient(timeout=45.0, follow_redirects=True)\n\n"
        "    async def _get_json(\n"
        "        self, client: httpx.AsyncClient, source: str, url: str, params: dict[str, Any]\n"
        "    ) -> dict[str, Any]:\n"
        "        identity = self.store.canonical_identity(url, params)\n\n"
        "        async def fetch() -> bytes:\n"
        "            response = await client.get(url, params=params)\n"
        "            response.raise_for_status()\n"
        "            return response.content\n\n"
        "        stored = await self.store.aget_or_fetch(\n"
        "            source=source,\n"
        "            identity=identity,\n"
        "            fetcher=fetch,\n"
        "            metadata={\"url\": url, \"params\": params, \"media_type\": \"application/json\"},\n"
        "            suffix=\".json\",\n"
        "        )\n"
        "        return httpx.Response(200, content=stored.content).json()\n",
        "async def _get_json(",
    )
    replace_once(
        KNOWLEDGE,
        "            response = await client.get(\n"
        "                CTGOV_STUDIES_URL,\n"
        "                params={\n"
        "                    \"query.cond\": \"Papillary Thyroid Carcinoma\",\n"
        "                    \"pageSize\": min(max(page_size, 1), 1000),\n"
        "                    \"format\": \"json\",\n"
        "                },\n"
        "            )\n"
        "            response.raise_for_status()\n"
        "            count = 0\n"
        "            for study in response.json().get(\"studies\", []):\n",
        "            params = {\n"
        "                \"query.cond\": \"Papillary Thyroid Carcinoma\",\n"
        "                \"pageSize\": min(max(page_size, 1), 1000),\n"
        "                \"format\": \"json\",\n"
        "            }\n"
        "            payload = await self._get_json(client, \"clinicaltrials.gov\", CTGOV_STUDIES_URL, params)\n"
        "            count = 0\n"
        "            for study in payload.get(\"studies\", []):\n",
        "payload = await self._get_json(client, \"clinicaltrials.gov\"",
    )
    replace_once(
        KNOWLEDGE,
        "                response = await client.get(OPENFDA_LABEL_URL, params={\"search\": search, \"limit\": 10})\n"
        "                if response.status_code == 404:\n"
        "                    continue\n"
        "                response.raise_for_status()\n"
        "                for record in response.json().get(\"results\", []):\n",
        "                params = {\"search\": search, \"limit\": 10}\n"
        "                try:\n"
        "                    payload = await self._get_json(client, \"openfda\", OPENFDA_LABEL_URL, params)\n"
        "                except httpx.HTTPStatusError as exc:\n"
        "                    if exc.response.status_code == 404:\n"
        "                        continue\n"
        "                    raise\n"
        "                for record in payload.get(\"results\", []):\n",
        "payload = await self._get_json(client, \"openfda\"",
    )


def patch_literature() -> None:
    replace_once(
        LITERATURE,
        "from src.backend.services.ptc_knowledge_service import PTCKnowledgeService, infer_target_genes\n",
        "from src.backend.services.ptc_knowledge_service import PTCKnowledgeService, infer_target_genes\n"
        "from src.backend.sync.public_data_store import PublicDataStore\n",
        "from src.backend.sync.public_data_store import PublicDataStore",
    )
    replace_once(
        LITERATURE,
        "    def __init__(self, db: AsyncSession, client: httpx.AsyncClient | None = None):\n"
        "        self.db = db\n"
        "        self.client = client\n",
        "    def __init__(\n"
        "        self,\n"
        "        db: AsyncSession,\n"
        "        client: httpx.AsyncClient | None = None,\n"
        "        store: PublicDataStore | None = None,\n"
        "        *,\n"
        "        force_refresh: bool = False,\n"
        "    ):\n"
        "        self.db = db\n"
        "        self.client = client\n"
        "        self.store = store or PublicDataStore(force_refresh=force_refresh)\n",
        "self.store = store or PublicDataStore",
    )
    replace_once(
        LITERATURE,
        "    async def _http(self) -> httpx.AsyncClient:\n"
        "        return self.client or httpx.AsyncClient(timeout=60.0, follow_redirects=True)\n",
        "    async def _http(self) -> httpx.AsyncClient:\n"
        "        return self.client or httpx.AsyncClient(timeout=60.0, follow_redirects=True)\n\n"
        "    async def _get_bytes(\n"
        "        self,\n"
        "        client: httpx.AsyncClient,\n"
        "        source: str,\n"
        "        url: str,\n"
        "        *,\n"
        "        params: dict[str, Any] | None = None,\n"
        "        method: str = \"GET\",\n"
        "        headers: dict[str, str] | None = None,\n"
        "        json_body: dict[str, Any] | None = None,\n"
        "        suffix: str = \".bin\",\n"
        "    ) -> bytes:\n"
        "        identity_params = dict(params or {})\n"
        "        if json_body is not None:\n"
        "            identity_params[\"__body__\"] = json_body\n"
        "        identity = self.store.canonical_identity(f\"{method}:{url}\", identity_params)\n\n"
        "        async def fetch() -> bytes:\n"
        "            response = await client.request(\n"
        "                method, url, params=params, headers=headers, json=json_body\n"
        "            )\n"
        "            response.raise_for_status()\n"
        "            return response.content\n\n"
        "        stored = await self.store.aget_or_fetch(\n"
        "            source=source,\n"
        "            identity=identity,\n"
        "            fetcher=fetch,\n"
        "            metadata={\"url\": url, \"params\": params or {}, \"method\": method},\n"
        "            suffix=suffix,\n"
        "        )\n"
        "        return stored.content\n",
        "async def _get_bytes(",
    )
    replace_once(
        LITERATURE,
        "            response = await client.get(\n"
        "                NCBI_EFETCH_URL,\n"
        "                params={\"db\": \"pmc\", \"id\": \",\".join(sorted(set(pmcids))), \"retmode\": \"xml\"},\n"
        "            )\n"
        "            response.raise_for_status()\n"
        "            return parse_pmc_fulltext_xml(response.text)\n",
        "            payload = await self._get_bytes(\n"
        "                client,\n"
        "                \"pmc\",\n"
        "                NCBI_EFETCH_URL,\n"
        "                params={\"db\": \"pmc\", \"id\": \",\".join(sorted(set(pmcids))), \"retmode\": \"xml\"},\n"
        "                suffix=\".xml\",\n"
        "            )\n"
        "            return parse_pmc_fulltext_xml(payload.decode(\"utf-8\"))\n",
        "payload = await self._get_bytes(\n                client,\n                \"pmc\"",
    )
    replace_once(
        LITERATURE,
        "            search = await client.get(\n"
        "                NCBI_ESEARCH_URL,\n"
        "                params={\"db\": \"pubmed\", \"term\": query, \"retmode\": \"json\", \"retmax\": min(max(retmax, 1), 500)},\n"
        "            )\n"
        "            search.raise_for_status()\n"
        "            ids = search.json().get(\"esearchresult\", {}).get(\"idlist\", [])\n",
        "            search_payload = await self._get_bytes(\n"
        "                client,\n"
        "                \"pubmed\",\n"
        "                NCBI_ESEARCH_URL,\n"
        "                params={\"db\": \"pubmed\", \"term\": query, \"retmode\": \"json\", \"retmax\": min(max(retmax, 1), 500)},\n"
        "                suffix=\".json\",\n"
        "            )\n"
        "            ids = httpx.Response(200, content=search_payload).json().get(\"esearchresult\", {}).get(\"idlist\", [])\n",
        "search_payload = await self._get_bytes(",
    )
    replace_once(
        LITERATURE,
        "            fetch = await client.get(\n"
        "                NCBI_EFETCH_URL,\n"
        "                params={\"db\": \"pubmed\", \"id\": \",\".join(ids), \"retmode\": \"xml\"},\n"
        "            )\n"
        "            fetch.raise_for_status()\n"
        "            rows = parse_pubmed_xml(fetch.text)\n",
        "            fetch_payload = await self._get_bytes(\n"
        "                client,\n"
        "                \"pubmed\",\n"
        "                NCBI_EFETCH_URL,\n"
        "                params={\"db\": \"pubmed\", \"id\": \",\".join(ids), \"retmode\": \"xml\"},\n"
        "                suffix=\".xml\",\n"
        "            )\n"
        "            rows = parse_pubmed_xml(fetch_payload.decode(\"utf-8\"))\n",
        "fetch_payload = await self._get_bytes(",
    )
    replace_once(
        LITERATURE,
        "            response = await client.post(\n"
        "                CIVIC_GRAPHQL_URL,\n"
        "                headers={\"Authorization\": f\"Bearer {token}\", \"Content-Type\": \"application/json\"},\n"
        "                json={\"query\": query, \"variables\": {\"names\": sorted(set(gene_symbols))}},\n"
        "            )\n"
        "            response.raise_for_status()\n"
        "            body = response.json()\n",
        "            civic_payload = await self._get_bytes(\n"
        "                client,\n"
        "                \"civic\",\n"
        "                CIVIC_GRAPHQL_URL,\n"
        "                method=\"POST\",\n"
        "                headers={\"Authorization\": f\"Bearer {token}\", \"Content-Type\": \"application/json\"},\n"
        "                json_body={\"query\": query, \"variables\": {\"names\": sorted(set(gene_symbols))}},\n"
        "                suffix=\".json\",\n"
        "            )\n"
        "            body = httpx.Response(200, content=civic_payload).json()\n",
        "civic_payload = await self._get_bytes(",
    )


def patch_completion() -> None:
    replace_once(
        COMPLETION,
        "from src.backend.services.ptc_literature_service import PTCLiteratureService\n",
        "from src.backend.services.ptc_literature_service import PTCLiteratureService\n"
        "from src.backend.sync.public_data_store import PublicDataStore\n",
        "from src.backend.sync.public_data_store import PublicDataStore",
    )
    replace_once(
        COMPLETION,
        "    def __init__(self, db: AsyncSession):\n"
        "        self.db = db\n",
        "    def __init__(\n"
        "        self, db: AsyncSession, *, force_refresh: bool = False, store: PublicDataStore | None = None\n"
        "    ):\n"
        "        self.db = db\n"
        "        self.store = store or PublicDataStore(force_refresh=force_refresh)\n",
        "self.store = store or PublicDataStore",
    )
    replace_once(
        COMPLETION,
        "                GDCClient().fetch_ptc_cases_with_mutations,\n",
        "                GDCClient(store=self.store).fetch_ptc_cases_with_mutations,\n",
        "GDCClient(store=self.store)",
    )
    replace_once(
        COMPLETION,
        "        knowledge = PTCKnowledgeService(self.db)\n"
        "        literature = PTCLiteratureService(self.db)\n",
        "        knowledge = PTCKnowledgeService(self.db, store=self.store)\n"
        "        literature = PTCLiteratureService(self.db, store=self.store)\n",
        "PTCKnowledgeService(self.db, store=self.store)",
    )
    replace_once(
        COMPLETION,
        "            \"summary\": summary,\n"
        "        }\n",
        "            \"summary\": summary,\n"
        "            \"download_store\": self.store.stats(),\n"
        "        }\n",
        "\"download_store\": self.store.stats()",
    )


def patch_api() -> None:
    replace_once(
        API,
        "    include_civic: bool = False\n",
        "    include_civic: bool = False\n"
        "    force_refresh: bool = False\n",
        "force_refresh: bool = False",
    )
    replace_once(
        API,
        "    return await PTCCompletionService(db).sync_all(\n",
        "    return await PTCCompletionService(db, force_refresh=body.force_refresh).sync_all(\n",
        "force_refresh=body.force_refresh",
    )


def main() -> None:
    patch_gdc()
    patch_knowledge()
    patch_literature()
    patch_completion()
    patch_api()


if __name__ == "__main__":
    main()
