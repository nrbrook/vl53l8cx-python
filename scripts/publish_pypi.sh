#!/bin/bash
set -euo pipefail

# Build and publish to TestPyPI or PyPI.
# Usage:
#   ./scripts/publish_pypi.sh test    # Upload to TestPyPI
#   ./scripts/publish_pypi.sh prod    # Upload to PyPI
#
# Requires:
#   - python3, pip, build, twine
#   - ~/.pypirc configured OR TWINE_USERNAME/TWINE_PASSWORD env vars

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-test}"

case "$TARGET" in
  test|prod) ;;
  *) echo "Target must be 'test' or 'prod'" >&2; exit 1;;
esac

cd "$REPO_ROOT"

echo "Cleaning old dist/build files..."
rm -rf library/build library/dist library/*.egg-info || true

echo "Ensuring build tooling..."
python3 -m pip install --upgrade --user build twine

echo "Building extension wheel..."
(
  cd library
  python3 setup.py sdist bdist_wheel
)

echo "Artifacts:"
ls -l library/dist

if [ "$TARGET" = "test" ]; then
  echo "Uploading to TestPyPI..."
  python3 -m twine upload --repository-url https://test.pypi.org/legacy/ library/dist/*
else
  echo "Uploading to PyPI..."
  python3 -m twine upload library/dist/*
fi

echo "Done."



