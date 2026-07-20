# AI-Kill-Cancer v1.0.1 Release Notes

## Fixed
- Case-based drug ranking (was 501)
- Knowledge layer now has real ClinVar, PubMed, ClinicalTrials.gov adapters
- PDF report generation framework
- CI/CD pipeline (GitHub Actions)
- Missing VariantRepository.find_by_case method

## Added
- 21 integration tests across all layers
- Public API knowledge source adapters
- PDFRenderer with weasyprint/playwright support

## Known Limitations
- External API live tests: NOT RUN
- Docker build: NOT VERIFIED
- Frontend: v0.4.0 baseline (not extended in this patch)
