import pytest

from src.extractor import extract_lead


def test_missing_api_key_fails_loudly(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        extract_lead("example.com", "some cleaned text", [])
