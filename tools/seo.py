"""Per-page SEO copy: title, meta description, H1, FAQ and related links.

One entry per page instead of the same four generic questions and one title
block repeated across seventeen templates. Search engines need each page to
look different from every other one, and this file is where that difference
lives.

`views` puts the matching entry into the template context as `seo`, and
`base.html` renders the title, meta description, Open Graph tags and the
JSON-LD from it.
"""

# label: short name used when a tool is listed under "Related tools".
PAGES = {
    "home": {
        "label": "All PDF tools",
        "title": "Free Online PDF Tools - Merge, Split, Compress, Convert | tryPDF!",
        "description": (
            "13 free online PDF tools: merge, split, compress, rotate, protect and convert "
            "PDF to Word or image. No signup, no watermark, files deleted after download."
        ),
        "h1": "Free Online PDF Tools",
        "faq": [
            ("Is tryPDF! really free?",
             "Yes. Every tool is free, with no account, no signup and no watermark on the result."),
            ("Do I need to install anything?",
             "No. tryPDF! runs in your browser on desktop, tablet and mobile - there is nothing to download or install."),
            ("What happens to my files?",
             "Uploads are deleted straight after processing and the result is deleted as it downloads. Nothing is kept or shared."),
            ("Is there a file size limit?",
             "Yes, a per-file upload limit is shown on each tool page. Split a very large PDF first if you hit it."),
        ],
        "related": [],
    },

    "merge_pdf": {
        "label": "Merge PDF",
        "title": "Merge PDF Online Free - Combine PDF Files | tryPDF!",
        "description": (
            "Combine two or more PDF files into one document online for free. Drag the files "
            "into the order you want and download the merged PDF instantly. No signup."
        ),
        "h1": "Merge PDF",
        "faq": [
            ("How do I merge two PDF files into one?",
             "Upload the PDFs, drag the cards to set the order they should be joined in, then press Merge and download the combined file."),
            ("How many PDFs can I merge at once?",
             "You can merge several PDFs in one go, up to the file count and size limit shown on the upload box."),
            ("Will merging change the quality of my PDF?",
             "No. Pages are copied across as they are, so text stays selectable and images keep their original resolution."),
            ("Can I change the order of the files before merging?",
             "Yes. Each uploaded file appears as a card - drag the cards around and the PDFs are joined in that order."),
        ],
        "related": ["split_pdf", "reorder_pdf", "extract_pages", "compress_pdf"],
    },

    "split_pdf": {
        "label": "Split PDF",
        "title": "Split PDF Online Free - Separate PDF Into Pages | tryPDF!",
        "description": (
            "Split a PDF into separate one-page files and download them all in a single zip. "
            "Free, fast and secure - no signup, and nothing is stored on our servers."
        ),
        "h1": "Split PDF",
        "faq": [
            ("How do I split a PDF into separate pages?",
             "Upload the PDF and press Split. Every page becomes its own PDF file, and they are returned together in one zip archive."),
            ("What do I get back after splitting?",
             "A zip file containing one PDF per page, named after your original file so the order is easy to follow."),
            ("Can I split only some pages instead of all of them?",
             "Yes - use the Extract Pages tool if you only want a range such as 1-3, or a handful of specific pages."),
            ("Does splitting a PDF reduce its quality?",
             "No. Each page is copied out untouched, so text, fonts and images are identical to the original."),
        ],
        "related": ["extract_pages", "merge_pdf", "reorder_pdf", "pdf_to_image"],
    },

    "compress_pdf": {
        "label": "Compress PDF",
        "title": "Compress PDF Online Free - Reduce PDF File Size | tryPDF!",
        "description": (
            "Reduce PDF file size online without losing readable quality. Pick a compression "
            "level, shrink large PDFs for email or upload, and download instantly. Free."
        ),
        "h1": "Compress PDF",
        "faq": [
            ("How much smaller will my PDF get?",
             "It depends on the file. Scanned or image-heavy PDFs often drop by 50-90%, while a PDF that is mostly text is already small and shrinks less."),
            ("Will compressing reduce the quality of my PDF?",
             "Images are re-encoded, so the stronger levels trade some sharpness for size. Start with the balanced level and go further only if you need to."),
            ("How do I compress a PDF for email?",
             "Upload it, choose a compression level and download the result. Most mail providers cap attachments at 20-25MB, which the balanced level usually clears."),
            ("Is there a limit on the PDF size I can upload?",
             "Yes - the per-file limit is shown on the upload box above."),
        ],
        "related": ["compress_100kb", "split_pdf", "pdf_to_image", "merge_pdf"],
    },

    "compress_100kb": {
        "label": "Compress PDF to 100KB",
        "title": "Compress PDF to 100KB Online Free - Shrink to a Size | tryPDF!",
        "description": (
            "Compress a PDF to 100KB, 200KB or 500KB for exam, visa and job application "
            "upload limits. Free online tool that hits a strict size cap and stays readable."
        ),
        "h1": "Compress PDF to a Target Size",
        "faq": [
            ("How do I compress a PDF to under 100KB?",
             "Upload the PDF, pick 100KB as the target and download the result. The tool lowers image quality step by step until the file fits."),
            ("Why would I need a PDF under 100KB?",
             "Government forms, exam registrations, visa portals and job applications often refuse anything larger, which is exactly what this tool is for."),
            ("What if my PDF cannot reach the target size?",
             "Very long or heavily scanned documents may stop above the target. Try 200KB or 500KB, or split the PDF and upload only the part you need."),
            ("Will the text still be readable at 100KB?",
             "Text stays sharp because it is not stored as an image. Photos and scans lose detail, which is the trade-off for hitting a hard size cap."),
        ],
        "related": ["compress_pdf", "split_pdf", "extract_pages", "image_to_pdf"],
    },

    "extract_pages": {
        "label": "Extract Pages",
        "title": "Extract Pages from PDF Online Free - Get a Page Range | tryPDF!",
        "description": (
            "Pull selected pages out of a PDF into a new document. Enter a range like 1-3, 7 "
            "and download just the pages you need. Free, no signup, nothing stored."
        ),
        "h1": "Extract Pages from PDF",
        "faq": [
            ("How do I extract certain pages from a PDF?",
             "Upload the PDF and type the pages you want, for example 1-3, 7, 10-12. The tool builds a new PDF containing only those pages."),
            ("How do I write a page range?",
             "Use a hyphen for a range and commas between entries: 1-3, 7, 10-12. Spaces are ignored."),
            ("Does the original PDF change?",
             "No. Your upload is never modified - a new PDF is created with the pages you asked for, and the upload is deleted afterwards."),
            ("What is the difference between extracting and splitting?",
             "Extracting gives you one PDF containing the pages you chose. Splitting gives you every page as its own separate file in a zip."),
        ],
        "related": ["split_pdf", "merge_pdf", "reorder_pdf", "rotate_pdf"],
    },

    "image_to_pdf": {
        "label": "Image to PDF",
        "title": "Image to PDF Converter Free - JPG and PNG to PDF | tryPDF!",
        "description": (
            "Convert JPG, PNG or WebP images into a single PDF online for free. Pick the page "
            "size, combine photos and scans into one document, and download instantly."
        ),
        "h1": "Convert Image to PDF",
        "faq": [
            ("How do I turn multiple photos into one PDF?",
             "Upload all the images at once, choose a page size and press convert. They are placed in order, one image per page, in a single PDF."),
            ("Which image formats are supported?",
             "JPG, JPEG, PNG and WebP."),
            ("Can I choose the page size?",
             "Yes. Pick a standard printable page size, or let the page fit each image."),
            ("Is this good for scanned documents?",
             "Yes. Photograph or scan each page, upload them in order, and you get one PDF ready to email or upload."),
        ],
        "related": ["pdf_to_image", "compress_pdf", "merge_pdf", "docx_to_pdf"],
    },

    "pdf_to_image": {
        "label": "PDF to Image",
        "title": "PDF to Image Online Free - Convert PDF to PNG or JPG | tryPDF!",
        "description": (
            "Convert every page of a PDF into PNG or JPG images at the resolution you choose, "
            "and download them all in one zip. Free online PDF to image converter."
        ),
        "h1": "Convert PDF to Image",
        "faq": [
            ("How do I convert a PDF page to an image?",
             "Upload the PDF, choose PNG or JPG and a DPI, then download the zip containing one image per page."),
            ("Which DPI should I pick?",
             "150 DPI is fine for screens and email. Choose a higher DPI for printing, or when you need to zoom into fine detail."),
            ("PNG or JPG - which is better?",
             "PNG keeps text and line art crisp and is the safer default. JPG produces smaller files and suits photo-heavy pages."),
            ("Can I convert just one page?",
             "Extract the page you want first with the Extract Pages tool, then convert that single-page PDF to an image."),
        ],
        "related": ["image_to_pdf", "extract_pages", "compress_pdf", "pdf_to_docx"],
    },

    "pdf_to_docx": {
        "label": "PDF to Word",
        "title": "PDF to Word Converter Free - Convert PDF to DOCX | tryPDF!",
        "description": (
            "Convert a PDF into an editable Word DOCX file online for free, keeping the layout "
            "as close to the original as possible. No signup and no watermark."
        ),
        "h1": "Convert PDF to Word",
        "faq": [
            ("How do I convert a PDF to an editable Word file?",
             "Upload the PDF and press convert. You get a DOCX file you can open and edit in Word, Google Docs or LibreOffice."),
            ("Will the layout stay the same?",
             "The converter reproduces text, spacing and tables as closely as it can. Complex multi-column designs may still need a tidy-up in Word."),
            ("Can it convert a scanned PDF?",
             "A scan is a picture of text, so those pages come through as images rather than editable words. You need OCR software for that."),
            ("Is the converted file free of watermarks?",
             "Yes. The DOCX you download contains only your own content."),
        ],
        "related": ["docx_to_pdf", "pdf_to_image", "extract_pages", "compress_pdf"],
    },

    "docx_to_pdf": {
        "label": "Word to PDF",
        "title": "Word to PDF Converter Free - Convert DOCX to PDF | tryPDF!",
        "description": (
            "Convert Word DOC and DOCX files to PDF online for free. Fonts, layout and page "
            "breaks are preserved, so the PDF looks exactly like your document."
        ),
        "h1": "Convert Word to PDF",
        "faq": [
            ("How do I convert a Word document to PDF?",
             "Upload the DOC or DOCX file and press convert. The PDF downloads straight away."),
            ("Will my formatting and fonts be kept?",
             "Yes. Headings, tables, images and page breaks are rendered as they appear in Word."),
            ("Why convert to PDF at all?",
             "A PDF looks the same on every device and cannot be edited by accident, which is why applications and print shops usually ask for one."),
            ("Does it work with old .doc files?",
             "Yes, both .doc and .docx are accepted."),
        ],
        "related": ["pdf_to_docx", "merge_pdf", "compress_pdf", "protect_pdf"],
    },

    "rotate_pdf": {
        "label": "Rotate PDF",
        "title": "Rotate PDF Online Free - Fix Sideways PDF Pages | tryPDF!",
        "description": (
            "Rotate PDF pages 90, 180 or 270 degrees and save the change permanently. Fix "
            "sideways scans and upside-down pages online for free."
        ),
        "h1": "Rotate PDF",
        "faq": [
            ("How do I permanently rotate a PDF?",
             "Upload the PDF, choose 90, 180 or 270 degrees and download the result. The new orientation is saved into the file, not just into your viewer."),
            ("Why does my PDF look sideways only in some apps?",
             "Rotating inside a PDF reader is often just a view setting that is never saved. Rotating here writes the change into the file itself."),
            ("Which way is 90 degrees?",
             "90 turns the pages clockwise and 270 turns them counter-clockwise."),
            ("Does rotating affect the text or the quality?",
             "No. Only the page orientation changes - the content is untouched."),
        ],
        "related": ["reorder_pdf", "extract_pages", "merge_pdf", "pdf_to_image"],
    },

    "protect_pdf": {
        "label": "Protect PDF",
        "title": "Password Protect a PDF Online Free - AES-256 | tryPDF!",
        "description": (
            "Add a password to a PDF with AES-256 encryption so only people who know it can "
            "open the file. Free online PDF protection, with nothing stored on our servers."
        ),
        "h1": "Password Protect PDF",
        "faq": [
            ("How do I put a password on a PDF?",
             "Upload the PDF, type the password twice so a typo cannot lock you out, and download the encrypted file."),
            ("How strong is the encryption?",
             "The file is encrypted with AES-256, the standard modern PDF readers use. It is only as safe as the password you pick."),
            ("What happens if I forget the password?",
             "Nobody can recover it, including us - we never see or store your password. Keep a copy of the original file somewhere safe."),
            ("Do you keep a copy of my password or file?",
             "No. The password is used once during processing, and both the upload and the result are deleted straight afterwards."),
        ],
        "related": ["unlock_pdf", "compress_pdf", "merge_pdf", "docx_to_pdf"],
    },

    "unlock_pdf": {
        "label": "Unlock PDF",
        "title": "Unlock PDF Online Free - Remove a PDF Password | tryPDF!",
        "description": (
            "Remove the password from a PDF you own by entering it once, then download an "
            "unlocked copy you can open and print freely. Free, and nothing is stored."
        ),
        "h1": "Unlock PDF",
        "faq": [
            ("How do I remove a password from a PDF?",
             "Upload the protected PDF, enter its current password, and download the unlocked copy."),
            ("Can I unlock a PDF without knowing the password?",
             "No. This tool decrypts a file you can already open - it does not crack or guess passwords."),
            ("Is the original file changed?",
             "No. You get a new, unlocked copy, and your upload is deleted after processing."),
            ("Why unlock a PDF at all?",
             "So you stop retyping the password every time, and so the file can be merged, compressed or printed by tools that cannot open encrypted PDFs."),
        ],
        "related": ["protect_pdf", "merge_pdf", "compress_pdf", "pdf_to_docx"],
    },

    "reorder_pdf": {
        "label": "Reorder Pages",
        "title": "Reorder PDF Pages Online Free - Rearrange a PDF | tryPDF!",
        "description": (
            "Drag PDF pages into any order and download the rearranged document. Free online "
            "page organizer with a visual preview of every page. No signup."
        ),
        "h1": "Reorder PDF Pages",
        "faq": [
            ("How do I change the page order in a PDF?",
             "Upload the PDF to see a thumbnail of each page, drag them into the order you want, and download the rearranged file."),
            ("Can I move a page to the front?",
             "Yes. Drag its thumbnail to the first position - any page can go anywhere."),
            ("Can I delete pages here too?",
             "Use Extract Pages to keep only the pages you want. This tool changes the order rather than removing pages."),
            ("Does reordering change the page content?",
             "No. The pages are copied into a new sequence exactly as they were."),
        ],
        "related": ["extract_pages", "merge_pdf", "rotate_pdf", "split_pdf"],
    },

    "about": {
        "label": "About",
        "title": "About tryPDF! - Free Online PDF Tools",
        "description": (
            "What tryPDF! is, why it is free, and how the PDF tools handle your files: "
            "processed on the server and deleted as soon as your download starts."
        ),
        "h1": "About tryPDF!",
        "faq": [],
        "related": [],
    },

    "privacy": {
        "label": "Privacy Policy",
        "title": "Privacy Policy - tryPDF!",
        "description": (
            "How tryPDF! handles the files you upload: processed on the server, deleted as "
            "soon as your download starts, never stored permanently or shared."
        ),
        "h1": "Privacy Policy",
        "faq": [],
        "related": [],
    },

    "terms": {
        "label": "Terms of Service",
        "title": "Terms of Service - tryPDF!",
        "description": "The terms you agree to when using the free tryPDF! online PDF tools.",
        "h1": "Terms of Service",
        "faq": [],
        "related": [],
    },
}

# Resolve the related lists once at import time, so templates get ready-made
# {name, label} pairs instead of doing lookups of their own. `app` marks the
# pages that are software rather than prose, so base.html knows which ones get
# WebApplication markup.
for _key, _page in PAGES.items():
    _page["related_links"] = [
        {"name": _name, "label": PAGES[_name]["label"]} for _name in _page["related"]
    ]
    _page["app"] = _key not in ("about", "privacy", "terms")
