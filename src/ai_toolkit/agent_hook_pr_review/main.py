import argparse
import json
import shutil
import subprocess
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TypedDict

from ai_toolkit.forge.api import (
    fj_api_url,
    fj_get,
    gh_run,
    gh_run_single,
    is_github,
    parse_remote_ref,
)

DEFAULT_BACKOFF_SECONDS: tuple[float, ...] = (30.0, 60.0, 120.0, 240.0, 300.0)


@dataclass(frozen=True)
class PollOptions:
    listen: bool
    expected_commit: str | None = None
    intervals: tuple[float, ...] = DEFAULT_BACKOFF_SECONDS


class Review(TypedDict):
    id: int
    state: str
    body: str
    commit_id: str

def _latest_review(
    reviews: list[Review],
    expected_commit: str | None,
) -> Review | None:
    matching = [
        review
        for review in reviews
        if expected_commit is None or review.get("commit_id") == expected_commit
    ]
    if not matching:
        return None
    return matching[-1]


def poll_for_review(
    fetch_reviews: Callable[[], list[Review]],
    wait: Callable[[float], None],
    notify: Callable[[Review], None],
    options: PollOptions,
) -> Review | None:
    interval_index = 0
    while True:
        review = _latest_review(fetch_reviews(), options.expected_commit)
        if review is not None:
            notify(review)
            return review
        if not options.listen:
            return None
        interval = options.intervals[min(interval_index, len(options.intervals) - 1)]
        wait(interval)
        interval_index += 1


def _review_from_mapping(data: Mapping[str, object]) -> Review:
    raw_id = data.get("id", 0)
    review_id = raw_id if isinstance(raw_id, int) else 0
    return {
        "id": review_id,
        "state": str(data.get("state", "")),
        "body": str(data.get("body", "")),
        "commit_id": str(data.get("commit_id", "")),
    }


def _github_reviews(owner: str, repo: str, number: str) -> list[Review]:
    rows = gh_run(
        [
            "api",
            f"/repos/{owner}/{repo}/pulls/{number}/reviews",
            "--jq",
            ".[] | {id, state, body, commit_id}",
            "--paginate",
        ]
    )
    return [_review_from_mapping(row) for row in rows]


def _forgejo_reviews(host: str, owner: str, repo: str, number: str) -> list[Review]:
    data = fj_get(fj_api_url(host, f"{owner}/{repo}/pulls/{number}/reviews"))
    if not isinstance(data, list):
        return []
    return [
        _review_from_mapping(row)
        for row in data
        if isinstance(row, Mapping)
    ]


def _pull_request_head(reference: str) -> str:
    host, owner, repo, number = parse_remote_ref(reference, kinds=("pull", "pulls"))
    if is_github(host):
        head = gh_run_single(
            [
                "api",
                f"/repos/{owner}/{repo}/pulls/{number}",
                "--jq",
                ".head.sha",
            ]
        )
        return str(head)
    if not host:
        raise ValueError("Could not detect the forge host from the pull request reference")
    data = fj_get(fj_api_url(host, f"{owner}/{repo}/pulls/{number}"))
    if not isinstance(data, Mapping):
        return ""
    head = data.get("head")
    if not isinstance(head, Mapping):
        return ""
    return str(head.get("sha", ""))


def _fetch_reviews(reference: str) -> list[Review]:
    host, owner, repo, number = parse_remote_ref(reference, kinds=("pull", "pulls"))
    if is_github(host):
        return _github_reviews(owner, repo, number)
    if not host:
        raise ValueError("Could not detect the forge host from the pull request reference")
    return _forgejo_reviews(host, owner, repo, number)


def _notify_review(reference: str, review: Review) -> None:
    if shutil.which("notify-send") is None:
        return
    state = review.get("state", "").lower()
    message = f"{reference}: pull request review {state}"
    subprocess.run(["notify-send", "PR review available", message], check=False)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Poll for a pull request review")
    parser.add_argument("reference", help="PR URL or owner/repo/number")
    parser.add_argument(
        "--listen",
        action="store_true",
        help="Keep polling with incremental backoff until a review appears",
    )
    return parser.parse_args()


def main() -> int:
    arguments = _arguments()
    expected_commit = _pull_request_head(arguments.reference)
    review = poll_for_review(
        lambda: _fetch_reviews(arguments.reference),
        time.sleep,
        lambda item: _notify_review(arguments.reference, item),
        PollOptions(
            listen=arguments.listen,
            expected_commit=expected_commit,
        ),
    )
    if review is not None:
        print(json.dumps(review, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
