#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-.}"

if ! command -v rg >/dev/null 2>&1; then
  echo "错误：缺少 ripgrep（rg）命令，请先安装后再执行。"
  exit 2
fi

if [ ! -d "$TARGET" ] && [ ! -f "$TARGET" ]; then
  echo "错误：目标路径不存在：$TARGET"
  exit 2
fi

error_count=0
warn_count=0

print_hits() {
  local level="$1"
  local title="$2"
  local pattern="$3"
  shift 3

  local out
  out=$(rg -n --hidden --glob '!node_modules' --glob '!.git' "$@" "$pattern" "$TARGET" || true)
  if [ -n "$out" ]; then
    echo "[$level] $title"
    echo "$out"
    echo
    if [ "$level" = "ERROR" ]; then
      error_count=$((error_count + 1))
    else
      warn_count=$((warn_count + 1))
    fi
  fi
}

print_hits "ERROR" "仍存在 Vant 组件引用" "<van-|from ['\"]vant|@vant" --glob '*.vue' --glob '*.ts'
print_hits "ERROR" "仍存在 Vue Router 旧 API 调用" "router\.push|router\.replace|router\.go\(-1\)|currentRoute\.value\.query" --glob '*.vue' --glob '*.ts'
print_hits "ERROR" "仍存在不建议的页面生命周期钩子" "onBeforeMount\(|onUnmounted\(" --glob '*.vue' --glob '*.ts'

print_hits "WARN" "可能仍有 px 单位未转换" "[0-9]+px" --glob '*.vue' --glob '*.scss' --glob '*.css'
# print_hits "WARN" "检测到 @include，请确认是否已正确引入 mixins.scss" "@include" --glob '*.scss'

echo "审计汇总：错误(ERROR)=${error_count}，警告(WARN)=${warn_count}"

if [ "$error_count" -gt 0 ]; then
  exit 1
fi
