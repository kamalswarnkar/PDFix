"""Shared upload validation and media-file helpers.

Every tool routes uploads through validate_upload() so the size cap, the
extension allow-list and the magic-byte check are enforced in exactly one
place instead of thirteen.
"""
import os
import uuid

from django.conf import settings


class ToolError(Exception):
    """An error whose message is safe to show the user verbatim."""


# First bytes each accepted format must start with. The extension alone is a
# client-side hint; these bytes are what actually reaches Ghostscript/LibreOffice.
_MAGIC = {
    ".pdf": (b"%PDF-",),
    ".docx": (b"PK\x03\x04",),
    ".doc": (b"\xd0\xcf\x11\xe0", b"PK\x03\x04"),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".webp": (b"RIFF",),
}

_LABEL = {
    ".pdf": "PDF",
    ".docx": "Word (DOCX)",
    ".doc": "Word",
    ".png": "PNG",
    ".jpg": "JPG",
    ".jpeg": "JPG",
    ".webp": "WebP",
}


def human_mb(num_bytes):
    return f"{num_bytes / (1024 * 1024):.0f} MB"


def extension(name):
    return os.path.splitext(name or "")[1].lower()


def validate_upload(upload, allowed_extensions):
    """Raise ToolError unless `upload` is a plausible file of an allowed type."""
    if upload is None:
        raise ToolError("No file selected. Please choose a file and try again.")

    name = upload.name
    ext = extension(name)
    if ext not in allowed_extensions:
        names = ", ".join(dict.fromkeys(_LABEL.get(e, e) for e in allowed_extensions))
        raise ToolError(f"'{name}' is not supported. Please upload a {names} file.")

    if upload.size == 0:
        raise ToolError(f"'{name}' is empty.")

    if upload.size > settings.MAX_UPLOAD_BYTES:
        limit = human_mb(settings.MAX_UPLOAD_BYTES)
        raise ToolError(f"'{name}' is {human_mb(upload.size)}. The limit is {limit} per file.")

    signatures = _MAGIC.get(ext)
    if signatures:
        upload.seek(0)
        header = upload.read(8)
        upload.seek(0)
        if not any(header.startswith(sig) for sig in signatures):
            label = _LABEL.get(ext, ext)
            raise ToolError(
                f"'{name}' does not look like a real {label} file. "
                "It may be corrupt, or renamed from another format."
            )


def validate_uploads(uploads, allowed_extensions, max_files=None):
    """Validate a list of uploads and enforce the per-request count/size caps."""
    if not uploads:
        raise ToolError("No files selected. Please upload at least one file.")

    limit = max_files or settings.MAX_UPLOAD_FILES
    if len(uploads) > limit:
        raise ToolError(
            f"Too many files ({len(uploads)}). Please upload at most {limit} at a time."
        )

    total = sum(u.size for u in uploads)
    if total > settings.MAX_UPLOAD_TOTAL_BYTES:
        cap = human_mb(settings.MAX_UPLOAD_TOTAL_BYTES)
        raise ToolError(f"Those files total {human_mb(total)}. The combined limit is {cap}.")

    for upload in uploads:
        validate_upload(upload, allowed_extensions)


def read_pdf(source, label="PDF"):
    """Open a PDF, turning pypdf's failure modes into user-facing messages.

    Every tool reads its input through here, so a corrupt or password-protected
    upload produces the same clear message everywhere instead of a stack trace.
    """
    from pypdf import PdfReader
    from pypdf.errors import DependencyError, FileNotDecryptedError

    encrypted_message = (
        f"'{label}' is password-protected. "
        "Remove the password with the Unlock PDF tool first."
    )

    try:
        reader = PdfReader(source)
    except (DependencyError, FileNotDecryptedError) as exc:
        # ponytail: pypdf cannot even *identify* an AES-encrypted PDF without the
        # optional `cryptography` package - it raises DependencyError from inside
        # the decryption path. That only happens for encrypted files, so treat it
        # as such rather than pulling in the dependency just to print a message.
        raise ToolError(encrypted_message) from exc
    except Exception as exc:
        raise ToolError(
            f"'{label}' could not be read. It may be corrupt or not a real PDF."
        ) from exc

    if reader.is_encrypted:
        # Many PDFs carry an owner password only; the empty user password opens them.
        try:
            opened = reader.decrypt("")
        except Exception:
            opened = False
        if not opened:
            raise ToolError(encrypted_message)

    try:
        page_count = len(reader.pages)
    except Exception as exc:
        raise ToolError(f"'{label}' could not be read. It may be corrupt.") from exc

    if page_count == 0:
        raise ToolError(f"'{label}' contains no pages.")

    return reader


def safe_stem(name, fallback="document"):
    """Filename stem with anything path-like or archive-hostile stripped out."""
    stem = os.path.splitext(os.path.basename(name or ""))[0]
    stem = "".join(ch for ch in stem if ch.isalnum() or ch in " ._-").strip()
    return stem[:60] or fallback


def media_path(filename):
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    return os.path.join(settings.MEDIA_ROOT, filename)


def new_media_path(suffix):
    """Return (filename, absolute path) for a fresh, collision-free output file."""
    filename = f"{uuid.uuid4()}{suffix}"
    return filename, media_path(filename)


def save_upload(upload, suffix):
    """Stream an upload to disk in chunks; returns the absolute path."""
    _, path = new_media_path(suffix)
    with open(path, "wb") as out:
        for chunk in upload.chunks():
            out.write(chunk)
    return path
