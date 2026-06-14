from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

VALID_TARGETS = {"folder", "github-pages", "cloudflare"}


class ConfigError(Exception):
    """Raised when site.toml is missing required fields or has bad values."""


@dataclass
class SiteConfig:
    title: str
    url: str
    author: str
    description: str
    language: str = "en"


@dataclass
class BuildConfig:
    content_dir: str = "content"
    output_dir: str = "public"
    theme: str = "default"
    feed_limit: int = 20


@dataclass
class SecurityConfig:
    csp: str = "locked"
    referrer_policy: str = "no-referrer"
    sanitize: bool = True
    hsts: bool = True


@dataclass
class DeployConfig:
    target: str = "folder"


@dataclass
class Config:
    site: SiteConfig
    build: BuildConfig = field(default_factory=BuildConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    deploy: DeployConfig = field(default_factory=DeployConfig)


def _require(table: dict, key: str, where: str) -> object:
    if key not in table:
        raise ConfigError(f"[{where}] is missing required key '{key}'")
    return table[key]


def load_config(path: str | Path) -> Config:
    path = Path(path)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from exc

    site_raw = data.get("site")
    if not isinstance(site_raw, dict):
        raise ConfigError("missing required [site] table")
    site = SiteConfig(
        title=str(_require(site_raw, "title", "site")),
        url=str(_require(site_raw, "url", "site")),
        author=str(_require(site_raw, "author", "site")),
        description=str(_require(site_raw, "description", "site")),
        language=str(site_raw.get("language", "en")),
    )

    build_raw = data.get("build", {})
    feed_limit = int(build_raw.get("feed_limit", 20))
    if feed_limit < 0:
        raise ConfigError("[build] feed_limit must be zero or a positive integer")
    build = BuildConfig(
        content_dir=str(build_raw.get("content_dir", "content")),
        output_dir=str(build_raw.get("output_dir", "public")),
        theme=str(build_raw.get("theme", "default")),
        feed_limit=feed_limit,
    )

    sec_raw = data.get("security", {})
    security = SecurityConfig(
        csp=str(sec_raw.get("csp", "locked")),
        referrer_policy=str(sec_raw.get("referrer_policy", "no-referrer")),
        sanitize=bool(sec_raw.get("sanitize", True)),
        hsts=bool(sec_raw.get("hsts", True)),
    )

    deploy_raw = data.get("deploy", {})
    target = str(deploy_raw.get("target", "folder"))
    if target not in VALID_TARGETS:
        raise ConfigError(
            f"[deploy] target '{target}' must be one of {sorted(VALID_TARGETS)}"
        )
    deploy = DeployConfig(target=target)

    return Config(site=site, build=build, security=security, deploy=deploy)
