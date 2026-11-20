"""Ownership and hash protocol for generator-managed files (see references/setup.md, section "Ownership record").

File: .project/specs/website.managed.json (deterministic JSON: sorted keys, 2 spaces, final newline)

    {
      "version": 1,
      "project_files": {                      # files outside any site that setup wrote, keyed by repo-relative path
        ".project/specs/website.schema.json": {"sha256": "<hex>", "template_version": "static-1"}
      },
      "sites": {
        "<site-id>": {
          "mode": "created" | "adopted",      # adopted sites own no site file
          "type": "astro-static",
          "template_version": "static-1",
          "files": {"<path relative to the site folder>": "<sha256 hex of the bytes setup wrote>"}
        }
      }
    }

Validation (`validate`, run by `load` before any value is used): `version` is 1; every site has `mode` (created|adopted),
non-empty string `type` and `template_version`, and a `files` object (empty for adopted sites); every project file has
`sha256` and `template_version`; every hash is 64 lowercase hex characters; every path (project file or site file) is
relative with no `..`, `.`, empty segment, backslash, drive letter or NUL; site keys are site IDs (the manifest `name`). An invalid record
stops the run with a structured `invalid` result; the record and the project stay unchanged.

Rules: a file is generator-managed only if it is listed here. A file without an entry is foreign, even when its
content looks like the template. `setup verify` never changes this file. Hashes are written only together with
the file they describe (same transaction).
"""
import hashlib
import json
import re
from pathlib import Path

from errors import Stop

MANAGED = ".project/specs/website.managed.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def empty() -> dict:
    return {"version": 1, "project_files": {}, "sites": {}}


HEX_RE = re.compile(r"^[0-9a-f]{64}$")
SITE_ID_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?$")
SEGMENT_RE = re.compile(r"^[A-Za-z0-9._@+ ~-]+$")


def _path_problem(value) -> str:
    """Why `value` is not an acceptable relative path (None if it is). Checked before the path is ever used."""
    if not isinstance(value, str) or not value:
        return "must be a non-empty string"
    if value.startswith("/") or "\\" in value or "\0" in value or re.match(r"^[A-Za-z]:", value):
        return "must be relative (no leading '/', drive letter or backslash)"
    for part in value.split("/"):
        if part in ("", ".", ".."):
            return f"must not contain '{part or 'an empty segment'}'"
        if not SEGMENT_RE.match(part):
            return "contains unsupported characters"
    return None


def validate(data) -> list:
    """All problems of a parsed record (empty list = valid). Field by field, so one message names the exact place."""
    if not isinstance(data, dict):
        return ["the record must be a JSON object"]
    out = []
    if data.get("version") != 1 or isinstance(data.get("version"), bool):
        out.append("version must be 1")
    files = data.get("project_files")
    if not isinstance(files, dict):
        out.append("project_files must be an object")
    else:
        for rel, entry in files.items():
            bad = _path_problem(rel)
            if bad:
                out.append(f"project_files key {rel!r}: {bad}")
            if not isinstance(entry, dict):
                out.append(f"project_files[{rel!r}] must be an object")
                continue
            if not (isinstance(entry.get("sha256"), str) and HEX_RE.match(entry["sha256"])):
                out.append(f"project_files[{rel!r}].sha256 must be 64 lowercase hex characters")
            if not (isinstance(entry.get("template_version"), str) and entry["template_version"]):
                out.append(f"project_files[{rel!r}].template_version must be a non-empty string")
    sites = data.get("sites")
    if not isinstance(sites, dict):
        out.append("sites must be an object")
    else:
        for domain, entry in sites.items():
            if not (isinstance(domain, str) and SITE_ID_RE.match(domain)):
                out.append(f"sites key {domain!r} is not a site ID")
            if not isinstance(entry, dict):
                out.append(f"sites[{domain!r}] must be an object")
                continue
            if entry.get("mode") not in ("created", "adopted"):
                out.append(f"sites[{domain!r}].mode must be 'created' or 'adopted'")
            for key in ("type", "template_version"):
                if not (isinstance(entry.get(key), str) and entry[key]):
                    out.append(f"sites[{domain!r}].{key} is required and must be a non-empty string")
            tracked = entry.get("files")
            if not isinstance(tracked, dict):
                out.append(f"sites[{domain!r}].files must be an object")
                continue
            if entry.get("mode") == "adopted" and tracked:
                out.append(f"sites[{domain!r}]: an adopted site owns no files")
            for rel, digest in tracked.items():
                bad = _path_problem(rel)
                if bad:
                    out.append(f"sites[{domain!r}].files key {rel!r}: {bad}")
                if not (isinstance(digest, str) and HEX_RE.match(digest)):
                    out.append(f"sites[{domain!r}].files[{rel!r}] must be a sha256 of 64 lowercase hex characters")
    return out


def load(file: Path) -> dict:
    """Missing file = empty record. A file that is not a valid record stops (it is never overwritten)."""
    if not file.exists():
        return empty()
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as error:
        raise Stop(f"ownership record {file} is not valid JSON ({error}); not overwritten")
    problems = validate(data)
    if problems:
        shown = "\n  ".join(problems[:10]) + (f"\n  ... and {len(problems) - 10} more" if len(problems) > 10 else "")
        raise Stop(f"{file} is not a valid ownership record (version 1); not overwritten:\n  {shown}")
    return data


def dumps(record: dict) -> bytes:
    return (json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
