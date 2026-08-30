#!/usr/bin/env bash
set -euo pipefail

CONTAINER="spark-iceberg-master"
SPARK_MASTER="spark://spark-master:7077"
SCRIPTS_DIR="/opt/spark/scripts"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 scripts/<target-file> [args...]"
  exit 1
fi

TARGET="$1"
shift

# 简单校验路径
if [[ ! "$TARGET" =~ ^scripts/ ]]; then
  echo "Error: argument must start with 'scripts/'"
  exit 1
fi

TARGET_FILE="${TARGET#scripts/}"
CONTAINER_PATH="$SCRIPTS_DIR/$TARGET_FILE"

echo "[INFO] Submitting Spark job:"
echo "       Container : $CONTAINER"
echo "       File      : $CONTAINER_PATH"
echo "       Arguments : $@"
echo

exec docker exec -it "$CONTAINER" \
  spark-submit \
  --master "$SPARK_MASTER" \
  "$CONTAINER_PATH" "$@"
