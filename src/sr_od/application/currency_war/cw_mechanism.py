"""机制常数注册表 v0(redesign 23 号落地第一步;ADR 待补)。

设计:每个游戏机制常数(区别于策略权重——判据:能否从 telemetry 直接测量)登记为
MechanismConstant:value(点或区间)/ provenance / status / consumers / audit_spec。
读口 get(name) → (value, status);telemetry 核对器(audit)后续接入。

首批迁移 ~14 个(23 号 §2.1 清单):从散落硬编码收编,**值不变、语义显式化**——
本步只建注册表+把「纯猜」的来源标 unverified,消费端接线后续逐步切(不一次性
大迁移,防回归)。24 号 offline_weight_search 的适应度地形、28 号穷举扫描直接
消费本表。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MechanismConstant:
    """一个游戏机制常数(可被 telemetry 测量的物理/经济/概率规则参数)。"""

    name: str
    value: float | dict          # 点值或区间/表(dict 键=level/cost 档)
    kind: str                    # physics|income|odds|prior|meta
    provenance: str              # 来源:bwiki|数据银行|plaza|实测+ADR-NN|OCR-live|粗估
    status: str                  # unverified|bracketed|verified|refuted|stale
    consumers: tuple[str, ...] = ()   # 消费模块(告警反查影响面)
    note: str = ''


# ===== 首批登记(2026-08-17;值从原散落处原样收编,来源照实标) =====
_REGISTRY: dict[str, MechanismConstant] = {c.name: c for c in [
    # —— 收入/经济流 ——
    MechanismConstant(
        'BASE_INCOME', 5.0, 'income', 'bwiki+多局telemetry对拍', 'verified',
        ('cw_horizon', 'cw_economy'), note='每节点基础收入'),
    MechanismConstant(
        'INTEREST_THRESHOLD', 50.0, 'income', 'bwiki(息封顶50)', 'verified',
        ('cw_plan', 'cw_economy', 'cw_horizon'), note='攒息上限(息=gold//10,封顶5)'),
    MechanismConstant(
        'SHOP_REFRESH_COST', 2.0, 'income', '粗估,实机校准(注释许诺未兑现)', 'unverified',
        ('cw_plan', 'cw_economy'), note='刷新商店花费;telemetry: refresh 动作前后 gold 差即测'),
    MechanismConstant(
        'XP_PER_BUY', 4.0, 'income', '用户口述+ADR-0129', 'verified',
        ('cw_horizon',), note='买牌附赠 XP'),
    MechanismConstant(
        'XP_CLICK_COST_FLAT', 4.0, 'income', '实测 4-8 区间取下限(cw_horizon 注释自记敏感点)',
        'bracketed', ('cw_horizon',),
        note='购买经验单击 XP;V1.0 取值过贵 → DP 全路径值 0 坍塌(23 号 §1 事故)'),
    # —— 概率表 ——
    MechanismConstant(
        'SHOP_ODDS_TABLE', {}, 'odds', '3费=13 单点吻合,其余注册表粗值', 'bracketed',
        ('cw_shop_odds', 'cw_belief_pool'), note='各 level 刷新各费用概率;16/17 号消费'),
    # —— 规则确定性 ——
    MechanismConstant(
        'BENCH_CAPACITY', 9, 'physics', '实测(备战栏 9 槽)', 'verified',
        ('cw_state',), note='备战席槽位'),
    MechanismConstant(
        'DEPLOY_FRONT_SLOTS', 4, 'physics', '实测+screen_info', 'verified',
        ('cw_state', 'deploy_bench'), note='前排槽(投资环境可变? 见 gameplay doc 变槽位注记)'),
    MechanismConstant(
        'DEPLOY_BACK_SLOTS', 6, 'physics', '实测+screen_info', 'bracketed',
        ('cw_state', 'deploy_bench'), note='后排槽;某投资环境 6→7(用户确认)——非常量,环境条件'),
    MechanismConstant(
        'STAR_MERGE_COUNT', 3, 'physics', '官方玩法说明+实测', 'verified',
        ('cw_performance',), note='3 同星同名 → 升 1 星'),
    MechanismConstant(
        'SELL_REFUND_1COST', 1.0, 'income', '实测锚(1费各星全额退)', 'bracketed',
        ('cw_economy',), note='≥2费 2★+ 亏 1 手续费(部分实测)'),
    MechanismConstant(
        'MAX_UNITS_BASE', 10, 'physics', '游侠/bwiki(队伍总8-10)', 'bracketed',
        ('cw_state',), note='上阵上限=level(+宝钻加成,D-50)'),
    # —— 策略侧先验(非物理;登记供 19 号收紧) ——
    MechanismConstant(
        'HP_LOSS_PRIOR', {}, 'prior', 'plaza 派生', 'bracketed',
        ('cw_damage_ledger',), note='19 号伤害账本区间先验'),
    MechanismConstant(
        'STAR3_RATE_BY_COST', {'1': 0.76, '2': 0.81, '3': 0.87, '4': 0.58, '5': 0.37},
        'meta', 'plaza 648 篇统计', 'bracketed',
        ('cw_plaza_comps',), note='星级目标先验;自家局聚合可覆盖'),
]}


def get_mechanism(name: str) -> MechanismConstant | None:
    """读机制常数;未登记名 → None(消费端 fallback 原值)。"""
    return _REGISTRY.get(name)
