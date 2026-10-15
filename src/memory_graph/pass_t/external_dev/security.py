"""Bounded, non-extracting parser for the existing annotation return contract."""
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile
import zlib

MAX_ARCHIVE = 16 * 1024 * 1024
MAX_MEMBER = 2 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
MAX_MEMBERS = 256
MAX_RATIO = 200
HEX = re.compile(r'[0-9a-f]{64}\Z')
RESPONSE = re.compile(r'responses/PT2A_[0-9a-f]{16}_r[12]\.json\Z')
PROOF = re.compile(r'validated/[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\.json\Z')
ROOT_FILES = {'return_manifest.json', 'release_receipt.json', 'manifest.freeze.json'}


class Blocked(ValueError):
    """A hard integrity/preservation gate failed; never silently recover."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def strict_json(data):
    def pairs(rows):
        out = {}
        for key, value in rows:
            if key in out:
                raise Blocked('DUPLICATE_JSON_KEY: ' + key)
            out[key] = value
        return out
    def finite(value, depth=0):
        if depth > 48:
            raise Blocked('JSON_DEPTH_LIMIT')
        if isinstance(value, float) and not math.isfinite(value):
            raise Blocked('NONFINITE_JSON_NUMBER')
        if isinstance(value, dict):
            for v in value.values(): finite(v, depth+1)
        if isinstance(value, list):
            for v in value: finite(v, depth+1)
    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(Blocked('NONFINITE_JSON_NUMBER')))
        finite(value)
        if not isinstance(value, dict):
            raise Blocked('JSON_OBJECT_REQUIRED')
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise Blocked('INVALID_JSON: ' + str(error)) from error


def safe_relative(name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name or '\x00' in name:
        raise Blocked('UNSAFE_PATH')
    path = PurePosixPath(name)
    if path.is_absolute() or any(p in ('', '.', '..') for p in name.split('/')):
        raise Blocked('UNSAFE_PATH: ' + name)
    return name


def safe_path(base, name):
    safe_relative(name)
    base = Path(base).resolve()
    path = base / name
    current = path
    while current != base:
        if current.is_symlink() or (hasattr(current, 'is_junction') and current.is_junction()):
            raise Blocked('LINK_IN_OUTPUT_PATH')
        current = current.parent
    if not path.resolve().is_relative_to(base):
        raise Blocked('PATH_OUTSIDE_STORE')
    return path


def parse_archive(path, expected_sha):
    if not HEX.fullmatch(expected_sha):
        raise Blocked('EXPECTED_SHA256_REQUIRED')
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(MAX_ARCHIVE+1)
    except OSError as error:
        raise Blocked('SOURCE_ARCHIVE_INACCESSIBLE: ' + str(error)) from error
    if len(raw) > MAX_ARCHIVE:
        raise Blocked('ARCHIVE_SIZE_LIMIT')
    if digest(raw) != expected_sha:
        raise Blocked('ARCHIVE_SHA256_MISMATCH')
    import io
    members = {}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            if not 1 <= len(infos) <= MAX_MEMBERS:
                raise Blocked('MEMBER_COUNT_LIMIT')
            seen = set(); total = 0
            for info in infos:
                name = safe_relative(info.filename)
                if name.casefold() in seen:
                    raise Blocked('DUPLICATE_OR_CASE_COLLISION')
                seen.add(name.casefold())
                mode = info.external_attr >> 16
                if (info.is_dir() or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                        or info.external_attr & 0x400 or info.flag_bits & 1):
                    raise Blocked('UNSAFE_FILE_TYPE_OR_ENCRYPTED')
                if name not in ROOT_FILES and not RESPONSE.fullmatch(name) and not PROOF.fullmatch(name):
                    raise Blocked('UNAUTHORIZED_ARCHIVE_MEMBER: ' + name)
                total += info.file_size
                if (info.file_size > MAX_MEMBER or total > MAX_TOTAL
                        or info.file_size / max(1, info.compress_size) > MAX_RATIO):
                    raise Blocked('DECOMPRESSION_RESOURCE_LIMIT')
                with archive.open(info) as member:
                    data = member.read(MAX_MEMBER+1)
                    if len(data) != info.file_size or len(data) > MAX_MEMBER or member.read(1):
                        raise Blocked('MEMBER_SIZE_MISMATCH')
                members[name] = data  # full bounded read independently checks CRC
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, zlib.error) as error:
        raise Blocked('ZIP_CRC_OR_FORMAT_FAILURE: ' + str(error)) from error
    if not ROOT_FILES <= members.keys():
        raise Blocked('MISSING_MANDATORY_RETURN_FILE')
    values = {name: strict_json(data) for name, data in members.items()}
    manifest = values['return_manifest.json']
    if manifest.get('schema_version') != 'PASS_T_ANNOTATION_RETURN_V1':
        raise Blocked('UNSUPPORTED_RETURN_SCHEMA')
    files = manifest.get('files_sha256')
    if not isinstance(files, dict) or set(members) != ROOT_FILES | set(files):
        raise Blocked('EXACT_MEMBER_ALLOWLIST_MISMATCH')
    if not any(RESPONSE.fullmatch(n) for n in files):
        raise Blocked('NO_RETURNED_RESPONSES')
    for name, value in files.items():
        if (not (RESPONSE.fullmatch(name) or PROOF.fullmatch(name))
                or not isinstance(value, str) or not HEX.fullmatch(value) or digest(members[name]) != value):
            raise Blocked('DECLARED_MEMBER_HASH_MISMATCH: ' + name)
    if manifest.get('release_receipt_sha256') != digest(members['release_receipt.json']):
        raise Blocked('RELEASE_RECEIPT_HASH_MISMATCH')
    return {'sha256': expected_sha, 'members': members, 'values': values,
            'compressed_bytes': len(raw), 'uncompressed_bytes': sum(map(len, members.values())),
            'crc_verified': True, 'member_hashes_verified': len(files)}
