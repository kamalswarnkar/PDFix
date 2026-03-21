# PDFix

PDFix is a Django-based web app for common PDF workflows such as merging, splitting, compressing, converting, protecting, unlocking, rotating, extracting, and reordering files. The project is built as a lightweight server-rendered toolkit: users upload files through HTML forms, Django views call focused service modules, processed files are written to `media/`, and the result is streamed back as a download.

## What the project includes

PDFix currently ships with these tools:

- Merge PDF
- Split PDF
- Compress PDF
- Compress PDF to 100 KB target
- Extract Pages
- Image to PDF
- PDF to Image
- PDF to DOCX
- DOCX to PDF
- Rotate PDF
- Protect PDF
- Unlock PDF
- Reorder PDF Pages

It also includes supporting pages for `About`, `Privacy`, `Terms`, plus `robots.txt` and `sitemap.xml`.

## Tech stack

- Backend: Django 6
- Language: Python
- PDF processing: `pypdf`
- PDF compression: Ghostscript via `subprocess`
- PDF to image: `pdf2image`
- PDF to DOCX: `pdf2docx`
- Image to PDF: Pillow
- DOCX to PDF: LibreOffice / `soffice`
- Frontend: Django templates, vanilla JavaScript, CSS
- Client-side page preview and sorting: PDF.js and SortableJS via CDN
- Database: SQLite (default Django setup, but the app itself is effectively stateless)

## Architecture overview

The project uses a simple Django app structure:

```text
PDFix/
|-- config/                  # Django project config
|   |-- settings.py
|   |-- urls.py
|   |-- asgi.py
|   `-- wsgi.py
|-- tools/                   # Main app
|   |-- services/            # One file-processing module per tool
|   |-- templates/tools/     # Pages, shared components, SEO/static pages
|   |-- utils/cleanup.py     # Deletes old generated files from media/
|   |-- views.py             # Request handling and download responses
|   `-- urls.py              # Tool routes
|-- static/                  # Logo and favicon
|-- media/                   # Temporary uploaded/generated files
|-- db.sqlite3
`-- manage.py
```

### Request workflow

Most tools follow the same lifecycle:

1. A user opens a page rendered from `tools/templates/tools/*.html`.
2. The form submits uploaded file(s) to a dedicated view in `tools/views.py`.
3. The view calls `cleanup_old_files()` before processing.
4. The view hands the uploaded file(s) to a matching service module in `tools/services/`.
5. The service writes the output into `MEDIA_ROOT` using a UUID-based filename.
6. The view returns a `FileResponse` so the browser immediately downloads the processed result.
7. A cookie named `fileDownload=true` is set so the frontend spinner can stop after the file download begins.

### Frontend workflow

- `tools/templates/tools/base.html` provides the shared layout, metadata, and footer links.
- Shared fragments in `tools/templates/tools/components/` handle the uploader UI, FAQ block, and loading spinner.
- Most tool pages are server-rendered forms with very light JavaScript.
- `reorder_pdf.html` is the most interactive page:
  - It renders PDF previews in the browser using PDF.js.
  - Users drag pages into a new order with SortableJS.
  - The final page order is submitted as a hidden input to the backend service.

### Service-layer design

Each tool is isolated in its own module under `tools/services/`. That keeps the view layer thin and makes the project easy to extend. Examples:

- `merge_pdf.py` combines uploaded PDFs with `PdfWriter`
- `split_pdf.py` creates one PDF per page and returns a ZIP archive
- `compress_pdf.py` and `compress_to_size.py` shell out to Ghostscript
- `pdf_to_image.py` converts PDFs into PNGs and packages them as ZIP
- `pdf_to_docx.py` uses `pdf2docx`
- `docx_to_pdf.py` shells out to `soffice --headless`
- `protect_pdf.py` and `unlock_pdf.py` handle password operations with `pypdf`
- `reorder_pdf.py` validates the submitted page sequence before rebuilding the file

## Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd PDFix
```

### 2. Create and activate a virtual environment

Windows:

```bash
python -m venv penv
penv\Scripts\activate
```

macOS / Linux:

```bash
python -m venv penv
source penv/bin/activate
```

### 3. Install Python packages

Install dependencies from the committed `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 4. Install system dependencies

Some tools rely on executables outside Python:

- Ghostscript
  - Required for `compress-pdf` and `compress-pdf-100kb`
  - The code resolves `gs`/`gswin64c` from `PATH` (with a Windows fallback path check).
- LibreOffice
  - Required for `docx-to-pdf`
  - The code expects `soffice` to be available in `PATH`
- Poppler
  - Required by `pdf2image` for `pdf-to-image`
  - Make sure Poppler binaries are installed and available in `PATH`

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Start the development server

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## URL map

Main routes exposed by `tools/urls.py`:

- `/`
- `/merge-pdf/`
- `/split-pdf/`
- `/compress-pdf/`
- `/compress-pdf-100kb/`
- `/extract-pages/`
- `/image-to-pdf/`
- `/pdf-to-image/`
- `/pdf-to-docx/`
- `/docx-to-pdf/`
- `/rotate-pdf/`
- `/protect-pdf/`
- `/unlock-pdf/`
- `/reorder-pdf/`
- `/about/`
- `/privacy/`
- `/terms/`
- `/robots.txt`
- `/sitemap.xml`

## File handling and cleanup

- Generated files are stored in `media/`
- Filenames are UUID-based to avoid collisions
- `cleanup_old_files()` removes files older than 30 minutes
- Cleanup runs at the start of each tool request, not as a background job

This makes the app simple to run locally, but production deployments may benefit from scheduled cleanup, isolated temp directories, and stricter validation around uploads.

## Current implementation notes

- The app does not currently define domain models beyond Django defaults, so the database is not central to the product workflow.
- `tools/tests.py` is still empty, so automated test coverage has not been added yet.
- `DEBUG = False`, `ALLOWED_HOSTS = ["*"]`, and a hardcoded secret key are present in `config/settings.py`; the secret key and host policy should be hardened before production deployment.
- Compression and DOCX conversion depend on local machine tooling, so portability is limited until those paths/settings are externalized.
- Most tools trust uploaded input and perform only minimal validation. That is acceptable for a local/demo project, but production use should add stronger validation, error handling, logging, and size limits.

## How to add a new tool

To extend PDFix with another PDF utility:

1. Add a new processing function in `tools/services/`
2. Create a view in `tools/views.py`
3. Register a route in `tools/urls.py`
4. Add a new template in `tools/templates/tools/`
5. Link it from `home.html`

The current project structure is clean enough that new tools can be added without changing the overall architecture.

## Summary

PDFix is a straightforward, modular Django PDF toolkit with:

- Server-rendered pages
- Thin views
- Per-tool service modules
- Temporary file output in `media/`
- Direct file-download responses
- Small reusable frontend components

It is a good base for a personal project, portfolio app, or small utility product, and it has clear next steps if you want to harden it for production.




