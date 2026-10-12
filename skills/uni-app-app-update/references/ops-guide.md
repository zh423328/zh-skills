# App 更新操作手册

> 面向发版执行者的逐步操作说明。机制原理、字段定义、坑点说明见配套文档：`docs/app-update-说明文档.md`。

---

## 〇、发版前必读（30 秒版）

1. **先判断改了什么**：只改了前端（页面/样式/JS）→ 发 wgt；动了原生插件、manifest 原生配置、SDK → 发整包。
2. **版本号只增不减**：`src/manifest.json` 的 `versionCode` 每次发版（含 wgt）必须 +1 以上，且必须高于历史上所有已发版本的 versionCode。
3. **不确定发什么**：打一个 wgt 覆盖安装到旧包上跑主流程，白屏/报错就改发整包。

---

## 一、发 wgt 热更新（Android + iOS 通用）

**适用**：纯前端改动。**耗时**：约 30 分钟，无需审核。

### 步骤

1. **改版本号**：`src/manifest.json` → 基础配置，将 `versionName`（如 1.0.3）和 `versionCode`（如 103）各 +1。
2. **打 wgt 包**：HBuilderX 菜单 **发行 → 原生App-制作应用wgt包**，产物在 `unpackage/release/`（*.wgt）。
3. **覆盖安装验证**（不可跳过）：
   - 手机装着线上版本的 apk/ipa；
   - 把新 wgt 文件改后缀前先记录其 versionCode，通过 `plus.runtime.install` 或直接用测试工具覆盖安装；
   - 跑一遍主流程（登录、首页、核心业务页），确认不白屏、不报错。
4. **上传**：wgt 上传到服务器/OSS，拿到**可直连的下载直链**（浏览器地址栏能直接下载即合格）。
5. **改服务端版本接口**：递增 `versionCode`，`downloadUrl` 填 wgt 直链，`updateContent` 写更新说明，`forceUpdate` 按需（紧急修复 true，常规 false）。
6. **真机验证**：旧版本 App 杀掉重开（或切后台再回）→ 弹更新窗 → 下载进度 → 安装 → 点关闭重启 → 设置页确认版本号已变。

### 服务端配置示例

```json
{
  "name": "normal",
  "versionCode": 103,
  "version": "1.0.3",
  "updateContent": "1. 修复xx问题\n2. 优化xx体验",
  "forceUpdate": false,
  "downloadUrl": "https://your-cdn.com/app/release_103.wgt"
}
```

---

## 二、发 Android 整包

**适用**：新增/升级原生插件或 SDK、改了 manifest 的 App 模块/权限。

### 步骤

1. **改版本号**：manifest `versionName` / `versionCode` +1（必须高于历史所有 wgt 版本，否则整包装上后仍会加载旧 wgt 资源，见机制文档第三节）。
2. **云打包**：HBuilderX **发行 → 原生App-云打包**，选 Android、使用自有证书，勾选本次涉及的原生插件。
3. **真机验证新 apk**：覆盖安装跑主流程，重点验证新加的原生功能。
4. **上传 apk 直链**。
5. **改服务端**：Android 条目 `versionCode` 递增，`downloadUrl` 填 apk 直链。
6. **验证**：Android 8+ 真机触发更新 → 下载 → 首次会跳"允许安装未知应用"授权页 → 允许后安装 → 新版本生效。

---

## 三、发 iOS 整包（TestFlight）

**适用**：iOS 侧原生变更。前端变更请优先发 wgt（见第一节）。

### 步骤

1. **改版本号**：manifest `versionName` / `versionCode` +1；打包配置中 `CFBundleVersion` 同步递增（上传 App Store Connect 的硬性要求）。
2. **打 ipa**：HBuilderX **发行 → 原生App-云打包**，选 iOS（或本地打包），拿到 ipa。
3. **上传 App Store Connect**：Transporter 或 Xcode 上传 → 等待 Beta 处理完成（几十分钟到数小时）。
4. **拿到 TestFlight 加入链接**：App Store Connect → TestFlight → 对应构建 → 公开链接（格式 `https://testflight.apple.com/join/xxxxxxxx`）。**确认"公开链接"开关已开启**。
5. **改服务端**：iOS 条目 `versionCode` 递增，`downloadUrl` 填上述 TestFlight 加入链接。
6. **验证**：iOS 真机（已装 TestFlight App）触发更新 → 点"立即升级" → 直接拉起 TestFlight App 定位到本应用 → 点"更新"安装新构建。

### 注意

- 新 ipa 只包含新原生基座 + 新内置资源；如果之前发过 versionCode 更高的 wgt，用户装完新构建仍会加载旧 wgt 代码 —— 所以规则同上：**versionCode 单调递增**。
- TestFlight 构建 90 天过期，过期需用户重装，上传新构建会重置。

---

## 四、验证当前实际加载的资源版本

发版后如需确认用户端实际跑的是哪份资源：

- App 内任意位置调用 `getCurrentNo`（`src/utils/appUpdate.ts` 导出），返回的 `versionCode`/`versionName` 就是**当前实际加载的资源版本**（wgt 更新后是新 wgt 的版本，不一定是 apk/ipa 的版本）。
- 对照服务端下发的 versionCode 一致即更新成功。

---

## 五、回滚处理

| 场景 | 处理方式 |
|---|---|
| wgt 更新后发现前端 bug | 立即打一个回退版本的 wgt（versionCode 继续递增，内容回退），走正常 wgt 流程推送。**注意：versionCode 不能回退，只能"新版本号 + 旧代码"** |
| 整包发现严重问题 | iOS：无法快速回滚，只能上传修复版构建；Android：下发旧版本 apk 直链（versionCode 递增包装） |
| 更新接口出错导致误推送 | 服务端把对应平台的 `update` 条目下线或把 versionCode 改回不大于线上的值，App 端下次检查即不再弹窗 |

---

## 六、快速决策流程图

```
本次改动是什么？
│
├─ 纯前端（页面/样式/JS）
│   └─ 打 wgt → 覆盖安装验证 → 上传直链 → 服务端下 wgt 链接   ✅ 30分钟完成
│
├─ 动了原生插件 / manifest 模块权限 / SDK
│   ├─ Android → 云打包 apk → 上传 → 服务端下 apk 链接
│   └─ iOS → 打 ipa → 上传 App Store Connect → 服务端下 TestFlight 加入链接
│
└─ 拿不准
    └─ 先按 wgt 覆盖安装验证，异常即转整包
```
