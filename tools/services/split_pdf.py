import io
import zipfile

from pypdf import PdfWriter

from ..uploads import ToolError, new_media_path, read_pdf, safe_stem


def split_pdf(file):
    """Split every page into its own PDF, returned as a zip.

    Pages are built in memory and written straight into the archive. The old
    version wrote each page to media/page_N.pdf first, so two concurrent
    requests overwrote each other's temp files.
    """
    reader = read_pdf(file, file.name)
    total = len(reader.pages)
    if total < 2:
        raise ToolError("This PDF has only one page, so there is nothing to split.")

    stem = safe_stem(file.name, "page")
    width = len(str(total))  # zero-pad so the pages sort correctly in a file browser

    filename, zip_path = new_media_path("_split.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for index, page in enumerate(reader.pages, start=1):
            writer = PdfWriter()
            writer.add_page(page)
            buffer = io.BytesIO()
            writer.write(buffer)
            archive.writestr(f"{stem}_page_{index:0{width}d}.pdf", buffer.getvalue())

    return filename
