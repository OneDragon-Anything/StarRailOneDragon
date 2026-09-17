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
#: 并存多条不同写端前缀的豁免)。扩面 = 在此登记代码常量,禁运行时
#: 动态增删(注册表写代码 = 治理可见,运行时改 = 后门)。
EXEMPT_REGISTRY: dict[tuple[str, str], tuple[ExemptEntry, ...]] = {
    # 备战帧随机收入盲区:奖励节点点球金(奖励球内容随机,金额执行点
    # 不可推算)不预入逻辑金账——声明盲区锚 = cw_exec_state.apply_op_effect
    # 的 ClickSpheres 零推进申报与 prep_actions._executed_gold_delta
    # docstring。下一备战帧实读把「卖牌退款投影」证伪时,差值恰为该随机
    # 收入,属机制性差异非推算 bug;豁免行留证可审计,真投影错(退款
    # 公式错)由 sim 单帧锁守,不经本条目兜。点球收入若证实可确定性
    # 建模,本条目退役改建模补全。
    ('货币战争-备战', 'gold'): (
        ExemptEntry(
            screen='货币战争-备战', field='gold',
            logic_evidence='proj_sell_refund',
            reason='备战帧随机收入(奖励节点点球金)不可预知,声明盲区'
                   '(kernel/cw_exec_state apply_op_effect ClickSpheres '
                   '零推进申报;2026-09-16 归因批 journal 实证 +4/+7 两起)'),
    ),
}

#: 外部随机备战席授予申报表(卡规范名 → 授予单位数;代码常量,变更走
#: review 可见,同 :data:`EXEMPT_REGISTRY` 纪律)。辖域 = 效果注册表尚未
#: 逐条确定的「获得随机角色」类投资卡:随机身份按效果域写入归属判据
#: 不建逻辑写端(effect-domain §6.3 概率随机分支/§6.4 随机资产面观察
#: 收口),确认后备战席实读必多出逻辑态没有的单位——不申报会被统一
#: 观察对账安灯当推算 bug 停机。吸收语义(非豁免键,豁免注册表的三维
#: 键表达不了「外部授予」形状):确认挂点按本表置
#: ``GameState.exec_books.external_bench_grant_pending``,observe() 失配
#: 分支对 bench 做「纯超集 + 差额 ≤ 待吸收数」精确校验,命中落
#: ``external_grant_absorbed`` 台账行(无告警无停机);形状不符(缺员/
#: 超额/纯槽位错位差额 0)交回三分流照真失配停——随机授予的身份不可
#: 推算,但数量与「只多不少」形状确定,校验据此守住真投影 bug 不被吞。
#: 逐条确定批给这些卡立规格(STRATEGY_EFFECTS)后,条目随批退役改规格
#: 承载。
EXTERNAL_BENCH_GRANTS: dict[str, int] = {
    # 102501 武装支援(银):「获得1件随机简易装备和2个随机3费角色。」
    # (data/cw_invest_data.py 官方卡文;2026-09-18 实机 reconcile 事故:
    #  确认后实读 bench 多出 2 单位,安灯停局首例)
    '武装支援': 2,
    # 102502 武装支援+(银):「获得1件随机简易装备和1个随机4费角色,获得6金币。」
    '武装支援+': 1,
}


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
#: 注入槽模式先例 = ``set_defect_sink``;生产装配点 = currency_war_app
#: 装配段(与 defect sink 同点注入)。
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
        log.debug(f'[cw-gs] reconcile andon skip: {e}')
