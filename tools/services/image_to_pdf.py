from PIL import Image
from pypdf import PdfWriter, PdfReader
import io
import os
import uuid
from django.conf import settings

# A4 at 72 DPI: 595 × 842 px → 595 × 842 pt PDF page
A4_W, A4_H = 595, 842


def _fit_to_a4(img: Image.Image) -> Image.Image:
    """Return img letterboxed onto a white A4 canvas (595×842 px, 72 DPI)."""
    img = img.convert("RGB")
    img.thumbnail((A4_W, A4_H), Image.LANCZOS)
    canvas = Image.new("RGB", (A4_W, A4_H), (255, 255, 255))
    x = (A4_W - img.width) // 2
    y = (A4_H - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def img_to_pdf(files):
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    writer = PdfWriter()

    for file in files:
        img = Image.open(file)
        # ponytail: letterbox onto fixed A4 canvas so every page is uniform 595×842 pt.
        # resolution=72 tells PIL to set PDF media box to exactly canvas pixel size in pts.
        canvas = _fit_to_a4(img)
        buf = io.BytesIO()
        canvas.save(buf, format="PDF", resolution=72)
        buf.seek(0)
        reader = PdfReader(buf)
        writer.add_page(reader.pages[0])

    filename = f"{uuid.uuid4()}_images.pdf"
    output_path = os.path.join(settings.MEDIA_ROOT, filename)

    with open(output_path, "wb") as f:
        writer.write(f)

    return filename
