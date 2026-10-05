from typing import TypedDict

import pytest

from ai_toolkit.agent_hook_pr_review.main import (
    DEFAULT_BACKOFF_SECONDS,
    PollOptions,
    poll_for_review,
)

pytestmark = pytest.mark.unit


class Review(TypedDict):
    id: int
    state: str
    body: str
    commit_id: str


def test_poll_for_review_increases_wait_between_empty_checks() -> None:
    responses: list[list[Review]] = [
        [],
        [],
        [{"id": 7, "state": "APPROVED", "body": "ok", "commit_id": "head"}],
    ]
    waits: list[float] = []
    notifications: list[Review] = []

    def fetch_reviews() -> list[Review]:
        return responses.pop(0)

    result = poll_for_review(
        fetch_reviews,
        waits.append,
        notifications.append,
        PollOptions(listen=True, expected_commit="head"),
    )

    assert result == {
        "id": 7,
        "state": "APPROVED",
        "body": "ok",
        "commit_id": "head",
    }
    assert waits == list(DEFAULT_BACKOFF_SECONDS[:2])
    assert notifications == [result]


def test_poll_for_review_caps_wait_at_final_backoff_interval() -> None:
    responses: list[list[Review]] = [[], [], []]
    waits: list[float] = []

    def fetch_reviews() -> list[Review]:
        if responses:
            return responses.pop(0)
        return [{"id": 8, "state": "CHANGES_REQUESTED", "body": "fix", "commit_id": "head"}]

    result = poll_for_review(
        fetch_reviews,
        waits.append,
        lambda _review: None,
        PollOptions(listen=True, intervals=(1.0, 2.0), expected_commit="head"),
    )

    assert result == {
        "id": 8,
        "state": "CHANGES_REQUESTED",
        "body": "fix",
        "commit_id": "head",
    }
    assert waits == [1.0, 2.0, 2.0]


def test_poll_for_review_checks_once_without_listen_mode() -> None:
    fetch_count = 0
    waits: list[float] = []

    def fetch_reviews() -> list[Review]:
        nonlocal fetch_count
        fetch_count += 1
        return []

    result = poll_for_review(
        fetch_reviews,
        waits.append,
        lambda _review: None,
        PollOptions(listen=False),
    )

    assert result is None
    assert fetch_count == 1
    assert waits == []


def test_poll_for_review_ignores_review_for_old_commit() -> None:
    responses: list[list[Review]] = [
        [{"id": 9, "state": "APPROVED", "body": "old", "commit_id": "old"}],
        [{"id": 10, "state": "APPROVED", "body": "new", "commit_id": "new"}],
    ]
    waits: list[float] = []

    def fetch_reviews() -> list[Review]:
        return responses.pop(0)

    result = poll_for_review(
        fetch_reviews,
        waits.append,
        lambda _review: None,
        PollOptions(listen=True, expected_commit="new", intervals=(1.0,)),
    )

    assert result == {
        "id": 10,
        "state": "APPROVED",
        "body": "new",
        "commit_id": "new",
    }
    assert waits == [1.0]
