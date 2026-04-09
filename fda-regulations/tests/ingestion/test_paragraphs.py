"""Unit tests for paragraph extraction from letter HTML."""

from fda_regulations.chunking.paragraphs import extract_paragraph_texts


def test_extract_from_article_main_content() -> None:
    html = """
    <html><body><article id="main-content">
    <p>First line.</p>
    <p>Second line.</p>
    </article></body></html>
    """
    assert extract_paragraph_texts(html) == ["First line.", "Second line."]


def test_extract_falls_back_to_id_main_content_div() -> None:
    html = """
    <html><body><div id="main-content">
    <p>Only region.</p>
    </div></body></html>
    """
    assert extract_paragraph_texts(html) == ["Only region."]


def test_extract_prefers_article_main_content_over_div_with_same_id() -> None:
    html = """
    <html><body>
    <div id="main-content"><p>Div paragraph.</p></div>
    <article id="main-content"><p>Article paragraph.</p></article>
    </body></html>
    """
    # Implementation tries article#main-content before #main-content
    out = extract_paragraph_texts(html)
    assert out == ["Article paragraph."]


def test_extract_strips_script_and_style() -> None:
    html = """
    <article id="main-content">
    <script>alert(1)</script>
    <style>.x{}</style>
    <p>Visible text.</p>
    </article>
    """
    paras = extract_paragraph_texts(html)
    assert paras == ["Visible text."]
    assert "alert" not in paras[0]


def test_extract_skips_empty_paragraphs() -> None:
    html = """
    <article id="main-content">
    <p>Real.</p>
    <p>   </p>
    <p></p>
    <p>Also real.</p>
    </article>
    """
    assert extract_paragraph_texts(html) == ["Real.", "Also real."]


def test_extract_returns_empty_when_no_main_region() -> None:
    assert extract_paragraph_texts("<html><body><p>Orphan</p></body></html>") == []
