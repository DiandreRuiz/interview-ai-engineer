"""Main-text extraction from FDA letter HTML."""

from fda_regulations.ingest.scrape import extract_warning_letter_main_text


def test_extract_main_text_from_article_main_content() -> None:
    html = """
    <html><body>
    <div class="noise">Nav noise</div>
    <article id="main-content" class="article main-content">
      <p>WARNING LETTER</p>
      <p>Ms. Reader:</p>
      <p>Body paragraph.</p>
    </article>
    </body></html>
    """
    text = extract_warning_letter_main_text(html)
    assert "WARNING LETTER" in text
    assert "Body paragraph" in text
    assert "Nav noise" not in text


def test_extract_returns_empty_when_no_main_region() -> None:
    assert extract_warning_letter_main_text("<html><body><p>Only this</p></body></html>") == ""
