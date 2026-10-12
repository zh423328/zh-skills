# App 更新机制说明文档

> 涉及文件：`src/utils/appUpdate.ts`（更新弹窗/下载/安装）、`src/config/componentConfig.ts`（服务端版本接口对接）、`src/App.vue`（onShow 时触发检查）。
> 本文档基于当前代码实际实现编写，作为发版操作手册使用。

---

## 一、整体更新流程

```
App 启动/回前台 (App.vue onShow)
    ↓
appUpdate() 入口 (#ifdef APP-PLUS，仅 App 端生效)
    ↓
getCurrentNo() → plus.runtime.getProperty 读取「应用资源版本号」(versionCode/versionName)
    ↓
componentConfig.getServerNo() → 请求服务端版本接口
    ↓
版本号数字比较（服务端 versionCode > 本地 versionCode 才触发）
    ↓
按 downloadUrl 后缀分发：
    ├── *.wgt   → 下载 wgt → plus.runtime.install 安装 → 重启生效
    ├── *.html  → plus.runtime.openURL 打开网页
    ├── *.apk (Android) → 下载 apk → plus.runtime.install 拉起系统安装器
    └── 其他链接
        ├── Android → 按 apk 下载安装处理
        └── iOS → openURL 打开 TestFlight 加入链接，直接拉起 TestFlight App
```

### 更新类型（updateType）

| updateType | 行为 | 来源 |
|---|---|---|
| `forcibly` | 强制更新：弹窗不可关闭，必须立即升级 | 服务端 `forceUpdate = true` |
| `solicit` | 弹窗确认更新：可点"暂不升级"或点遮罩关闭 | 服务端 `forceUpdate = false` |
| `silent` | 静默更新：无弹窗，后台下载安装，下次启动生效 | **仅当服务端直接下发该字段时生效**，当前 `getServerNo` 不会产出此类型 |

---

## 二、wgt 热更新 vs 整包更新：如何抉择

| 本次改动内容 | 更新方式 |
|---|---|
| 页面、样式、JS 逻辑、纯前端 bug 修复 | **wgt 热更新**（体积小、无需审核、秒级生效） |
| 新增/升级原生插件、第三方 SDK（如推送、地图、zego） | **整包** |
| manifest.json 修改 App 模块配置、权限、图标、启动图 | **整包** |
| HBuilderX 大版本升级 / 编译器不兼容 | **整包** |

**判断口诀：wgt 只能更新"前端资源"，凡是动了"原生层"都必须整包。**

稳妥验证法：把 wgt 覆盖安装到旧包上跑一遍主流程，不白屏、不报错就可以发 wgt；否则必须整包。

**wgt 更新失败的典型表现**：`plus.runtime.install` 报错（如 code -1205 版本校验失败），或安装成功但运行时白屏/报错（说明动了原生层）。

---

## 三、双端支持矩阵

### Android

| 能力 | 支持情况 | 备注 |
|---|---|---|
| wgt 热更新 | ✅ | 服务端下发 `.wgt` 链接即可 |
| apk 整包更新 | ✅ | 服务端下发 `.apk` 链接，下载后拉起安装器 |
| 安装权限 | — | Android 8+ 需要 `REQUEST_INSTALL_PACKAGES` 权限（**已在 manifest.json 配置**），且用户需手动授权"允许安装未知应用" |

### iOS（TestFlight 分发，不上 App Store）

| 能力 | 支持情况 | 备注 |
|---|---|---|
| wgt 热更新 | ✅ | TestFlight 的 ipa 就是正常签名的 App，`plus.runtime.install` 装 wgt 不受限制 |
| 原生层更新 | ✅ 引导式 | 服务端下发 TestFlight 加入链接（`https://testflight.apple.com/join/{code}`），App 通过 `openURL` 直接拉起 TestFlight App 定位到应用更新页 |
| 新原生版本分发 | — | 必须上传新 ipa 到 App Store Connect（TestFlight），用户在 TestFlight App 内更新 |

---

## 四、TestFlight 专项说明（重点）

1. **wgt 热更新完全可用**。Beta 审核只在上传构建时进行，不拦截运行时的 JS 资源热更新。
2. **两套独立的版本号体系**：
   - **ipa 版本**（`CFBundleShortVersionString` / `CFBundleVersion`）：App Store Connect 上传构建时使用，每次上传构建必须递增 CFBundleVersion。
   - **wgt 资源版本**（manifest.json 的 versionName/versionCode）：`plus.runtime.getProperty` 读取的就是它，服务端版本比较用的是它。两者互不影响。
3. **每次发 wgt 也必须递增 manifest.json 的 versionCode**，否则服务端版本比较不成立，更新检查不会触发。
4. **TestFlight 构建 90 天过期**，过期后测试员需从 TestFlight 重新安装；上传新构建会重置有效期。
5. **iOS 原生层更新的唯一途径**：打包新 ipa → 上传 App Store Connect → 等待 Beta 处理完成 → 服务端把 iOS 条目的 `downloadUrl` 更新为 TestFlight 加入链接，用户点击更新时 App 会自动拉起 TestFlight App。

---

## 五、服务端接口字段约定

接口：`apiGetAppVersion()`（`src/api/aps_api/common`），返回结构：

```json
{
  "update": [
    { "name": "ios",    "versionCode": 102, "version": "1.0.2", "updateContent": "更新说明", "forceUpdate": false, "downloadUrl": "https://xxx/update.wgt" },
    { "name": "normal", "versionCode": 102, "version": "1.0.2", "updateContent": "更新说明", "forceUpdate": false, "downloadUrl": "https://xxx/update.apk" }
  ]
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | 是 | 平台标识：iOS 取 `ios`，Android 取 `normal` |
| `versionCode` | 是 | **必须是数字**（前端已做 parseInt 兼容，但建议服务端直接下发数字）。每次发版（含 wgt）必须递增 |
| `version` | 是 | 版本名称，弹窗标题展示（"发现新版本 x.x.x"） |
| `updateContent` | 是 | 更新说明，弹窗正文展示 |
| `forceUpdate` | 是 | `true` = 强制更新，`false` = 弹窗确认更新 |
| `downloadUrl` | 是 | 见下方约定 |

### downloadUrl 约定

| 平台 | 场景 | downloadUrl 内容 |
|---|---|---|
| Android | 前端改动 | `.wgt` 文件直链 |
| Android | 原生改动 | `.apk` 文件直链 |
| iOS | 前端改动 | `.wgt` 文件直链（TF 下 wgt 热更可用） |
| iOS | 原生改动 | TestFlight 加入链接：`https://testflight.apple.com/join/{code}`（openURL 直接拉起 TestFlight App） |
| 双端 | 运营页/说明页 | `.html` 链接（openURL 打开） |

**注意**：服务端返回的 `downloadUrl` 必须是可直连的文件直链（不要 302 跳转、不要需要登录鉴权的链接），否则下载器 status ≠ 200 会提示下载失败。

---

## 六、发版操作 Checklist

### 发 wgt 热更新（Android + iOS 通用）

- [ ] 确认本次改动**不涉及**原生插件、manifest 原生配置、SDK、HBuilderX 编译器大版本变化
- [ ] 修改 `src/manifest.json` 的 `versionName` 和 `versionCode`（必须大于线上资源版本）
- [ ] HBuilderX 菜单：**发行 → 原生App-制作应用wgt包**
- [ ] 将 wgt 覆盖安装到旧包验证主流程无异常
- [ ] 上传 wgt 到服务器/OSS，确认拿到可直连的下载直链
- [ ] 服务端更新版本接口：递增 `versionCode`、更新 `downloadUrl` 为 wgt 直链
- [ ] 真机验证：旧版本 App 触发更新 → 下载进度 → 安装 → 重启后版本号生效

### 发整包（Android）

- [ ] 修改 manifest 版本号
- [ ] 云打包生成 apk（含原生插件变更）
- [ ] 上传 apk 直链，服务端更新 `downloadUrl`
- [ ] 验证 Android 8+ 真机安装授权流程

### 发整包（iOS / TestFlight）

- [ ] 修改 manifest 版本号，同时准备上传新构建（CFBundleVersion 在打包配置中递增）
- [ ] 云打包生成 ipa，上传 App Store Connect
- [ ] 等待 Beta 处理完成，通知测试员更新
- [ ] 服务端 iOS 条目更新 `versionCode` / `downloadUrl`（下发 TestFlight 加入链接，用户点更新时 App 直接拉起 TestFlight）

---

## 七、常见坑（务必阅读）

1. **版本号字符串比较**：前端已改为 `parseInt` 数字比较，但服务端仍建议下发数字类型。
2. **`@/` 路径在原生层无效**：更新弹窗图标走 `plus.nativeObj.View` 绘制，路径必须以 `/static/` 开头，不能用前端别名 `@/`（已修复默认值；如配置 `componentConfig.appUpdateIcon` 同样遵循此规则）。
3. **wgt 更新后读到的版本号是资源版本**：`getCurrentNo` 读的是 wgt 资源版本，不是 apk/ipa 版本，服务端比较逻辑基于此设计。
4. **wgt 覆盖安装验证是必须步骤**：跳过验证直接推送，遇到原生层不兼容会导致线上白屏。
5. **silent 更新不会立即生效**：安装完成后要等下次启动才生效，不要把 silent 用于需要立即生效的场景。
6. **Android 安装 apk 需用户授权**：首次会跳转"允许安装未知应用"设置页，用户拒绝则安装失败，属正常流程。
7. **TestFlight 加入链接必须在 iOS 真机/App 内打开才会拉起 TestFlight App**：在浏览器或电脑上打开只是普通网页；设备上未安装 TestFlight App 时会打开网页邀请页，需先装 TestFlight。同时 App Store Connect 后台的公开链接开关需开启，否则邀请链接对未受邀测试员无效。
