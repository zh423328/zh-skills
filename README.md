# zh-skill — Agent Skills 合集

本仓库用于沉淀与维护自定义的 AI 编程助手（ZCode / Claude Code）skill。每个 skill 是一个独立目录，包含触发描述（`SKILL.md`）、参考资料（`references/`）与可执行脚本（`scripts/`）。

## 目录结构

```
zh-skill/
├── README.md                        # 本文件：仓库总览与各 skill 简介
└── skills/
    ├── fastapi-init-skill/          # FastAPI 项目一键初始化
    ├── article-auto-publisher/      # 主题自动写作与发布
    └── vue-vant-to-uniapp-migrator/ # Vue Vant 页面迁移 UniApp
```

## Skill 一览

### 1. [fastapi-init-skill](skills/fastapi-init-skill/) — FastAPI 项目一键初始化

面向零基础用户，说一句"帮我搭一个 FastAPI 项目"即可从环境探测、自动安装到服务启动一条命令跑通。

- **生成的骨架**：对齐 FastAPI 官方模板主流分层（`api / core / crud / models / schemas / db`），内置 JWT 鉴权、示例 CRUD、统一响应 `{ code, message, data }`、Swagger 文档、一键启动脚本（`restart.sh` / `restart.bat`）、Docker 编排
- **数据库**：MySQL（默认）/ PostgreSQL / MongoDB / 无数据库，四选一
- **触发词**：`FastAPI 脚手架`、`初始化 FastAPI 项目`、`帮我搭一个 FastAPI`、`fastapi init` 等
- 📖 **详细介绍**：[skills/fastapi-init-skill/README.md](skills/fastapi-init-skill/README.md)（完整功能规格见 [SPEC.md](skills/fastapi-init-skill/SPEC.md)）

### 2. [article-auto-publisher](skills/article-auto-publisher/) — 主题自动写作与发布

主题驱动的一键写作发布：用户只给一个主题，大模型生成标题、摘要与 HTML 正文，再由脚本登录本地 AI BI System 后台并调用文章发布接口完成自动发布。

- **典型场景**：验证文章模块接口链路、快速初始化后台文章数据、内容运营流程演示
- **触发词**：`帮我写一篇关于 XX 的文章并发布`、`自动发布文章` 等
- 📖 **详细介绍**：[skills/article-auto-publisher/README.md](skills/article-auto-publisher/README.md)

### 3. [vue-vant-to-uniapp-migrator](skills/vue-vant-to-uniapp-migrator/) — Vue Vant 页面迁移 UniApp

将标准 Vue 3 + Vant + H5 页面迁移到 `create-zh-uni` 默认脚手架（uni-app + wot-design-uni + Vue 3 + TypeScript + UnoCSS），转换组件标签、生命周期、路由、分页与样式。

- **硬性约束**：保留业务逻辑、函数名、文件名与样式类名；不引入自定义组件；不改动目标项目请求封装
- **触发词**：`迁移页面`、`Vant 转 uni-app`、`H5 迁移到小程序` 等
- 📖 **详细介绍**：[skills/vue-vant-to-uniapp-migrator/README.md](skills/vue-vant-to-uniapp-migrator/README.md)

## 如何使用

1. 将需要的 skill 目录复制或链接到 agent 的技能目录（如 `~/.agents/skills/`），或按所用客户端的 skill 安装方式加载；
2. 对话中使用上表中的触发词，agent 会自动匹配对应 skill；
3. 详细用法、参数与注意事项见各 skill 的「详细介绍」链接。
