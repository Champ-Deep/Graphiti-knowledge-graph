"""
Load the Google OAuth client id and secret for Gmail setup scripts.

Credentials come from the environment or from a gitignored client JSON
file. These values must never be hardcoded in source.
"""
import json
import os
from pathlib import Path
from typing import Mapping, Optional, Tuple


class GoogleOAuthConfigError(Exception):
    """Google OAuth client id or secret is not configured."""


_MISSING_MESSAGE = (
    "Google OAuth client credentials are not configured. "
    "Set both GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET, or set "
    "GOOGLE_CLIENT_SECRETS_FILE to a gitignored OAuth client JSON file "
    "downloaded from Google Cloud Console. The JSON must include "
    "client_id and client_secret on an \"installed\" or \"web\" client. "
    "Do not commit the client secret."
)


def load_google_oauth_client(
    environ: Optional[Mapping[str, str]] = None,
) -> Tuple[str, str]:
    """Return ``(client_id, client_secret)`` from the environment or a JSON file.

    Resolution order:

    1. ``GOOGLE_CLIENT_ID`` and ``GOOGLE_CLIENT_SECRET`` when both are set.
    2. The OAuth client JSON at ``GOOGLE_CLIENT_SECRETS_FILE``.

    Raises:
        GoogleOAuthConfigError: A required value or the JSON file is missing
            or unusable. The message names the variable to set and does not
            include credential values.
    """
    env = os.environ if environ is None else environ
    client_id = _nonempty(env.get("GOOGLE_CLIENT_ID"))
    client_secret = _nonempty(env.get("GOOGLE_CLIENT_SECRET"))
    secrets_file = _nonempty(env.get("GOOGLE_CLIENT_SECRETS_FILE"))

    if client_id and client_secret:
        return client_id, client_secret

    if client_id or client_secret:
        present = "GOOGLE_CLIENT_ID" if client_id else "GOOGLE_CLIENT_SECRET"
        missing = "GOOGLE_CLIENT_SECRET" if client_id else "GOOGLE_CLIENT_ID"
        raise GoogleOAuthConfigError(
            f"{present} is set but {missing} is missing. "
            "Set both GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET, or leave "
            "both unset and set GOOGLE_CLIENT_SECRETS_FILE to a gitignored "
            "OAuth client JSON file."
        )

    if secrets_file:
        return _client_from_secrets_file(secrets_file)

    raise GoogleOAuthConfigError(_MISSING_MESSAGE)


def _nonempty(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _client_from_secrets_file(path: str) -> Tuple[str, str]:
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        raise GoogleOAuthConfigError(
            f"GOOGLE_CLIENT_SECRETS_FILE does not exist: {file_path}"
        )

    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        reason = exc.strerror or "unable to read file"
        raise GoogleOAuthConfigError(
            f"Could not read GOOGLE_CLIENT_SECRETS_FILE ({file_path}): {reason}"
        ) from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise GoogleOAuthConfigError(
            f"GOOGLE_CLIENT_SECRETS_FILE is not valid JSON: {file_path}"
        )

    section = _oauth_section(data, file_path)
    client_id = section.get("client_id")
    client_secret = section.get("client_secret")
    if not isinstance(client_id, str) or not isinstance(client_secret, str):
        raise GoogleOAuthConfigError(
            "GOOGLE_CLIENT_SECRETS_FILE is missing client_id or client_secret. "
            "Use the OAuth client JSON downloaded from Google Cloud Console "
            "(an \"installed\" or \"web\" client)."
        )

    client_id = _nonempty(client_id)
    client_secret = _nonempty(client_secret)
    if not client_id or not client_secret:
        raise GoogleOAuthConfigError(
            "GOOGLE_CLIENT_SECRETS_FILE is missing client_id or client_secret. "
            "Use the OAuth client JSON downloaded from Google Cloud Console "
            "(an \"installed\" or \"web\" client)."
        )
    return client_id, client_secret


def _oauth_section(data: object, file_path: Path) -> Mapping[str, object]:
    if not isinstance(data, dict):
        raise GoogleOAuthConfigError(
            f"GOOGLE_CLIENT_SECRETS_FILE must be a JSON object: {file_path}"
        )

    for key in ("installed", "web"):
        section = data.get(key)
        if isinstance(section, dict):
            return section

    if "client_id" in data or "client_secret" in data:
        return data

    raise GoogleOAuthConfigError(
        "GOOGLE_CLIENT_SECRETS_FILE has no \"installed\" or \"web\" OAuth "
        f"client: {file_path}"
    )
