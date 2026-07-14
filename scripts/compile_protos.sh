#!/usr/bin/env bash
# Compile hermes proto files into Python gRPC stubs.
# Run from the admin-service root after `uv add grpcio protobuf && uv add --group dev grpcio-tools`.
#
# Usage: bash scripts/compile_protos.sh
set -euo pipefail

PROTO_DIR="protos"
OUT_DIR="app/grpc/generated"

mkdir -p "$OUT_DIR"
touch "$OUT_DIR/__init__.py"

python -m grpc_tools.protoc \
  -I"$PROTO_DIR" \
  --python_out="$OUT_DIR" \
  --grpc_python_out="$OUT_DIR" \
  hermes/gateway.proto \
  hermes/lists.proto \
  hermes/v2/whatsapp.proto \
  "hermes/v2/message-trace.proto" \
  hermes/control/business.proto

echo "Stubs written to $OUT_DIR"
