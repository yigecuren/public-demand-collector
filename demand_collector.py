#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import html
import json
import math
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
DEFAULT_TEMPLATE = DATA_DIR / "manual_template.csv"
CLAUDE_ENV = Path.home() / ".claude" / ".env"
TIKHUB_CLI_CANDIDATES = [
    Path.home() / ".local" / "bin" / "tikhub",
    Path.home() / ".codex" / "skills" / "social-account-doctor" / "tikhub" / "bin" / "tikhub",
]
TIKHUB_DEFAULT_TOOLS = {
    "xiaohongshu": "xiaohongshu_app_v2_search_notes",
    "douyin": "douyin_search_fetch_video_search_v2",
    "bilibili": "bilibili_web_fetch_general_search",
}

USER_AGENT = "Mozilla/5.0"
BILIBILI_HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://www.bilibili.com/",
    "Origin": "https://www.bilibili.com",
    "Accept": "application/json, text/plain, */*",
}
DEMAND_CUES = [
    "怎么",
    "如何",
    "有没有",
    "求",
    "不会",
    "想做",
    "想卖",
    "推荐",
    "避坑",
    "需要",
    "能不能",
    "麻烦",
    "副业",
    "变现",
    "赚钱",
]
TITLE_BAIT_CUES = [
    "一篇说清楚",
    "纯小白",
    "一分钟",
    "太爽了",
    "终极指南",
    "喂饭版",
    "不要错过",
    "必须看",
    "超赚",
    "暴利",
    "野路子",
    "普通人真可以",
]
REAL_DEMAND_CUES = [
    "类目怎么选",
    "怎么做",
    "如何做",
    "怎么卖",
    "能不能做",
    "求模板",
    "求资料",
    "不会做",
    "哪里找",
    "怎么变现",
    "怎么引流",
    "怎么接单",
]
PAYMENT_INTENT_CUES = [
    "怎么买",
    "怎么下单",
    "有链接吗",
    "多少钱",
    "价格",
    "收费",
    "付费",
    "哪里买",
    "怎么购买",
    "能买吗",
    "有现成的吗",
    "求链接",
]
BLUE_OCEAN_PROBLEM_CUES = [
    "猫",
    "狗",
    "宠物",
    "补光灯",
    "补光",
    "自拍",
    "拍照",
    "返图",
    "前置",
    "录像",
    "夜灯",
    "收纳",
    "租房",
    "宿舍",
    "工位",
    "桌面",
    "厨房",
    "浴室",
    "老人",
    "宝宝",
    "通勤",
    "出差",
    "噪音",
    "掉毛",
    "防水",
    "省空间",
    "不好用",
    "太暗",
    "总是",
    "经常",
]
PHOTO_SCENE_CUES = [
    "补光",
    "补光灯",
    "自拍",
    "拍照",
    "返图",
    "前置",
    "录像",
    "live",
    "色卡",
    "氛围感",
]
AI_PRODUCT_CUES = [
    "app",
    "App",
    "应用",
    "工具",
    "网站",
    "小程序",
    "网页",
    "脚本",
    "工作流",
    "自动化",
    "插件",
    "表单",
    "提醒",
    "记录",
    "生成器",
]
MONEY_HYPE_CUES = [
    "副业",
    "赚钱",
    "创业",
    "搞钱",
    "变现",
    "月入",
    "暴利",
    "项目",
]
DEMAND_SOURCE_CUES = [
    "求推荐",
    "有没有",
    "怎么选",
    "怎么解决",
    "怎么弄",
    "怎么设置",
    "总是",
    "经常",
    "老是",
    "困扰",
    "返图",
    "有没有同款",
]
SOLUTION_SHOWCASE_CUES = [
    "我做了",
    "我开发了",
    "我用",
    "上线了",
    "登上了",
    "排行榜",
    "appstore",
    "AppStore",
    "开源",
    "复刻",
    "从零开发",
]
TUTORIAL_CUES = [
    "教程",
    "指南",
    "手把手",
    "喂饭",
    "保姆级",
    "合集",
    "分享",
    "拆解",
]
SHOWOFF_CUES = [
    "挑战",
    "第一",
    "爆了",
    "火了",
    "太牛了",
    "限免",
]
NON_DEMAND_NOISE_CUES = [
    "女大学生",
    "男友",
    "围观",
    "食堂",
    "饭不香",
    "脱衣",
    "笑颠",
    "找茬",
    "大师",
    "整蛊",
    "搞笑",
    "名场面",
    "热梗",
    "离谱",
]
HIGH_RISK_KEYWORDS = [
    "高考",
    "志愿",
    "教育",
    "医疗",
    "股票",
    "荐股",
    "法律",
    "移民",
    "贷款",
    "资质",
]
QUALIFICATION_RULES = [
    {
        "keywords": ["高考", "志愿", "升学", "选科", "中考", "考研", "留学申请", "学科培训", "教育培训"],
        "qualification_requirement": "高敏感教育类；通常至少需要企业主体。若实质涉及校外培训、升学辅导等，往往还需办学许可/审批类资质，且有地方监管差异。",
        "individual_viability": "不建议个人直接推进",
        "qualification_level": "高门槛",
    },
    {
        "keywords": ["医疗", "问诊", "诊疗", "处方", "心理咨询", "康复"],
        "qualification_requirement": "医疗健康类；通常涉及专业执业资质、机构资质和强监管要求。",
        "individual_viability": "不建议个人直接推进",
        "qualification_level": "高门槛",
    },
    {
        "keywords": ["股票", "荐股", "基金", "理财", "投资顾问", "贷款", "保险"],
        "qualification_requirement": "金融类；通常涉及持牌经营、投顾/金融合规要求。",
        "individual_viability": "不建议个人直接推进",
        "qualification_level": "高门槛",
    },
    {
        "keywords": ["法律", "律师", "合同审查", "诉讼", "移民"],
        "qualification_requirement": "法律/移民类；通常涉及执业资格或专门许可。",
        "individual_viability": "不建议个人直接推进",
        "qualification_level": "高门槛",
    },
    {
        "keywords": ["招聘", "劳务", "兼职分发", "猎头"],
        "qualification_requirement": "招聘劳务类；可能涉及人力资源服务许可或备案，需按当地口径核验。",
        "individual_viability": "谨慎评估",
        "qualification_level": "中门槛",
    },
]
FAST_MVP_KEYWORDS = {
    "资料包": ["资料", "清单", "模板", "话术", "提示词", "教程", "笔记"],
    "服务型MVP": ["代做", "陪跑", "咨询", "交付", "定制", "整理", "代运营"],
    "自动化服务": ["自动化", "工作流", "智能体", "脚本", "AI", "批量"],
    "轻产品": ["工具", "网站", "小程序", "系统", "app", "应用"],
}
PLATFORM_REACH_WEIGHTS = {
    "xiaohongshu": 4.7,
    "douyin": 4.4,
    "bilibili": 3.1,
    "weibo": 3.4,
}
PLATFORM_DEMAND_PRIORITY = {
    "xiaohongshu": 4,
    "douyin": 3,
    "weibo": 2,
    "bilibili": 1,
}


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_dotenv_value(path: Path, key: str) -> Optional[str]:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return None


def has_tikhub_key() -> bool:
    return bool(os.environ.get("TIKHUB_API_KEY") or load_dotenv_value(CLAUDE_ENV, "TIKHUB_API_KEY"))


def resolve_tikhub_cli() -> Optional[Path]:
    for candidate in TIKHUB_CLI_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def fetch_json(url: str, headers: Dict[str, str] = None) -> Dict:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8", "ignore"))


def strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", "", text or "")
    return html.unescape(clean).strip()


def to_number(value) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().lower()
    text = text.replace(",", "")
    if text.endswith("w"):
        try:
            return int(float(text[:-1]) * 10000)
        except ValueError:
            return 0
    match = re.match(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return 0
    try:
        return int(float(match.group(1)))
    except ValueError:
        return 0


def demand_score(item: Dict) -> float:
    likes = to_number(item.get("likes"))
    replies = to_number(item.get("replies"))
    favorites = to_number(item.get("favorites"))
    shares = to_number(item.get("shares"))
    return likes * 1.0 + replies * 1.8 + favorites * 1.3 + shares * 1.2


def extract_cues(text: str) -> List[str]:
    raw = text or ""
    matches = []
    for cue in DEMAND_CUES:
        if cue in raw:
            matches.append(cue)
    return matches


def extract_query_tokens(query: str) -> List[str]:
    raw = [token.strip() for token in re.split(r"[\s/|]+", query or "") if token.strip()]
    stopwords = {"app", "App", "工具", "生成器", "小程序", "网站", "应用"}
    return [token for token in raw if token not in stopwords]


def score_query_relevance(item: Dict) -> Dict[str, Any]:
    query = item.get("query", "") or ""
    text = " ".join([item.get("title", ""), item.get("summary", ""), item.get("notes", "")])
    tokens = extract_query_tokens(query)
    if not tokens:
        return {"query_relevance": 0.5, "query_relevance_hits": 0, "query_relevance_total": 0}
    hits = sum(1 for token in tokens if token in text)
    relevance = round(hits / max(len(tokens), 1), 2)
    return {
        "query_relevance": relevance,
        "query_relevance_hits": hits,
        "query_relevance_total": len(tokens),
    }


def excerpt(text: str, limit: int = 90) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def infer_solution_type(item: Dict) -> str:
    text = " ".join([item.get("query", ""), item.get("title", ""), item.get("summary", ""), item.get("notes", "")]).lower()
    query = (item.get("query", "") or "").lower()
    product_intent_tokens = ["app", "小程序", "工具", "生成器", "网站", "应用"]
    if any(token in query for token in product_intent_tokens):
        return "轻产品"
    if any(token in text for token in ["app", "小程序", "生成器"]) and not any(token in text for token in ["资料包", "模板包"]):
        return "轻产品"
    for solution_type, keywords in FAST_MVP_KEYWORDS.items():
        if any(keyword.lower() in text for keyword in keywords):
            return solution_type
    return "内容验证页"


def estimate_build(solution_type: str, risk_level: str) -> Dict[str, str]:
    mapping = {
        "资料包": ("1-3天", "1人；内容整理 + 基础设计", "低"),
        "服务型MVP": ("2-5天", "1人；交付SOP + 收单表单", "低"),
        "自动化服务": ("3-7天", "1人；API key + 脚本 + 简单交付界面", "中"),
        "轻产品": ("7-21天", "1名开发 + 1份结构化数据/需求文档", "中"),
        "内容验证页": ("1-2天", "1人；落地页/表单 + 内容样稿", "低"),
    }
    dev_time, resources, complexity = mapping.get(solution_type, mapping["内容验证页"])
    if risk_level == "高":
        resources += " + 合规校验"
    return {
        "estimated_dev_time": dev_time,
        "estimated_resources": resources,
        "delivery_complexity": complexity,
    }


def infer_deliverable(solution_type: str, item: Dict) -> str:
    text = " ".join([item.get("query", ""), item.get("title", ""), item.get("summary", ""), item.get("notes", "")])
    scene = infer_product_scene(item)
    if solution_type == "轻产品":
        if scene == "photo":
            return "单设备补光自拍 PWA / App 原型"
        if scene == "baby":
            return "宝宝喂养记录小程序 / PWA 快捷入口"
        if scene == "reminder":
            return "照护提醒小程序 / PWA 提醒工具"
        if scene == "travel":
            return "出门防漏带清单 H5 / 小程序"
        if scene == "space":
            return "空间整理方案生成网页 / H5"
        if scene == "relationship":
            return "关系场景应答 H5 工具"
        if scene == "work":
            return "工作资料提炼网页工具 / 浏览器入口"
        if scene == "pet":
            return "宠物照护记录小程序 / PWA 快捷入口"
    if solution_type == "资料包":
        if any(token in text for token in ["提示词", "AI"]):
            return "提示词包 / SOP / 模板包 / PDF资料包"
        return "清单 / 模板 / 教程 / PDF资料包"
    if solution_type == "服务型MVP":
        return "1对1诊断 / 代做服务 / 陪跑交付 / 定制整理"
    if solution_type == "自动化服务":
        return "自动抓取脚本 / 周报看板 / 线索整理服务"
    if solution_type == "轻产品":
        if "小程序" in text:
            return "场景型小程序原型"
        return "场景型网页工具"
    return "引流内容 + 留资表单 + 私域成交页"


def infer_carrier_strategy(solution_type: str, item: Dict) -> Dict[str, Any]:
    text = " ".join([item.get("query", ""), item.get("title", ""), item.get("summary", ""), item.get("notes", "")])
    scene = infer_product_scene(item)
    base = {
        "product_carrier": "H5/网页验证页",
        "carrier_fit": "中",
        "carrier_fit_score": 3.2,
        "carrier_fit_reason": "适合先验证需求和收集反馈，但未必适合长期高频使用",
        "solution_fit": "能验证需求，但需要继续确认用户是否愿意在该入口里反复使用",
        "validation_carrier": "先用 H5/网页原型 + 内容引流验证点击、留资和复用意愿",
        "upgrade_path": "内容验证 -> H5/网页原型 -> 小程序/App 或自动化服务",
        "compliance_risk": "低到中",
        "compliance_notes": "先不碰高风险行业建议、支付闭环和敏感个人信息；正式运营再核验备案、隐私、平台类目和收款规则",
        "personal_validation_boundary": "个人可先做无支付、少数据、可删除的原型验证；一旦做长期账号、支付、订阅通知或数据存储，需要补平台与备案核验",
        "launch_requirements": "正式上线前检查 ICP/APP备案、隐私政策、用户协议、平台类目、支付/广告规则",
    }

    if solution_type in {"资料包", "服务型MVP", "自动化服务", "内容验证页"}:
        return base

    if scene == "baby":
        return {
            "product_carrier": "微信小程序 / PWA 快捷入口；不建议只做普通网页",
            "carrier_fit": "中高",
            "carrier_fit_score": 4.1,
            "carrier_fit_reason": "喂养记录是高频、碎片、手机端场景，需要一手打开、提醒和家庭共享；普通网页打开摩擦大",
            "solution_fit": "能解决，但前提是把记录压到 1-2 次点击，并支持提醒、时间轴和家庭成员同步",
            "validation_carrier": "先做 H5/PWA 快捷入口或小程序体验版，验证连续 3 天记录率、家人共享需求和提醒打开率",
            "upgrade_path": "H5/PWA 内测 -> 微信小程序 -> 留存稳定后再考虑 App",
            "compliance_risk": "中",
            "compliance_notes": "涉及婴幼儿和家庭记录，需数据最小化、隐私政策、用户可删除；避免医疗诊断、喂养处方和健康承诺",
            "personal_validation_boundary": "个人可先做本地存储/匿名内测；正式小程序、云端同步、订阅通知或收费前，必须核验备案、隐私接口、平台类目和收款规则",
            "launch_requirements": "小程序上架需备案和平台审核；处理个人信息需隐私指引；云端存储需用户协议、删除入口和数据安全方案",
        }

    if scene == "reminder":
        return {
            "product_carrier": "微信小程序 / PWA / App；不建议只做静态网页",
            "carrier_fit": "中",
            "carrier_fit_score": 3.7,
            "carrier_fit_reason": "提醒类需求依赖通知、重复打卡和低摩擦打开，普通网页很难形成习惯",
            "solution_fit": "能解决一部分计划和记录问题；如果核心价值是强提醒，需要接入订阅通知、日历或系统提醒",
            "validation_carrier": "先做可分享的提醒计划 H5，验证用户是否愿意配置提醒；再做小程序订阅通知",
            "upgrade_path": "H5 计划生成 -> 小程序提醒 -> App/硬件联动",
            "compliance_risk": "中",
            "compliance_notes": "照护记录可能涉及健康和老人信息，避免医疗建议，收集信息越少越好",
            "personal_validation_boundary": "个人可做非医疗、非诊断的计划工具验证；涉及健康管理、长期云同步或收费时需复核平台类目和隐私合规",
            "launch_requirements": "正式上架需备案、隐私政策、提醒权限说明和健康/照护类目核验",
        }

    if scene == "photo":
        return {
            "product_carrier": "PWA / App 原型；网页可验证，App 更适合长期体验",
            "carrier_fit": "高",
            "carrier_fit_score": 4.3,
            "carrier_fit_reason": "补光/自拍是即时使用场景，用户要的是打开即用；PWA 可先验证，一体化体验后续更适合 App",
            "solution_fit": "能解决，因为它把找色卡、调亮度、切拍摄流程压缩成单入口操作",
            "validation_carrier": "先做 PWA/网页原型验证使用完成率和二次打开；再根据系统能力决定是否做 App",
            "upgrade_path": "PWA 原型 -> App Store/应用市场版本 -> 付费模板或高级灯效",
            "compliance_risk": "低",
            "compliance_notes": "尽量不上传照片、不采集人脸；若调用相机/相册，需要明确权限用途和隐私说明",
            "personal_validation_boundary": "个人可先做本地处理、不上传图片的原型；上架 App 或小程序前核验权限、备案和平台审核",
            "launch_requirements": "正式上架需隐私说明、权限声明、备案/应用市场审核和素材版权检查",
        }

    if scene == "space":
        return {
            "product_carrier": "网页 / H5 最合适",
            "carrier_fit": "高",
            "carrier_fit_score": 4.4,
            "carrier_fit_reason": "空间方案生成是低频决策和结果查看场景，用户愿意上传信息后拿方案，不要求每日打开",
            "solution_fit": "能解决，核心是输入空间约束后给出可执行清单、布局建议和购买/改造步骤",
            "validation_carrier": "先做 H5 表单 + 方案生成页，验证上传意愿、收藏/转发和咨询转化",
            "upgrade_path": "H5 生成页 -> 模板库/案例库 -> 小程序收藏和复访",
            "compliance_risk": "低到中",
            "compliance_notes": "注意图片隐私、素材版权和电商导购/广告标识；不涉及特殊行业资质时门槛较低",
            "personal_validation_boundary": "个人可先做无支付 H5 和手动/半自动方案验证；导购返佣或收费时核验平台和税务/收款规则",
            "launch_requirements": "正式上线前补隐私政策、图片删除入口、素材来源说明和备案",
        }

    if scene == "travel":
        return {
            "product_carrier": "H5 / 微信小程序",
            "carrier_fit": "高",
            "carrier_fit_score": 4.0,
            "carrier_fit_reason": "清单类需求适合手机端打开、分享和复用；H5 能先验证，小程序利于收藏和复访",
            "solution_fit": "能解决，前提是按场景自动生成清单，并支持勾选、复用和分享",
            "validation_carrier": "先做 H5 清单生成器，验证收藏、分享和二次使用",
            "upgrade_path": "H5 清单 -> 小程序收藏/提醒 -> 模板市场",
            "compliance_risk": "低",
            "compliance_notes": "避免采集不必要的位置、身份和行程敏感信息；导购需注意广告标识",
            "personal_validation_boundary": "个人可先做 H5 验证；正式小程序和收款前核验备案、平台类目和隐私声明",
            "launch_requirements": "正式上线前补备案、隐私政策、用户协议和数据删除入口",
        }

    if scene == "work":
        return {
            "product_carrier": "网页工具 / 浏览器入口",
            "carrier_fit": "中高",
            "carrier_fit_score": 3.9,
            "carrier_fit_reason": "办公资料处理常发生在电脑端，网页更自然；但上传文件会带来隐私和保密顾虑",
            "solution_fit": "能解决，关键是让用户快速得到结构化摘要、清单或改写结果，并明确数据不滥用",
            "validation_carrier": "先做本地文件/粘贴文本网页工具，验证复用频次和付费意愿",
            "upgrade_path": "网页工具 -> 浏览器插件/飞书钉钉入口 -> 团队版",
            "compliance_risk": "中",
            "compliance_notes": "可能处理企业资料和个人简历，需隐私说明、数据删除、避免保留敏感内容",
            "personal_validation_boundary": "个人可先做本地处理或少量样本文本验证；企业数据、长期存储和对公服务需更严格合规",
            "launch_requirements": "正式上线前补备案、隐私政策、数据处理说明和安全边界",
        }

    if scene == "relationship":
        return {
            "product_carrier": "H5 / 小程序",
            "carrier_fit": "中高",
            "carrier_fit_score": 3.8,
            "carrier_fit_reason": "用户需要在聊天前快速生成答案，手机端入口更自然；网页可验证但复访弱",
            "solution_fit": "能解决轻量场景，核心是给出可复制的话术和不同语气版本",
            "validation_carrier": "先做 H5 生成器，验证复制率、收藏和私信反馈",
            "upgrade_path": "H5 生成器 -> 小程序快捷入口 -> 输入法/聊天插件",
            "compliance_risk": "低到中",
            "compliance_notes": "注意避免欺诈、PUA、违法营销和敏感关系操控类内容",
            "personal_validation_boundary": "个人可先做轻量生成器；若做付费或大规模分发，需补平台内容安全和隐私规则",
            "launch_requirements": "正式上线前补备案、内容安全过滤、隐私政策和平台审核",
        }

    if scene == "pet":
        return {
            "product_carrier": "微信小程序 / PWA 快捷入口",
            "carrier_fit": "中高",
            "carrier_fit_score": 4.0,
            "carrier_fit_reason": "宠物照护记录偏高频、多人协作和提醒，手机端快捷入口比普通网页更顺手",
            "solution_fit": "能解决，前提是支持快速记录、提醒、家庭/搭子共享和异常提示",
            "validation_carrier": "先做 PWA/H5 快捷入口，验证连续记录率和共享需求",
            "upgrade_path": "PWA 内测 -> 小程序 -> 会员/模板或宠物服务连接",
            "compliance_risk": "低到中",
            "compliance_notes": "避免宠物医疗诊断；若连接宠物医疗/药品服务需另行核验资质",
            "personal_validation_boundary": "个人可先做非医疗记录工具验证；正式小程序、云同步和收费前核验备案、隐私和平台类目",
            "launch_requirements": "正式上线前补备案、隐私政策、提醒权限说明和数据删除入口",
        }

    return base


def infer_deliverable_parts(solution_type: str, item: Dict) -> List[str]:
    text = " ".join([item.get("query", ""), item.get("title", ""), item.get("summary", ""), item.get("notes", "")])
    if solution_type == "资料包":
        base = [
            "1份目录页：说明用户能拿到什么",
            "1份正文资料：教程 / 清单 / SOP / 模板",
            "1份成交说明：适合谁、不适合谁、交付方式",
            "1份售卖页：封面图 + 详情文案 + FAQ",
        ]
        if "AI" in text or "提示词" in text:
            base.insert(2, "1份提示词文件：按场景分类整理")
        return base
    if solution_type == "服务型MVP":
        return [
            "1份服务说明页：服务边界、交付成果、价格",
            "1份收单表单：收集用户情况和需求",
            "1份交付SOP：你如何完成服务",
            "1份复盘模板：交付后记录常见问题",
        ]
    if solution_type == "自动化服务":
        return [
            "1份需求输入表：用户提交需求",
            "1套自动化脚本/工作流：完成核心处理",
            "1份结果输出模板：周报 / 清单 / 表格 / 看板",
            "1份演示页：说明效果、限制和使用方式",
        ]
    if solution_type == "轻产品":
        deliverable = infer_deliverable(solution_type, item)
        return [
            f"1个可访问原型：{deliverable}",
            "1套核心数据结构：字段、输入、输出",
            "1份使用说明：用户怎么上手",
            "1份收集反馈入口：表单/客服/私信",
        ]
    return [
        "1篇引流内容：说明问题和结果",
        "1个留资表单：收集用户线索",
        "1页成交说明：服务/资料介绍",
        "1套转化话术：私信或评论区回复模板",
    ]


def infer_reach_path(platform: str, solution_type: str) -> str:
    mapping = {
        "xiaohongshu": "笔记选题 -> 评论区/私信关键词 -> 留资表单/微信 -> 成交",
        "douyin": "短视频/直播切需求 -> 评论区/私信 -> 表单/私域 -> 成交",
        "bilibili": "视频/专栏 -> 置顶评论/简介链接 -> 表单/私域 -> 成交",
        "weibo": "话题内容 -> 评论/私信 -> 表单/私域 -> 成交",
    }
    base = mapping.get(platform, "内容触达 -> 留资 -> 私域成交")
    if solution_type == "自动化服务":
        return base.replace("成交", "试用/演示 -> 成交")
    if solution_type == "内容验证页":
        return base.replace("成交", "咨询/预约 -> 成交")
    return base


def infer_content_path(platform: str, solution_type: str) -> str:
    mapping = {
        "xiaohongshu": "选细分需求 -> 拆3-5篇对标笔记 -> 产出图文/封面 -> 发布 -> 看评论与私信 -> 导流成交",
        "douyin": "选细分需求 -> 拆对标短视频 -> 出脚本/口播/剪辑 -> 发布 -> 看评论与私信 -> 导流成交",
        "bilibili": "选细分需求 -> 拆对标视频/专栏 -> 出脚本/封面 -> 发布 -> 看评论/简介点击 -> 导流成交",
        "weibo": "选细分需求 -> 拆话题内容 -> 输出短帖/长图 -> 发布 -> 看评论/私信 -> 导流成交",
    }
    return mapping.get(platform, "选需求 -> 产内容 -> 发布 -> 收反馈 -> 导流成交")


def infer_platform_requirement(platform: str, solution_type: str, text: str) -> str:
    if platform == "xiaohongshu":
        if solution_type == "资料包":
            return "需重点核验小红书对虚拟资料、私信导流、店铺类目、收款方式和外链/微信导流的限制；个人号能发内容，不等于能稳定闭环成交。"
        return "需重点核验小红书对私信导流、表单留资、商业营销表述和店铺/类目限制。"
    if platform == "douyin":
        return "需重点核验抖音对私信导流、商品类目、虚拟商品、企业认证和外部跳转限制。"
    if platform == "bilibili":
        return "需重点核验B站简介链接、评论区导流、商业推广标识和站外收款方式。"
    return "需核验平台对导流、收款、外链、营销内容和类目的限制。"


def build_platform_checklist(platform: str, solution_type: str) -> List[str]:
    if platform == "xiaohongshu":
        return [
            "是否允许当前主体类型开店或经营该类目",
            "虚拟资料/数字商品是否属于允许经营范围",
            "是否允许通过私信、评论区、主页简介导流到微信/表单",
            "收款是走平台店铺、第三方店铺，还是站外收款",
            "内容是否涉及夸大宣传、收益承诺、营销违规",
        ]
    if platform == "douyin":
        return [
            "个人/个体/企业哪类主体可入驻当前商品体系",
            "虚拟商品或知识服务是否允许经营",
            "评论区/私信/直播间是否允许导流站外",
            "是否需要橱窗、抖店或达人身份",
            "商业推广和收益承诺是否触发违规",
        ]
    if platform == "bilibili":
        return [
            "当前商品是走工房、小店还是站外成交",
            "虚拟成品/数字内容是否允许发布",
            "简介链接、置顶评论导流是否受限",
            "是否需要商业合作标识",
            "收款与售后路径是否清晰",
        ]
    return [
        "主体是否符合平台经营要求",
        "类目是否允许",
        "导流是否允许",
        "收款方式是否合规",
        "营销表达是否合规",
    ]


def infer_product_scene(item: Dict) -> str:
    query = item.get("query", "") or ""
    title = item.get("title", "") or ""
    summary = item.get("summary", "") or ""
    query_text = query.lower()
    visible_text = " ".join([title, summary])
    all_text = " ".join([query, title, summary])

    scene_rules = [
        ("relationship", ["回复", "话术", "送礼", "破冰", "冷场", "高情商", "聊天", "语音厅"]),
        ("work", ["会议", "简历", "面试", "纪要", "资料整理", "资料 提炼"]),
        ("space", ["收纳", "宿舍", "租房", "布置", "厨房", "工位", "桌面", "水槽", "橱柜", "空间"]),
        ("travel", ["出差", "旅行", "忘带", "出行", "行李", "通勤", "搬家 清单"]),
        ("pet", ["猫", "狗", "宠物", "喂食", "遛狗"]),
        ("baby", ["喂奶", "喂养", "母婴", "新手爸妈", "宝宝 记录"]),
        ("reminder", ["起夜", "吃药", "提醒", "打卡", "照护", "老人"]),
    ]
    if any(token.lower() in query_text for token in PHOTO_SCENE_CUES):
        return "photo"
    for scene, tokens in scene_rules:
        if any(token in query for token in tokens):
            return scene

    if any(token in all_text for token in PHOTO_SCENE_CUES):
        return "photo"
    for scene, tokens in scene_rules:
        if scene == "baby":
            baby_tokens = ["喂奶", "喂养", "母婴", "新手爸妈", "宝宝记录", "宝宝 记录"]
            if any(token in visible_text for token in baby_tokens):
                return scene
            continue
        if any(token in visible_text for token in tokens):
            return scene
    return "general"


def infer_go_no_go(item: Dict) -> Dict[str, str]:
    platform = item.get("platform", "")
    solution_type = item.get("solution_type", "")
    qualification_level = item.get("qualification_level", "")
    text = " ".join([item.get("title", ""), item.get("summary", ""), item.get("notes", "")])
    noise = detect_non_demand_noise(item)

    if noise["non_demand_noise"]:
        return {
            "recommendation": "不建议做",
            "recommendation_reason": "标题/摘要更像娱乐、擦边或无关内容，互动不能直接证明这是产品需求。",
        }
    if qualification_level == "高门槛":
        return {
            "recommendation": "不建议做",
            "recommendation_reason": "行业或主体门槛过高，个人短期难以合法闭环。",
        }
    if platform == "xiaohongshu" and solution_type == "资料包":
        return {
            "recommendation": "待核验后再做",
            "recommendation_reason": "需求存在，但要先核验小红书对虚拟资料、店铺类目和站外导流的限制，再决定是否正式卖货。",
        }
    if any(keyword in text for keyword in ["小程序", "SaaS", "系统", "应用"]):
        return {
            "recommendation": "待核验后再做",
            "recommendation_reason": "工具类需求可做，但正式长期运营常常受主体、备案、平台规则影响。",
        }
    return {
        "recommendation": "建议先做验证版",
        "recommendation_reason": "可先用内容 + 留资 + 轻交付验证需求，不必先重投入。",
    }


def infer_product_category(item: Dict, solution_type: str) -> str:
    text = " ".join([item.get("query", ""), item.get("title", ""), item.get("summary", "")])
    scene = infer_product_scene(item)
    if any(token in text for token in ["app", "App", "应用", "小程序", "网站", "工具", "网页", "插件", "脚本"]):
        if scene == "photo":
            return "拍照补光互联网产品"
        if scene == "pet":
            return "宠物场景互联网产品"
        if scene == "space":
            return "空间优化互联网产品"
        if scene in {"baby", "reminder"}:
            return "家庭照护互联网产品"
        if scene == "relationship":
            return "关系表达互联网产品"
        if scene == "work":
            return "学习工作提效互联网产品"
        if scene == "travel":
            return "日常清单提醒互联网产品"
        return "场景型互联网产品"
    if scene == "photo":
        return "拍照补光需求"
    if scene == "pet":
        return "宠物场景需求"
    if scene == "space":
        return "居家收纳/空间优化需求"
    if scene in {"baby", "reminder"}:
        return "家庭照护需求"
    if scene == "travel":
        return "通勤便携需求"
    if scene == "relationship":
        return "关系表达需求"
    if scene == "work":
        return "学习工作提效需求"
    if any(token in text for token in ["虚拟资料", "资料售卖", "资料包", "电子资料"]):
        return "虚拟资料包"
    if any(token in text for token in ["自媒体", "涨粉", "博主", "带货"]):
        return "自媒体变现教程"
    if any(token in text for token in ["AI副业", "AI赚钱", "提示词", "自动化"]):
        return "AI副业方法包"
    if solution_type == "自动化服务":
        return "自动化代运营/工具服务"
    return "待人工细分的泛需求类目"


def explain_title(item: Dict, category: str) -> str:
    query = item.get("query", "")
    title = item.get("title", "")
    if category == "虚拟资料包":
        return f"这不是具体产品名，更像吸引点击的内容标题；它背后的可售卖类目更接近“{query or '虚拟资料'}”相关资料包。"
    if category == "AI副业方法包":
        return f"标题表达的是用户想学的结果，不是最终SKU；真正可卖的是围绕“{query or 'AI副业'}”整理出的教程/模板/SOP。"
    return f"标题更像内容包装，不是最终商品名；需要把它翻译成可售卖的具体类目，目前更接近“{category}”。"


def build_score_evidence(item: Dict) -> str:
    likes = item.get("likes", 0)
    replies = item.get("replies", 0)
    favorites = item.get("favorites", 0)
    shares = item.get("shares", 0)
    parts = [
        f"点赞 {likes}",
        f"评论/回复 {replies}",
        f"收藏 {favorites}",
        f"转发 {shares}",
    ]
    reason = []
    if replies >= 100:
        reason.append("回复量高，说明用户愿意表达具体问题")
    if favorites >= 500:
        reason.append("收藏高，说明更像工具/教程/模板需求")
    if likes >= 1000:
        reason.append("点赞高，说明题材有广泛关注")
    return "；".join(parts + reason)


def infer_maker(solution_type: str) -> str:
    if solution_type == "资料包":
        return "由 Codex 搭结构和初版，Hermes 补素材与复检，你负责最终判断和验收。"
    if solution_type == "服务型MVP":
        return "由 Codex 搭交付SOP和收单结构，Hermes 补案例与校对，你负责真实交付和验收。"
    if solution_type == "自动化服务":
        return "由 Codex 搭流程和脚本初版，Hermes 补样本和测试记录，你负责验收效果与是否上线。"
    if solution_type == "轻产品":
        return "由 Codex 搭原型和结构，Hermes 补数据与测试清单，你负责需求判断和最终验收。"
    return "由 Codex 搭验证页初版，Hermes 补素材与复检，你负责判断是否值得继续投入。"


def infer_maker_breakdown(solution_type: str, item: Dict) -> List[str]:
    deliverables = infer_deliverable_parts(solution_type, item)
    return [
        f"Codex：负责结构设计、文案骨架、脚本/页面/模板初版，先把 {deliverables[0]} 做出来",
        f"Hermes：负责搜集素材、补案例、整理目录、批量改写与复检，协助补完 {deliverables[1]}",
        "你：负责判断内容是否真懂用户、是否值得卖、是否符合你的表达风格，并做最后验收",
    ]


def extract_xiaohongshu_note_id(url: str) -> str:
    match = re.search(r"/explore/([A-Za-z0-9]+)", url or "")
    return match.group(1) if match else ""


def extract_bilibili_ids(url: str) -> Dict[str, str]:
    text = url or ""
    bv_match = re.search(r"/video/(BV[A-Za-z0-9]+)", text)
    if bv_match:
        return {"bvid": bv_match.group(1), "aid": ""}
    aid_match = re.search(r"/video/av(\d+)", text)
    if aid_match:
        return {"bvid": "", "aid": aid_match.group(1)}
    return {"bvid": "", "aid": ""}


def resolve_bilibili_bvid(aid: str) -> str:
    if not aid:
        return ""
    payload = fetch_json(f"https://api.bilibili.com/x/web-interface/view?aid={aid}", headers=BILIBILI_HEADERS)
    return str(pick(payload, ("data", "bvid"), default="") or "")


def comment_has_demand_signal(text: str) -> bool:
    raw = text or ""
    if any(cue in raw for cue in REAL_DEMAND_CUES):
        return True
    if any(cue in raw for cue in DEMAND_CUES):
        return True
    return ("?" in raw or "？" in raw) and len(raw) <= 80


def normalize_xiaohongshu_comments(raw: Any) -> List[Dict[str, Any]]:
    comments = []
    for node in walk_dicts(raw):
        text = pick(node, ("content",), default="")
        comment_id = pick(node, ("id",), default="")
        user = pick(node, ("user", "nickname"), default="")
        if not text or not comment_id:
            continue
        comments.append(
            {
                "comment_id": str(comment_id),
                "author": user,
                "content": strip_html(text),
                "likes": to_number(pick(node, ("like_count",), default=0)),
                "reply_count": to_number(pick(node, ("sub_comment_count",), default=0)),
            }
        )
    return comments


def normalize_bilibili_comments(raw: Any) -> List[Dict[str, Any]]:
    comments = []
    replies = pick(raw, ("data", "data", "replies"), default=[]) or []
    for node in replies:
        text = pick(node, ("content", "message"), default="")
        comment_id = pick(node, ("rpid_str",), ("rpid",), default="")
        user = pick(node, ("member", "uname"), default="")
        if not text or not comment_id:
            continue
        comments.append(
            {
                "comment_id": str(comment_id),
                "author": user,
                "content": strip_html(text),
                "likes": to_number(pick(node, ("like",), default=0)),
                "reply_count": to_number(pick(node, ("count",), default=0)),
            }
        )
    return comments


def summarize_comment_insights(comments: List[Dict[str, Any]]) -> Dict[str, Any]:
    demand_comments = [item for item in comments if comment_has_demand_signal(item.get("content", ""))]
    payment_comments = [
        item for item in comments
        if any(cue in item.get("content", "") for cue in PAYMENT_INTENT_CUES)
    ]
    top_comments = sorted(
        demand_comments or comments,
        key=lambda item: (item.get("reply_count", 0), item.get("likes", 0)),
        reverse=True,
    )[:5]
    cue_counter: Dict[str, int] = {}
    for item in demand_comments:
        text = item.get("content", "")
        for cue in REAL_DEMAND_CUES + DEMAND_CUES:
            if cue in text:
                cue_counter[cue] = cue_counter.get(cue, 0) + 1
    top_cues = sorted(cue_counter.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    return {
        "comment_count": len(comments),
        "demand_comment_count": len(demand_comments),
        "payment_comment_count": len(payment_comments),
        "top_comment_quotes": [item.get("content", "") for item in top_comments],
        "top_comment_authors": [item.get("author", "") for item in top_comments],
        "comment_high_freq_cues": [cue for cue, _ in top_cues],
    }


def enrich_record_with_comments(item: Dict, timeout: int = 45) -> Dict[str, Any]:
    platform = item.get("platform", "")
    enriched = dict(item)
    comments: List[Dict[str, Any]] = []
    if platform == "xiaohongshu":
        note_id = extract_xiaohongshu_note_id(item.get("url", ""))
        if note_id:
            raw = run_tikhub(
                "xiaohongshu",
                "xiaohongshu_app_v2_get_note_comments",
                {"note_id": note_id, "cursor": "", "index": 0, "pageArea": "UNFOLDED", "sort_strategy": "latest_v2"},
                timeout=timeout,
            )
            comments = normalize_xiaohongshu_comments(raw)
    elif platform == "bilibili":
        ids = extract_bilibili_ids(item.get("url", ""))
        bvid = ids.get("bvid") or resolve_bilibili_bvid(ids.get("aid", ""))
        if bvid:
            raw = run_tikhub("bilibili", "bilibili_web_fetch_video_comments", {"bv_id": bvid, "pn": 1}, timeout=timeout)
            comments = normalize_bilibili_comments(raw)
            enriched["bvid"] = bvid
    summary = summarize_comment_insights(comments) if comments else {
        "comment_count": 0,
        "demand_comment_count": 0,
        "payment_comment_count": 0,
        "top_comment_quotes": [],
        "top_comment_authors": [],
        "comment_high_freq_cues": [],
    }
    enriched["comments_sampled"] = comments[:10]
    enriched.update(summary)
    return normalize_record(enriched)


def count_keyword_hits(text: str, cues: List[str]) -> int:
    return sum(1 for cue in cues if cue in text)


def detect_non_demand_noise(item: Dict) -> Dict[str, Any]:
    title = item.get("title", "") or ""
    summary = item.get("summary", "") or ""
    notes = item.get("notes", "") or ""
    visible_text = " ".join([title, summary, notes])
    noise_hits = count_keyword_hits(visible_text, NON_DEMAND_NOISE_CUES)
    product_hits = count_keyword_hits(visible_text, AI_PRODUCT_CUES)
    demand_hits = count_keyword_hits(visible_text, REAL_DEMAND_CUES + DEMAND_SOURCE_CUES)
    tutorial_hits = count_keyword_hits(visible_text, TUTORIAL_CUES)
    payment_hits = count_keyword_hits(visible_text, PAYMENT_INTENT_CUES)
    is_noise = noise_hits > 0 and product_hits == 0 and demand_hits == 0 and tutorial_hits == 0 and payment_hits == 0
    return {
        "non_demand_noise_hits": noise_hits,
        "non_demand_noise": is_noise,
    }


def classify_content_archetype(item: Dict) -> str:
    title = item.get("title", "") or ""
    summary = item.get("summary", "") or ""
    notes = item.get("notes", "") or ""
    query = item.get("query", "") or ""
    text = " ".join([title, summary, notes])
    title_text = title.lower()
    query_text = query.lower()
    demand_comments = to_number(item.get("demand_comment_count"))

    demand_hits = count_keyword_hits(text, DEMAND_SOURCE_CUES) + (1 if "求" in title and "返图" not in title else 0)
    showcase_hits = count_keyword_hits(text, SOLUTION_SHOWCASE_CUES)
    tutorial_hits = count_keyword_hits(text, TUTORIAL_CUES)
    showoff_hits = count_keyword_hits(text, SHOWOFF_CUES)
    creator_story_hits = count_keyword_hits(text, ["独立开发者", "产品经理", "分享", "全过程", "复盘", "诞生"])
    scenario_hits = count_keyword_hits(" ".join([title, summary, query]), BLUE_OCEAN_PROBLEM_CUES)
    creator_narrative = any(token in title for token in ["分享", "全过程", "复盘", "诞生", "独立开发者", "产品经理"])
    noise = detect_non_demand_noise(item)

    if noise["non_demand_noise"]:
        return "娱乐/无关噪音"
    if demand_comments >= 3:
        demand_hits += 2
    if any(token in title_text for token in ["求", "有没有", "怎么", "如何", "能不能"]):
        demand_hits += 1
    if "返图" in text:
        demand_hits += 1

    if creator_narrative:
        return "解决方案展示"
    if creator_story_hits >= 1 and not any(token in title for token in ["求", "返图", "有没有", "怎么", "如何", "能不能"]):
        return "解决方案展示"
    if creator_story_hits >= 1 and scenario_hits <= 1 and demand_comments == 0:
        return "解决方案展示"
    if demand_hits >= showcase_hits + tutorial_hits and demand_hits >= 2 and (scenario_hits >= 1 or "app" in query_text or "小程序" in query_text):
        return "真实需求源"
    if showcase_hits >= 2 and demand_comments == 0 and showoff_hits >= 1:
        return "项目炫耀/流量包装"
    if showcase_hits >= 1:
        return "解决方案展示"
    if tutorial_hits >= 1:
        return "教程/经验分享"
    return "待判断"


def score_demand_authenticity(item: Dict) -> Dict[str, Any]:
    text = " ".join([item.get("title", ""), item.get("summary", ""), item.get("notes", "")])
    replies = to_number(item.get("replies"))
    favorites = to_number(item.get("favorites"))
    likes = to_number(item.get("likes"))
    title_bait_hits = count_keyword_hits(item.get("title", ""), TITLE_BAIT_CUES)
    real_demand_hits = count_keyword_hits(text, REAL_DEMAND_CUES) + len(item.get("cues", []))
    blue_ocean_hits = count_keyword_hits(text, BLUE_OCEAN_PROBLEM_CUES)
    money_hype_hits = count_keyword_hits(text, MONEY_HYPE_CUES)
    ai_product_hits = count_keyword_hits(text, AI_PRODUCT_CUES)
    noise = detect_non_demand_noise(item)
    archetype = classify_content_archetype(item)
    qa_bonus = 1 if "？" in text or "?" in text else 0
    reply_bonus = 1 if replies >= 50 else 0
    favorite_bonus = 1 if favorites >= 200 else 0
    like_noise = 1 if likes > 5000 and replies < 100 and real_demand_hits <= 1 else 0

    raw = 3.0 + real_demand_hits * 0.45 + qa_bonus * 0.35 + reply_bonus * 0.45 + favorite_bonus * 0.25
    raw += blue_ocean_hits * 0.18
    raw += ai_product_hits * 0.12
    raw -= title_bait_hits * 0.35
    if archetype == "真实需求源":
        raw += 0.45
    elif archetype == "解决方案展示":
        raw -= 0.15
    elif archetype == "教程/经验分享":
        raw -= 0.25
    elif archetype == "项目炫耀/流量包装":
        raw -= 0.55
    elif archetype == "娱乐/无关噪音":
        raw = min(raw - 1.4, 1.8)
    if money_hype_hits >= 2 and blue_ocean_hits == 0:
        raw -= 0.45
    raw -= noise["non_demand_noise_hits"] * 0.35
    raw -= like_noise * 0.5
    authenticity = round(clamp(raw, 1, 5), 1)

    reasons = []
    if real_demand_hits:
        reasons.append(f"真实需求线索 {real_demand_hits} 处")
    if blue_ocean_hits:
        reasons.append(f"具体问题/场景线索 {blue_ocean_hits} 处")
    if ai_product_hits:
        reasons.append(f"可产品化线索 {ai_product_hits} 处")
    if archetype:
        reasons.append(f"内容类型：{archetype}")
    if replies >= 50:
        reasons.append("回复量支持真实问题存在")
    if title_bait_hits:
        reasons.append(f"标题党信号 {title_bait_hits} 处")
    if money_hype_hits >= 2 and blue_ocean_hits == 0:
        reasons.append("泛赚钱叙事较重，可能更偏流量赛道")
    if noise["non_demand_noise"]:
        reasons.append("标题/摘要更像娱乐或无关内容，不应当作产品需求")
    if like_noise:
        reasons.append("高赞低问答，存在流量型内容风险")
    if not reasons:
        reasons.append("缺少足够的真实需求证据")

    return {
        "demand_authenticity": authenticity,
        "title_bait_hits": title_bait_hits,
        "real_demand_hits": real_demand_hits,
        "blue_ocean_hits": blue_ocean_hits,
        "money_hype_hits": money_hype_hits,
        "ai_product_hits": ai_product_hits,
        "non_demand_noise_hits": noise["non_demand_noise_hits"],
        "non_demand_noise": noise["non_demand_noise"],
        "content_archetype": archetype,
        "authenticity_reason": "；".join(reasons),
    }


def infer_qualification(text: str, solution_type: str) -> Dict[str, str]:
    for rule in QUALIFICATION_RULES:
        if any(keyword in text for keyword in rule["keywords"]):
            return {
                "qualification_requirement": rule["qualification_requirement"],
                "individual_viability": rule["individual_viability"],
                "qualification_level": rule["qualification_level"],
            }

    if any(keyword in text for keyword in ["小程序", "网站", "SaaS", "系统", "应用"]):
        return {
            "qualification_requirement": "工具/站点/小程序类需同步核验主体、备案、支付、广告宣称和平台类目要求；正式长期运营通常企业主体更稳。",
            "individual_viability": "谨慎评估",
            "qualification_level": "中门槛",
        }

    if solution_type in {"资料包", "内容验证页"}:
        return {
            "qualification_requirement": "通常无专门行业资质；若涉及收款、备案、广告宣称或特定行业内容，仍需按平台和地区规则核验。",
            "individual_viability": "个人可先验证",
            "qualification_level": "低门槛",
        }
    if solution_type == "服务型MVP":
        return {
            "qualification_requirement": "通常可先以个人服务验证；若涉及合同、发票、稳定收款或广告投放，企业主体更稳。",
            "individual_viability": "个人可先验证",
            "qualification_level": "低到中门槛",
        }
    if solution_type == "自动化服务":
        return {
            "qualification_requirement": "通常无专门行业资质；若涉及企业交付、对公收款、SaaS长期运营，企业主体更稳。",
            "individual_viability": "个人可先验证",
            "qualification_level": "低到中门槛",
        }
    return {
        "qualification_requirement": "轻产品/工具类通常需同步核验主体、备案、收款和平台规则；正式长期运营更适合企业主体。",
        "individual_viability": "谨慎评估",
        "qualification_level": "中门槛",
    }


def score_business_opportunity(item: Dict) -> Dict[str, Any]:
    score = float(item.get("score", 0))
    replies = to_number(item.get("replies"))
    favorites = to_number(item.get("favorites"))
    likes = max(to_number(item.get("likes")), 1)
    plays = max(to_number(item.get("plays")), 1)
    platform = item.get("platform", "")
    text = " ".join([item.get("title", ""), item.get("summary", ""), item.get("notes", "")])
    solution_type = infer_solution_type(item)
    risk_hits = [kw for kw in HIGH_RISK_KEYWORDS if kw in text]
    risk_level = "高" if len(risk_hits) >= 2 else "中" if risk_hits else "低"
    qualification = infer_qualification(text, solution_type)
    carrier_strategy = infer_carrier_strategy(solution_type, item)
    authenticity = score_demand_authenticity(item)
    recommendation = infer_go_no_go(
        {
            "platform": platform,
            "solution_type": solution_type,
            "qualification_level": qualification["qualification_level"],
            "title": item.get("title", ""),
            "summary": item.get("summary", ""),
            "notes": item.get("notes", ""),
        }
    )

    demand_strength = clamp(1 + math.log10(score + 1), 1, 5)
    reply_ratio = replies / max(likes + replies, 1)
    reachability = clamp(PLATFORM_REACH_WEIGHTS.get(platform, 3.0) + min(math.log10(plays + 1) / 3, 1), 1, 5)
    willingness = clamp(2.0 + min(favorites / max(replies + 1, 1), 3.0), 1, 5)

    delivery_map = {
        "资料包": 4.5,
        "服务型MVP": 4.2,
        "自动化服务": 3.6,
        "轻产品": 2.6,
        "内容验证页": 4.0,
    }
    delivery = delivery_map.get(solution_type, 3.5)
    if risk_level == "高":
        delivery = max(1.5, delivery - 1.2)
    elif risk_level == "中":
        delivery = max(1.8, delivery - 0.6)
    if solution_type == "轻产品":
        delivery = clamp(delivery * 0.72 + float(carrier_strategy["carrier_fit_score"]) * 0.28, 1, 5)

    validation_speed_map = {
        "资料包": 4.8,
        "服务型MVP": 4.2,
        "自动化服务": 3.7,
        "轻产品": 2.4,
        "内容验证页": 4.6,
    }
    validation_speed = validation_speed_map.get(solution_type, 3.8)
    if risk_level == "高":
        validation_speed = max(1.5, validation_speed - 1.2)
    elif risk_level == "中":
        validation_speed = max(2.0, validation_speed - 0.6)

    business_score = round(
        (
            demand_strength * 0.30
            + (reachability + reply_ratio) * 0.20
            + willingness * 0.20
            + delivery * 0.20
            + validation_speed * 0.10
        )
        * 20,
        1,
    )
    adjusted_business_score = round(
        business_score * (0.82 + (authenticity["demand_authenticity"] - 1) * 0.06),
        1,
    )
    build = estimate_build(solution_type, risk_level)
    return {
        "demand_strength": round(demand_strength, 1),
        "reachability": round(reachability + reply_ratio, 1),
        "willingness_to_pay": round(willingness, 1),
        "delivery_feasibility": round(delivery, 1),
        "validation_speed": round(validation_speed, 1),
        "business_score": business_score,
        "adjusted_business_score": adjusted_business_score,
        "solution_type": solution_type,
        "product_category": infer_product_category(item, solution_type),
        "title_explanation": explain_title(item, infer_product_category(item, solution_type)),
        "deliverable": infer_deliverable(solution_type, item),
        "deliverable_parts": infer_deliverable_parts(solution_type, item),
        **carrier_strategy,
        "reach_path": infer_reach_path(platform, solution_type),
        "content_path": infer_content_path(platform, solution_type),
        "maker_role": infer_maker(solution_type),
        "maker_breakdown": infer_maker_breakdown(solution_type, item),
        "platform_requirement": infer_platform_requirement(platform, solution_type, text),
        "platform_checklist": build_platform_checklist(platform, solution_type),
        "score_evidence": build_score_evidence(item),
        "target_user": infer_target_user(item),
        "trigger_scenario": infer_trigger_scenario(item),
        "current_workaround": infer_current_workaround(item),
        "most_annoying_step": infer_most_annoying_step(item),
        "payment_signal": infer_payment_signal(item),
        "lifecycle": infer_lifecycle(item),
        "primary_platform": infer_primary_platform(item),
        "content_angle": infer_content_angle(item),
        "conversion_path": infer_conversion_path(item),
        "personal_path": infer_personal_path(item),
        "mvp_definition": infer_mvp_definition(item),
        "payment_intent_strength": infer_payment_intent_strength(item),
        **authenticity,
        "risk_level": risk_level,
        "risk_keywords": risk_hits,
        "qualification_requirement": qualification["qualification_requirement"],
        "individual_viability": qualification["individual_viability"],
        "qualification_level": qualification["qualification_level"],
        "recommendation": recommendation["recommendation"],
        "recommendation_reason": recommendation["recommendation_reason"],
        **build,
    }


def normalize_record(item: Dict) -> Dict:
    merged = dict(item)
    merged["likes"] = to_number(item.get("likes"))
    merged["replies"] = to_number(item.get("replies"))
    merged["favorites"] = to_number(item.get("favorites"))
    merged["shares"] = to_number(item.get("shares"))
    merged["plays"] = to_number(item.get("plays"))
    merged["score"] = round(demand_score(merged), 2)
    merged["cues"] = extract_cues(" ".join([merged.get("title", ""), merged.get("summary", ""), merged.get("notes", "")]))
    merged.update(score_query_relevance(merged))
    merged.update(score_business_opportunity(merged))
    return merged


def pick(data: Any, *paths, default=None):
    for path in paths:
        cur = data
        ok = True
        for key in path:
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break
        if ok and cur not in (None, ""):
            return cur
    return default


def walk_dicts(node: Any) -> Iterable[Dict]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk_dicts(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk_dicts(value)


def run_tikhub(platform: str, tool_name: str, arguments: Dict, timeout: int = 45) -> Any:
    cli = resolve_tikhub_cli()
    if not cli:
        raise RuntimeError("未找到 tikhub CLI，请先安装 social-account-doctor skill。")
    if not has_tikhub_key():
        raise RuntimeError(f"缺少 TIKHUB_API_KEY。请写入 {CLAUDE_ENV} 或导出到环境变量。")
    cmd = [str(cli), platform, tool_name, "--json", json.dumps(arguments, ensure_ascii=False)]
    last_message = "未知错误"
    for attempt in range(1, 4):
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        if proc.returncode == 0:
            raw = proc.stdout.strip()
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
        last_message = proc.stderr.strip() or proc.stdout.strip() or "未知错误"
        transient = any(token in last_message for token in ["EOF occurred", "RetryError", "timed out", "network error"])
        if not transient or attempt == 3:
            break
    raise RuntimeError(f"tikhub 调用失败：{last_message}")


def build_tikhub_search_args(platform: str, query: str, page: int, page_size: int) -> Dict:
    if platform == "xiaohongshu":
        return {"keyword": query, "page": page, "sort_type": "general"}
    if platform == "douyin":
        return {
            "keyword": query,
            "cursor": max(page - 1, 0) * page_size,
            "sort_type": "0",
            "publish_time": "0",
            "filter_duration": "0",
            "content_type": "0",
        }
    if platform == "bilibili":
        return {"keyword": query, "order": "totalrank", "page": page, "page_size": page_size}
    raise ValueError(f"平台 {platform} 暂未提供默认搜索参数，请使用手工导入，或后续补充自定义工具。")


def normalize_xiaohongshu_items(raw: Any, query: str) -> List[Dict]:
    rows = []
    seen = set()
    for node in walk_dicts(raw):
        note = node.get("note_card") or node.get("noteCard") or node.get("note")
        if note:
            item = note
        elif "display_title" in node or "interact_info" in node or "note_id" in node or "liked_count" in node or "comments_count" in node:
            item = node
        else:
            continue
        note_id = pick(item, ("note_id",), ("id",), default="")
        if note_id in seen:
            continue
        seen.add(note_id)
        title = pick(item, ("display_title",), ("title",), ("note_title",), default="")
        summary = pick(item, ("desc",), ("content",), ("display_desc",), default="")
        rows.append(
            normalize_record(
                {
                    "platform": "xiaohongshu",
                    "query": query,
                    "title": title,
                    "url": f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else "",
                    "author": pick(item, ("user", "nickname"), ("author", "nickname"), ("user", "name"), default=""),
                    "summary": strip_html(summary),
                    "likes": pick(item, ("interact_info", "liked_count"), ("interactInfo", "likedCount"), ("liked_count",), default=0),
                    "replies": pick(item, ("interact_info", "comment_count"), ("interactInfo", "commentCount"), ("comment_count",), ("comments_count",), default=0),
                    "favorites": pick(item, ("interact_info", "collected_count"), ("interactInfo", "collectedCount"), ("collected_count",), default=0),
                    "shares": pick(item, ("interact_info", "share_count"), ("interactInfo", "shareCount"), ("share_count",), ("shared_count",), default=0),
                    "plays": pick(item, ("interact_info", "view_count"), ("interactInfo", "viewCount"), ("view_count",), default=0),
                    "published_at": pick(item, ("time",), ("publish_time",), ("last_update_time",), ("timestamp",), default=""),
                    "notes": "",
                    "source_type": "tikhub",
                }
            )
        )
    return rows


def normalize_douyin_items(raw: Any, query: str) -> List[Dict]:
    rows = []
    seen = set()
    for node in walk_dicts(raw):
        item = node.get("aweme_info") if isinstance(node.get("aweme_info"), dict) else node
        aweme_id = pick(item, ("aweme_id",), ("group_id",), default="")
        if not aweme_id:
            continue
        has_signal = pick(item, ("statistics", "digg_count"), ("statistics", "comment_count"), ("desc",), default=None)
        if has_signal is None:
            continue
        if aweme_id in seen:
            continue
        seen.add(aweme_id)
        rows.append(
            normalize_record(
                {
                    "platform": "douyin",
                    "query": query,
                    "title": pick(item, ("desc",), default=""),
                    "url": f"https://www.douyin.com/video/{aweme_id}",
                    "author": pick(item, ("author", "nickname"), default=""),
                    "summary": pick(item, ("desc",), default=""),
                    "likes": pick(item, ("statistics", "digg_count"), ("statistics", "like_count"), default=0),
                    "replies": pick(item, ("statistics", "comment_count"), default=0),
                    "favorites": pick(item, ("statistics", "collect_count"), default=0),
                    "shares": pick(item, ("statistics", "share_count"), default=0),
                    "plays": pick(item, ("statistics", "play_count"), default=0),
                    "published_at": pick(item, ("create_time",), default=""),
                    "notes": "",
                    "source_type": "tikhub",
                }
            )
        )
    return rows


def normalize_bilibili_items(raw: Any, query: str) -> List[Dict]:
    rows = []
    seen = set()
    for node in walk_dicts(raw):
        title = pick(node, ("title",), default="")
        bvid = pick(node, ("bvid",), default="")
        arcurl = pick(node, ("arcurl",), default="")
        if not title or (not bvid and not arcurl):
            continue
        key = bvid or arcurl
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            normalize_record(
                {
                    "platform": "bilibili",
                    "query": query,
                    "title": strip_html(title),
                    "url": arcurl or f"https://www.bilibili.com/video/{bvid}",
                    "author": pick(node, ("author",), ("owner", "name"), default=""),
                    "summary": strip_html(pick(node, ("description",), ("desc",), default="")),
                    "likes": pick(node, ("like",), ("stat", "like"), default=0),
                    "replies": pick(node, ("review",), ("reply",), ("stat", "reply"), default=0),
                    "favorites": pick(node, ("favorites",), ("favorite",), ("stat", "favorite"), default=0),
                    "shares": pick(node, ("share",), ("stat", "share"), default=0),
                    "plays": pick(node, ("play",), ("view",), ("stat", "view"), default=0),
                    "published_at": pick(node, ("pubdate",), default=""),
                    "notes": "",
                    "source_type": "tikhub",
                }
            )
        )
    return rows


def normalize_weibo_items(raw: Any, query: str) -> List[Dict]:
    rows = []
    seen = set()
    for node in walk_dicts(raw):
        item = node.get("mblog") if isinstance(node.get("mblog"), dict) else node
        post_id = pick(item, ("id",), ("mid",), default="")
        text = pick(item, ("text",), ("text_raw",), default="")
        if not post_id or not text:
            continue
        if post_id in seen:
            continue
        seen.add(post_id)
        rows.append(
            normalize_record(
                {
                    "platform": "weibo",
                    "query": query,
                    "title": excerpt(strip_html(text), 40),
                    "url": f"https://weibo.com/detail/{post_id}",
                    "author": pick(item, ("user", "screen_name"), ("user", "name"), default=""),
                    "summary": strip_html(text),
                    "likes": pick(item, ("attitudes_count",), default=0),
                    "replies": pick(item, ("comments_count",), default=0),
                    "favorites": 0,
                    "shares": pick(item, ("reposts_count",), default=0),
                    "plays": pick(item, ("reads_count",), default=0),
                    "published_at": pick(item, ("created_at",), default=""),
                    "notes": "",
                    "source_type": "tikhub",
                }
            )
        )
    return rows


def normalize_tikhub_items(platform: str, raw: Any, query: str) -> List[Dict]:
    if platform == "xiaohongshu":
        return normalize_xiaohongshu_items(raw, query)
    if platform == "douyin":
        return normalize_douyin_items(raw, query)
    if platform == "bilibili":
        return normalize_bilibili_items(raw, query)
    if platform == "weibo":
        return normalize_weibo_items(raw, query)
    return []


def bilibili_search(query: str, limit: int) -> List[Dict]:
    encoded = urllib.parse.quote(query)
    page_size = 20
    pages = max(1, math.ceil(limit / page_size))
    results = []
    headers = BILIBILI_HEADERS

    for page in range(1, pages + 1):
        url = (
            "https://api.bilibili.com/x/web-interface/search/type"
            f"?search_type=video&keyword={encoded}&page={page}"
        )
        payload = fetch_json(url, headers=headers)
        for row in payload.get("data", {}).get("result", []):
            if len(results) >= limit:
                break
            bvid = row.get("bvid")
            stat_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
            stat_payload = fetch_json(stat_url, headers=headers).get("data", {})
            stat = stat_payload.get("stat", {})
            results.append(
                normalize_record(
                    {
                        "platform": "bilibili",
                        "query": query,
                        "title": strip_html(row.get("title", "")),
                        "url": f"https://www.bilibili.com/video/{bvid}",
                        "author": row.get("author", ""),
                        "summary": strip_html(row.get("description", "")),
                        "likes": stat.get("like", 0),
                        "replies": stat.get("reply", 0),
                        "favorites": stat.get("favorite", 0),
                        "shares": stat.get("share", 0),
                        "plays": stat.get("view", 0),
                        "published_at": dt.datetime.fromtimestamp(
                            stat_payload.get("pubdate", row.get("pubdate", 0))
                        ).strftime("%Y-%m-%d")
                        if stat_payload.get("pubdate") or row.get("pubdate")
                        else "",
                        "notes": "",
                        "source_type": "auto",
                    }
                )
            )
    return results[:limit]


def write_jsonl(path: Path, records: Iterable[Dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for item in records:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> List[Dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(normalize_record(json.loads(line)))
    return rows


def read_csv(path: Path) -> List[Dict]:
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not any((value or "").strip() for value in row.values()):
                continue
            content_fields = [
                row.get("title", ""),
                row.get("summary", ""),
                row.get("url", ""),
                row.get("author", ""),
                row.get("notes", ""),
            ]
            if not any((value or "").strip() for value in content_fields):
                continue
            row["source_type"] = row.get("source_type") or "manual"
            rows.append(normalize_record(row))
    return rows


def canonical_title(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[|｜:：!！?？,，。、“”\"'`·\-—_（）()【】\[\]]+", "", text)
    return text


def dedupe_records(records: List[Dict]) -> List[Dict]:
    best_by_key: Dict[str, Dict[str, Any]] = {}
    for item in records:
        title_key = canonical_title(item.get("title", ""))
        query_key = canonical_title(item.get("query", ""))
        url = item.get("url", "") or ""
        key = "||".join(
            [
                item.get("platform", ""),
                url or title_key,
                query_key,
            ]
        )
        best = best_by_key.get(key)
        if not best or item.get("adjusted_business_score", 0) > best.get("adjusted_business_score", 0):
            best_by_key[key] = item
    return list(best_by_key.values())


def write_topic_outputs(batch_dir: Path, topic: str, records: List[Dict]) -> Dict[str, Path]:
    records = dedupe_records(records)
    merged_output = batch_dir / f"{topic}_merged.jsonl"
    write_jsonl(merged_output, records)
    report_output = batch_dir / f"{topic}_需求报告.md"
    report_output.write_text(render_report(topic, records), encoding="utf-8")
    pool_output = batch_dir / f"{topic}_机会池.md"
    pool_output.write_text(render_opportunity_pool(topic, records), encoding="utf-8")
    return {"merged": merged_output, "report": report_output, "pool": pool_output}


def write_failure_log(path: Path, topic: str, platform: str, query: str, error: str) -> None:
    append_jsonl(
        path,
        {
            "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
            "topic": topic,
            "platform": platform,
            "query": query,
            "status": "failed",
            "error": error,
        },
    )


def aggregate_cues(records: List[Dict]) -> List[tuple]:
    counter: Dict[str, int] = {}
    for item in records:
        for cue in item.get("cues", []):
            counter[cue] = counter.get(cue, 0) + 1
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))


def group_by_platform(records: List[Dict]) -> Dict[str, List[Dict]]:
    grouped: Dict[str, List[Dict]] = {}
    for item in records:
        grouped.setdefault(item.get("platform", "unknown"), []).append(item)
    return grouped


def top_records(records: List[Dict], limit: int = 10) -> List[Dict]:
    return sorted(records, key=lambda item: item.get("score", 0), reverse=True)[:limit]


def archetype_priority(item: Dict) -> int:
    mapping = {
        "真实需求源": 4,
        "解决方案展示": 3,
        "教程/经验分享": 2,
        "待判断": 1,
        "项目炫耀/流量包装": 0,
    }
    return mapping.get(item.get("content_archetype", "待判断"), 1)


def top_business(records: List[Dict], limit: int = 10) -> List[Dict]:
    return sorted(
        records,
        key=lambda item: (
            archetype_priority(item),
            PLATFORM_DEMAND_PRIORITY.get(item.get("platform", ""), 0),
            item.get("query_relevance", 0),
            item.get("demand_comment_count", 0),
            item.get("adjusted_business_score", item.get("business_score", 0)),
        ),
        reverse=True,
    )[:limit]


def build_competition_snapshot(target: Dict, records: List[Dict]) -> str:
    same_bucket = [
        item for item in records
        if item.get("platform") == target.get("platform") and item.get("query") == target.get("query")
    ]
    if not same_bucket:
        return "当前样本里缺少同平台同关键词对照，竞争度暂不明确。"
    scores = sorted((item.get("score", 0) for item in same_bucket), reverse=True)
    rank = 1 + sum(1 for item in same_bucket if item.get("score", 0) > target.get("score", 0))
    return f"同平台同关键词样本 {len(same_bucket)} 条；当前内容互动排位约第 {rank}；头部需求信号分 {scores[0]}。"


def infer_payment_intent_strength(item: Dict) -> str:
    payment_comments = to_number(item.get("payment_comment_count"))
    demand_comments = to_number(item.get("demand_comment_count"))
    favorites = to_number(item.get("favorites"))
    replies = to_number(item.get("replies"))
    if payment_comments >= 3:
        return "强：评论区已出现明确购买/价格/链接咨询"
    if payment_comments >= 1:
        return "中强：已有明确购买意图评论，值得尽快测试成交"
    if demand_comments >= 5 and favorites >= 200:
        return "中：求解和收藏都不低，适合先做试卖或留资验证"
    if replies >= 50 or favorites >= 200:
        return "中弱：关注度不低，但还缺直接购买信号"
    return "弱：目前更多是关注或讨论，支付意图证据不足"


def infer_competition_density(item: Dict, records: List[Dict]) -> str:
    same_query = [
        row for row in records
        if row.get("platform") == item.get("platform") and row.get("query") == item.get("query")
    ]
    same_category = [
        row for row in records
        if row.get("product_category") == item.get("product_category")
    ]
    head_count = sum(1 for row in same_query if row.get("score", 0) >= item.get("score", 0) * 0.7)
    if len(same_query) >= 12 and head_count >= 5:
        return "高：同关键词下高互动样本较多，内容竞争偏挤"
    if len(same_query) >= 8 or len(same_category) >= 20:
        return "中：已有一定内容供给，需要靠切口或交付差异化"
    return "低：当前样本里同类内容不算多，适合先抢验证位"


def infer_differentiation_hint(item: Dict) -> str:
    text = " ".join([item.get("query", ""), item.get("title", ""), item.get("summary", "")])
    if any(token in text for token in PHOTO_SCENE_CUES):
        return "不要做泛拍照工具，优先做“少一步完成”的具体场景版本"
    if any(token in text for token in ["收纳", "方案", "布置"]):
        return "不要做泛收纳内容，优先做输入场景后直接出方案的结果型工具"
    if any(token in text for token in ["记录", "提醒", "清单"]):
        return "不要做泛打卡工具，优先切“哪类人 + 哪个时刻最容易断”"
    if any(token in text for token in ["回复", "送礼", "话术"]):
        return "不要做泛话术库，优先切即时场景和具体关系角色"
    return "优先从更窄的人群、时刻或动作切入，避免做泛工具"


def build_mini_rpd(item: Dict) -> List[str]:
    return [
        f"目标用户：被“{item.get('query', '')}”吸引、希望快速拿到现成方法的人群",
        f"核心交付：{item.get('deliverable', '')}",
        f"制作内容：封面1版 + 销售页文案1版 + 资料正文/模板 + 引流笔记3-5篇",
        f"验证动作：先发内容测试评论/私信，再决定是否正式包装成交",
        f"复检重点：用户是否问价格、问目录、问交付方式、问是否真实有效",
    ]


def infer_target_user(item: Dict) -> str:
    scene = infer_product_scene(item)
    if scene == "photo":
        return "在拍照、自拍、氛围感表达上有即时需求的人"
    if scene in {"baby", "reminder"}:
        return "家庭照护者 / 新手父母 / 需要稳定提醒的人"
    if scene == "space":
        return "空间有限、希望快速得到方案的人"
    if scene == "travel":
        return "经常出门、容易遗漏步骤的人"
    if scene == "relationship":
        return "需要快速组织表达、降低社交压力的人"
    if scene == "work":
        return "需要提升工作学习效率的人"
    if scene == "pet":
        return "新手宠物主人 / 高频照护用户"
    return "有明确小麻烦、希望更省事完成任务的人"


def infer_trigger_scenario(item: Dict) -> str:
    scene = infer_product_scene(item)
    if scene in {"baby", "reminder"}:
        return "需要按时记录或提醒，但日常容易中断、遗漏"
    if scene == "space":
        return "遇到空间整理或重新布置时，不知道先做哪一步"
    if scene == "travel":
        return "出门前需要准备很多东西，但经常漏项"
    if scene == "relationship":
        return "社交表达需要快速给出合适内容，但当下想不出来"
    if scene == "work":
        return "信息量大、整理耗时，容易拖延或返工"
    if scene == "photo":
        return "想快速拍出更好效果，但现有方法步骤多、切换麻烦"
    return "用户有明确任务要完成，但现有流程不顺手"


def infer_current_workaround(item: Dict) -> str:
    scene = infer_product_scene(item)
    if scene in {"baby", "reminder"}:
        return "手写、备忘录、闹钟、家庭群消息等零散方式拼凑解决"
    if scene == "space":
        return "看多个攻略、自己列步骤、反复试错"
    if scene == "travel":
        return "靠脑子记、翻旧备忘录、临时搜索模板"
    if scene == "relationship":
        return "临时搜范例、问朋友、自己硬想"
    if scene == "work":
        return "手动整理文档、复制粘贴、多轮改写"
    if scene == "photo":
        return "切换多个工具、手动找素材或靠两部设备完成"
    return "用户靠手工、多个工具切换或临时搜索来完成"


def infer_most_annoying_step(item: Dict) -> str:
    scene = infer_product_scene(item)
    if scene in {"baby", "reminder", "travel"}:
        return "信息要重复输入，且很难稳定坚持"
    if scene == "space":
        return "不知道先做哪一步，方案选择成本高"
    if scene == "relationship":
        return "当下没有现成答案，决策和表达压力大"
    if scene == "work":
        return "从原始信息到可用结果之间，整理和提炼太耗时"
    if scene == "photo":
        return "为了一个效果要切换多个动作或设备，操作链路太长"
    return "用户需要自己拼流程，缺少一步到位的工具"


def infer_payment_signal(item: Dict) -> str:
    comment_hits = item.get("comment_high_freq_cues", []) or []
    demand_comment_count = to_number(item.get("demand_comment_count"))
    payment_comment_count = to_number(item.get("payment_comment_count"))
    favorites = to_number(item.get("favorites"))
    replies = to_number(item.get("replies"))
    if payment_comment_count >= 3:
        return "评论区已出现多条购买/价格/链接咨询，支付意图很强"
    if payment_comment_count >= 1:
        return "评论区已经出现直接购买信号，值得尽快测试成交"
    if any(cue in comment_hits for cue in ["怎么做", "求模板", "求资料", "怎么卖", "能不能做"]):
        return "评论区已经出现强求解信号，具备较强转化可能"
    if demand_comment_count >= 5:
        return "评论区真实提问较多，适合先做留资或试用验证"
    if favorites >= 500 and replies >= 50:
        return "收藏和回复都高，说明用户不只是围观，更可能愿意拿现成方案"
    if favorites >= 200:
        return "收藏明显，说明用户有复用或稍后获取的意愿"
    return "当前更多是需求关注信号，付费意愿还需要进一步验证"


def infer_lifecycle(item: Dict) -> str:
    text = " ".join([item.get("query", ""), item.get("title", ""), item.get("summary", "")])
    if any(token in text for token in ["节日", "情人节", "生日", "毕业季", "开学"]):
        return "季节性 / 节点波峰"
    if any(token in text for token in ["喂奶", "吃药", "起夜", "记录", "会议", "简历", "清单", "收纳"]):
        return "长期高频 / 可复用"
    if any(token in text for token in PHOTO_SCENE_CUES):
        return "长期存在，但更依赖内容驱动爆发"
    return "待观察"


def infer_primary_platform(item: Dict) -> str:
    text = " ".join([item.get("query", ""), item.get("title", ""), item.get("summary", "")])
    if any(token in text for token in ["回复", "送礼", "清单", "收纳", "拍照", "氛围感"]):
        return "小红书优先：适合问题展示、对比图和评论区收口"
    if any(token in text for token in ["会议", "面试", "简历", "工作流", "教程", "复盘"]):
        return "B站优先：适合解释链路、演示效果和建立信任"
    return "小红书优先，再用B站补解释型内容"


def infer_content_angle(item: Dict) -> str:
    text = " ".join([item.get("query", ""), item.get("title", ""), item.get("summary", "")])
    if any(token in text for token in PHOTO_SCENE_CUES):
        return "效果对比切口：前后差异 / 少一步完成 / 单设备替代旧办法"
    if any(token in text for token in ["记录", "提醒", "清单"]):
        return "麻烦链路切口：总忘 / 总漏 / 总断，展示如何一键补齐"
    if any(token in text for token in ["收纳", "方案", "布置"]):
        return "结果切口：输入场景 -> 自动给方案，减少试错"
    if any(token in text for token in ["回复", "话术", "送礼"]):
        return "即时救场切口：不知道怎么回 / 怎么选时，立刻给出可用答案"
    return "问题切口：原来怎么做太麻烦，现在一步完成"


def infer_conversion_path(item: Dict) -> str:
    solution_type = item.get("solution_type", "")
    platform = item.get("platform", "")
    if solution_type == "资料包":
        return f"{platform}内容验证 -> 评论/私信收需求 -> 目录页/PDF试卖 -> 再决定是否店铺化"
    if solution_type == "服务型MVP":
        return f"{platform}内容引流 -> 表单收单 -> 手工交付 -> 复盘高频需求 -> 再产品化"
    if solution_type == "自动化服务":
        return f"{platform}内容引流 -> 演示页/试用 -> 收第一批种子用户 -> 再补自动化闭环"
    if solution_type == "轻产品":
        return f"{platform}内容验证 -> 网页MVP/内测链接 -> 收反馈和留资 -> 再决定正式上线"
    return f"{platform}内容试探 -> 评论/私信问法验证 -> 留资页 -> 再决定做资料、服务还是工具"


def infer_personal_path(item: Dict) -> List[str]:
    solution_type = item.get("solution_type", "")
    platform = item.get("platform", "")
    if solution_type == "资料包":
        return [
            "最轻验证：先发内容 + 私信/表单收需求，不急着开店",
            "第二阶段：整理成 PDF/模板包，测试用户是否愿意为现成结果付费",
            "商业化路径：若平台规则允许，再考虑店铺化或站外长期成交",
        ]
    if solution_type == "服务型MVP":
        return [
            "最轻验证：先接 1-3 单手工服务，确认用户真愿意付费",
            "第二阶段：把交付过程整理成 SOP，减少重复劳动",
            "商业化路径：高频后再决定是否做工具化或企业化承接",
        ]
    if solution_type == "自动化服务":
        return [
            "最轻验证：先做演示版，不急着正式上线",
            "第二阶段：半手工半自动交付，验证真实留存和复购",
            "商业化路径：确认有效后再补账号体系、支付、正式产品化",
        ]
    if solution_type == "轻产品":
        return [
            "最轻验证：先做网页原型或内测版，通过内容收第一批用户",
            "第二阶段：先不碰重平台入驻，优先验证留存和复用频率",
            "商业化路径：确认长期价值后，再考虑小程序/App/企业主体",
        ]
    return [
        "最轻验证：先发内容看评论和私信，不急着开发重产品",
        "第二阶段：根据反馈决定做资料、服务还是工具",
        "商业化路径：只在需求稳定后再增加主体、备案或平台投入",
    ]


def infer_mvp_definition(item: Dict) -> List[str]:
    deliverable = item.get("deliverable") or infer_deliverable(item.get("solution_type", "内容验证页"), item)
    return [
        f"最小用户：{infer_target_user(item)}",
        f"最小场景：{infer_trigger_scenario(item)}",
        f"最小功能：围绕“{infer_most_annoying_step(item)}”只解决一个关键动作",
        f"最小交付：{deliverable}",
        f"最小验证动作：{infer_conversion_path(item)}",
    ]


def infer_product_name(item: Dict) -> str:
    scene = infer_product_scene(item)
    if scene == "photo":
        return "单设备补光自拍助手"
    if scene == "baby":
        return "新手喂养记录器"
    if scene == "reminder":
        return "照护提醒管家"
    if scene == "travel":
        return "出门防忘清单"
    if scene == "space":
        return "空间整理方案生成器"
    if scene == "relationship":
        return "关系场景应答助手"
    if scene == "work":
        return "工作资料提炼助手"
    if scene == "pet":
        return "宠物照护记录助手"
    return "场景任务小助手"


def infer_product_value(item: Dict) -> str:
    scene = infer_product_scene(item)
    if scene == "photo":
        return "把原来要切换多个工具或设备的拍照补光流程压成一次完成。"
    if scene == "baby":
        return "把喂养、睡眠、换尿布等零散记录合成一个连续可提醒的流程。"
    if scene == "reminder":
        return "把容易断掉的提醒动作变成稳定、低负担的照护节奏。"
    if scene == "travel":
        return "按出行场景自动生成携带清单，减少临出门漏带。"
    if scene == "space":
        return "输入空间条件后直接给整理或布置方案，减少试错。"
    if scene == "relationship":
        return "在具体关系场景里，立刻给出能直接用的回复或选择建议。"
    if scene == "work":
        return "把原始信息快速提炼成可直接使用的工作结果。"
    if scene == "pet":
        return "把宠物照护记录和提醒收进一个顺手的小工具里。"
    return "把原本分散的手工步骤压缩成一个可直接使用的小产品。"


def infer_core_features(item: Dict) -> List[str]:
    scene = infer_product_scene(item)
    if scene == "photo":
        return ["补光/自拍一体化", "场景预设", "一键保存常用设置"]
    if scene == "baby":
        return ["一键记录", "自动下一次提醒", "时间线回看"]
    if scene == "reminder":
        return ["提醒计划", "完成反馈", "连续记录"]
    if scene == "travel":
        return ["按场景生成清单", "临出门二次提醒", "历史模板复用"]
    if scene == "space":
        return ["输入空间条件", "自动给方案", "方案调整与保存"]
    if scene == "relationship":
        return ["输入关系场景", "生成可用答案", "风格切换"]
    if scene == "work":
        return ["导入原始内容", "自动提炼结果", "导出可用版本"]
    if scene == "pet":
        return ["照护记录", "提醒计划", "日常状态回看"]
    return ["场景输入", "自动生成结果", "结果保存/复用"]


def infer_solution_mechanism(item: Dict) -> str:
    scene = infer_product_scene(item)
    if scene == "baby":
        return "用户每次只记录一次喂养动作，系统自动串起时间轴并推算下一次提醒。"
    if scene == "reminder":
        return "把提醒拆成固定节奏，用户只要确认完成，系统自动延续下一次安排。"
    if scene == "travel":
        return "用户输入出行情境，系统自动生成携带清单并在出门前二次提醒。"
    if scene == "space":
        return "用户输入空间条件和目标，系统直接给出可执行整理方案。"
    if scene == "photo":
        return "把补光、拍照、预设切换合成一条链路，减少设备和动作切换。"
    if scene == "relationship":
        return "输入关系和场景，系统直接生成当下可用的回答或选择。"
    if scene == "work":
        return "导入原始材料后，系统自动提炼成能直接使用的输出。"
    if scene == "pet":
        return "每次照护只记一次，系统自动整理日常状态并给出下一步提醒。"
    return "把原本分散的手工步骤合成一个连续动作，让用户少做判断和重复输入。"


def infer_use_flow(item: Dict) -> str:
    scene = infer_product_scene(item)
    if scene == "baby":
        return "选宝宝 -> 点喂养类型 -> 输时长/奶量 -> 自动生成下一次提醒 -> 家人共享时间轴。"
    if scene == "reminder":
        return "设提醒计划 -> 到点确认完成 -> 系统自动续下一次 -> 回看连续记录。"
    if scene == "travel":
        return "选出行类型 -> 自动生成清单 -> 勾选补充 -> 出门前二次提醒。"
    if scene == "space":
        return "输入空间大小/目标 -> 生成方案 -> 选可执行版本 -> 保存和微调。"
    if scene == "photo":
        return "选场景预设 -> 开始补光/自拍 -> 保存常用配置 -> 下次一键复用。"
    if scene == "relationship":
        return "输入关系和上下文 -> 生成候选答案 -> 切换风格 -> 复制直接用。"
    if scene == "work":
        return "导入材料 -> 选目标输出 -> 自动提炼 -> 导出可用版本。"
    if scene == "pet":
        return "点一次照护动作 -> 自动记入时间轴 -> 到点提醒下一步 -> 回看状态变化。"
    return "输入场景 -> 系统自动处理 -> 输出结果 -> 保存复用。"


def infer_switch_reason(item: Dict) -> str:
    scene = infer_product_scene(item)
    if scene == "baby":
        return "不用翻聊天记录和备忘录，也不用自己算下次时间。"
    if scene == "reminder":
        return "不用重复设闹钟，提醒和完成记录在一处闭环。"
    if scene == "travel":
        return "不用每次从头想和手写，场景一选就能直接出结果。"
    if scene == "space":
        return "不用反复搜攻略和试错，先拿到一版可执行方案。"
    if scene == "photo":
        return "不用切换多个工具或设备，一个入口完成原本多步操作。"
    if scene == "relationship":
        return "不用临时搜索和硬想，马上拿到能直接用的答案。"
    if scene == "work":
        return "不用手动整理和改写，节省最耗时的中间处理环节。"
    if scene == "pet":
        return "不用分散记录，照护动作和后续提醒天然连在一起。"
    return "它把原来分散、重复、靠记忆的步骤合成了一个可直接完成的流程。"


def infer_ai_product_form(item: Dict) -> str:
    category = item.get("product_category", "")
    text = " ".join([item.get("title", ""), item.get("summary", ""), item.get("query", "")])
    if "互联网产品" in category or any(token in text for token in ["app", "App", "小程序", "网站", "工具", "脚本"]):
        if any(token in text for token in ["提醒", "起夜", "防摔", "记录"]):
            return "提醒/记录类轻应用"
        if any(token in text for token in ["补光灯", "夜灯", "拍照", "识别"]):
            return "场景增强类小 App"
        if any(token in text for token in ["收纳", "整理", "方案", "搭配"]):
            return "方案生成/推荐类工具"
        return "场景型轻应用 / AI工具"
    return "非互联网产品优先方向，需二次筛选"


def top_comment_lines(item: Dict) -> List[str]:
    quotes = item.get("top_comment_quotes", []) or []
    authors = item.get("top_comment_authors", []) or []
    lines = []
    for idx, quote in enumerate(quotes[:3]):
        author = authors[idx] if idx < len(authors) else ""
        prefix = f"{author}：" if author else ""
        lines.append(prefix + quote)
    return lines


def build_compact_opportunity_lines(item: Dict, records: List[Dict]) -> List[str]:
    competition_density = infer_competition_density(item, records)
    product_name = infer_product_name(item)
    product_value = infer_product_value(item)
    features = " / ".join(infer_core_features(item))
    solution = infer_solution_mechanism(item)
    flow = infer_use_flow(item)
    switch_reason = infer_switch_reason(item)
    return [
        f"- 产品：**{product_name}**｜{product_value}",
        f"- 交付：{excerpt(item.get('deliverable', ''), 24)}｜载体：{excerpt(item.get('product_carrier', ''), 28)}｜适配：{item.get('carrier_fit', '')}",
        f"- 能否解决：{excerpt(item.get('solution_fit', ''), 54)}｜功能：{excerpt(features, 30)}",
        f"- 链路：{excerpt(flow, 44)}｜验证：{excerpt(item.get('validation_carrier', ''), 42)}",
        f"- 合规：{item.get('compliance_risk', '')}｜{excerpt(item.get('compliance_notes', ''), 48)}｜个人边界：{excerpt(item.get('personal_validation_boundary', ''), 36)}",
        f"- 判断：**{item.get('recommendation', '')}**｜分数 {item.get('adjusted_business_score', 0)}｜{item.get('qualification_level', '')}｜竞争 {competition_density.split('：', 1)[0]}｜证据 赞{item.get('likes', 0)}/评{item.get('replies', 0)}/藏{item.get('favorites', 0)}",
    ]


def is_kitten_style_opportunity(item: Dict) -> bool:
    archetype = item.get("content_archetype", "待判断")
    category = item.get("product_category", "")
    product_form = infer_ai_product_form(item)
    qualification_level = item.get("qualification_level", "")
    scenario_hits = to_number(item.get("blue_ocean_hits"))
    product_hits = to_number(item.get("ai_product_hits"))
    replies = to_number(item.get("replies"))
    text = " ".join([item.get("title", ""), item.get("summary", ""), item.get("query", "")])
    photo_hits = count_keyword_hits(text, PHOTO_SCENE_CUES)

    if "互联网产品" not in category:
        return False
    if item.get("query_relevance", 0) < 0.34:
        return False
    if qualification_level == "高门槛":
        return False
    if archetype not in {"真实需求源", "解决方案展示"}:
        return False
    if scenario_hits < 1:
        return False
    if photo_hits < 2 and scenario_hits < 2:
        return False
    if product_hits < 1 and "app" not in text.lower() and "小程序" not in text:
        return False
    if replies < 10 and archetype != "解决方案展示":
        return False
    if product_form == "非互联网产品优先方向，需二次筛选":
        return False
    return True


def render_opportunity_pool(topic: str, records: List[Dict]) -> str:
    today = dt.date.today().isoformat()
    pool = [
        item for item in top_business(records, 30)
        if is_kitten_style_opportunity(item)
    ]
    lines = [
        "---",
        "type: note",
        f"date: {today}",
        "tags: [机会池, AI产品, 蓝海需求, 场景产品]",
        "status: 活跃",
        "confidence: medium",
        "---",
        "",
        f"# {topic} - 小猫补光灯型机会池",
        "",
        "## 筛选标准",
        "",
        "- 有具体场景，不是泛创业叙事",
        "- 已经存在用户行为或解决方案展示",
        "- 当前链路麻烦，能被 AI 快速做成轻量互联网产品",
        "- 尽量避开高资质、高主体门槛方向",
        "",
        f"## 候选数",
        "",
        f"- 共 {len(pool)} 条",
        "",
    ]
    if not pool:
        lines.extend(["- 暂无符合条件的机会", ""])
        return "\n".join(lines)

    lines.extend(["## 候选机会", ""])
    for idx, item in enumerate(pool[:12], start=1):
        lines.extend(
            [
                f"### {idx}. {item.get('title', '')}",
                f"- 平台：`{item.get('platform', '')}` | 关键词：`{item.get('query', '')}`",
                f"- 内容类型：`{item.get('content_archetype', '待判断')}` | 更像哪类 AI 产品：`{infer_ai_product_form(item)}`",
                f"- 校正后好生意分：**{item.get('adjusted_business_score', 0)}** | 真实需求度：**{item.get('demand_authenticity', 0)} / 5**",
                f"- 为什么入池：{item.get('authenticity_reason', '')}",
                f"- 建议解法：`{item.get('solution_type', '')}` | 实际交付物：{item.get('deliverable', '')}",
                f"- 载体适配：{item.get('product_carrier', '')} | 匹配度：{item.get('carrier_fit', '')} | {item.get('carrier_fit_reason', '')}",
                f"- 交付物能否解决：{item.get('solution_fit', '')}",
                f"- 触达链路：{item.get('reach_path', '')}",
                f"- 合规/主体：{item.get('qualification_requirement', '')} | 载体风险：{item.get('compliance_risk', '')}，{item.get('compliance_notes', '')}",
                f"- 个人验证边界：{item.get('personal_validation_boundary', '')}",
                f"- 预计时长：{item.get('estimated_dev_time', '')} | 预计资源：{item.get('estimated_resources', '')}",
                f"- 需求证据：{excerpt(item.get('summary', '') or item.get('title', ''))}",
                "",
            ]
        )
    return "\n".join(lines)


def render_report(topic: str, records: List[Dict]) -> str:
    today = dt.date.today().isoformat()
    records = dedupe_records(sorted(records, key=lambda item: item.get("score", 0), reverse=True))
    cues = aggregate_cues(records)
    grouped = group_by_platform(records)
    archetype_counts: Dict[str, int] = {}
    for item in records:
        archetype = item.get("content_archetype", "待判断")
        archetype_counts[archetype] = archetype_counts.get(archetype, 0) + 1
    recommended = [item for item in top_business(records, 20) if item.get("recommendation") == "建议先做验证版"]
    verify_first = [item for item in top_business(records, 20) if item.get("recommendation") == "待核验后再做"]
    avoid_items = [item for item in top_business(records, 20) if item.get("recommendation") == "不建议做"]

    lines = [
        "---",
        "type: note",
        f"date: {today}",
        "tags: [需求挖掘, 副业, 公域平台, 内容分析]",
        "status: 活跃",
        "confidence: medium",
        "---",
        "",
        f"# {topic} - 公域需求报告",
        "",
        "## 总览",
        "",
        f"- 样本总数：{len(records)}",
        f"- 覆盖平台：{', '.join(sorted(grouped.keys())) if grouped else '无'}",
        f"- 最高需求信号分：{records[0]['score'] if records else 0}",
        f"- 最高好生意分：{max((item.get('business_score', 0) for item in records), default=0)}",
        "",
        "## 平台分布",
        "",
    ]

    for platform, items in sorted(grouped.items()):
        avg_score = round(sum(item["score"] for item in items) / len(items), 2)
        lines.append(f"- `{platform}`：{len(items)} 条，平均需求信号分 {avg_score}")

    lines.extend(["", "## 决策分组", ""])
    lines.append(f"- 建议先做验证版：{len(recommended)} 条")
    lines.append(f"- 待核验后再做：{len(verify_first)} 条")
    lines.append(f"- 不建议做：{len(avoid_items)} 条")
    lines.append("- 候选机会卡默认按“校正后好生意分”排序，已对标题党和低真实需求信号做降权。")
    lines.append("- 如果某条样本已补评论，会额外显示评论证据和高频评论线索。")
    lines.append("- 现在会额外识别“具体问题/场景线索”和“泛赚钱叙事”，帮助把蓝海需求和同质化流量赛道分开。")
    lines.append("- 现在会把样本拆成“真实需求源 / 解决方案展示 / 教程经验 / 项目炫耀”，避免把内容热度误判成用户需求。")
    lines.append("- 现在会单独判断“交付载体是否匹配用户习惯”，避免把真需求误做成用户不愿意用的网页/工具。")
    if archetype_counts:
        lines.append(
            "- 内容类型分布："
            + "；".join(f"{key} {value} 条" for key, value in sorted(archetype_counts.items(), key=lambda kv: (-kv[1], kv[0])))
        )
    lines.extend(["", "## 个人主体白名单机会", ""])
    if recommended:
        for item in recommended[:5]:
            lines.append(f"- `{item.get('product_category', '')}`｜{item.get('title', '')}｜{item.get('recommendation_reason', '')}")
    else:
        lines.append("- 暂无")

    lines.extend(["", "## 待核验机会", ""])
    if verify_first:
        for item in verify_first[:5]:
            lines.append(f"- `{item.get('product_category', '')}`｜{item.get('title', '')}｜{item.get('recommendation_reason', '')}")
    else:
        lines.append("- 暂无")

    lines.extend(["", "## 禁止进入机会", ""])
    if avoid_items:
        for item in avoid_items[:5]:
            lines.append(f"- `{item.get('product_category', '')}`｜{item.get('title', '')}｜{item.get('recommendation_reason', '')}")
    else:
        lines.append("- 暂无")

    lines.extend(["", "## 候选机会卡", ""])

    candidate_cards = [
        item for item in top_business(records, 30)
        if item.get("recommendation") != "不建议做"
    ][:8]
    if not candidate_cards:
        candidate_cards = top_business(records, 8)

    for idx, item in enumerate(candidate_cards, start=1):
        compact_lines = build_compact_opportunity_lines(item, records)
        lines.extend(
            [
                f"### {idx}. {item.get('title', '无标题')}",
                f"- 平台：`{item.get('platform', '')}` | 关键词：`{item.get('query', '')}`",
            ]
        )
        lines.extend(compact_lines)
        lines.append("")

    lines.extend(["## 高信号内容", ""])

    for idx, item in enumerate(top_records(records, 12), start=1):
        lines.extend(
            [
                f"### {idx}. {item.get('title', '无标题')}",
                f"- 平台：`{item.get('platform', '')}` | 关键词：`{item.get('query', '')}`",
                f"- 互动：点赞 {item.get('likes', 0)} / 回复 {item.get('replies', 0)} / 收藏 {item.get('favorites', 0)} / 转发 {item.get('shares', 0)}",
                f"- 需求信号分：**{item.get('score', 0)}** | 校正后好生意分：**{item.get('adjusted_business_score', 0)}**",
                f"- 作者：{item.get('author', '')}",
                f"- 链接：{item.get('url', '')}",
                f"- 类目判断：{item.get('product_category', '')}",
                f"- 关键词相关性：{item.get('query_relevance_hits', 0)}/{item.get('query_relevance_total', 0)} 命中 | 分数 {item.get('query_relevance', 0)}",
                f"- 内容类型：{item.get('content_archetype', '待判断')}",
                f"- 真实需求度：{item.get('demand_authenticity', 0)} / 5 | {item.get('authenticity_reason', '')}",
                f"- 蓝海信号：具体问题/场景 {item.get('blue_ocean_hits', 0)} 处 | 可产品化线索 {item.get('ai_product_hits', 0)} 处 | 泛赚钱叙事 {item.get('money_hype_hits', 0)} 处",
                f"- 评分依据：{item.get('score_evidence', '')}",
                f"- 推荐解法：{item.get('solution_type', '')} | 实际交付物：{item.get('deliverable', '')}",
                f"- 载体适配：{item.get('product_carrier', '')} | 匹配度：{item.get('carrier_fit', '')} | {item.get('carrier_fit_reason', '')}",
                f"- 交付物能否解决需求：{item.get('solution_fit', '')}",
                f"- 验证载体与升级路径：{item.get('validation_carrier', '')} -> {item.get('upgrade_path', '')}",
                f"- 首发平台建议：{item.get('primary_platform', '')} | 内容切口：{item.get('content_angle', '')}",
                f"- 支付意图强度：{item.get('payment_intent_strength', '')} | 竞争密度：{infer_competition_density(item, records)}",
                f"- 平台要求：{item.get('platform_requirement', '')}",
                f"- 行业/主体要求：{item.get('qualification_requirement', '')}",
                f"- 正式上线合规：{item.get('compliance_risk', '')} | {item.get('compliance_notes', '')} | {item.get('launch_requirements', '')}",
                f"- 个人验证边界：{item.get('personal_validation_boundary', '')}",
                f"- 个人可行性：{item.get('individual_viability', '')} | 开发时长：{item.get('estimated_dev_time', '')}",
                f"- 需求原子卡：用户 {item.get('target_user', '')}；场景 {item.get('trigger_scenario', '')}；现有土办法 {item.get('current_workaround', '')}",
                f"- MVP定义：{'; '.join(item.get('mvp_definition', [])[:3])}",
                f"- 评论证据：已抓取 {item.get('comment_count', 0)} 条评论，疑似真实需求评论 {item.get('demand_comment_count', 0)} 条，明确购买意图评论 {item.get('payment_comment_count', 0)} 条",
                f"- 需求证据：{excerpt(item.get('summary', '') or item.get('notes', '') or item.get('title', ''))}",
                "",
            ]
        )

    lines.extend(["## 高频需求线索", ""])
    if cues:
        for cue, count in cues[:12]:
            lines.append(f"- `{cue}`：出现 {count} 次")
    else:
        lines.append("- 暂未识别到高频线索")

    lines.extend(["", "## 观察结论", ""])
    if records:
        lines.append("- 高互动内容优先反映的是用户愿意停留和反馈的问题，而不只是作者在输出什么。")
        lines.append("- 如果回复数明显高于点赞占比，通常说明内容更像问题入口，值得重点看评论区原话。")
        lines.append("- 如果收藏数高，说明它更接近工具、清单、模板、方法论，适合转成资料或服务。")
        lines.append("- 这份报告现在不只给分，还会明确需求原子卡、MVP定义、成交路径和所需资质，避免把不可做或不好卖的方向误判成机会。")
    else:
        lines.append("- 当前没有样本，无法形成结论。")

    lines.extend(["", "## 下一步", ""])
    lines.append("- 对前 10 条高信号内容逐条补充评论区原话，再做二次需求归类。")
    lines.append("- 按同一主题继续补 2-3 个平台样本，避免单平台错觉。")
    lines.append("- 从高信号内容里提炼 3 个可验证的交付方向。")
    lines.append("")
    return "\n".join(lines)


def cmd_template(args: argparse.Namespace) -> int:
    ensure_dirs()
    if DEFAULT_TEMPLATE.exists() and not args.force:
        print(f"模板已存在：{DEFAULT_TEMPLATE}")
        return 0
    DEFAULT_TEMPLATE.write_text(
        "platform,query,title,url,author,summary,likes,replies,favorites,shares,plays,published_at,notes\n",
        encoding="utf-8",
    )
    print(f"已生成模板：{DEFAULT_TEMPLATE}")
    return 0


def cmd_fetch_bilibili(args: argparse.Namespace) -> int:
    ensure_dirs()
    records = bilibili_search(args.query, args.limit)
    output = Path(args.output) if args.output else OUTPUT_DIR / f"bilibili_{args.query}.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(output, records)
    print(f"已写入 {len(records)} 条：{output}")
    return 0


def cmd_fetch_tikhub(args: argparse.Namespace) -> int:
    ensure_dirs()
    platform = args.platform
    if platform == "weibo" and not args.tool_name:
        raise RuntimeError("微博当前缺默认搜索映射。等你配置好 TIKHUB_API_KEY 后，可先刷新 catalog，再用 --tool-name 自定义接入。")

    tool_name = args.tool_name or TIKHUB_DEFAULT_TOOLS.get(platform)
    if not tool_name:
        raise RuntimeError(f"平台 {platform} 暂未配置默认工具，请使用 --tool-name。")

    pages = max(1, math.ceil(args.limit / args.page_size))
    records: List[Dict] = []
    raw_pages: List[Any] = []

    for page in range(1, pages + 1):
        if args.args_json:
            arguments = json.loads(args.args_json)
        else:
            arguments = build_tikhub_search_args(platform, args.query, page, args.page_size)
        raw = run_tikhub(platform, tool_name, arguments, timeout=args.timeout)
        raw_pages.append(raw)
        batch = normalize_tikhub_items(platform, raw, args.query)
        records.extend(batch)
        if len(records) >= args.limit or args.args_json:
            break

    records = records[: args.limit]
    output = Path(args.output) if args.output else OUTPUT_DIR / f"{platform}_{args.query}.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(output, records)

    if args.raw_output:
        raw_output = Path(args.raw_output)
        raw_output.parent.mkdir(parents=True, exist_ok=True)
        raw_output.write_text(json.dumps(raw_pages, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"已写入 {len(records)} 条：{output}")
    return 0


def fetch_for_topic(topic: str, queries: List[str], platforms: List[str], limit: int, page_size: int, timeout: int) -> Dict[str, Path]:
    ensure_dirs()
    stamp = dt.datetime.now().strftime("%Y%m%d")
    batch_dir = OUTPUT_DIR / stamp / topic
    batch_dir.mkdir(parents=True, exist_ok=True)
    outputs: Dict[str, Path] = {}
    merged: List[Dict] = []
    failure_log = batch_dir / f"{topic}_failures.jsonl"

    for platform in platforms:
        for query in queries:
            try:
                if platform in TIKHUB_DEFAULT_TOOLS:
                    tool_name = TIKHUB_DEFAULT_TOOLS.get(platform)
                    pages = max(1, math.ceil(limit / page_size))
                    records = []
                    for page in range(1, pages + 1):
                        args = build_tikhub_search_args(platform, query, page, page_size)
                        raw = run_tikhub(platform, tool_name, args, timeout=timeout)
                        records.extend(normalize_tikhub_items(platform, raw, query))
                        if len(records) >= limit:
                            break
                    records = records[:limit]
                else:
                    records = bilibili_search(query, limit)
            except Exception as exc:
                write_failure_log(failure_log, topic, platform, query, str(exc))
                records = []
            output = batch_dir / f"{platform}_{query}.jsonl"
            write_jsonl(output, records)
            outputs[f"{platform}:{query}"] = output
            merged.extend(records)

    outputs.update(write_topic_outputs(batch_dir, topic, merged))
    outputs["failures"] = failure_log
    return outputs


def load_run_config(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "topics" in data:
        return data
    if isinstance(data, dict) and all(key in data for key in ["topic", "queries", "platforms"]):
        return {"defaults": {}, "topics": [data]}
    raise ValueError("配置文件格式无效，需要包含 topics 列表，或兼容旧版 topic/queries/platforms 结构。")


def load_inputs(inputs: List[str]) -> List[Dict]:
    records: List[Dict] = []
    for raw in inputs:
        path = Path(raw)
        if not path.is_absolute():
            candidate_paths = [
                Path.cwd() / raw,
                ROOT / raw,
                ROOT.parent / raw,
                ROOT.parent.parent / raw,
            ]
            path = next((candidate for candidate in candidate_paths if candidate.exists()), candidate_paths[0])
        if not path.exists():
            raise FileNotFoundError(f"找不到输入文件：{path}")
        if path.suffix.lower() == ".jsonl":
            records.extend(read_jsonl(path))
        elif path.suffix.lower() == ".csv":
            records.extend(read_csv(path))
        else:
            raise ValueError(f"暂不支持的文件类型：{path.suffix}")
    return dedupe_records(records)


def cmd_analyze(args: argparse.Namespace) -> int:
    ensure_dirs()
    records = load_inputs(args.input)
    output = Path(args.output) if args.output else OUTPUT_DIR / f"{args.topic}_需求报告.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(args.topic, records), encoding="utf-8")
    print(f"已生成报告：{output}")
    return 0


def cmd_run_topic(args: argparse.Namespace) -> int:
    outputs = fetch_for_topic(
        topic=args.topic,
        queries=args.query,
        platforms=args.platform,
        limit=args.limit,
        page_size=args.page_size,
        timeout=args.timeout,
    )
    for key, path in outputs.items():
        print(f"{key}: {path}")
    return 0


def cmd_enrich_comments(args: argparse.Namespace) -> int:
    ensure_dirs()
    records = load_inputs([args.input])
    selected = sorted(
        records,
        key=lambda item: item.get("adjusted_business_score", item.get("business_score", 0)),
        reverse=True,
    )
    if args.platform:
        selected = [item for item in selected if item.get("platform") in args.platform]
    selected = selected[: args.limit]

    enriched_map: Dict[str, Dict[str, Any]] = {}
    for item in selected:
        key = item.get("url") or f"{item.get('platform')}::{item.get('title')}::{item.get('query')}"
        try:
            enriched_map[key] = enrich_record_with_comments(item, timeout=args.timeout)
        except Exception as exc:
            failed = dict(item)
            failed["comment_error"] = str(exc)
            enriched_map[key] = normalize_record(failed)

    final_records = []
    for item in records:
        key = item.get("url") or f"{item.get('platform')}::{item.get('title')}::{item.get('query')}"
        final_records.append(enriched_map.get(key, item))

    output = Path(args.output) if args.output else Path(args.input).with_name(Path(args.input).stem + "_comments.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(output, final_records)
    print(f"已补充评论证据并写入：{output}")
    return 0


def cmd_run_config(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path.cwd() / config_path
    if not config_path.exists():
        raise FileNotFoundError(f"找不到配置文件：{config_path}")

    config = load_run_config(config_path)
    defaults = config.get("defaults", {})
    topics = config.get("topics", [])
    if not topics:
        raise ValueError("配置里没有 topics，无法执行。")

    for item in topics:
        if item.get("enabled", True) is False:
            continue
        topic = item.get("topic") or item.get("name")
        queries = item.get("queries") or defaults.get("queries") or []
        platforms = item.get("platforms") or defaults.get("platforms") or []
        limit = int(item.get("limit", defaults.get("limit", args.limit)))
        page_size = int(item.get("page_size", defaults.get("page_size", args.page_size)))
        timeout = int(item.get("timeout", defaults.get("timeout", args.timeout)))
        manual_inputs = item.get("manual_inputs") or defaults.get("manual_inputs") or []
        if not topic or not queries or not platforms:
            raise ValueError(f"配置项缺少 topic/queries/platforms：{item}")

        outputs = fetch_for_topic(topic, queries, platforms, limit, page_size, timeout)
        merged_records = read_jsonl(outputs["merged"])
        if manual_inputs:
            merged_records.extend(load_inputs(manual_inputs))
            outputs.update(write_topic_outputs(outputs["merged"].parent, topic, merged_records))

        print(f"=== {topic} ===")
        for key, path in outputs.items():
            print(f"{key}: {path}")
    return 0


def cmd_export_pool(args: argparse.Namespace) -> int:
    ensure_dirs()
    records = load_inputs(args.input)
    output = Path(args.output) if args.output else OUTPUT_DIR / f"{args.topic}_机会池.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_opportunity_pool(args.topic, records), encoding="utf-8")
    print(f"已生成机会池：{output}")
    return 0


def infer_specific_product_name(item: Dict) -> str:
    text = " ".join([item.get("query", ""), item.get("title", ""), item.get("summary", "")])
    scene = infer_product_scene(item)
    if scene == "relationship":
        if any(token in text for token in ["送礼", "礼物"]):
            return "关系送礼推荐器"
        if any(token in text for token in ["冷场", "破冰", "话题", "语音厅"]):
            return "冷场破冰话题生成器"
        return "高情商回复生成器"
    if scene == "work":
        if "简历" in text:
            return "简历诊断改写助手"
        if "面试" in text:
            return "面试复盘生成器"
        if any(token in text for token in ["会议", "纪要", "录音"]):
            return "会议录音纪要整理器"
        return "资料提炼知识库助手"
    if scene == "space":
        if "厨房" in text or "水槽" in text or "橱柜" in text:
            return "厨房收纳方案生成器"
        if "工位" in text or "桌面" in text:
            return "工位桌面整理方案生成器"
        if "宿舍" in text:
            return "宿舍收纳方案生成器"
        if "租房" in text:
            return "租房布置方案生成器"
        return "空间整理方案生成器"
    if scene == "travel":
        if "搬家" in text:
            return "搬家整理清单生成器"
        if "旅行" in text or "出差" in text:
            return "出行收纳清单生成器"
        return "出门防忘清单"
    if scene == "baby":
        return "宝宝喂养记录小程序"
    if scene == "reminder":
        if "吃药" in text:
            return "吃药打卡提醒工具"
        if "睡" in text or "熬夜" in text:
            return "睡眠作息提醒工具"
        return "家庭照护提醒工具"
    if scene == "pet":
        if "喂食" in text:
            return "宠物喂食提醒小程序"
        if "遛狗" in text:
            return "遛狗打卡记录工具"
        return "宠物成长档案工具"
    if scene == "photo":
        if "返图" in text:
            return "返图拍照效果助手"
        return "单设备补光自拍助手"
    return infer_product_name(item)


def product_group_key(item: Dict) -> str:
    return "||".join(
        [
            infer_product_scene(item),
            infer_specific_product_name(item),
            item.get("deliverable", ""),
        ]
    )


def shortlist_group_score(items: List[Dict]) -> float:
    ordered = sorted(items, key=lambda row: row.get("adjusted_business_score", 0), reverse=True)
    top_scores = [row.get("adjusted_business_score", 0) for row in ordered[:3]]
    base = sum(top_scores) / max(len(top_scores), 1)
    total_replies = sum(to_number(row.get("replies")) for row in items)
    total_favorites = sum(to_number(row.get("favorites")) for row in items)
    demand_bonus = min(len(items), 8) * 1.2
    reply_bonus = min(math.log10(total_replies + 1), 3) * 2.0
    favorite_bonus = min(math.log10(total_favorites + 1), 4) * 1.5
    best = ordered[0] if ordered else {}
    qualification_penalty = 10 if best.get("qualification_level") == "高门槛" else 4 if best.get("qualification_level") == "中门槛" else 0
    competition = infer_competition_density(best, items) if best else ""
    competition_penalty = 4 if competition.startswith("高") else 2 if competition.startswith("中") else 0
    return round(base + demand_bonus + reply_bonus + favorite_bonus - qualification_penalty - competition_penalty, 1)


def render_product_shortlist(title: str, records: List[Dict], limit: int = 10) -> str:
    today = dt.date.today().isoformat()
    eligible = [
        item for item in records
        if item.get("platform") == "xiaohongshu"
        and item.get("recommendation") != "不建议做"
        and not item.get("non_demand_noise")
        and item.get("query_relevance", 0) >= 0.34
        and item.get("qualification_level") != "高门槛"
    ]
    groups: Dict[str, List[Dict]] = {}
    for item in eligible:
        groups.setdefault(product_group_key(item), []).append(item)

    ranked_candidates = sorted(
        groups.values(),
        key=lambda items: shortlist_group_score(items),
        reverse=True,
    )
    ranked: List[List[Dict]] = []
    scene_counts: Dict[str, int] = {}
    for items in ranked_candidates:
        best = sorted(items, key=lambda row: row.get("adjusted_business_score", 0), reverse=True)[0]
        scene = infer_product_scene(best)
        if scene_counts.get(scene, 0) >= 2:
            continue
        ranked.append(items)
        scene_counts[scene] = scene_counts.get(scene, 0) + 1
        if len(ranked) >= limit:
            break

    lines = [
        "---",
        "type: note",
        f"date: {today}",
        "tags: [产品清单, 小红书需求, 蓝海需求, AI产品]",
        "status: 活跃",
        "confidence: medium",
        "---",
        "",
        f"# {title}",
        "",
        "## 筛选口径",
        "",
        "- 只用小红书样本作为主需求池",
        "- 按产品机会聚合，不按单条笔记抢排名",
        "- 排除不建议做、无关噪音、低关键词相关和高资质门槛样本",
        "- 优先看：真实需求表达、交付物能否解决、载体是否符合习惯、个人能否先验证",
        "- 同一大场景最多保留 2 个机会，避免被单一赛道刷屏",
        "",
        f"## 样本概况",
        "",
        f"- 输入样本：{len(records)} 条",
        f"- 入选候选样本：{len(eligible)} 条",
        f"- 聚合产品机会：{len(groups)} 个",
        "",
        "## Top 10 产品机会",
        "",
    ]

    if not ranked:
        lines.append("- 暂无符合条件的产品机会")
        return "\n".join(lines)

    for idx, items in enumerate(ranked, start=1):
        ordered = sorted(items, key=lambda row: row.get("adjusted_business_score", 0), reverse=True)
        best = ordered[0]
        product_name = infer_specific_product_name(best)
        features = " / ".join(infer_core_features(best))
        evidence_titles = "；".join(excerpt(row.get("title", ""), 24) for row in ordered[:3])
        total_likes = sum(to_number(row.get("likes")) for row in items)
        total_replies = sum(to_number(row.get("replies")) for row in items)
        total_favorites = sum(to_number(row.get("favorites")) for row in items)
        queries = " / ".join(sorted({row.get("query", "") for row in items if row.get("query")})[:3])
        competition = infer_competition_density(best, records)
        lines.extend(
            [
                f"### {idx}. {product_name}",
                f"- 需求：{infer_product_value(best)}",
                f"- 交付物：{best.get('deliverable', '')}｜载体：{best.get('product_carrier', '')}｜适配：{best.get('carrier_fit', '')}",
                f"- 能否解决：{best.get('solution_fit', '')}",
                f"- 核心功能：{features}",
                f"- 用户链路：{infer_use_flow(best)}",
                f"- 触达路径：小红书笔记切痛点 -> 评论/私信收具体场景 -> H5/PWA/样品原型试用 -> 再决定是否小程序化",
                f"- 所需资质/主体：{best.get('qualification_requirement', '')}",
                f"- 个人验证边界：{best.get('personal_validation_boundary', '')}",
                f"- 开发预估：{best.get('estimated_dev_time', '')}｜资源：Codex 做原型/页面/数据结构，Hermes 补样本、话术和复检，你做验收和上线判断",
                f"- 市场/竞争：{competition}",
                f"- 证据：{len(items)} 条样本｜赞 {total_likes} / 评 {total_replies} / 藏 {total_favorites}｜关键词：{queries}",
                f"- 代表笔记：{evidence_titles}",
                f"- 机会分：{shortlist_group_score(items)}｜建议：{best.get('recommendation', '')}",
                "",
            ]
        )
    return "\n".join(lines)


def cmd_export_shortlist(args: argparse.Namespace) -> int:
    ensure_dirs()
    records = load_inputs(args.input)
    output = Path(args.output) if args.output else OUTPUT_DIR / f"{args.title}_Top{args.limit}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_product_shortlist(args.title, records, args.limit), encoding="utf-8")
    print(f"已生成产品清单：{output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="公域需求收集工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    template_parser = subparsers.add_parser("template", help="生成手工导入模板")
    template_parser.add_argument("--force", action="store_true", help="覆盖已有模板")
    template_parser.set_defaults(func=cmd_template)

    bili_parser = subparsers.add_parser("fetch-bilibili", help="抓取 B 站搜索结果")
    bili_parser.add_argument("--query", required=True, help="搜索关键词")
    bili_parser.add_argument("--limit", type=int, default=10, help="抓取条数")
    bili_parser.add_argument("--output", help="输出 jsonl 文件")
    bili_parser.set_defaults(func=cmd_fetch_bilibili)

    tikhub_parser = subparsers.add_parser("fetch-tikhub", help="通过 tikhub 抓取跨平台搜索结果")
    tikhub_parser.add_argument("--platform", required=True, choices=["xiaohongshu", "douyin", "bilibili", "weibo"], help="目标平台")
    tikhub_parser.add_argument("--query", required=True, help="搜索关键词")
    tikhub_parser.add_argument("--limit", type=int, default=10, help="抓取条数")
    tikhub_parser.add_argument("--page-size", type=int, default=10, help="单页条数")
    tikhub_parser.add_argument("--timeout", type=int, default=45, help="单次 tikhub 调用超时秒数")
    tikhub_parser.add_argument("--tool-name", help="手动指定 tikhub 工具名")
    tikhub_parser.add_argument("--args-json", help="手动指定参数 JSON；指定后跳过默认参数拼装")
    tikhub_parser.add_argument("--output", help="输出 jsonl 文件")
    tikhub_parser.add_argument("--raw-output", help="额外保存原始返回 JSON")
    tikhub_parser.set_defaults(func=cmd_fetch_tikhub)

    analyze_parser = subparsers.add_parser("analyze", help="分析输入样本")
    analyze_parser.add_argument("--topic", required=True, help="报告主题")
    analyze_parser.add_argument("--input", action="append", required=True, help="输入文件，可重复传入")
    analyze_parser.add_argument("--output", help="输出 markdown 文件")
    analyze_parser.set_defaults(func=cmd_analyze)

    topic_parser = subparsers.add_parser("run-topic", help="按主题批量抓取并生成需求报告")
    topic_parser.add_argument("--topic", required=True, help="主题名，用于输出目录")
    topic_parser.add_argument("--query", action="append", required=True, help="搜索关键词，可重复传入")
    topic_parser.add_argument("--platform", action="append", required=True, choices=["xiaohongshu", "douyin", "bilibili"], help="平台，可重复传入")
    topic_parser.add_argument("--limit", type=int, default=10, help="每个平台每个关键词抓取条数")
    topic_parser.add_argument("--page-size", type=int, default=10, help="单页条数")
    topic_parser.add_argument("--timeout", type=int, default=45, help="单次 tikhub 调用超时秒数")
    topic_parser.set_defaults(func=cmd_run_topic)

    config_parser = subparsers.add_parser("run-config", help="按配置批量抓取多个主题并生成报告")
    config_parser.add_argument("--config", required=True, help="JSON 配置文件路径")
    config_parser.add_argument("--limit", type=int, default=10, help="默认每个平台每个关键词抓取条数")
    config_parser.add_argument("--page-size", type=int, default=10, help="默认单页条数")
    config_parser.add_argument("--timeout", type=int, default=45, help="默认单次 tikhub 调用超时秒数")
    config_parser.set_defaults(func=cmd_run_config)

    comments_parser = subparsers.add_parser("enrich-comments", help="给样本补充评论证据并输出新 jsonl")
    comments_parser.add_argument("--input", required=True, help="输入 jsonl 文件")
    comments_parser.add_argument("--output", help="输出 jsonl 文件")
    comments_parser.add_argument("--platform", action="append", choices=["xiaohongshu", "bilibili"], help="只补指定平台，可重复")
    comments_parser.add_argument("--limit", type=int, default=8, help="按校正后好生意分挑选前 N 条补评论")
    comments_parser.add_argument("--timeout", type=int, default=45, help="单次评论抓取超时秒数")
    comments_parser.set_defaults(func=cmd_enrich_comments)

    pool_parser = subparsers.add_parser("export-pool", help="导出小猫补光灯型机会池")
    pool_parser.add_argument("--topic", required=True, help="机会池主题")
    pool_parser.add_argument("--input", action="append", required=True, help="输入文件，可重复传入")
    pool_parser.add_argument("--output", help="输出 markdown 文件")
    pool_parser.set_defaults(func=cmd_export_pool)

    shortlist_parser = subparsers.add_parser("export-shortlist", help="导出按产品机会聚合的 Top 产品清单")
    shortlist_parser.add_argument("--title", required=True, help="清单标题")
    shortlist_parser.add_argument("--input", action="append", required=True, help="输入文件，可重复传入")
    shortlist_parser.add_argument("--limit", type=int, default=10, help="导出产品机会数量")
    shortlist_parser.add_argument("--output", help="输出 markdown 文件")
    shortlist_parser.set_defaults(func=cmd_export_shortlist)

    return parser


def main(argv: List[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"执行失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
