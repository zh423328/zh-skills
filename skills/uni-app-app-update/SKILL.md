---
name: uni-app-app-update
description: 在经典 uni-app 项目（vue3 + plus.* API，非 uni-app x）中复刻完整的 App 应用内更新系统：版本检查更新弹窗、wgt 热更新、Android apk 整包下载安装、iOS App Store/TestFlight 引导、CLI 命令行打包 wgt（不依赖 HBuilderX）。当用户要求"加应用更新/版本更新/检查更新功能"、"做 wgt 热更新"、"打 wgt 包"、"App 内更新 apk"、"更新弹窗"，或要在新 uni-app 项目里移植现有项目的更新逻辑时，务必使用本 skill。
---

# uni-app App 更新系统复刻

帮用户在一个经典 uni-app 项目里搭建完整的应用内更新能力。本 skill 附带一套已在生产项目验证过的完整实现，你的工作是把这套实现正确地适配进目标项目，而不是从零发明。

## 适用范围判断

先确认目标项目满足以下条件，不满足则告知用户本 skill 不适用：

1. **经典 uni-app**（使用 `plus.*` API、`#ifdef APP-PLUS` 条件编译），**不是 uni-app x**（uni-app x 用 UTS 强类型，`plus` API 不可用）。
2. vue3 项目（vue2 也能用，但代码是 TS + Composition API 风格，需按项目约定调整）。
3. 目标平台是 App（Android/iOS）；H5 和小程序端代码全部被 `#ifdef APP-PLUS` 包裹，不影响其他平台。

## 实现原理（给用户解释时用）

App 是双层结构：原生基座（apk/ipa）+ 前端资源（www 目录）。wgt 只是前端资源的 zip 包，`plus.runtime.install` 解压到独立资源目录并记录版本，启动时运行时**加载版本号更高的那份资源**。由此推出两条铁律，写代码和文档时都要体现：

1. wgt 不能改变原生层（新增原生插件、manifest 原生配置、SDK 变更必须整包更新）。
2. versionCode 必须**单调递增**且大于历史上所有已发版本（含 wgt），否则整包升级后运行时仍会加载残留的旧 wgt 资源。

## 复刻步骤

按顺序执行，每步先读目标项目的对应文件再修改：

### 1. 复制核心文件

从本 skill 的 `references/` 复制两个源码文件到目标项目（读原文，按项目 TS/JS 约定适配）：

- `references/appUpdate.ts` → 目标项目 `src/utils/appUpdate.ts`：更新弹窗（plus.nativeObj.View 原生绘制）、下载进度、`plus.runtime.install` 安装、重启。**整份复制，不要重写**——弹窗按钮的坐标点击判定、进度条重绘逻辑是固定算法，改动容易引入 bug。
- `references/componentConfig.ts` → 目标项目 `src/config/componentConfig.ts`：服务端版本接口对接层。**只有这里的 `getServerNo` 需要按目标项目的真实接口改写**：把 `apiGetAppVersion()` 替换为目标项目的版本检查接口，按其响应结构取值（字段说明见文件内注释）。

### 2. 接入启动检查

在目标项目 `App.vue` 的 `onShow` 中加入（用条件编译包裹，App.vue 顶部也要 import）：

```js
// #ifdef APP-PLUS
import appUpdate from "@/utils/appUpdate";
// #endif

onShow(() => {
    // #ifdef APP-PLUS
    appUpdate();
    // #endif
});
```

### 3. 确认 manifest 权限

读目标项目 `src/manifest.json`，确认 Android 节点包含 `REQUEST_INSTALL_PACKAGES` 权限（apk 更新必需，Android 8+），没有则加上。同时记录 manifest 的 `versionCode`/`versionName`/`appid` 供第 5 步使用。

### 4. CLI 打 wgt 包（不依赖 HBuilderX）

把本 skill 的 `scripts/pack-wgt.js` 复制到目标项目 `scripts/pack-wgt.js`，并在 package.json 加：

```json
"build:wgt": "uni build -p app && node scripts/pack-wgt.js"
```

脚本逻辑：`uni build -p app` 产出 `dist/build/app-plus`（与官方 `build:app-plus` 一致），再压缩目录**内的文件**（不含目录本身）为 `${appid}_${versionCode}.wgt`（官方 quickstart-cli 命名规则）。脚本会从 manifest.json 用**正则**提取字段——manifest.json 允许注释（JSONC），不能用 JSON.parse，这是实测踩过的坑，脚本已处理，不要改回 JSON.parse。

注意事项向用户说明：依赖系统 `zip` 命令（macOS 自带，Windows 需 Git Bash）；打出的 wgt **仍需覆盖安装验证**才能发布，CLI 打包不改变"wgt 不能含原生变更"的规则。

### 5. 输出发版文档

把 `references/release-guide.md`（机制+坑点）和 `references/ops-guide.md`（操作手册）复制或改写到目标项目 `docs/` 下，路径中的项目特定信息（appid、目录名）替换为目标项目的值。文档中"上传服务器"相关章节按需保留（本 skill 不负责上传实现）。

### 适配清单（复制完代码后逐项核对）

复制代码后必须按目标项目实际情况修改的地方，漏掉任意一项都会导致功能异常：

- [ ] `componentConfig.ts` 顶部 import：`apiGetAppVersion` 来自源项目的 `@/api/aps_api/common`，必须替换为目标项目的版本检查接口（或改为请求 `assets/version.json` 模板的静态地址）
- [ ] `appUpdate.ts` 第 8 行默认弹窗图标 `/static/ic_ar.png`：确认目标项目 `src/static/` 下存在此图片，否则换成实际存在的图片路径
- [ ] `App.vue`：`import appUpdate` 必须放在 `#ifdef APP-PLUS` 内，否则 H5/小程序编译报错（plus 未定义）
- [ ] `manifest.json`：确认 Android 节点有 `REQUEST_INSTALL_PACKAGES` 权限；记录 appid/versionCode 供 pack-wgt.js 使用
- [ ] `pack-wgt.js`：目标项目若无 `scripts/` 目录则随复制创建；确认 package.json 中 `build:wgt` 脚本路径与实际目录一致
- [ ] 版本检查触发时机：默认在 `App.vue` 的 `onShow`（每次回前台检查），如需"仅启动时检查"改在 `onLaunch` 调用

## 必须向用户交代的已知坑（都来自实测）

1. **版本号比较必须用 parseInt**：服务端下发字符串版本号时 `"100" > "99"` 为 false，会导致更新永不触发。参考代码已修复，适配时不要退化。
2. **弹窗图标路径不能用 `@/` 别名**：plus.nativeObj.View 原生层不识别，必须 `/static/` 开头。参考代码默认 `/static/ic_ar.png`，目标项目若无此图片，改为其实际存在的 static 图片路径。
3. **iOS 无 App Store 链接的场景（如 TestFlight）**：非 wgt/html 链接直接 `plus.runtime.openURL`，TestFlight 加入链接（`https://testflight.apple.com/join/{code}`）会被直接拉起 TestFlight App。不要画蛇添足加域名判断。
4. **versionCode 判断入口在 `plus.runtime.getProperty`**：读到的是资源版本（wgt 更新后即 wgt 的版本），不是 apk/ipa 版本，服务端比较逻辑基于此设计。
5. **wgt 更新后点"关闭"按钮才重启**（`plus.runtime.restart()`）；silent 静默更新不重启、下次冷启动生效。当前 componentConfig 只产出 forcibly/solicit 两种类型，silent 仅当服务端直接下发 updateType 字段时生效。

## 服务端接口约定（指导用户或后端对接）

版本接口需返回平台化的更新条目，核心字段：`name`（ios/normal）、`versionCode`（数字，单调递增）、`version`、`updateContent`、`forceUpdate`、`downloadUrl`。downloadUrl 分发规则：

| 平台 | 前端改动 | 原生改动 |
|---|---|---|
| Android | `.wgt` 直链 | `.apk` 直链 |
| iOS | `.wgt` 直链 | App Store 链接或 TestFlight 加入链接（openURL 打开） |
| 双端运营页 | `.html` 链接 | — |

链接必须是可直连的文件直链（不要 302、不要鉴权），否则下载器 status ≠ 200。

## version.json 模板

模板文件在本 skill 的 `assets/version.json`。目标项目没有后端版本接口时，可以直接把这份 json 放到静态服务器/OSS 上，componentConfig 的 `getServerNo` 改为请求该 json 地址即可（零后端方案）。有后端接口时，此模板即响应结构的约定。

```json
{
  "update": [
    {
      "name": "normal",
      "platform": "android",
      "version": "1.1.5",
      "versionCode": 119,
      "updateContent": "1. 修复xx问题\n2. 优化xx体验",
      "forceUpdate": false,
      "updateType": "solicit",
      "downloadUrl": "https://your-cdn.com/app/wgt/__UNI__XXXXXX_119.wgt",
      "publishTime": "2026-10-12 10:00:00"
    },
    {
      "name": "ios",
      "platform": "ios",
      "version": "1.1.5",
      "versionCode": 119,
      "updateContent": "1. 修复xx问题\n2. 优化xx体验",
      "forceUpdate": false,
      "updateType": "solicit",
      "downloadUrl": "https://testflight.apple.com/join/XXXXXXXX",
      "publishTime": "2026-10-12 10:00:00"
    }
  ]
}
```

字段说明（字段名以 componentConfig 实际读取的为准，改字段名必须同步改 getServerNo）：

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | 是 | 平台条目标识：Android 用 `normal`，iOS 用 `ios`（componentConfig 按 name 取值） |
| `versionCode` | 是 | **数字类型**，单调递增，必须大于历史上所有已发版本（含 wgt） |
| `version` | 是 | 版本名称，弹窗标题展示（"发现新版本 x.x.x"） |
| `updateContent` | 是 | 更新说明，componentConfig 映射到 `versionInfo` 供弹窗正文展示，支持 `\n` 换行 |
| `forceUpdate` | 是 | `true` = 强制更新（弹窗不可关闭），`false` = 弹窗确认更新 |
| `updateType` | 否 | forcibly/solicit/silent。**参考实现优先采用此字段**，不填时按 `forceUpdate` 推导；silent 静默更新只有直接下发该字段才会触发 |
| `downloadUrl` | 是 | 按上方分发规则填写；wgt 文件名规则 `${appid}_${versionCode}.wgt` |
| `publishTime` | 否 | 发布时间，便于排查线上发的是哪个包 |

## 触发条件

以下场景应当使用本 skill（模型判断依据，也是给用户的使用说明）：

**应触发：**
- 用户要求在 uni-app 项目中"加应用更新 / 版本更新 / 检查更新功能"
- 用户提到"wgt 热更新"、"打 wgt 包"、"制作 wgt"、"CLI 打包 wgt 不用 HBuilderX"
- 用户要做"App 内下载 apk 更新"、"更新弹窗"、"强制更新/静默更新"
- 用户要把已有项目的更新逻辑（如 appUpdate.ts / componentConfig）移植到新项目
- 用户询问 plus.runtime.install / getProperty / 版本资源更新相关实现

**不应触发（转交其他方式处理）：**
- uni-app x 项目（UTS 语言，plus API 不可用）——需用 uni-app x 的 API 重写
- 纯 H5 或小程序端的"版本更新"（无 plus API，通常是接口缓存清理或小程序审核机制）
- 上传 wgt/apk 到服务器、CDN、1Panel 等发布动作——本 skill 只到"产出文件"为止
- App Store 上架审核、证书签名等原生工程问题

## 深入阅读

- `references/appUpdate.ts`：更新弹窗/下载/安装完整实现（约 830 行，复制时整份使用）
- `references/componentConfig.ts`：服务端接口对接层（唯一需要按项目改写的文件）
- `assets/version.json`：版本接口响应模板（可直接静态托管，零后端方案）
- `references/release-guide.md`：机制原理、决策表、TestFlight 专项、常见坑
- `references/ops-guide.md`：wgt/apk/TestFlight 发版操作手册与回滚方案
