"""Per-user Claude rate-limit tests (Phase 21 cost guardrail).

The `claude_rate_limit` dependency is wired on every Claude-touching
endpoint. We test the helper itself (since exercising it through the
real endpoints would require mocking out the underlying AI services)
plus one route-level smoke test against the quiz-generate endpoint to
confirm the dependency is actually attached.
"""
from __future__ import annotations

import time
import uuid

import pytest

from app.api import deps
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def _reset_buckets():
    deps._reset_claude_buckets_for_tests()
    yield
    deps._reset_claude_buckets_for_tests()


def test_first_call_is_allowed():
    user_id = uuid.uuid4()
    assert deps._consume_claude_token(user_id) is True


def test_burst_up_to_rate_then_429():
    """Bucket starts at full capacity = rate. After `rate` calls in
    a single tick, the next call is rejected."""
    settings = get_settings()
    rate = settings.claude_requests_per_minute
    user_id = uuid.uuid4()
    for i in range(rate):
        assert deps._consume_claude_token(user_id) is True, f"call {i + 1} should pass"
    # Bucket should now be drained (or nearly so — the refill between
    # iterations is in microseconds at this rate).
    assert deps._consume_claude_token(user_id) is False


def test_bucket_refills_over_time():
    """After waiting > 60/rate seconds we get at least one token back."""
    settings = get_settings()
    rate = settings.claude_requests_per_minute
    user_id = uuid.uuid4()
    # Drain.
    for _ in range(rate):
        deps._consume_claude_token(user_id)
    assert deps._consume_claude_token(user_id) is False
    # Wait long enough for one token to drip back. At rate=20, that's 3s.
    # We only need a tiny fraction of a token, so 0.5s is plenty for a unit test.
    refill_time = 60.0 / rate + 0.1
    time.sleep(refill_time)
    assert deps._consume_claude_token(user_id) is True


def test_separate_users_have_separate_buckets():
    settings = get_settings()
    rate = settings.claude_requests_per_minute
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    for _ in range(rate):
        deps._consume_claude_token(user_a)
    # A is drained — but B should still have full bucket.
    assert deps._consume_claude_token(user_a) is False
    assert deps._consume_claude_token(user_b) is True


def test_quiz_generate_route_is_rate_limited(client, signup_payload, monkeypatch):
    """One smoke test that proves the dependency is wired at the route layer.

    We don't need quiz generation to actually succeed — we just need to
    confirm that draining the bucket causes the endpoint to 429 before
    any Claude call would be attempted. Patch the underlying service to
    raise if it gets called, so we know the limiter intercepts first.
    """
    from app.services import quiz_generator

    def _should_not_run(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("quiz_generator.generate_quiz reached past rate limit")

    monkeypatch.setattr(quiz_generator, "generate_quiz", _should_not_run)

    r = client.post("/api/v1/auth/signup", json=signup_payload("teacher"))
    assert r.status_code in (200, 201)
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    user_id = uuid.UUID(r.json()["user"]["id"])

    # Manually drain this user's bucket.
    rate = get_settings().claude_requests_per_minute
    for _ in range(rate):
        deps._consume_claude_token(user_id)

    # Now any quiz-generate call should be blocked before quiz_generator
    # is invoked. We don't need a real subject/document — the limiter
    # runs as a FastAPI dependency, before the handler body.
    body = {
        "subject_id": str(uuid.uuid4()),
        "document_id": str(uuid.uuid4()),
        "num_questions": 3,
        "difficulty": "medium",
        "topic_hint": "test",
    }
    resp = client.post("/api/v1/quizzes/generate", json=body, headers=headers)
    assert resp.status_code == 429, resp.text
    assert "Retry-After" in resp.headers
