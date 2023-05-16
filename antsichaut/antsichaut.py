#!/usr/bin/python
"""The antsichaut module."""

import re
from functools import cached_property
from importlib.metadata import version as _version
from pathlib import Path
from typing import Any, Optional, Sequence

import configargparse
import requests
from ruamel.yaml import YAML
from single_source import get_version

ChLogType = Optional[
    dict[
        str,
        dict[
            str,
            dict[
                str,
                dict[str, list[str]],
            ],
        ],
    ]
]


class ChangelogCIBase:
    """Base Class for antsichaut."""

    # pylint: disable=too-many-instance-attributes

    github_api_url = "https://api.github.com"

    def __init__(  # noqa: PLR0913
        self,
        repository: str,
        since_version: str,
        to_version: str,
        group_config: list[dict[str, Sequence[str]]],
        filename: str = "changelogs/changelog.yaml",
        token: Optional[str] = None,
    ) -> None:
        # pylint: disable=too-many-arguments
        self.repository = repository
        self.filename = Path(filename)
        self.token = token
        self.since_version = since_version
        self.to_version = to_version
        self.group_config = group_config
        self._string_data: ChLogType = None
        self._sorted_string_data: ChLogType = None

    @cached_property
    def _get_request_headers(self) -> dict[str, str]:
        """Get headers for GitHub API request.

        :return: The constructed headers
        """
        headers = {"Accept": "application/vnd.github.v3+json"}
        # if the user adds `GITHUB_TOKEN` add it to API Request
        # required for `private` repositories
        if self.token:
            headers["authorization"] = f"Bearer {self.token}"

        return headers

    def _get_release_id(self, release_version: str) -> str:
        """Get ID of a specific release.

        :param release_version: The version of the release
        :return: The release ID
        """
        url = f"{self.github_api_url}/repos/{self.repository}/releases/tags/{release_version}"

        response = requests.get(url, headers=self._get_request_headers, timeout=10)

        release_id = ""

        if response.ok:
            response_data = response.json()
            # get the published date of the latest release
            release_id = response_data["id"]
        else:
            # if there is no previous release API will return 404 Not Found
            msg = (
                f"Could not find any release id for "
                f"{self.repository}, status code: {response.status_code}"
            )
            print(msg)
        return release_id

    def _get_release_date(self, release_version: str) -> str:
        """Using GitHub API gets latest release date.

        :param release_version: The version of the release
        :return: The release date
        """
        if release_version == "latest":
            _version = release_version
        else:
            _version = self._get_release_id(release_version)

        url = f"{self.github_api_url}/repos/{self.repository}/releases/{_version}"

        response = requests.get(url, headers=self._get_request_headers, timeout=10)

        published_date = ""

        if response.ok:
            response_data = response.json()
            # get the published date of the latest release
            published_date = response_data["published_at"]
        else:
            # if there is no previous release API will return 404 Not Found
            msg = (
                f"Could not find any previous release for "
                f"{self.repository}, status code: {response.status_code}"
            )
            print(msg)

        return published_date

    def _write_changelog(self) -> None:
        """Write changelog to the changelog file."""

        yaml = YAML()
        yaml.explicit_start = True
        yaml.indent(sequence=4, offset=2)
        yaml.dump(self._string_data, self.filename)

    @staticmethod
    def _get_changelog_line(item: dict[str, str]) -> str:
        """Generate each line of changelog.

        :param item: The item to generate the line for
        :return: The generated line
        """
        return f"{item['title']} ({item['url']})"

    def get_changes_after_last_release(self) -> list[dict[str, str]]:
        """Get all the merged pull request.

        Only after specified release, optionally until specified release.

        :return: The list of pull requests
        """
        since_release_date = self._get_release_date(self.since_version)

        merged_date_filter = (
            f"merged:{since_release_date}..{self._get_release_date(self.to_version)}"
            if self.to_version
            else f"merged:>={since_release_date}"
        )

        url = (
            f"{self.github_api_url}/search/issues"
            f"?q=repo:{self.repository}+"
            "is:pr+"
            "is:merged+"
            "sort:author-date-asc+"
            f"{merged_date_filter}"
            "&sort=merged"
            "&per_page=100"
        )

        items = []

        response = requests.get(url, headers=self._get_request_headers, timeout=10)

        if response.ok:
            response_data = response.json()
            # `total_count` represents the number of
            # pull requests returned by the API call
            if response_data["total_count"] > 0:
                for item in response_data["items"]:
                    data = {
                        "title": item["title"],
                        "number": item["number"],
                        "url": item["html_url"],
                        "labels": [label["name"] for label in item["labels"]],
                    }
                    items.append(data)
            else:
                print("No pull request found")
        else:
            msg = (
                f"Could not get pull requests for "
                f"{self.repository} from GitHub API. "
                f"response status code: {response.status_code}"
            )
            print(msg)

        return items

    def remove_outdated(
        self,
        changes: list[dict[str, str]],
        data: dict[str, dict[str, dict[str, dict[str, list[str]]]]],
        new_version: str,
    ) -> None:
        """Remove outdate changes from changelog.

        Walk through the existing changelog looking for each PR.
        If the PR is found in a given line, but the title has changed,
        remove the line from the changelog. Rather than exit early,
        continue to walk through the changelog to ensure that all
        changes are removed.

        :param changes: list of PRs
        :param data: existing changelog data
        :param new_version: new version of the package to be released
        """
        current_changes = data["releases"][new_version]["changes"]
        for pull_request in changes:
            new_entry = self._get_changelog_line(pull_request)
            url = pull_request["url"]
            for change_type, changes_of_type in current_changes.items():
                change_list = reversed(list(enumerate(changes_of_type)))
                for idx, current_entry in change_list:
                    url_found = url in current_entry
                    not_full_match = new_entry != current_entry
                    if url_found and not_full_match:
                        del current_changes[change_type][idx]

    @staticmethod
    def _sort_by_semver(data: ChLogType) -> ChLogType:
        """Sort releases by semver.

        :param data: The full changelog structure
        :return: The sorted releases
        """
        if not data or "releases" not in data:
            return data
        data["releases"] = dict(
            sorted(
                data["releases"].items(),
                key=lambda t: [int(v) for v in t[0].split(".")],
                reverse=True,
            ),
        )
        return data

    def parse_changelog(  # noqa: C901, PLR0912
        self,
        changes: list[dict[str, str]],
    ) -> Any:
        """Parse the pull requests data and return a string.

        :param changes: The list of PRs
        :return: A dictionary representing the complete changelog
        """
        # pylint: disable=too-many-branches
        yaml = YAML()

        changelog = Path("changelogs/changelog.yaml")
        with changelog.open(encoding="utf-8") as file:
            data = yaml.load(file)

        # get the new version from the changelog.yaml
        # by using the last item in the list of releases
        data = self._sort_by_semver(data)
        new_version = list(data["releases"].keys())[0]

        # add changes-key to the release dict
        dict(data)["releases"][new_version].insert(0, "changes", {})

        # Remove outdated changes from changelog
        self.remove_outdated(
            changes=changes,
            data=data,
            new_version=new_version,
        )

        leftover_changes = []

        skip_labels = self.group_config.pop(
            [i for i, d in enumerate(self.group_config) if d["title"] == "skip_changelog"][0],
        )["labels"]

        for pull_request in changes:
            # if a PR contains a skip changelog label, ignore it entirely
            # do not add it to the changelog
            if any(label in pull_request["labels"] for label in skip_labels):
                break

            for config in self.group_config:
                if any(label in pull_request["labels"] for label in config["labels"]):
                    change_type = config["title"]

                    # add the new change section if it does not exist yet
                    if change_type not in dict(data)["releases"][new_version]["changes"]:
                        dict(data)["releases"][new_version]["changes"].update(
                            {change_type: []},
                        )

                    cl_entry = self._get_changelog_line(pull_request)

                    # if the pr is already in the dict, do not add it, just remove it
                    # from the list of pull_requests
                    if cl_entry in dict(data)["releases"][new_version]["changes"][change_type]:
                        break

                    # if there is no change of this change_type yet, add a new list
                    if not dict(data)["releases"][new_version]["changes"][change_type]:
                        dict(data)["releases"][new_version]["changes"][change_type] = [
                            cl_entry,
                        ]
                        break
                    # if there is a change of this change_type, append to the list
                    dict(data)["releases"][new_version]["changes"][change_type].append(
                        cl_entry,
                    )
                    break
            else:
                leftover_changes.append(pull_request)
                continue

        # all other changes without labels go to the trivial section
        change_type = "trivial"
        for pull_request in leftover_changes:
            if change_type not in dict(data)["releases"][new_version]["changes"]:
                dict(data)["releases"][new_version]["changes"].update({change_type: []})

            cl_entry = self._get_changelog_line(pull_request)

            # if the pr is already in the dict, do not add it, just remove it
            # from the list of pull_requests
            if cl_entry in dict(data)["releases"][new_version]["changes"][change_type]:
                continue
            if not dict(data)["releases"][new_version]["changes"][change_type]:
                dict(data)["releases"][new_version]["changes"][change_type] = [cl_entry]
            # if there is a change of this change_type, append to the list
            else:
                dict(data)["releases"][new_version]["changes"][change_type].append(cl_entry)

        return data

    def _sort_by_pr(self) -> None:
        """Sort changelog by PR number."""
        if not self._string_data or "releases" not in self._string_data:
            return
        for _release_number, release_changes in self._string_data["releases"].items():
            if "changes" not in release_changes:
                continue
            for _change_type, changes in release_changes["changes"].items():
                if not isinstance(changes, list):
                    continue
                changes.sort(
                    key=self._extract_pr_number_from_url,
                    reverse=True,
                )

    @staticmethod
    def _extract_pr_number_from_url(url: str) -> int:
        """Extract PR number from URL.

        :param url: The URL to extract the PR number from
        :return: The PR number
        """
        match = re.search(r"pull/(\d+)\)", url)
        if match:
            return int(match.group(1))
        return 0

    def run(self) -> None:
        """Entrypoint."""
        changes = self.get_changes_after_last_release()
        # exit the method if there are no changes found
        if not changes:
            return

        self._string_data = self.parse_changelog(changes)
        self._sort_by_pr()
        self._write_changelog()


def version() -> str:
    """Return the version of this package.

    :return: the version of this package
    :raises TypeError: if the version is not a string
    """
    __version__ = get_version(__name__, Path(__file__).parent.parent)
    if not __version__:  # pragma: no cover
        # Only works when package is installed
        __version__ = _version("antsichaut")
    if not isinstance(__version__, str):
        err = "Unable to detect version"
        raise TypeError(err)
    return __version__


def main() -> None:
    """Entrypoint."""
    parser = configargparse.ArgParser(
        default_config_files=[".antsichaut.yaml"],
        config_file_parser_class=configargparse.YAMLConfigFileParser,
        formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
    )

    # Add the arguments
    parser.add(
        "--repository",
        type=str,
        help="the github-repository in the form of owner/repo-name",
        env_var="GITHUB_REPOSITORY",
        required=True,
    )
    parser.add(
        "--github_token",
        type=str,
        help="a token to access github",
        env_var="GITHUB_TOKEN",
        required=True,
    )
    parser.add(
        "--since_version",
        type=str,
        help="the version to fetch PRs since",
        env_var="SINCE_VERSION",
        required=True,
    )
    parser.add(
        "--to_version",
        type=str,
        help="the version to fetch PRs to",
        env_var="TO_VERSION",
        required=False,
    )
    parser.add(
        "--major_changes_labels",
        dest="major_changes_labels",
        type=str,
        action="append",
        help="the labels for major changes. Default: ['major', 'breaking']",
        env_var="MAJOR_CHANGES_LABELS",
        required=False,
    )
    parser.add(
        "--minor_changes_labels",
        dest="minor_changes_labels",
        type=str,
        action="append",
        help="the labels for minor changes. Default: ['minor', 'enhancement']",
        env_var="MINOR_CHANGES_LABELS",
        required=False,
    )
    parser.add(
        "--breaking_changes_labels",
        dest="breaking_changes_labels",
        type=str,
        action="append",
        help="the labels for breaking changes. Default: ['major', 'breaking']",
        env_var="BRAKING_CHANGES_LABELS",
        required=False,
    )
    parser.add(
        "--deprecated_features_labels",
        dest="deprecated_features_labels",
        type=str,
        action="append",
        help="the labels for deprecated features. Default: ['deprecated']",
        env_var="DEPRECATED_FEATURES_LABELS",
        required=False,
    )
    parser.add(
        "--removed_features_labels",
        dest="removed_features_labels",
        type=str,
        action="append",
        help="the labels for removed features. Default: ['removed']",
        env_var="REMOVED_FEATURES_LABELS",
        required=False,
    )
    parser.add(
        "--security_fixes_labels",
        dest="security_fixes_labels",
        type=str,
        action="append",
        help="the labels for security fixes. Default: ['security']",
        env_var="SECURITY_FIXES_LABELS",
        required=False,
    )
    parser.add(
        "--bugfixes_labels",
        dest="bugfixes_labels",
        type=str,
        action="append",
        help="the labels for bugfixes. Default: ['bug', 'bugfix']",
        env_var="BUGFIXES_LABELS",
        required=False,
    )
    parser.add(
        "--skip_changelog_labels",
        dest="skip_changelog_labels",
        type=str,
        action="append",
        help=(
            "the labels for skip_changelog. "
            "Default: ['skip_changelog', 'skip-changelog', 'skipchangelog']"
        ),
        env_var="SKIP_CHANGELOG_LABELS",
        required=False,
    )
    parser.add("--version", action="version", version=version())

    # Execute the parse_args() method
    args = parser.parse_args()

    # set defaults if the labels are undefined
    # setting them with argparse does not work, because
    # with argparse you can only append to the defaults, not override them
    if not args.major_changes_labels:
        args.major_changes_labels = ["major", "breaking"]
    if not args.minor_changes_labels:
        args.minor_changes_labels = ["minor", "enhancement"]
    if not args.breaking_changes_labels:
        args.breaking_changes_labels = ["major", "breaking"]
    if not args.deprecated_features_labels:
        args.deprecated_features_labels = ["deprecated"]
    if not args.removed_features_labels:
        args.removed_features_labels = ["removed"]
    if not args.security_fixes_labels:
        args.security_fixes_labels = ["security"]
    if not args.bugfixes_labels:
        args.bugfixes_labels = ["bug", "bugfix"]
    if not args.skip_changelog_labels:
        args.skip_changelog_labels = ["skip_changelog", "skip-changelog", "skipchangelog"]

    repository = args.repository
    since_version = args.since_version
    to_version = args.to_version
    token = args.github_token

    group_config = [
        {"title": "major_changes", "labels": args.major_changes_labels},
        {"title": "minor_changes", "labels": args.minor_changes_labels},
        {"title": "breaking_changes", "labels": args.breaking_changes_labels},
        {"title": "deprecated_features", "labels": args.deprecated_features_labels},
        {"title": "removed_features", "labels": args.removed_features_labels},
        {"title": "security_fixes", "labels": args.security_fixes_labels},
        {"title": "bugfixes", "labels": args.bugfixes_labels},
        {"title": "skip_changelog", "labels": args.skip_changelog_labels},
    ]
    cl_cib = ChangelogCIBase(
        repository,
        since_version,
        to_version,
        group_config,
        token=token,
    )
    # Run Changelog CI
    cl_cib.run()


if __name__ == "__main__":
    main()
