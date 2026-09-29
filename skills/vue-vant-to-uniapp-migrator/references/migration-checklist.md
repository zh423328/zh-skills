# 迁移检查清单

## 必须通过

- 目标项目由 `npx @zayn919/create-zh-uni` 创建。
- 默认脚手架结构保持不变。
- 未引入自定义替代组件。
- 原函数名保持不变。
- 原文件名保持不变（仅目录迁移，不改文件基名）。
- 原样式类名/样式标识名保持不变。
- 目标项目新版本 `request.ts` 未被修改（请求封装保持原样）。
- `van-nav-bar` 已移除，使用 uni 默认导航栏。
- `div/span/img` 已转换为 `view/text/image`。
- Vant 组件已替换为官方 wot 组件。
- 路由调用已迁移为 uni 导航 API。
- 页面参数在 `onLoad` 中读取。
- 触底分页使用 `onReachBottom`。
- `wd-loadmore` 仅用于状态展示，不包裹列表。
- SCSS 尽量保留，尺寸按 `1px = 2rpx` 规则转换。
- 需要 mixin 时存在 `@import '@/static/sass/mixins.scss';`。
- 新增样式优先 UnoCSS。
- 函数名未改变。
- 业务流程未改变。
- 页面目录已迁移到 `src/pages` 体系（不限原目录名是否为 `views`）。
- 页面引用图片资源已迁移到 `src/static`，且路径已完成改写。
- `reactive` 中包含所有模板绑定字段。
- 迁移边界类型已稳定（仅必要处使用 `any`、`as any[]`）。
- 平台差异仅在必要处用 `#ifdef`/`#endif`。

## 来自 DCloud 官方指南的补充检查项

- `select` 标签已替换为 `wd-picker` / 原生 `picker`。
- 固定高度 + `overflow: auto` 容器已改为 `scroll-view`（带 `scroll-y`）。
- 滑动切换（banner/引导页/tab）已改为 `swiper`，无 div + touch 模拟残留。
- `<input type="search">` 已改为 `confirm-type="search"` + `@confirm`。
- `v-html` 已改为 `rich-text`，或用 `#ifdef` 限定非小程序端（App 端可保留）。
- `window.addEventListener('resize')` 已改为 `uni.onWindowResize`。
- `navigator.geolocation` 已改为 `uni.getLocation`。
- `navigator.userAgent` 设备判断已改为 `uni.getSystemInfoSync().platform`。
- DOM 尺寸获取已改为 `uni.createSelectorQuery`（`<script setup>` 中配合 `getCurrentInstance()`）。
- WebSocket 已改为 `uni.connectSocket` 系列。
- input 的 H5 type 值（email/tel/url/password）已按小程序规则处理（改 text + JS 校验 / password 布尔属性）。
- `<audio>` 标签已改为 `uni.createInnerAudioContext` API 方式。
- 样式中无 `*` 通配选择器，`body` 选择器已改为 `page`。
- 未使用过新的 CSS 语法（避免低端 Android 样式错误）。
- 三方库无 dom/window/navigator 依赖（有的话已走替代/renderjs/人工确认）。
- `data` 为函数 return 写法（`<script setup>` 天然满足）。

## 建议验证

```bash
bash scripts/migration_audit.sh <目标项目或子目录>
```

人工抽查：
- 组件事件映射后的行为一致性
- `::v-deep` 类名替换是否正确
- 空态与加载完成态是否符合预期
