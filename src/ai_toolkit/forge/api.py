import json
import os
import re
import subprocess
import sys
from urllib.parse import urlparse


def get_main_remote() -> str | None:
    remote = os.environ.get("REMOTE")
    if remote:
        return remote

    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        remote = result.stdout.strip().split("/")[0]
        if remote:
            return remote

    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return "origin"

    result = subprocess.run(
        ["git", "remote"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        remotes = result.stdout.strip().splitlines()
        if remotes:
            return remotes[0]

    return None


def get_remote_url(remote: str | None = None) -> str | None:
    if remote is None:
        remote = get_main_remote()
    if remote is None:
        return None
    result = subprocess.run(
        ["git", "remote", "get-url", remote],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _extract_host(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.hostname:
        return parsed.hostname
    if ":" in url:
        return url.split(":")[0].split("@")[-1]
    return None


def get_remote_host() -> str | None:
    url = get_remote_url()
    if url is None:
        return None
    return _extract_host(url)


FORGE_PATTERNS: dict[str, list[re.Pattern]] = {
    "github": [re.compile(r"github\.", re.I)],
    "gitlab": [re.compile(r"gitlab[\-\.]", re.I), re.compile(r"\.gitlab\.", re.I)],
    "bitbucket": [re.compile(r"bitbucket\.", re.I)],
    "codeberg": [re.compile(r"codeberg\.", re.I)],
    "gitea": [re.compile(r"gitea\.", re.I)],
    "forgejo": [re.compile(r"forgejo\.", re.I)],
}


def classify_forge(host: str) -> str:
    for forge, patterns in FORGE_PATTERNS.items():
        for pat in patterns:
            if pat.search(host):
                return forge
    return "unknown"


def detect_forge() -> str | None:
    host = get_remote_host()
    if not host:
        return None
    return classify_forge(host)


def parse_remote_ref(
    ref: str, kinds: tuple[str, ...] = ("issues", "pull", "pulls")
) -> tuple[str, str, str, str]:
    parsed = urlparse(ref)
    if parsed.scheme and parsed.netloc:
        host = parsed.netloc
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 4 and parts[2] in kinds:
            return host, parts[0], parts[1], parts[3]
        raise ValueError(f"Unrecognized URL: {ref}")
    parts = ref.split("/")
    if len(parts) == 3:
        host = get_remote_host() or ""
        return host, parts[0], parts[1], parts[2]
    raise ValueError(f"Expected owner/repo/number or full URL, got: {ref}")


def is_github(host: str) -> bool:
    return "github.com" in host


def gh_run(args: list[str]) -> list[dict]:
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"gh error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    lines = result.stdout.strip().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def gh_run_single(args: list[str]) -> dict:
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"gh error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def gh_post(args: list[str], body: str) -> dict:
    result = subprocess.run(
        ["gh", *args, "--body", body],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"gh error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def gh_post_list(args: list[str], body: str) -> list[dict]:
    result = subprocess.run(
        ["gh", *args, "--body", body],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"gh error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    lines = result.stdout.strip().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def fj_api_url(host: str, path: str) -> str:
    return f"https://{host}/api/v1/repos/{path}"


def fj_get(url: str) -> list | dict:
    env_token = os.environ.get("FORGEJO_TOKEN") or os.environ.get("FJ_TOKEN") or ""
    headers = ["-H", f"Authorization: token {env_token}"] if env_token else []
    result = subprocess.run(
        ["curl", "-s", *headers, url],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = result.stderr.strip() or f"curl exit code {result.returncode}"
        print(f"curl error: {msg}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def fj_post(url: str, payload: dict) -> dict:
    env_token = os.environ.get("FORGEJO_TOKEN") or os.environ.get("FJ_TOKEN") or ""
    headers = ["-H", "Content-Type: application/json"]
    if env_token:
        headers += ["-H", f"Authorization: token {env_token}"]
    data = json.dumps(payload)
    result = subprocess.run(
        ["curl", "-s", "-X", "POST", *headers, "-d", data, url],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = result.stderr.strip() or f"curl exit code {result.returncode}"
        print(f"curl error: {msg}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def fj_patch(url: str, payload: dict) -> dict:
    env_token = os.environ.get("FORGEJO_TOKEN") or os.environ.get("FJ_TOKEN") or ""
    headers = ["-H", "Content-Type: application/json"]
    if env_token:
        headers += ["-H", f"Authorization: token {env_token}"]
    data = json.dumps(payload)
    result = subprocess.run(
        ["curl", "-s", "-X", "PATCH", *headers, "-d", data, url],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = result.stderr.strip() or f"curl exit code {result.returncode}"
        print(f"curl error: {msg}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)
