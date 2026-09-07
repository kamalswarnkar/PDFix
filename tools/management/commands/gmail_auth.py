"""One-time OAuth helper: turn a Google client ID/secret into a refresh token.

Run once on your own machine, paste the result into .env and your host's
environment, and never run it again - refresh tokens do not expire unless you
revoke them or leave the app in "Testing" publishing status.
"""
import http.server
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

from django.core.management.base import BaseCommand, CommandError

from config.email_backend import SCOPE, TOKEN_URL

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

SETUP_HELP = """
Before running this you need an OAuth client:

  1. https://console.cloud.google.com/  ->  create (or pick) a project
  2. APIs & Services -> Library -> "Gmail API" -> Enable
  3. APIs & Services -> OAuth consent screen
       User type: External. Fill in the required fields.
       Under "Test users", add the Gmail address you will send from.
       When it works, come back and click "Publish app" - while the app is in
       Testing, Google expires the refresh token after 7 days.
  4. APIs & Services -> Credentials -> Create credentials -> OAuth client ID
       Application type: Desktop app   (simplest - no redirect URI to set up)
       A Web application client also works, as long as one of its authorised
       redirect URIs is a loopback address such as http://127.0.0.1:8000/
  5. Download the client JSON and run:

       python manage.py gmail_auth --client-secret-file path/to/client_secret_*.json

     or pass the values directly:

       python manage.py gmail_auth --client-id XXX --client-secret YYY

Note: a Web client can only use a port it has already registered, so that port
must be free while this runs - stop `manage.py runserver` first if it is on 8000.
"""

class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Catches Google's redirect and stashes the authorization code."""

    code = None
    error = None

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _CallbackHandler.code = params.get("code", [None])[0]
        _CallbackHandler.error = params.get("error", [None])[0]

        ok = _CallbackHandler.code is not None
        body = (
            "<h2>PDFix is authorised.</h2><p>You can close this tab and go back "
            "to the terminal.</p>" if ok else
            f"<h2>Authorisation failed</h2><p>{_CallbackHandler.error or 'no code returned'}</p>"
        )
        self.send_response(200 if ok else 400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):
        pass  # keep the console clean


class Command(BaseCommand):
    help = "Obtain a Gmail API refresh token for sending mail over HTTPS."

    def add_arguments(self, parser):
        # Not required: running the command bare should print the setup guide
        # rather than an argparse usage error.
        parser.add_argument("--client-id")
        parser.add_argument("--client-secret")
        parser.add_argument(
            "--client-secret-file",
            help="Path to the client_secret_*.json downloaded from Google Cloud "
                 "Console. Reads the id, secret and redirect URI from it.",
        )
        parser.add_argument(
            "--port", type=int, default=0,
            help="Loopback port for the OAuth redirect. Ignored for a Web "
                 "client, which must use a port it has already registered.",
        )
        parser.add_argument(
            "--no-browser", action="store_true",
            help="Print the URL instead of opening a browser.",
        )

    def handle(self, *args, **options):
        if options["client_secret_file"]:
            client_id, client_secret, host, port, path = self._read_client_file(
                options["client_secret_file"]
            )
        elif options["client_id"] and options["client_secret"]:
            client_id = options["client_id"].strip()
            client_secret = options["client_secret"].strip()
            host, port, path = "localhost", options["port"], ""
        else:
            self.stdout.write(SETUP_HELP)
            return

        if not client_id.endswith(".apps.googleusercontent.com"):
            self.stderr.write(self.style.WARNING(
                "That client ID looks unusual - expected it to end in "
                ".apps.googleusercontent.com\n" + SETUP_HELP
            ))

        # Check by *connecting*, not by binding. Windows lets a second socket
        # bind a port that is already in use (HTTPServer sets allow_reuse_address),
        # so a bind test passes and the OAuth callback then lands on whatever else
        # is listening - which answers 404 and this command waits forever.
        if port:
            with socket.socket() as probe:
                probe.settimeout(1)
                if probe.connect_ex(("127.0.0.1", port)) == 0:
                    raise CommandError(
                        f"Something is already listening on 127.0.0.1:{port}.\n"
                        "That is the port your OAuth client registered as its redirect "
                        "URI, so it has to be free for a moment.\n"
                        "Stop it (most likely `manage.py runserver`) and run this again."
                    )

        try:
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", port))
                port = probe.getsockname()[1]
        except OSError as exc:
            raise CommandError(f"Cannot listen on 127.0.0.1:{port}: {exc}") from None

        redirect_uri = f"http://{host}:{port}{path}"
        self.stdout.write(f"Using redirect URI: {redirect_uri}")
        auth_url = f"{AUTH_URL}?" + urllib.parse.urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",   # this is what yields a refresh token
            "prompt": "consent",        # force one even on a repeat run
        })

        self.stdout.write("Approve access in the browser window that opens.")
        self.stdout.write(f"If nothing opens, visit:\n\n{auth_url}\n")
        if not options["no_browser"]:
            webbrowser.open(auth_url)

        _CallbackHandler.code = _CallbackHandler.error = None
        deadline = time.monotonic() + 300

        # Keep serving until the real callback arrives. handle_request() consumes
        # one TCP connection, and browsers routinely open speculative ones that
        # carry no request - serving only once would let a preconnect eat the
        # single shot and leave the callback hitting a closed socket.
        with http.server.HTTPServer(("127.0.0.1", port), _CallbackHandler) as server:
            server.timeout = 5
            while _CallbackHandler.code is None and _CallbackHandler.error is None:
                if time.monotonic() > deadline:
                    break
                server.handle_request()

        if _CallbackHandler.error:
            raise CommandError(f"Google returned an error: {_CallbackHandler.error}")
        if not _CallbackHandler.code:
            raise CommandError("No authorization code received (timed out after 5 minutes).")

        tokens = self._exchange(client_id, client_secret, _CallbackHandler.code, redirect_uri)
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise CommandError(
                "Google did not return a refresh token. Revoke PDFix at "
                "https://myaccount.google.com/permissions and run this again."
            )

        self.stdout.write(self.style.SUCCESS("\nDone. Add these three to .env and to your host:\n"))
        self.stdout.write(f"GMAIL_CLIENT_ID={client_id}")
        self.stdout.write(f"GMAIL_CLIENT_SECRET={client_secret}")
        self.stdout.write(f"GMAIL_REFRESH_TOKEN={refresh_token}")
        self.stdout.write(
            "\nThen check it works:\n"
            "  python manage.py sendtestemail you@example.com\n"
        )

    def _read_client_file(self, path):
        """Pull the credentials, and a usable loopback redirect, out of Google's JSON.

        Desktop ("installed") clients accept any loopback port, so we pick a free
        one. Web clients only accept a redirect URI that is already registered,
        so we have to reuse one of theirs verbatim - Google matches it exactly.
        """
        try:
            with open(path, encoding="utf-8") as handle:
                blob = json.load(handle)
        except (OSError, ValueError) as exc:
            raise CommandError(f"Could not read {path}: {exc}") from None

        kind = "installed" if "installed" in blob else "web" if "web" in blob else None
        if not kind:
            raise CommandError(
                f"{path} is not an OAuth client file - expected a top-level "
                '"installed" or "web" key.'
            )

        section = blob[kind]
        client_id = section.get("client_id", "").strip()
        client_secret = section.get("client_secret", "").strip()
        if not client_id or not client_secret:
            raise CommandError(f"{path} is missing client_id or client_secret.")

        if kind == "installed":
            return client_id, client_secret, "localhost", 0, ""

        # Web client: find a loopback redirect URI it already has registered.
        for uri in section.get("redirect_uris", []):
            parts = urllib.parse.urlparse(uri)
            if parts.hostname in ("localhost", "127.0.0.1") and parts.scheme == "http":
                self.stdout.write(
                    "Web-application client detected; reusing its registered "
                    "loopback redirect URI."
                )
                return (client_id, client_secret, parts.hostname,
                        parts.port or 80, parts.path or "")

        raise CommandError(
            "This is a Web-application OAuth client with no loopback redirect URI, "
            "so this command has nothing to listen on.\n\n"
            "Fix it either way:\n"
            "  (a) Credentials -> your client -> Authorised redirect URIs -> add\n"
            "        http://127.0.0.1:8000/\n"
            "      then download the JSON again, or\n"
            "  (b) create a new OAuth client with Application type = Desktop app,\n"
            "      which needs no redirect configuration at all."
        )

    def _exchange(self, client_id, client_secret, code, redirect_uri):
        payload = urllib.parse.urlencode({
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }).encode()
        request = urllib.request.Request(TOKEN_URL, data=payload, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:600].decode("utf-8", errors="replace")
            raise CommandError(f"Token exchange failed (HTTP {exc.code}): {detail}") from None
