import zipfile

import pymupdf

from ..uploads import ToolError, new_media_path, safe_stem

# Rendered with PyMuPDF instead of pdf2image/poppler: no subprocess, no
# system package, and pages stream one at a time instead of the whole
# document being held in memory as bitmaps.
DPI_CHOICES = (72, 150, 300)
FORMATS = ("png", "jpg")
MAX_PAGES = 300


def pdf_to_images(files, dpi=150, image_format="png"):
    """Render every page of every PDF to an image, returned as one zip."""
    dpi = dpi if dpi in DPI_CHOICES else 150
    image_format = image_format if image_format in FORMATS else "png"

    filename, zip_path = new_media_path("_images.zip")
    used_stems = {}
    rendered = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for upload in files:
            upload.seek(0)
            try:
                document = pymupdf.open(stream=upload.read(), filetype="pdf")
            except Exception as exc:
                raise ToolError(
                    f"'{upload.name}' could not be read. It may be corrupt or not a real PDF."
                ) from exc

            with document:
                if document.needs_pass:
                    raise ToolError(
                        f"'{upload.name}' is password-protected. Unlock it first."
                    )

                rendered += document.page_count
                if rendered > MAX_PAGES:
                    raise ToolError(
                        f"That is more than {MAX_PAGES} pages in one go. "
                        "Please split the work into smaller batches."
                    )

                # Two uploads called report.pdf must not overwrite each other
                # inside the archive.
                stem = safe_stem(upload.name, "document")
                used_stems[stem] = used_stems.get(stem, 0) + 1
                if used_stems[stem] > 1:
                    stem = f"{stem}_{used_stems[stem]}"

                width = len(str(document.page_count))
                for index, page in enumerate(document, start=1):
                    pixmap = page.get_pixmap(dpi=dpi)
                    data = (
                        pixmap.tobytes("jpg", jpg_quality=88)
                        if image_format == "jpg"
                        else pixmap.tobytes("png")
                    )
                    archive.writestr(
                        f"{stem}_page_{index:0{width}d}.{image_format}", data
                    )

    if rendered == 0:
        raise ToolError("Those PDFs contain no pages.")

    return filename
