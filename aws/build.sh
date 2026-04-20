#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPS_DIR="$SCRIPT_DIR/.deps"

echo "==> 用 Docker (Amazon Linux) 安装依赖..."
rm -rf "$DEPS_DIR"
mkdir -p "$DEPS_DIR"
docker run --rm \
  --platform linux/amd64 \
  --entrypoint pip \
  -v "$DEPS_DIR":/var/task \
  -v "$SCRIPT_DIR/requirements.txt":/requirements.txt \
  public.ecr.aws/lambda/python:3.11 \
  install -r /requirements.txt -t /var/task --quiet

build_lambda() {
  local name=$1         # create_order | query | get_order
  local handler=$2      # create_order_lambda.py | query_lambda.py | get_order_lambda.py
  local pkg_dir="$SCRIPT_DIR/.pkg_${name}"
  local zip_file="$SCRIPT_DIR/${name}_lambda.zip"

  echo "==> 打包 ${name}_lambda..."
  rm -rf "$pkg_dir"
  cp -r "$DEPS_DIR" "$pkg_dir"

  cp "$SCRIPT_DIR/$handler" "$pkg_dir/"
  cp "$SCRIPT_DIR/lambda_settings.py" "$pkg_dir/"
  cp -r "$PROJECT_ROOT/app/core" "$pkg_dir/"

  find "$pkg_dir" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
  find "$pkg_dir" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
  find "$pkg_dir" -name "*.pyc" -delete 2>/dev/null || true

  cd "$pkg_dir" && zip -r "$zip_file" . -x "*.dist-info/*" -x "*.egg-info/*" > /dev/null
  cd "$SCRIPT_DIR"
  rm -rf "$pkg_dir"

  SIZE=$(du -sh "$zip_file" | cut -f1)
  echo "  ✓ ${name}_lambda.zip ($SIZE)"
}

build_lambda "create_order" "create_order_lambda.py"
build_lambda "get_order" "get_order_lambda.py"

rm -rf "$DEPS_DIR"

echo ""
echo "✓ 全部打包完成"
echo "  Lambda Handler 填写："
echo "    create_order_lambda.zip → create_order_lambda.handler"
echo "    get_order_lambda.zip    → get_order_lambda.handler"
