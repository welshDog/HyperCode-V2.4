#!/bin/sh
# Resolver dry-run (nothing is installed) inside python:3.12-slim. Usage: run_dryrun_docker2.sh B A
cd "$(dirname "$0")"
for tag in "$@"; do
  docker run --rm --memory 700m --memory-swap 700m -v "$(pwd -W):/work" -w /work python:3.12-slim sh -c \
    "pip install --dry-run --ignore-installed --report dryrun-docker-$tag.json -r requirements.candidate$tag.txt > dryrun-docker-$tag.log 2>&1; echo \$? > dryrun-docker-$tag.exit"
done
echo done > dryrun-docker2.done
