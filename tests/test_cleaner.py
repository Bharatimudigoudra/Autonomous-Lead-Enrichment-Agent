from src.cleaner import build_llm_context, clean_html


def test_clean_html_strips_chrome_and_scripts(sample_pages):
    text = clean_html(sample_pages["https://exampleco.com/"])
    assert "ExampleCo builds payment APIs" in text
    assert "tracker()" not in text  # scripts removed
    assert "menu links" not in text  # nav removed
    assert "copyright" not in text  # footer removed


def test_build_llm_context_labels_sources(sample_pages):
    context = build_llm_context(sample_pages)
    assert "SOURCE URL: https://exampleco.com/" in context


def test_build_llm_context_enforces_budget(sample_pages):
    context = build_llm_context(sample_pages, max_chars=50)
    assert len(context) <= 50
