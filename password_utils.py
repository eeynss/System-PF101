import hashlib
import hmac
import secrets

# Password helpers for the login system.
# Hash = a one-way scrambled version of the password. The database never stores the real password.
# Salt = a random value mixed into each password, so two equal passwords get different hashes.
PASSWORD_ITERATIONS = 120000


def new_salt():
    return secrets.token_hex(16)


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt),
        PASSWORD_ITERATIONS
    ).hex()


def password_matches(password, salt, saved_hash):
    # compare_digest compares safely (same speed whether the first letter or the last one is wrong).
    return hmac.compare_digest(hash_password(password, salt), saved_hash)
