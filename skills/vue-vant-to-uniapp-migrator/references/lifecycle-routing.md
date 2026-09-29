# 生命周期与路由迁移规则

## 生命周期

页面加载/展示相关逻辑使用 `@dcloudio/uni-app` 的页面生命周期。

```ts
import { onLoad, onShow, onUnload, onReachBottom } from '@dcloudio/uni-app'
```

迁移建议：
- `onBeforeMount` -> `onLoad`
- `onMounted` -> `onShow`（仅用于页面展示语义）
- `onUnmounted` -> `onUnload`

不要把页面生命周期逻辑混入 Vue-only 生命周期。

## 补充钩子

| 钩子 | 使用场景 |
|------|---------|
| `onReady` | 页面初次渲染完成，需要获取节点尺寸做布局时配合 `uni.createSelectorQuery` 使用 |
| `onPullDownRefresh` | 下拉刷新，需先在 pages.json 对应页面开启 `enablePullDownRefresh` |
| `onPageScroll` | 监听页面滚动（替代 H5 的 window scroll 监听） |
| `onShareAppMessage` | 小程序分享（按需） |

## App 级生命周期（App.vue）

App 级钩子写在 `App.vue` 中（配合 `<script setup>` 需从 `@dcloudio/uni-app` 导入）：

| 钩子 | 用途 | H5 来源 |
|------|------|---------|
| `onLaunch` | 应用启动执行一次 | `main.ts` / `App.vue` 中的初始化逻辑 |
| `onShow` | 应用从后台切前台 | `document visibilitychange` 监听 |
| `onHide` | 应用切后台 | 同上 |

注意：本技能默认不迁移 `App.vue` / `main.ts`（两端入口差异大）。如源项目入口存在全局初始化逻辑（如全局错误上报、SSO），记录到"需人工确认"清单。

## 数据请求位置（官方建议）

- 页面：在 `onLoad` 或 `onShow` 中请求数据（组件仍然是 `created` / `mounted`）
- `onLoad` 适合首屏一次性加载 + 接收路由参数
- `onShow` 适合每次展示都需刷新的数据

## 路由

- `router.push(...)` -> `uni.navigateTo(...)`
- `router.replace(...)` -> `uni.redirectTo(...)`
- `router.go(-1)` -> `uni.navigateBack()`
- `router.currentRoute.value.query` -> `onLoad((options) => { ... })`

路由参数迁移时：
- 在 setup 逻辑中把 `options` 归一化为业务需要的类型。
- 保持函数命名和业务分支判断不变。
