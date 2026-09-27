#!/usr/bin/env bash
# Linux 打包（含麒麟/统信）：构建 core + web + Tauri，产出 deb/rpm/AppImage。
# 用法：./scripts/package-linux.sh [target-triple]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-x86_64-unknown-linux-gnu}"

echo "==> 构建核心引擎 ($TARGET)"
cargo build --release --manifest-path "$ROOT/core/Cargo.toml" --target "$TARGET"

echo "==> 暂存核心二进制"
mkdir -p "$ROOT/desktop/src-tauri/binaries"
cp "$ROOT/core/target/$TARGET/release/ai-client" "$ROOT/desktop/src-tauri/binaries/ai-client"

echo "==> 构建前端"
(cd "$ROOT/web" && pnpm install && pnpm run build)

echo "==> Tauri 打包"
(cd "$ROOT/desktop" && pnpm install && pnpm tauri build --target "$TARGET")

echo "完成：$ROOT/desktop/src-tauri/target/$TARGET/release/bundle/"
