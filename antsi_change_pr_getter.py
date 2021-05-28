import os
from functools import cached_property
import requests
from ruamel.yaml import YAML


class ChangelogCIBase:
    """Base Class for antsi_change_pr_getter """

    github_api_url = "https://api.github.com"

    def __init__(
        self,
        repository,
        since_version,
        filename="changelogs/changelog.yaml",
        token=None,
    ):
        self.repository = repository
        self.filename = filename
        self.token = token
        self.since_version = since_version

    @cached_property
    def _get_request_headers(self):
        """Get headers for GitHub API request"""
        headers = {"Accept": "application/vnd.github.v3+json"}
        # if the user adds `GITHUB_TOKEN` add it to API Request
        # required for `private` repositories
        if self.token:
            headers.update({"authorization": "Bearer {token}".format(token=self.token)})

        return headers

    def _get_release_id(self):
        """Get ID of a specific release"""

        url = ("{base_url}/repos/{repo_name}/releases/tags/{since_version}").format(
            base_url=self.github_api_url,
            repo_name=self.repository,
            since_version=self.since_version,
        )

        response = requests.get(url, headers=self._get_request_headers)

        release_id = ""

        if response.status_code == 200:
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

    def _get_latest_release_date(self):
        """Using GitHub API gets latest release date"""

        if since_version == "latest":
            version = since_version
        else:
            version = self._get_release_id()

        url = ("{base_url}/repos/{repo_name}/releases/{version}").format(
            base_url=self.github_api_url, repo_name=self.repository, version=version
        )

        response = requests.get(url, headers=self._get_request_headers)

        published_date = ""

        if response.status_code == 200:
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

    def _write_changelog(self, string_data):
        """Write changelog to the changelog file"""

        with open(self.filename, "r+") as file:
            # read the existing data and store it in a variable
            yaml = YAML()
            yaml.dump(string_data, file)

    @staticmethod
    def _get_changelog_line(item):
        """Generate each line of changelog"""
        return "{title} ({url})".format(title=item["title"], url=item["url"])

    def get_changes_after_last_release(self):
        """Get all the merged pull request after latest release"""
        previous_release_date = self._get_latest_release_date()

        if previous_release_date:
            merged_date_filter = "merged:>=" + previous_release_date
        else:
            # if there is no release for the repo then
            # do not filter by merged date
            merged_date_filter = ""

        url = (
            "{base_url}/search/issues"
            "?q=repo:{repo_name}+"
            "is:pr+"
            "is:merged+"
            "sort:author-date-asc+"
            "{merged_date_filter}"
            "&sort=merged"
            "&per_page=100"
        ).format(
            base_url=self.github_api_url,
            repo_name=self.repository,
            merged_date_filter=merged_date_filter,
        )

        items = []

        response = requests.get(url, headers=self._get_request_headers)

        if response.status_code == 200:
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
                msg = (
                    f"There was no pull request "
                    f"made on {self.repository} after last release."
                )
                print(msg)
        else:
            msg = (
                f"Could not get pull requests for "
                f"{self.repository} from GitHub API. "
                f"response status code: {response.status_code}"
            )
            print(msg)

        return items

    def parse_changelog(self, changes):
        """Parse the pull requests data and return a string"""
        yaml = YAML()

        group_config = [
            {"title": "major_changes", "labels": ["major", "breaking"]},
            {"title": "minor_changes", "labels": ["minor", "enhancement"]},
            {"title": "breaking_changes", "labels": ["major", "breaking"]},
            {"title": "deprecated_features", "labels": ["deprecated"]},
            {"title": "removed_features", "labels": ["removed"]},
            {"title": "security_fixes", "labels": ["security"]},
            {"title": "bugfixes", "labels": ["bug", "bugfix"]},
        ]

        with open(
            "changelogs/changelog.yaml",
        ) as file:
            data = yaml.load(file)

        # get the new version from the changelog.yaml
        new_version = list(dict(dict(data)["releases"]))[0]

        # add changes-key to the release dict
        dict(data)["releases"][new_version].insert(0, "changes", {})

        leftover_changes = []
        for pull_request in changes:
            if len(changes) == 0:
                break
            for config in group_config:
                if any(label in pull_request["labels"] for label in config["labels"]):
                    change_type = config["title"]

                    # add the new change section if it does not exist yet
                    if change_type not in dict(data)["releases"][new_version]["changes"]:
                        dict(data)["releases"][new_version]["changes"].update(
                            {change_type: []}
                        )

                    pr = self._get_changelog_line(pull_request)

                    # if the pr is already in the dict, do not add it, just remove it
                    # from the list of pull_requests
                    if (
                        pr
                        in dict(data)["releases"][new_version]["changes"][change_type]
                    ):
                        break

                    # if there is no change of this change_type yet, add a new list
                    if not dict(data)["releases"][new_version]["changes"][change_type]:
                        dict(data)["releases"][new_version]["changes"][change_type] = [
                            pr
                        ]
                        break
                    # if there is a change of this change_type, append to the list
                    else:
                        dict(data)["releases"][new_version]["changes"][
                            change_type
                        ].append(pr)
                        break
            else:
                leftover_changes.append(pull_request)
                continue


        # all other changes without labels go to the trivial section
        change_type = "trivial"
        for pull_request in leftover_changes:
            if change_type not in dict(data)["releases"][new_version]["changes"]:
                dict(data)["releases"][new_version]["changes"].update(
                    {change_type: []}
                )

            pr = self._get_changelog_line(pull_request)

            # if the pr is already in the dict, do not add it, just remove it
            # from the list of pull_requests
            if (
                pr
                in dict(data)["releases"][new_version]["changes"][change_type]
            ):
                continue
            if not dict(data)["releases"][new_version]["changes"][change_type]:
                dict(data)["releases"][new_version]["changes"][change_type] = [
                    pr
                ]
            # if there is a change of this change_type, append to the list
            else:
                dict(data)["releases"][new_version]["changes"][
                    change_type
                ].append(pr)

        return data


    def run(self):
        """Entrypoint to the Changelog CI"""

        changes = self.get_changes_after_last_release()
        # exit the method if there are no changes found
        if not changes:
            return

        string_data = self.parse_changelog(changes)

        self._write_changelog(string_data)

if __name__ == "__main__":
    repository = os.environ["GITHUB_REPOSITORY"]
    token = os.environ.get("GITHUB_TOKEN")
    since_version = os.environ.get("SINCE_VERSION")

    ci = ChangelogCIBase(repository, since_version, token=token)
    # Run Changelog CI
    ci.run()
