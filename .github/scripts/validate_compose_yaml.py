#!/usr/bin/env python3
"""Fail if any docker-compose*.yml/.yaml file in the repo isn't valid YAML."""
import glob
import sys

import yaml


class ComposeLoader(yaml.SafeLoader):
    """SafeLoader plus the compose-spec merge tags `!override`/`!reset`
    (see docker-compose.observability.yml's security_opt blocks -- a real,
    intentional Docker Compose feature that controls how a value merges
    across -f files, not a YAML error. Plain yaml.safe_load has no
    constructor for either tag and fails outright; this only needs to
    parse structurally for validation, so both are treated as a plain
    passthrough of their underlying node, ignoring merge semantics that
    only `docker compose` itself needs to act on."""


def _passthrough(loader: yaml.SafeLoader, node: yaml.Node):
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return loader.construct_scalar(node)


ComposeLoader.add_constructor("!override", _passthrough)
ComposeLoader.add_constructor("!reset", _passthrough)


def main():
    files = glob.glob("docker-compose*.yml") + glob.glob("docker-compose*.yaml")
    errors = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                yaml.load(fh, Loader=ComposeLoader)
            print(f"PASS: {f}")
        except Exception as e:
            print(f"FAIL: {f} -> {e}")
            errors.append(f)

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
