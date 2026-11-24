"""
Lectura local de archivos en CPU (sin GPU ni servicios externos).

  extract_text(path, mime) → {"text", "method", "pages"}

  PDF con texto  → pypdf (sin OCR)
  PDF escaneado  → pypdfium2 renderiza las páginas → OCR
  Imagen         → OCR con Tesseract (español + inglés)
  Word (.docx)   → python-docx
  Excel (.xlsx)  → openpyxl
  Texto plano    → lectura directa
"""
import os

MAX_CHARS = 20000
MAX_PAGES = int(os.getenv('OCR_MAX_PAGES', '5'))
OCR_LANG = os.getenv('OCR_LANG', 'spa+eng')
MAX_PIXELS = 40_000_000  # evita imágenes gigantes (bombas de descompresión)


def _clean(text):
    lines = [' '.join(line.split()) for line in (text or '').splitlines()]
    return '\n'.join(line for line in lines if line).strip()[:MAX_CHARS]


def _ocr_image(img):
    import pytesseract
    from PIL import ImageOps
    img = ImageOps.exif_transpose(img).convert('L')
    # Las fotos de WhatsApp vienen comprimidas: ampliar las pequeñas mejora mucho el OCR
    if max(img.size) < 1600:
        factor = 1600 / max(img.size)
        img = img.resize((int(img.width * factor), int(img.height * factor)))
    return pytesseract.image_to_string(img, lang=OCR_LANG, config='--oem 1 --psm 3')


def _image(path):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    with Image.open(path) as img:
        return {'text': _clean(_ocr_image(img)), 'method': 'ocr', 'pages': 1}


def _pdf(path):
    from pypdf import PdfReader
    reader = PdfReader(path)
    pages = reader.pages[:MAX_PAGES]
    text = '\n'.join((p.extract_text() or '') for p in pages)
    if len(text.strip()) >= 30 * max(1, len(pages)) // 2:
        return {'text': _clean(text), 'method': 'pdf_text', 'pages': len(pages)}
    # Escaneado: renderizar y pasar OCR
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(path)
    out = []
    for i in range(min(len(pdf), MAX_PAGES)):
        img = pdf[i].render(scale=2).to_pil()
        out.append(_ocr_image(img))
    return {'text': _clean('\n'.join(out)), 'method': 'ocr', 'pages': min(len(pdf), MAX_PAGES)}


def _docx(path):
    import docx
    d = docx.Document(path)
    parts = [p.text for p in d.paragraphs]
    for table in d.tables:
        for row in table.rows:
            parts.append(' | '.join(c.text for c in row.cells))
    return {'text': _clean('\n'.join(parts)), 'method': 'docx', 'pages': 1}


def _xlsx(path):
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    parts = []
    for ws in wb.worksheets[:3]:
        for row in ws.iter_rows(max_row=200, values_only=True):
            cells = [str(c) for c in row if c not in (None, '')]
            if cells:
                parts.append(' | '.join(cells))
    return {'text': _clean('\n'.join(parts)), 'method': 'xlsx', 'pages': len(wb.worksheets)}


def extract_text(path, mime=''):
    ext = os.path.splitext(path)[1].lower()
    mime = (mime or '').lower()
    if mime.startswith('image/') or ext in ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff', '.gif'):
        return _image(path)
    if mime == 'application/pdf' or ext == '.pdf':
        return _pdf(path)
    if 'wordprocessingml' in mime or ext == '.docx':
        return _docx(path)
    if 'spreadsheetml' in mime or ext == '.xlsx':
        return _xlsx(path)
    if mime.startswith('text/') or ext in ('.txt', '.csv'):
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            return {'text': _clean(fh.read(MAX_CHARS)), 'method': 'text', 'pages': 1}
    raise ValueError(f'Tipo de archivo no soportado: {mime or ext}')
