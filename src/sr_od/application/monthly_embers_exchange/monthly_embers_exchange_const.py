APP_ID = "monthly_embers_exchange"
APP_NAME = "每月余烬兑换"
DEFAULT_GROUP = True
NEED_NOTIFY = True

MONTHLY_GOODS: list[str] = ["special_pass", "pass", "tracks_of_destiny"]
"""月限三件套固定全集(英文标识符;canonical 顺序即默认兑换顺序
专票>通票>足迹,用户裁定 2026-11-13 第 8 条)"""
