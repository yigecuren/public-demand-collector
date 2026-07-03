#!/bin/bash

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

PYTHON_BIN="${PYTHON_BIN:-python3}"

pause() {
  echo
  read -r -p "按回车退出..." _
}

print_header() {
  clear
  echo "=============================="
  echo " 公域需求收集工具 - 初始化"
  echo "=============================="
  echo
}

check_python() {
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "未找到 python3。"
    echo
    echo "请先安装 Python 3："
    echo "https://www.python.org/downloads/"
    echo
    echo "安装完成后，再双击 setup.command。"
    return 1
  fi

  echo "已找到 Python：$("$PYTHON_BIN" --version 2>&1)"
  return 0
}

check_script() {
  if [ ! -f "$SCRIPT_DIR/demand_collector.py" ]; then
    echo "未找到 demand_collector.py。"
    echo "请确认你打开的是完整项目目录。"
    return 1
  fi

  if ! "$PYTHON_BIN" -m py_compile "$SCRIPT_DIR/demand_collector.py"; then
    echo
    echo "脚本检查失败，请重新下载项目后再试。"
    return 1
  fi

  echo "脚本检查通过。"
  return 0
}

prepare_dirs() {
  mkdir -p "$SCRIPT_DIR/output"
  echo "已准备 output 目录。"
}

show_next_steps() {
  echo
  echo "初始化完成。"
  echo
  echo "你现在可以："
  echo "1. 双击 run.command"
  echo "2. 在菜单里选择要执行的操作"
  echo
  echo "如果你需要抓取小红书 / 抖音 / TikHub 数据，"
  echo "还需要先配置自己的 TIKHUB_API_KEY。"
}

main() {
  print_header

  if ! check_python; then
    pause
    exit 1
  fi

  if ! check_script; then
    pause
    exit 1
  fi

  prepare_dirs
  show_next_steps
  pause
}

main
