# 公域需求收集工具

一个基于 Python 标准库的命令行工具，用来抓取和整理公域平台内容样本，并输出结构化的需求报告与机会池。

这个公开版仓库只保留工具本体、示例配置和示例数据模板，不包含你的私有笔记、抓取结果或原始平台返回数据。

## 功能

- 抓取 B 站搜索结果
- 通过 `tikhub` 抓取小红书、抖音、B 站结果
- 合并多份输入样本做需求分析
- 按主题批量生成日报/周报
- 导出机会池和产品清单

## 仓库结构

```text
.
├── README.md
├── demand_collector.py
├── queries.example.json
└── data/
    ├── blue_ocean_topics.json
    ├── manual_template.csv
    └── weekly_topics.json
```

## 环境要求

- Python 3.10+
- 可选：`tikhub` CLI

脚本本身只依赖 Python 标准库，不需要安装第三方 Python 包。

## 一键启动

如果你是 Mac 用户，可以直接双击：

```text
run.command
```

它会打开终端菜单，你可以直接选择：

- 生成手工导入模板
- 运行示例配置
- 抓取一份 B 站样本
- 打开 `output/` 输出目录

第一次双击如果被系统拦住，可以：

1. 右键 `run.command`
2. 点“打开”
3. 再确认一次打开

## 命令行使用

### 1. 生成手工导入模板

```bash
python3 demand_collector.py template
```

输出文件：

```text
data/manual_template.csv
```

### 2. 抓取 B 站样本

```bash
python3 demand_collector.py fetch-bilibili \
  --query '副业' \
  --limit 10
```

输出文件：

```text
output/bilibili_副业.jsonl
```

### 3. 通过 tikhub 抓取跨平台样本

```bash
python3 demand_collector.py fetch-tikhub \
  --platform xiaohongshu \
  --query '副业' \
  --limit 10 \
  --raw-output output/xiaohongshu_副业_raw.json
```

如果你使用 `tikhub`，需要先准备好自己的 `TIKHUB_API_KEY`，并按你本地的 CLI 约定配置环境变量。

### 4. 分析样本

```bash
python3 demand_collector.py analyze \
  --topic '副业需求' \
  --input output/bilibili_副业.jsonl \
  --input data/manual_template.csv
```

### 5. 按配置批量跑

```bash
python3 demand_collector.py run-config \
  --config queries.example.json
```

## 适合上传 GitHub 的内容

- 工具代码
- 示例配置
- 空模板
- 说明文档

## 不建议上传的内容

- `output/` 下的抓取结果
- 任意平台原始返回 JSON
- 你的 API Key、Cookie、账号信息
- 私人笔记、过程文档、业务素材

## 给朋友使用时的最低要求

- macOS
- 已安装 `python3`
- 如果要抓小红书 / 抖音 / TikHub 数据，还需要对方自己配置 `TIKHUB_API_KEY`

## 后续可继续增强

- 再补一个 `setup.command`，自动检查 Python 和环境
- 再补 Windows 版 `start.bat`
- 做成带按钮的桌面 GUI 或网页版本
