from pathlib import Path
import json, base64
from nacl.signing import VerifyKey
from datetime import date
import requests
from platformdirs import user_data_dir

LICENSE_URL = "https://script.google.com/macros/s/AKfycbxxm5Bj5FMil_2ZiDga-2n4sEaVUKDLGmUc38a7QQAxwOg4MoKWi-_52VXsy8ek6orn/exec"

def activate(key):
    try:
        r = requests.post(LICENSE_URL, json={"key": key}, timeout=10)
    except requests.RequestException:
        return False, "Ingen forbindelse"
    try:
        data = r.json()
        return data["ok"], data.get("msg", "")
    except (ValueError, KeyError):
        return False, "Uventet svar fra serveren"


PUBLIC_KEY = b"\x9a1\xe8\r\xc2;\x90\xe4\xaf\xb87\xd2\xf3`s\xe1\xf8r\xf9\xb1D\x9f\x8a\xf67s(.\x90#\xd0t"




def check_license(license_key: str):
    try:
        raw = base64.b64decode(license_key)
        signature, payload = raw[:64], raw[64:]
        VerifyKey(PUBLIC_KEY).verify(payload, signature)
        data = json.loads(payload)
    except Exception:
        return False, "Ugyldig licens"

    try:
        expires = date.fromisoformat(str(data["expires"])[:10])
    except Exception:
        return False, "Ugyldig udløbsdato"

    if expires < date.today():
        return False, "Licens udløbet"

    return True, data


CONFIG_DIR = Path(user_data_dir("fihsih calc", appauthor=False))
CONFIG_FILE = CONFIG_DIR / "license.json"


def save_activation(license_key: str, data: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump({"key": license_key, "data": data}, f)


def load_activation():
    if not CONFIG_FILE.exists():
        return None
    with open(CONFIG_FILE) as f:
        return json.load(f)


def start_check():
    # offline only: the signed key and its expiry date are checked locally, so the app starts without internet
    try:
        loaded = load_activation()
        if not loaded:
            return False
        licensed, _ = check_license(loaded["key"])
        return licensed
    except Exception:
        return False
