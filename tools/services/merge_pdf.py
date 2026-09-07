from pypdf import PdfWriter

from ..uploads import ToolError, new_media_path, read_pdf


def merge_pdfs(files):
    """Concatenate PDFs in the order given. Returns the output filename."""
    if len(files) < 2:
        raise ToolError("Please upload at least two PDFs to merge.")

    writer = PdfWriter()
    for upload in files:
        reader = read_pdf(upload, upload.name)
        for page in reader.pages:
            writer.add_page(page)

    filename, output_path = new_media_path("_merged.pdf")
    with open(output_path, "wb") as out:
        writer.write(out)

    return filename
