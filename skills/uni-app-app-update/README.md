# uni-app-app-update

在经典 uni-app 项目（vue3 + `plus.*` API，**非 uni-app x**）中复刻完整的 App 应用内更新系统。附带一套已在生产项目验证过的完整实现：版本检查弹窗、wgt 热更新、Android apk 整包下载安装、iOS App Store / TestFlight 引导、CLI 命令行打 wgt（不依赖 HBuilderX）。

本 skill 只服务一件事：**把成熟的更新系统正确移植进目标项目**。代码整份复制，不重写；只有服务端接口对接层按目标项目改写。

## 适合谁用

- 已有 uni-app App 项目，需要加"检查更新 / 应用更新 / 版本更新"功能
- 需要 wgt 热更新能力，且希望用 CLI 打包而不开 HBuilderX 的团队
- 要把一个项目的成熟更新逻辑（appUpdate.ts / componentConfig）移植到新项目
- 用 TestFlight 分发 iOS 的团队（wgt 热更 + TF 引导更新整链）
- 排查 `plus.runtime.install` / `getProperty` / 版本资源更新相关问题的开发者

## 一句话描述

你说"给我的 uni-app 项目加应用更新"，它给你一套生产验证过的完整实现——原生弹窗、下载进度、wgt 热更新、apk 安装、TestFlight 拉起，外加 CLI 打 wgt 脚本和全套发版操作文档。

## 触发关键词

```
加应用更新、版本更新、检查更新功能、App 内更新、更新弹窗、
强制更新、静默更新、wgt 热更新、打 wgt 包、制作 wgt、
CLI 打包 wgt 不用 HBuilderX、App 内下载 apk 更新、
移植更新逻辑到新项目、plus.runtime.install、版本资源更新
```

## 能力清单

| 能力 | 说明 |
|---|---|
| **更新检查弹窗** | `plus.nativeObj.View` 原生绘制：遮罩层、图标、标题、更新说明（自动换行）、按钮，不依赖前端页面渲染 |
| **三种更新类型** | `forcibly` 强制更新（不可关闭）/ `solicit` 弹窗确认 / `silent` 静默更新（无弹窗，下次启动生效） |
| **wgt 热更新** | 下载 wgt → `plus.runtime.install` 安装 → 点"关闭"重启生效，带进度条弹窗 |
| **apk 整包更新** | Android 下载 apk → 拉起系统安装器（需 `REQUEST_INSTALL_PACKAGES` 权限） |
| **iOS 分发** | App Store 链接或 TestFlight 加入链接（`https://testflight.apple.com/join/{code}`），`openURL` 直接拉起 TestFlight App |
| **downloadUrl 分发** | 按后缀自动分流：`.wgt` 热更 / `.html` 运营页 / `.apk` 整包 / 其他链接按平台走 apk 或 openURL |
| **CLI 打 wgt** | `node scripts/pack-wgt.js`：`uni build -p app` 后压缩产物为 `${appid}_${versionCode}.wgt`，不依赖 HBuilderX |
| **零后端方案** | `assets/version.json` 可直接静态托管到 OSS/CDN，接口层改请求该 json 即可 |

## 复刻流程概览

完整步骤见 [SKILL.md](SKILL.md)，这里给出全景：

| 步骤 | 动作 | 要点 |
|---|---|---|
| 1 | 复制核心文件 | `appUpdate.ts` 整份复制；`componentConfig.ts` 只改 `getServerNo` 里的版本接口 |
| 2 | 接入启动检查 | `App.vue` 的 `onShow` 里调 `appUpdate()`，必须用 `#ifdef APP-PLUS` 包裹 import 和调用 |
| 3 | 确认 manifest 权限 | Android 节点需有 `REQUEST_INSTALL_PACKAGES`；记录 appid / versionCode |
| 4 | CLI 打 wgt | 复制 `scripts/pack-wgt.js`，package.json 加 `"build:wgt": "uni build -p app && node scripts/pack-wgt.js"` |
| 5 | 输出发版文档 | 把 `references/release-guide.md` + `references/ops-guide.md` 落到目标项目 `docs/` |

## 落地文件对照表

| 本 skill 文件 | 复制到目标项目 | 是否需要改写 |
|---|---|---|
| `references/appUpdate.ts` | `src/utils/appUpdate.ts` | **不改写**（弹窗坐标判定、进度重绘是固定算法）；仅确认默认图标路径存在 |
| `references/componentConfig.ts` | `src/config/componentConfig.ts` | **必须改写**：`apiGetAppVersion` 替换为目标项目的版本检查接口；`appUpdateColor` / `appUpdateIcon` 按需配置 |
| `scripts/pack-wgt.js` | `scripts/pack-wgt.js` | 不改写；确认 package.json 的 `build:wgt` 路径一致 |
| `references/release-guide.md` | `docs/app-update-说明文档.md` | 替换项目特定信息（appid、目录名） |
| `references/ops-guide.md` | `docs/app-update-操作手册.md` | 替换项目特定信息 |
| `assets/version.json` | （可选）静态服务器 / OSS | 零后端方案时直接托管，接口层改请求其地址 |

## 适配清单（复制完代码后逐项核对）

漏掉任意一项都会导致功能异常：

- [ ] `componentConfig.ts` 顶部 import：`apiGetAppVersion` 来自源项目 `@/api/aps_api/common`，必须替换为目标项目的版本检查接口（或改为请求静态托管的 `version.json`）
- [ ] `appUpdate.ts` 默认弹窗图标 `/static/ic_ar.png`：确认目标项目 `src/static/` 下存在，否则换成实际存在的图片路径（**不能用 `@/` 别名**，原生层不识别）
- [ ] `App.vue`：`import appUpdate` 必须放在 `#ifdef APP-PLUS` 内，否则 H5 / 小程序编译报错
- [ ] `manifest.json`：Android 节点确认有 `REQUEST_INSTALL_PACKAGES` 权限
- [ ] `pack-wgt.js`：目标项目无 `scripts/` 目录则随复制创建
- [ ] 版本检查时机：默认 `onShow`（每次回前台检查）；如需"仅启动时检查"改到 `onLaunch`

## 必须向用户交代的已知坑（全部来自实测）

1. **版本号比较必须用 parseInt**：服务端下发字符串版本号时 `"100" > "99"` 为 false，更新永不触发。参考代码已修复，适配时不要退化。
2. **弹窗图标路径不能用 `@/` 别名**：`plus.nativeObj.View` 是原生层，只认 `/static/` 开头的路径。
3. **versionCode 单调递增**：且必须大于历史上所有已发版本（含 wgt），否则整包升级后运行时仍会加载残留的旧 wgt 资源。
4. **`plus.runtime.getProperty` 读到的是资源版本**：wgt 更新后即 wgt 的版本，不是 apk / ipa 版本，服务端比较逻辑基于此设计。
5. **wgt 更新后点"关闭"按钮才重启**（`plus.runtime.restart()`）；silent 静默更新不重启、下次冷启动生效。
6. **iOS TestFlight 链接直接 openURL 即可**：会被直接拉起 TestFlight App，不要画蛇添足加域名判断。
7. **CLI 打 wgt 仍需覆盖安装验证**：CLI 打包不改变"wgt 不能含原生变更"的规则。
8. **manifest.json 允许注释（JSONC）**：`pack-wgt.js` 用正则提取字段，不要改回 `JSON.parse`。

## 适用范围判断（不满足则不适用）

1. **经典 uni-app**（`plus.*` API + `#ifdef APP-PLUS` 条件编译）。uni-app x 用的是 UTS 强类型，`plus` API 不可用，需按 uni-app x 的 API 重写。
2. vue3 项目（vue2 也能用，但参考代码是 TS + Composition API 风格，需按项目约定调整）。
3. 目标平台是 App（Android / iOS）。H5 和小程序端代码全部被 `#ifdef APP-PLUS` 包裹，不影响其他平台。

同样不适用：上传 wgt / apk 到服务器或 CDN 的发布动作（本 skill 只到"产出文件"为止）、App Store 上架审核与证书签名等原生工程问题。

## 目录结构

```
uni-app-app-update/
├── SKILL.md                        # 技能入口：适用范围、复刻步骤、适配清单、触发条件
├── README.md                       # 本文件：使用文档
├── references/
│   ├── appUpdate.ts                # 更新弹窗/下载/安装完整实现（约 830 行，整份复制）
│   ├── componentConfig.ts          # 服务端接口对接层（唯一需要按项目改写的文件）
│   ├── release-guide.md            # 机制原理、决策表、TestFlight 专项、常见坑
│   └── ops-guide.md                # wgt / apk / TestFlight 发版操作手册与回滚方案
├── scripts/
│   └── pack-wgt.js                 # CLI 打 wgt：uni build -p app 产物 → ${appid}_${versionCode}.wgt
└── assets/
    └── version.json                # 版本接口响应模板（可静态托管，零后端方案）
```

## 深入阅读

- 📖 **完整使用文档**：[../../docs/uni-app-app-update-使用文档.md](../../docs/uni-app-app-update-使用文档.md)（机制原理、接入步骤、发版操作、FAQ 一站式）
- [SKILL.md](SKILL.md)：agent 执行复刻时的完整指令（步骤、清单、坑点）
- `references/release-guide.md`：更新机制与坑点说明（落地为目标项目 `docs/app-update-说明文档.md`）
- `references/ops-guide.md`：发版操作手册（落地为目标项目 `docs/app-update-操作手册.md`）
