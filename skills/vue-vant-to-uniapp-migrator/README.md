## Vue3 + Vant H5 迁移到 uni-app 技能使用指南

本文档介绍两个 AI 迁移技能的使用方法。它们分别适用于「首次全量迁移」和「后续增量同步」两个阶段，配合使用可以将一个 Vue3 + Vant4 的 H5 项目平滑迁移到 uni-app + wot-design-uni 技术栈。

两个技能都是通用技能，不内置任何具体项目路径。源/目标项目路径、分支等在运行时通过对话或配置文件获取。

---

### 技能概览

| 技能名称 | 触发关键词 | 适用场景 |
|---------|----------|---------|
| **vue-vant-to-uniapp-migrator** | "迁移"、"migrate"、"H5 转 uni" | 首次将一个 H5 项目的页面整体迁移到 uni-app 新项目 |
| **h5-to-uni-sync** | "同步"、"sync"、"增量同步" | H5 项目持续迭代时，将新增变更增量同步到 uni-app 项目 |

简单来说：**先 migrate，后 sync**。`vue-vant-to-uniapp-migrator` 是迁移的核心规则库，`h5-to-uni-sync` 在此基础上封装了增量 diff、版本追踪和自动化审计流程。

---

### 技术栈对照

| 维度 | H5 源项目 | uni-app 目标项目 |
|------|----------|----------------|
| 框架 | Vue 3 | Vue 3 |
| UI 库 | Vant 4 | wot-design-uni (wd-) |
| 路由 | Vue Router | uni-app pages.json + uni 导航 API |
| 请求 | Axios (request.ts 封装) | 目标项目自带 request.ts（不可修改） |
| 状态管理 | Pinia Options API | Pinia Setup API |
| 样式 | PostCSS px-to-vw | SCSS + rpx（1px = 2rpx） |
| CSS 方案 | 传统 SCSS | UnoCSS + SCSS |

---

### 一、vue-vant-to-uniapp-migrator（全量迁移）

#### 1.1 前置准备

在使用迁移技能之前，需要先创建好目标 uni-app 项目（目标项目必须由 `create-zh-uni` 脚手架创建）：

```bash
npx @zayn919/create-zh-uni <项目名>
# 或指定 wot-ui 模板
npx @zayn919/create-zh-uni <项目名> --template base-wotui
```

创建完成后安装依赖并执行一次 uvm 编译：

```bash
cd <项目名>
pnpm install
npx @dcloudio/uvm@latest
```

源项目与目标项目路径由用户在对话中提供；未提供时以当前工作目录推断，并与用户确认其角色（源项目还是目标项目）。

#### 1.2 触发方式

在对话中直接描述迁移需求即可触发，例如：

- "帮我把这个 H5 项目迁移到 uni-app"
- "migrate 这个页面到 uni"
- "H5 转 uni，迁移 login 页面"

#### 1.3 迁移工作流（Step 0 ~ Step 10）

**Step 0 — 确认源/目标项目路径**：源项目与目标项目路径由用户在对话中提供；未提供时以当前工作目录推断并与用户确认。技能本身不内置任何具体路径。

**Step 1 — 创建/确认目标项目**：确认目标项目已用 `create-zh-uni` 脚手架创建，保持默认目录结构不变。若用户已提供已创建的目标项目路径，直接使用。

**Step 2 — 目录与资源映射**：按以下规则映射文件路径（API 目录前缀以目标项目实际结构为准，首次配置时确认）：

| 源路径 | 目标路径 | 说明 |
|-------|---------|------|
| `src/views/**` | `src/pages/**` | 页面目录重命名 |
| `src/components/**` | `src/components/**` | 路径不变 |
| `src/apis/**` | 目标项目 API 目录（首次配置时确认，如 `src/api/apis/**`） | API 目录前缀变更 |
| `src/utils/**` | `src/utils/**` | 路径不变 |
| `src/stores/**` | `src/store/**` | 单数形式 |
| `src/assets/**` | `src/static/**` | 静态资源目录重命名 |

重命名特例按项目配置维护（如 `src/stores/userInfo.ts` → `src/store/user.ts` 这类重命名在 `.sync-config.json` 的 `renameMap` 中维护）。

**Step 3 — 转换模板标签**：

| H5 标签 | uni-app 标签 |
|---------|------------|
| `<div>` | `<view>` |
| `<span>` / `<font>` | `<text>` |
| `<img>` | `<image>` |
| `<a>` | `<navigator>`（站内跳转）或 `wd-button type="text"`（动作型） |
| `<select>` | `<wd-picker>`（优先）或原生 `<picker>` |
| `<iframe>` | `<web-view>` |
| `<table>` | `<view>` 布局替代 |

`<img>` 需要额外添加 `mode` 属性（常用 `aspectFit`、`aspectFill`、`widthFix`），并将路径从 `@/assets/` 改为 `/static/`。

滚动与滑动（DCloud 官方指南要求）：

- 固定高度 + `overflow: auto` 的区域滚动容器 → `scroll-view`（加 `scroll-y` 并保留固定高度），否则小程序端不滚动
- banner / 引导页 / tab 等滑动切换 → `swiper`，禁止 div + touch 事件模拟
- `<input type="search">` → 普通 input + `confirm-type="search"` + `@confirm`（不再用 `@keyup.enter`）
- `v-html` → `<rich-text :nodes="..." />`（小程序端不支持 v-html；App 端可 `#ifdef` 保留）

**Step 4 — 转换组件层**：将 Vant 组件替换为 wot-design-uni 组件。常用映射速查：

| Vant | wot-design-uni | 注意事项 |
|------|---------------|---------|
| `van-button` | `wd-button` | 属性基本一致 |
| `van-field` | `wd-input` | 组件名不同 |
| `van-cell` | `wd-cell` | 基本一致 |
| `van-popup` | `wd-popup` | position 属性值可能不同 |
| `van-form` | `wd-form` | 校验规则写法不同 |
| `van-tabs` / `van-tab` | `wd-tabs` / `wd-tab` | 基本一致 |
| `van-picker` | `wd-picker` | 事件名可能不同 |
| `van-dialog` | `wd-message-box` | 调用方式不同 |
| `van-search` | `wd-search` | 事件名需核对 |
| `van-list` | `v-for` + `wd-loadmore` | loadmore 仅做状态展示 |
| `van-nav-bar` | 移除 | 使用 uni-app 默认导航栏 |
| `van-dropdown-menu` | `wd-drop-menu` | 组件名不同 |
| `van-tag` | `wd-tag` | 基本一致 |
| `van-rate` | `wd-rate` | 基本一致 |
| `van-calendar` | `wd-calendar` | 基本一致 |
| `van-sticky` | `wd-sticky` | 基本一致 |

遇到未收录的组件时，技能会启动「未覆盖组件评估模板」，先评估再迁移。

**Step 5 — 转换生命周期与路由**：

页面文件（`src/pages/` 下）使用 uni-app 页面生命周期：

```ts
// 移除
import { onBeforeMount, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

// 替换为
import { onLoad, onShow, onUnload, onReachBottom } from '@dcloudio/uni-app'
```

映射关系：`onBeforeMount` → `onLoad`，`onMounted` → `onShow`，`onUnmounted` → `onUnload`。

路由跳转替换：

```ts
router.push({ path: '/home' })           →  uni.navigateTo({ url: '/pages/home/index' })
router.replace({ path: '/login' })       →  uni.redirectTo({ url: '/pages/login/index' })
router.go(-1)                            →  uni.navigateBack()
route.query.id                           →  onLoad((options) => { const id = options.id })
```

**重要区分**：子组件（`src/components/` 下）保持 Vue 原生生命周期（`onMounted`/`onUnmounted`），只有页面文件才使用 uni-app 生命周期。

**Step 6 — 转换 Web API（DCloud 官方指南核心，js 层）**：

uni-app 非 H5 端不支持 `window` / `navigator` / `document`，常见替换：

| H5 写法 | uni-app 替代 |
|---------|------------|
| `window.addEventListener('resize', cb)` | `uni.onWindowResize(cb)`（ECharts 自适应高频） |
| `navigator.geolocation` | `uni.getLocation({ type: 'gcj02' })` |
| `navigator.userAgent` 判断设备 | `uni.getSystemInfoSync().platform` |
| `getBoundingClientRect()` 量尺寸 | `uni.createSelectorQuery()` |
| `new WebSocket(...)` | `uni.connectSocket` 系列 |
| `alert()` / `confirm()` | `uni.showModal` |
| `<audio>` 标签 | `uni.createInnerAudioContext` |

依赖 dom/window 的三方库（echarts、地图等 web 版）：优先去插件市场找 uni 生态版本；仅 H5 端用条件编译包裹；App 端必须用时走 renderjs。

**Step 7 — 转换分页**：使用 `onReachBottom` 处理触底分页。注意不能设置页面高度，否则页面会被撑开导致 `onReachBottom` 无法正常触发。`wd-loadmore` 仅做加载状态展示，不包裹列表容器。H5 自定义下拉刷新可对应 `onPullDownRefresh`（需在 pages.json 开启 `enablePullDownRefresh`）。

**Step 8 — 转换样式**：

- 尺寸按 `1px = 2rpx` 转换（`padding: 16px` → `padding: 32rpx`）
- 例外：`border: 1px solid` 中的 `1px` 保持不变（hairline 边框）
- SCSS 变量路径：`@/assets/sass/` → `@/static/sass/`
- 深度选择器中 `van-` 前缀替换为 `wd-`
- 选择器约束：不支持 `*` 通配选择器（改显式枚举 `view, text, image {...}`）；`body` 选择器改 `page`；元素选择器用 uni 标签
- 避免过新的 CSS 语法（低端 Android 端会样式错误）
- 新增样式优先使用 UnoCSS

**Step 9 — 保持业务逻辑稳定**：函数名、文件名、样式类名、事件处理流程全部保持不变。接口返回结构不确定时可使用 `any` 保证编译通过。

**Step 10 — 运行迁移审计**：执行 `scripts/migration_audit.sh <目标路径>`，所有 `ERROR` 必须清零后再结束迁移。审计项包含：Vant 残留、vue-router 残留、**页面文件**（`src/pages/`）误用 Vue 生命周期（组件目录不检查，组件保留 Vue 生命周期是合法的）、v-html 残留（改 rich-text 或 `#ifdef` 限定非小程序端后即视为处理）、`*` 通配选择器、body 选择器、overflow 区域滚动、浏览器 API 残留（resize/定位/UA/DOM/WebSocket）、input type=search、px 未转换等。

#### 1.4 硬性约束

迁移过程中有以下不可违反的约束：

- 必须保留原函数名、原文件名、原样式类名
- 禁止修改目标项目的 `request.ts`
- 禁止引入自定义组件，仅使用 wot-design-uni 官方组件
- 禁止覆盖 uni-app 独有文件（目标项目有、源项目没有的文件，首次同步时自动生成清单写入配置）

---

### 二、h5-to-uni-sync（增量同步）

#### 2.1 适用场景

当 H5 源项目持续迭代（新增功能、修 bug），需要把开发分支上的新变更增量同步到已迁移好的 uni-app 项目时使用。

#### 2.2 触发方式

在对话中描述同步需求即可：

- "帮我同步一下"
- "H5 改了，帮我同步"
- "sync 最新的改动"

#### 2.3 项目配置与版本追踪

**项目配置（`.sync-config.json`）**：本技能不内置任何具体项目路径。首次使用时，技能会询问以下信息并写入目标项目根目录的 `.sync-config.json`，之后自动读取：

- H5 源项目路径、开发分支、基准分支
- uni-app 目标项目路径
- 目标项目 API 目录（源 `src/apis/` 的映射目标）
- 编译检查命令（默认 `pnpm build:h5`）

**版本追踪（`.sync-log.json`）**：同步技能通过 `.sync-log.json` 文件追踪版本，避免重复同步：

```json
{
  "lastSyncedCommit": "<上次同步到的完整 commit hash>",
  "lastSyncedShort": "<短 hash>",
  "lastSyncedMessage": "<commit message>",
  "lastSyncedDate": "2026-07-17",
  "syncHistory": [
    {
      "commit": "...",
      "short": "...",
      "message": "...",
      "date": "2026-07-15",
      "filesSynced": 5,
      "filesSkipped": 1,
      "filesManual": 0
    }
  ]
}
```

每次同步只处理 `lastSyncedCommit` 之后的新提交。开发分支与基准分支在首次配置时确认并写入 `.sync-config.json`；首次同步时以 `origin/<基准分支>` 为起点，处理开发分支相对于基准分支的全部变更。

#### 2.4 同步工作流（Phase 0 ~ Phase 8）

**Phase 0 — 项目配置**：读取 `<目标项目>/.sync-config.json`；若不存在，询问用户源/目标路径、分支、API 目录、编译命令并写入配置。首次同步时自动对比源/目标项目，生成目标项目独有文件清单 `exclusiveFiles`。

**Phase 1 — 获取增量变更**：读取配置获取源/目标路径与分支，切换到 H5 源项目的开发分支，读取 `.sync-log.json`，执行 `git diff --name-status <上次commit>..<开发分支> -- src/` 获取变更文件列表，展示给用户确认。

**Phase 2 — 文件分类与路径映射**：解析 diff 输出，按 A（新增）/ M（修改）/ D（删除）/ R（重命名）分类。自动跳过以下文件：`src/router/` 目录（路由由 pages.json 管理）、`src/utils/request.ts`（硬性约束）、`src/libs/bus.ts`（事件总线，uni-app 用 `uni.$on/$emit`）、`src/App.vue` / `src/main.ts`（入口文件差异大）、字体文件和备份文件。项目级追加跳过项见配置 `skipList`。

**Phase 3 — 逐文件转换**：按文件类别执行不同的转换策略（模板标签、组件映射、脚本转换、样式转换等），与迁移技能的规则一致。新增页面自动注册到 `pages.json`。

**Phase 4 — 智能决策与人工确认**：遇到浏览器专属功能（SSO 免登、Cookie 操作等）、无法映射的 Vant 组件、H5 独有依赖（`js-cookie`、`docx-preview` 等）时，标记为"需人工确认"并建议替代方案。

**Phase 5 — 输出同步报告 + 更新版本记录**：更新 `.sync-log.json`，输出变更概览、已同步文件清单、跳过文件清单、需人工确认清单。

**Phase 6 — 自动注册新页面**：新增的页面文件自动写入 `src/pages.json`，从源文件内容推断中文标题。

**Phase 7 — 编译检查**：执行配置的编译命令（默认 `pnpm build:h5`）验证编译。编译失败时自动尝试修复（import 路径、类型错误、缺失变量等），最多重试 3 次。3 次后仍有错误则记录到报告中等待人工处理。

**Phase 8 — 同步后审计**：这是最关键的质控环节，分 4 个子步骤：

- **8.1 文件覆盖率检查**：确认每个变更文件要么已同步，要么有明确的跳过理由
- **8.2 转换质量抽查**：启动 3-4 个并行子代理，逐文件检查 10 个维度（Vant 残留、px 残留、浏览器 API 残留、vue-router 残留、生命周期未转换、import 路径未转换、console.log 残留、注释代码块、Pinia 响应性、数据传递完整性），按严重性分为严重 / 中等 / 轻微三级
- **8.3 自动修复**：将审计发现的问题分批并行修复，修复后重新编译验证（最多 3 轮）
- **8.4 最终报告**：追加审计结果摘要到同步报告

#### 2.5 审计报告解读

同步完成后会输出类似以下格式的报告：

```
## 同步报告

### 版本信息
- 同步起点：ffead4d 上传优化
- 同步终点：45780d3 功能更新
- 本次涉及提交：3 个

### 变更概览
- 检测到的变更文件：40 个
- 已同步：39 个
- 跳过：1 个
- 需人工确认：0 个

### 审计结果
- 审计文件数：39
- 发现问题数：31（严重: 3, 中等: 15, 轻微: 13）
- 已自动修复：31
- 遗留需手动处理：0
- 最终编译状态：通过
```

如果"遗留需手动处理"不为 0，报告中会列出具体的文件、问题和建议，需要人工介入处理。

---

### 三、关键转换规则速查

以下规则在两个技能中通用，了解这些有助于理解迁移结果和排查问题。

#### 3.1 Pinia Store 转换

Options API → Setup 语法：

```ts
// H5
export const useXxxStore = defineStore('xxx', {
  state: () => ({ field1: null }),
  getters: { computedField: (state) => state.field1 ?? 'default' },
  actions: { async doSomething(params) { /* ... */ } },
})

// uni-app
export const useXxxStore = defineStore('xxx', () => {
  const field1 = ref(null)
  const computedField = computed(() => field1.value ?? 'default')
  const doSomething = async (params) => { /* ... */ }
  return { field1, computedField, doSomething }
}, { persist: true })
```

从 store 解构值时必须使用 `storeToRefs` 保持响应性：

```ts
// 错误
const { CURRENT_ROLE } = userInfoStore

// 正确
import { storeToRefs } from 'pinia'
const { CURRENT_ROLE } = storeToRefs(userInfoStore)
```

#### 3.2 存储 API 替换

```ts
localStorage.setItem('key', val)   →  uni.setStorageSync('key', val)
localStorage.getItem('key')        →  uni.getStorageSync('key')
sessionStorage.setItem('k', val)   →  uni.setStorageSync('k', val)
```

导航前的 `sessionStorage` 数据存储不可遗漏，否则目标页面获取不到数据。

#### 3.3 Vant 方法调用替换

```ts
showToast('消息')          →  uni.showToast({ title: '消息', icon: 'none' })
showSuccessToast('成功')   →  uni.showToast({ title: '成功', icon: 'success' })
showLoadingToast('加载中') →  uni.showLoading({ title: '加载中' })
closeToast()              →  uni.hideLoading()
showConfirmDialog({...})  →  uni.showModal({ title, content, showCancel: true })
```

#### 3.4 样式转换规则

```scss
// H5
.container {
  padding: 16px;        // → 32rpx
  font-size: 14px;      // → 28rpx
  width: 375px;         // → 750rpx
  border: 1px solid #eee;  // 保持 1px（hairline）
  background: url('@/assets/img/bg.png');  // → url('/static/img/bg.png')
}
```

#### 3.5 页面 vs 组件生命周期区分

| 文件位置 | 生命周期来源 | 使用的钩子 |
|---------|------------|----------|
| `src/pages/**/*.vue` | `@dcloudio/uni-app` | `onLoad`, `onShow`, `onReady`, `onUnload`, `onReachBottom`, `onPullDownRefresh` |
| `src/components/**/*.vue` | `vue` | `onMounted`, `onUnmounted`（保持原样） |
| `App.vue` | `@dcloudio/uni-app` | `onLaunch`, `onShow`, `onHide`（应用级，默认不迁移） |

这是最常出现的错误类型之一。页面文件误用 `onMounted`、组件文件误用 `onLoad` 都会导致问题。

#### 3.6 Web 专属能力替换（来自 DCloud 官方指南 36174）

| Web 写法 | uni-app 替代 |
|---------|------------|
| `overflow: auto` 区域滚动 | `scroll-view`（`scroll-y` + 固定高度） |
| div + touch 滑动切换 | `swiper` / `swiper-item` |
| `<input type="search">` | `confirm-type="search"` + `@confirm` |
| `v-html` | `rich-text`（小程序端）/ App 端可 `#ifdef` 保留 |
| `<select>` | `wd-picker`（优先）或原生 `picker` |
| `<audio>` 标签 | `uni.createInnerAudioContext` |
| `window.addEventListener('resize')` | `uni.onWindowResize` |
| `navigator.geolocation` | `uni.getLocation` |
| `navigator.userAgent` 设备判断 | `uni.getSystemInfoSync().platform` |
| `getBoundingClientRect()` | `uni.createSelectorQuery` |
| `new WebSocket` | `uni.connectSocket` 系列 |
| `*` 通配选择器 | 显式枚举（`view, text, image {...}`） |
| `body` 选择器 | `page` 选择器 |
| 依赖 dom/window 的三方库 | 插件市场替代 / H5 条件编译 / App 端 renderjs |

---

### 四、常见问题与注意事项

**Q：首次迁移用哪个技能？**
使用 `vue-vant-to-uniapp-migrator`。它会引导你完成完整的 9 步迁移流程，包括审计。

**Q：H5 项目更新了怎么办？**
使用 `h5-to-uni-sync`，说"帮我同步一下"即可。首次会询问配置并写入 `.sync-config.json`，之后自动读取，并自动识别上次同步的版本，只处理新变更。

**Q：同步后编译报错怎么办？**
`h5-to-uni-sync` 的 Phase 7 会自动尝试修复编译错误（最多 3 轮）。如果仍有问题，报告中的"编译错误（需人工处理）"部分会列出具体信息。

**Q：有哪些文件不会被同步？**
路由文件（`src/router/`）、请求封装（`src/utils/request.ts`）、事件总线（`src/libs/bus.ts`）、入口文件（`App.vue`/`main.ts`）、字体文件和备份文件会被自动跳过。目标项目的独有文件（目标有、源无的文件）也不会被覆盖。

**Q：审计发现"严重"问题怎么处理？**
严重问题通常是运行时错误级别的（未转换的 Vant 组件、缺失的 API 调用、数据丢失）。`h5-to-uni-sync` 的 Phase 8.3 会自动修复，修复不了才需要人工介入。

**Q：`border: 1px` 为什么没有转成 rpx？**
这是故意保留的。`border: 1px solid` 是 hairline 边框写法，在移动端能渲染出物理 1 像素的细线，转成 `2rpx` 反而变粗。

**Q：H5 里的 `v-html` 迁移后怎么处理？**
小程序端不支持 `v-html`。默认方案是换成 `<rich-text :nodes="htmlStr" />`；如果只在 App 端运行，可以用 `#ifdef` 条件编译保留 v-html；复杂富文本（带点击链接等交互）建议用插件市场的 uparse。

**Q：H5 项目用了 echarts / 地图等依赖 DOM 的库怎么办？**
这类库在小程序端跑不了。优先去 uni-app 插件市场（ext.dcloud.net.cn）找 uni 生态版本（如 uni-echarts、map 组件/nmap）；如果某功能只需 H5 端，用 `#ifdef H5` 条件编译包裹；App 端必须用 for-web 库时走 renderjs 引入。

**Q：`window.addEventListener('resize')` 的图表自适应怎么转？**
改成 `uni.onWindowResize(cb)`，页面卸载时记得 `uni.offWindowResize(cb)` 清理。

---

### 五、推荐工作流

1. **首次迁移**：用 `vue-vant-to-uniapp-migrator` 将 H5 项目的核心页面批量迁移到 uni-app 新项目（目标项目由 `create-zh-uni` 脚手架创建）
2. **验证**：编译检查 + 迁移审计，确保 ERROR 清零
3. **日常迭代**：H5 项目在开发分支继续开发，定期用 `h5-to-uni-sync` 同步变更
4. **质量闭环**：每次同步后的 Phase 8 审计会自动检查转换质量、修复问题并输出报告

两个技能配合使用，可以实现「一次迁移 + 持续同步」的长期维护模式。
