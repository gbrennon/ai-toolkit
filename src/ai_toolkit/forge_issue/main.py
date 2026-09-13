import argparse
import json
import subprocess
import sys

from ai_toolkit.forge.api import (
    fj_api_url,
    fj_get,
    fj_post,
    gh_run,
    gh_run_single,
    is_github,
    parse_remote_ref,
)




def gh_list(owner: str, repo: str, state: str, label: str | None) -> list[dict]:
    args = [
        "api",
        f"/repos/{owner}/{repo}/issues",
        "--jq",
        ".[] | {number, title, state, user: .user.login, labels: [.labels[].name], created_at}",
        "--paginate",
        "-f",
        f"state={state}",
    ]
    if label:
        args += ["-f", f"labels={label}"]
    return gh_run(args)


def fj_list(
    host: str, owner: str, repo: str, state: str, label: str | None
) -> list[dict]:
    path = f"{owner}/{repo}/issues?state={state}"
    if label:
        path += f"&labels={label}"
    data = fj_get(fj_api_url(host, path))
    if not isinstance(data, list):
        return []
    return [
        {
            "number": i.get("number"),
            "title": i.get("title", ""),
            "state": i.get("state", ""),
            "user": i.get("user", {}).get("login", ""),
            "labels": [lb.get("name", "") for lb in i.get("labels", [])],
            "created_at": i.get("created_at", ""),
        }
        for i in data
    ]


def cmd_list(args: argparse.Namespace) -> None:
    host, owner, repo, _ = parse_remote_ref(f"{args.owner_repo}/1")
    state = args.state
    label = args.label

    issues = (
        gh_list(owner, repo, state, label)
        if is_github(host)
        else fj_list(host, owner, repo, state, label)
    )

    print(f"# Issues ({state})")
    for i in issues:
        labels = f" [{', '.join(i['labels'])}]" if i.get("labels") else ""
        print(f"- #{i['number']} [{i['state']}] {i['title']} by {i['user']}{labels}")
    if not issues:
        print("_No issues found._")




def gh_view(owner: str, repo: str, number: str) -> tuple[dict, list[dict]]:
    issue = gh_run_single(
        [
            "api",
            f"/repos/{owner}/{repo}/issues/{number}",
            "--jq",
            "{number, title, state, body, user: .user.login, labels: [.labels[].name], created_at}",
        ]
    )
    comments = gh_run(
        [
            "api",
            f"/repos/{owner}/{repo}/issues/{number}/comments",
            "--jq",
            ".[] | {id, user: .user.login, body, created_at}",
            "--paginate",
        ]
    )
    return issue, comments


def fj_view(host: str, owner: str, repo: str, number: str) -> tuple[dict, list[dict]]:
    data = fj_get(fj_api_url(host, f"{owner}/{repo}/issues/{number}"))
    if isinstance(data, list):
        print("Unexpected array", file=sys.stderr)
        sys.exit(1)
    issue = {
        "number": data.get("number"),
        "title": data.get("title", ""),
        "state": data.get("state", ""),
        "body": data.get("body", ""),
        "user": data.get("user", {}).get("login", ""),
        "labels": [lb.get("name", "") for lb in data.get("labels", [])],
        "created_at": data.get("created_at", ""),
    }
    raw = fj_get(fj_api_url(host, f"{owner}/{repo}/issues/{number}/comments"))
    comments = [
        {
            "id": c.get("id"),
            "user": c.get("user", {}).get("login", ""),
            "body": c.get("body", ""),
            "created_at": c.get("created_at", ""),
        }
        for c in (raw if isinstance(raw, list) else [])
    ]
    return issue, comments


def cmd_view(args: argparse.Namespace) -> None:
    host, owner, repo, number = parse_remote_ref(str(args.ref))
    issue, comments = (
        gh_view(owner, repo, number)
        if is_github(host)
        else fj_view(host, owner, repo, number)
    )

    labels = f" [{', '.join(issue['labels'])}]" if issue.get("labels") else ""
    print(f"# #{issue['number']} — {issue['title']}{labels}")
    print(f"**State:** {issue['state']}  ")
    print(f"**Author:** {issue['user']}  ")
    print()

    body = issue.get("body", "").strip()
    if body:
        print("## Body")
        print(body)
        print()

    print("## Comments")
    if comments:
        for c in comments:
            b = c.get("body", "").strip()
            if b:
                print(f"### {c['user']}")
                print(b)
                print()
    else:
        print("_No comments._")
        print()

    print(f"---\n_Issue #{issue['number']} with {len(comments)} comment(s)_")




def gh_create(owner: str, repo: str, title: str, body: str, labels: list[str]) -> dict:
    payload = json.dumps({"title": title, "body": body, "labels": labels})
    r = subprocess.run(
        [
            "gh",
            "api",
            f"/repos/{owner}/{repo}/issues",
            "--jq",
            "{number, title, html_url}",
            "--body",
            payload,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        print(f"gh error: {r.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(r.stdout)


def fj_create(
    host: str, owner: str, repo: str, title: str, body: str, labels: list[str]
) -> dict:
    return fj_post(
        fj_api_url(host, f"{owner}/{repo}/issues"),
        {"title": title, "body": body, "labels": labels},
    )


def cmd_create(args: argparse.Namespace) -> None:
    host, owner, repo, _ = parse_remote_ref(f"{args.owner_repo}/1")
    title = args.title
    body = sys.stdin.read().strip()
    labels = args.label or []

    result = (
        gh_create(owner, repo, title, body, labels)
        if is_github(host)
        else fj_create(host, owner, repo, title, body, labels)
    )

    print(f"Created #{result['number']} — {result['title']}")
    url = result.get("html_url", "")
    if url:
        print(url)




def gh_comment(owner: str, repo: str, number: str, body: str) -> dict:
    r = subprocess.run(
        [
            "gh",
            "api",
            f"/repos/{owner}/{repo}/issues/{number}/comments",
            "--jq",
            "{id, html_url}",
            "--body",
            json.dumps({"body": body}),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        print(f"gh error: {r.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(r.stdout)


def fj_comment(host: str, owner: str, repo: str, number: str, body: str) -> dict:
    return fj_post(
        fj_api_url(host, f"{owner}/{repo}/issues/{number}/comments"), {"body": body}
    )


def cmd_comment(args: argparse.Namespace) -> None:
    host, owner, repo, number = parse_remote_ref(str(args.ref))
    body = sys.stdin.read().strip()

    result = (
        gh_comment(owner, repo, number, body)
        if is_github(host)
        else fj_comment(host, owner, repo, number, body)
    )

    print(f"Comment added (id={result.get('id', '?')})")
    url = result.get("html_url", "")
    if url:
        print(url)




def gh_label_add(owner: str, repo: str, number: str, label: str) -> None:
    r = subprocess.run(
        [
            "gh",
            "api",
            f"/repos/{owner}/{repo}/issues/{number}/labels",
            "-f",
            f"labels[]={label}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        print(f"gh error: {r.stderr}", file=sys.stderr)
        sys.exit(1)


def gh_label_remove(owner: str, repo: str, number: str, label: str) -> None:
    r = subprocess.run(
        [
            "gh",
            "api",
            "-X",
            "DELETE",
            f"/repos/{owner}/{repo}/issues/{number}/labels/{label}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        print(f"gh error: {r.stderr}", file=sys.stderr)
        sys.exit(1)


def fj_label_add(host: str, owner: str, repo: str, number: str, label: str) -> None:
    fj_post(
        fj_api_url(host, f"{owner}/{repo}/issues/{number}/labels"), {"labels": [label]}
    )


def fj_label_remove(host: str, owner: str, repo: str, number: str, label: str) -> None:
    env_token = (
        __import__("os").environ.get("FORGEJO_TOKEN")
        or __import__("os").environ.get("FJ_TOKEN")
        or ""
    )
    headers = ["-H", "Content-Type: application/json"]
    if env_token:
        headers += ["-H", f"Authorization: token {env_token}"]
    url = fj_api_url(host, f"{owner}/{repo}/issues/{number}/labels/{label}")
    r = subprocess.run(
        ["curl", "-s", "-X", "DELETE", *headers, url],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        print(f"curl error: {r.stderr}", file=sys.stderr)
        sys.exit(1)


def cmd_label(args: argparse.Namespace) -> None:
    host, owner, repo, number = parse_remote_ref(str(args.ref))
    label = args.label_name
    add = args.action == "add"

    if is_github(host):
        gh_label_add(owner, repo, number, label) if add else gh_label_remove(
            owner, repo, number, label
        )
    else:
        if not host:
            print("Could not detect remote host.", file=sys.stderr)
            sys.exit(1)
        fj_label_add(host, owner, repo, number, label) if add else fj_label_remove(
            host, owner, repo, number, label
        )

    print(f"Label '{label}' {'added to' if add else 'removed from'} #{number}")




def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interact with issues on GitHub or Forgejo."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="List issues")
    p.add_argument("owner_repo", help="owner/repo")
    p.add_argument("--state", default="open", choices=["open", "closed", "all"])
    p.add_argument("--label", "-l", help="Filter by label")

    p = sub.add_parser("view", help="View issue + comments as markdown")
    p.add_argument("ref", help="URL or owner/repo/number")

    p = sub.add_parser("create", help="Create issue (body from stdin)")
    p.add_argument("owner_repo", help="owner/repo")
    p.add_argument("title", help="Issue title")
    p.add_argument("--label", "-l", action="append", dest="label", help="Labels")

    p = sub.add_parser("comment", help="Add comment (body from stdin)")
    p.add_argument("ref", help="URL or owner/repo/number")

    p = sub.add_parser("label", help="Add or remove a label")
    p.add_argument("ref", help="URL or owner/repo/number")
    p.add_argument("action", choices=["add", "remove"])
    p.add_argument("label_name", help="Label name")

    args = parser.parse_args()

    {
        "list": cmd_list,
        "view": cmd_view,
        "create": cmd_create,
        "comment": cmd_comment,
        "label": cmd_label,
    }[args.command](args)
