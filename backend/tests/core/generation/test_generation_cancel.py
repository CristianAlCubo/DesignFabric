"""Tests de cancel cooperativa en JobStore y providers de imagen."""

from __future__ import annotations

import pytest

from designfabric.core.generation.image_providers import TestImageProvider
from designfabric.jobs.errors import JobCancelled
from designfabric.jobs.models import Job, JobStatus, JobType
from designfabric.jobs.store import JobStore


def test_request_cancel_queued_marks_cancelled():
    store = JobStore()
    job = Job.new(JobType.BATCH, payload={})
    store.add(job)
    assert store.request_cancel(job.id) is True
    assert store.get(job.id).status is JobStatus.CANCELLED
    assert store.is_cancel_requested(job.id)


def test_request_cancel_running_sets_flag():
    store = JobStore()
    job = Job.new(JobType.BATCH, payload={})
    store.add(job)
    store.mark_running(job.id)
    assert store.request_cancel(job.id) is True
    snap = store.get(job.id)
    assert snap.status is JobStatus.RUNNING
    assert snap.cancel_requested is True
    assert store.is_cancel_requested(job.id)


def test_request_cancel_terminal_returns_false():
    store = JobStore()
    job = Job.new(JobType.BATCH, payload={})
    store.add(job)
    store.mark_succeeded(job.id, result={"ok": True})
    assert store.request_cancel(job.id) is False


def test_test_image_provider_raises_job_cancelled(tmp_path):
    cancel_after = {"n": 0}

    def should_cancel() -> bool:
        cancel_after["n"] += 1
        return cancel_after["n"] > 1

    with pytest.raises(JobCancelled) as exc_info:
        TestImageProvider().generate_images(
            ["a", "b", "c"],
            output_dir=str(tmp_path),
            should_cancel=should_cancel,
        )
    assert isinstance(exc_info.value.partial_result, list)
    assert len(exc_info.value.partial_result) == 1
