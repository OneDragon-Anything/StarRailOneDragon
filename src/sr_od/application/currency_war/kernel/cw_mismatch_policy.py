"""统一观察对账·失配处置策略(豁免注册表 + 安灯钩子槽)。

**正本指针** = ``docs/develop/sr_od/application/currency_war/game_state/README.md``
(观察对账与安灯节;迭代设计 =
``docs/develop/sr_od/application/currency_war/changes/2026-09-16-unified-obs-reconcile/design.md``)。

失配 = ``GameState.observe()`` 观察覆盖 logic 值不一致(逻辑态被实读证伪
= bug:此前观察态错 / 逻辑推算代码错),处置三分流住在观察写入口
(cw_game_state 侧路由),本模块只承载其中两个**声明式治理面**:

1. **豁免注册表**:确证为游戏机制性结构差异、建模不可行的失配模式,按
   「画面×字段×逻辑写端」三维度逐条申报(键坐标系见 :class:`ExemptEntry`);
   豁免 ≠ 消失——豁免命中仍落 ``exempt_mismatch`` 台账行,只是无告警无停机。
   初始为空:已知生产失配都是 bug(归日常修/归因批),注册表是给未来
   确证机制差异留治理位,不是给已知 bug 开后门。
2. **安灯钩子槽**:真失配缺陷行落行后的运行时处置钩子(生产装配 = 截图
   留证 + 停机 flag,装配点 = currency_war_app 装配段)。kernel 侧纯记录:
   缺省 None = 测试/sim 环境零副作用(只留证不停机),满足「可注入回调、
   缺省无真实现」约束;注入槽先例 = ``set_defect_sink``。

**导入方向**:本模块零依赖 ``cw_game_state``(被其单向 import;kernel→kernel
单向依赖先例 = ``cw_state_journal``),禁反向。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from one_dragon.utils.log_utils import log

#: 豁免条目的「不限维度」通配值(screen 维通配另经注册表键 ``('*',
#: field)`` 承载,条目内 screen 值不参与匹配)。
EXEMPT_ANY: str = '*'


@dataclass(frozen=True)
class ExemptEntry:
    """一条失配豁免申报(三维度全命中才豁免)。

    - ``screen`` = 观察侧画面建档名(键坐标系 = **本次 observe 写入的
      sig.screen**;logic 族写入 screen 恒 None 不参与对账)。条目值恒
      建档名,通配按画面走注册表 ``('*' , field)`` 键,条目内不写 '*'
      ——按画面治理的粒度由键结构保证,条目内通配会把「买了没扣钱」类
      真失败一并吞掉;
    - ``field`` = 容器字段名(GameState dataclass 字段,如 'gold');
    - ``logic_evidence`` = 逻辑侧写端 evidence **前缀**(:data:`EXEMPT_ANY`
      = 不限写端)。同字段内分流失配成因——例「刷新执行写下的金值与实读
      不合」按写端前缀豁免,不波及同字段购买写端(真点击落空照停);
    - ``reason`` = 持久索引(文件路径/符号名/ADR-NNNN 或纯语义描述);
      条目为代码常量,变更走 review 可见。

    frozen = 申报一经落地不被就地改写(与 Field 帧替换同纪律)。
    """

    screen: str
    field: str
    logic_evidence: str
    reason: str


#: 失配豁免注册表(键 = (screen, field),值为条目元组——同画面同字段可
#: 并存多条不同写端前缀的豁免)。初始为空;扩面 = 在此登记代码常量,
#: 禁运行时动态增删(注册表写代码 = 治理可见,运行时改 = 后门)。
EXEMPT_REGISTRY: dict[tuple[str, str], tuple[ExemptEntry, ...]] = {}


def lookup_mismatch_exempt(screen: str | None, field_name: str,
                           logic_evidence: str | None) -> ExemptEntry | None:
    """失配豁免查表(先精确桶、后通配桶,**两桶独立评估互不阻断**)。

    - 精确桶键 = ``(screen, field_name)``;``screen=None`` 时精确键不可能
      命中,仅 ``('*', field_name)`` 通配条目可豁免(不可指名画面的写端
      由通配条目治理);
    - 桶内逐条比对 ``logic_evidence`` 前缀(条目 :data:`EXEMPT_ANY` = 不限
      写端),首条全维命中即返回;精确桶 evidence 不中**不跳过**通配桶;
    - 字段 logic evidence 为 None 时,仅 EXEMPT_ANY 条目可命中(前缀比对
      对 None 恒不中,禁把「无注记」当任意前缀)。

    :param screen: 观察侧 sig.screen(可为 None);
    :param field_name: 容器字段名;
    :param logic_evidence: 逻辑侧 ``Field.evidence``(可为 None)。
    """
    buckets: tuple[tuple[str, str], ...] = (
        ((screen, field_name),) if screen is not None else ()) + \
        ((EXEMPT_ANY, field_name),)
    for key in buckets:
        for entry in EXEMPT_REGISTRY.get(key, ()):
            if entry.logic_evidence == EXEMPT_ANY or (
                    logic_evidence is not None
                    and logic_evidence.startswith(entry.logic_evidence)):
                return entry
    return None


#: 真失配安灯钩子槽(缺省 None = 测试/sim 零副作用,只留证不停机)。
#: 注入槽模式先例 = ``set_defect_sink`` / ``set_star_evidence_saver``;
#: 生产装配点 = currency_war_app 装配段(与 defect sink 同点注入)。
_ANDON_HOOK: Callable[[dict], None] | None = None


def set_reconcile_andon_hook(fn: Callable[[dict], None] | None) -> None:
    """接通/复位真失配安灯钩子(None = 关,缺省态;注入槽模式)。

    契约:真失配缺陷行落行后同步调用 ``fn(row)``;``row`` = 缺陷行 dict
    (ts / field / expected / actual / observed_evidence / screen / actor /
    group_id / logic_evidence);``fn`` 异常不阻塞写路径(best-effort,
    同 defect sink 契约)。
    """
    global _ANDON_HOOK
    _ANDON_HOOK = fn


def fire_reconcile_andon(row: dict) -> None:
    """触发真失配安灯(best-effort:钩子缺席/异常都不阻塞观察写链;
    由 cw_game_state 缺陷行落行后调用,本模块不自判触发时机)。"""
    hook = _ANDON_HOOK
    if hook is None:
        return
    try:
        hook(row)
    except Exception as e:  # noqa: BLE001  安灯 best-effort,不毒化写入链
        log.debug(f'[cw-bs] reconcile andon skip: {e}')
