import base64
import json
from datetime import date, timedelta

import pytest
import requests
from nacl.signing import SigningKey

import license_manager


@pytest.fixture
def signing_key(monkeypatch):
    # sign test licenses with our own key pair instead of the real private key
    key = SigningKey.generate()
    monkeypatch.setattr(license_manager, "PUBLIC_KEY", bytes(key.verify_key))
    return key


def make_license(key, payload):
    data = json.dumps(payload).encode()
    return base64.b64encode(key.sign(data).signature + data).decode()


def days_from_today(n):
    return (date.today() + timedelta(days=n)).isoformat()


# --- check_license ---

def test_valid_license(signing_key):
    payload = {"expires": days_from_today(30), "name": "Test"}
    assert license_manager.check_license(make_license(signing_key, payload)) == (True, payload)


def test_license_is_valid_on_its_last_day(signing_key):
    ok, _ = license_manager.check_license(make_license(signing_key, {"expires": days_from_today(0)}))
    assert ok


def test_expiry_date_with_time(signing_key):
    ok, _ = license_manager.check_license(make_license(signing_key, {"expires": days_from_today(30) + "T10:00:00"}))
    assert ok


def test_expired_license(signing_key):
    key = make_license(signing_key, {"expires": days_from_today(-1)})
    assert license_manager.check_license(key) == (False, "Licens udløbet")


@pytest.mark.parametrize("payload", [{"expires": "nope"}, {"name": "no expiry"}, [1, 2]])
def test_bad_expiry_date(signing_key, payload):
    assert license_manager.check_license(make_license(signing_key, payload)) == (False, "Ugyldig udløbsdato")


@pytest.mark.parametrize("key", ["", "not base64!!", base64.b64encode(b"short").decode()])
def test_garbage_is_invalid(signing_key, key):
    assert license_manager.check_license(key) == (False, "Ugyldig licens")


def test_tampered_license_is_invalid(signing_key):
    raw = bytearray(base64.b64decode(make_license(signing_key, {"expires": days_from_today(30)})))
    raw[-3] ^= 1
    assert license_manager.check_license(base64.b64encode(bytes(raw)).decode()) == (False, "Ugyldig licens")


def test_license_signed_with_another_key_is_invalid(signing_key):
    key = make_license(SigningKey.generate(), {"expires": days_from_today(30)})
    assert license_manager.check_license(key) == (False, "Ugyldig licens")


def test_signed_text_that_is_not_json_is_invalid(signing_key):
    key = base64.b64encode(signing_key.sign(b"not json").signature + b"not json").decode()
    assert license_manager.check_license(key) == (False, "Ugyldig licens")


def test_real_public_key_rejects_a_self_made_license():
    key = make_license(SigningKey.generate(), {"expires": days_from_today(30)})
    assert license_manager.check_license(key) == (False, "Ugyldig licens")


# --- saved activation ---

@pytest.fixture
def config_in_tmp(tmp_path, monkeypatch):
    # never touch the real license.json
    monkeypatch.setattr(license_manager, "CONFIG_DIR", tmp_path / "data")
    monkeypatch.setattr(license_manager, "CONFIG_FILE", tmp_path / "data" / "license.json")
    return tmp_path / "data" / "license.json"


def test_save_and_load_activation(config_in_tmp):
    license_manager.save_activation("KEY", {"expires": "2099-01-01"})
    assert license_manager.load_activation() == {"key": "KEY", "data": {"expires": "2099-01-01"}}


def test_load_activation_without_file(config_in_tmp):
    assert license_manager.load_activation() is None


def test_start_check_with_valid_saved_license(config_in_tmp, signing_key):
    license_manager.save_activation(make_license(signing_key, {"expires": days_from_today(30)}), {})
    assert license_manager.start_check() is True


def test_start_check_with_expired_saved_license(config_in_tmp, signing_key):
    license_manager.save_activation(make_license(signing_key, {"expires": days_from_today(-1)}), {})
    assert license_manager.start_check() is False


def test_start_check_without_saved_license(config_in_tmp):
    assert license_manager.start_check() is False


@pytest.mark.parametrize("content", ["{not json", '{"no key": 1}'])
def test_start_check_with_broken_file(config_in_tmp, content):
    config_in_tmp.parent.mkdir()
    config_in_tmp.write_text(content)
    assert license_manager.start_check() is False


# --- activate (server is faked, no network) ---

class FakeResponse:
    def __init__(self, data):
        self.data = data

    def json(self):
        if self.data is None:
            raise ValueError("not json")
        return self.data


def answer(data):
    return lambda *args, **kwargs: FakeResponse(data)


@pytest.mark.parametrize("data, expected", [
    ({"ok": True, "msg": "Aktiveret"}, (True, "Aktiveret")),
    ({"ok": False, "msg": "Allerede brugt"}, (False, "Allerede brugt")),
    ({"ok": True}, (True, "")),
])
def test_activate(monkeypatch, data, expected):
    monkeypatch.setattr(requests, "post", answer(data))
    assert license_manager.activate("KEY") == expected


def test_activate_sends_the_key(monkeypatch):
    sent = {}

    def post(url, **kwargs):
        sent.update(url=url, json=kwargs["json"])
        return FakeResponse({"ok": True})

    monkeypatch.setattr(requests, "post", post)
    license_manager.activate("KEY")
    assert sent == {"url": license_manager.LICENSE_URL, "json": {"key": "KEY"}}


def test_activate_without_connection(monkeypatch):
    def post(*args, **kwargs):
        raise requests.ConnectionError

    monkeypatch.setattr(requests, "post", post)
    assert license_manager.activate("KEY") == (False, "Ingen forbindelse")


@pytest.mark.parametrize("data", [None, {"msg": "no ok field"}])
def test_activate_unexpected_answer(monkeypatch, data):
    monkeypatch.setattr(requests, "post", answer(data))
    assert license_manager.activate("KEY") == (False, "Uventet svar fra serveren")


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    old, new = tmp_path / "fihsih calc", tmp_path / "Carbon"
    monkeypatch.setattr(license_manager, "OLD_CONFIG_DIR", old)
    monkeypatch.setattr(license_manager, "CONFIG_DIR", new)
    return old, new


def test_migrate_moves_old_folder(dirs):
    old, new = dirs
    old.mkdir()
    (old / "license.json").write_text("{}")
    license_manager.migrate_old_config()
    assert not old.exists()
    assert (new / "license.json").read_text() == "{}"


def test_migrate_keeps_existing_new_folder(dirs):
    old, new = dirs
    old.mkdir()
    new.mkdir()
    (new / "license.json").write_text("new")
    license_manager.migrate_old_config()
    assert old.exists()
    assert (new / "license.json").read_text() == "new"


def test_migrate_without_old_folder(dirs):
    license_manager.migrate_old_config()
    assert not dirs[1].exists()
