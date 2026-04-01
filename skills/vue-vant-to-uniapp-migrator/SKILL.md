---
name: vue-vant-to-uniapp-migrator
description: 将标准 Vue 3 + Vant + H5 页面迁移为通过 npx @zayn919/create-zh-uni 创建的默认 uni-app + wot-design-uni + Vue 3 + TypeScript + UnoCSS 项目。用于页面迁移时转换组件、生命周期、路由、分页与样式，同时保留业务逻辑和函数名，不引入自定义组件，并保持默认脚手架结构。
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

1. 创建或确认目标项目
- 仅允许使用以下方式创建项目：
```bash
npx @zayn919/create-zh-uni <项目名>
# 或
npx @zayn919/create-zh-uni <项目名> --template base-wotui
```
- 安装后调用 pnpm 安装`npx @dcloudio/uvm@latest` 进行一次 uvm 编译。
- 保持默认脚手架目录结构，不重构目录。
- 将迁移页面放入默认 uni-app 页面/分包约定位置。

1.1 目录与资源映射规则
- 页面文件：`src/<任意页面目录>/**/*.vue` -> `src/pages/**/<同名文件>.vue`
- 图片资源：源项目页面引用图片 -> 目标项目 `src/static/**`
- 图片路径改写后要求可在 H5/小程序端正常访问。

1. 转换模板标签
- 替换基础标签：
  - `div` -> `view`
  - `span` -> `text`
  - `img` -> `image`
- 保持语义结构与事件绑定不变。

1. 转换组件层（仅官方组件）
- 仅使用 wot-design-uni 官方组件。
- 不允许新增自定义替代组件。
- 映射规则见 `references/component-map.md`。

1. 转换生命周期与路由
- 页面生命周期使用 uni-app API，避免页面逻辑混用 Vue-only 生命周期。
- 使用 `onLoad` 处理路由参数与首屏初始化。
- 路由调用替换为 `uni.navigateTo` / `uni.redirectTo` / `uni.navigateBack`。
- 详细规则见 `references/lifecycle-routing.md`。

1. 转换分页与触底加载
- 使用 `onReachBottom` 处理触底分页,不能设置页面高度, 否则页面会被撑开,触发onReachBottom事件
- `wd-loadmore` 仅做加载状态展示，不包裹列表容器。
- 保持原分页函数名和状态流转语义。

1. 转换样式策略
- 尽量保留原 SCSS。
- 按 `1px = 2rpx` 转换尺寸。
- 需要时保留 `::v-deep()`。
- 新增样式优先使用 UnoCSS。

1. 保持业务逻辑与类型稳定
- 函数名保持不变。
- 文件名保持不变。
- 样式类名保持不变。
- 事件处理与数据处理流程保持不变。
- 接口返回结构不确定时，可使用 `any` 保证迁移期编译通过。
- 边界数组类型可使用 `as any[]`。

1. 处理跨平台差异
- 仅在必要处添加 `#ifdef` / `#endif`。
- 优先保持共用逻辑，最小化平台分支。

1. 运行迁移审计
- 执行 `scripts/migration_audit.sh <目标路径>`。
- 所有 `ERROR` 必须清零后再结束迁移。

## 输出约定

每次页面迁移完成后输出：
- 已迁移文件清单
- 仍需人工确认项（如有）
- 审计结果摘要（`ERROR` / `WARN` 数量）

## 参考资料

- 组件映射：`references/component-map.md`
- 生命周期与路由：`references/lifecycle-routing.md`
- 迁移检查清单：`references/migration-checklist.md`
