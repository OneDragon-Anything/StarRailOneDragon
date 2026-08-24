"""货币战争 胜率模型特征工程(win_model M1,ADR 草稿 §1)。

从 decisions 帧 ``state.deployed``(战前上场名单,角色级)提取训练特征:
BoW 角色计数 / 星级分布 / 羁绊档位计数 / 装备件数 / total_cost 完成度代理。
node_type 等非 deployed 派生特征由训练表侧 join 提供,见
``features_from_deployed`` docstring 的消费契约。

设计单一源 = ``.debug/temp/currency_war/cw_dev/win_model_design/ADR_草稿.md`` §1
(TFT 特征 → CW 映射表)。本模块是**纯函数**(无 I/O / 无游戏依赖),
sim 与离线训练脚本共用;M2 接入 sim 结算器时直接 import。

数值单一源:
- 阵营计数复用 ``cw_sim._board_factions_of``(factions+flows 并计口径);
- 激活阈值读 ``cw_factions.FACTIONS[*].tiers``(不复制数值);
- 角色费用读 ``cw_chars.CHARACTERS[*].cost``。
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from sr_od.application.currency_war.cw_factions import FACTIONS
from sr_od.application.currency_war.cw_sim import _board_factions_of


def _tier_of(faction: str, count: int) -> int:
    """单个羁绊的激活档位数(0=未激活第一层;tiers 单一源=注册表)。

    独立羁绊(单人专属,tiers=(1,))场上 1 人即 tier1——按注册表
    阈值通用计算,不特判。
    """
    info = FACTIONS.get(faction)
    if info is None:
        return 0
    return sum(1 for t in info.tiers if count >= t)


def features_from_deployed(deployed: list[dict]) -> dict[str, Any]:
    """战前上场名单 → 胜率模型特征 dict(win_model M1,ADR 草稿 §1)。

    输入:decisions 行 ``state.deployed``,每项含
    ``char_id/star/equips/slot``(缺字段容忍;空 ``char_id`` = 占位槽,
    与生产 OCR 空板同形,不计入任何计数)。

    输出特征(dict,JSON 可序列化):

    - ``char_count`` / ``bow``:上场人数与角色计数(BoW;空 char_id 不计);
    - ``star_sum`` / ``star_hist``:星级总和与分布({1:..,2:..,3:..});
    - ``equip_count``:装备件数(``deployed[].equips``,已装备口径;
      未装备池 ``state.equips`` 不在此)。**当前语料零方差**(10927 条
      deployed 仅 1.1% 非空,批38 审计)——M1 不指望它有贡献,
      语料攒厚后自然生效,训练侧可按需排除;
    - ``total_cost``:Σ 注册表 ``cost``×计数——**完成度代理,已知偏差**:
      注册表 cost=起始费,升星升费未建模(cw_chars 银狼LV.999 注释,
      ADR 草稿风险 4),系统性低估高星阵容;
    - ``unknown_char_count``:char_id 非空但不在注册表的人数(识别形变
      残留,>0 时 bow/total_cost 有漏计,训练侧披露口径);
    - ``faction_counts``:阵营计数(``_board_factions_of`` 口径,
      factions+flows 并计);
    - ``tier_hist``:羁绊档位直方图({1:..,2:..,3:..,4:..},
      每羁绊激活到第几层,阈值对照 ``FACTIONS[*].tiers``);
    - ``max_tier``:最高激活档位(阵容成型度粗粒度代理);
    - ``tier3_count``:tier_hist 中档位==3 的羁绊个数。批39 压测实证
      (``.debug/temp/currency_war/cw_dev/sim_压测_批39/报告.md``):
      tier-3 羁绊数是 P1 boss 胜负近似分界(t3≤2 → 0/19 胜;t3=3 的
      板唯一胜)——max_tier 不区分「有几个 t3 羁绊」(3×tier-3 板与
      1×tier-3 板同值),tier3_count 补上这一维度。

    ⚠️ **node_type 不在本函数输出里**(设计决策,批38 审计修订):
    node_type(普通战斗/遭遇/boss)是**训练表侧 join 的强先验特征**
    (批38:胜率 0.309/0.040/0.056),不是 ``deployed`` 派生量——本函数
    只做 deployed 派生特征,不引入「入参原样透传出参」的伪特征。
    消费侧(sim 结算器 / 训练脚本)拼特征向量时须**显式加入 node_type**
    (训练表已由 ``win_model_build_table.py`` join 带上该列)。
    """
    bow: dict[str, int] = {}
    star_hist: dict[int, int] = {}
    star_sum = 0
    equip_count = 0
    total_cost = 0
    unknown_char_count = 0
    from sr_od.application.currency_war.cw_chars import CHARACTERS

    for d in deployed or []:
        cid = (d.get('char_id') or '').strip()
        if not cid:
            continue  # 占位槽(空 char_id)不计,ADR 草稿 §1 处置
        bow[cid] = bow.get(cid, 0) + 1
        star = d.get('star') or 0
        star_sum += star
        star_hist[star] = star_hist.get(star, 0) + 1
        equip_count += len(d.get('equips') or [])
        ch = CHARACTERS.get(cid)
        if ch is None:
            unknown_char_count += 1
        else:
            total_cost += ch.cost

    # 阵营计数复用 sim 生产口径(dict → attr shim,零复制)
    shim = [SimpleNamespace(char_id=(d.get('char_id') or '').strip())
            for d in (deployed or [])]
    faction_counts: dict[str, int] = _board_factions_of(shim)

    tier_hist: dict[int, int] = {}
    max_tier = 0
    for faction, cnt in faction_counts.items():
        t = _tier_of(faction, cnt)
        if t > 0:
            tier_hist[t] = tier_hist.get(t, 0) + 1
            max_tier = max(max_tier, t)

    return {
        'char_count': sum(bow.values()),
        'bow': bow,
        'star_sum': star_sum,
        'star_hist': {str(k): v for k, v in sorted(star_hist.items())},
        'equip_count': equip_count,
        'total_cost': total_cost,
        'unknown_char_count': unknown_char_count,
        'faction_counts': faction_counts,
        'tier_hist': {str(k): v for k, v in sorted(tier_hist.items())},
        'max_tier': max_tier,
        'tier3_count': tier_hist.get(3, 0),
    }
