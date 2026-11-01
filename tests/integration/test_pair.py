"""Verify the public HTTP contract against backups produced by real borgmatic."""

import time
from datetime import datetime, timezone

import pytest

from tests.integration.harness import wait_until

pytestmark = pytest.mark.integration

REPOSITORY_METRICS = {
    "borg_total_chunks": "total_chunks",
    "borg_total_compressed_size": "total_csize",
    "borg_total_size": "total_size",
    "borg_total_deduplicated_compressed_size": "unique_csize",
    "borg_total_deduplicated_size": "unique_size",
}
ARCHIVE_METRICS = {
    "borg_last_backup_files": "nfiles",
    "borg_last_backup_deduplicated_compressed_size": "deduplicated_size",
    "borg_last_backup_compressed_size": "compressed_size",
    "borg_last_backup_size": "original_size",
}


def assert_matches_borg(pair, counts):
    samples = pair.scrape()
    assert {repository for _, repository in samples} == set(pair.repositories)
    for repository, count in zip(pair.repositories, counts, strict=True):
        info = pair.borg_json("info", repository, "--last", "1")
        listing = pair.borg_json("list", repository)
        assert len(listing["archives"]) == count
        assert samples[("borg_total_backups", repository)] == count
        for metric, key in REPOSITORY_METRICS.items():
            assert samples[(metric, repository)] == info["cache"]["stats"][key]
        if not count:
            assert not any(
                name.startswith("borg_last_backup_") and label == repository
                for name, label in samples
            )
            continue
        archive = info["archives"][0]
        for metric, key in ARCHIVE_METRICS.items():
            assert samples[(metric, repository)] == archive["stats"][key]
        assert samples[("borg_last_backup_duration", repository)] == pytest.approx(
            archive["duration"], rel=1e-6, abs=1e-6
        )
        end = datetime.fromisoformat(archive["end"])
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        assert samples[("borg_last_backup_timestamp", repository)] == pytest.approx(
            end.timestamp(), rel=0, abs=0.001
        )
        assert len([name for name, label in samples if label == repository]) == 12
    return samples


def test_empty_repository(pair_factory):
    pair = pair_factory()
    pair.initialize()
    assert_matches_borg(pair, [0])


@pytest.mark.parametrize("encryption", ["none", "repokey", "keyfile"])
def test_backup_metrics_and_refresh(pair_factory, encryption):
    pair = pair_factory()
    pair.initialize(encryption)
    pair.backup()
    first = assert_matches_borg(pair, [1])
    pair.write(f"{pair.root}/source/second.txt", "second backup\n" * 300)
    pair.backup()
    second = assert_matches_borg(pair, [2])
    repository = pair.repositories[0]
    assert second[("borg_last_backup_files", repository)] == (
        first[("borg_last_backup_files", repository)] + 1
    )
    assert (
        second[("borg_last_backup_timestamp", repository)]
        > first[("borg_last_backup_timestamp", repository)]
    )
    pair.borgmatic("check", "--force")


@pytest.mark.parametrize("config_mode", ["default", "multiple", "directory"])
def test_multiple_repositories(pair_factory, config_mode):
    pair = pair_factory(config_mode=config_mode, repository_count=2)
    pair.initialize()
    pair.backup()
    pair.backup(pair.repositories[1])
    assert_matches_borg(pair, [1, 2])


def test_cache_expires(pair_factory):
    # Leave room for slow ARM emulation to finish creating the second archive.
    cache_timeout = 60
    pair = pair_factory(cache_timeout=cache_timeout)
    pair.initialize()
    pair.backup()
    started = time.monotonic()
    cached = pair.scrape()
    pair.backup()
    assert (
        time.monotonic() - started < cache_timeout
    ), "Backup exceeded cache test window"
    assert pair.scrape() == cached
    repository = pair.repositories[0]
    wait_until(
        lambda: pair.scrape()[("borg_total_backups", repository)] == 2,
        "cached metrics to refresh",
        timeout=cache_timeout + 30,
    )
    assert_matches_borg(pair, [2])


def test_repository_failure_and_recovery(pair_factory):
    pair = pair_factory()
    pair.initialize()
    pair.backup()
    assert_matches_borg(pair, [1])
    repository = pair.repositories[0]
    pair.rename(repository, f"{repository}.unavailable")
    try:
        assert pair.get("/metrics")[0] == 500
    finally:
        pair.rename(f"{repository}.unavailable", repository)
    pair.backup()
    assert_matches_borg(pair, [2])


def test_scrape_with_repository_lock(pair_factory):
    pair = pair_factory()
    pair.initialize()
    pair.backup()
    expected = assert_matches_borg(pair, [1])
    with pair.locked_repository(pair.repositories[0]):
        assert pair.scrape() == expected
    pair.backup()
    assert_matches_borg(pair, [2])
