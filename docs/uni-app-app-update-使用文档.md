# uni-app App 更新系统使用文档

> 本文是 `uni-app-app-update` skill 的完整使用文档，覆盖从机制原理、项目接入、服务端对接、日常发版到回滚排查的全链路。
> 面向两类读者：**要把更新系统接入 uni-app 项目的开发者**，以及**接入后负责日常发版的执行者**。
> 复刻用的源码、脚本与模板随 skill 提供（`skills/uni-app-app-update/`），本文说明怎么用它们。

---

## 一、机制原理：先理解，再动手

### 1.1 App 是双层结构

uni-app 打出来的 App 分两层：

```
App = 原生基座（apk / ipa，含 manifest 配置、原生插件、SDK）
    + 前端资源（www 目录：页面、样式、JS）
```

wgt 只是前端资源的 zip 包。`plus.runtime.install` 把它解压到独立资源目录并记录版本；**App 启动时，运行时加载版本号更高的那份资源**——这就是热更新能生效的全部秘密。

由此推出两条铁律，写代码、发版、排查问题都绕不开：

1. **wgt 不能改变原生层**：新增原生插件、manifest 原生配置变更、SDK 变更，必须整包更新。
2. **versionCode 必须单调递增**，且大于历史上所有已发版本（含 wgt）。否则整包升级后，运行时仍会加载残留的旧 wgt 资源——用户明明装了新包，跑的还是旧代码。

### 1.2 整体更新流程

```
App 启动 / 回前台（App.vue onShow）
    ↓
appUpdate() 入口（#ifdef APP-PLUS，仅 App 端生效）
    ↓
getCurrentNo() → plus.runtime.getProperty 读取「应用资源版本号」
    ↓
componentConfig.getServerNo() → 请求服务端版本接口
    ↓
版本号数字比较（parseInt 后，服务端 versionCode > 本地才触发）
    ↓
按 updateType 分发：
    ├── forcibly  → 强制弹窗（不可关闭）→ 用户点"立即升级"
    ├── solicit   → 确认弹窗（可关闭）  → 用户点"立即升级"
    └── silent    → 无弹窗，后台下载安装，下次启动生效
    ↓
按 downloadUrl 后缀分发：
    ├── *.wgt   → 下载 wgt → plus.runtime.install → 点"关闭"重启生效
    ├── *.html  → plus.runtime.openURL 打开运营页
    ├── *.apk   → Android：下载后拉起系统安装器
    └── 其他链接 → Android 按 apk 处理；iOS 直接 openURL（TestFlight 加入链接拉起 TF App）
```

### 1.3 三种更新类型

| updateType | 行为 | 来源 |
|---|---|---|
| `forcibly` | 强制更新：弹窗不可关闭，必须立即升级 | 服务端 `forceUpdate = true` |
| `solicit` | 弹窗确认更新：可点"暂不升级"或点遮罩关闭 | 服务端 `forceUpdate = false` |
| `silent` | 静默更新：无弹窗，后台下载安装，下次冷启动生效 | **仅当服务端直接下发 `updateType: "silent"` 时生效**，按 `forceUpdate` 推导不出此类型 |

---

## 二、接入步骤（五步）

> 前提：目标项目是**经典 uni-app**（vue3 + `plus.*` API + `#ifdef APP-PLUS` 条件编译）。uni-app x（UTS 语言）不适用，需用 uni-app x 的 API 重写。

### 2.1 复制核心文件

从 `skills/uni-app-app-update/references/` 复制两个源码文件到目标项目：

| 源文件 | 目标路径 | 改写要求 |
|---|---|---|
| `appUpdate.ts` | `src/utils/appUpdate.ts` | **整份复制，不要重写**。弹窗按钮的坐标点击判定、进度条重绘逻辑是固定算法，改动容易引入 bug |
| `componentConfig.ts` | `src/config/componentConfig.ts` | **只有 `getServerNo` 需要按项目改写**：把 `apiGetAppVersion()` 替换为目标项目的版本检查接口，按其响应结构取值（字段说明见文件内注释） |

复制后顺手确认两处默认值：

- `appUpdate.ts` 顶部默认弹窗图标 `/static/ic_ar.png`——目标项目没有这张图就换成 `src/static/` 下实际存在的图片。**不能用 `@/` 别名**，`plus.nativeObj.View` 是原生层，只认 `/static/` 开头的路径。
- `componentConfig.ts` 底部的 `appUpdateColor`（弹窗主颜色，不填默认粉色）和 `appUpdateIcon`（弹窗图标，留空用默认值）。

### 2.2 接入启动检查

`App.vue` 中（import 和调用都要用条件编译包裹，否则 H5 / 小程序编译报错）：

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

默认每次回前台都检查。如需"仅启动时检查"，把调用移到 `onLaunch`。

### 2.3 确认 manifest 权限

读目标项目 `src/manifest.json`：

- Android 节点必须包含 `REQUEST_INSTALL_PACKAGES` 权限（apk 更新必需，Android 8+），没有则加上；
- 记录 `versionCode` / `versionName` / `appid`，第 2.4 步打 wgt 要用。

### 2.4 CLI 打 wgt（不依赖 HBuilderX）

把 `skills/uni-app-app-update/scripts/pack-wgt.js` 复制到目标项目 `scripts/`，package.json 加一条脚本：

```json
"build:wgt": "uni build -p app && node scripts/pack-wgt.js"
```

以后打 wgt 就是 `pnpm build:wgt`（或 npm / yarn 对应命令），产物在 `dist/release/${appid}_${versionCode}.wgt`（命名规则同官方 quickstart-cli）。

脚本的两个实现细节，改动前先读注释：

- 从 `dist/build/app-plus` 压缩**目录内的文件**（不含目录本身）——wgt 的 zip 根目录必须是 manifest.json 所在层级；
- manifest.json 允许注释（JSONC），脚本用**正则**提取 `versionCode` / `appid`，**不要改回 `JSON.parse`**（实测踩过的坑）。

注意事项：依赖系统 `zip` 命令（macOS 自带，Windows 需 Git Bash）；CLI 打出的 wgt **仍需覆盖安装验证**才能发布。

### 2.5 落地发版文档

把 skill 的两份参考文档复制到目标项目 `docs/` 下，路径中的项目特定信息（appid、目录名）替换为目标项目的值：

| 源文件 | 落地为 |
|---|---|
| `references/release-guide.md` | `docs/app-update-说明文档.md`（机制 + 坑点） |
| `references/ops-guide.md` | `docs/app-update-操作手册.md`（逐步操作手册 + 回滚） |

"上传服务器"相关章节按需保留——skill 只负责到"产出文件"为止，上传实现（OSS / CDN / 1Panel）不在范围内。

---

## 三、服务端接口约定

### 3.1 接口响应结构

版本接口返回平台化的更新条目，核心结构：

```json
{
  "update": [
    { "name": "ios",    "versionCode": 119, "version": "1.1.5", "updateContent": "1. 修复xx问题", "forceUpdate": false, "downloadUrl": "https://testflight.apple.com/join/XXXXXXXX" },
    { "name": "normal", "versionCode": 119, "version": "1.1.5", "updateContent": "1. 修复xx问题", "forceUpdate": false, "downloadUrl": "https://your-cdn.com/app/wgt/__UNI__XXXXXX_119.wgt" }
  ]
}
```

`componentConfig` 按平台取条目：iOS 取 `name == 'ios'`，Android 取 `name == 'normal'`。

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | 是 | 平台条目标识：Android 用 `normal`，iOS 用 `ios` |
| `versionCode` | 是 | **数字类型**，单调递增，必须大于历史上所有已发版本（含 wgt） |
| `version` | 是 | 版本名称，弹窗标题展示（"发现新版本 x.x.x"） |
| `updateContent` | 是 | 更新说明，映射为 `versionInfo` 供弹窗正文展示，支持 `\n` 换行 |
| `forceUpdate` | 是 | `true` = 强制更新（弹窗不可关闭），`false` = 弹窗确认更新 |
| `updateType` | 否 | `forcibly` / `solicit` / `silent`。优先采用此字段，不填时按 `forceUpdate` 推导；**silent 只有直接下发该字段才会触发** |
| `downloadUrl` | 是 | 按 3.2 的分发规则填写 |
| `publishTime` | 否 | 发布时间，便于排查线上发的是哪个包 |

### 3.2 downloadUrl 分发规则

| 平台 | 前端改动 | 原生改动 |
|---|---|---|
| Android | `.wgt` 直链 | `.apk` 直链 |
| iOS | `.wgt` 直链（TestFlight 下 wgt 热更可用） | TestFlight 加入链接（`https://testflight.apple.com/join/{code}`，openURL 拉起） |
| 双端 | `.html` 运营页链接（openURL 打开） | — |

**硬性要求**：downloadUrl 必须是可直连的文件直链——不要 302 跳转、不要登录鉴权，否则下载器 status ≠ 200，用户侧表现是"文件下载失败"。

### 3.3 零后端方案

目标项目没有后端版本接口时，直接把 skill 的 `assets/version.json` 放到静态服务器 / OSS 上，把 `componentConfig` 的 `getServerNo` 改为请求该 json 地址即可。有后端接口时，此模板即响应结构的约定。

---

## 四、日常发版操作

### 4.0 发版前 30 秒判断

1. **先判断改了什么**：只改了前端（页面 / 样式 / JS）→ 发 wgt；动了原生插件、manifest 原生配置、SDK → 发整包。
2. **版本号只增不减**：`src/manifest.json` 的 `versionCode` 每次发版（含 wgt）必须 +1 以上，且高于历史上所有已发版本。
3. **拿不准**：打一个 wgt 覆盖安装到旧包上跑主流程，白屏 / 报错就改发整包。

### 4.1 发 wgt 热更新（Android + iOS 通用）

**适用**：纯前端改动。**耗时**：约 30 分钟，无需审核。

- [ ] 确认本次改动**不涉及**原生插件、manifest 原生配置、SDK、编译器大版本变化
- [ ] 修改 `src/manifest.json` 的 `versionName` 和 `versionCode`（必须大于线上资源版本）
- [ ] 打包：`pnpm build:wgt`（CLI）或 HBuilderX **发行 → 原生App-制作应用wgt包**，产物 `*.wgt`
- [ ] **覆盖安装验证**（不可跳过）：手机装线上旧包，安装新 wgt，跑一遍主流程（登录、首页、核心业务页），不白屏、不报错
- [ ] 上传 wgt 到服务器 / OSS，拿到可直连的下载直链（浏览器地址栏能直接下载即合格）
- [ ] 服务端更新版本接口：递增 `versionCode`、`downloadUrl` 填 wgt 直链、`updateContent` 写更新说明、`forceUpdate` 按需（紧急修复 true，常规 false）
- [ ] 真机验证：旧版本 App 杀掉重开（或切后台再回）→ 弹更新窗 → 下载进度 → 安装 → 点关闭重启 → 设置页确认版本号已变

服务端配置示例：

```json
{
  "name": "normal",
  "versionCode": 120,
  "version": "1.1.6",
  "updateContent": "1. 修复xx问题\n2. 优化xx体验",
  "forceUpdate": false,
  "downloadUrl": "https://your-cdn.com/app/wgt/__UNI__XXXXXX_120.wgt"
}
```

### 4.2 发 Android 整包

**适用**：新增 / 升级原生插件或 SDK、改了 manifest 的 App 模块 / 权限。

- [ ] 修改 manifest 版本号（必须高于历史所有 wgt 版本，否则整包装上后仍会加载旧 wgt 资源）
- [ ] HBuilderX **发行 → 原生App-云打包**，选 Android、使用自有证书，勾选本次涉及的原生插件
- [ ] 真机覆盖安装新 apk 跑主流程，重点验证新加的原生功能
- [ ] 上传 apk 直链，服务端 Android 条目 `versionCode` 递增、`downloadUrl` 填 apk 直链
- [ ] 验证：Android 8+ 真机触发更新 → 下载 → 首次跳"允许安装未知应用"授权页 → 允许后安装 → 新版本生效

### 4.3 发 iOS 整包（TestFlight）

**适用**：iOS 侧原生变更。前端变更请优先发 wgt（4.1）。

- [ ] 修改 manifest 版本号；打包配置中 `CFBundleVersion` 同步递增（上传 App Store Connect 的硬性要求）
- [ ] HBuilderX **发行 → 原生App-云打包**（或本地打包）拿到 ipa
- [ ] 上传 App Store Connect（Transporter 或 Xcode），等待 Beta 处理完成（几十分钟到数小时）
- [ ] 拿 TestFlight 加入链接：App Store Connect → TestFlight → 对应构建 → 公开链接，**确认"公开链接"开关已开启**
- [ ] 服务端 iOS 条目 `versionCode` 递增，`downloadUrl` 填上述 TestFlight 加入链接
- [ ] 验证：iOS 真机（已装 TestFlight App）触发更新 → 点"立即升级" → 直接拉起 TestFlight App 定位到本应用 → 点"更新"安装新构建

> **iOS 两套版本号体系**：ipa 版本（`CFBundleShortVersionString` / `CFBundleVersion`）用于 App Store Connect 上传，每次上传必须递增；wgt 资源版本（manifest 的 versionName / versionCode）是 `plus.runtime.getProperty` 读到的值、服务端比较的依据。两者互不影响，**每次发 wgt 也必须递增 manifest 的 versionCode**，否则更新检查不触发。

### 4.4 验证当前实际加载的资源版本

发版后确认用户端实际跑的是哪份资源：App 内任意位置调用 `getCurrentNo`（`src/utils/appUpdate.ts` 导出），返回的 `versionCode` / `versionName` 就是当前实际加载的资源版本——wgt 更新后是新 wgt 的版本，不一定是 apk / ipa 的版本。对照服务端下发的 versionCode 一致即更新成功。

### 4.5 回滚处理

| 场景 | 处理方式 |
|---|---|
| wgt 更新后发现前端 bug | 立即打一个回退版本的 wgt（**versionCode 继续递增，内容回退**），走正常 wgt 流程推送。versionCode 不能回退，只能"新版本号 + 旧代码" |
| 整包发现严重问题 | iOS：无法快速回滚，只能上传修复版构建；Android：下发旧版本 apk 直链（versionCode 递增包装） |
| 更新接口出错导致误推送 | 服务端把对应平台的 `update` 条目下线，或把 versionCode 改回不大于线上的值，App 端下次检查即不再弹窗 |

---

## 五、FAQ 与常见坑

**Q：为什么版本号更新了却不弹窗？**
按概率排序：① 服务端 `versionCode` 是字符串且前端没做 parseInt 比较（`"100" > "99"` 为 false）；② 服务端 versionCode 没大于当前资源版本（`plus.runtime.getProperty` 读到的是 wgt 资源版本，不是 apk 版本）；③ downloadUrl 是 302 或需鉴权的链接，下载失败；④ H5 / 小程序端运行——更新代码被 `#ifdef APP-PLUS` 包裹，其他平台不执行。

**Q：wgt 安装成功但白屏 / 报错？**
动了原生层。`plus.runtime.install` 只更新前端资源，新增原生插件、改 manifest 模块配置、SDK 变更必须整包。这也是"覆盖安装验证不可跳过"的原因。

**Q：弹窗图标不显示？**
图标路径不能用 `@/` 别名，`plus.nativeObj.View` 是原生层，只认 `/static/` 开头的路径。确认目标项目 `src/static/` 下有配置的那张图。

**Q：silent 更新为什么没生效？**
silent 只有服务端直接下发 `updateType: "silent"` 字段才触发；按 `forceUpdate` 推导只会得到 forcibly / solicit。且 silent 安装后不重启，下次冷启动才生效——不要用于需要立即生效的场景。

**Q：iOS 上点了更新没反应 / 打开的是网页？**
设备上没装 TestFlight App 时，加入链接会打开网页邀请页；装上 TestFlight 后再点就会直接拉起。另外 App Store Connect 后台的"公开链接"开关必须开启，否则邀请链接对未受邀测试员无效。TestFlight 构建 90 天过期，过期后测试员需重装，上传新构建会重置有效期。

**Q：manifest.json 里有注释，脚本解析失败？**
正常——manifest.json 允许注释（JSONC），`JSON.parse` 会直接抛错。`pack-wgt.js` 已改用正则提取字段，保持现状，不要改回 `JSON.parse`。

**Q：wgt 文件名有规定吗？**
按官方 quickstart-cli 规则：`${appid}_${versionCode}.wgt`。`pack-wgt.js` 自动按 manifest 的 appid + versionCode 生成；文件名不影响 `plus.runtime.install`，但保持规则便于排查线上发的是哪个包。

**Q：Windows 上打 wgt 报错？**
脚本依赖系统 `zip` 命令，Windows 需在 Git Bash 中执行（或安装 zip 并加入 PATH）。

---

## 六、适配清单汇总

接入完成后逐项核对，漏掉任意一项都会导致功能异常：

- [ ] `componentConfig.ts` 的 `apiGetAppVersion` 已替换为目标项目的版本检查接口（或静态 version.json 地址）
- [ ] 弹窗图标路径有效且以 `/static/` 开头
- [ ] `App.vue` 的 import 与调用都在 `#ifdef APP-PLUS` 内
- [ ] `manifest.json` Android 节点有 `REQUEST_INSTALL_PACKAGES` 权限
- [ ] `scripts/pack-wgt.js` 已复制，package.json 有 `build:wgt` 脚本
- [ ] 版本检查时机符合预期（默认 onShow，可改 onLaunch）
- [ ] 服务端版本接口按第三节约定下发字段，downloadUrl 为可直连直链
- [ ] 发版文档已落地到目标项目 `docs/`
