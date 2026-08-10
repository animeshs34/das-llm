import pytest
from pathlib import Path
from das_llm.docgen import AutoDocGenerator

def test_autodoc_generator_compiles_all_files(tmp_path):
    generator = AutoDocGenerator(repo_root=tmp_path)
    generated = generator.generate_all()

    assert "architecture" in generated
    assert "invariants" in generated
    assert "api" in generated
    assert "portal" in generated

    for name, filepath in generated.items():
        assert filepath.exists(), f"Doc file {filepath} was not generated!"
        assert filepath.stat().st_size > 50, f"Doc file {filepath} is empty!"

    # Verify interactive HTML portal content
    html_content = generated["portal"].read_text(encoding="utf-8")
    assert "DAS-LLM Live Documentation & Policy Portal" in html_content
    assert "PrivacyGuard Zero-Leakage Sanitizer" in html_content
