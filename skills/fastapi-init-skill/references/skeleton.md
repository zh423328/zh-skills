# FastAPI 项目完整骨架

生成 FastAPI 项目时按本骨架现场写代码。版本号一律不写，由 SKILL.md 的版本获取策略动态决定。

> 维护者可用 `scripts/generate_project.py` 从本文件和 `references/startup-scripts.md` 自动生成完整项目，避免人工复制遗漏文件或编码错误。

## 目录结构

对齐 FastAPI 官方 full-stack 模板的主流分层：`api/`（路由 + 依赖）、`core/`（配置 / 安全 / 统一响应）、`crud/`（数据访问）、`models/`（ORM）、`schemas/`（出入参）、`db/`（会话）。

```
{{PROJECT_NAME}}/
├── app/
│   ├── __init__.py
│   ├── main.py              # 应用入口：lifespan、CORS、安全头、日志、异常、路由注册
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py          # 依赖注入：get_db、get_current_user
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py    # 健康检查 GET /api/health、GET /api/health/db
│   │       ├── auth.py      # 注册/登录/刷新/登出/me POST|GET /api/auth/*
│   │       └── items.py     # 示例 CRUD GET|POST|PUT|DELETE /api/items*
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Pydantic Settings：从 .env 读取全部配置
│   │   ├── security.py      # JWT 签发/解析 + bcrypt 密码哈希
│   │   ├── exceptions.py    # 业务异常：BusinessException
│   │   └── response.py      # 统一响应：EnvelopeRoute + api_response 兜底
│   ├── crud/
│   │   ├── __init__.py
│   │   ├── user.py          # 用户数据访问
│   │   └── item.py          # 条目数据访问
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py       # 数据库引擎与 Session：SQLAlchemy async / Motor
│   │   └── base.py          # ORM 基类与模型汇总导入
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py          # User 表模型
│   │   └── item.py          # Item 示例业务表模型
│   └── schemas/
│       ├── __init__.py
│       ├── user.py          # 用户出入参（Pydantic v2）
│       └── item.py          # 条目出入参（Pydantic v2）
├── docs/
│   └── project-guide.md     # 项目指南（强制交付物）
├── restart.sh               # 一键启动/重启脚本（Linux/macOS，dev/prod 双模式）
├── restart.bat              # 一键启动/重启脚本（Windows，dev/prod 双模式）
├── gunicorn.conf.py         # gunicorn 生产配置（master-worker + HUP 热更新，仅 Linux/macOS）
├── requirements.txt         # Python 依赖清单
├── .env.example             # 环境变量模板（带安全注释，必须生成）
├── .env                     # 实际运行环境变量（首次从 .env.example 复制，按需修改）
├── .gitignore               # Git 忽略规则（必须生成，.env 默认不提交）
├── Dockerfile               # 容器镜像构建（多阶段 + 非 root）
├── docker-compose.yml       # MySQL 编排
├── docker-compose.pg.yml    # PostgreSQL 编排
├── docker-compose.mongo.yml # MongoDB 编排
└── README.md                # 项目说明
```

## 配置生成与加载规则（强制）

1. **`.env.example`、`.env`、`.gitignore` 必须随脚手架一起生成**。`.gitignore` 中必须忽略 `.env`、`.env.local`、`.env.production` 等包含敏感信息的文件。
2. **首次生成时**，若用户目录不存在 `.env`，自动从 `.env.example` 复制一份，并提示用户按需修改数据库、JWT、CORS 等关键配置。
3. **所有运行时可变配置必须从 `.env` 加载**。`app/core/config.py` 使用 Pydantic Settings（`SettingsConfigDict(env_file=".env")`）读取全部环境变量，禁止在业务代码中硬编码端口、数据库连接、密钥等。
4. **`.env.example` 中的每一项配置都必须在 `app/core/config.py` 中有对应字段**，并在 main、db、routes 等运行环节被实际使用。

## 依赖清单（requirements.txt）

```txt
fastapi
uvicorn[standard]
gunicorn
uvicorn-worker
pydantic
pydantic-settings
python-dotenv
sqlalchemy[asyncio]
pymysql
aiomysql
asyncpg
motor
cryptography
bcrypt
python-jose[cryptography]
alembic
email-validator
```

## 关键文件模板

### app/__init__.py

```python
```

### app/main.py

```python
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.api.routes import health
if settings.db_type not in ("none", "mongodb"):
    from app.api.routes import auth, items

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.db_type not in ("mongodb", "none"):
        from app.db.base import Base
        from app.db.session import engine
        # ⚠️ 开发阶段自动建表；生产环境请使用 Alembic 迁移，禁用 create_all
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    elif settings.db_type == "mongodb":
        from app.db.session import connect_db
        await connect_db()
    # db_type == "none": 跳过数据库初始化
    logger.info("服务启动完成，端口 %s", settings.app_port)
    if settings.jwt_secret == "change-me-in-production":
        logger.warning("⚠️ JWT_SECRET 为默认值！请编辑 .env 将其改为随机字符串！")
    yield
    if settings.db_type not in ("mongodb", "none"):
        from app.db.session import engine
        await engine.dispose()
    elif settings.db_type == "mongodb":
        from app.db.session import close_db
        await close_db()
    logger.info("服务已关闭")


app = FastAPI(
    title=settings.app_name,
    description="FastAPI 开箱即用服务 — 支持 JWT 鉴权 / 示例 CRUD / 统一响应",
    version="0.1.0",
    lifespan=lifespan,
    # ⚠️ 生产环境建议关闭 Swagger 文档，防止暴露 API 结构
    # docs_url=None,
    # redoc_url=None,
    docs_url="/docs",
    redoc_url="/redoc",
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=settings.app_name,
        version="0.1.0",
        description="## 快速开始\n\n1. 注册账号: `POST /api/auth/register`\n2. 登录获取 Token: `POST /api/auth/login`\n3. 在右上角 **Authorize** 填入 Token\n4. 开始调用其他接口（如 `GET /api/items`）",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

_cors_origins = [o.strip() for o in settings.cors_origins.split(",")]
_allow_all = _cors_origins == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _cors_origins,
    allow_credentials=not _allow_all,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
    expose_headers=["X-Request-Id"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """安全头中间件：为所有响应添加基础安全头，防御常见 Web 攻击。"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# 包含敏感信息的 URL 路径关键词，日志中需要过滤或标记
_SENSITIVE_PATHS = ("password", "token", "secret", "auth", "login", "register")


@app.middleware("http")
async def request_log_middleware(request: Request, call_next):
    request_id = uuid.uuid4().hex[:16]
    request.state.request_id = request_id
    start = time.time()
    response = await call_next(request)
    duration = int((time.time() - start) * 1000)

    path = request.url.path
    # 若 URL 包含敏感关键词，只记录路径前缀，不记录查询参数
    if any(k in path.lower() for k in _SENSITIVE_PATHS):
        logger.info("[%s] %s <敏感路径> %s %dms [已过滤详细路径]", request_id, request.method, response.status_code, duration)
    else:
        logger.info("[%s] %s %s %s %dms", request_id, request.method, path, response.status_code, duration)

    response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(BusinessException)
async def business_exception_handler(_, exc: BusinessException):
    return JSONResponse(status_code=200, content={"code": exc.code, "message": exc.message, "data": None})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(x) for x in first.get("loc", []) if x != "body")
    msg = f"{loc} {first.get('msg', '')}".strip() or "参数校验错误"
    return JSONResponse(status_code=200, content={"code": -1001, "message": msg, "data": None})


@app.exception_handler(Exception)
async def global_exception_handler(_, exc: Exception):
    logger.exception("未捕获的异常")
    return JSONResponse(status_code=200, content={"code": -2000, "message": "系统繁忙，请稍后再试", "data": None})


app.include_router(health.router, prefix="/api", tags=["健康检查"])
if settings.db_type not in ("none", "mongodb"):
    app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
    app.include_router(items.router, prefix="/api/items", tags=["条目管理"])
```

### app/core/__init__.py

```python
```

### app/core/config.py

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "{{project}}"
    app_port: int = 8080
    app_debug: bool = True  # ⚠️ 生产环境必须设为 false，防止泄漏堆栈跟踪等敏感信息

    db_type: str = "mysql"  # mysql / postgresql / mongodb / none
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "app_db"
    db_user: str = "root"
    # 🔴 生产环境务必修改为强密码！
    db_password: str = "root"
    # 完整连接串，优先级高于上面的分项配置
    db_url: str | None = None

    cors_origins: str = "*"

    jwt_secret: str = "change-me-in-production"
    jwt_expires_in: int = 86400
    jwt_refresh_expires_in: int = 604800

    bcrypt_rounds: int = 12

    @property
    def database_url(self) -> str:
        if self.db_url:
            return self.db_url
        if self.db_type == "mysql":
            return f"mysql+aiomysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        if self.db_type == "postgresql":
            return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        if self.db_type == "mongodb":
            return f"mongodb://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?authSource=admin"
        return ""


settings = Settings()
```

### app/core/security.py

```python
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def create_access_token(user_id: int, username: str) -> str:
    """签发 access_token，默认有效期见 .env 的 JWT_EXPIRES_IN。"""
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=settings.jwt_expires_in),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def create_refresh_token(user_id: int, username: str) -> str:
    """签发 refresh_token，默认有效期见 .env 的 JWT_REFRESH_EXPIRES_IN。"""
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=settings.jwt_refresh_expires_in),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """解析并校验 Token，无效或过期时抛出 JWTError。"""
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


def hash_password(password: str) -> str:
    # bcrypt 只使用前 72 字节，超出部分截断（与 bcrypt 历史行为一致）
    hashed = bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt(rounds=settings.bcrypt_rounds))
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8")[:72], hashed_password.encode("utf-8"))
    except ValueError:
        return False
```

### app/core/exceptions.py

```python
class BusinessException(Exception):
    """业务异常：携带业务错误码与提示信息，由全局异常处理器统一转为响应信封。"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
```

### app/core/response.py

```python
import json

from fastapi import Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.routing import APIRoute


class EnvelopeRoute(APIRoute):
    """统一响应信封路由。

    handler 返回 dict/Pydantic 模型 → 自动包装为 { code: 0, message: "success", data: ... }
    StreamingResponse（文件下载等）直接透传，不包信封。
    """

    def get_route_handler(self):
        original = super().get_route_handler()

        async def custom_handler(request: Request) -> Response:
            response = await original(request)
            # 只包装明确的 JSONResponse，流式/文件响应一律透传
            if isinstance(response, StreamingResponse):
                return response
            if not isinstance(response, JSONResponse):
                return response
            body = response.body
            if body is None:
                return JSONResponse({"code": 0, "message": "success", "data": None}, status_code=200)
            data = body.decode("utf-8") if isinstance(body, bytes) else body
            if isinstance(data, str):
                data = json.loads(data)
            return JSONResponse({"code": 0, "message": "success", "data": data}, status_code=200)

        return custom_handler


def api_response(data=None, code=0, message="success"):
    """仅供 exception_handler 构造信封；handler 禁止调用。"""
    return {"code": code, "message": message, "data": data}
```

### app/db/__init__.py

```python
```

### app/db/session.py

```python
from app.core.config import settings

if settings.db_type == "mongodb":
    from motor.motor_asyncio import AsyncIOMotorClient

    _mongo_client: AsyncIOMotorClient | None = None

    async def connect_db():
        global _mongo_client
        _mongo_client = AsyncIOMotorClient(settings.database_url)

    async def close_db():
        global _mongo_client
        if _mongo_client:
            _mongo_client.close()

    async def get_db():
        if _mongo_client is None:
            await connect_db()
        return _mongo_client[settings.db_name]


elif settings.db_type == "none":
    class DummyDB:
        async def execute(self, *args, **kwargs):
            return None

        async def command(self, *args, **kwargs):
            return None

    async def get_db():
        return DummyDB()


else:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.orm import DeclarativeBase

    engine = create_async_engine(
        settings.database_url,
        echo=settings.app_debug,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,      # 1 小时后回收连接，防止数据库端连接失效
        pool_pre_ping=True,     # 连接前发送 ping，自动重连失效连接
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


    class Base(DeclarativeBase):
        pass


    async def get_db():
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
```

### app/db/base.py

```python
"""ORM 基类与模型汇总导入：确保 create_all 能发现全部表结构。"""
from app.db.session import Base  # noqa: F401
import app.models.user  # noqa: F401,E402
import app.models.item  # noqa: F401,E402
```

### app/models/__init__.py

```python
from app.models.user import User  # noqa: F401
from app.models.item import Item  # noqa: F401
```

### app/models/user.py

```python
from datetime import datetime

from sqlalchemy import String, DateTime, func, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    """用户表：认证相关字段 + 基础资料，可按需扩展。"""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password: Mapped[str] = mapped_column(String(256), nullable=False)
    email: Mapped[str | None] = mapped_column(String(128), default=None)
    phone: Mapped[str | None] = mapped_column(String(20), default=None)
    nickname: Mapped[str | None] = mapped_column(String(64), default=None)
    avatar: Mapped[str | None] = mapped_column(Text, default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
    refresh_token: Mapped[str | None] = mapped_column(String(512), default=None)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

### app/models/item.py

```python
from datetime import datetime

from sqlalchemy import String, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Item(Base):
    """条目表：示例业务模型，新增业务表时参照本文件编写。"""

    __tablename__ = "item"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    owner_id: Mapped[int] = mapped_column(nullable=False, index=True)  # 创建者用户 ID
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

### app/schemas/__init__.py

```python
```

### app/schemas/user.py

```python
from datetime import datetime

from pydantic import BaseModel, Field, EmailStr


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, description="用户名")
    # 🔴 生产环境建议将 min_length 提高到 8 并增加复杂度校验（大小写+数字+特殊字符）
    password: str = Field(..., min_length=8, max_length=128, description="密码")
    email: EmailStr | None = Field(default=None, max_length=128, description="邮箱")
    phone: str | None = Field(default=None, max_length=20, description="手机号")


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="刷新令牌")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None = None
    phone: str | None = None
    nickname: str | None = None
    avatar: str | None = None
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

### app/schemas/item.py

```python
from datetime import datetime

from pydantic import BaseModel, Field


class ItemCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=128, description="标题")
    description: str | None = Field(default=None, description="描述")


class ItemUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=128, description="标题")
    description: str | None = Field(default=None, description="描述")
    is_active: bool | None = Field(default=None, description="是否启用")


class ItemResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ItemPageResponse(BaseModel):
    page: int
    page_size: int = Field(..., alias="pageSize", serialization_alias="pageSize")
    total: int
    list: list[ItemResponse]
```

### app/crud/__init__.py

```python
```

### app/crud/user.py

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User


async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    username: str,
    password: str,
    email: str | None = None,
    phone: str | None = None,
) -> User:
    user = User(
        username=username,
        password=hash_password(password),
        email=email,
        phone=phone,
    )
    db.add(user)
    await db.flush()
    return user


async def set_refresh_token(db: AsyncSession, user: User, refresh_token: str | None) -> None:
    """写入/清空 refresh_token（登出时传 None）。"""
    user.refresh_token = refresh_token
    await db.flush()
```

### app/crud/item.py

```python
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item


async def get_by_id(db: AsyncSession, item_id: int) -> Item | None:
    result = await db.execute(select(Item).where(Item.id == item_id))
    return result.scalar_one_or_none()


async def list_items(db: AsyncSession, page: int, page_size: int) -> tuple[list[Item], int]:
    """分页查询，返回（条目列表, 总数）。"""
    count_result = await db.execute(select(func.count(Item.id)))
    total = count_result.scalar()
    result = await db.execute(
        select(Item).order_by(Item.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return list(result.scalars().all()), total


async def create(db: AsyncSession, owner_id: int, title: str, description: str | None = None) -> Item:
    item = Item(owner_id=owner_id, title=title, description=description)
    db.add(item)
    await db.flush()
    return item


async def update(db: AsyncSession, item: Item, data: dict) -> Item:
    for key, value in data.items():
        setattr(item, key, value)
    await db.flush()
    return item


async def delete(db: AsyncSession, item: Item) -> None:
    await db.delete(item)
    await db.flush()
```

### app/api/__init__.py

```python
```

### app/api/deps.py

```python
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from app.core import security
from app.core.exceptions import BusinessException
from app.db.session import get_db  # noqa: F401  统一从 deps 透出，路由层只依赖本模块

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """解析 JWT，注入当前用户信息 { user_id, username }。"""
    if credentials is None:
        raise BusinessException(-1002, "未登录，请先获取 Token")
    try:
        payload = security.decode_token(credentials.credentials)
    except JWTError:
        raise BusinessException(-1002, "Token 无效或已过期")
    if payload.get("type") != "access":
        raise BusinessException(-1002, "Token 类型错误")
    return {"user_id": int(payload["sub"]), "username": payload["username"]}
```

### app/api/routes/__init__.py

```python
```

### app/api/routes/health.py

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.core.config import settings
from app.core.response import EnvelopeRoute
from app.api.deps import get_db

router = APIRouter(route_class=EnvelopeRoute)


@router.get("/health", summary="健康检查")
async def health():
    return {"status": "ok"}


@router.get("/health/db", summary="数据库连通性检查")
async def health_db(db=Depends(get_db)):
    if settings.db_type == "none":
        return {"status": "ok", "database": "none"}
    try:
        if hasattr(db, "command"):
            await db.command("ping")
        else:
            await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        return {"status": "ok", "database": "disconnected"}
```

### app/api/routes/auth.py

```python
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import bearer_scheme, get_current_user, get_db
from app.core import security
from app.core.exceptions import BusinessException
from app.core.response import EnvelopeRoute
from app.crud import user as crud_user
from app.schemas.user import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(route_class=EnvelopeRoute)


@router.post("/register", summary="注册新用户")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if await crud_user.get_by_username(db, body.username):
        raise BusinessException(-1005, "用户名已存在")
    user = await crud_user.create(db, body.username, body.password, body.email, body.phone)
    access_token = security.create_access_token(user.id, user.username)
    refresh_token = security.create_refresh_token(user.id, user.username)
    await crud_user.set_refresh_token(db, user, refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", summary="用户登录")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await crud_user.get_by_username(db, body.username)
    if not user or not security.verify_password(body.password, user.password):
        raise BusinessException(-1002, "用户名或密码错误")
    if not user.is_active:
        raise BusinessException(-1002, "账号已被禁用")
    access_token = security.create_access_token(user.id, user.username)
    refresh_token = security.create_refresh_token(user.id, user.username)
    user.last_login_at = datetime.now(timezone.utc)
    await crud_user.set_refresh_token(db, user, refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", summary="刷新令牌")
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = security.decode_token(body.refresh_token)
    except JWTError:
        raise BusinessException(-1002, "刷新令牌无效或已过期")
    if payload.get("type") != "refresh":
        raise BusinessException(-1002, "无效的刷新令牌")

    user = await crud_user.get_by_id(db, int(payload["sub"]))
    if not user or user.refresh_token != body.refresh_token:
        raise BusinessException(-1002, "刷新令牌无效")

    access_token = security.create_access_token(user.id, user.username)
    refresh_token = security.create_refresh_token(user.id, user.username)
    await crud_user.set_refresh_token(db, user, refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", summary="登出")
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    if credentials:
        try:
            payload = security.decode_token(credentials.credentials)
            user = await crud_user.get_by_id(db, int(payload["sub"]))
            if user:
                await crud_user.set_refresh_token(db, user, None)
        except JWTError:
            pass
    return {"message": "已登出"}


@router.get("/me", summary="当前用户信息")
async def me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await crud_user.get_by_id(db, current_user["user_id"])
    if not user:
        raise BusinessException(-1004, "用户不存在")
    return UserResponse.model_validate(user)
```

### app/api/routes/items.py

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.exceptions import BusinessException
from app.core.response import EnvelopeRoute
from app.crud import item as crud_item
from app.schemas.item import (
    ItemCreateRequest,
    ItemPageResponse,
    ItemResponse,
    ItemUpdateRequest,
)

router = APIRouter(route_class=EnvelopeRoute)


@router.get("", summary="条目列表（分页）")
async def list_items(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize", description="每页数量"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    items, total = await crud_item.list_items(db, page, page_size)
    return ItemPageResponse(
        page=page,
        pageSize=page_size,
        total=total,
        list=[ItemResponse.model_validate(i) for i in items],
    )


@router.post("", summary="创建条目")
async def create_item(
    body: ItemCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    item = await crud_item.create(db, owner_id=current_user["user_id"], title=body.title, description=body.description)
    return ItemResponse.model_validate(item)


@router.get("/{item_id}", summary="条目详情")
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    item = await crud_item.get_by_id(db, item_id)
    if not item:
        raise BusinessException(-1004, "条目不存在")
    return ItemResponse.model_validate(item)


@router.put("/{item_id}", summary="更新条目")
async def update_item(
    item_id: int,
    body: ItemUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    item = await crud_item.get_by_id(db, item_id)
    if not item:
        raise BusinessException(-1004, "条目不存在")
    if item.owner_id != current_user["user_id"]:
        raise BusinessException(-1003, "无权限操作该条目")
    data = body.model_dump(exclude_unset=True)
    item = await crud_item.update(db, item, data)
    return ItemResponse.model_validate(item)


@router.delete("/{item_id}", summary="删除条目")
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    item = await crud_item.get_by_id(db, item_id)
    if not item:
        raise BusinessException(-1004, "条目不存在")
    if item.owner_id != current_user["user_id"]:
        raise BusinessException(-1003, "无权限操作该条目")
    await crud_item.delete(db, item)
    return {"message": "删除成功"}
```

### .env.example

```env
# ==================== 应用配置 ====================
APP_NAME={{project}}
APP_PORT=8080
# ⚠️ 生产环境必须设为 false，防止泄漏堆栈跟踪、配置详情等敏感信息
APP_DEBUG=true

# ==================== 数据库配置 ====================
# 数据库类型：mysql（默认） / postgresql / mongodb / none
DB_TYPE=mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=app_db
DB_USER=root
# 🔴 生产环境务必修改为强密码！
DB_PASSWORD=root

# 完整连接串示例（优先级高于上面分项）:
# DB_URL=mysql+aiomysql://root:root@localhost:3306/app_db?charset=utf8mb4

# ==================== 安全配置 ====================
# 🔴 生产环境必须修改为随机字符串（建议 32 字节以上）！
# 生成命令：openssl rand -hex 32
JWT_SECRET=change-me-in-production
JWT_EXPIRES_IN=86400
JWT_REFRESH_EXPIRES_IN=604800
BCRYPT_ROUNDS=12

# ==================== CORS ====================
# 🔴 生产环境必须指定具体域名，禁止用 *，否则存在 CSRF 等安全风险
# 示例：CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
CORS_ORIGINS=*
```

### .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*.so
*.egg-info/
dist/
build/
venv/
.env
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# 数据库
*.db
*.sqlite3

# Docker
.docker/

# 日志
*.log
logs/

# 测试
.coverage
htmlcov/
.pytest_cache/

# 环境配置（敏感信息，切勿提交到仓库）
.env.production
.env.local
.env.*.local
```

### gunicorn.conf.py

```python
"""gunicorn 生产配置（仅 Linux/macOS；Windows 下 restart.bat 仍使用 uvicorn）。

由 restart.sh prod 启动：gunicorn app.main:app -c gunicorn.conf.py
热更新：代码更新后再次执行 ./restart.sh prod，脚本给 master 发 HUP 信号，
新 worker 加载新代码、旧 worker 处理完存量请求后退出，服务不中断。
"""

import os

# 端口与 worker 数来自环境变量，与 restart.sh 的约定保持一致
bind = "0.0.0.0:" + os.getenv("APP_PORT", "8080")
workers = int(os.getenv("APP_WORKERS", "2"))
worker_class = "uvicorn_worker.UvicornWorker"

# master 进程 PID 写入 app.pid，restart.sh 的热更新判断与 kill -HUP 依赖它
pidfile = "app.pid"

# ⚠️ 保持 False：HUP 热更新依赖 worker 重新 import 磁盘上的新代码；
# 开启 True 会导致 HUP 出来的新 worker 仍跑 master 内存中的旧代码
preload_app = False

# 优雅退出最长等待（秒）：旧 worker 处理完存量请求，超时强杀
graceful_timeout = 30
# worker 无响应判定（秒）：超时被 master 自动拉起
timeout = 60
# keepalive 长连接保持（秒）
keepalive = 5
```

## 关键约定

- 表名：snake_case 单数（如 `user`、`item`），主键 `id` 自增，必备 `created_at` / `updated_at`
- 路由前缀：`/api`；认证路由 `/api/auth/*`；示例 CRUD `/api/items`
- 健康检查：`GET /api/health`、`GET /api/health/db`
- 校验：Pydantic v2，失败由 `RequestValidationError` handler 转 `-1001`
- 统一响应：`EnvelopeRoute` 自动包装 `{ code, message, data }`，非 JSON 响应自动透传
- 数据库默认 MySQL，可选 PostgreSQL / MongoDB / 暂不启用数据库；MongoDB 与 none 模式仅 health 路由可用（认证与 CRUD 模板基于 SQLAlchemy）
- 密码 bcrypt 12 rounds，最小 8 位
- JWT access_token 24h / refresh_token 7d
- 生产模式：gunicorn master-worker 托管（`gunicorn.conf.py`）；服务运行中重复执行 `./restart.sh prod` 即热更新（HUP 优雅重启 worker），开发模式仍为 uvicorn --reload
- 所有注释、文档使用中文

### Dockerfile

```dockerfile
# 构建阶段
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 运行阶段
FROM python:3.11-slim
WORKDIR /app

# 非 root 运行，降低安全风险
RUN groupadd -r appuser && useradd -r -g appuser appuser
COPY --from=builder /root/.local /home/appuser/.local
COPY . .
RUN chown -R appuser:appuser /app
USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8080
CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]
```

### docker-compose.yml

```yaml
version: "3.8"

services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: app_db
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
```

### docker-compose.pg.yml

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: root
      POSTGRES_DB: app_db
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data

volumes:
  pg_data:
```

### docker-compose.mongo.yml

```yaml
version: "3.8"

services:
  mongo:
    image: mongo:6
    environment:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: root
      MONGO_INITDB_DATABASE: app_db
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

volumes:
  mongo_data:
```

## project-guide 填充段

生成 `docs/project-guide.md` 时，按本 skill `references/project-guide-template.md` 的占位符填入以下本栈内容：

| 占位符 | 本栈填充值 |
|--------|-----------|
| `{{STACK}}` | Python + FastAPI + SQLAlchemy 2.0 异步 + JWT 鉴权（python-jose） |
| `{{START_COMMAND}}` | `./restart.sh dev`（开发）/ `./restart.sh prod`（生产） |
| `{{DIRECTORY_TREE}}` | 上文「目录结构」节 |
| `{{LAYER_RESPONSIBILITY}}` | api/routes 接请求、做业务编排；api/deps 依赖注入（get_db / get_current_user）；core 配置（config）、安全（security）、统一响应（response）、业务异常（exceptions）；crud 数据访问；models 表映射（SQLAlchemy ORM）；schemas 出入参校验（Pydantic v2）；db 引擎与 Session（session/base）；main 注册中间件/异常/路由 |
| `{{MIDDLEWARE_CHAIN}}` | `security_headers_middleware 安全头 → request_log_middleware 日志 → CORSMiddleware → 路由匹配 → get_current_user 鉴权依赖 → Pydantic v2 校验 → EnvelopeRoute 信封包装（非 JSON 响应自动透传）→ exception_handler 异常兜底` |
| `{{VALIDATION_WAY}}` | 请求体/查询参数用 Pydantic v2 模型 + 类型注解 + Field 约束，失败由 `RequestValidationError` handler 转 `-1001` |
| `{{ENVELOPE_WAY}}` | `EnvelopeRoute` 为唯一包装点，handler 返回裸数据；`api_response` 仅供 exception_handler 兜底；文件下载等非 JSON 响应自动透传 |
| `{{MODULE_STEPS}}` | ① `app/models/xxx.py` → ② `app/schemas/xxx.py` → ③ `app/crud/xxx.py` → ④ `app/api/routes/xxx.py`（`APIRouter(route_class=EnvelopeRoute)`）→ ⑤ `app/main.py` 中 `include_router` → ⑥ `python -m compileall app` + curl 验证 |
| `{{MIDDLEWARE_STEPS}}` | 横切逻辑用 `@app.middleware("http")`；鉴权/权限类优先用 `Depends` 依赖注入 |
| `{{ONE_CLICK_WAY}}` | Linux/macOS 运行 `./restart.sh [dev|prod]`（dev 热重载；prod 由 gunicorn master-worker 托管，服务运行中重复执行即热更新），Windows 运行 `restart.bat [dev|prod]`；脚本自动检测/创建 venv → 安装依赖 → 热更新或安全停止旧进程 → 启动服务 → 输出日志命令 |
| `{{MIGRATION_WAY}}` | 开发阶段 `lifespan` 中 `create_all()` 自动建表；生产环境请使用 Alembic 管理迁移 |
| `{{DB_START_WAY}}` | MySQL：`docker run -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=app_db mysql:8.0`；PostgreSQL：`docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=root -e POSTGRES_DB=app_db postgres:15`；MongoDB：`docker run -d -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=root -e MONGO_INITDB_ROOT_PASSWORD=root -e MONGO_INITDB_DATABASE=app_db mongo:6`；无数据库：将 `.env` 中 `DB_TYPE=none`。本地安装：确保数据库已启动且 `.env` 中连接信息正确 |
