from pypdf import PdfWriter

from ..uploads import ToolError, new_media_path, read_pdf


def parse_order(order, total):
    """Validate a '3,1,2' page order against a `total`-page document."""
    parts = [part.strip() for part in (order or "").split(",") if part.strip()]
    if not parts:
        raise ToolError("Upload a PDF and wait for the page previews before submitting.")

    pages = []
    for part in parts:
        if not part.isdigit():
            raise ToolError(f"'{part}' is not a page number.")
        pages.append(int(part))

    if len(pages) != total or sorted(pages) != list(range(1, total + 1)):
        raise ToolError(
            f"The new order must list each of the {total} pages exactly once. "
            "Reload the page and try again."
        )

    return pages


def reorder_pdf(file, order):
    """Rewrite a PDF with its pages in the sequence given by `order`."""
    reader = read_pdf(file, file.name)
    pages = parse_order(order, len(reader.pages))

    writer = PdfWriter()
    for number in pages:
        writer.add_page(reader.pages[number - 1])

    filename, output_path = new_media_path("_reordered.pdf")
    with open(output_path, "wb") as out:
        writer.write(out)

    return filename
