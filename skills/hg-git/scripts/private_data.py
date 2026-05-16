#!/usr/bin/env python3
"""Personal private-data sync helper for hg-git.

This tool keeps encryption/decryption behavior in the hg-git skill instead of
duplicating scripts in every private repository. Repositories only provide a
.hg-git-private-data.json config file.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from fnmatch import fnmatch
import getpass
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
except ImportError as exc:  # pragma: no cover - operational dependency check
    raise SystemExit(
        "Missing Python package 'cryptography'. Install it for the active "
        "Python 3 environment before using hg-git private-data encryption."
    ) from exc


MAGIC = b"HGPRIV1\n"
SALT = b"SevenDay-Private"
KDF_ITERATIONS = 250_000
NONCE_SIZE = 12


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def output(cmd: list[str], cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def repo_root(path: Path) -> Path:
    try:
        return Path(output(["git", "rev-parse", "--show-toplevel"], path))
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Not inside a git repository: {path}") from exc


def load_config(root: Path) -> dict:
    config_path = root / ".hg-git-private-data.json"
    if not config_path.exists():
        raise SystemExit(f"Missing config: {config_path}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def expand_path(value: str, root: Path) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(value))
    path = Path(expanded)
    if not path.is_absolute():
        path = root / path
    return path


def expand_platform_path(value: str | dict, root: Path) -> Path:
    if isinstance(value, dict):
        system = platform.system().lower()
        if system == "darwin":
            selected = value.get("macos") or value.get("darwin")
        elif system == "windows":
            selected = value.get("windows")
        else:
            selected = value.get("linux")
        selected = selected or value.get("default")
        if not selected:
            raise SystemExit(f"No path configured for platform: {platform.system()}")
        value = selected
    return expand_path(value, root)


def password_from_config(config: dict, root: Path) -> str:
    password_file = config.get("password_file")
    if password_file:
        path = expand_platform_path(password_file, root)
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    return getpass.getpass("Encryption password: ")


def derive_key(password: str) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_file(plain_path: Path, encrypted_path: Path, password: str) -> None:
    if not plain_path.exists():
        raise SystemExit(f"Plain secret file not found: {plain_path}")
    key = derive_key(password)
    plaintext = plain_path.read_bytes()
    if encrypted_path.exists():
        blob = encrypted_path.read_bytes()
        if blob.startswith(MAGIC) and len(blob) > len(MAGIC) + NONCE_SIZE:
            nonce_start = len(MAGIC)
            nonce = blob[nonce_start : nonce_start + NONCE_SIZE]
            ciphertext = blob[nonce_start + NONCE_SIZE :]
            try:
                if AESGCM(key).decrypt(nonce, ciphertext, None) == plaintext:
                    return
            except Exception:
                pass
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    encrypted_path.parent.mkdir(parents=True, exist_ok=True)
    encrypted_path.write_bytes(MAGIC + nonce + ciphertext)


def decrypt_file(encrypted_path: Path, plain_path: Path, password: str) -> None:
    if not encrypted_path.exists():
        raise SystemExit(f"Encrypted secret file not found: {encrypted_path}")
    blob = encrypted_path.read_bytes()
    if not blob.startswith(MAGIC) or len(blob) <= len(MAGIC) + NONCE_SIZE:
        raise SystemExit(f"Invalid encrypted secret file: {encrypted_path}")
    nonce_start = len(MAGIC)
    nonce = blob[nonce_start : nonce_start + NONCE_SIZE]
    ciphertext = blob[nonce_start + NONCE_SIZE :]
    plaintext = AESGCM(derive_key(password)).decrypt(nonce, ciphertext, None)
    plain_path.parent.mkdir(parents=True, exist_ok=True)
    plain_path.write_bytes(plaintext)


def normalized_path_text(path: Path) -> str:
    return "/" + str(path).replace("\\", "/").strip("/") + "/"


def should_exclude(path: Path, root: Path, exclude_parts: list[str]) -> bool:
    full = normalized_path_text(path)
    rel = normalized_path_text(path.relative_to(root))
    for part in exclude_parts:
        normalized = part.replace("\\", "/").strip("/")
        if not normalized:
            continue
        if any(char in normalized for char in "*?["):
            full_text = full.strip("/")
            rel_text = rel.strip("/")
            if (
                fnmatch(full_text, normalized)
                or fnmatch(full_text, f"*/{normalized}")
                or fnmatch(rel_text, normalized)
                or fnmatch(rel_text, f"*/{normalized}")
            ):
                return True
            if "/" not in normalized:
                rel_parts = path.relative_to(root).parts
                if any(fnmatch(path_part, normalized) for path_part in rel_parts):
                    return True
        if "/" in normalized:
            needle = "/" + normalized
            if needle in full or needle in rel:
                return True
        else:
            needle = "/" + normalized + "/"
            suffix = "/" + normalized
            if needle in full or needle in rel or full.rstrip("/").endswith(suffix) or rel.rstrip("/").endswith(suffix):
                return True
    return False


def ensure_path_within(path: Path, parent: Path) -> None:
    resolved_path = path.resolve()
    resolved_parent = parent.resolve()
    if resolved_path != resolved_parent and resolved_parent not in resolved_path.parents:
        raise SystemExit(f"Refusing to write outside expected directory: {resolved_path}")


def sync_tree(source: Path, target: Path, exclude_parts: list[str], *, destructive_target: bool = True) -> None:
    if not source.exists():
        raise SystemExit(f"Sync source not found: {source}")
    if target.exists() and destructive_target:
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for item in source.rglob("*"):
        if should_exclude(item, source, exclude_parts):
            continue
        rel = item.relative_to(source)
        dest = target / rel
        if item.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(item, dest)
            except OSError:
                continue


def backup_target(target: Path) -> Path | None:
    if not target.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = Path.home() / ".hg-git" / "private-data-backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_path = backup_root / f"{target.name}-{timestamp}"
    shutil.move(str(target), str(backup_path))
    return backup_path


def encrypt_all(root: Path, config: dict) -> None:
    password = password_from_config(config, root)
    for entry in config.get("secrets", []):
        encrypt_file(expand_path(entry["plain"], root), expand_path(entry["encrypted"], root), password)


def decrypt_all(root: Path, config: dict) -> None:
    password = password_from_config(config, root)
    for entry in config.get("secrets", []):
        decrypt_file(expand_path(entry["encrypted"], root), expand_path(entry["plain"], root), password)


def plaintext_sync_entries(config: dict, name: str | None = None) -> list[dict]:
    entries = config.get("plaintext_sync", [])
    if name is None:
        return entries
    return [entry for entry in entries if entry.get("name") == name]


def sync_plaintext_targets(root: Path, config: dict, name: str | None = None) -> None:
    for entry in plaintext_sync_entries(config, name):
        source = expand_platform_path(entry["source"], root)
        target = expand_path(entry["repo_target"], root)
        print(f"Syncing {entry.get('name', 'plaintext')} from {source} to {target}")
        sync_tree(source, target, entry.get("exclude_path_parts", []))


def install_plaintext_targets(root: Path, config: dict, name: str | None = None) -> None:
    for entry in plaintext_sync_entries(config, name):
        source = expand_path(entry["repo_target"], root)
        target = expand_platform_path(entry["install_target"], root)
        ensure_path_within(target, Path.home())
        backup_path = backup_target(target)
        if backup_path:
            print(f"Backed up existing {entry.get('name', 'plaintext')} data to {backup_path}")
        print(f"Installing {entry.get('name', 'plaintext')} from {source} to {target}")
        sync_tree(source, target, entry.get("install_exclude_path_parts", []), destructive_target=False)


def sync_postman(root: Path, config: dict) -> None:
    sync_plaintext_targets(root, config, "postman")


def install_postman(root: Path, config: dict) -> None:
    install_plaintext_targets(root, config, "postman")


def command_pull_decrypt(root: Path, config: dict) -> None:
    run(["git", "pull", "--ff-only"], root)
    decrypt_all(root, config)
    install_plaintext_targets(root, config)


def command_encrypt_push(root: Path, config: dict, message: str, *, sync_plaintext: bool = False) -> None:
    if sync_plaintext:
        sync_plaintext_targets(root, config)
    encrypt_all(root, config)
    add_paths = config.get("git_add", ["."])
    run(["git", "add", *add_paths], root)
    staged = output(["git", "diff", "--cached", "--name-only"], root)
    if staged:
        run(["git", "commit", "-m", message], root)
    run(["git", "push"], root)


def command_push(root: Path, config: dict, message: str) -> None:
    run(["git", "pull", "--ff-only"], root)
    command_encrypt_push(root, config, message, sync_plaintext=True)


def command_pull(root: Path, config: dict) -> None:
    command_pull_decrypt(root, config)


def command_status(root: Path, config: dict) -> None:
    print(f"repo: {root}")
    print(f"secrets: {len(config.get('secrets', []))}")
    print(f"plaintext_sync: {len(config.get('plaintext_sync', []))}")
    run(["git", "status", "--short", "--branch"], root)


def command_doctor(root: Path, config: dict) -> int:
    problems = 0
    print(f"repo: {root}")
    print(f"platform: {platform.system()}")
    try:
        remote = output(["git", "remote", "get-url", "origin"], root)
    except subprocess.CalledProcessError:
        remote = ""
        problems += 1
    print(f"remote: {remote or 'missing'}")
    if "github.com/hugang20230316/" not in remote:
        print("problem: origin is not a verified hugang20230316 GitHub remote")
        problems += 1

    password_file = config.get("password_file")
    if password_file:
        path = expand_platform_path(password_file, root)
        print(f"password_file: {path}")
        if not path.exists():
            print(f"problem: missing password file: {path}")
            problems += 1
    else:
        print("password_file: not configured; helper will prompt interactively")

    for entry in config.get("secrets", []):
        encrypted = expand_path(entry["encrypted"], root)
        plain = expand_path(entry["plain"], root)
        print(f"secret encrypted: {encrypted} ({'ok' if encrypted.exists() else 'missing'})")
        print(f"secret plain: {plain} ({'present' if plain.exists() else 'missing until decrypt'})")
        if not encrypted.exists():
            problems += 1

    for entry in config.get("plaintext_sync", []):
        name = entry.get("name", "plaintext")
        source = expand_platform_path(entry["source"], root)
        repo_target = expand_path(entry["repo_target"], root)
        install_target = expand_platform_path(entry["install_target"], root)
        print(f"sync {name} source: {source} ({'present' if source.exists() else 'missing until app creates it'})")
        print(f"sync {name} repo_target: {repo_target} ({'present' if repo_target.exists() else 'missing'})")
        print(f"sync {name} install_target: {install_target}")
        if not repo_target.exists():
            problems += 1

    if problems:
        print(f"doctor: found {problems} problem(s)")
        return 1
    print("doctor: ok")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="hg-git private data helper")
    parser.add_argument(
        "command",
        choices=[
            "encrypt",
            "decrypt",
            "sync-postman",
            "install-postman",
            "pull-decrypt",
            "encrypt-push",
            "pull",
            "push",
            "doctor",
            "status",
        ],
    )
    parser.add_argument("--repo", default=".", help="repository path")
    parser.add_argument("--message", default="Sync personal private data", help="commit message for encrypt-push")
    args = parser.parse_args(argv)

    root = repo_root(Path(args.repo).resolve())
    config = load_config(root)

    if args.command == "encrypt":
        encrypt_all(root, config)
    elif args.command == "decrypt":
        decrypt_all(root, config)
    elif args.command == "sync-postman":
        sync_postman(root, config)
    elif args.command == "install-postman":
        install_postman(root, config)
    elif args.command == "pull-decrypt":
        command_pull_decrypt(root, config)
    elif args.command == "encrypt-push":
        command_encrypt_push(root, config, args.message)
    elif args.command == "pull":
        command_pull(root, config)
    elif args.command == "push":
        command_push(root, config, args.message)
    elif args.command == "doctor":
        return command_doctor(root, config)
    elif args.command == "status":
        command_status(root, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
