"""货币战争 · 信号锁线(Phase A Day 5;redesign §4.4 信号 2 层)。

**策略层,手维护——不含任何识别逻辑**(用户 r222:现成识别代码
很多,我们只改策略部分):名字→规范名是识别层的职责
(read_shop_cards SIFT→resolve_char_name / BenchChar.char_id /
cw_reconcile 对账,均已存在);本模块拿到的输入**就是规范名**,
只做「出现了核心卡吗→锁哪条线」的策略判断,精确匹配。

Phase A 范围(redesign §11):信号 2 层=核心卡到手(看到即锁)。
0/1/3 层(策略文本/资源累计)Phase B;无「反常识信号加权」
(无感知载体,r213 对抗修正③已删)。

置信纪律的层次划分:
  识别层(现有):SIFT/OCR 的置信与未识别处理(name='' 不猜)
  策略层(本模块):name 为空=未识别=不锁(漏锁可接受,
    退化兜底线;误锁不可接受)。"""
from __future__ import annotations

from dataclasses import dataclass

from sr_od.application.currency_war.cw_line_library_v1 import (
    LINE_LIBRARY_V1,
    LineV1,
)


@dataclass
class LockResult:
    """一次锁线检查的结果。"""
    locked: bool
    line_id: str | None = None
    matched_name: str | None = None   # 命中的核心卡规范名(遥测用)


def check_core_signal(char_names: list[str] | set[str]) -> LockResult:
    """信号 2 层检查:可见角色里出现某线核心卡 → 锁线。

    Args:
        char_names: 规范名列表/集合——调用方从 GameState 组装
            (shop 的 ShopCard.name + deployed/bench 的 char_id;
            两者识别层已归一到规范名)。空串=未识别,跳过。

    Returns:
        LockResult;多线同时命中取 LINE_LIBRARY_V1 库序
        (redesign 同层冲突仲裁的 Phase A 简化:库序=调研
        优先级,非随机)。
    """
    hit: str | None = None
    for line in LINE_LIBRARY_V1:
        for core in line.core_cards:
            if core in char_names:
                hit = core
                break
        if hit:
            return LockResult(True, line.line_id, matched_name=hit)
    return LockResult(False)


def line_of(line_id: str) -> LineV1 | None:
    """按 id 查线(re-export 自线库——单源;调用方也可直接
    从 cw_line_library_v1 import)。"""
    from sr_od.application.currency_war.cw_line_library_v1 import (
        line_of as _line_of,
    )
    return _line_of(line_id)
