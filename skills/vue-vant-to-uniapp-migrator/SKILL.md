---
name: vue-vant-to-uniapp-migrator
description: 将标准 Vue 3 + Vant + H5 页面迁移为通过 npx @zayn919/create-zh-uni 创建的默认 uni-app + wot-design-uni + Vue 3 + TypeScript + UnoCSS 项目。用于页面迁移时转换组件、生命周期、路由、分页与样式，同时保留业务逻辑和函数名，不引入自定义组件，并保持默认脚手架结构。不内置任何具体项目路径，源/目标项目由用户在对话中提供或从工作目录推断。
allowed-tools: 
disable: false
---

# Vue Vant 到 UniApp 迁移技能

在把 Vue3 + Vant H5 页面迁移到默认 `create-zh-uni` 项目时使用本流程。必须保留业务逻辑和函数名，不引入自定义组件。

## 硬性约束

- 必须保留原函数名，不允许重命名业务函数。
- 必须保留原文件名（仅目录位置迁移，不改文件基名）。
- 必须保留原样式类名/样式标识名（避免影响现有业务选择器与逻辑绑定）。
- 迁移时禁止修改目标项目已有的新版本 `request.ts`（请求封装文件保持原样）。
- 源页面目录（不限于 `src/views`，任何页面目录都算）统一迁移到目标项目 `src/pages` 体系下。
- 源代码中的图片资源统一迁移到目标项目 `src/static` 下，并同步修正引用路径。

## 工作流

0. 确认源项目与目标项目路径
- 源项目与目标项目路径由用户在对话中提供；未提供时，以当前工作目录推断，并与用户确认其角色（源项目还是目标项目）。
- 本技能不内置任何具体项目路径，每次迁移以本次对话提供的信息为准。

1. 创建或确认目标项目
- 目标项目必须由 `npx @zayn919/create-zh-uni` 创建。
- 若用户已提供已创建的目标项目路径：直接使用，不重新创建。
- 若尚无目标项目，使用以下命令创建：
```bash
npx @zayn919/create-zh-uni <项目名>
# 或
npx @zayn919/create-zh-uni <项目名> --template base-wotui
```
- 安装后执行一次 uvm 编译：
```bash
npx @dcloudio/uvm@latest
```
- 保持默认脚手架目录结构，不重构目录。
- 将迁移页面放入默认 uni-app 页面/分包约定位置。

1.1 目录与资源映射规则
- 页面文件：`src/<任意页面目录>/**/*.vue` -> `src/pages/**/<同名文件>.vue`
- 图片资源：源项目页面引用图片 -> 目标项目 `src/static/**`
- 图片路径改写后要求可在 H5/小程序端正常访问。

2. 转换模板标签
- 替换基础标签（完整表见 `references/web-to-uni-basics.md`）：
  - `div` -> `view`
  - `span`、`font` -> `text`
  - `img` -> `image`（必须加 `mode` 属性）
  - `a` -> 站内跳转用 `navigator`，动作型链接用 `wd-button type="text"`
  - `select` -> `wd-picker`（优先）或原生 `picker`
  - `iframe` -> `web-view`
  - `ul/ol/li` -> `view`
- 滚动与滑动（详见 `references/web-to-uni-basics.md`）：
  - 固定高度 + `overflow: auto` 的区域滚动容器 -> `scroll-view`（必须 `scroll-y`/`scroll-x` 并保留固定高度）
  - 左右/上下滑动切换（banner、引导页、tab 滑动）-> `swiper` / `swiper-item`，禁止用 div + touch 事件模拟
- 表单细节：
  - `<input type="search">` -> 普通 `input` + `confirm-type="search"` + `@confirm`（不再是 `@keyup.enter`）
  - `v-html` 小程序端不可用 -> `<rich-text :nodes="htmlStr" />`（App 端可保留 v-html，用 `#ifdef` 区分）
- 保持语义结构与事件绑定不变。

3. 转换 Web API（js 层）
- 完整替换表见 `references/web-to-uni-basics.md` 第 5 节，重点：
  - `window.addEventListener('resize')` -> `uni.onWindowResize`（ECharts 自适应场景高频）
  - `navigator.geolocation` -> `uni.getLocation`
  - `navigator.userAgent` 判断设备 -> `uni.getSystemInfoSync().platform`（运行时检测，禁止正则 UA）
  - 量尺寸的 DOM 操作（`getBoundingClientRect` 等）-> `uni.createSelectorQuery`
  - WebSocket -> `uni.connectSocket` 系列
  - `alert`/`confirm` -> `uni.showModal`
- 混写 jQuery 等 DOM 操作库的，改为纯 Vue 数据绑定。

4. 转换组件层（仅官方组件）
- 仅使用 wot-design-uni 官方组件。
- 不允许新增自定义替代组件。
- 映射规则见 `references/component-map.md`。
- 三方库若内部依赖 dom/window/navigator：优先插件市场替代；仅 H5 端可用条件编译包裹；App 端必须用时走 renderjs；无法替代时列入"需人工确认"。

5. 转换生命周期与路由
- 页面生命周期使用 uni-app API，避免页面逻辑混用 Vue-only 生命周期。
- 使用 `onLoad` 处理路由参数与首屏初始化（数据请求放 `onLoad`/`onShow`，组件仍用 created/mounted）。
- 路由调用替换为 `uni.navigateTo` / `uni.redirectTo` / `uni.navigateBack`。
- 需要获取节点尺寸做布局的，用 `onReady` + `uni.createSelectorQuery`。
- 详细规则见 `references/lifecycle-routing.md`。

6. 转换分页与触底加载
- 使用 `onReachBottom` 处理触底分页,不能设置页面高度, 否则页面会被撑开,触发onReachBottom事件
- `wd-loadmore` 仅做加载状态展示，不包裹列表容器。
- 保持原分页函数名和状态流转语义。
- H5 中自定义下拉刷新逻辑可对应 `onPullDownRefresh`（需在 pages.json 对应页面开启 `enablePullDownRefresh`）。

7. 转换样式策略
- 尽量保留原 SCSS。
- 按 `1px = 2rpx` 转换尺寸（`border: 1px solid` hairline 除外）。
- 需要时保留 `::v-deep()`。
- 新增样式优先使用 UnoCSS。
- 选择器约束（详见 `references/web-to-uni-basics.md` 第 6 节）：
  - 不支持 `*` 通配选择器，改显式枚举（`view, text, image {...}`）
  - `body` 选择器改 `page` 选择器
  - 元素选择器需用 uni 标签（`div` -> `view` 等，编译器可自动处理，显式改写更保险）
- 避免过新的 CSS 语法，低端 Android 端会样式错误。

8. 保持业务逻辑与类型稳定
- 函数名保持不变。
- 文件名保持不变。
- 样式类名保持不变。
- 事件处理与数据处理流程保持不变。
- 接口返回结构不确定时，可使用 `any` 保证迁移期编译通过。
- 边界数组类型可使用 `as any[]`。

9. 处理跨平台差异
- 仅在必要处添加 `#ifdef` / `#endif`。
- 优先保持共用逻辑，最小化平台分支。

10. 运行迁移审计
- 执行 `scripts/migration_audit.sh <目标路径>`。
- 所有 `ERROR` 必须清零后再结束迁移。
- 审计中"页面生命周期"检查仅针对 `src/pages/` 下文件（组件保留 Vue 原生生命周期是合法的）；`v-html` 改为 rich-text 或 `#ifdef` 限定非小程序端后即视为处理。

## 输出约定

每次页面迁移完成后输出：
- 已迁移文件清单
- 仍需人工确认项（如有）
- 审计结果摘要（`ERROR` / `WARN` 数量）

## 参考资料

- Web → uni 基础转换规则（标签/Web API/CSS/三方库，来自 DCloud 官方指南 36174）：`references/web-to-uni-basics.md`
- 组件映射：`references/component-map.md`
- 生命周期与路由：`references/lifecycle-routing.md`
- 迁移检查清单：`references/migration-checklist.md`

### 官方文档
- [vue h5 转 uni-app 指南（DCloud 官方，本 skill 规则来源）](https://ask.dcloud.net.cn/article/36174)
- [uni-app 官方文档](https://uniapp.dcloud.io/)
- [wot-ui UI 文档](https://v1.wot-ui.cn/)
- [Vue 官方文档](https://cn.vuejs.org/)