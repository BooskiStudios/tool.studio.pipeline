import pytest

from booski_core.cli import _is_loopback, main


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1", "127.0.0.2"])
def test_loopback_hosts_are_recognised(host: str) -> None:
    assert _is_loopback(host)


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.20", "::", "example.com"])  # noqa: S104
def test_non_loopback_hosts_are_recognised(host: str) -> None:
    assert not _is_loopback(host)


def test_serve_refuses_non_loopback_host_until_auth_exists(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["serve", "--host", "0.0.0.0"]) == 2  # noqa: S104
    assert "Refusing to listen on 0.0.0.0" in capsys.readouterr().err


def test_unknown_command_exits_with_usage_error() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["nonsense"])
    assert exc.value.code == 2
