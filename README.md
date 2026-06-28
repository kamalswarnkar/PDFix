# PDFix 🛠️📄

PDFix is a lightweight, responsive, and robust Django-based web application providing a comprehensive suite of offline-first PDF workflows. It is built as a server-rendered toolkit optimized for speed, reliability, and security, allowing users to process sensitive documents entirely within a clean, modern interface.

---

## ✨ Features & Tools

PDFix includes production-ready document processing utilities and feedback channels:

*   **Merge PDF**: Combine multiple PDF files into one. Supports custom sorting and page reordering via drag-and-drop.
*   **Split PDF**: Extract every page of a PDF into separate files, compiled into a single ZIP archive.
*   **Compress PDF**: Reduce file size using optimized Ghostscript parameters.
*   **Compress to Smallest Size**: Automatically run multiple compression passes (adjusting DPI, JPEG quality, font compression) targeting a highly-compressed file (~100 KB) while ensuring quality and readability are preserved.
*   **Extract Pages**: Pull out a specific, validated page range (Start to End) to create a new PDF.
*   **Image to PDF**: Convert a sequence of JPG/PNG/WebP images into a single, uniform A4-sized PDF document. Supports custom drag-and-drop ordering.
*   **PDF to Image**: Convert pages of a PDF into high-quality PNG images, zipped for download.
*   **PDF to DOCX**: Convert PDFs to editable Word documents (leveraging Word COM on Windows or LibreOffice/pdf2docx as cross-platform fallbacks).
*   **DOCX to PDF**: Convert editable Word documents into professional PDFs with high layout fidelity.
*   **Rotate PDF**: Rotate pages clockwise or counterclockwise with a real-time rotation preview of the first page.
*   **Protect PDF**: Add high-strength password encryption to secure your files.
*   **Unlock PDF**: Remove password restrictions from protected documents.
*   **Reorder PDF Pages**: Drag-and-drop visual page preview grid to completely rearrange a document's page structure.
*   **User Feedback & Suggestions**: Floating quick-action widgets (🐛 Bug Report / 💡 Feature Suggestion) allowing users to submit forms directly, persisting data in the SQLite database and triggering instant email notifications to the admin.

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
*   **Database**: SQLite (built-in, tracking feedback and suggestions)
*   **PDF Libraries**: `pypdf`, `pikepdf`, `pdf2image`, `pdf2docx`, `Pillow`
*   **System Binaries**: Ghostscript, LibreOffice (soffice), Poppler
*   **Frontend**: HTML5, Vanilla JavaScript, CSS Grid/Flexbox
*   **Client Libraries**: PDF.js, SortableJS (via CDN)
*   **Asset Storage**: Auto-cleaned `media/` directory (UUID-based paths)

---

## 🛠️ Installation & Setup

### Local Run

#### 1. Clone & Setup Environment

```bash
git clone <repository-url>
cd PDFix

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
*   **Poppler** (Required for PDF to Image):
    *   Ensure Poppler binaries are installed and accessible on `PATH`.

#### 3. Database & App Initialization

1. Create a `.env` file in the project root containing your configurations (see `.env.example` as a template).
2. Run database migrations:
   ```bash
   python manage.py migrate
   ```
3. Run the development server:
   ```bash
   python manage.py runserver
   ```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your web browser.

---

### Docker Deployment

PDFix can be completely dockerized for a portable, unified setup. The provided `Dockerfile` compiles all required system dependencies (Ghostscript, LibreOffice, Poppler, and fonts) and packages the application.

#### 1. Set Up Environment Variables
Copy `.env.example` to `.env` in the root folder and configure:
```env
DJANGO_SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
DEBUG=false

# Optional Gmail SMTP config for email alerts:
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
FEEDBACK_EMAIL=kamalswarnkar0111@gmail.com
```

#### 2. Run with Docker Compose
Run the following command to build the image and launch the application container:
```bash
docker-compose up --build -d
```
This command:
*   Builds the image with all Python package dependencies and system binaries cached.
*   Runs Django database migrations inside the container automatically.
*   Mounts a persistent Docker volume `pdfix_media` to preserve uploads/downloads inside `/app/media`.
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
PDFix/
├── config/                  # Django project settings
│   ├── settings.py          # Environment configuration
│   └── urls.py              # App routing
├── tools/                   # Core application
│   ├── models.py            # Feedback & Suggestion database models
│   ├── services/            # Isolated file processing services
│   │   ├── compress_pdf.py
│   │   ├── docx_to_pdf.py
│   │   └── ...
│   ├── templates/tools/     # Responsive HTML templates
│   │   ├── components/      # Shared uploader, FAQ, spinner, and alerts
│   │   └── ...
│   ├── utils/
│   │   └── cleanup.py       # Temporary file housekeeping
│   ├── views.py             # Route request handlers
│   └── urls.py              # App URLs
├── media/                   # Workspace for active file conversions
├── static/                  # Brand assets (logo, favicon)
├── Dockerfile               # Production multi-step docker builder
├── docker-compose.yml       # Production-ready docker compose orchestration
├── .env.example             # Config file template
└── manage.py
```

---

## 🧼 File Housekeeping

Uploaded and generated files are automatically isolated in `media/` using unique UUID prefixes to prevent filename collisions. To keep the server storage clean, a lightweight cleanup module runs automatically on every tool request:

*   Deletes temporary and output files older than 30 minutes.
*   Runs safely in the request cycle, requiring no external cron/scheduler configuration.

---

## 🔒 Security & Privacy

*   **Stateless Operations**: No uploaded documents are ever indexed, cataloged, or saved in database models.
*   **Automated Purging**: Media files are deleted automatically after 30 minutes, or instantly where execution blocks allow.
*   **Local Processing Fallbacks**: Features like Windows COM automation bypass external network calls entirely.

