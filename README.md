# Antsichaut

This is a very rough first try at automating the parts
of creating a `changelog.yaml` used by antsibull-changelog.

You define a Github repository and a Github release. Then the script
searches all pull requests since the release and adds them to the `changelog.yaml`.

The PR's get categorized into the changelog-sections based on labels and
according to this configuration (currently hardcoded):

```
group_config = [
  {"title": "major_changes", "labels": ["major", "breaking"]},
  {"title": "minor_changes", "labels": ["minor", "enhancement"]},
  {"title": "breaking_changes", "labels": ["major", "breaking"]},
  {"title": "deprecated_features", "labels": ["deprecated"]},
  {"title": "removed_features", "labels": ["removed"]},
  {"title": "security_fixes", "labels": ["security"]},
  {"title": "bugfixes", "labels": ["bug", "bugfix"]},
]
```

This means for example that PR's with the label `major` get categorized
into the `major_changes` section of the changelog.

PR's that do not have one of the above labels get categorized into the
`trivial` section.

## Installation

Install the requirements:

```
pip install -r requirements.txt
```


## Usage

You need a minimal `changelog.yml` created by antsibull-changelog:

```
antsibull-changelog release --version 1.17.0
```

Then define the version and the github repository you want to fetch the PRs from.
Either via arguments or via environment variables:

```
> python3 antsi_change_pr_getter.py --github_token 123456789012345678901234567890abcdefabcd --since_version 1.17.0 --to_version 1.18.0 --github_repository=T-Systems-MMS/ansible-collection-icinga-director
```

```
export SINCE_VERSION=1.17.0  # (or `latest`)
export TO_VERSION=1.18.0     # optional. if unset, defaults to current date
export GITHUB_REPOSITORY=T-Systems-MMS/ansible-collection-icinga-director
```

## Acknowledgements and Kudos

This script was initially forked from https://github.com/saadmk11/changelog-ci/
and modified to suit my needs. Thank you, @saadmk11!

## License

The code in this project is released under the MIT License.
