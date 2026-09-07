import pikepdf

from ..uploads import ToolError, new_media_path


def unlock_pdf(file, pwd):
    """Remove password protection from a PDF, given the correct password.

    The old version ignored the result of decrypt(), so a wrong password
    produced an unrelated error further down. pikepdf reports it directly.
    """
    pwd = pwd or ""

    file.seek(0)
    try:
        pdf = pikepdf.open(file, password=pwd)
    except pikepdf.PasswordError:
        raise ToolError(
            "Incorrect password. Check it and try again - passwords are case-sensitive."
        ) from None
    except Exception as exc:
        raise ToolError(
            f"'{file.name}' could not be read. It may be corrupt or not a real PDF."
        ) from exc

    with pdf:
        if not pdf.is_encrypted:
            raise ToolError("This PDF is not password-protected, so there is nothing to remove.")

        filename, output_path = new_media_path("_unlocked.pdf")
        pdf.save(output_path)

    return filename
