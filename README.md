# Antsichaut

This is a first try at automating the filling of a `changelog.yaml` used by antsibull-changelog.

You define a Github repository and a Github release. Then the script
searches all pull requests since the release and adds them to the `changelog.yaml`.

The PR's get categorized into the changelog-sections based on these default labels:

```
group_config = [
  {"title": "major_changes", "labels": ["major", "breaking"]},
  {"title": "minor_changes", "labels": ["minor", "enhancement"]},
  {"title": "breaking_changes", "labels": ["major", "breaking"]},
  {"title": "deprecated_features", "labels": ["deprecated"]},
  {"title": "removed_features", "labels": ["removed"]},
  {"title": "security_fixes", "labels": ["security"]},
  {"title": "bugfixes", "labels": ["bug", "bugfix"]},
  {"title": "skip_changelog", "labels": ["skip_changelog"]},
]
```

This means for example that PR's with the label `major` get categorized
into the `major_changes` section of the changelog.

PR's that hace a `skip_changelog` do not get added to the changelog at all.

PR's that do not have one of the above labels get categorized into the
`trivial` section.

## Installation

```
pip install antsichaut
```


## Manual Usage

You need a minimal `changelog.yml` created by antsibull-changelog:

```
antsibull-changelog release --version 1.17.0
```

Then define the version and the github repository you want to fetch the PRs from.
Either via arguments or via environment variables:

```
> cd /path/to/your/ansible/collection
> antsichaut \
  --github_token 123456789012345678901234567890abcdefabcd \
  --since_version 1.17.0 \
  --to_version 1.18.0 \
  --major_changes_labels=foo
  --major_changes_labels=bar
  --minor_changes_labels=baz
  --repository=T-Systems-MMS/ansible-collection-icinga-director
```

```
> cd /path/to/your/ansible/collection
> export SINCE_VERSION=1.17.0  # (or `latest`)
> export TO_VERSION=1.18.0     # optional. if unset, defaults to current date
> export REPOSITORY=T-Systems-MMS/ansible-collection-icinga-director
> export MAJOR_CHANGES_LABELS=["foo","bar"]
> export MINOR_CHANGES_LABELS=["baz"]
> antsichaut
```

This will fill the `changelog.yaml` with Pull Requests.
Then run `antsibull-changelog generate` to create the final changelog.

## Usage with Github Actions

Check this [example](https://github.com/T-Systems-MMS/ansible-collection-icinga-director/blob/21e39f00ad792a36be1373c9d8755caa8b2bc2a5/.github/workflows/release.yml) out.

## Acknowledgements and Kudos

This script was initially forked from https://github.com/saadmk11/changelog-ci/
and modified to suit my needs. Thank you, @saadmk11!

## License

The code in this project is released under the MIT License.
