KEYWORD_RULES = [
    "价格", "多少钱", "优惠", "活动", "折扣",
    "买", "购买", "想买", "下单", "入手", "有货", "缺货",
    "发货", "物流", "快递", "到货", "收货",
    "比价", "对比", "划算", "贵", "便宜",
    "好用", "推荐", "效果", "敏感肌", "过敏",
    "精华液", "面霜", "粉底液", "奶瓶"
]


def extract_rule_keywords(message_content: str | None):
    content = message_content or ""
    keywords = []

    for keyword in KEYWORD_RULES:
        if keyword in content:
            keywords.append(keyword)

    if "跟上次" in content or "比怎么样" in content:
        keywords.append("比价")

    return list(dict.fromkeys(keywords))