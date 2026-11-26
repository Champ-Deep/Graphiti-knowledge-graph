"""Tests for Google OAuth client loading and the setup scripts."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from config.google_oauth import GoogleOAuthConfigError, load_google_oauth_client

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ("get_gmail_token.py", "setup_gmail_oauth.py")
CREDENTIAL_ENV = (
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_CLIENT_SECRETS_FILE",
)


def test_loads_client_from_environment():
    client_id, client_secret = load_google_oauth_client(
        {
            "GOOGLE_CLIENT_ID": " client-id ",
            "GOOGLE_CLIENT_SECRET": " client-secret ",
        }
    )
    assert client_id == "client-id"
    assert client_secret == "client-secret"


def test_missing_environment_names_the_variables():
    with pytest.raises(GoogleOAuthConfigError) as exc_info:
        load_google_oauth_client({})
    message = str(exc_info.value)
    assert "GOOGLE_CLIENT_ID" in message
    assert "GOOGLE_CLIENT_SECRET" in message
    assert "GOOGLE_CLIENT_SECRETS_FILE" in message


def test_partial_environment_names_the_missing_variable():
    with pytest.raises(GoogleOAuthConfigError, match="GOOGLE_CLIENT_SECRET is missing"):
        load_google_oauth_client({"GOOGLE_CLIENT_ID": "client-id"})

    with pytest.raises(GoogleOAuthConfigError, match="GOOGLE_CLIENT_ID is missing"):
        load_google_oauth_client({"GOOGLE_CLIENT_SECRET": "client-secret"})


def test_blank_environment_values_are_missing():
    with pytest.raises(GoogleOAuthConfigError, match="not configured"):
        load_google_oauth_client(
            {"GOOGLE_CLIENT_ID": "  ", "GOOGLE_CLIENT_SECRET": ""}
        )


def test_environment_wins_over_secrets_file(tmp_path: Path):
    secrets_path = tmp_path / "client_secret.json"
    secrets_path.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "file-client-id",
                    "client_secret": "file-client-secret",
                }
            }
        ),
        encoding="utf-8",
    )
    client_id, client_secret = load_google_oauth_client(
        {
            "GOOGLE_CLIENT_ID": "env-client-id",
            "GOOGLE_CLIENT_SECRET": "env-client-secret",
            "GOOGLE_CLIENT_SECRETS_FILE": str(secrets_path),
        }
    )
    assert client_id == "env-client-id"
    assert client_secret == "env-client-secret"


@pytest.mark.parametrize(
    "payload",
    [
        {"installed": {"client_id": "id-from-file", "client_secret": "secret-from-file"}},
        {"web": {"client_id": "id-from-file", "client_secret": "secret-from-file"}},
        {"client_id": "id-from-file", "client_secret": "secret-from-file"},
    ],
)
def test_loads_client_from_secrets_file(tmp_path: Path, payload: dict):
    secrets_path = tmp_path / "client_secret.json"
    secrets_path.write_text(json.dumps(payload), encoding="utf-8")
    client_id, client_secret = load_google_oauth_client(
        {"GOOGLE_CLIENT_SECRETS_FILE": str(secrets_path)}
    )
    assert client_id == "id-from-file"
    assert client_secret == "secret-from-file"


def test_missing_secrets_file_is_reported(tmp_path: Path):
    missing = tmp_path / "missing.json"
    with pytest.raises(GoogleOAuthConfigError, match="does not exist"):
        load_google_oauth_client({"GOOGLE_CLIENT_SECRETS_FILE": str(missing)})


def test_invalid_secrets_file_does_not_echo_contents(tmp_path: Path):
    secrets_path = tmp_path / "client_secret.json"
    secrets_path.write_text('{"installed": {"client_secret": "not-json"', encoding="utf-8")
    with pytest.raises(GoogleOAuthConfigError) as exc_info:
        load_google_oauth_client({"GOOGLE_CLIENT_SECRETS_FILE": str(secrets_path)})
    message = str(exc_info.value)
    assert "not valid JSON" in message
    assert "not-json" not in message


def test_secrets_file_without_client_fields(tmp_path: Path):
    secrets_path = tmp_path / "client_secret.json"
    secrets_path.write_text(json.dumps({"installed": {"project_id": "demo"}}), encoding="utf-8")
    with pytest.raises(GoogleOAuthConfigError, match="missing client_id or client_secret"):
        load_google_oauth_client({"GOOGLE_CLIENT_SECRETS_FILE": str(secrets_path)})


def test_scripts_have_no_hardcoded_oauth_client():
    for name in SCRIPTS:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "GOCSPX-" not in text
        assert "apps.googleusercontent.com" not in text
        assert "load_google_oauth_client" in text


@pytest.mark.parametrize("script_name", SCRIPTS)
def test_scripts_fail_when_credentials_are_missing(script_name: str, tmp_path: Path):
    env = os.environ.copy()
    for key in CREDENTIAL_ENV:
        env.pop(key, None)
    env["PYTHONPATH"] = str(ROOT)

    result = subprocess.run(
        [sys.executable, str(ROOT / script_name)],
        cwd=tmp_path,
        env=env,
        input="\n",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 1
    assert "GOOGLE_CLIENT_ID" in combined
    assert "GOOGLE_CLIENT_SECRET" in combined
    assert "GOOGLE_CLIENT_SECRETS_FILE" in combined
    assert "GOCSPX-" not in combined
