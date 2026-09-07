from pypdf import PdfWriter

from ..uploads import ToolError, new_media_path, read_pdf


def parse_page_selection(spec, total):
    """Turn '1-3, 7, 9-' into a list of 1-based page numbers.

    Accepts single pages, closed ranges, open-ended ranges ('9-' means 9 to the
    end) and the word 'all'. Order is preserved and duplicates are dropped, so
    '3,1,3' extracts page 3 then page 1.
    """
    spec = (spec or "").strip()
    if not spec:
        raise ToolError("Please enter which pages to extract, for example 1-3, 7.")

    if spec.lower() == "all":
        return list(range(1, total + 1))

    pages = []
    for part in spec.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            start_text, _, end_text = part.partition("-")
            start = _page_number(start_text, total, part)
            end = total if end_text == "" else _page_number(end_text, total, part)
            if start > end:
                raise ToolError(f"'{part}' is backwards - the start page must come first.")
            pages.extend(range(start, end + 1))
        else:
            pages.append(_page_number(part, total, part))

    if not pages:
        raise ToolError("Please enter which pages to extract, for example 1-3, 7.")

    return list(dict.fromkeys(pages))


def _page_number(text, total, context):
    if not text.isdigit():
        raise ToolError(f"'{context}' is not a valid page selection. Use numbers like 1-3, 7.")
    number = int(text)
    if number < 1 or number > total:
        raise ToolError(f"Page {number} does not exist - this PDF has {total} pages.")
    return number


def extract_pages(file, selection):
    """Extract `selection` (a page-range string) into a new PDF."""
    reader = read_pdf(file, file.name)
    pages = parse_page_selection(selection, len(reader.pages))

    writer = PdfWriter()
    for number in pages:
        writer.add_page(reader.pages[number - 1])

    filename, output_path = new_media_path("_extracted.pdf")
    with open(output_path, "wb") as out:
        writer.write(out)

    return filename
