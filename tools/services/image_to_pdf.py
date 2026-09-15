from PIL import Image, ImageOps

from ..uploads import ToolError, new_media_path

# The old version rendered every page at 72 DPI (595 px wide), which threw away
# most of the detail in a phone photo or a scan. 150 DPI is ~4x the pixels and
# still prints cleanly.
RENDER_DPI = 150
A4_PORTRAIT = (int(8.27 * RENDER_DPI), int(11.69 * RENDER_DPI))   # 1240 x 1753
A4_LANDSCAPE = (A4_PORTRAIT[1], A4_PORTRAIT[0])

PAGE_SIZES = ("a4", "fit")

# Pillow's default only *warns* between 89M and 178M pixels and decodes anyway,
# which is ~500MB of RSS on a container with 512MB. A crafted PNG a few hundred
# KB on the wire can do that, so cap it low enough to survive and let the
# resulting DecompressionBombError fall through to the "corrupt image" message.
Image.MAX_IMAGE_PIXELS = 50_000_000


def _flatten(img):
    """Convert to RGB, compositing any transparency onto white.

    A plain .convert('RGB') turns transparent PNG pixels black.
    """
    img = ImageOps.exif_transpose(img)          # honour phone-camera rotation
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        canvas = Image.new("RGB", rgba.size, (255, 255, 255))
        canvas.paste(rgba, mask=rgba.split()[-1])
        return canvas
    return img.convert("RGB")


def _to_page(img, page_size):
    if page_size == "fit":
        # Page matches the image exactly - no white bars. Scaled down only if
        # it would otherwise exceed A4 at RENDER_DPI.
        img.thumbnail(A4_LANDSCAPE if img.width > img.height else A4_PORTRAIT, Image.LANCZOS)
        return img

    # A4, auto-oriented so a landscape photo gets a landscape page.
    target = A4_LANDSCAPE if img.width > img.height else A4_PORTRAIT
    img.thumbnail(target, Image.LANCZOS)
    canvas = Image.new("RGB", target, (255, 255, 255))
    canvas.paste(img, ((target[0] - img.width) // 2, (target[1] - img.height) // 2))
    return canvas


def img_to_pdf(files, page_size="a4"):
    """Combine images into one PDF, in the order given."""
    if page_size not in PAGE_SIZES:
        page_size = "a4"

    pages = []
    for upload in files:
        upload.seek(0)
        try:
            with Image.open(upload) as img:
                img.load()
                pages.append(_to_page(_flatten(img), page_size))
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(
                f"'{upload.name}' could not be read as an image. It may be corrupt."
            ) from exc

    if not pages:
        raise ToolError("No images to convert.")

    filename, output_path = new_media_path("_images.pdf")
    # Pillow writes multi-page PDFs directly; resolution sets the page size in
    # points, so RENDER_DPI pixels map back to a correctly sized page.
    pages[0].save(
        output_path,
        "PDF",
        resolution=RENDER_DPI,
        save_all=True,
        append_images=pages[1:],
    )

    return filename
