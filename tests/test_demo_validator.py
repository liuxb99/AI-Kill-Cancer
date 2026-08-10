from pathlib import Path

from src.backend.demo.validator import validate_demo_dataset


def test_bundled_demo_dataset_is_valid():
    result = validate_demo_dataset(Path('data/demo'))
    assert result.ok is True
    assert result.errors == []
    assert result.counts['patients'] == 3
    assert result.counts['cancer_cases'] == 3
    assert result.counts['variants'] == 3
    assert result.counts['evidence'] == 3


def test_validator_detects_broken_reference(tmp_path):
    source = Path('data/demo')
    for file in source.glob('*.csv'):
        (tmp_path / file.name).write_text(file.read_text(encoding='utf-8'), encoding='utf-8')

    cases = tmp_path / 'cancer_cases.csv'
    cases.write_text(cases.read_text(encoding='utf-8').replace('PTC-PATIENT-001', 'MISSING-PATIENT', 1), encoding='utf-8')

    result = validate_demo_dataset(tmp_path)
    assert result.ok is False
    assert any('broken demo_patient_key' in error for error in result.errors)
