"""Unit tests for the local PostgreSQL manager (no download, no server)."""

import zipfile
from pathlib import Path

import pytest

from booski_core.devdb import (
    DevDbError,
    DevDbPaths,
    configured_port,
    extract,
    update_env_file,
    verify_checksum,
)


def _zip(path: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return path


def test_extract_keeps_only_server_folders(tmp_path: Path) -> None:
    archive = _zip(
        tmp_path / "pg.zip",
        {
            "pgsql/bin/postgres.exe": b"x",
            "pgsql/lib/a.dll": b"x",
            "pgsql/pgAdmin 4/big.exe": b"x",
            "pgsql/doc/i": b"x",
        },
    )
    target = tmp_path / "out"
    assert extract(archive, target) == 2
    assert (target / "pgsql/bin/postgres.exe").is_file()
    assert not (target / "pgsql/pgAdmin 4").exists()


def test_extract_rejects_paths_escaping_the_target(tmp_path: Path) -> None:
    archive = _zip(tmp_path / "evil.zip", {"pgsql/bin/../../../escaped.txt": b"x"})
    with pytest.raises(DevDbError, match="Unsafe path"):
        extract(archive, tmp_path / "out")
    assert not (tmp_path / "escaped.txt").exists()


def test_checksum_mismatch_is_rejected(tmp_path: Path) -> None:
    file = tmp_path / "pg.zip"
    file.write_bytes(b"not postgres")
    with pytest.raises(DevDbError, match="expected"):
        verify_checksum(file, expected="0" * 64)


def test_checksum_match_passes(tmp_path: Path) -> None:
    file = tmp_path / "pg.zip"
    file.write_bytes(b"abc")
    verify_checksum(file, expected="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")


def test_env_file_is_created_with_defaults(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    update_env_file(env, {"BOOSKI_DATABASE_URL": "postgresql+psycopg://a"})
    text = env.read_text(encoding="utf-8")
    assert "BOOSKI_ENVIRONMENT=development" in text
    assert "BOOSKI_DATABASE_URL=postgresql+psycopg://a" in text


def test_env_file_update_replaces_keys_and_keeps_other_lines(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("# mine\nBOOSKI_LOG_LEVEL=DEBUG\nBOOSKI_DATABASE_URL=old\n", encoding="utf-8")
    update_env_file(env, {"BOOSKI_DATABASE_URL": "new", "BOOSKI_TEST_DATABASE_URL": "test"})
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines[:3] == ["# mine", "BOOSKI_LOG_LEVEL=DEBUG", "BOOSKI_DATABASE_URL=new"]
    assert "BOOSKI_TEST_DATABASE_URL=test" in lines
    assert sum(line.startswith("BOOSKI_DATABASE_URL=") for line in lines) == 1


def test_configured_port_uses_the_last_setting(tmp_path: Path) -> None:
    paths = DevDbPaths(root=tmp_path, env_file=tmp_path / ".env")
    paths.data.mkdir()
    (paths.data / "postgresql.conf").write_text("#port = 5432\nport = 5432\nport = 55432\n", encoding="utf-8")
    assert configured_port(paths) == 55432
