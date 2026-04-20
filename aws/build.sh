#!/bin/bash
# 打包 query_lambda.zip，用 Docker 模拟 Amazon Linux 环境安装依赖
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PACKAGE_DIR="$SCRIPT_DIR/package"
ZIP_FILE="$SCRIPT_DIR/query_lambda.zip"

echo "==> 清理旧的打包目录..."
rm -rf "$PACKAGE_DIR" "$ZIP_FILE"
mkdir -p "$PACKAGE_DIR"

echo "==> 用 Docker (Amazon Linux) 安装依赖..."
# --platform linux/amd64 确保在 M1/M2 Mac 上也生成 x86_64 的二进制
docker run --rm \
  --platform linux/amd64 \
  --entrypoint pip \
  -v "$PACKAGE_DIR":/var/task \
  -v "$SCRIPT_DIR/requirements.txt":/requirements.txt \
  public.ecr.aws/lambda/python:3.11 \
  install -r /requirements.txt -t /var/task --quiet

echo "==> 复制 Lambda handler 和 settings..."
cp "$SCRIPT_DIR/query_lambda.py" "$PACKAGE_DIR/"
cp "$SCRIPT_DIR/get_order_lambda.py" "$PACKAGE_DIR/"
cp "$SCRIPT_DIR/create_order_lambda.py" "$PACKAGE_DIR/"
cp "$SCRIPT_DIR/lambda_settings.py" "$PACKAGE_DIR/"

echo "==> 复制 Django app (core/)..."
cp -r "$PROJECT_ROOT/app/core" "$PACKAGE_DIR/"

echo "==> 删除不需要的文件（减小 zip 体积）..."
find "$PACKAGE_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PACKAGE_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find "$PACKAGE_DIR" -name "*.pyc" -delete 2>/dev/null || true

echo "==> 打包成 zip..."
cd "$PACKAGE_DIR" && zip -r "$ZIP_FILE" . -x "*.dist-info/*" -x "*.egg-info/*" > /dev/null
cd "$SCRIPT_DIR"

SIZE=$(du -sh "$ZIP_FILE" | cut -f1)
echo ""
echo "✓ 打包完成：aws/query_lambda.zip ($SIZE)"
echo "  Lambda Handler 填写：query_lambda.handler"
