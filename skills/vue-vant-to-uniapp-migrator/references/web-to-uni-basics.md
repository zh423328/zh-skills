# Web → uni-app 基础转换规则（共享参考）

整合自 DCloud 官方指南《vue h5 转 uni-app 指南》(https://ask.dcloud.net.cn/article/36174)。
两个技能（`vue-vant-to-uniapp-migrator` / `h5-to-uni-sync`）共用的底层转换规则。

---

## 1. 标签转换完整表

uni-app 标签与小程序一致，编译器在非 H5 端会自动转换部分标签（编译回 H5 端时 div 还是 div），但源码层面统一替换更利于跨端一致性。

| H5 标签 | uni-app 标签 | 说明 |
|---------|------------|------|
| `<div>` | `<view>` | 块级容器 |
| `<span>` | `<text>` | 行内文本 |
| `<font>` | `<text>` | 行内文本 |
| `<img>` | `<image>` | 必须加 `mode` 属性 |
| `<a>` | `<navigator>` 或 `wd-button type="text"` | 站内跳转用 navigator，动作型用文本按钮 |
| `<select>` | `<picker>` | 原生下拉，或用 wd-picker / wd-col-picker |
| `<iframe>` | `<web-view>` | 内嵌网页 |
| `<p>` / `<h1>`~`<h6>` | `<view>` | 段落与标题 |
| `<ul>` / `<ol>` / `<li>` | `<view>` | 无列表标签，全部用 view |
| `<input>` | `<input>` | 保持不变，但 `type="search"` 特殊处理见下文；小程序 type 仅支持 text/number/idcard/digit 等 |
| `<textarea>` | `<textarea>` | 保持不变 |
| `<form>` / `<label>` | `<form>` / `<label>` | 保持不变 |
| `<audio>` | API 方式 `uni.createInnerAudioContext` | audio 组件不再推荐 |
| `<video>` | `<video>` 组件 | 保持，src 需可访问 |
| `<canvas>` | `<canvas>`（`canvas-id` 或 type="2d"） | 绘制 API 改 uni.createCanvasContext |
| `<table>` | `<view>` 布局替代 | uni-app 无 table，可由循环 + flex/grid 拼接 |

## 2. 表单细节

### 2.1 select → picker

```html
<!-- H5 -->
<select v-model="city">
  <option :value="c.value" v-for="c in cities">{{ c.label }}</option>
</select>

<!-- uni-app：原生 picker -->
<picker mode="selector" :range="cities" range-key="label" @change="onCityChange">
  <view class="picker-text">{{ cityLabel || '请选择' }}</view>
</picker>

<!-- uni-app：优先用 wot-design-uni（与 Vant 交互一致） -->
<wd-picker :columns="cityColumns" v-model="city" @confirm="onCityChange" />
```

### 2.2 input type="search"

H5 中 `<input type="search">` 的键盘"搜索"按钮，在 uni-app 中 `type` 属性不再控制键盘按钮，改用 `confirm-type`：

```html
<!-- H5 -->
<input type="search" @keyup.enter="onSearch" v-model="keyword" />

<!-- uni-app -->
<input
  v-model="keyword"
  confirm-type="search"
  @confirm="onSearch"
/>
```

- `confirm-type` 合法值：`search` / `send` / `next` / `go` / `done`
- 键盘回车事件用 `@confirm`，不是 `@keyup.enter`

### 2.3 input type 值差异（小程序端）

H5 的 `type="email"` / `tel` / `url` / `password` 在小程序端无效（type 仅支持 `text` / `number` / `idcard` / `digit` 等）：

| H5 type | uni-app 处理 |
|---------|-------------|
| `email` / `tel` / `url` | 改 `type="text"`，格式校验移到 JS |
| `password` | 改用 `password` 布尔属性（`:password="true"`） |
| `number` / `digit` | 直接可用 |

## 3. 滚动与滑动

### 3.1 区域滚动 → scroll-view

H5 中 `div` + `overflow: auto` 的区域滚动，在 uni-app 必须换成 `scroll-view`，否则小程序端不滚动：

```html
<!-- H5 -->
<div class="list-wrap" style="height: 300px; overflow-y: auto;">
  <div v-for="i in list">{{ i }}</div>
</div>

<!-- uni-app -->
<scroll-view scroll-y style="height: 300px;">
  <view v-for="i in list">{{ i }}</view>
</scroll-view>
```

要点：
- 必须 `scroll-y`（纵向）或 `scroll-x`（横向）
- scroll-view 需要显式固定高度（不写高度无法滚动）
- 页面级滚动不要用 scroll-view（用页面原生滚动 + `onReachBottom`）
- 判断依据：源代码中 `overflow: auto/scroll` + 固定高度容器 → 改 scroll-view

### 3.2 滑动切换 → swiper

左右/上下滑动切换（如 banner 轮播、tab 滑动切换、引导页），必须用 `swiper`，不要用 div + touch 事件模拟：

```html
<!-- H5：div 模拟轮播 -->
<div class="banner" @touchstart="..." @touchmove="..." @touchend="...">...</div>

<!-- uni-app -->
<swiper class="banner" :indicator-dots="true" :autoplay="true" :interval="4000" :circular="true">
  <swiper-item v-for="b in banners" :key="b.id">
    <image :src="b.url" mode="aspectFill" />
  </swiper-item>
</swiper>
```

### 3.3 audio 组件

H5 的 `<audio>` 标签在 uni-app 不再推荐，改成 API 方式（`uni.createInnerAudioContext` / 背景音频 `uni.getBackgroundAudioManager`）：

```ts
// uni-app
const audio = uni.createInnerAudioContext()
audio.src = 'https://example.com/a.mp3'
audio.play()
audio.onEnded(() => { /* ... */ })
```

## 4. v-html 处理

`v-html` 在 H5 端可用，**小程序端不可用**。迁移时必须处理：

| 场景 | 方案 |
|------|------|
| 纯展示富文本（HTML 字符串） | `rich-text` 组件：`<rich-text :nodes="htmlStr" />` |
| 图文混排、链接可点 | `uparse` 等插件（插件市场） |
| App 端 | 可保留 v-html（v3 编译器） |

```html
<!-- H5 -->
<div v-html="content"></div>

<!-- uni-app（跨端） -->
<rich-text :nodes="content" />
```

注意：rich-text 的 nodes 支持字符串和节点数组，`img` 标签内的路径需可访问（网络图或 /static 绝对路径）。

## 5. Web API 替换表（js 转换核心）

uni-app 非 H5 端（App + 小程序）不支持 `window`、`navigator`、`document` 等 web 专用对象。常见 API 对照：

### 5.1 window 相关

| H5 API | uni-app 替代 |
|--------|------------|
| `axios` / `$.ajax` / `fetch` | `uni.request`（目标项目已有 request.ts 封装，直接用） |
| `localStorage` / `sessionStorage` / `cookie` | `uni.setStorageSync` / `uni.getStorageSync` / `uni.removeStorageSync` |
| `alert()` / `confirm()` | `uni.showModal` |
| `window.addEventListener('resize', ...)` | `uni.onWindowResize(cb)` / `uni.offWindowResize(cb)` |
| `window.open(url)` | `uni.navigateTo({ url })`（或 web-view 页面） |
| `window.location.href = url` | `uni.redirectTo({ url })` 或 web-view |
| `window.location.reload()` | 无直接 API，可考虑页面数据重拉（onShow 中重取数据） |
| `document.title = '...'` | `uni.setNavigationBarTitle({ title })` |
| `setTimeout` / `setInterval` | 保持不变 |
| `window.getComputedStyle` | 无替代，改用数据驱动 |

### 5.2 navigator 相关

| H5 API | uni-app 替代 |
|--------|------------|
| `navigator.geolocation` | `uni.getLocation({ type: 'gcj02' })` |
| `navigator.userAgent` 判断设备 | `uni.getSystemInfoSync().platform`（`ios` / `android`）或 `uni.getDeviceInfo()` |
| `navigator.clipboard` | `uni.setClipboardData` |
| `navigator.onLine` | `uni.getNetworkType` / `uni.onNetworkStatusChange` |

设备/平台判断标准写法（替代 userAgent）：

```ts
// H5
const isIOS = /ios|iphone|ipad/i.test(navigator.userAgent)

// uni-app（推荐运行时检测）
const { platform } = uni.getSystemInfoSync()
const isIOS = platform === 'ios'
const isAndroid = platform === 'android'
```

### 5.3 DOM 相关

| H5 API | uni-app 替代 |
|--------|------------|
| `document.getElementById` / `querySelector`（改内容） | 不允许，改为 Vue 数据绑定驱动视图 |
| `el.offsetWidth` / `getBoundingClientRect()`（量尺寸） | `uni.createSelectorQuery()` |
| `el.addEventListener` | 用 Vue 的 `@click` 等模板事件 |
| jQuery 等 DOM 操作库 | 移除，改纯数据绑定 |

获取元素尺寸的标准写法：

```ts
// <script setup> 中获取节点尺寸（替代 getBoundingClientRect）
import { getCurrentInstance } from 'vue'
const instance = getCurrentInstance()
// 页面级查询可省略 .in()；组件内查询必须 .in(instance?.proxy) 限定作用域
const query = uni.createSelectorQuery().in(instance?.proxy)
query.select('.my-element').boundingClientRect((rect) => {
  console.log(rect.width, rect.height)
}).exec()
```

注意：H5 中的 `this` 指向（Options API）在 `<script setup>` 里不存在，必须用 `getCurrentInstance()` 获取组件实例。

### 5.4 专用能力 API

H5 中的 canvas、video、websocket、webgl、web bluetooth、nfc 等能力，uni-app 均有对应 API：

| Web 能力 | uni-app API |
|---------|------------|
| WebSocket | `uni.connectSocket` / `uni.onSocketMessage` 等 |
| canvas 绘制 | `uni.createCanvasContext` 或 canvas 2d（`canvas-id` / type="2d"） |
| video | `<video>` 组件（1.5MB 内短视频建议用 video 组件） |
| audio | `uni.createInnerAudioContext` |
| webgl | canvas 2d/3d 上下文（谨慎，低端机兼容性差） |
| web bluetooth/nfc | `uni.openBluetoothAdapter` 等 API |

## 6. CSS 约束与兼容

### 6.1 选择器限制

- **不支持 `*` 通配选择器**（如 `* { box-sizing: border-box }`），需要改写为显式元素/类选择器
- **没有 `body` 元素选择器**，改用 `page` 选择器（编译到非 H5 端时编译器可自动处理，但显式改写更保险）
- 元素选择器需用 uni-app 标签：`div` → `view`、`span`/`font` → `text`、`a` → `navigator`、`img` → `image`（编译器可自动处理，显式改写更保险）

```scss
// H5
* { box-sizing: border-box; }
body { background: #f5f5f5; font-size: 14px; }
div.item span { color: red; }

// uni-app
view, text, image { box-sizing: border-box; }  // 显式枚举替代 *
page { background: #f5f5f5; font-size: 28rpx; }
view.item text { color: red; }
```

### 6.2 CSS 兼容性

- 避免使用过新的 CSS 语法（CSS 领域最新特性），低端 Android（4.4、5.x）在 App 端会有样式错误
- 发布 App 端如需抹平浏览器内核差异，可考虑接入 x5 内核（参考 DCloud 文档 36806）
- UnoCSS 默认产物兼容性较好，新增样式优先 UnoCSS

## 7. 三方库处理

源项目若依赖了内部使用 dom/window/navigator 的三方 js 库（非纯逻辑库）：

1. **优先**：去 uni-app 插件市场（https://ext.dcloud.net.cn/）寻找同类替代
2. **仅 H5 端使用**：可保留原库（仅 H5 端运行时用条件编译包裹）
3. **App 端必须用 for-web 库**：使用 renderjs 引入（https://uniapp.dcloud.io/frame?id=renderjs）
4. **标记人工确认**：无法替代且必须跨端时，列入"需人工确认"清单

常见库替代建议：

| H5 常见库 | uni-app 建议 |
|----------|-------------|
| axios | 用目标项目 request.ts（uni.request 封装） |
| js-cookie | uni.setStorageSync / uni.getStorageSync |
| mitt 事件总线 | uni.$on / uni.$emit / uni.$off |
| docx-preview / vue-pdf-embed 等 web 渲染库 | 插件市场找替代（如 pdf 预览用 web-view 或专用插件） |
| dayjs / lodash 等纯逻辑库 | 可直接保留（无 dom 依赖） |

## 8. App 级与页面级生命周期

### 8.1 App 级（App.vue，一般不迁移）

| 钩子 | 用途 |
|------|------|
| `onLaunch` | 应用启动（仅一次），原 main.ts 初始化逻辑放这里 |
| `onShow` | 应用从后台切前台 |
| `onHide` | 应用切后台 |

### 8.2 页面级（src/pages/ 下的页面）

| 钩子 | 用途 | 迁移来源 |
|------|------|---------|
| `onLoad(options)` | 页面加载，接收路由参数 | `onBeforeMount` / created 数据请求 |
| `onShow` | 每次页面展示 | `onMounted`（展示语义部分） |
| `onReady` | 页面初次渲染完成 | 需要获取节点尺寸时用（配合 SelectorQuery） |
| `onHide` | 页面进入后台 | — |
| `onUnload` | 页面卸载 | `onUnmounted` / `onBeforeUnmount` |
| `onReachBottom` | 页面触底 | 分页滚动加载 |
| `onPullDownRefresh` | 下拉刷新 | 自定义下拉逻辑（需在 pages.json 开启 enablePullDownRefresh） |

页面数据请求的官方建议：H5 一般在 created/mounted 请求数据；uni-app 页面在 **onLoad 或 onShow** 中请求（组件仍然 created/mounted）。

### 8.3 组件级（src/components/ 下）

保持 Vue 原生生命周期（`onMounted` / `onUnmounted` 等），不混用 uni 页面生命周期。

## 9. data 写法约束

少量不常用的 vue 语法在非 H5 端不支持。**`data` 必须以函数 return 的方式编写**（Vue SFC 的 `<script setup>` 天然满足），禁止对象式 data。
