"""Encrypted vault: everything FirstVisit keeps lives in one file, encrypted at rest.

Key: scrypt(passphrase, random salt). Cipher: AES-256-GCM. Nothing is written to
disk in plaintext. The key exists only in memory while the vault is unlocked.

File layout: b"FVS1" | salt(16) | nonce(12) | ciphertext+tag
"""
import json
import os
import threading
import time

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"FVS1"
LEDGER_CAP = 2000
COST_KEYS = ["er", "urgent_care", "primary_care", "campus_health", "telehealth"]


class VaultError(Exception):
    pass


def _derive(passphrase, salt):
    return Scrypt(salt=salt, length=32, n=2 ** 15, r=8, p=1).derive(passphrase.encode())


def empty_profile():
    return {
        # About you: never leaves this laptop
        "full_name": "", "date_of_birth": "", "language": "English",
        "conditions": [], "medications": [], "allergies": [],
        # Where you are: city/state/ZIP are sent with place searches (by design, shown before sending)
        "city": "", "state": "", "zip": "",
        # Your insurance: member and group numbers never leave
        "insurer": "", "plan_name": "", "member_id": "", "group_number": "",
        "share_insurer": True,      # send the insurer's name with place searches
        "costs": {k: None for k in COST_KEYS},   # copays you copied from your card / plan summary
        "deductible": None, "coinsurance_pct": None, "oop_max": None,
        "campus_clinic": "", "campus_phone": "", "campus_hours": "",
        "nurse_line": "",
    }


def empty_data():
    return {
        "version": 1,
        "created": time.time(),
        "profile": empty_profile(),
        "cases": {},         # id -> what's wrong, triage, places, visit prep
        "bills": {},         # id -> pasted bill / EOB and its reading
        "ledger": [],        # every outbound request (sent, blocked or failed)
        "local_calls": 0,    # calls to the on-device model
    }


class Store:
    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()
        self._key = None
        self._salt = None
        self.data = None
        self.last_activity = time.time()

    # ---- lifecycle ----
    def exists(self):
        return self.path.exists()

    @property
    def unlocked(self):
        return self._key is not None

    def create(self, passphrase):
        if len(passphrase) < 8:
            raise VaultError("Passphrase must be at least 8 characters")
        if self.exists():
            raise VaultError("A vault already exists. Unlock it or delete it first.")
        with self.lock:
            self._salt = os.urandom(16)
            self._key = _derive(passphrase, self._salt)
            self.data = empty_data()
            self.save()

    def unlock(self, passphrase):
        if not self.exists():
            raise VaultError("No vault yet. Create one first.")
        raw = self.path.read_bytes()
        if raw[:4] != MAGIC:
            raise VaultError("Vault file is not recognised")
        salt, nonce, ct = raw[4:20], raw[20:32], raw[32:]
        key = _derive(passphrase, salt)
        try:
            plain = AESGCM(key).decrypt(nonce, ct, MAGIC)
        except InvalidTag:
            raise VaultError("Wrong passphrase")
        with self.lock:
            self._salt, self._key = salt, key
            self.data = json.loads(plain)
            self.touch()

    def lock_vault(self):
        with self.lock:
            if self.unlocked:
                self.save()
            self._key = None
            self.data = None

    def wipe(self):
        with self.lock:
            self._key = None
            self.data = None
            if self.exists():
                self.path.unlink()

    # ---- persistence ----
    def save(self):
        with self.lock:
            if not self.unlocked:
                raise VaultError("Vault is locked")
            nonce = os.urandom(12)
            ct = AESGCM(self._key).encrypt(nonce, json.dumps(self.data).encode(), MAGIC)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(MAGIC + self._salt + nonce + ct)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)

    def require(self):
        if not self.unlocked:
            raise VaultError("Vault is locked")
        return self.data

    def touch(self):
        self.last_activity = time.time()

    # ---- ledger ----
    def add_ledger(self, entry):
        with self.lock:
            if not self.unlocked:
                return
            self.data["ledger"].append(entry)
            if len(self.data["ledger"]) > LEDGER_CAP:
                self.data["ledger"] = self.data["ledger"][-LEDGER_CAP:]
            self.save()

    def count_local_call(self):
        with self.lock:
            if self.unlocked:
                self.data["local_calls"] = self.data.get("local_calls", 0) + 1
