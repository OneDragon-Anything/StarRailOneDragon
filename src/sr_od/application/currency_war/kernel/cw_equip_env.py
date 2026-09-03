"""货币战争 装备环境信号包(决策层读取口)。

(fill-to-3 量变体与变宝为废牺牲合成的序变体已随各自开关族
(equip_env_fill3_enabled / junk_first_sacrifice_enabled)删除——旧方案
清退批,清查报告 OLD_MIX_AUDIT §1.3:两开关默认关+开臂判据挂账未跑
即整体出局,``apply_equip_env_variants`` 退化为基分配直通(与全关
零漂移行为一致),kernel/cw_junk_first.py 模块同批删。机制真值
(软弱无力/额外打击/变宝为废词缀原文)保留在
data/affix_effects_data。)

保留件:
- ``build_equip_env_signals``:equip_all 决策调用处的环境信号单源
  构造点(生锈豁免等门变体仍消费 ``signals.enemy_affixes``,设计
  §2.2「变体不各自摸 state」纪律不变);
- ``apply_equip_env_variants``:EquipAll 唯一分配入口(签名保留,
  调用零改),现恒返回 ``cw_comps.equip_allocation`` 基分配。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp

# 环境词缀识别名(画面 OCR 原名;affix_effects_data 注册表同名)
# (fill3 变体已删,保留名单供判读/建档引用。)
EQUIP_ENV_FILL3_AFFIXES: tuple[str, str] = ('软弱无力', '额外打击')


@dataclass(frozen=True)
class EquipEnvSignals:
    """装备环境信号包(equip_all 决策调用处构造一次,门变体共享;设计 §2.2)。

    ``enemy_affixes`` = state.enemy_affixes(简报∪随采;state 缺失=空集);
    ``plane``/``round_num`` = state 记账/窗口字段(预留)。
    """
    enemy_affixes: frozenset[str]
    plane: int | None
    round_num: int | None


def build_equip_env_signals(state) -> EquipEnvSignals:
    """state → 信号包(唯一读取点;state 缺失/字段缺失 = 安全默认,不抛错)。

    ``state`` = ``session.last_state``(可为 None,离线/旧栈);字段经 getattr
    宽读,缺 = None / 空集。
    """
    affixes = list(getattr(state, 'enemy_affixes', None) or []) if state is not None else []
    plane = getattr(state, 'plane', None) if state is not None else None
    round_num = getattr(state, 'round_num', None) if state is not None else None
    return EquipEnvSignals(
        enemy_affixes=frozenset(affixes),
        plane=int(plane) if plane is not None else None,
        round_num=int(round_num) if round_num is not None else None,
    )


def apply_equip_env_variants(signals: EquipEnvSignals,
                             registry,
                             session,
                             comp: Comp | None,
                             deployed: list,
                             owned: list[str],
                             occupied: dict[tuple[str, int], list[str]] | None,
                             hold_active: bool,
                             ) -> tuple[list[tuple[str, str]], list[str]]:
    """装备分配入口(EquipAll 唯一调用点;基分配直通)。

    (原门→量→序变体管道的量(fill3)与序(变宝为废牺牲合成)两级已随
    开关族删除——旧方案清退批,清查报告 OLD_MIX_AUDIT §1.3;门级
    hold/生锈豁免在 equip_all 调用侧生效,不经本函数。签名保留调用
    零改;``registry``/``session``/``signals``/``hold_active`` 参数占位
    不再参与取值。)
    """
    from sr_od.application.currency_war.kernel.cw_comps import equip_allocation
    base = equip_allocation(comp, deployed, owned, occupied)
    return base, []
