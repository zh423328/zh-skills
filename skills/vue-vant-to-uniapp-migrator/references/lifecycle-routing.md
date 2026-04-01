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

## 路由

- `router.push(...)` -> `uni.navigateTo(...)`
- `router.replace(...)` -> `uni.redirectTo(...)`
- `router.go(-1)` -> `uni.navigateBack()`
- `router.currentRoute.value.query` -> `onLoad((options) => { ... })`

路由参数迁移时：
- 在 setup 逻辑中把 `options` 归一化为业务需要的类型。
- 保持函数命名和业务分支判断不变。
