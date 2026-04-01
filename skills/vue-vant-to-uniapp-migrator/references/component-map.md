# Vant 到 Wot 组件迁移映射（通用版）

仅使用 wot-design-uni 官方组件。除非用户明确要求，否则不要创建自定义包装组件。

## A 类：一一对应映射（优先使用）

| Vant 组件 | 推荐迁移 |
|---|---|
| `van-form` | `wd-form` |
| `van-tabs` | `wd-tabs` |
| `van-tab` | `wd-tab` |
| `van-collapse` | `wd-collapse` |
| `van-collapse-item` | `wd-collapse-item` |
| `van-popup` | `wd-popup` |
| `van-picker` | `wd-picker` |
| `van-cell` | `wd-cell` |
| `van-field` | `wd-input` |
| `van-button` | `wd-button` |
| `van-tag` | `wd-tag` |
| `van-dropdown-menu` | `wd-drop-menu` |
| `van-dropdown-item` | `wd-drop-menu-item` |
| `van-calendar` | `wd-calendar` |

### A 类重点：Form 校验迁移示例

从 `van-form + van-field` 迁移到 `wd-form + wd-input` 时，关键点是：
- `wd-form` 用 `:model` 挂载表单模型。
- 字段组件用 `prop` 关联规则字段。
- 校验规则可放 `wd-form :rules`，提交时调用 `validate()`。

```vue
<template>
  <wd-form ref="formRef" :model="formModel" :rules="formRules" errorType="message">
    <wd-cell-group border>
      <wd-input
        label="用户名"
        prop="username"
        v-model="formModel.username"
        placeholder="请输入用户名"
      />
      <wd-input
        label="手机号"
        prop="mobile"
        v-model="formModel.mobile"
        placeholder="请输入手机号"
      />
    </wd-cell-group>

    <view class="pt-24rpx">
      <wd-button type="primary" block @click="onSubmit">提交</wd-button>
    </view>
  </wd-form>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { FormRules } from '@/uni_modules/wot-design-uni/components/wd-form/types'

const formRef = ref()

const formModel = reactive({
  username: '',
  mobile: ''
})

const formRules: FormRules = {
  username: [{ required: true, message: '请填写用户名' }],
  mobile: [
    { required: true, message: '请填写手机号' },
    { pattern: /^1\\d{10}$/, message: '手机号格式不正确' }
  ]
}

const onSubmit = async () => {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  // 校验通过后执行原业务提交逻辑
}
</script>
```

## B 类：近似映射（可迁移，但需核对行为差异）

| Vant 组件 | 推荐迁移 | 需要重点核对 |
|---|---|---|
| `van-search` | `wd-search` | `v-model` 字段、确认事件与清空事件命名 |
| `van-dialog` | `wd-message-box` 或消息能力 | 打开方式（组件/方法）、确认取消回调时机 |
| `van-list` | `v-for` 列表 + `wd-loadmore` 状态 | `wd-loadmore` 只展示状态，不包裹列表容器 |

迁移原则：
- 先保留原函数名和业务流程。
- 再调整事件名、参数结构和样式细节。

## C 类：无直接映射或不建议直接映射

| Vant 组件 | 处理建议 |
|---|---|
| `van-nav-bar` | 移除，使用 uni-app 默认导航栏 |
| 其他未在 A/B 类列出的组件 | 按“未覆盖组件处理模板”走评估与替代 |

补充规则：
- `::v-deep` 中若存在 `van-` 类名前缀，按目标组件改为 `wd-` 或目标类名。
- 无法一一对应时，优先保证行为一致，再优化外观一致。

## 未覆盖组件处理模板

当遇到未收录组件时，按下面模板记录与执行：

```md
### 组件迁移评估：<van-xxx>

1. 使用场景
- 原页面文件：<path>
- 核心职责：<展示/输入/弹窗/选择/反馈>

2. 关键能力清单
- 必要能力1：<例如：多选、异步加载、虚拟滚动>
- 必要能力2：<例如：表单校验联动>
- 必要能力3：<例如：跨平台差异行为>

3. 迁移方案
- 优先方案：<wd-yyy / uni 原生能力 / 组合实现>
- 备选方案：<方案B>
- 不采用原因：<若有>

4. 事件与数据映射
- 输入输出字段映射：<old -> new>
- 事件映射：<old event -> new event>
- 生命周期/路由影响：<onLoad/onShow/onUnload 等>

5. 验收点
- 业务流程一致：<是/否>
- 函数名保持：<是/否>
- 跨平台验证：<H5/小程序/APP>
- 审计结果：<ERROR/WARN>
```

执行要求：
- 先提交评估模板，再实施迁移。
- 若优先方案需要引入自定义组件，必须先得到用户明确同意。
