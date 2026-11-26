# AGENTS.md — 全局红线与安全触发条件

> 作用域：本机所有项目、所有会话。更具体的项目 `AGENTS.md` 优先。
> 项目规则若**降低**本文档的红线，属于安全弱化：MUST 先向用户说明风险并取得确认。

## 0. 什么时候必须先加载 `server-security`

本次任务涉及以下任一项时，动手前 MUST 先读取 skill `server-security`
（`~/.agents/skills/server-security/SKILL.md`）全文：

- 服务端接口、路由、中间件、鉴权授权、会话
- 数据库读写、ORM 模型、迁移、多租户、缓存
- 文件上传 / 下载 / 导出、静态资源、对象存储
- 密钥、凭证、加密、Token、Cookie
- 部署、容器、反向代理、CI、引入新依赖
- 项目包含 AI / LLM / Agent 能力

纯前端样式、纯文档撰写、知识库整理类任务**不适用**：不要套用服务端规则，不要输出安全自检清单。

## 1. 八条红线（MUST / MUST NOT）

1. MUST NOT 把密钥、Token、密码、连接串写进代码、示例、测试、日志或前端产物。
2. MUST NOT 把上传或导出的文件放进 Web 根、公开静态目录或公共读 bucket；一律私有存储 + 鉴权下载或短时效签名 URL。
3. MUST NOT 用字符串拼接构造 SQL、shell 命令或文件路径：SQL 用参数化查询，命令用参数数组，路径规范化后校验仍在基目录内。
4. 按 ID 访问资源 MUST 做对象级授权（owner / tenant / ACL），MUST NOT 只校验"已登录"。
5. MUST NOT 信任请求里的 `user_id` / `tenant_id` / `role` / `price` / `status`；请求模型 MUST 用显式白名单字段。
6. 认证授权 MUST 用成熟库；MUST NOT 自研加密或认证协议；JWT MUST 校验签名、`exp`、`iss`、`aud` 并固定算法白名单。
7. 校验异常、鉴权服务不可用、配置缺失时 MUST 失败关闭（拒绝请求），MUST NOT 回退到宽松默认值。
8. 敏感操作（登录、权限变更、上传下载、导出、删除、密钥操作）MUST 有结构化审计日志；日志 MUST NOT 含密码、Token、完整证件号、签名 URL。

## 2. 跨项目约定

- 使用第三方 npm 镜像加速时，锁文件与完整性校验（`npm ci`）MUST NOT 被绕过。
- 安全相关的不确定项 MUST NOT 自行假设为"公开"或"宽松"：写 `TODO(security)` 并向用户提问。
- 例外 MUST 登记为：`TODO(security): 例外=<控制项> 原因=<...> 批准人=<...> 到期=<YYYY-MM-DD>`；无批准人或无到期日视为未批准。
