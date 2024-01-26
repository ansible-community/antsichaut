# Antsichaut

Antsichaut automates the filling of a `changelog.yaml` used by antsibull-changelog.

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

PR's that have a `skip_changelog` do not get added to the changelog at all.

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

### Inputs

#### `since_version`

**Required** the version to fetch PRs since

#### `to_version`

the version to fetch PRs to

### Usage

```yaml
---
- name: "Get Previous tag"
  id: previoustag
  uses: "WyriHaximus/github-action-get-previous-tag@master"
  env:
    GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}"

- name: "Run antsichaut"
  uses: ansible-community/antsichaut@main
  with:
    GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}"
    since_version: "${{ steps.previoustag.outputs.tag }}"
```

### Examples

Check these examples out:
[telekom_mms.icinga_director](https://github.com/telekom-mms/ansible-collection-icinga-director/blob/ecb35f7ac04e7d14d2ccf21299acfc8771b8f3fd/.github/workflows/release.yml)
[prometheus.prometheus](https://github.com/prometheus-community/ansible/blob/11802e4e9a8f785d3f6ad23cd5af24d62ed6f5a4/.github/workflows/release.yml)

## Acknowledgements and Kudos

This script was initially forked from https://github.com/saadmk11/changelog-ci/
and modified by @rndmh3ro. Thank you, @saadmk11!

From May 2021 through May 2023, this project was maintained by @rndmh3ro and then graciously transferred to the ansible community organization. Thank you @rndmh3ro!

## License

The code in this project is released under the MIT License.
