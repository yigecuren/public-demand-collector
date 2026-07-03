#!/bin/bash

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

PYTHON_BIN="${PYTHON_BIN:-python3}"

pause() {
  echo
  read -r -p "按回车继续..." _
}

require_python() {
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "没有找到 python3。"
    echo "请先安装 Python 3，再重新双击 run.command。"
    pause
    exit 1
  fi
}

run_cmd() {
  echo
  echo "正在执行：$*"
  echo
  "$@"
  local status=$?
  echo
  if [ $status -eq 0 ]; then
    echo "执行完成。"
  else
    echo "执行失败，退出码：$status"
  fi
  pause
}

show_header() {
  clear
  echo "=============================="
  echo " 公域需求收集工具"
  echo "=============================="
  echo "当前目录：$SCRIPT_DIR"
  echo
}

show_menu() {
  echo "请选择要执行的操作："
  echo "1. 生成手工导入模板"
  echo "2. 运行示例配置（queries.example.json）"
  echo "3. 抓取 B 站样本（关键词：副业）"
  echo "4. 查看帮助"
  echo "5. 打开 output 目录"
  echo "0. 退出"
  echo
}

open_output_dir() {
  mkdir -p "$SCRIPT_DIR/output"
  open "$SCRIPT_DIR/output"
  echo "已打开 output 目录。"
  pause
}

main() {
  require_python

  while true; do
    show_header
    show_menu
    read -r -p "请输入数字并回车： " choice

    case "$choice" in
      1)
        run_cmd "$PYTHON_BIN" demand_collector.py template
        ;;
      2)
        run_cmd "$PYTHON_BIN" demand_collector.py run-config --config queries.example.json
        ;;
      3)
        run_cmd "$PYTHON_BIN" demand_collector.py fetch-bilibili --query "副业" --limit 10
        ;;
      4)
        run_cmd "$PYTHON_BIN" demand_collector.py --help
        ;;
      5)
        open_output_dir
        ;;
      0)
        exit 0
        ;;
      *)
        echo
        echo "请输入 0-5 之间的数字。"
        pause
        ;;
    esac
  done
}

main
