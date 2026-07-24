import base64
import hashlib
import hmac
import os

from nicegui import app

from db import get_user_by_email, get_user_by_id


SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64
MIN_PASSWORD_LENGTH = 10


def normalize_email(email):
    return (email or "").strip().lower()


def validate_password(password):
    if not isinstance(password, str):
        raise ValueError("Le mot de passe est invalide.")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Le mot de passe doit contenir au moins "
            f"{MIN_PASSWORD_LENGTH} caractères."
        )

    return password


def hash_password(password):
    validate_password(password)
    salt = os.urandom(16)
    derived_key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )

    return "$".join(
        [
            "scrypt",
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(derived_key).decode("ascii"),
        ]
    )


def verify_password(password, stored_hash):
    try:
        algorithm, n_text, r_text, p_text, salt_text, hash_text = (
            stored_hash.split("$", 5)
        )

        if algorithm != "scrypt":
            return False

        expected_hash = base64.urlsafe_b64decode(hash_text.encode("ascii"))
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        calculated_hash = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n_text),
            r=int(r_text),
            p=int(p_text),
            dklen=len(expected_hash),
        )
    except (ValueError, TypeError, AttributeError):
        return False

    return hmac.compare_digest(calculated_hash, expected_hash)


def set_authenticated_user(user_id):
    app.storage.user.clear()
    app.storage.user["authenticated"] = True
    app.storage.user["user_id"] = int(user_id)


def clear_session():
    app.storage.user.clear()


def get_current_user_id():
    if not app.storage.user.get("authenticated"):
        return None

    user_id = app.storage.user.get("user_id")

    try:
        return int(user_id)
    except (TypeError, ValueError):
        return None


def get_current_user():
    user_id = get_current_user_id()

    if user_id is None:
        return None

    user = get_user_by_id(user_id)

    if user is None or not user["is_active"]:
        clear_session()
        return None

    return user


def authenticate(email, password):
    user = get_user_by_email(normalize_email(email))

    if user is None or not user["is_active"]:
        return None

    if not verify_password(password or "", user["password_hash"]):
        return None

    set_authenticated_user(user["id"])
    return user
