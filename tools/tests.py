"""Tests for the parts that break silently: validation, page-range parsing,
and each tool's happy path.

Ghostscript and LibreOffice are not required - the tools that shell out to them
(compress, compress-to-size, docx-to-pdf, pdf-to-docx) are covered at the
validation layer only, which is where their bugs actually were.
"""
import base64
import io
import json
import os
import re
import shutil
import socketserver
import tempfile
import time
from io import StringIO
import urllib.error
import zipfile
from unittest import mock

import pikepdf
import pymupdf
from django.conf import settings
from django.core import mail
from django.core.mail import EmailMessage
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from pypdf import PdfReader, PdfWriter

from config.email_backend import TOKEN_URL, GmailAPIBackend, GmailAPIError

from . import views
from .management.commands.gmail_auth import Command as GmailAuthCommand
from .models import Feedback
from .services.extract_pages import extract_pages, parse_page_selection
from .services.image_to_pdf import img_to_pdf
from .services.merge_pdf import merge_pdfs
from .services.pdf_to_image import pdf_to_images
from .services.protect_pdf import protect_pdf
from .services.reorder_pdf import parse_order, reorder_pdf
from .services.rotate_pdf import rotate_pdf
from .services.split_pdf import split_pdf
from .services.unlock_pdf import unlock_pdf
from .seo import PAGES
from .uploads import ToolError, media_path, validate_upload, validate_uploads

MEDIA = tempfile.mkdtemp(prefix="trypdf-tests-")


def pdf_bytes(pages=3):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=300)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def pdf_upload(pages=3, name="doc.pdf"):
    return SimpleUploadedFile(name, pdf_bytes(pages), content_type="application/pdf")


def image_upload(name="photo.png", size=(400, 200), mode="RGB"):
    buffer = io.BytesIO()
    Image.new(mode, size, (200, 30, 30)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def output_bytes(filename):
    with open(media_path(filename), "rb") as handle:
        return handle.read()


@override_settings(MEDIA_ROOT=MEDIA)
class UploadValidationTests(TestCase):
    def test_accepts_a_real_pdf(self):
        validate_upload(pdf_upload(), (".pdf",))

    def test_rejects_missing_file(self):
        with self.assertRaises(ToolError):
            validate_upload(None, (".pdf",))

    def test_rejects_wrong_extension(self):
        upload = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        with self.assertRaisesMessage(ToolError, "not supported"):
            validate_upload(upload, (".pdf",))

    def test_rejects_empty_file(self):
        upload = SimpleUploadedFile("empty.pdf", b"", content_type="application/pdf")
        with self.assertRaisesMessage(ToolError, "empty"):
            validate_upload(upload, (".pdf",))

    def test_rejects_content_that_is_not_really_a_pdf(self):
        """A .exe renamed to .pdf must not reach Ghostscript."""
        upload = SimpleUploadedFile("evil.pdf", b"MZ\x90\x00payload", content_type="application/pdf")
        with self.assertRaisesMessage(ToolError, "does not look like"):
            validate_upload(upload, (".pdf",))

    @override_settings(MAX_UPLOAD_BYTES=1024)
    def test_rejects_oversized_file(self):
        with self.assertRaisesMessage(ToolError, "The limit is"):
            validate_upload(pdf_upload(pages=40), (".pdf",))

    def test_stream_is_rewound_after_the_magic_check(self):
        upload = pdf_upload()
        validate_upload(upload, (".pdf",))
        self.assertTrue(upload.read().startswith(b"%PDF-"))

    @override_settings(MAX_UPLOAD_FILES=2)
    def test_rejects_too_many_files(self):
        with self.assertRaisesMessage(ToolError, "Too many files"):
            validate_uploads([pdf_upload() for _ in range(3)], (".pdf",))

    @override_settings(MAX_UPLOAD_TOTAL_BYTES=100)
    def test_rejects_oversized_batch(self):
        with self.assertRaisesMessage(ToolError, "combined limit"):
            validate_uploads([pdf_upload(), pdf_upload()], (".pdf",))


class PageSelectionTests(TestCase):
    def test_single_pages_ranges_and_order(self):
        self.assertEqual(parse_page_selection("1-3, 7", 10), [1, 2, 3, 7])
        self.assertEqual(parse_page_selection("3,1", 10), [3, 1])
        self.assertEqual(parse_page_selection("all", 3), [1, 2, 3])

    def test_open_ended_range_runs_to_the_end(self):
        self.assertEqual(parse_page_selection("8-", 10), [8, 9, 10])

    def test_duplicates_are_dropped_but_order_is_kept(self):
        self.assertEqual(parse_page_selection("3,1,3", 5), [3, 1])

    def test_rejects_out_of_range(self):
        with self.assertRaisesMessage(ToolError, "does not exist"):
            parse_page_selection("1-99", 5)

    def test_rejects_backwards_range(self):
        with self.assertRaisesMessage(ToolError, "backwards"):
            parse_page_selection("5-2", 10)

    def test_rejects_garbage(self):
        with self.assertRaises(ToolError):
            parse_page_selection("one to three", 5)
        with self.assertRaises(ToolError):
            parse_page_selection("", 5)

    def test_page_zero_is_rejected(self):
        with self.assertRaises(ToolError):
            parse_page_selection("0", 5)


class PageOrderTests(TestCase):
    def test_accepts_a_full_permutation(self):
        self.assertEqual(parse_order("3,1,2", 3), [3, 1, 2])

    def test_rejects_a_partial_order(self):
        with self.assertRaisesMessage(ToolError, "exactly once"):
            parse_order("1,2", 3)

    def test_rejects_a_repeated_page(self):
        with self.assertRaisesMessage(ToolError, "exactly once"):
            parse_order("1,1,2", 3)

    def test_rejects_non_numeric(self):
        with self.assertRaises(ToolError):
            parse_order("1,x,3", 3)


@override_settings(MEDIA_ROOT=MEDIA)
class ServiceTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def test_merge_joins_page_counts(self):
        result = merge_pdfs([pdf_upload(2), pdf_upload(3)])
        self.assertEqual(len(PdfReader(io.BytesIO(output_bytes(result))).pages), 5)

    def test_merge_needs_two_files(self):
        with self.assertRaisesMessage(ToolError, "at least two"):
            merge_pdfs([pdf_upload()])

    def test_merge_reports_an_encrypted_input_clearly(self):
        locked = SimpleUploadedFile(
            "locked.pdf", output_bytes(protect_pdf(pdf_upload(), "hunter2")),
            content_type="application/pdf",
        )
        with self.assertRaisesMessage(ToolError, "password-protected"):
            merge_pdfs([locked, pdf_upload()])

    def test_split_produces_one_zip_entry_per_page(self):
        result = split_pdf(pdf_upload(pages=12, name="report.pdf"))
        with zipfile.ZipFile(io.BytesIO(output_bytes(result))) as archive:
            names = archive.namelist()
        self.assertEqual(len(names), 12)
        # Zero-padded so a file browser sorts them correctly.
        self.assertEqual(names[0], "report_page_01.pdf")
        self.assertEqual(names[-1], "report_page_12.pdf")

    def test_split_refuses_a_single_page_document(self):
        with self.assertRaisesMessage(ToolError, "nothing to split"):
            split_pdf(pdf_upload(pages=1))

    def test_extract_keeps_the_requested_order(self):
        result = extract_pages(pdf_upload(pages=5), "4,1")
        self.assertEqual(len(PdfReader(io.BytesIO(output_bytes(result))).pages), 2)

    def test_rotate_sets_the_page_rotation(self):
        result = rotate_pdf(pdf_upload(pages=1), 90)
        page = PdfReader(io.BytesIO(output_bytes(result))).pages[0]
        self.assertEqual(page.get("/Rotate"), 90)

    def test_rotate_rejects_an_arbitrary_angle(self):
        with self.assertRaisesMessage(ToolError, "90, 180 or 270"):
            rotate_pdf(pdf_upload(), 45)
        with self.assertRaises(ToolError):
            rotate_pdf(pdf_upload(), None)

    def test_reorder_rewrites_the_page_sequence(self):
        result = reorder_pdf(pdf_upload(pages=3), "3,2,1")
        self.assertEqual(len(PdfReader(io.BytesIO(output_bytes(result))).pages), 3)

    def test_protect_then_unlock_round_trips(self):
        protected = output_bytes(protect_pdf(pdf_upload(), "hunter2"))

        with self.assertRaises(pikepdf.PasswordError):
            pikepdf.open(io.BytesIO(protected))

        upload = SimpleUploadedFile("locked.pdf", protected, content_type="application/pdf")
        unlocked = output_bytes(unlock_pdf(upload, "hunter2"))
        self.assertFalse(pikepdf.open(io.BytesIO(unlocked)).is_encrypted)

    def test_protect_uses_aes_256_not_rc4(self):
        protected = output_bytes(protect_pdf(pdf_upload(), "hunter2"))
        with pikepdf.open(io.BytesIO(protected), password="hunter2") as pdf:
            self.assertEqual(pdf.encryption.R, 6)  # AES-256

    def test_protect_rejects_a_short_password(self):
        with self.assertRaisesMessage(ToolError, "at least 4"):
            protect_pdf(pdf_upload(), "ab")

    def test_unlock_reports_a_wrong_password(self):
        protected = output_bytes(protect_pdf(pdf_upload(), "hunter2"))
        upload = SimpleUploadedFile("locked.pdf", protected, content_type="application/pdf")
        with self.assertRaisesMessage(ToolError, "Incorrect password"):
            unlock_pdf(upload, "wrong")

    def test_unlock_says_so_when_there_is_no_password(self):
        with self.assertRaisesMessage(ToolError, "not password-protected"):
            unlock_pdf(pdf_upload(), "anything")

    def test_image_to_pdf_renders_above_72_dpi(self):
        """The old version letterboxed everything to 595 px wide, at 72 DPI."""
        result = img_to_pdf([image_upload(size=(2000, 1400))], page_size="a4")
        with pymupdf.open(stream=output_bytes(result), filetype="pdf") as doc:
            image = doc[0].get_images(full=True)[0]
            self.assertGreater(image[2], 1000)  # pixel width of the embedded image

    def test_image_to_pdf_auto_orients_a4_pages(self):
        wide = img_to_pdf([image_upload(size=(1600, 900))], page_size="a4")
        with pymupdf.open(stream=output_bytes(wide), filetype="pdf") as doc:
            page = doc[0].rect
        self.assertGreater(page.width, page.height)

    def test_image_to_pdf_fit_mode_matches_the_image_aspect(self):
        result = img_to_pdf([image_upload(size=(1000, 500))], page_size="fit")
        with pymupdf.open(stream=output_bytes(result), filetype="pdf") as doc:
            page = doc[0].rect
        self.assertAlmostEqual(page.width / page.height, 2.0, places=1)

    def test_image_to_pdf_flattens_transparency_to_white(self):
        buffer = io.BytesIO()
        Image.new("RGBA", (100, 100), (255, 0, 0, 0)).save(buffer, format="PNG")
        upload = SimpleUploadedFile("clear.png", buffer.getvalue(), content_type="image/png")
        result = img_to_pdf([upload])  # would raise or go black before the fix
        self.assertTrue(output_bytes(result).startswith(b"%PDF-"))

    def test_image_to_pdf_combines_pages_in_order(self):
        result = img_to_pdf([image_upload("a.png"), image_upload("b.png")])
        with pymupdf.open(stream=output_bytes(result), filetype="pdf") as doc:
            self.assertEqual(doc.page_count, 2)

    def test_pdf_to_image_names_entries_uniquely_per_source(self):
        """Two uploads with the same name used to overwrite each other."""
        result = pdf_to_images(
            [pdf_upload(2, "report.pdf"), pdf_upload(2, "report.pdf")], dpi=72
        )
        with zipfile.ZipFile(io.BytesIO(output_bytes(result))) as archive:
            names = archive.namelist()
        self.assertEqual(len(names), 4)
        self.assertEqual(len(set(names)), 4)

    def test_pdf_to_image_honours_format_and_dpi(self):
        result = pdf_to_images([pdf_upload(1)], dpi=72, image_format="jpg")
        with zipfile.ZipFile(io.BytesIO(output_bytes(result))) as archive:
            name = archive.namelist()[0]
            self.assertTrue(name.endswith(".jpg"))
            self.assertTrue(archive.read(name).startswith(b"\xff\xd8\xff"))


@override_settings(
    GMAIL_CLIENT_ID="cid", GMAIL_CLIENT_SECRET="secret", GMAIL_REFRESH_TOKEN="refresh",
    EMAIL_TIMEOUT=5,
)
class GmailAPIBackendTests(TestCase):
    """The Gmail API backend: HTTPS transport for hosts that block SMTP."""

    def setUp(self):
        GmailAPIBackend._token = None
        GmailAPIBackend._token_expires_at = 0.0

    @staticmethod
    def _response(payload):
        stub = mock.MagicMock()
        stub.read.return_value = json.dumps(payload).encode()
        stub.__enter__.return_value = stub
        return stub

    def _run(self, urlopen, subject="Hi", body="There", to="admin@example.com"):
        with mock.patch("config.email_backend.urllib.request.urlopen", urlopen):
            return GmailAPIBackend().send_messages(
                [EmailMessage(subject, body, "me@gmail.com", [to])]
            )

    def test_refreshes_a_token_then_sends(self):
        urlopen = mock.MagicMock(side_effect=[
            self._response({"access_token": "tok", "expires_in": 3600}),
            self._response({"id": "18f"}),
        ])
        self.assertEqual(self._run(urlopen), 1)

        token_req, send_req = urlopen.call_args_list[0][0][0], urlopen.call_args_list[1][0][0]
        self.assertEqual(token_req.full_url, "https://oauth2.googleapis.com/token")
        self.assertIn(b"grant_type=refresh_token", token_req.data)
        self.assertEqual(
            send_req.full_url, "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        )
        self.assertEqual(send_req.get_header("Authorization"), "Bearer tok")

    def test_message_is_base64url_encoded_rfc822(self):
        urlopen = mock.MagicMock(side_effect=[
            self._response({"access_token": "tok", "expires_in": 3600}),
            self._response({"id": "18f"}),
        ])
        self._run(urlopen, subject="Bug in Merge PDF", body="it broke")

        raw = json.loads(urlopen.call_args_list[1][0][0].data)["raw"]
        # base64url, not standard base64: + and / would corrupt the payload.
        self.assertNotIn("+", raw)
        self.assertNotIn("/", raw)
        decoded = base64.urlsafe_b64decode(raw).decode()
        self.assertIn("Subject: Bug in Merge PDF", decoded)
        self.assertIn("it broke", decoded)
        self.assertIn("To: admin@example.com", decoded)

    def test_token_is_reused_across_sends(self):
        urlopen = mock.MagicMock(side_effect=[
            self._response({"access_token": "tok", "expires_in": 3600}),
            self._response({"id": "1"}),
            self._response({"id": "2"}),
        ])
        with mock.patch("config.email_backend.urllib.request.urlopen", urlopen):
            backend = GmailAPIBackend()
            backend.send_messages([EmailMessage("a", "b", "me@gmail.com", ["x@y.z"])])
            backend.send_messages([EmailMessage("c", "d", "me@gmail.com", ["x@y.z"])])
        self.assertEqual(urlopen.call_count, 3)  # one token, two sends

    def test_expired_token_is_refreshed(self):
        GmailAPIBackend._token = "stale"
        GmailAPIBackend._token_expires_at = time.monotonic() - 1
        urlopen = mock.MagicMock(side_effect=[
            self._response({"access_token": "fresh", "expires_in": 3600}),
            self._response({"id": "1"}),
        ])
        self._run(urlopen)
        self.assertEqual(
            urlopen.call_args_list[1][0][0].get_header("Authorization"), "Bearer fresh"
        )

    def test_google_error_body_is_surfaced_not_swallowed(self):
        """invalid_grant is the usual failure; the message must say so."""
        error = urllib.error.HTTPError(
            TOKEN_URL, 400, "Bad Request", {},
            io.BytesIO(b'{"error":"invalid_grant","error_description":"Token has been expired or revoked."}'),
        )
        with mock.patch("config.email_backend.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(GmailAPIError) as caught:
                GmailAPIBackend(fail_silently=False).send_messages(
                    [EmailMessage("a", "b", "me@gmail.com", ["x@y.z"])]
                )
        self.assertIn("invalid_grant", str(caught.exception))
        self.assertIn("400", str(caught.exception))

    def test_fail_silently_returns_zero_instead_of_raising(self):
        with mock.patch("config.email_backend.urllib.request.urlopen",
                        side_effect=urllib.error.URLError("no route to host")):
            sent = GmailAPIBackend(fail_silently=True).send_messages(
                [EmailMessage("a", "b", "me@gmail.com", ["x@y.z"])]
            )
        self.assertEqual(sent, 0)

    @override_settings(GMAIL_REFRESH_TOKEN="")
    def test_missing_credentials_name_the_setting(self):
        with self.assertRaisesMessage(GmailAPIError, "GMAIL_REFRESH_TOKEN"):
            GmailAPIBackend(fail_silently=False).send_messages(
                [EmailMessage("a", "b", "me@gmail.com", ["x@y.z"])]
            )

    def test_no_messages_makes_no_network_call(self):
        with mock.patch("config.email_backend.urllib.request.urlopen") as urlopen:
            self.assertEqual(GmailAPIBackend().send_messages([]), 0)
        urlopen.assert_not_called()


class GmailAuthClientFileTests(TestCase):
    """Reading Google's client_secret_*.json, for both client types."""

    def _write(self, blob):
        path = os.path.join(tempfile.mkdtemp(), "client_secret.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(blob, handle)
        return path

    def test_desktop_client_gets_a_free_port_and_no_path(self):
        path = self._write({"installed": {
            "client_id": "x.apps.googleusercontent.com", "client_secret": "s",
            "redirect_uris": ["http://localhost"],
        }})
        cid, secret, host, port, sub = GmailAuthCommand()._read_client_file(path)
        self.assertEqual((cid, secret, host, port, sub),
                         ("x.apps.googleusercontent.com", "s", "localhost", 0, ""))

    def test_web_client_reuses_its_registered_redirect_uri(self):
        """Google matches the redirect exactly, so we must not invent one."""
        path = self._write({"web": {
            "client_id": "x.apps.googleusercontent.com", "client_secret": "s",
            "redirect_uris": ["http://127.0.0.1:8000/accounts/google/login/callback/"],
        }})
        _, _, host, port, sub = GmailAuthCommand()._read_client_file(path)
        self.assertEqual(host, "127.0.0.1")
        self.assertEqual(port, 8000)
        self.assertEqual(sub, "/accounts/google/login/callback/")

    def test_web_client_skips_non_loopback_redirects(self):
        path = self._write({"web": {
            "client_id": "x.apps.googleusercontent.com", "client_secret": "s",
            "redirect_uris": ["https://trypdf.example/callback",
                              "http://localhost:9000/cb"],
        }})
        _, _, host, port, sub = GmailAuthCommand()._read_client_file(path)
        self.assertEqual((host, port, sub), ("localhost", 9000, "/cb"))

    def test_web_client_without_a_loopback_redirect_explains_both_fixes(self):
        path = self._write({"web": {
            "client_id": "x.apps.googleusercontent.com", "client_secret": "s",
            "redirect_uris": ["https://trypdf.example/callback"],
        }})
        with self.assertRaises(CommandError) as caught:
            GmailAuthCommand()._read_client_file(path)
        self.assertIn("Desktop app", str(caught.exception))
        self.assertIn("127.0.0.1", str(caught.exception))

    def test_rejects_a_file_that_is_not_an_oauth_client(self):
        path = self._write({"something": "else"})
        with self.assertRaisesMessage(CommandError, "not an OAuth client file"):
            GmailAuthCommand()._read_client_file(path)

    def test_rejects_a_missing_file(self):
        with self.assertRaisesMessage(CommandError, "Could not read"):
            GmailAuthCommand()._read_client_file("no/such/file.json")

    def test_bare_invocation_prints_the_setup_guide(self):
        out = StringIO()
        call_command("gmail_auth", stdout=out)
        self.assertIn("Gmail API", out.getvalue())
        self.assertIn("Desktop app", out.getvalue())

    def test_refuses_a_port_that_is_already_in_use(self):
        """Windows lets HTTPServer rebind a busy port, so guard by connecting."""
        with socketserver.TCPServer(("127.0.0.1", 0), None, bind_and_activate=False) as busy:
            busy.server_bind()
            busy.server_activate()
            port = busy.server_address[1]
            path = self._write({"web": {
                "client_id": "x.apps.googleusercontent.com", "client_secret": "s",
                "redirect_uris": [f"http://127.0.0.1:{port}/cb"],
            }})
            with self.assertRaisesMessage(CommandError, "already listening"):
                call_command("gmail_auth", client_secret_file=path, stdout=StringIO())


@override_settings(MEDIA_ROOT=MEDIA)
class ViewTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        views._recent_submissions.clear()

    def test_every_tool_page_loads(self):
        self.assertEqual(len(views.TOOLS), 13)
        for name in views.TOOLS:
            with self.subTest(tool=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_home_and_static_pages_load(self):
        for path in ("/", "/about/", "/privacy/", "/terms/", "/healthz", "/robots.txt", "/sitemap.xml"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_posting_without_a_file_shows_an_error_not_a_crash(self):
        response = self.client.post("/merge-pdf/", {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No files selected")

    def test_posting_a_disguised_file_is_refused(self):
        upload = SimpleUploadedFile("evil.pdf", b"MZ\x90\x00", content_type="application/pdf")
        response = self.client.post("/rotate-pdf/", {"file": upload, "angle": "90"})
        self.assertContains(response, "does not look like")

    def test_merge_returns_a_download(self):
        response = self.client.post(
            "/merge-pdf/", {"files": [pdf_upload(1, "a.pdf"), pdf_upload(1, "b.pdf")]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("a_merged.pdf", response["Content-Disposition"])

    def test_split_returns_a_zip(self):
        response = self.client.post("/split-pdf/", {"file": pdf_upload(3, "doc.pdf")})
        self.assertIn("doc_split.zip", response["Content-Disposition"])

    def test_extract_reports_a_bad_range_to_the_user(self):
        response = self.client.post(
            "/extract-pages/", {"file": pdf_upload(3), "pages": "1-99"}
        )
        self.assertContains(response, "does not exist")

    def test_protect_rejects_mismatched_confirmation(self):
        response = self.client.post(
            "/protect-pdf/",
            {"file": pdf_upload(), "pwd": "hunter2", "pwd_confirm": "hunter3"},
        )
        self.assertContains(response, "do not match")

    def test_errors_never_leak_a_server_path(self):
        response = self.client.post("/reorder-pdf/", {"file": pdf_upload(3), "order": "1,2"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Traceback")
        self.assertNotIn(MEDIA, response.content.decode())

    def test_feedback_requires_both_fields(self):
        response = self.client.post("/feedback/submit/", {"feature": "Merge PDF"})
        self.assertEqual(response.status_code, 400)

    def test_feedback_is_saved_and_then_rate_limited(self):
        for _ in range(5):
            response = self.client.post(
                "/feedback/submit/", {"feature": "Merge PDF", "issue": "broken"}
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/feedback/submit/", {"feature": "Merge PDF", "issue": "broken"}
        )
        self.assertEqual(response.status_code, 429)

    def test_feedback_rejects_get(self):
        self.assertEqual(self.client.get("/feedback/submit/").status_code, 405)

    def test_feedback_emails_the_admin(self):
        self.client.post("/feedback/submit/", {"feature": "Merge PDF", "issue": "it broke"})
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, [settings.FEEDBACK_EMAIL])
        self.assertEqual(sent.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertIn("Merge PDF", sent.subject)
        self.assertIn("it broke", sent.body)

    def test_suggestion_emails_the_admin(self):
        self.client.post(
            "/suggestion/submit/", {"description": "add OCR", "why_needed": "scanned files"}
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("add OCR", mail.outbox[0].body)

    def test_a_broken_mail_server_still_saves_the_report(self):
        """A dead SMTP host must not turn a saved report into a 500."""
        with mock.patch("tools.views.send_mail", side_effect=OSError("connection refused")):
            response = self.client.post(
                "/feedback/submit/", {"feature": "Split PDF", "issue": "boom"}
            )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"ok": True})
        self.assertTrue(Feedback.objects.filter(feature="Split PDF").exists())


class SEOTests(TestCase):
    """Every page has to look different to a crawler, or they compete with
    each other for the same searches instead of ranking for their own."""

    def _html(self, name):
        return self.client.get(reverse(name)).content.decode()

    def test_every_url_has_seo_copy(self):
        """A page rendered without `seo` in its context silently loses its
        title, description and schema, which is invisible in the browser."""
        for name in PAGES:
            with self.subTest(page=name):
                html = self._html(name)
                self.assertIn("<title>%s</title>" % PAGES[name]["title"], html)
                self.assertIn(PAGES[name]["description"], html)

    def test_titles_and_descriptions_are_unique(self):
        titles = [page["title"] for page in PAGES.values()]
        descriptions = [page["description"] for page in PAGES.values()]
        self.assertEqual(len(set(titles)), len(titles))
        self.assertEqual(len(set(descriptions)), len(descriptions))

    def test_titles_and_descriptions_fit_a_search_result(self):
        for name, page in PAGES.items():
            with self.subTest(page=name):
                self.assertLessEqual(len(page["title"]), 65)
                self.assertLessEqual(len(page["description"]), 160)

    def test_exactly_one_h1_per_page(self):
        for name in PAGES:
            with self.subTest(page=name):
                self.assertEqual(self._html(name).count("<h1"), 1)

    def test_structured_data_is_valid_json(self):
        pattern = r'<script type="application/ld\+json">(.*?)</script>'
        for name in PAGES:
            with self.subTest(page=name):
                blocks = re.findall(pattern, self._html(name), re.S)
                self.assertTrue(blocks)
                for block in blocks:
                    json.loads(block)

    def test_canonical_ignores_query_parameters(self):
        """A shared ?utm_source= link must point back at the clean URL."""
        html = self.client.get("/merge-pdf/?utm_source=twitter").content.decode()
        self.assertIn('<link rel="canonical" href="http://testserver/merge-pdf/">', html)

    def test_related_links_point_at_real_tools(self):
        for name, page in PAGES.items():
            for related in page["related"]:
                with self.subTest(page=name, related=related):
                    self.assertIn(related, PAGES)
                    self.assertNotEqual(related, name)
