from whitenoise.storage import CompressedManifestStaticFilesStorage


class ForgivingManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Manifest storage that does not take the whole site down over one asset.

    The strict default raises ValueError when a template references a file that
    is not in staticfiles.json, which turns a single missing image into a 500 on
    every page. Falling back to the unhashed URL loses cache-busting for that one
    file and nothing else.
    """

    manifest_strict = False
