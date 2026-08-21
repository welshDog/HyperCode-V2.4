#!/usr/bin/env python3
"""Fail if any docker-compose*.yml/.yaml file in the repo isn't valid YAML."""
import glob
import sys

import yaml


def main():
    files = glob.glob("docker-compose*.yml") + glob.glob("docker-compose*.yaml")
    errors = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                yaml.safe_load(fh)
            print(f"PASS: {f}")
        except Exception as e:
            print(f"FAIL: {f} -> {e}")
            errors.append(f)

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
