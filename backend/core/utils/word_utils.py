from docx import Document
from io import BytesIO
import base64


def create_word_with_template(content: str, title: str, letterhead_base64: str = None):
    """Create a Word document from content and title.

    If `letterhead_base64` is provided and represents a valid .docx file (base64,
    optionally prefixed with `data:`), the function will open that template and
    append the generated content into it so the template's layout/header/footer
    are preserved.

    Returns a BytesIO buffer containing the generated .docx.
    """
    try:
        if letterhead_base64:
            lb = letterhead_base64
            if lb.startswith('data:'):
                lb = lb.split(',', 1)[1]
            template_bytes = base64.b64decode(lb)
            template_buf = BytesIO(template_bytes)
            try:
                doc = Document(template_buf)
            except Exception:
                # fallback to new document if template cannot be opened
                doc = Document()
        else:
            doc = Document()

        if title:
            try:
                doc.add_heading(title, level=1)
            except Exception:
                # Some templates may not include the standard 'Heading 1' style
                # (localized templates or minimal templates). Fall back to
                # inserting a bold paragraph instead of relying on styles.
                p = doc.add_paragraph()
                run = p.add_run(title)
                run.bold = True

        for paragraph in str(content or '').split('\n\n'):
            for line in paragraph.split('\n'):
                text = line.strip()
                if text:
                    doc.add_paragraph(text)
            doc.add_paragraph('')

        buf = BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf
    except Exception as exc:
        raise RuntimeError(f'Word generation failed: {exc}')
