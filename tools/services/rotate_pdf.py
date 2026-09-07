from pypdf import PdfWriter

from ..uploads import ToolError, new_media_path, read_pdf

VALID_ANGLES = (90, 180, 270)


def rotate_pdf(file, angle, pages=None):
    """Rotate pages clockwise by `angle` degrees.

    `pages` is an optional list of 1-based page numbers; None rotates everything.
    Rotation is relative, so it stacks on any rotation the page already carries.
    """
    try:
        angle = int(angle)
    except (TypeError, ValueError):
        raise ToolError("Please choose a rotation angle.") from None

    if angle not in VALID_ANGLES:
        raise ToolError("Rotation must be 90, 180 or 270 degrees.")

    reader = read_pdf(file, file.name)
    targets = set(pages) if pages else None

    writer = PdfWriter()
    for number, page in enumerate(reader.pages, start=1):
        if targets is None or number in targets:
            page.rotate(angle)
        writer.add_page(page)

    filename, output_path = new_media_path("_rotated.pdf")
    with open(output_path, "wb") as out:
        writer.write(out)

    return filename
