import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "releases"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
PREVIEW_PATTERN = re.compile(r"^v\d+\.\d+\.\d+-lite\.\d+-rc\.\d+$")
STABLE_PATTERN = re.compile(r"^v\d+\.\d+\.\d+-lite\.\d+$")


def _records() -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in RELEASES.glob("*.json")
    ]


def test_public_release_records_are_complete_and_immutable() -> None:
    records = _records()
    assert records
    for record in records:
        version = record["release_version"]
        assert record["channel"] in {"preview", "stable"}
        assert record["unofficial"] is True
        assert record["license"] == "GPL-3.0-only"
        assert SHA_PATTERN.fullmatch(record["official"]["backend_sha"])
        assert SHA_PATTERN.fullmatch(record["official"]["frontend_sha"])
        assert SHA_PATTERN.fullmatch(record["lite"]["backend_sha"])
        assert SHA_PATTERN.fullmatch(record["lite"]["frontend_sha"])
        assert DIGEST_PATTERN.fullmatch(record["image"]["digest"])
        assert record["image"]["tag"] == version
        assert "latest" not in json.dumps(record).lower()
        assert sorted(record["image"]["platforms"]) == [
            "linux/amd64",
            "linux/arm64",
        ]
        if record["channel"] == "preview":
            assert PREVIEW_PATTERN.fullmatch(version)
        else:
            assert STABLE_PATTERN.fullmatch(version)
            assert record["canary"]["status"] == "complete"
