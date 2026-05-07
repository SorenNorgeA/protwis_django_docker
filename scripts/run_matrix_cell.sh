#!/usr/bin/env bash
# Run one compatibility-matrix cell.
#
#   ./scripts/run_matrix_cell.sh PY_MIN PY_MAX DJ_MAJOR DJ_NEXT RDK_MAJOR RDK_NEXT OUT_DIR
#
# Two gates:
#   1. uv lock         — does the dep graph resolve?
#   2. docker build    — does the image build all the way through?
#
# On success, the image is tagged. If env GH_OWNER is set the image is also
# pushed to ghcr.io/${GH_OWNER}/protwis_django_docker:<tag>; otherwise it
# stays local. This lets the same script run on CI (push) and on a laptop
# (no push).
#
# Each invocation writes a JSON result file to OUT_DIR/<tag>.json. The outer
# loop / aggregator picks these up and renders compatibility-matrix.md.
#
# This script never aborts on a single-cell failure: red cells are data,
# not exceptions. Use `set -e` only around its callsites if you need that.

set -uo pipefail

if [ "$#" -ne 7 ]; then
    echo "usage: $0 PY_MIN PY_MAX DJ_MAJOR DJ_NEXT RDK_MAJOR RDK_NEXT OUT_DIR" >&2
    exit 2
fi

PY_MIN=$1; PY_MAX=$2
DJANGO_MAJOR=$3; DJANGO_NEXT=$4
RDKIT_MAJOR=$5; RDKIT_NEXT=$6
OUT=$7

mkdir -p "$OUT"

# tag suffix: drop dots so it's a valid OCI tag (matrix-py311-dj42-rdk202409)
strip_dots() { echo "$1" | tr -d '.'; }
TAG="matrix-py$(strip_dots "$PY_MIN")-dj$(strip_dots "$DJANGO_MAJOR")-rdk$(strip_dots "$RDKIT_MAJOR")"
RESULT="$OUT/$TAG.json"

echo "::group::Cell $TAG  (Python $PY_MIN, Django $DJANGO_MAJOR, RDKit $RDKIT_MAJOR)"

LOCK=fail
BUILD=skip
TAG_PUSHED=

# 1. Render pyproject.toml from the template.
export PY_MIN PY_MAX DJANGO_MAJOR DJANGO_NEXT RDKIT_MAJOR RDKIT_NEXT
envsubst < pyproject.matrix.toml.tmpl > pyproject.toml

# 2. Gate 1: uv lock.
if timeout 120 uv lock; then
    LOCK=pass

    # 3. Gate 2: docker build (and push if GH_OWNER is set).
    BUILD_TAG_LOCAL="matrix-probe-local:$TAG"
    BUILD_ARGS=(
        --build-arg "PYTHON_VERSION=$PY_MIN"
        --tag "$BUILD_TAG_LOCAL"
        --cache-to   "type=gha,scope=$TAG,mode=max"
        --cache-from "type=gha,scope=$TAG"
    )

    if [ -n "${GH_OWNER:-}" ]; then
        REMOTE_TAG="ghcr.io/${GH_OWNER}/protwis_django_docker:$TAG"
        BUILD_ARGS+=(--tag "$REMOTE_TAG" --push)
        TAG_PUSHED="$REMOTE_TAG"
    else
        BUILD_ARGS+=(--load)
    fi

    if timeout 600 docker buildx build "${BUILD_ARGS[@]}" .; then
        BUILD=pass
    else
        BUILD=fail
        TAG_PUSHED=
    fi
fi

# 4. Emit JSON result. This is the wire format consumed by render_matrix_md.py.
cat > "$RESULT" <<EOF
{
  "python": "$PY_MIN",
  "django": "$DJANGO_MAJOR",
  "rdkit":  "$RDKIT_MAJOR",
  "lock":   "$LOCK",
  "build":  "$BUILD",
  "tag":    "$TAG",
  "pushed": "${TAG_PUSHED:-}"
}
EOF

echo "Cell $TAG: lock=$LOCK build=$BUILD"
echo "::endgroup::"

# Always exit 0 — the result is in the JSON, not the exit code.
exit 0
