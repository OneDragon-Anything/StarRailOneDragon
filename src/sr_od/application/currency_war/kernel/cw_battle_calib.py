"""货币战争战斗校准与板面聚合函数族(现役面收束后形态)。

现役函数三组:
- 结算成型度键(:func:`_settle_rung` 四体系达成数 /
  :func:`deployed_star_depth` 净星深)——sim power_model 特征面消费;
- 板面聚合族(:func:`_board_factions_of` 生产 board 口径阵营计数,
  cw_win_features 复用;:func:`_engines_count` 薄委托
  knowledge/cw_engine_facts 权威副本);
- 商店轮岗概率表(:func:`roll_rotation_per_stage` sim 抽店消费;
  :func:`_roll_rotation` 旧树 replay 交叉核对口径保留面)。

历史面(规则表结算层 node_delta 族 / P2 参数化存活层 p2_* 族 /
Δ池采样键 _deployable_depth)随 sim 结算收口删除——消费方
(Δ池采样 / 规则表回退)已随 sim 重做批次退场,src/测试仓零调用;
数据表正本 data/cw_battle_tables.py 同批删除(git 历史可溯)。

桩点契约:消费方函数内懒 import 本模块符号(属性动态解析),
monkeypatch 钉本模块符号(锁改判裁决=N7,禁 shim)。
"""
from __future__ import annotations

import random

from sr_od.application.currency_war.data.cw_shop_odds import (
    REFRESH_PROB,
    ROTATION_CHANCE,
    rotation_probs,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    deployed_rows_of,
)


def deployed_star_depth(gs: GameState) -> int:
    """净星深 = 上场件 Σ(star−1)(全量口径;纯 state 可算、生产/sim/
    离线回放三面同式)。

    消费点 = sim power_model 特征面(星级深度特征)。已知边界:2★→3★
    合并键 −1(3 副本 Σ(star−1)=3 → 载体 2),仅当键恰为 3 的倍数时
    跨桶——高级合并当前语料零样本,语料攒厚后复核。
    """
    front, back = deployed_rows_of(gs)
    return sum(int(getattr(d, 'star', 1) or 1) - 1
               for d in (*front, *back) if d is not None)


def _settle_rung(gs: GameState) -> int:
    """结算时点成型度 rung(四体系达成数;sim power_model 特征面消费)。

    口径 = _engines_count(仙舟3/列车2/DOT2/希儿系),输入 = board 全集
    口径(口径统一源=_recount_board,星徽贡献并计)+上场名单(希儿系
    单卡判据)。
    """
    from sr_od.application.currency_war.kernel.cw_bond_equips import _recount_board
    front, back = deployed_rows_of(gs)
    _bf = _recount_board([*front, *back])
    _names = frozenset(d.char_id for d in (*front, *back)
                       if d is not None and getattr(d, 'char_id', ''))
    return _engines_count(_bf, _names)


def _board_factions_of(deployed) -> dict[str, int]:
    """上场角色的阵营计数(生产 board 口径,flows 并计)。

    消费点 = cw_win_features 阵营计数复用。选边型双羁绊角色(布洛妮娅,
    ``cw_chars.SIDE_PICK_DUAL_BONDS``)按 ``cw_chars.side_pick_bond``
    选边单边计入(基数 = 其余在场角色注册表出身,不含装备贡献)。
    """
    from sr_od.application.currency_war.data.cw_chars import (
        CHARACTERS as _CH,
    )
    from sr_od.application.currency_war.data.cw_chars import (
        SIDE_PICK_DUAL_BONDS as _SP,
    )
    from sr_od.application.currency_war.data.cw_chars import (
        side_pick_bond as _side_pick,
    )
    out: dict[str, int] = {}
    units = [d for d in (deployed or []) if d is not None]
    cids = [str(getattr(d, 'char_id', '') or '') for d in units]
    for cid in cids:
        ch = _CH.get(cid) if cid else None
        if ch is None:
            continue
        if cid in _SP:
            tags: tuple[str, ...] = (_side_pick(
                cid, [c for c in cids if c != cid]),)
        else:
            tags = (ch.factions or ()) + (ch.flows or ())
        for f in tags:
            out[f] = out.get(f, 0) + 1
    return out


#: 公开别名(单一源语义:成型/镜像类消费一律经此名,与旧层兜底门
#: 同一板面计数口径;私有名仅供本模块历史调用点)。
board_factions_of = _board_factions_of


def _engines_count(board_factions: dict[str, int],
                   deployed_names: frozenset[str] | set[str] = frozenset()
                   ) -> int:
    """过渡体系达成数(三选几+希儿系;两两组合=过渡成型)。

    本体 = knowledge/cw_engine_facts.engines_count 权威副本
    (机制事实判据,不依赖迁移待办的 kernel/cw_deploy_logic);
    本模块消费点 = _settle_rung。
    希儿系=希儿在场 AND(量子同频≥2 OR 贝洛伯格≥2)——
    与三羁绊同级可组合。
    """
    from sr_od.application.currency_war.knowledge.cw_engine_facts import (
        engines_count as _impl,
    )
    return _impl(board_factions, deployed_names)


def _roll_rotation(rng: random.Random, level: int) -> dict[int, float] | None:
    """本备战期轮岗事件(审计项 F4):概率 ROTATION_CHANCE 掷中 →
    随机一档(基线 0<p<0.5 才可能被翻倍)×2 → 完整概率表;
    未掷中/该等级无可翻倍档 → None(基线表,生产「未读到概率条」同态)。

    ⚠️ 语义已勘误(01_strategy_layer.md §4.10 概率表族):「20%」是
    replay 观测在场频率,非机制概率——运行时被测体已改用
    ``roll_rotation_per_stage``。本函数保留作旧树 replay 交叉核对口径,
    勿在新消费点接线。
    """
    if rng.random() >= ROTATION_CHANCE:
        return None
    base = REFRESH_PROB.get(level, {})
    tiers = [c for c, p in base.items() if 0 < p < 0.5]
    if not tiers:
        return None
    return rotation_probs(level, rng.choice(tiers))


def roll_rotation_per_stage(rng: random.Random, level: int) -> dict[int, float] | None:
    """已选轮岗环境的本备战期概率表(勘误后机制建模)。

    机制(游戏原文 cw_invest_data id=114「每个备战阶段重新随机」):选择后
    **每备战阶段 100% 生效、每阶段重掷翻倍档**;翻倍档分布 = 费用档 1/5
    均匀系**建模假设,实机待核**(01 §4.10 概率表族)。翻倍档不可行档
    (基线 p=0 或 2p≥1)在该级不存在翻倍语义 → 从可行档内均匀重掷
    (对 1/5 假设的可行档截断;全不可行 → None 退基线,同生产「低级帧
    无轮岗」)。生产真值仍是读屏概率条(parse_prob_bar),本函数只服务
    sim 抽店。
    """
    base = REFRESH_PROB.get(level, {})
    tiers = [c for c, p in base.items() if 0 < p < 0.5]
    if not tiers:
        return None
    return rotation_probs(level, rng.choice(tiers))
