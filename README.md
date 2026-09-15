# tryPDF! 🛠️📄

tryPDF! is a lightweight, responsive, and robust Django-based web application providing a comprehensive suite of offline-first PDF workflows. It is built as a server-rendered toolkit optimized for speed, reliability, and security, allowing users to process sensitive documents entirely within a clean, modern interface.

---

## ✨ Features & Tools

tryPDF! includes production-ready document processing utilities and feedback channels:

*   **Merge PDF**: Combine multiple PDF files into one. Supports custom sorting and page reordering via drag-and-drop.
*   **Split PDF**: Extract every page of a PDF into separate files, compiled into a single ZIP archive.
*   **Compress PDF**: Reduce file size with Ghostscript at three quality levels (smallest / balanced / best). If compression cannot beat the original, the original is returned rather than a larger file.
*   **Compress to a Target Size**: Runs progressively stronger passes (DPI, JPEG quality, font compression) until the file meets a 100/200/500 KB target, returning the smallest result achieved if the target is unreachable.
*   **Extract Pages**: Pull out any selection - single pages, ranges, open-ended ranges or `all` (e.g. `1-3, 7, 9-`) - preserving the order you asked for.
*   **Image to PDF**: Combine JPG/PNG/WebP images into one PDF at 150 DPI, with EXIF rotation honoured, transparency flattened to white, and a choice of A4 pages (auto-orienting to landscape) or pages fitted to the image. Drag to reorder.
*   **PDF to Image**: Render every page to PNG or JPG at 72/150/300 DPI, zipped for download, with entries named so they sort in page order.
*   **PDF to DOCX**: Convert PDFs to editable Word documents (leveraging Word COM on Windows or LibreOffice/pdf2docx as cross-platform fallbacks).
*   **DOCX to PDF**: Convert editable Word documents into professional PDFs with high layout fidelity.
*   **Rotate PDF**: Rotate pages clockwise or counterclockwise with a real-time rotation preview of the first page.
*   **Protect PDF**: Encrypt with **AES-256** (via qpdf), with a confirm-password field so a typo cannot lock a file with a password nobody knows.
*   **Unlock PDF**: Remove password protection, distinguishing a wrong password from a file that was never encrypted.
*   **Reorder PDF Pages**: Drag-and-drop visual page preview grid to completely rearrange a document's page structure.
*   **User Feedback & Suggestions**: Floating widgets (🐛 Bug Report / 💡 Feature Suggestion) that persist to the database and notify the admin through the Gmail API, rate-limited per IP. A mail failure never loses a submission.

---

## 🎨 User Experience & Mobile Compatibility

*   **Fully Responsive Mobile Layout**: Restyled with standard viewport scaling and media-query break points to ensure optimal readability, navigation, and usability across mobiles, tablets, laptops, and desktop computers.
*   **Dynamic Drag-and-Drop Uploader**: Built on top of HTML5 drag-and-drop with custom client-side validation, duplicate checks, and card previews.
*   **Interactive File Previews**: View thumbnails of selected images or doc cards before processing.
*   **Live Rotation Previews**: Real-time rendering of PDF rotation using PDF.js prior to submission.
*   **Elapsed Processing Timers**: Accurate time feedback ("Processing... (0:15)") for long-running conversions to eliminate user frustration.
*   **Secure Password Toggle**: Smooth eye toggle visibility helper for secure, hassle-free credential typing.
*   **Comprehensive Error Handling**: Clean, non-intrusive alert component to gracefully catch invalid page numbers, decryption errors, and conversion failures without triggering unhandled server 500 crashes.

---

## 💻 Tech Stack

*   **Backend**: Django 6.x (Python)
*   **Database**: PostgreSQL via `DATABASE_URL` in production, SQLite locally
*   **PDF Libraries**: `pypdf`, `pikepdf` (qpdf), `PyMuPDF`, `pdf2docx`, `Pillow`
*   **System Binaries**: Ghostscript (compression), LibreOffice/`soffice` (DOCX conversion). Poppler is no longer required - PDF rendering uses PyMuPDF.
*   **Frontend**: HTML5, Vanilla JavaScript, CSS Grid/Flexbox
*   **Client Libraries**: PDF.js and SortableJS, pinned to exact versions with Subresource Integrity hashes
*   **Asset Storage**: Auto-cleaned `media/` directory (UUID-based paths)

---

## 🛠️ Installation & Setup

### Local Run

#### 1. Clone & Setup Environment

```bash
git clone <repository-url>
cd trypdf

# Create a virtual environment
python -m venv penv
source penv/bin/activate  # On Windows: penv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Install System Dependencies

Some advanced tools require system-level executables:

*   **Ghostscript** (Required for PDF Compression):
    *   *Windows*: Install the latest release (e.g., v10.06.0) and add the `bin` directory to your path.
    *   *Linux/macOS*: Install via package manager (`apt-get install ghostscript` or `brew install ghostscript`).
*   **LibreOffice** (Required for DOCX to PDF / PDF to DOCX):
    *   Ensure the `soffice` executable is added to your environment `PATH`.

Poppler is **not** required: PDF-to-image rendering happens in-process via PyMuPDF.

#### 3. Database & App Initialization

1. Copy `.env.example` to `.env` and fill it in. `settings.py` loads it automatically;
   real environment variables always take precedence.
   `DJANGO_SECRET_KEY` is **required** unless `DEBUG=true` - the app refuses to start without it.
2. Run database migrations:
   ```bash
   python manage.py migrate
   ```
3. Run the development server:
   ```bash
   python manage.py runserver
   ```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your web browser.

#### 4. Run the tests

```bash
python manage.py test tools
```

53 tests covering upload validation, page-range parsing, and each tool's happy and
failure paths. Ghostscript and LibreOffice are not needed to run them.

#### 5. Check the deployment configuration

```bash
python manage.py check --deploy
```

#### 6. Set up email (optional)

Notifications go out through the **Gmail API over HTTPS**, not SMTP - hosts like
Render block outbound port 587, which is why the API transport exists. Run this
once and paste the three values it prints into `.env` and your host's environment:

```bash
python manage.py gmail_auth --client-secret-file path/to/client_secret_*.json
```

Run it with no arguments to see how to create the OAuth client. It accepts both
Desktop and Web application clients; a Web client must have a loopback redirect
URI registered, and that port has to be free while the command runs. Then verify:

```bash
python manage.py sendtestemail you@example.com
```

Gmail SMTP still works as a fallback if you prefer it - set `EMAIL_HOST_USER`
and an App Password in `EMAIL_HOST_PASSWORD` and leave the `GMAIL_*` values
empty. With neither configured, mail is printed to the console and submissions
are still saved to the database.

---

### Docker Deployment

The provided `Dockerfile` installs the required system dependencies (Ghostscript, LibreOffice, fonts), runs `collectstatic`, drops to an unprivileged user, and wires `/healthz` up as the container health check.

#### 1. Set Up Environment Variables
Copy `.env.example` to `.env` in the root folder and configure:
```env
DJANGO_SECRET_KEY=your-production-secret-key   # required, app will not boot without it
ALLOWED_HOSTS=your-domain.com
DEBUG=false

# Email alerts via the Gmail API over HTTPS. Get these with:
#   python manage.py gmail_auth --client-id XXX --client-secret YYY
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REFRESH_TOKEN=your-refresh-token
FEEDBACK_EMAIL=kamalswarnkar0111@gmail.com
```

See `.env.example` for the full list, including upload limits and conversion timeouts.

#### 2. Run with Docker Compose
Run the following command to build the image and launch the application container:
```bash
docker-compose up --build -d
```
This command:
*   Builds the image with all Python package dependencies and system binaries cached.
*   Runs Django database migrations inside the container automatically.
*   Mounts a persistent Docker volume `trypdf_media` to preserve uploads/downloads inside `/app/media`.
*   Serves the application on port `8000`.

To view container logs or status:
```bash
docker-compose logs -f
```

To stop the containers:
```bash
docker-compose down
```

---

## 📂 Project Architecture

```text
trypdf/
├── config/                  # Django project settings
│   ├── settings.py          # Environment configuration
│   ├── storage.py           # Non-strict manifest static storage
│   └── urls.py              # App routing
├── tools/                   # Core application
│   ├── models.py            # Feedback & Suggestion database models
│   ├── uploads.py           # Shared upload validation, media helpers, cleanup
│   ├── throttle.py          # Per-IP limits for tools, feedback and admin login
│   ├── seo.py               # Per-page title, description, FAQ and links
│   ├── tests.py             # Test suite
│   ├── services/            # Isolated file processing services
│   │   ├── compress_pdf.py
│   │   ├── docx_to_pdf.py
│   │   └── ...
│   ├── templates/tools/     # Responsive HTML templates
│   │   ├── components/      # Shared uploader, FAQ, spinner, and alerts
│   │   └── ...
│   ├── views.py             # Route request handlers
│   └── urls.py              # App URLs
├── media/                   # Workspace for active file conversions
├── static/                  # Brand assets, plus vendored pdf.js and Sortable
├── Dockerfile               # Production multi-step docker builder
├── docker-compose.yml       # Production-ready docker compose orchestration
├── .env.example             # Config file template
└── manage.py
```

---

## 🧼 File Housekeeping

Uploaded and generated files are automatically isolated in `media/` using unique UUID prefixes to prevent filename collisions. To keep the server storage clean, a lightweight cleanup module runs automatically on every tool request:

*   Result files are unlinked the moment the download response is built (on POSIX), so
    nothing lingers in normal operation.
*   A sweeper removes anything older than `MEDIA_RETENTION_SECONDS` (default 30 minutes) on
    the next upload, covering interrupted downloads and killed workers.
*   Runs inside the request cycle, so no cron or scheduler is needed.

---

## 🔒 Security & Privacy

*   **Validated uploads**: Every upload is checked server-side for extension, size
    (`MAX_UPLOAD_MB`, default 50) and magic bytes before any library or subprocess touches it,
    so a renamed executable never reaches Ghostscript or LibreOffice.
*   **AES-256 encryption**: Protect PDF uses qpdf's AES-256 rather than pypdf's RC4-128 default.
*   **No leaked internals**: Unexpected errors are logged server-side and shown to the user as a
    generic message; exception text and server paths are never rendered into the page.
*   **Hardened headers**: HSTS, HTTPS redirect, secure/HttpOnly cookies, `nosniff`,
    `X-Frame-Options: DENY` and a same-origin referrer policy are all active when `DEBUG=false`.
*   **Rate limiting**: The feedback and suggestion endpoints are throttled per IP.
*   **Stateless operations**: No uploaded document is ever indexed, catalogued, or written to a
    database model.
*   **Local processing**: Conversions run on our own server; no document is sent to a third party.

