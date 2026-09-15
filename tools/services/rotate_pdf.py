from pypdf import PdfWriter

from ..uploads import ToolError, new_media_path, read_pdf

VALID_ANGLES = (90, 180, 270)


def rotate_pdf(file, angle):
    """Rotate every page clockwise by `angle` degrees.

    Rotation is relative, so it stacks on any rotation the page already carries.
    """
    try:
        angle = int(angle)
    except (TypeError, ValueError):
        raise ToolError("Please choose a rotation angle.") from None

    if angle not in VALID_ANGLES:
        raise ToolError("Rotation must be 90, 180 or 270 degrees.")

    reader = read_pdf(file, file.name)

    writer = PdfWriter()
    for page in reader.pages:
        page.rotate(angle)
        writer.add_page(page)

    filename, output_path = new_media_path("_rotated.pdf")
    with open(output_path, "wb") as out:
        writer.write(out)

    return filename
