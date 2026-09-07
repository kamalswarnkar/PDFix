import pikepdf

from ..uploads import ToolError, new_media_path

MIN_PASSWORD_LENGTH = 4


def protect_pdf(file, pwd):
    """Encrypt a PDF with AES-256.

    Uses pikepdf/qpdf rather than pypdf: pypdf falls back to RC4-128 (broken)
    unless the extra `cryptography` package is installed, while qpdf ships
    AES-256 support in the wheel we already depend on.
    """
    pwd = (pwd or "").strip()
    if not pwd:
        raise ToolError("Please enter a password.")
    if len(pwd) < MIN_PASSWORD_LENGTH:
        raise ToolError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    file.seek(0)
    try:
        pdf = pikepdf.open(file)
    except pikepdf.PasswordError:
        raise ToolError(
            "This PDF is already password-protected. "
            "Unlock it first if you want to set a new password."
        ) from None
    except Exception as exc:
        raise ToolError(
            f"'{file.name}' could not be read. It may be corrupt or not a real PDF."
        ) from exc

    filename, output_path = new_media_path("_protected.pdf")
    with pdf:
        # R=6 is the AES-256 revision from the PDF 2.0 spec.
        pdf.save(output_path, encryption=pikepdf.Encryption(user=pwd, owner=pwd, R=6))

    return filename
