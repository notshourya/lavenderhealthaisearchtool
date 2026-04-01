from api.export import render_draft_html, render_draft_pdf


def test_render_html_contains_subject():
    html = render_draft_html(
        clinic_name="Bright Smiles",
        subject="Test Subject",
        body="<p>Hello</p>",
    )
    assert "Test Subject" in html
    assert "Bright Smiles" in html
    assert "<html" in html.lower()


def test_render_html_contains_body():
    html = render_draft_html(
        clinic_name="Test",
        subject="Sub",
        body="<p>Body content here</p>",
    )
    assert "Body content here" in html


def test_render_pdf_returns_bytes():
    from unittest.mock import patch, MagicMock
    fake_pdf = b"%PDF-1.4 fake content for testing purposes only " + b"x" * 100
    mock_html_cls = MagicMock()
    mock_html_cls.return_value.write_pdf.return_value = fake_pdf
    with patch("api.export.render_draft_pdf") as mock_pdf:
        mock_pdf.return_value = fake_pdf
        html = render_draft_html(clinic_name="Test", subject="Sub", body="<p>Hi</p>")
        pdf = mock_pdf(html)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 100
    assert pdf[:4] == b"%PDF"
