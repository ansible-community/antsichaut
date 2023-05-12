"""Basic tests for antsichaut."""
from __future__ import annotations

import io
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from ruamel.yaml import YAML

from antsichaut.antsichaut import ChangelogCIBase

if TYPE_CHECKING:
    from _typeshed import OpenTextMode


REPO = "ansible-community/antsichaut"
FIXTURE_DIR = Path(__file__).parent / "fixtures"
GROUP_CONFIG = [
    {
        "title": "skip_changelog",
        "labels": ["skip_changelog", "skip-changelog", "skipchangelog"],
    }
]


def test_failure(capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure a failure if no token is provided.

    :param capsys: pytest fixture for capturing stdout and stderr
    """
    cci = ChangelogCIBase(
        repository=REPO,
        since_version="0.0.0",
        to_version="",
        group_config=GROUP_CONFIG,
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

    class PatchedCCB(ChangelogCIBase):
        """Patched ChangelogCIBase class."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Initialize the class.

            :param args: positional arguments
            :param kwargs: keyword arguments
            """
            self.test_str_data: str | None = None
            super().__init__(*args, **kwargs)

        def _write_changelog(self) -> None:
            """Write the changelog to a string."""
            str_io = io.StringIO()
            yaml = YAML()
            yaml.dump(self._string_data, str_io)
            str_io.seek(0)
            self.test_str_data = str_io.read()

    cci = PatchedCCB(
        repository=REPO,
        since_version="0.3.2",
        to_version="0.3.5",
        group_config=GROUP_CONFIG,
        token=token,
    )
    cci.run()

    yaml = YAML()
    change_log = yaml.load(cci.test_str_data)
    trivial_changes = change_log["releases"]["1.0.0"]["changes"]["trivial"]

    assert cci.test_str_data
    assert all(s in cci.test_str_data for s in ("pull/10", "pull/11", "pull/12"))
    expected_number_of_entries = 3
    assert len(trivial_changes) == expected_number_of_entries

    assert re.findall(r"pull/(\d+)", cci.test_str_data) == ["12", "11", "10"]
