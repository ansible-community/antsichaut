"""Basic tests for antsichaut."""
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from ruamel.yaml import YAML

from antsichaut.antsichaut import ChangelogCIBase

if TYPE_CHECKING:
    from collections import OrderedDict

    from _typeshed import OpenTextMode


REPO = "ansible-community/antsichaut"
FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_failure(capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure a failure if no token is provided.

    :param capsys: pytest fixture for capturing stdout and stderr
    """
    cci = ChangelogCIBase(
        repository=REPO,
        since_version="0.0.0",
        to_version="",
        group_config=[],
    )
    cci.run()
    captured = capsys.readouterr()
    message = "Could not find any release id"
    assert captured[0].startswith(message)


def test_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a success if a token is provided.

    :param monkeypatch: pytest fixture for monkey patching
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        pytest.fail("No GITHUB_TOKEN environment variable found")

    orig_open = Path.open

    def _open(  # noqa: PLR0913
        path: Path,
        mode: OpenTextMode = "r",  # noqa: ARG001
        buffering: int = -1,  # noqa: ARG001
        encoding: str | None = None,  # noqa: ARG001
        errors: str | None = None,  # noqa: ARG001
        newline: str | None = None,  # noqa: ARG001
    ) -> io.TextIOWrapper:
        # pylint: disable=unused-argument
        # pylint: disable=too-many-arguments
        return orig_open(FIXTURE_DIR / path)

    monkeypatch.setattr(Path, "open", _open)

    cci = ChangelogCIBase(
        repository=REPO,
        since_version="0.3.2",
        to_version="0.3.5",
        group_config=[],
        token=token,
    )

    def _write_changelog(string_data: OrderedDict[str, str]) -> None:
        str_io = io.StringIO()
        yaml = YAML()
        yaml.dump(string_data, str_io)
        str_io.seek(0)
        string = str_io.read()
        change_log = yaml.load(string)
        trivial_changes = change_log["releases"]["1.0.0"]["changes"]["trivial"]
        assert all(s in string for s in ("pull/10", "pull/11", "pull/12"))
        expected_number_of_entries = 3
        assert len(trivial_changes) == expected_number_of_entries

    monkeypatch.setattr(cci, "_write_changelog", _write_changelog)
    cci.run()
