# 打包与跨平台适配

## 构建矩阵

| 平台 | 架构 | 命令 / 产物 |
| --- | --- | --- |
| Windows | x64 | `scripts\package.ps1` → NSIS `.exe` / MSI |
| macOS | x64/arm64 | `scripts/package-linux.sh` 同型改为 macOS 脚本 → `.dmg` |
| Linux 通用 | x64/arm64 | `scripts/package-linux.sh` → deb / rpm / AppImage |
| 麒麟 V10 | x64(海光/兆芯) / arm64(飞腾/鲲鹏) | 同上（Debian/Ubuntu 系，Tauri 依赖 webkit2gtk） |
| 统信 UOS | x64 / arm64 / LoongArch64 | deb；LoongArch 用 `loongarch64-unknown-linux-gnu` 源码构建 |
| 鸿蒙 | 通用 | **Web/PWA**（`web/dist`，浏览器离线安装）+ 可选 OpenHarmony ArkTS 壳 |

## Linux 依赖（麒麟/UOS）

```bash
sudo apt install -y libwebkit2gtk-4.1-dev libgtk-3-dev \
  libayatana-appindicator3-dev librsvg2-dev patchelf libssl-dev
```

## LoongArch64 说明

- Rust 目标：`loongarch64-unknown-linux-gnu`（在龙芯机器或交叉工具链上构建）。
- 若 webkit2gtk 不可用，降级为 `core(headless) + web/dist`（Nginx/静态服务器）运行。

## 鸿蒙（Web/PWA）

- 构建 `web/dist` 后，即可在鸿蒙系统浏览器访问并「添加到主屏幕」离线运行。
- PWA 已内置 manifest + service worker（见 `web/public/`）。
- 原生形态：用 OpenHarmony ArkTS 的 Web 组件加载 `web/dist`，通过 localhost HTTP 对接 core。

## CI

`.github/workflows/build.yml` 在 Windows/macOS/Linux(x64+arm64) 上自动编译 core、构建 web、打包 Tauri 并上传产物。
