#!/usr/bin/env python3
"""Read-only Fletes finance API helper for Lux/OpenClaw.

Loads the local API token from /root/.config/lux/secrets/finance-api.env by
default and never prints it. The helper only performs GET requests.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_ENV_PATH = Path("/root/.config/lux/secrets/finance-api.env")
DEFAULT_BASE_URL = "http://127.0.0.1/api/v1"
RESOURCES = ("snapshot", "summary", "jobs", "drivers", "vehicles", "leads", "settings")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_config(env_path: Path, base_url_arg: str | None) -> tuple[str, str]:
    load_env_file(env_path)
    token = os.environ.get("FINANCE_READ_API_KEY") or os.environ.get("MAIN_API_KEY")
    if not token:
        raise SystemExit(
            "Missing finance API token. Set FINANCE_READ_API_KEY in "
            f"{env_path} with chmod 600."
        )
    base_url = (
        base_url_arg
        or os.environ.get("FINANCE_API_BASE_URL")
        or os.environ.get("MAIN_API_BASE_URL")
        or DEFAULT_BASE_URL
    )
    return normalize_base_url(base_url), token


def normalize_base_url(value: str) -> str:
    base_url = value.rstrip("/")
    if base_url.endswith("/api/v1"):
        return base_url
    return f"{base_url}/api/v1"


def build_params(args: argparse.Namespace) -> dict[str, str]:
    params: dict[str, str] = {}
    if getattr(args, "from_date", None):
        params["from"] = args.from_date
    if getattr(args, "to_date", None):
        params["to"] = args.to_date
    if getattr(args, "status", None):
        params["status"] = args.status
    if getattr(args, "driver_id", None):
        params["driverId"] = args.driver_id
    return params


def api_get(base_url: str, token: str, resource: str, params: dict[str, str]) -> Any:
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v})
    url = f"{base_url}/finance/{resource}"
    if query:
        url = f"{url}?{query}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "x-api-key": token,
            "Accept": "application/json",
            "User-Agent": "lux-fletes-finance/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"Fletes finance API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Fletes finance API connection error: {exc}") from exc


def maybe_limit_payload(payload: Any, resource: str, limit: int | None) -> Any:
    if not limit or limit < 1:
        return payload
    if isinstance(payload, list):
        return payload[:limit]
    if not isinstance(payload, dict):
        return payload
    trimmed = dict(payload)
    for key in (resource, "items", "data", "results"):
        value = trimmed.get(key)
        if isinstance(value, list):
            trimmed[key] = value[:limit]
            trimmed.setdefault("_clientLimit", limit)
            break
    return trimmed


def print_json(payload: Any, compact: bool) -> None:
    if compact:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))


def command_check(args: argparse.Namespace) -> None:
    base_url, token = get_config(args.env, args.base_url)
    payload = api_get(base_url, token, "summary", {})
    summary = {
        "ok": True,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "baseUrl": base_url,
        "resource": "summary",
    }
    if isinstance(payload, dict):
        for key in ("currency", "hasSummary", "jobs", "completedJobs", "totalRevenue", "totalCosts", "profit"):
            if key in payload:
                summary[key] = payload[key]
    print_json(summary, args.compact)


def command_resource(args: argparse.Namespace) -> None:
    base_url, token = get_config(args.env, args.base_url)
    payload = api_get(base_url, token, args.resource, build_params(args))
    print_json(maybe_limit_payload(payload, args.resource, args.limit), args.compact)


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--from", dest="from_date", help="YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", help="YYYY-MM-DD")
    parser.add_argument("--status", help="Optional job status filter, e.g. DONE or DONE,PENDING")
    parser.add_argument("--driver-id", help="Optional driver id filter")
    parser.add_argument("--limit", type=int, help="Client-side list limit for large responses")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Fletes finance API helper")
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV_PATH, help="Path to env file")
    parser.add_argument("--base-url", help="Override base URL; accepts root URL or /api/v1 URL")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Validate credentials against finance summary")
    check.add_argument("--compact", action="store_true", help="Print compact JSON")

    get = sub.add_parser("get", help="Fetch one finance resource")
    get.add_argument("resource", choices=RESOURCES)
    add_common_args(get)

    for resource in RESOURCES:
        resource_parser = sub.add_parser(resource, help=f"Fetch finance {resource}")
        resource_parser.set_defaults(resource=resource)
        add_common_args(resource_parser)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "check":
        command_check(args)
    else:
        command_resource(args)


if __name__ == "__main__":
    main()
