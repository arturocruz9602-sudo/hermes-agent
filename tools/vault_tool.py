"""Bloque T (23 Jul 2026) -- personal encrypted credential vault.

A single symmetrically-encrypted file (``~/.hermes/boveda/entries.json.enc``)
for credentials Arturo explicitly asks Hermes to remember for him
(passwords, API keys, etc.). This is intentionally SEPARATE from the normal
memory system (MEMORY.md/USER.md/memoria_estructurada/semantic index) --
vault entries must never be injected into a prompt automatically, must
never be summarized, and must never appear in any of those stores.

Real, non-theoretical motivation: Hermes has repeated real API keys back
in its own chat responses twice in this project (4-jul, 20-jul incidents,
see ~/.hermes/docs history). The vault is designed assuming that failure
mode is real, not hypothetical -- see the module-level constraints below.

Encryption: age (the CLI tool) was the original spec, but is not installed
on this machine and installing it requires sudo, which this agent does not
run. Same security properties implemented in pure Python instead, using
the `cryptography` library (already an installed dependency):
  - scrypt to derive a 256-bit key from the passphrase + a random salt
    (salt is stored alongside the ciphertext -- it is not a secret).
  - AES-256-GCM for authenticated encryption. A wrong passphrase or a
    tampered file fails the GCM auth tag check -- this is what makes wrong
    passphrases fail "generically" without any partial/oracle behavior.

The passphrase is NEVER written to disk, .env, or config.yaml anywhere.
It exists only in Arturo's head and whatever he types when using the
vault -- this module never persists it in memory beyond the single
decrypt/encrypt call it's needed for.

KNOWN, ACCEPTED RESIDUAL EXPOSURE (documented explicitly, not hidden):
the passphrase and the credential value Arturo types DO flow through the
normal Telegram message -> state.db message-logging path like any other
message, because that is the only channel this conversational interface
has. This module (T.4) redacts those turns from the RAW layer export
(~/.hermes/scripts/raw_layer_export.py output) and T.6 adds an outbound
scanner so Hermes never echoes a vault value back in its own response,
but state.db itself (the live operational database) still contains the
plaintext turn, the same category of residual risk already accepted for
the 4-jul/20-jul incidents in OT-0.5. This is an inherent limit of a
chat-based interface, not something this module can fully close.
"""

from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from tools.registry import registry

_SALT_LEN = 16
_NONCE_LEN = 12
_KEY_LEN = 32  # AES-256

# scrypt cost parameters -- deliberately expensive (real-world guidance,
# ~2025-era interactive-use recommendation) since this key derivation runs
# once per vault operation, not in a hot loop.
_SCRYPT_N = 2**17
_SCRYPT_R = 8
_SCRYPT_P = 1


def _vault_dir() -> Path:
    home = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
    return Path(home) / "boveda"


def _vault_path() -> Path:
    return _vault_dir() / "entries.json.enc"


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=_KEY_LEN, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return kdf.derive(passphrase.encode("utf-8"))


def _encrypt(plaintext: bytes, passphrase: str) -> Dict[str, str]:
    salt = os.urandom(_SALT_LEN)
    nonce = os.urandom(_NONCE_LEN)
    key = _derive_key(passphrase, salt)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    return {
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }


class VaultAuthError(Exception):
    """Wrong passphrase or a tampered/corrupt vault file. Deliberately
    generic -- callers must not distinguish "wrong passphrase" from
    "corrupt file" in what gets sent back to the user (no oracle)."""


def _decrypt(envelope: Dict[str, str], passphrase: str) -> bytes:
    try:
        salt = base64.b64decode(envelope["salt"])
        nonce = base64.b64decode(envelope["nonce"])
        ciphertext = base64.b64decode(envelope["ciphertext"])
        key = _derive_key(passphrase, salt)
        return AESGCM(key).decrypt(nonce, ciphertext, None)
    except Exception as exc:
        raise VaultAuthError("wrong passphrase or corrupt vault") from exc


def _load_entries(passphrase: str) -> List[Dict[str, Any]]:
    path = _vault_path()
    if not path.exists():
        return []
    envelope = json.loads(path.read_text(encoding="utf-8"))
    plaintext = _decrypt(envelope, passphrase)
    try:
        data = json.loads(plaintext.decode("utf-8"))
    finally:
        # Best-effort scrub of the local plaintext bytes/str references.
        # CPython strings/bytes are not guaranteed erasable, but we drop
        # every reference immediately rather than holding onto them.
        del plaintext
    if not isinstance(data, list):
        raise VaultAuthError("corrupt vault contents")
    return data


def _save_entries(entries: List[Dict[str, Any]], passphrase: str) -> None:
    vault_dir = _vault_dir()
    vault_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(vault_dir, 0o700)
    except OSError:
        pass
    plaintext = json.dumps(entries, ensure_ascii=False).encode("utf-8")
    envelope = _encrypt(plaintext, passphrase)
    del plaintext
    path = _vault_path()
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(envelope), encoding="utf-8")
    try:
        os.chmod(tmp_path, 0o600)
    except OSError:
        pass
    tmp_path.replace(path)


def vault_save(
    servicio: str,
    valor: str,
    passphrase: str,
    notas: str = "",
) -> Dict[str, Any]:
    """T.2: add or overwrite one vault entry. Never returns ``valor``."""
    if not servicio or not valor or not passphrase:
        return {"success": False, "error": "servicio, valor y passphrase son obligatorios."}
    try:
        entries = _load_entries(passphrase)
    except VaultAuthError:
        return {"success": False, "error": "passphrase incorrecta o bóveda dañada."}

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    replaced = False
    for entry in entries:
        if entry.get("servicio") == servicio:
            entry["valor"] = valor
            entry["notas"] = notas
            entry["fecha_agregado"] = now
            replaced = True
            break
    if not replaced:
        entries.append({
            "servicio": servicio,
            "valor": valor,
            "fecha_agregado": now,
            "notas": notas,
        })

    _save_entries(entries, passphrase)
    del entries  # drop the decrypted list reference as soon as we're done
    return {
        "success": True,
        "message": f"Guardado en la bóveda: {servicio}." + (" (reemplazó una entrada existente.)" if replaced else ""),
    }


def vault_get(servicio: str, passphrase: str) -> Dict[str, Any]:
    """T.3: retrieve exactly one entry. Generic failure on bad passphrase."""
    if not servicio or not passphrase:
        return {"success": False, "error": "servicio y passphrase son obligatorios."}
    try:
        entries = _load_entries(passphrase)
    except VaultAuthError:
        return {"success": False, "error": "passphrase incorrecta o bóveda dañada."}

    match = next((e for e in entries if e.get("servicio") == servicio), None)
    del entries
    if match is None:
        return {"success": False, "error": f"No hay ninguna entrada guardada para '{servicio}'."}
    return {
        "success": True,
        "servicio": match.get("servicio"),
        "valor": match.get("valor"),
        "fecha_agregado": match.get("fecha_agregado"),
        "notas": match.get("notas", ""),
    }


def vault_list_services(passphrase: str) -> Dict[str, Any]:
    """List only the service NAMES (never values) -- lets Arturo ask "qué
    tengo guardado" without re-exposing any credential."""
    try:
        entries = _load_entries(passphrase)
    except VaultAuthError:
        return {"success": False, "error": "passphrase incorrecta o bóveda dañada."}
    services = [{"servicio": e.get("servicio"), "fecha_agregado": e.get("fecha_agregado")} for e in entries]
    del entries
    return {"success": True, "entries": services}


def check_vault_requirements() -> bool:
    """No external requirements beyond the `cryptography` package, which
    is a hard import at module load time -- if this module imported
    successfully, the requirement is met."""
    return True


def vault_tool(
    action: str = "",
    servicio: str = "",
    valor: str = "",
    passphrase: str = "",
    notas: str = "",
) -> str:
    """Single entry point matching the memory_tool dispatch convention."""
    if action == "save":
        result = vault_save(servicio, valor, passphrase, notas)
    elif action == "get":
        result = vault_get(servicio, passphrase)
    elif action == "list":
        result = vault_list_services(passphrase)
    else:
        result = {"success": False, "error": f"Unknown action '{action}'. Use: save, get, list"}
    return json.dumps(result, ensure_ascii=False)


# =============================================================================
# OpenAI Function-Calling Schema
# =============================================================================

VAULT_SCHEMA = {
    "name": "vault",
    "description": (
        "Personal encrypted credential vault, SEPARATE from normal memory. Use ONLY "
        "when Arturo EXPLICITLY asks to save or retrieve a password/API key/credential "
        "(e.g. 'guarda mi contraseña de X', 'dame mi API de Y'). NEVER save credentials "
        "here via the 'memory' tool, and NEVER put credentials in a normal chat response.\n\n"
        "Requires a passphrase Arturo types each time -- it is never stored anywhere. "
        "IMPORTANT: there is ONE master passphrase for the ENTIRE vault (all entries "
        "share it), not one per entry -- the whole file is a single encrypted blob. "
        "If this is the first entry ever saved, whatever passphrase Arturo gives now "
        "BECOMES the master passphrase for everything saved later too -- say so "
        "explicitly before saving the first entry. If a save/get fails with 'passphrase "
        "incorrecta o bóveda dañada' and entries already exist, the most likely cause is "
        "Arturo typed a DIFFERENT passphrase than the one the vault was created with -- "
        "you may say that plainly and ask him to retry, but do NOT retry the identical "
        "call yourself, and do NOT imply the vault is corrupted.\n\n"
        "If Arturo hasn't given a passphrase in this turn, ASK for it first (as its own "
        "message) before calling this tool -- do not guess or reuse an old one.\n\n"
        "On 'get': after receiving the result, deliver the value plainly ONCE. Do not "
        "repeat it again in later turns, and do not summarize/log it elsewhere.\n"
        "On 'save': confirm success WITHOUT repeating the value back.\n\n"
        "HARD RULE on wrong passphrase (no exceptions): relay ONLY the generic failure "
        "string exactly as the tool returned it. NEVER state, confirm, spell out, or "
        "hint at what the correct passphrase is or how it differs from what was typed "
        "-- not even if you can see the correct one earlier in this same conversation's "
        "history (e.g. from when it was first set). Recalling it from your own context "
        "and repeating it back defeats the entire point of gating retrieval on the "
        "passphrase -- treat your own conversation memory of a passphrase as something "
        "you must never volunteer, only use silently to call this tool when Arturo "
        "supplies the correct one himself. If he mistyped it, just say the generic "
        "failure and ask him to try again -- never confirm or deny what he guessed."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["save", "get", "list"],
                "description": "'save' to store/overwrite a credential, 'get' to retrieve one, 'list' to see saved service names only (never values).",
            },
            "servicio": {
                "type": "string",
                "description": "Short service/account name, e.g. 'gmail', 'groq_api'. Required for save/get.",
            },
            "valor": {
                "type": "string",
                "description": "The credential value to store. Required for 'save' only -- never send this for 'get'.",
            },
            "passphrase": {
                "type": "string",
                "description": "The passphrase Arturo just typed this turn. Required for every action.",
            },
            "notas": {
                "type": "string",
                "description": "Optional free-text note about this credential (save only).",
            },
        },
        "required": ["action", "passphrase"],
    },
}


registry.register(
    name="vault",
    toolset="vault",
    schema=VAULT_SCHEMA,
    handler=lambda args, **kw: vault_tool(
        action=args.get("action", ""),
        servicio=args.get("servicio", ""),
        valor=args.get("valor", ""),
        passphrase=args.get("passphrase", ""),
        notas=args.get("notas", ""),
    ),
    check_fn=check_vault_requirements,
    emoji="🔐",
)
