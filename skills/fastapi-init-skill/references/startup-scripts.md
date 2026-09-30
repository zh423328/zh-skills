# 一键启动脚本模板

生成项目时，只落地两个脚本：

- `restart.sh`（Linux / macOS）
- `restart.bat`（Windows）

一条命令完成：拉代码 → 装依赖 → 热更新或安全停止旧进程 → 启动服务 → 输出日志命令。

**两种模式的运行方式不同**：

| 模式 | 启动方式 | 热更新 |
|------|----------|--------|
| `dev` | `uvicorn --reload` | 文件变更自动重启进程（热重载） |
| `prod`（Linux/macOS） | `gunicorn -c gunicorn.conf.py`（master-worker） | 服务运行中重复执行 `./restart.sh prod`，脚本给 master 发 `kill -HUP`，优雅重启 worker，**服务不中断** |
| `prod`（Windows） | `uvicorn --workers` | 无（gunicorn 不支持 Windows） |

## 使用方式

```bash
# Linux / macOS
./restart.sh          # 默认 dev 模式（热重载，日志 logs/dev.log）
./restart.sh prod     # 生产模式（gunicorn master-worker，日志 logs/app.log）
./restart.sh prod     # 服务运行中再次执行 = 热更新（HUP 优雅重启 worker）
```

```batch
:: Windows
restart.bat         :: 默认 dev 模式
restart.bat prod    :: 生产模式（uvicorn 多 worker，无热更新）
```

环境变量（由 `gunicorn.conf.py` 与脚本共同约定）：

- `APP_PORT`：端口，默认 8080
- `APP_WORKERS`：`prod` 模式 worker 数，默认 2

## 编写规则（强制）

1. **单入口**：每个平台只生成一个脚本，禁止拆成 setup / dev / start / restart 多个文件。
2. **参数区分模式**：`./restart.sh dev` 开发模式（uvicorn --reload），`./restart.sh prod` 生产模式（gunicorn master-worker），默认 `dev`。
3. **一条龙**：脚本必须依次完成——拉代码（可选）→ 安装/更新依赖 → 热更新或安全停止旧进程 → 启动服务 → 输出日志命令。
4. **生产热更新优先**：`prod` 模式下若 `app.pid` 对应的进程存活、进程命令行包含 gunicorn、且 `APP_PORT` 正在监听，则只发 `kill -HUP` 热更新，**不执行杀旧进程**；三个条件任一不满足（首次启动、进程挂了、改了端口）才走完全重启。dev 模式永远走完全重启。注意用 `ps -o command=` 匹配命令行而不是 `comm=`——gunicorn 的 comm 显示为 python3（除非安装了 setproctitle）。
5. **安全杀旧进程**（完全重启路径）：
   - 先按 `app.pid` 停止已记录的 uvicorn/gunicorn/python 进程；
   - 若 PID 文件丢失或进程已失效，必须按 `APP_PORT` 扫描并强制清理占用端口的残留进程；
   - 禁止无差别 `killall python`。
6. **自动生成 .env**：启动前若根目录无 `.env`，自动从 `.env.example` 复制并提示用户编辑。
7. **日志落地**：`dev` 输出到 `logs/dev.log`，`prod` 输出到 `logs/app.log`，启动成功后必须打印查看日志命令。
8. **PID 记录**：dev 模式启动后把主进程 PID 写入 `app.pid`；prod 模式由 `gunicorn.conf.py` 的 `pidfile` 配置写入同一个 `app.pid`（master 进程）。
9. **失败可排查**：启动失败时打印最近 50 行日志路径，而不是只报"起不来"。
10. **跨平台**：`.sh` 使用 POSIX/Bash，`set -e`；`.bat` 使用 `setlocal enabledelayedexpansion`，错误时 `exit /b`。
11. **不替用户提交 git**：可以 `git pull`，但绝不执行 `git add/commit/push`。

## restart.sh（Linux / macOS）

```bash
#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

MODE="${1:-dev}"
PORT="${APP_PORT:-8080}"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/logs"
PID_FILE="$PROJECT_DIR/app.pid"

if [ "$MODE" = "prod" ]; then
    LOG_FILE="$LOG_DIR/app.log"
    WORKERS="${APP_WORKERS:-2}"
else
    LOG_FILE="$LOG_DIR/dev.log"
    WORKERS=1
fi

mkdir -p "$LOG_DIR"

echo "========================================"
echo "  一键重启 [$MODE]"
echo "  端口：$PORT"
echo "  日志：$LOG_FILE"
echo "========================================"

# 1. 拉取代码（可选）
if command -v git &> /dev/null && [ -d "$PROJECT_DIR/.git" ]; then
    echo "[1/4] 拉取代码更新..."
    git pull || echo "  ⚠ git pull 失败，将继续使用当前代码"
else
    echo "[1/4] 未检测到 git 仓库，跳过拉取"
fi

# 2. 安装/更新依赖
echo "[2/4] 检查环境并安装依赖..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR" 2>/dev/null || python -m venv "$VENV_DIR"
    echo "  ✓ 虚拟环境已创建"
fi
source "$VENV_DIR/bin/activate"
pip install -r "$PROJECT_DIR/requirements.txt"
echo "  ✓ 依赖已更新"

# 3. 生产模式优先热更新：gunicorn master 存活 + 端口在监听 → 只发 HUP，不断服务
HOT_UPDATED=0
PID=""
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null || true)
fi
if [ "$MODE" = "prod" ] && [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null \
    && ps -p "$PID" -o command= 2>/dev/null | grep -q "gunicorn" \
    && command -v lsof &> /dev/null && lsof -ti tcp:"$PORT" >/dev/null 2>&1; then
    echo "[3/4] 检测到 gunicorn 服务运行中，热更新（HUP 优雅重启 worker）..."
    kill -HUP "$PID"
    HOT_UPDATED=1
    sleep 2
    echo "  ✓ 热更新完成：新 worker 已加载最新代码，旧 worker 处理完存量请求后退出"
else
    # 3. 安全停止旧进程（首次启动 / 进程已挂 / dev 模式 / 改过端口时走这里）
    echo "[3/4] 安全停止旧进程..."
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" -o command= 2>/dev/null | grep -qE "uvicorn|gunicorn|python"; then
            echo "  → 停止 PID: $PID"
            kill "$PID" 2>/dev/null || true
            sleep 2
        else
            echo "  ⚠ PID 文件已失效，忽略"
        fi
        rm -f "$PID_FILE"
    fi

    OLD_PIDS=""
    if command -v lsof &> /dev/null; then
        OLD_PIDS=$(lsof -ti tcp:"$PORT" 2>/dev/null || true)
    elif command -v ss &> /dev/null; then
        OLD_PIDS=$(ss -ltnp "sport = :$PORT" 2>/dev/null | awk -F'pid=' '{print $2}' | awk -F',' '{print $1}' | sort -u | tr '\n' ' ')
    elif command -v fuser &> /dev/null; then
        fuser -k "$PORT"/tcp 2>/dev/null || true
    fi

    if [ -n "$OLD_PIDS" ]; then
        echo "  → 端口 $PORT 仍有残留进程，强制清理: $OLD_PIDS"
        kill -9 $OLD_PIDS 2>/dev/null || true
        sleep 1
    fi

    echo "  ✓ 旧进程已清理"
fi

# 4. 启动服务（热更新路径跳过）
if [ "$HOT_UPDATED" = "0" ]; then
    echo "[4/4] 启动服务..."
    if [ ! -f "$PROJECT_DIR/.env" ] && [ -f "$PROJECT_DIR/.env.example" ]; then
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        echo "  ⚠ 已自动生成 .env，请编辑后重新启动"
    fi

    if [ "$MODE" = "prod" ]; then
        # 生产：gunicorn master-worker 托管；服务运行中再次执行 ./restart.sh prod 即热更新
        echo "  启动方式：gunicorn master-worker（$WORKERS workers）"
        APP_PORT="$PORT" APP_WORKERS="$WORKERS" nohup gunicorn app.main:app -c gunicorn.conf.py > "$LOG_FILE" 2>&1 &
    else
        nohup uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload --log-level info > "$LOG_FILE" 2>&1 &
    fi

    echo $! > "$PID_FILE"

    sleep 1
    if ps -p "$(cat "$PID_FILE")" -o comm= &> /dev/null; then
        echo ""
        echo "========================================"
        echo "  ✓ 服务已启动 [$MODE]"
        echo "  PID: $(cat "$PID_FILE")"
        echo "  Swagger: http://localhost:${PORT}/docs"
        echo "  健康检查: http://localhost:${PORT}/api/health"
        if [ "$MODE" = "prod" ]; then
            echo ""
            echo "  热更新：代码更新后再次执行 ./restart.sh prod"
            echo "  （HUP 优雅重启 worker，服务不中断）"
        fi
        echo ""
        echo "  查看日志："
        echo "    tail -f \"$LOG_FILE\""
        echo "========================================"
    else
        echo "  ✗ 服务启动失败，请查看日志："
        echo "    tail -n 50 \"$LOG_FILE\""
        exit 1
    fi
else
    echo ""
    echo "========================================"
    echo "  ✓ 热更新完成 [$MODE]"
    echo "  PID: $(cat "$PID_FILE")"
    echo "  Swagger: http://localhost:${PORT}/docs"
    echo "  健康检查: http://localhost:${PORT}/api/health"
    echo ""
    echo "  查看日志："
    echo "    tail -f \"$LOG_FILE\""
    echo "========================================"
fi
```

Windows 不支持 gunicorn，prod 模式仍使用 uvicorn 多 worker，无热更新能力。

## restart.bat（Windows）

```batch
@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set PROJECT_DIR=%~dp0
cd /d "%PROJECT_DIR%"

set MODE=dev
if not "%~1"=="" set MODE=%~1
set PORT=8080
if defined APP_PORT set PORT=%APP_PORT%
set VENV_DIR=%PROJECT_DIR%venv
set LOG_DIR=%PROJECT_DIR%logs
set PID_FILE=%PROJECT_DIR%app.pid

if "%MODE%"=="prod" (
    set LOG_FILE=%LOG_DIR%\app.log
    set WORKERS=2
    if defined APP_WORKERS set WORKERS=%APP_WORKERS%
) else (
    set LOG_FILE=%LOG_DIR%\dev.log
    set WORKERS=1
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo ========================================
echo   一键重启 [%MODE%]
echo   端口：%PORT%
echo   日志：%LOG_FILE%
echo ========================================

:: 1. 拉取代码（可选）
where git >nul 2>nul
if !errorlevel! equ 0 (
    if exist "%PROJECT_DIR%.git" (
        echo [1/4] 拉取代码更新...
        git pull
        if !errorlevel! neq 0 echo   ! git pull 失败，将继续使用当前代码
    ) else (
        echo [1/4] 未检测到 git 仓库，跳过拉取
    )
) else (
    echo [1/4] 未安装 git，跳过拉取
)

:: 2. 安装/更新依赖
echo [2/4] 检查环境并安装依赖...
if not exist "%VENV_DIR%" (
    python -m venv "%VENV_DIR%"
    echo   虚拟环境已创建
)
call "%VENV_DIR%\Scripts\activate.bat"
pip install -r "%PROJECT_DIR%requirements.txt"
echo   依赖已更新

:: 3. 安全停止旧进程
echo [3/4] 安全停止旧进程...
if exist "%PID_FILE%" (
    for /f %%P in (%PID_FILE%) do (
        echo   停止旧进程 PID: %%P
        taskkill /PID %%P >nul 2>nul
        timeout /t 2 /nobreak >nul
        taskkill /PID %%P /F >nul 2>nul
    )
    del "%PID_FILE%"
)

for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%PORT%"') do (
    echo   端口 %PORT% 仍被占用，清理残留 PID: %%A
    taskkill /PID %%A /F >nul 2>nul
)
timeout /t 1 /nobreak >nul
echo   旧进程已清理

:: 4. 启动服务
echo [4/4] 启动服务...
if not exist "%PROJECT_DIR%.env" (
    if exist "%PROJECT_DIR%.env.example" (
        copy /y "%PROJECT_DIR%.env.example" "%PROJECT_DIR%.env" >nul
        echo   ! 已自动生成 .env，请编辑后重新启动
    )
)

if "%MODE%"=="prod" (
    start /b uvicorn app.main:app --host 0.0.0.0 --port %PORT% --workers %WORKERS% --limit-max-requests 10000 --limit-concurrency 100 --timeout-graceful-shutdown 30 --log-level info > "%LOG_FILE%" 2>&1
) else (
    start /b uvicorn app.main:app --host 0.0.0.0 --port %PORT% --reload --log-level info > "%LOG_FILE%" 2>&1
)

:: 5. 记录 PID
timeout /t 2 /nobreak >nul
set PID=
for /f "tokens=2 delims=," %%P in ('wmic process where "name='python.exe' and CommandLine like '%%app.main:app%%'" get ProcessId /format:csv 2^>nul ^| findstr "[0-9]"') do (
    echo %%P > "%PID_FILE%"
    set PID=%%P
    goto :started
)
:started

echo.
echo ========================================
echo   服务已启动 [%MODE%]
if defined PID echo   PID: %PID%
echo   Swagger: http://localhost:%PORT%/docs
echo   健康检查: http://localhost:%PORT%/api/health
echo.
echo   查看日志：
echo     type "%LOG_FILE%"            （查看全部）
echo     Get-Content "%LOG_FILE%" -Wait    （PowerShell 实时查看）
echo ========================================

pause
```

## 脚本权限设置（Linux / macOS）

生成 `.sh` 文件后，需执行：

```bash
chmod +x restart.sh
```

## 自定义端口与工作进程

```bash
# 使用自定义端口
APP_PORT=9090 ./restart.sh

# 生产模式指定 worker 数
APP_PORT=9090 APP_WORKERS=4 ./restart.sh prod

# 改端口后无需手动清理：脚本检测到端口未监听，会自动停旧进程再按新端口启动
```

Windows：

```batch
set APP_PORT=9090
restart.bat prod
```

## AI 生成注意事项

1. 生成 `.sh` 和 `.bat` 文件时，分别使用 LF 和 CRLF 换行符
2. `.sh` 文件自动设置可执行权限
3. Windows 脚本必须保存为 **UTF-8 with BOM**；模板本身是 UTF-8 纯文本，生成到项目时需自动追加 BOM（`\xef\xbb\xbf`），否则 `cmd.exe` 会按系统默认 ANSI（中文系统为 GBK）解析，导致中文乱码、命令被截断
4. Windows 脚本首行保留 `chcp 65001` 将控制台切到 UTF-8，配合 BOM 保证中文显示正常
5. Shell 脚本使用 `set -e`，batch 脚本错误时 `exit /b`
6. 生成时需根据用户的项目名替换 `app` 目录路径
7. `DB_TYPE` 根据用户选择的数据库类型生成（mysql / postgresql / mongodb / none）
8. `restart.sh prod` 依赖 `gunicorn.conf.py`（生成器必须同时落地该文件），二者配套使用
