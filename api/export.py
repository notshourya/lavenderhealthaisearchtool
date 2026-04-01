_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Open Sans', Arial, sans-serif; max-width: 600px; margin: 40px auto; color: #1a1a2e; }}
  h1 {{ color: #4d65ff; font-size: 18px; margin-bottom: 4px; }}
  .meta {{ color: #888; font-size: 13px; margin-bottom: 24px; }}
  .subject {{ font-weight: 600; font-size: 16px; margin-bottom: 16px; }}
  .body {{ line-height: 1.7; }}
</style>
</head>
<body>
  <h1>{clinic_name}</h1>
  <div class="subject">Subject: {subject}</div>
  <div class="body">{body}</div>
</body>
</html>"""


def render_draft_html(clinic_name: str, subject: str, body: str) -> str:
    return _HTML_TEMPLATE.format(
        clinic_name=clinic_name,
        subject=subject,
        body=body,
    )


def render_draft_pdf(html: str) -> bytes:
    from weasyprint import HTML
    return HTML(string=html).write_pdf()
