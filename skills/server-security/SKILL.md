---
name: server-security
description: 服务端安全设计与编码基线（与语言框架无关）：认证与会话、授权与越权/IDOR、输入校验与注入、文件上传下载与静态资源、HTTP 头与 CORS/CSRF、限流、SSRF、数据分级与密钥、审计日志、供应链、容器部署，以及 AI/LLM 与 Agent 功能安全。当任务涉及服务端接口、鉴权授权、数据库与多租户、文件上传/下载/导出、密钥与 Token、部署配置，或需要做服务端安全评审与代码审计时使用。
whenToUse: 编写或修改服务端代码（接口、中间件、数据模型、异步任务、部署配置），评审服务端安全，或排查越权、上传、下载、SSRF、密钥、审计相关问题。
---

# 服务端安全设计与编码规则

> 适用范围：所有涉及服务端代码、接口、鉴权、数据、文件、密钥、部署的项目（FastAPI / Flask / Django / Express / NestJS / Spring / Go / Rust 等），与语言框架无关。
> 常驻红线：本机 `~/.agents/AGENTS.md` 只保留适用性判定与八条红线；本文件是完整基线，触发条件见该文件。
> 目的：AI 在编写、修改、评审代码时，必须遵守本文档。涉及安全审计的点一律"默认拒绝、显式放行"。
> 关键词约定：**MUST** = 必须；**MUST NOT** = 禁止；**SHOULD** = 强烈建议，偏离需在代码注释或 PR 中说明理由。规则句统一以 MUST / MUST NOT 表达，正文中的"禁止""必须"与之一致。

---

## 0. 总原则

1. **默认拒绝（Deny by default）**：新接口默认需要认证 + 授权，公开接口需显式标注并说明理由。
2. **不信任任何输入**：来自客户端的一切（body、query、header、cookie、文件名、文件内容、Content-Type、JWT claim、第三方回调、MQ 消息）都不可信。
3. **服务端是唯一可信边界**：前端校验、前端隐藏按钮、前端传来的角色/用户 ID 都不算安全控制。
4. **最小权限**：数据库账号、云凭证、容器进程、API Token、文件系统权限均只给必要的最小权限。
5. **纵深防御**：不依赖单一控制点（如：既做鉴权，又做对象级校验，又做审计日志）。
6. **安全失败（Fail closed）**：校验异常、鉴权服务不可用、配置缺失时，拒绝请求而不是放行。
7. **可审计**：任何敏感操作都能回答"谁、何时、从哪里、对什么资源、做了什么、结果如何"。
8. **不确定就问**：遇到安全相关的不明确需求（权限归属、数据密级、保留期限），AI 必须向用户提问或在代码中留下 `TODO(security)`，禁止自行假设为"公开"或"宽松"。
9. **信任边界只有一处**：只有服务端进程内代码与受控代理层可信；`X-Forwarded-For`、`X-Real-IP`、`X-Forwarded-Proto`、`Origin`、`Host`、任何自定义头都来自客户端，除非确认由受控代理覆写。
10. **默认拒绝的落地**：路由表 MUST 为每个接口显式标注"公开 / 内部 / 需登录"，公开项 MUST 写明理由并纳入审计；新增路由默认继承"需登录"。

---

## 1. 认证（Authentication）

- MUST 使用成熟库/框架能力（OAuth2/OIDC、会话框架），MUST NOT 自行发明加密或认证协议。
- 密码 MUST 使用 `argon2id` / `bcrypt` / `scrypt` 加盐哈希；MUST NOT 使用 MD5/SHA1/SHA256 直接存密码。
- JWT：
  - MUST 校验签名、`exp`、`iss`、`aud`；MUST 固定允许的算法白名单，禁止 `alg=none`。
  - Access Token 短有效期（建议 ≤ 15 分钟），Refresh Token 支持轮换与吊销。
  - MUST NOT 在 JWT payload 存放敏感数据（手机号、身份证、密码等）。
- Session / Cookie：`HttpOnly`、`Secure`、`SameSite=Lax/Strict`；登录后 MUST 重新生成 session ID（防固定）。
- 登录、注册、找回密码、验证码、MFA 接口 MUST 有限流与失败锁定/退避；错误提示不泄露账号是否存在。
- API Key / 服务间 Token：MUST 可吊销、可轮换、有作用域（scope）、存储时只存哈希。
- 修改密码、邮箱、手机号、MFA 等敏感操作 MUST 二次验证（旧密码 / 验证码 / 重新登录）。
- 密码策略 MUST 以长度为主（单因子 ≥ 15 字符，至少 ≥ 8 且配合 MFA），MUST NOT 强制组合规则与定期强制轮换（对齐 NIST SP 800-63B），MUST 比对已泄露密码库（如 HIBP k-匿名接口）；MUST NOT 使用"安全问题"找回。
- 口令泄露比对 MUST 使用 k-匿名方式（如 HIBP range API），MUST NOT 把明文密码发给第三方；引入新依赖前 MUST 核实维护状态与已知漏洞（见第 13 节）。
- 找回密码：重置 token MUST 由 CSPRNG 生成、单次有效、短时效（≤ 15 分钟）、绑定用户与一次性 nonce，用后立即失效；响应 MUST NOT 暴露账号是否存在。
- 会话吊销：修改密码、修改邮箱/手机号、权限变更、管理员踢出后 MUST 在服务端吊销该用户全部会话与 refresh token 家族，MUST NOT 只依赖客户端删 Cookie。
- 账户锁定 MUST 采用指数退避 + 验证码 + 告警，MUST NOT 使用可被第三方用来锁死他人账号的全局硬锁定。
- Token、签名、验证码、重置码的比对 MUST 使用恒定时间比较（`hmac.compare_digest` / `crypto.timingSafeEqual`）。
- OAuth2 / OIDC：
  - `redirect_uri` MUST 精确匹配（禁止前缀、通配、子域模糊）；
  - 公共客户端 MUST 使用 PKCE；MUST 校验 `state` 防 CSRF；`id_token` MUST 校验签名、`iss`、`aud`、`nonce`、`exp`；
  - MUST NOT 使用 implicit flow；scope MUST 最小化；
  - 第三方登录绑定既有账号时 MUST 要求 `email_verified=true` 并走二次确认，防止账号接管。
- WebSocket / SSE：握手 MUST 鉴权并校验 `Origin`；MUST 对每条消息重新校验权限（长连接不会再经过 HTTP 中间件）；MUST 限制单用户连接数与消息速率。

## 2. 授权（Authorization）

这是审计中最常见的高危问题来源（越权 / IDOR / BOLA）。

- **MUST 对每个资源访问做对象级授权**：不能只校验"已登录"，必须校验"当前用户是否有权访问这个 `id` 对应的对象"。
  ```python
  # ❌ 错误：只按 id 查
  doc = db.get(Document, doc_id)

  # ✅ 正确：查询条件中带上所有权/租户约束
  doc = db.query(Document).filter(
      Document.id == doc_id,
      Document.tenant_id == current_user.tenant_id,
      # 以及 owner / ACL / 角色判断
  ).first()
  if not doc: raise NotFound()   # 无权与不存在统一返回 404，避免枚举
  ```
- MUST 做**函数级授权**（普通用户不能调用管理接口）和**属性级授权**（普通用户不能修改 `role`、`is_admin`、`tenant_id`、`price`、`status` 等字段）。
- 多租户：租户 ID MUST 来自服务端认证上下文，MUST NOT 来自请求参数；数据层建议强制注入租户过滤（ORM 全局过滤器 / 行级安全 RLS）。
- 授权逻辑集中实现（依赖注入 / 中间件 / 策略层），MUST NOT 在各 handler 里散写、复制粘贴。
- 防 **Mass Assignment**：请求模型使用显式白名单字段（DTO / Pydantic schema），MUST NOT 把请求体直接 `**dict` 写入数据库模型。
- 管理后台、内部接口、运维接口（`/admin`、`/internal`、`/debug`、`/metrics`、`/actuator`）MUST 独立鉴权，且不得仅靠"路径隐蔽"或"内网假设"。
- **授权缓存是一等风险**：缓存键 MUST 含 `user_id` / `tenant_id` / 资源 ID，MUST NOT 只用资源 ID；权限变更后 MUST 失效相关缓存。
- 所有缓存（Redis、进程内、CDN、HTTP 缓存）MUST 假设"数据可能被别的用户读到"：键不含主体标识即视为越权漏洞。
- 原生 SQL 与手写查询同样 MUST 显式带租户与所有权条件，MUST NOT 依赖 ORM 全局过滤器（raw 查询会绕过它）。
- 权限矩阵 MUST 作为设计产物沉淀：每个接口标注 `认证方式 / 所需权限 / 对象级校验字段 / 限流 / 审计事件`。

## 3. 输入校验与注入防护

- 所有入参 MUST 做类型、长度、范围、格式、枚举校验（Pydantic / Zod / Bean Validation 等），拒绝未知字段（`extra="forbid"` 一类配置）。
- **SQL 注入**：MUST 使用参数化查询/ORM 绑定参数；MUST NOT 字符串拼接 SQL。动态排序字段/表名 MUST 走白名单映射。
- **命令注入**：MUST NOT 把用户输入拼进 shell 命令；必须调用外部程序时使用参数数组形式（不经过 shell），并白名单参数。
- **路径遍历**：见第 5、6 节。
- **SSRF**：见第 9 节。
- **模板注入 / XSS**：模板引擎开启自动转义；MUST NOT 把用户输入当模板渲染；富文本使用成熟白名单净化库。
- **反序列化**：MUST NOT 对不可信数据使用 `pickle`、`yaml.load`（非 safe）、Java 原生反序列化等；优先 JSON + schema。
- **XXE**：解析 XML 时禁用外部实体与 DTD。
- **ReDoS / 资源耗尽**：避免对不可信输入使用复杂正则；限制 body 大小、JSON 深度、数组长度、分页大小、嵌套层级。
- **日志注入**：写日志前对换行符等控制字符做转义/结构化日志。
- **NoSQL / LDAP / GraphQL**：同样禁止拼接查询；GraphQL 需限制深度、复杂度，生产关闭内省或加鉴权。

## 4. API 设计

- 分页 MUST 设置默认值和上限（如 `limit ≤ 100`），禁止无上限导出。
- 批量接口限制单次数量；耗时操作异步化并限流。
- 响应使用显式输出模型（response schema），MUST NOT 直接返回 ORM 对象/数据库行，防止泄露 `password_hash`、内部字段、其他用户数据。
- ID 尽量使用不可预测标识（UUIDv4/ULID），但**不能把"不可猜测"当作授权**，授权仍必须校验。
- 状态变更使用 POST/PUT/PATCH/DELETE，GET MUST 无副作用。
- 幂等性：支付、下单、发券等关键操作 MUST 支持幂等键，防重放；并发修改使用乐观锁/事务，防竞态（余额、库存、优惠券）。
- 业务逻辑校验在服务端：价格、折扣、数量、状态流转（如"已支付→已发货"）必须服务端校验，禁止信任前端传入金额。
- 统一错误格式；错误响应 MUST NOT 暴露堆栈、SQL、内部路径、框架版本、服务器信息。
- 限流触发 MUST 返回 `429` 并带 `Retry-After`；错误码语义 MUST 统一（401 未认证、403 无权限、404 不存在或无权、409 冲突、422 校验失败）。
- 并发修改 MUST 使用乐观锁（版本号，或 `ETag` + `If-Match`）或事务/行锁，冲突 MUST 返回可识别错误，MUST NOT 静默覆盖。
- 幂等键 MUST 由客户端提供并由服务端持久化（键 → 结果摘要，TTL ≥ 业务重试窗口）；重复请求 MUST 返回首次结果，MUST NOT 产生二次扣款、二次发货、二次发券。

---

## 5. 文件上传（重点审计项）

### 5.1 校验

- MUST 限制：**最大文件大小**（在反向代理和应用层都设置）、**单次文件数量**、**允许的类型白名单**（扩展名 + MIME + 魔数 magic bytes 三者一致）。
- MUST NOT 仅信任：客户端文件名、`Content-Type` 头、扩展名。
- 流式读取并在读取过程中统计大小，超限立即中断；MUST NOT 先全量读入内存再判断。
- 压缩包（zip/tar/7z）：防 **Zip Slip**（解压路径逃逸）、**压缩炸弹**（限制解压后总大小/文件数/嵌套层数）、符号链接。
- 图片/Office/PDF：对内容做解析校验；必要时**重新编码/转换**（图片 re-encode、去除 EXIF）以剥离恶意载荷与隐私元数据。
- 禁止上传并保留可执行/可被服务端解释的类型（`.php .jsp .asp .aspx .sh .exe .bat .py .html .svg`）；SVG、HTML 视为可执行内容（含脚本），除非明确净化，否则禁止作为可内联展示的上传类型。
- PDF 可含 JavaScript/嵌入文件/外链，涉及不可信 PDF 时按风险评估是否需要净化或沙箱预览。
- 需要时接入病毒/恶意内容扫描（ClamAV 或云厂商服务），扫描通过前文件状态为 `pending`，不可被下载或使用。
- 不可信文件 MUST 在隔离环境解析：独立子进程或容器、无网络、限 CPU/内存/超时、非 root；图片/PDF/Office 解析库历史 RCE 较多，MUST 保持补丁更新，MUST NOT 在主进程内直接解析。

### 5.2 存储

- MUST NOT 使用用户提供的文件名作为存储路径或文件名；存储名由服务端生成（UUID / 内容哈希）。原始文件名仅作为元数据存数据库，展示/下载时再净化。
- MUST NOT 把上传目录放在 Web 根目录或任何被静态服务直接暴露的目录下。
- 推荐存储到**对象存储（私有 bucket）**，或应用 Web 根之外的目录；bucket 默认私有、禁止公共读写、禁止列目录。
- 存储目录权限最小化：目录 `0700`（或 `0750`）且禁止列目录，文件 `0644`，挂载点可加 `noexec`；MUST NOT 让 Web 服务器以可写+可执行方式访问上传目录（应只读挂载）。
- 文件元数据入库：`file_id`、`owner_id`、`tenant_id`、`原始文件名`、`存储key`、`size`、`sha256`、`检测到的 MIME`、`扫描状态`、`上传时间`、`上传 IP`、`业务关联对象`、`保留期限`。
- 路径拼接 MUST 做规范化后校验仍在基目录内：
  ```python
  # is_relative_to 需 Python >= 3.9；更早版本用 os.path.commonpath 比较
  base = Path(UPLOAD_DIR).resolve(strict=False)
  target = (base / stored_name).resolve(strict=False)  # resolve 同时消除 .. 与符号链接
  if not target.is_relative_to(base):
      raise Forbidden()
  ```
- 上传接口 MUST 鉴权 + 限流 + 配额（每用户/租户存储总量与频率）。
- 失败/中断的上传需要清理临时文件；定期清理孤儿文件。

### 5.3 审计日志

- 记录：谁、何时、IP、文件 ID、大小、哈希、检测类型、扫描结果、成功/失败原因。
- 被拒绝的上传（类型不符、超限、病毒）同样记录，便于发现攻击行为。

---

## 6. 文件下载与静态资源访问（重点审计项，如直接访问 PDF）

**核心规则：凡是带有业务数据、用户数据、合同、报表、发票、证件、导出文件的资源，MUST NOT 作为"公开静态文件"直接暴露。**

### 6.1 禁止的做法

- ❌ 把 PDF/Word/Excel/图片/导出文件放进 `static/`、`public/`、`/uploads/`，通过 `https://host/static/xxx.pdf` 直接匿名访问。
- ❌ 使用自增 ID 或可预测文件名（`/files/1001.pdf`、`/export/20240101.xlsx`）。
- ❌ 对象存储 bucket 设置为公共读，或永久公开的 URL。
- ❌ 开启目录浏览（autoindex / directory listing）。
- ❌ 静态服务挂载根目录过宽（挂载整个项目目录、`/` 或包含 `.env`、`.git`、备份、日志、源码的目录）。
- ❌ 在日志、前端代码、错误信息、第三方 Referer 中泄露带长期有效凭证的文件 URL。

### 6.2 推荐做法

1. **鉴权下载接口**：文件通过受控接口提供，如 `GET /api/files/{file_id}/download`：
   - 校验登录态 → 校验对该文件的对象级权限（owner/租户/ACL）→ 校验文件状态（已扫描通过、未删除、未过期）→ 返回流。
   - 无权与不存在统一返回 404。
2. **短时效签名 URL**（预签名 URL / 带签名的 token）：
   - 有效期短（建议 ≤ 5～15 分钟）、绑定用户/文件/操作，必要时绑定 IP；
   - 过期、篡改一律拒绝；签名密钥可轮换。
   - 预签名 URL 视同凭证：不写入日志明文、不缓存、不长期保存。
3. **响应头**（下载与预览均需设置）：
   - `Content-Type`：由服务端按白名单确定，不使用用户上传的 `Content-Type`。
   - `X-Content-Type-Options: nosniff`
   - `Content-Disposition: attachment; filename="<ASCII 兜底名>"; filename*=UTF-8''<percent-encoded 名>`（`filename*` 的值 MUST 按 RFC 5987 做 percent-encode，并同时给 ASCII `filename` 兜底；默认强制下载；确需内联预览时仅限安全类型，如 PDF/PNG/JPEG，并配合 CSP）。浏览器内置 PDF 查看器对 `CSP: sandbox` 支持不一致，预览与下载 SHOULD 分两条路径并经实测确认。
   - 用户文件使用**独立域名**（如 `usercontent.example.com`）提供，避免与主站同源导致存储型 XSS 窃取 Cookie。
   - `Cache-Control: no-store`（敏感文件）；禁止被 CDN/代理缓存公共副本。
   - `Content-Security-Policy: sandbox; default-src 'none'`（内联预览用户内容时）。
4. **文件名净化**：去掉路径分隔符、控制字符、换行（防响应头注入）、前导点；长度限制。
5. **Range / 大文件**：支持流式输出，设置带宽/并发限制，防止被用于耗尽资源。
6. **纯公开资源**（Logo、产品公开图、前端构建产物）才允许走静态目录/CDN，且 MUST 确认：内容不含个人/业务敏感信息、文件名无敏感含义、目录无其他文件。
7. **静态文件服务配置**：
   - 只挂载专用的、最小化的目录；
   - 关闭目录列表；
   - 禁止符号链接跟随（或限制在目录内）；
   - 屏蔽隐藏文件与敏感后缀（`.env .git .svn .DS_Store .bak .old .sql .log .swp .pem .key .zip .map`），生产环境不暴露 source map（除非明确需要）。
8. **水印 / 防泄露（按需）**：对高敏感文档动态加用户水印并记录下载者，便于溯源。
9. **可撤销分享链接**：面向终端用户的分享 MUST 使用服务端可撤销 token（记录创建者、资源、过期时间、访问次数），MUST 支持主动失效与审计；MUST NOT 把长期有效的预签名 URL 贴进页面或交给第三方。
10. **缓存**：敏感文件响应 MUST 为 `Cache-Control: no-store`；MUST NOT 被 CDN 或共享缓存保存；确需缓存时 `Vary` MUST 含 `Authorization` / `Cookie`，缓存键 MUST 含主体。

### 6.3 导出文件（报表 / Excel / CSV / PDF 生成）

- 生成的导出文件按"受控文件"处理（同 6.2），存放私有存储，设置过期自动清理。
- 导出前 MUST 按**当前用户的数据权限**过滤，而不是全量导出。
- **CSV/Excel 公式注入**：单元格以 `= + - @ \t \r` 开头时，需前缀单引号或转义。
- 大批量导出需限流、审计、必要时审批。

### 6.4 下载审计日志

必须记录：`user_id / tenant_id / file_id / 文件名 / 来源 IP / User-Agent / 时间 / 结果（成功/拒绝/不存在）/ 请求 ID`；对**批量下载、异常频率、跨租户尝试、遍历 ID** 触发告警。

- 记录来源 IP 时 MUST 使用受控代理链解析后的真实地址（见第 7 节信任链）；直接保存 `X-Forwarded-For` 原始值会导致审计造假与告警失效。

---

## 7. HTTP 层安全

- 全站 HTTPS；开启 HSTS；禁止明文传输凭证。
- **安全响应头**：`X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`（或 CSP `frame-ancestors`）、`Referrer-Policy: no-referrer`/`strict-origin-when-cross-origin`、`Permissions-Policy`、合理的 `Content-Security-Policy`。
- **CORS**：
  - MUST NOT 使用 `Access-Control-Allow-Origin: *` 搭配凭证；
  - MUST NOT 把请求头 `Origin` 原样反射；
  - 使用精确的来源白名单。
- **CSRF**：基于 Cookie 的认证 MUST 有 CSRF 防护（SameSite + CSRF Token / 双重提交 / 自定义头校验）。
- 限制请求体大小、请求头大小、超时、并发连接；设置反向代理层与应用层的双重限制。
- 重定向：`redirect_url` / `next` 参数使用白名单，防开放重定向。
- Host 头校验（防 Host 头注入/缓存投毒）：配置允许的 Host 列表。
- 生产环境 MUST 关闭：debug 模式、自动生成的 API 文档（或加鉴权）、详细错误页、测试接口、默认账号。
- 上传/下载接口用的 `Content-Length` 与实际流大小不一致时按攻击处理。
- **代理信任链**：`X-Forwarded-For` / `X-Real-IP` / `X-Forwarded-Proto` MUST 仅在"请求确实来自受控代理"时使用；按可信跳数取最右侧的非可信地址；服务直连暴露时 MUST NOT 读取这些头。反向代理 MUST 覆写这些头，MUST NOT 原样追加透传客户端伪造值。
- **TLS 基线**：最低 TLS 1.2（优先 1.3）；MUST 禁用 SSLv3 / TLS 1.0 / 1.1、弱套件与压缩；证书 MUST 自动续期并有到期告警；HSTS 带 `includeSubDomains`（启用 preload 需谨慎评估）。
- **现代隔离响应头**：`Cross-Origin-Opener-Policy`、`Cross-Origin-Embedder-Policy`、`Cross-Origin-Resource-Policy`；登出与改密响应 SHOULD 返回 `Clear-Site-Data: "cache","cookies","storage"`。
- **CSP 落地**：MUST 使用 nonce 或 hash，MUST NOT 依赖 `unsafe-inline`；从 `default-src 'none'` 起步按需放开；用户内容域名 MUST 单独配置更严格策略。
- **请求走私**：网关 MUST 拒绝 `Content-Length` 与 `Transfer-Encoding` 同时存在或互相矛盾的请求；长度语义 MUST 只由一层决定。
- **缓存安全**：认证响应 MUST 为 `private` 或 `no-store`；缓存键 MUST 含租户与主体；除 Host 校验外 MUST NOT 把不可信请求头纳入缓存键（防缓存投毒）。
- **第三方资源**：外部 `<script>` / 样式 MUST 加 SRI；第三方埋点与 SDK MUST 评估数据外泄与合规风险；悬空 DNS / CNAME MUST 定期巡检（防子域接管）。

## 8. 限流与滥用防护

- 全局限流 + 按用户/IP/Token 限流；登录、验证码、短信/邮件发送、搜索、导出、上传、AI 调用等高成本接口使用更严格的限流与配额。
- 防枚举：用户名/手机号/邮箱探测、资源 ID 遍历，统一响应与耗时。
- 异步任务/队列设置并发与重试上限，防止被打爆；防止"放大攻击"（一个请求触发大量内部请求）。
- 分布式限流 MUST 共享计数（网关或 Redis），MUST NOT 只靠单实例内存；限流键 MUST 组合"账号 + IP + 资源"，避免 NAT 下误伤或被绕开。
- 验证码、短信、邮件通道 MUST 同时按"目标地址"与"来源"双维度计数，防短信轰炸与费用放大。

## 9. 服务端发起外部请求（SSRF）

- 任何由用户提供 URL 的功能（Webhook、图片抓取、URL 预览、导入、代理）MUST：
  - 只允许 `http/https`，域名/IP 走**白名单**优先；
  - 解析 DNS 后校验 IP，**禁止**内网、回环、链路本地、CGNAT、保留段、组播与云元数据地址。完整网段与元数据端点清单见 [`references/ssrf-denylist.md`](references/ssrf-denylist.md)，MUST 全覆盖：`127.0.0.0/8`、`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`、`169.254.0.0/16`、`100.64.0.0/10`、`0.0.0.0/8`、`198.18.0.0/15`、`224.0.0.0/4`、`240.0.0.0/4`、`::1`、`fe80::/10`、`fc00::/7`、`::ffff:0:0/96`、`2002::/16`；
  - 校验重定向后的目标（限制或禁用重定向）；防 DNS rebinding（连接时使用已校验的 IP）；
  - 设置超时、响应大小上限、并发上限；
  - 出站流量尽量经过受控的出口代理。
- Webhook 接收方 MUST 验证签名、时间戳、防重放（nonce/幂等键）。

## 10. 数据保护

- 传输加密（TLS）与存储加密（磁盘/数据库/对象存储加密）；敏感字段（身份证、银行卡、手机号等）考虑字段级加密或脱敏存储。
- **数据分级**：识别 PII/敏感数据，响应与日志中默认脱敏（手机号 `138****0000`、证件号、邮箱、Token）。
- 最小化收集与返回：不需要的字段不查、不存、不返回。
- 保留期限与删除：定义文件和数据的保留策略，用户注销/到期后真正删除（含备份策略、对象存储生命周期规则）。
- 备份加密，访问受限，定期恢复演练。
- 测试/开发环境 MUST NOT 使用未脱敏的生产数据。
- 数据出境：使用境外 SaaS、SDK、日志或云服务前 MUST 判定是否构成数据出境，MUST NOT 因选型而无意识出境（PIPL / GDPR 合规）。
- 加密实现：AEAD 的 nonce MUST 唯一（随机或计数器，MUST NOT 复用）；密文 MUST 带 key id 以支持轮换；敏感字段加密 MUST 使用带完整性校验的模式。

## 11. 密钥与配置

- MUST NOT 把密钥、Token、密码、证书、数据库连接串硬编码或提交到代码仓库、示例配置、测试用例、Dockerfile、前端代码、日志。
- 使用环境变量 / Secret Manager / KMS；`.env` 加入 `.gitignore`；仓库提供 `.env.example`（仅占位值）。
- 不同环境（dev/test/prod）密钥隔离；密钥支持轮换；泄露后立即吊销。
- 强随机数用 CSPRNG（`secrets` / `crypto.randomBytes` / `SecureRandom`），MUST NOT 用 `random` / `Math.random` 生成 Token、验证码、重置链接。
- 加密算法：使用 AES-GCM / ChaCha20-Poly1305 等 AEAD；MUST NOT 自写加密、使用 ECB、硬编码 IV/密钥、使用 MD5/SHA1 做安全用途。
- 配置缺失（如缺少 `SECRET_KEY`）时启动失败，而不是回退到不安全默认值。

## 12. 日志与审计

### 12.1 必须审计的事件

| 类别 | 事件 |
|---|---|
| 身份 | 登录成功/失败、登出、MFA、密码修改/重置、Token 创建/吊销、账号锁定 |
| 权限 | 角色/权限变更、授权失败（403/404 越权尝试）、提权操作 |
| 数据 | 敏感数据的查看/导出/下载/修改/删除、批量操作 |
| 文件 | 上传、下载、删除、分享链接生成/访问、签名 URL 签发、扫描结果 |
| 管理 | 配置变更、用户管理、密钥操作、管理员操作 |
| 安全 | 限流触发、输入校验异常集中出现、疑似攻击（遍历、注入特征） |

### 12.2 日志字段（结构化 JSON）

`timestamp(UTC)`、`request_id/trace_id`、`actor（user_id/service_id）`、`tenant_id`、`ip`、`user_agent`、`action`、`resource_type`、`resource_id`、`result`、`reason`、`变更前后摘要（非敏感）`。

### 12.3 规则

- MUST NOT 记录：密码、Token、完整 Cookie、完整身份证/银行卡、预签名 URL 完整签名、密钥、完整请求体中的敏感字段。
- 审计日志与应用调试日志分离；审计日志 **只追加**、防篡改（独立存储 / WORM / 日志服务），应用账号不可删除。
- 保留期满足合规要求（常见 ≥ 180 天，按行业/法规确定）。
- 时间统一 UTC 并保证时钟同步；每个请求带 `request_id` 并回传给调用方便于排障。
- 对异常模式设置告警（暴力破解、短时间大量下载、跨租户访问尝试、权限变更）。
- 审计日志本身包含个人信息（IP、UA、资源名）：MUST 明确合法性基础、访问控制与保留期限，并在隐私政策中说明；MUST NOT 以"要审计"为由无限期留存。
- 防篡改 MUST 有具体手段：追加写 + 哈希链（每条含上一条摘要）并定期锚定，或写入 WORM / 独立日志服务；仅"应用账号不可删除"不足以证明未被篡改。

## 13. 依赖与供应链

- 锁定依赖版本（lock 文件），仅从可信源安装；新增依赖需评估维护状态、许可证、已知漏洞。
- 集成 SCA/依赖扫描（`pip-audit`、`npm audit`、Dependabot/Renovate、Trivy 等）与 SAST（Semgrep、Bandit、CodeQL）、Secret 扫描（gitleaks）到 CI。
- 容器镜像：使用最小基础镜像、固定版本/摘要、非 root 运行、只读根文件系统（可行时）、不安装多余工具。
- AI 生成代码引入的依赖 MUST 核实真实存在、名称无拼写劫持（typosquatting）。
- MUST 产出 SBOM（`syft` / `cdxgen`）并在 CI 中比对漏洞库；容器镜像 MUST 签名（cosign / notation），部署时 MUST 校验签名。
- **依赖混淆**：私有包 MUST 锁定作用域与 registry（`.npmrc` / `pip.conf` 固定 index），MUST NOT 允许同名内部包从公共源解析。
- 第三方镜像源（含国内 npm 镜像）仅用于加速：锁文件与完整性校验（`npm ci`、`pip --require-hashes`）MUST NOT 被绕过；企业项目 SHOULD 使用私有 registry + scope 隔离。

## 14. 部署与运行环境

- 应用以非 root 运行；数据库、缓存（Redis 等）、消息队列不暴露公网，开启认证与 TLS。
- 网络分区：公网 → 网关/WAF → 应用 → 数据层；数据库只允许应用来源访问。
- 云资源（对象存储、数据库、密钥）使用最小权限的 IAM 角色，禁止长期 AK/SK 写入代码。
- 健康检查/监控端点不暴露敏感信息，或仅内网可访问。
- 生产环境关闭不必要的端口、服务、调试工具。
- 容器 MUST 以非 root 运行、drop 全部 capability 后按需添加、启用 seccomp / AppArmor、可行时 `readOnlyRootFilesystem`；MUST NOT 使用 `privileged`，MUST NOT 挂载 docker socket。
- Kubernetes：Secret MUST 加密存储并最小授权；ServiceAccount 权限最小化；网络策略 SHOULD 默认拒绝。

## 15. 异步任务、定时任务与消息

- 消息体也是不可信输入：消费者 MUST 校验 schema 与权限上下文，不能仅因"来自内部队列"而放行。
- 任务中带的用户身份/租户 ID 需来自可信来源并在任务内重新校验授权。
- 任务具备超时、重试上限、死信队列；避免无限重试产生放大效应。
- 任务产物（导出文件、报告）按第 6.3 节处理。
- 毒消息 MUST 进入死信队列并告警，MUST NOT 无限重试；重试 MUST 有退避与上限。
- 消费者 MUST 幂等（按消息 ID 或业务键去重），防重复投递造成二次副作用。

## 16. 错误处理

- 对外返回通用错误信息 + `request_id`；详细异常只写入服务端日志。
- 统一处理未捕获异常，避免框架默认错误页泄露细节。
- 认证/授权失败、资源不存在的响应在语义和耗时上尽量一致（防信息泄露与枚举）。
- 异常与审计 MUST 闭环：捕获异常后 MUST NOT 只打日志就返回 200，MUST 让调用方拿到可判定的失败语义。

---

## 17. AI 编码行为约束（给 AI 助手的直接指令）

动手前 MUST 先写出**接口安全卡**：`认证方式 / 所需权限 / 对象级校验字段 / 输入输出 schema / 限流 / 审计事件`，缺失项 MUST 写成 `TODO(security)` 并向用户确认。

AI 在编写或修改代码时 MUST：

1. 新增接口前先明确：**谁可以调用（认证）、能访问哪些对象（授权）、输入输出 schema、限流、审计事件**。缺失则主动询问或写出假设与 `TODO(security)`。
2. 涉及**文件上传/下载/导出/静态资源**时，MUST 遵循第 5、6 节；MUST NOT 为了"能跑通"把文件放进公开静态目录或开放 `*` 的 CORS。
3. 使用**参数化查询**；MUST NOT 拼接 SQL/命令/路径。
4. 所有 ID 参数的查询 MUST 带上所有权/租户条件。
5. MUST NOT 在代码、测试、示例、注释、日志中写入真实或看似真实的密钥与凭证。
6. MUST NOT 关闭 TLS 校验（`verify=False`）、关闭 CSRF/鉴权、使用 `eval/exec`、`pickle.loads` 处理不可信数据，除非用户明确要求且标注风险。
7. 引入新依赖时说明原因，并使用主流且维护活跃的库。
8. 修改认证、授权、文件处理、加密、支付等**安全敏感模块**时，必须在变更说明中列出：影响面、风险点、对应测试。
9. 为安全相关逻辑编写测试：越权访问（A 访问 B 的资源）、未登录访问、非法文件类型/超大文件/路径穿越文件名、过期/篡改的签名 URL、限流触发。
10. 不得为了通过测试或简化实现而弱化已有安全控制；发现现有代码违反本规则时，指出并建议修复。
11. **仅当本次改动涉及服务端接口、数据、文件、密钥、权限或部署配置时**，在输出末尾附第 18 节自检清单的勾选结果；纯前端样式、纯文档任务 MUST NOT 输出清单。



---

## 18. 提交前安全自检清单（PR Checklist）

完整逐项清单见 [`references/checklist.md`](references/checklist.md)，提交前 MUST 逐条勾选。核心判定如下（均为 MUST）：

| 检查点 | 通过标准 |
|---|---|
| 认证 | 新接口默认需认证；公开接口有理由并进审计 |
| 对象授权 | 每个按 ID 的访问都带 owner / 租户 / ACL 条件 |
| 身份来源 | 不信任请求里的 `user_id` / `tenant_id` / `role` / `price` / `status` |
| 输入 | 类型、长度、范围、枚举校验，未知字段拒绝 |
| 注入 | 无 SQL / 命令 / 路径拼接；路径规范化后校验 |
| 输出 | 显式 schema，无敏感字段；分页有上限 |
| 上传 | 大小与类型（扩展名 + MIME + 魔数）；服务端命名；私有存储 |
| 下载 | 鉴权接口或短时效签名 URL；响应头齐全；无匿名直链 |
| 密钥 | 无硬编码；配置缺失时启动失败 |
| 审计 | 敏感操作有结构化日志；日志无凭证；IP 来自可信代理链 |
| 测试 | 有越权 / 未认证 / 恶意文件 / 过期签名 / 限流用例 |

---

## 19. 常见反模式速查

| 反模式 | 风险 | 正确做法 |
|---|---|---|
| `app.mount("/static", StaticFiles(directory="uploads"))` | 上传文件匿名可读、可遍历 | 私有存储 + 鉴权下载/签名 URL |
| `open(f"uploads/{file.filename}")` | 路径穿越、覆盖文件 | 服务端生成文件名 + 路径规范化校验 |
| 只校验 `file.content_type` | 伪造类型，上传恶意文件 | 扩展名 + MIME + 魔数三重校验，必要时重编码 |
| `GET /files/123.pdf`（自增 ID，无鉴权） | IDOR，批量爬取 | UUID + 对象级授权 + 审计 |
| `db.get(Model, id)` 后直接返回 | 越权访问他人数据 | 查询条件带 owner/tenant |
| `Model(**request.dict())` | Mass Assignment（改 role 等） | 显式字段白名单 DTO |
| `allow_origins=["*"]` + `allow_credentials=True` | 跨站读取敏感数据 | 精确来源白名单 |
| `requests.get(user_url)` | SSRF，访问云元数据/内网 | 白名单 + IP 校验 + 限制重定向 |
| 报错返回堆栈 | 信息泄露 | 通用错误 + request_id |
| 日志打印完整请求/Token | 凭证泄露 | 脱敏 + 结构化字段白名单 |
| 用户上传 HTML/SVG 同域内联展示 | 存储型 XSS | 独立域名 + `attachment` + CSP sandbox |
| `random` 生成 Token/验证码 | 可预测 | `secrets` / CSPRNG |
| 预签名 URL 有效期数天且被日志记录 | 凭证泄露后长期可用 | 短时效 + 日志脱敏 |
| 直接读 `X-Forwarded-For` 做限流或审计 | IP 伪造、限流绕过、审计造假 | 只信任受控代理，按可信跳数取址 |
| 缓存键只含资源 ID | 跨租户数据泄露 | 键含 `user_id` / `tenant_id` |
| 用 `random` 或时间戳生成重置码 | 可预测、可爆破 | CSPRNG + 单次 + 短时效 |
| 改密后不吊销旧会话 | 被盗会话长期有效 | 服务端吊销全部会话与 refresh token |

---

## 20. AI/LLM 与 Agent 功能安全（仅项目包含 AI 能力时适用）

- **提示注入**：用户输入、上传文件、抓取的网页、RAG 文档、工具返回 MUST 视为不可信数据，MUST NOT 当作指令执行；系统提示与工具权限 MUST NOT 被检索到的内容改变。
- **模型输出不可信**：模型生成的 SQL、命令、URL、代码 MUST 经校验或沙箱执行，MUST NOT 直接 `eval` / `exec`、拼进 SQL、或用于访问内网。
- **工具调用最小权限**：Agent 可调用工具 MUST 白名单 + 最小权限 + 危险操作人工确认；长期凭证 MUST NOT 进入模型上下文。
- **成本与滥用**：LLM 接口 MUST 限流 + 配额 + 超时 + 最大 token；MUST 防放大（一次请求触发大量模型或工具调用）。
- **数据边界**：PII 与密钥 MUST NOT 进入 prompt 或写入模型日志；会话记录 MUST 有保留期限与访问控制；MUST 明确数据是否用于训练。
- **RAG 与向量库**：检索 MUST 按用户 / 租户过滤，MUST NOT 让一个租户检索到另一个租户的片段；文档入库前 MUST 做敏感信息扫描。


## 21. 参考标准（供设计与审计对照）

- OWASP Top 10、OWASP API Security Top 10（BOLA、Broken Auth、BOPLA、资源耗尽、SSRF 等）
- OWASP ASVS（应用安全验证标准）、OWASP Cheat Sheet Series（File Upload、Authorization、Logging、SSRF 等）
- CWE Top 25
- 等保 2.0 / ISO 27001 / SOC 2 / GDPR / 个人信息保护法（按业务合规要求选用）

> 本文档应随项目演进持续更新。任何与本文档冲突的需求，AI MUST 先向用户说明风险并取得明确确认，才能以"例外"形式实现。
> 例外 MUST 用统一格式登记在代码与 PR 说明中，便于审计检索：
> `TODO(security): 例外=<控制项编号> 原因=<为什么必须> 批准人=<姓名/工单> 到期=<YYYY-MM-DD>`
> 无批准人或无到期日的例外视为未批准，MUST NOT 合入。
