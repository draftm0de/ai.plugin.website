"""Deterministic input checks. No decisions are left to the caller."""
import json
import re
from pathlib import Path

from errors import Ask, Stop

DOMAIN_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$")


def load_config(skill_root: Path) -> dict:
    return json.loads((skill_root / "types.json").read_text(encoding="utf-8"))


def supported_types(config: dict) -> list:
    return sorted(config["types"])


def check_domain(domain):
    if not domain:
        raise Ask("Which domain should the site have (e.g. example.com)?")
    if not DOMAIN_RE.match(domain):
        raise Stop(f"'{domain}' is not a valid domain (lowercase, with a dot, e.g. example.com).")
    return domain


def check_type(site_type, config: dict):
    types = supported_types(config)
    if not site_type:
        raise Ask(f"Which --type? Supported: {', '.join(types)}.")
    if site_type not in config["types"]:
        raise Stop(f"Unsupported type '{site_type}'. Supported: {', '.join(types)}.")
    return site_type


def check_port(value):
    if value is not None and not 1024 <= value <= 65535:
        raise Stop(f"--port must be between 1024 and 65535: {value}")
    return value
