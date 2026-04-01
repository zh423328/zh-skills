# Vue-Vant 到 UniApp Skill 操作文档

## 1. 文档目的

本文用于指导团队使用 Skill：`vue-vant-to-uniapp-migrator`，将 Vue3 + Vant + H5 项目迁移到 `create-zh-uni` 默认结构项目（uni-app + wot-design-uni + Vue3 + TS + UnoCSS）。

---

## 2. Skill 信息

- Skill 名称：`vue-vant-to-uniapp-migrator`
- Skill 文件路径：`/Users/zhenghui/.codex/skills/vue-vant-to-uniapp-migrator/SKILL.md`

---

## 3. 何时使用

在以下场景使用本 Skill：
- 需要将旧项目页面从 `src/views`（或任意页面目录）迁移到 `src/pages`
- 需要将旧资源路径从 `@/assets` 转换为 `@/static`
- 需要将 API 路径从 `@/apis` 转换为 `@/api/ahx_api/apis`
- 需要按规则逐页完成 Vant -> wot-design-uni 迁移

---

## 4. 核心硬约束（必须遵守）

- 保留函数名（不重命名业务函数）
- 保留文件名（只迁移目录位置，不改文件基名）
- 保留样式类名/样式标识名
- 页面统一落到 `src/pages`
- 图片资源统一落到 `src/static`
- 禁止修改目标项目的新版本 `request.ts`
- 不引入自定义替代组件（除非用户明确要求）

---

## 5. 使用方式（对话触发）

在对话里明确写：

```text
使用 $vue-vant-to-uniapp-migrator 把 <源路径> 迁移到 <目标路径>，保留函数名/文件名/样式名，不修改 request.ts
```

推荐模板：

```text
使用 $vue-vant-to-uniapp-migrator 把 /path/source-project 迁移到 /path/target-project。
要求：保持 create-zh-uni 默认结构；保留函数名、文件名、样式名；
页面迁移到 src/pages；图片迁移到 src/static；
不要修改 src/utils/request.ts；迁移后输出审计结果与待人工确认项。
```

---

## 6. 标准执行流程

1. 初始化目标项目（若目标不存在）
- 使用：
```bash
npx @zayn919/create-zh-uni <project-name> --template base-wotui
```

2. 结构迁移
- 页面：`src/<任意页面目录>/**/*.vue` -> `src/pages/**`
- 图片：`src/assets/**` -> `src/static/**`
- API：`src/apis/**` -> `src/api/ahx_api/apis/**`

3. 引用替换
- `@/apis/` -> `@/api/ahx_api/apis/`
- `@/assets/` -> `@/static/`
- `vue-router` 迁移到 uni 路由方案（或兼容层）

4. 组件迁移
- 按 `component-map.md` 做 A/B/C 三类转换
- 优先一一映射，近似映射需核对事件与行为

5. 迁移后审计
- 执行：
```bash
bash /Users/zhenghui/.codex/skills/vue-vant-to-uniapp-migrator/scripts/migration_audit.sh <target-path>
```

6. 输出迁移报告
- 已迁移文件列表
- 错误/警告汇总
- 待人工确认项

---

## 7. 推荐工作方式

- 先做“样板页”（1~2 页），确认规则后再批量
- 每完成一组页面就跑一次审计
- 对“无直接映射组件”先走评估模板，再实施

---

## 8. 常见问题

### Q1：`create-zh-uni` 是 MCP 吗？
不是。它是 npm 脚手架命令，通常通过 `npx @zayn919/create-zh-uni` 调用。

### Q2：为什么强调不改 `request.ts`？
因为目标项目请求层通常是新版本封装，改动会引入额外回归风险。迁移只应改业务页面与业务 API 层引用。

### Q3：是否必须一次性全量迁完？
不建议。推荐“分批迁移 + 分批审计 + 分批验收”。

---

## 9. 验收清单（简版）

- 页面是否在 `src/pages`
- 资源是否在 `src/static`
- 函数名/文件名/样式名是否保持
- `request.ts` 是否未改动
- 是否仍有 `van-*` 残留
- 路由、生命周期、分页是否符合 uni-app 规则

