"""货币战争 BoardState 局内记录(迁移批次一骨架)。

**正本入口** = ``docs/develop/currency_war/game_state/README.md``(总纲);
**字段级详设**(迭代期,寿命=迭代) =
``docs/develop/sr_od/application/currency_war/changes/2026-09-11-unified-state/details/BoardState-数据结构设计.md``
(下按节号引用)。BoardState = 当前仍为真的局内已知事实快照:单例,每局新建,
只描述「此刻」;画面 op 与决策 op 写,策略器读(设计 §1)。历史序列归遥测,
不经本结构。

**与现役 GameState 的关系**:并行记录,本批(迁移批次一,设计 §8.7)不切
消费——GameState 消费者行为零变化;消费切换归迁移批次二。字段准入按设计
§8.8 治理三件:派生量(席空数/席满判定/board 下档阈值)是计算函数不存储;
识别质量位是写入闸门不存储(失读统一口径 = §2.2 carried/机制性 None)。

**两个关键结构**(设计 §2.4;预期条目表已随两态制废除):
1. 帧观察完整度标注 + 心跳——标注(full/view/none)消费即清;停更检测
   哨兵用只增不减的写点序号 :attr:`BoardState.write_seq`,不用标注现值。
2. bs_schema——域粒度版本映射(缺域键 = 该域未建模,§3.7.1)。

**两态直写**(ADR-0651,2026-09-11 用户裁定):字段来源只保留 observation
与 logic 两种——逻辑推算值经 :meth:`BoardState.write_logic` 直接写字段
(source=logic,策略器立即可读),expect/confirm 两步机制(预期条目表/
PendingEntry/confirm 转正/discard_expected)全套废除;逻辑态错误 =
代码 bug(修推算代码,不靠运行时挂账对账兜底)。观察赢原则不变(§2.3):
下一帧实读覆盖 logic,失配缺陷台账留证。

**单例宿主** = session 旁表(:func:`board_state_of`;同 ``cw_exec_state``
旁表模式,弱引用表 + 桩面兜底)——session 对象 = 局身份,新局新 session
即天然新建,符合「单例,每局新建」(§1/§6.2)。

**sim 合成口** = :func:`synthesize_from_game_state`:sim 以 GameState 真值
合成时同样记 observation,evidence 恒带 ``sim:synthesized``(§2.1);
bench 槽位保序映射——记录模型按实机真值箱占席(§3.2.5),不采 sim
「无箱实体」的内部口径约定。

**统一 state 遥测升级(R5 W1 常开化后形态)**:写入 API 全部带**必填**渠道签名
(:class:`ChannelSig`,渠道族封闭集 obs/logic_action/logic_hook + 字段级
质量元数据;R1 影子期的「缺位合成 legacy 签名」过渡路径已随直迁裁定退役——
R5 迁移规划 W1/ADR-0634,集内无空 actor 行);:attr:`BoardState.write_seq`
升格为**版本 id**(每次写入单调分配,不重不漏,:meth:`BoardState.current_version`
读口);每次写入落一行**自足状态流水**(行 = 改了什么 + 渠道签名 + 版本 id +
写入后完整 state 快照,行行自足查询直接读——无快照锚/无对账自检/无前溯推导,
禁回归)。落盘由 :mod:`sr_od.application.currency_war.kernel.cw_state_journal`
承载,**无条件常开**(生产装配单点 = currency_war_app 装配段,无开关;行落盘
另以 sink 在场与 run_id 在场为准,sink 缺席 = 行不落而写路径照常——记录被动,
不改写路径语义)。新增**逻辑态
派生域与画面上下文域**(ADR-0630 决策 1+修订节 2;字段面 as-built =
``docs/develop/currency_war/game_state/node-domain.md`` §2):``prev_screen``/``current_screen``
(①观察汇聚写)+ ``top_bar_raw``(顶栏原文,**观察层**,observe() 只落原始
读数)+ ``node_ord``(**逻辑层序键**,派生规则唯一写点;用户终裁 2026-09-11
字段层次终极版:观察层只放画面原始读数,序键是逻辑层字段,四条腿全部
write_logic,无 observe 写序键的例外)。
四规则组:①备战腿顶栏权威/②位面过渡腿 0q→(plane+1,1)/③BOSS简报腿
0p→当前+1+boss 类型/④弹窗腿守卫族;推进去重键 =(run_id, effective_ord),
类型派生 = 专属画面直定+未定型查链预留)。本段持久正本 =
``docs/develop/currency_war/decisions/0630-unified-state-journal.md``
(ADR-0630,含修订节:守卫族终版/单字段双值结构/字段层次终极版;设计
工作稿存 .debug/temp 为易失档,禁作正本指针)。派生规则判定本体单一源 =
场景一判定方案(现行版次以文件头为准;该档不入 git,持久裁定锚 = ADR-0630
关联行与 ``docs/game/currency_war/research/screen_flow_timing.md``
#26/#14/#27)。
"""
from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import json
import subprocess
import time
import weakref
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    ActiveEffectInventory,
)
from sr_od.application.currency_war.kernel.cw_registry import DEFAULT_REGISTRY

if TYPE_CHECKING:
    # 仅类型注解引用(项目规范);运行时按鸭子类型读 GameState 属性,
    # 避免与 cw_state 建立运行时依赖(cw_state 将来消费本模块时不成环)。
    from sr_od.application.currency_war.kernel.cw_state import GameState


# ============================================================ 常量

#: 备战席容量默认恒 9,不随等级/职级变化(§3.2.5;现役同口径常量 =
#: ``cw_state.BENCH_CAPACITY``)。唯一改写源 = 节省工位时限效果(激活期 3、
#: 3 节点后自动回 9,经效果账本 §5.1 逻辑写入)。
BENCH_CAPACITY_DEFAULT: int = 9

#: 行级 schema 版本(§3.7.1)。域版本映射见 ``DEFAULT_BS_SCHEMA``。
BS_SCHEMA_VERSION: int = 1

#: 域粒度版本映射的当前全集(缺域键 = 该域未建模,禁建「None=未建模」占位
#: 字段,§2.2/§8.8)。域增删或字段语义破坏性变更时 bump 对应域版本。
DEFAULT_BS_SCHEMA: dict[str, int] = {
    'node': 1,              # node/node_path(§3.2.1/§3.2.2)
    'units': 1,             # front_row/back_row/bench/back_layout(§3.2.3-§3.2.7)
    'economy': 1,           # gold/level/xp/streak/hp/level_up_cost(§3.2.9-§3.2.13)
    'match_facts': 1,       # 职级/对局类型/敌人难度/boss/词缀/环境/持卡/board(§3.1/§3.2.6/§3.2.14/§3.2.20)
    'refresh_counters': 1,  # 商店刷新计数组(§3.3.6-§3.3.9,写入=仅逻辑)
    'node_screen_refresh': 1,  # 节点屏刷新计数组(§3.4.1-§3.4.4;遭遇/补给/环境/策略逐卡)
    'inventory': 1,         # equips/consumables/免战牌(§3.2.15/§3.2.16/§3.2.19〔勘误:免战牌正本=effect_inventory.remaining_uses,§8.6-3——本域不含其字段〕)
    'spheres': 1,           # 奖励球(§3.2.8,不占席)
    'substate': 1,          # 分类子态/事件浮层(§3.2.17/§3.6.1)
    'shop': 1,              # 商店开态 payload(§3.3)
    'encounter': 1,         # 遭遇屏 payload(§3.4.1)
    'supply': 1,            # 补给屏 payload(§3.4.2)
    'event_choices': 1,     # 十事件屏 chosen_*(§3.4/§4 事件选择)
    'settlement': 1,        # 结算真值组 + hp 保底事件位(§3.5)
    'effects': 1,           # 在场效果激活账本(§5.1,非 Field 载体)
    'derivation': 3,        # 逻辑态派生域与画面上下文域(R1 §3.1.4;域版本 3 =
                            # 字段层次终极版:node_ord 纯逻辑层四腿 write_logic、
                            # 新增顶栏原文观察层字段 top_bar_raw,用户终裁
                            # 2026-09-11;历史:1=R1 双腿双字段,2=单字段双层)
    'receipts': 1,          # 动作回执域(R2 §3.1.1-4/§3.2.5:普通 Field 域滚动窗,唯一写点 = note_action_receipt)
    'match_final': 1,       # 局终域(R5 W2;§3.6.1 runs 收编载体:一段一行,
                            # 恢复局跨段 = 多行,game 级聚合取段序末行;唯一
                            # 写点 = write_match_final,actor=MatchClose)
}

#: 画面附加域(§2.2 显式例外):语义 = 「当前画面的 payload,非当前画面
#: =None」——离开画面置 None 是结构事实非失读,不受 carried 硬边界辖。
_PAYLOAD_DOMAINS: frozenset[str] = frozenset({'shop', 'encounter', 'supply'})


# ---- 画面上下文域常量(R1 §3.1.4/§3.4;派生规则输入面)----

#: 干净备战帧画面标识(画面建档 screen_name;备战腿触发面)。
SCREEN_PREP_FRAME: str = '货币战争-备战'

#: 弹窗族清单(R1 §3.4.1 规则一;成员照搬判定方案 R3 §3.3 规则一四类:
#: 遭遇/投资策略/补给/商店面板——「按下一节点类型自动弹」中有独立分发分支
#: 的四类;巨星/祈愿非节点边界标记不入清单,R3 §5-③.1 残留申报)。
SCREEN_CONTEXT_POPUP_FAMILY: frozenset[str] = frozenset({
    '货币战争-遭遇节点',
    '货币战争-投资策略',
    '货币战争-补给',
    '货币战争-备战-开商店',
})

#: 弹窗腿守卫集(§3.4.1 规则四;语义 = 「本节点备战帧未被分派过」的画面侧
#: 判据。**成员终版 = 结算窗 ∪ 开局链,0p/0q 出族**(用户终裁 2026-09-11,
#: 攻击 R5 高-1:守卫族残留 0p/0q 会与专用腿②③构成级联双推进——专用腿推进
#: 后弹窗腿再 +1,节点键控整段偏移;弹窗腿缓存守卫只是掩码,不是结构防线)):
#: - ``BATTLE_WAIT_CONTEXT`` = 战斗/结算窗段内相位 token(R3 的「战斗等待」
#:   分支——段内多物理屏,观察阶段键 battle_or_transit 无法细分到建档名,
#:   按分支级记录,边界申报见值注释);
#: - 开局链成员 = 简报/投资环境/等待 1-1(0r/0s 写点 = cw_loop 分派分支的
#:   分支标识写入,R2 开局链写点)+ 等待 1-1(投资环境后的开局补给动画等待
#:   段,无独立画面建档——分支级 token 同 ``BATTLE_WAIT_CONTEXT`` 变体;
#:   判定方案 §3.6 S1 形态判据:等待期商店面板先被采到 → 弹窗腿开局候选);
#: - **出族成员申报**:``货币战争-BOSS简报``(0p)与 ``货币战争-位面过渡``
#:   (0q)各有确定性专用腿(本模块规则③/②),自身推进不依赖弹窗腿,作为
#:   prev 也不得再触发弹窗腿(R1.1 曾以 E12 边序勘误把 0p 列入本族,随规则③
#:   落码出族;boss 流真序 = 奖励关结算 → 0p 简报 → 商店自动开,
#:   screen_flow_timing.md #26/#14/#27 不变)。
BATTLE_WAIT_CONTEXT: str = '货币战争-战斗等待'
SCREEN_CONTEXT_GUARD_PREV: frozenset[str] = frozenset({
    BATTLE_WAIT_CONTEXT,
    '货币战争-简报',
    '货币战争-投资环境',
    '货币战争-等待1-1',
})

# ---- 确定性腿触发面与类型派生映射(R1.2,§3.4.1 四规则组终版)----

#: 位面过渡画面标识(0q;规则②触发面。写点 = cw_loop 分支分支标识写入
#: 「点击空白处继续」判定;0q 不入弹窗守卫族,出族申报见
#: SCREEN_CONTEXT_GUARD_PREV 值注释)。过渡屏链 = 离开位面链
#: (件 B 设计 v1.1 §3.1.1 F1 定谳)——下位面节点类型不可自定,本屏只供
#: 规则②节点推进,零类型写。
SCREEN_PLANE_TRANSITION: str = '货币战争-位面过渡'

#: BOSS 简报画面标识(0p;规则③触发面,写点 = cw_loop 0p 分支「强敌来袭」
#: 判定;亦为弹窗腿守卫族成员——成员面申报见上,规则③落码后推进来源 =
#: 本屏自身,守卫成员降为次序无关的语义申报)。
SCREEN_BOSS_BRIEFING: str = '货币战争-BOSS简报'

#: 类型派生·专属画面直定映射(§3.4.1 类型派生;键 = 画面标识,值 = 节点
#: 类型 token)。值词表与备战帧链读链(obs ``_NODE_TYPE_KEYWORDS``)及 sim
#: 引擎类型池同源,禁新造 token。**商店面板块不入本映射**——商店对任意
#: 节点类型都开(非专属)→ 类型「未定型」零直定写;查现行链按件 B 设计
#: v1.1 §3.4 ``chain_node_type`` 语义预留(:func:`chain_node_type`),查链
#: 接线归件 B 实施批。目标节点坐标系 = 专属屏所属节点(弹窗族屏 = 即将
#: 进入的节点,0p = 简报所报的下一节点)。
SCREEN_NODE_TYPE_DIRECT: dict[str, str] = {
    SCREEN_BOSS_BRIEFING: 'boss',
    '货币战争-补给': 'supply',
    '货币战争-遭遇节点': 'encounter',
    '货币战争-投资策略': 'invest',
}


def node_ordinal_of(plane: int, round_num: int) -> int:
    """节点序 = (plane-1)*9 + round_num(基 1;坐标系与效果账本 advance_node
    去重键同源,判定方案 R3 §3.2 身份键)。"""
    return (int(plane) - 1) * 9 + int(round_num)

#: 帧观察完整度三档(§2.4 关键结构 2)。
FrameObsLevel = Literal['full', 'view', 'none']

#: 来源四分类字面量(§2.1)。
FieldSource = Literal['observation', 'logic', 'carried', 'prior']

#: sim 合成口统一 evidence 标记(§2.1:sim 侧真值合成恒带)。
SIM_SYNTHESIZED: str = 'sim:synthesized'


# ============================================================ 渠道签名(R1 统一写入口)

#: 渠道族封闭集(设计 §3.2.1;裁定 1 的三写入源,集外值 = 红):
#: obs = 画面 op 观察 / logic_action = 动作 op 逻辑计算 / logic_hook = 流程
#: hook 驱动的逻辑计算(含节点推进派生规则)。carried/prior/synthesized 不是
#: 第四源,是 obs 族内的来源子模(由 mode 承载)。
CHANNEL_FAMILIES: tuple[str, ...] = ('obs', 'logic_action', 'logic_hook')

#: obs 族子模词表(§3.2.1 mode):真读 / 失读沿用 / 开局先验 / sim 真值合成。
OBS_MODES: tuple[str, ...] = ('read', 'carried', 'prior', 'synthesized')

#: obs_event 事件词表封闭集(§3.2.3 行型 2:arbitrate=拒读/仲裁拒绝留证 /
#: miss=失读留证 / popup=弹窗类流程异常留证)。集外值 = 红(硬约束 2 同纪律:
#: 事件面漂移要在登记点暴露,禁自由串)。
OBS_EVENT_EVENTS: tuple[str, ...] = ('arbitrate', 'miss', 'popup')

#: logic 两族子模:恒 compute(逻辑计算,无观察质量语义)。
LOGIC_MODES: tuple[str, ...] = ('compute',)

#: actor 登记面在册名(§3.2.1:显式 sig 的写入者须在册,登记式封闭集防自由
#: 串漂移;未来流程 hook 系统的写入者随其登记面申报——写入口只校验在册,
#: 零接口预留)。R5 W1 起写入口签名必填(影子期「无 sig 调用」的合成签名
#: 过渡路径已退役,ADR-0634),全部行 actor 在册非空。
REGISTERED_ACTORS: set[str] = {
    'cw_observation',          # 观察汇聚模块(read_game_state 唯一漏斗)
    'cw_back_layout',          # 后排布局选档(back_layout 观察写端:三信号
                               # 裁决值经 resolve_back_slots 收尾落容器)
    'obs_conflict',            # 观察冲突仲裁汇点(obs_conflict 证据行型 2)
    'CwScreenPrep',            # 备战画面 op(reconcile 核对口观察写入)
    'CwScreenBattleWait',      # 战斗/结算画面 op(结算覆盖写端,§3.5.1)
    'CwScreenBookcard',        # 星徽秘典弹窗(chosen_tome 选择写点)
    'CwScreenEncounter',       # 遭遇弹窗(chosen_encounter/刷新计数写点)
    'CwScreenExpertInvite',    # 专家邀约(chosen_expert 选择写点)
    'CwScreenInvestEnv',       # 投资环境(active_env 选择写点)
    'CwScreenInvestStrategy',  # 投资策略(active_strategies/刷新计数写点)
    'CwScreenMegastar',        # 盛会之星(chosen_megastar 选择写点)
    'CwScreenPartner',         # 伙伴选择(chosen_partner 选择写点)
    'CwScreenSupplyNode',      # 补给(chosen_supply 选择写点)
    'CwScreenWishTrial',       # 祈愿试炼(chosen_wish 选择写点)
    'derive_node_inferred',    # 派生规则·弹窗腿(§3.4.1 规则一)
    'derive_node_observed',    # 派生规则·备战腿(§3.4.1 规则二)
    'derive_node_plane_transition',  # 派生规则·位面过渡腿(§3.4.1 规则二·R1.2)
    'derive_node_boss_brief',        # 派生规则·BOSS简报腿(§3.4.1 规则三·R1.2)
    'derive_node_type',              # 派生规则·类型直定(§3.4.1 类型派生·R1.2)
    'ResumeAttach',            # 接管协议(载体中继登记名,§3.2.4)
    'MatchClose',              # 局终收口(局终域写点,接线归后续批)
    'synthesize_from_game_state',  # sim 合成口(§2.1)
    # —— R2 动作 op 写入接线(渠道② logic_action,§3.2.1 登记类属 =
    # 「动作 op / handler 类名」;actor = 执行动作的 op 类,动作身份由
    # 回执记录 op 字段承载)——
    'PrepActionExecutor',      # 备战动作执行器(动作全集唯一分派点)
    'CwOpBuyCards',            # 商店单动作循环(run_buy_waves;含刷新执行
                               # 事实组 record_refresh_execution 的计数写入)
    'CwOpOpenShop',            # 开商店原子(op 函数与独立壳同名登记)
    'CwOpCloseShop',           # 关商店原子
    'CwLoop',                  # 外循环(开局链分支标识写点,obs 族 ①)
    'EffectLedgerBridge',      # 效果账本→字段桥(容量投影/增额授予;v3.2-G4
                               # §3.2.1 登记类属补项;R5 W1 起显式签名)
}


def register_sig_actors(*names: str) -> None:
    """登记新的写入者名(登记面扩面唯一入口;重复登记幂等)。"""
    REGISTERED_ACTORS.update(names)


def actor_registered(name: str) -> bool:
    """actor 是否已登记(测试与诊断用;写入口校验走 :func:`_validate_sig`)。"""
    return name in REGISTERED_ACTORS


def _journal_emit(row: dict) -> None:
    """状态流水行外送(写入口共用;缺省关 + 局外拒写 + best-effort)。"""
    sink = _STATE_JOURNAL_SINK
    if sink is None:
        return
    try:
        if not _current_run_id_safe():
            return   # 局外写入拒绝(§3.2.3):不写假行,诚实缺失
        sink(row)
    except Exception as e:  # noqa: BLE001  记录层 best-effort,不毒化写入链
        log.debug(f'[cw-bs] journal row skip: {e}')


def _validate_sig(sig: ChannelSig, allowed_families: tuple[str, ...]) -> None:
    """显式签名的写入口校验(§3.2.4 硬约束 2):渠道族须匹配该 API 的合法族、
    actor 须在册;违反显式炸错(禁静默收下——渠道面漂移要在写点暴露)。"""
    if sig.family not in allowed_families:
        raise ValueError(
            f'渠道族 {sig.family!r} 不属本写入口合法族 {allowed_families}'
            f'(§3.2.4 硬约束 2 渠道封闭集)')
    if sig.actor not in REGISTERED_ACTORS:
        raise ValueError(
            f'actor {sig.actor!r} 未登记(register_sig_actors 申报;§3.2.4 '
            f'硬约束 2 登记面在册校验)')


@dataclass(frozen=True)
class ChannelSig:
    """渠道签名(§3.2.1):每次写入携带的「谁写的、从哪写的、质量如何」
    结构化标注,随状态流水行落盘。

    - family = 渠道族(:data:`CHANNEL_FAMILIES` 封闭集,构造期校验);
    - actor = 登记面在册的写入者名(:data:`REGISTERED_ACTORS`;显式 sig 经
      写入口在册校验,合成 sig 过渡期豁免);
    - screen = 画面标识(obs = 画面建档 screen_name;logic_hook = 关联画面;
      logic_action = None);
    - mode = 渠道族子模(obs 族 :data:`OBS_MODES` / logic 两族恒 compute,
      构造期校验);
    - quality = 字段级质量元数据(字段名 → 标记,承接现役 *_readable 语义:
      真读/兜底可分;词表起步面见设计 §3.2.1,扩面逐字段登记申报);
    - group_id = 一次逻辑计算打包的组标识(②= 'act:<op类名>@<seq>' /
      ③= 'hook:<写入者登记名>@<seq>';组内行同 group)。

    frozen = 行内 sig 不被事后改写(自足行即真相);quality dict 请勿就地
    变更(冻结只保引用位,纪律面约束)。
    """

    family: str
    actor: str
    screen: str | None = None
    mode: str | None = None          # None = 按 family 取缺省(obs→read/logic→compute)
    quality: dict[str, str] = field(default_factory=dict)
    group_id: str | None = None

    def __post_init__(self) -> None:
        if self.family not in CHANNEL_FAMILIES:
            raise ValueError(
                f'渠道族 {self.family!r} 集外(封闭集 = {CHANNEL_FAMILIES};'
                f'§3.2.1 硬约束 2)')
        if self.mode is None:
            object.__setattr__(
                self, 'mode',
                'compute' if self.family in ('logic_action', 'logic_hook')
                else 'read')
        legal = (LOGIC_MODES if self.family in ('logic_action', 'logic_hook')
                 else OBS_MODES)
        if self.mode not in legal:
            raise ValueError(
                f'mode {self.mode!r} 不属渠道族 {self.family} 的合法子模 '
                f'{legal}(§3.2.1 mode 词表)')

    def to_json(self) -> dict:
        """行内 sig 形态(键序固定,同态同形)。"""
        return {
            'family': self.family, 'actor': self.actor, 'screen': self.screen,
            'mode': self.mode, 'quality': dict(self.quality),
            'group_id': self.group_id,
        }

#: 字段值类型参数(Field 泛型;值域由各字段注解承载,运行期不做 isinstance
#: 门——观察值类型由写入端调用点保证)。
_T = TypeVar('_T')


# ============================================================ 字段容器


@dataclass(frozen=True)
class Field(Generic[_T]):
    """一个字段:值 + 来源 + 可选源注记。只存正式值——来源两态
    (observation/logic,ADR-0651;来源子模 carried/prior 见 §2.1)。

    - observation = 亲眼看到的(识别结果/sim 真值合成,evidence 恒带标记);
    - logic = 决策动作按游戏规则推算的预期效果,经
      :meth:`BoardState.write_logic` 直接写入(策略器立即可读),**保持
      logic 不翻 observation**(§8.1),直到下一次观察覆盖(失配 = 推算
      bug,缺陷台账留证,修推算代码);
    - carried = 沿用上次好值,evidence 必带 ``carried:<来源帧>``
      (§2.1/§2.2 失读处置①);
    - prior = 历史遥测先验(开局 hp,§3.1.6),evidence 必带 ``prior:<来源>``;
      仅限显式申报条目,禁扩散。

    frozen = 帧替换语义的结构保证(§2.4):写入只能经 BoardState API 以
    写时刻现引用为基底换新帧,禁原地改旧帧后跨耗时段写回。
    """

    value: Any | None = None
    source: FieldSource = 'observation'
    evidence: str | None = None


# ============================================================ 单位与槽位(§8.2)


@dataclass(frozen=True)
class Unit:
    """一个单位(前台/后台通用):角色带星级与装备。

    **阵营不存**(§3.2.3/§8.6-7):阵营是角色静态属性,由 char_id 查角色
    注册表(cw_chars)派生;唯一例外开拓者形态随排(前台=记忆/后台=欢愉),
    由 char_id+当前排推导(ADR-0158)。禁在 Unit 另存阵营(防注册表双源)。
    """

    char_id: str
    star: int                       # 星级 1..3(合成上限;观察期快照)
    equips: list[str] = field(default_factory=list)
    # [索引定义] slot = 屏幕槽位号,行内 1 基(前排 1..4/后排 X 槽 1..N/
    # 备战栏 1..9,坐标 = screen_info 区域);与现役 deployed 容器 0 基下标
    # (ADR-0392:0-3 前台/4-9 后台)的换算归迁移映射层(批次二)。
    # 取值时机 = 观察期快照。
    slot: int = 0


@dataclass(frozen=True)
class BenchSlot:
    """备战席一槽:四种内容之一(统一槽位视图,占位真值一份,§3.2.5)。

    占席真值 = :func:`slot_occupies`:unit/supply_box/tome 占 1 槽、empty
    不占(奖励球不占席——它是点击目标不是席位居民,§3.2.5)。sim 合成帧
    「箱不占席」= sim 无箱实体的内部口径约定,**记录模型按实机真值**。
    """

    kind: Literal['unit', 'supply_box', 'tome', 'empty'] = 'empty'
    unit: Unit | None = None        # kind='unit' 时有效
    # tome=星徽秘典:席位内容物之一,占席待实机证实(§3.2.5——画面档案只有
    # 弹窗、无席位区域锚);按「席位内容物」建模即占席,证伪时改归不占席域。


@dataclass(frozen=True)
class BenchView:
    """备战席统一槽位视图 = 槽位表 + 容量(§8.2 实现注意:capacity 随效果
    改写,默认恒 9;唯一临时改写 = 节省工位时限效果,§3.2.5)。

    槽位表按物理槽位 1..capacity 定位:slots[i] = 物理槽 i+1(0 基列表下标
    ↔ 1 基屏幕槽位,与现役 ``cw_state.bench`` 下标语义同构,ADR-0316)。
    席空数/席满判定 = 派生计算(:func:`bench_free_slots`/:func:`bench_is_full`),
    不入 schema(§8.8 字段准入③)。
    """

    slots: list[BenchSlot] = field(default_factory=list)
    capacity: int = BENCH_CAPACITY_DEFAULT


@dataclass(frozen=True)
class SphereSight:
    """奖励球观察面(§3.2.8):数量/颜色——交互机会信号,**不占席**。

    colors 为画面读取到的颜色标签元组(词表随识别线建线批定型,先以
    不透明字符串承载);count None = 未读到。
    """

    count: int | None = None
    colors: tuple[str, ...] = ()


# ============================================================ 节点与画面载荷(§8.3)


@dataclass(frozen=True)
class NodeKey:
    """当前节点坐标系(跨位面 round 重启,plane 必在键内,§3.2.1)。"""

    plane: int = 1
    # [索引定义] round_num = 位面内轮次,1 基(跨位面重启,与 plane 组成
    # 复合键);取值时机 = 备战帧节点条现读(权威写端,§3.2.1)。
    round_num: int = 1
    kind: str = 'prep'              # battle/encounter/supply/reward/boss/prep/…


@dataclass(frozen=True)
class ShopCard:
    """商店一张牌(§3.3.1)。

    升星预览不入存储——派生计算函数(bench/rows+注册表合成规则自算,
    merge_mechanics §2.7 口径);✦ 读取器读数仅核对信号(ADR-0416 降级)。
    牌位点击坐标不入存储——坐标单一真相源 = screen_info「商店牌-N」区域
    (cw_obs_core.shop_card_click_points)。
    """

    name: str = ''
    faction: str = ''
    cost: int = 0
    star: int = 1
    # 信源位(§3.3.1):**原值透传不折叠**(P2-4 落地审:证据分级禁丢)——
    # 词表 = 现役 GameState.ShopCard.cost_source 三值:badge=费用徽章直读 /
    # roster=注册表查表(sim/replay 构造缺省) / roster_fallback=徽章失读
    # 退查表。设计的两值口径(badge=徽章直读 vs registry=注册表查表)的
    # 归并消费归批次二,消费前必须保住 roster_fallback 的「徽章失读」分级。
    cost_source: str = 'badge'


@dataclass(frozen=True)
class ShopPayload:
    """商店开态附加(§3.3):五张牌与概率条。非当前画面 = None(§2.2 例外)。"""

    cards: list[ShopCard] = field(default_factory=list)            # 恒 5 张
    refresh_probs: dict[int, float] = field(default_factory=dict)  # 费用档→概率(§3.3.2 契约)


@dataclass(frozen=True)
class EncounterPayload:
    """遭遇屏附加(§3.4.1):分支选项。options = (难度档 1..6, 奖励文本)。"""

    options: list[tuple[int, str]] = field(default_factory=list)


@dataclass(frozen=True)
class SupplyPayload:
    """补给屏附加(§3.4.2):列数动态——通常4选1,效果改写3-5,勿写死(cw_node_obs.py:279-282)。options = (角色, 装备, 有钻石)。"""

    options: list[tuple[str, str, bool]] = field(default_factory=list)


@dataclass(frozen=True)
class Settlement:
    """结算屏真值组(§3.5.1):战斗后覆盖更新的数据源。

    伤害不入本结构——遥测面(字段准入①:无决策消费,设计 §3.5.1 明示);
    金仅胜局有值(败局结算屏无收入面板);等级/经验仅胜局结算页可读
    (cw_settlement_obs.py:118-135)。
    """

    hp_after: int | None = None
    streak_after: int | None = None                 # 带符号(§3.2.12)
    killed: bool | None = None
    progress_delta: int | None = None
    gold: int | None = None                         # 仅胜局(§3.5.1)
    level: int | None = None                        # 仅胜局结算页可读
    xp: int | None = None


# ============================================================ 局终域(§3.6.1 runs 收编载体;持久裁定锚 = ADR-0630 修订节)

#: 终局类型词表封闭集(retirement.md §2 runs 行:局终收口一行;收编映射 =
#: 现役 runs result 词表 win/loss/stopped + 非完结/无收口行 = abnormal)。
FINAL_WIN: str = 'win'
FINAL_LOSS: str = 'loss'
FINAL_STOPPED: str = 'stopped'
FINAL_ABNORMAL: str = 'abnormal'
MATCH_FINAL_TYPES: tuple[str, ...] = (
    FINAL_WIN, FINAL_LOSS, FINAL_STOPPED, FINAL_ABNORMAL)

#: 局终域字段名(行寻址键;判定面/装配器/判读读面同引此常量,禁散落字面量)。
MATCH_FINAL_FIELD: str = 'match_final'


def _resolve_code_commit() -> str:
    """主仓 git 短哈希(版本戳取值,模块导入时点解析一次)。

    best-effort 契约(同 telemetry/version_stamp.code_commit):非 git 环境/
    命令失败 = 返 '',不产错误值。仓库根按本模块位置向上定位(pyproject.toml
    锚),不用 cwd——server/GUI 工作目录不可信。
    """
    module_path = Path(__file__).resolve()
    repo = next((c for c in module_path.parents
                 if (c / 'pyproject.toml').is_file()), module_path.parents[4])
    try:
        r = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                           cwd=str(repo), capture_output=True, text=True,
                           timeout=5)
        if r.returncode == 0:
            return str(r.stdout).strip()
    except Exception:   # noqa: BLE001  版本戳观测 best-effort
        pass
    return ''


def _normalize_stamp_value(o: Any) -> Any:
    """递归规范化为可稳定 JSON 化的结构(指纹口径,与
    telemetry/version_stamp._normalize 逐位同语义——桶依赖矩阵禁
    kernel→telemetry import,就地复刻;等值性由局终锁对拍钉住):
    dataclass 转 dict(集合内成员 asdict 不递归,此处补)/dict 键 str 化并
    按键排序/set 先试原生排序、不可比退 JSON 串序(恒全序,default=repr
    兜住任意对象)/list·tuple 转 list。"""
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        return _normalize_stamp_value(dataclasses.asdict(o))
    if isinstance(o, dict):
        return {str(k): _normalize_stamp_value(v) for k, v in sorted(
            ((str(k), v) for k, v in o.items()), key=lambda kv: kv[0])}
    if isinstance(o, (set, frozenset)):
        elems = [_normalize_stamp_value(x) for x in o]
        try:
            return sorted(elems)
        except TypeError:
            return sorted(elems, key=lambda x: json.dumps(
                x, sort_keys=True, ensure_ascii=False, default=repr))
    if isinstance(o, (list, tuple)):
        return [_normalize_stamp_value(x) for x in o]
    return o


def _resolve_registry_fingerprint() -> str:
    """决策注册表内容指纹(sha256 前 12 位;注册表值变更即变)。

    「这局实际跑的参数」口径:追注册表现值不追 git 历史,工作区未提交改动
    也反映在指纹里。终 dumps 挂 default=repr 兜底——未识别对象序列化为
    repr 而非 TypeError(调用点在局终写口,指纹炸 = 终局行整行丢失)。
    """
    payload = json.dumps(
        _normalize_stamp_value(dataclasses.asdict(DEFAULT_REGISTRY)),
        sort_keys=True, ensure_ascii=False, default=repr)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:12]


#: 写入时点版本戳(正本 §3.6.1 runs 行「+ code_commit/registry_fingerprint
#: 版本戳,沿用 version_stamp」;runs 退役后 = 策略版本戳唯一在档载体,
#: 由 :meth:`write_match_final` 落账时填充)。模块级常量 = 进程导入时点
#: 解析一次,同进程跑的局戳一致;取值单一源语义 = telemetry/version_stamp,
#: 桶依赖矩阵禁 kernel→telemetry(sr-od-test test_cw_package_layout
#: .LEGAL_EDGES),故同口径就地落常量,与单一源的等值性由
#: test_cw_match_final::test_match_final_version_stamps 对拍钉住。
_CODE_COMMIT: str = _resolve_code_commit()
_REGISTRY_FINGERPRINT: str = _resolve_registry_fingerprint()


@dataclass(frozen=True)
class MatchFinal:
    """局终域行载荷(一段一行;恢复局跨段 = 多行,game 级聚合取段序末行)。

    - ``final_type`` = :data:`MATCH_FINAL_TYPES` 封闭集;abnormal = 异常终局
      (哨兵叫停/进程死亡等无正常收口路径的形态,**段内补写**落行——哨兵
      收口兜底路径按段尾账面补写,``backfilled`` = True + 行注记
      ``recovered`` 显影,判读按注记区分真伪,§3.6.1 runs 行 G8 谓词;
      启动扫描的**历史段**补写不经本载荷的运行时写口,走专用装配通道,
      遥测正本 §3.2.2 规则 6②);
    - ``at_version`` = 本行自身版本 id(:meth:`write_match_final` 装配时点
      即将分配的 write_seq,与行头 ``v`` 恒等——终局时点的账面版本锚);
    - ``code_commit``/``registry_fingerprint`` = 写入时点版本戳(§3.6.1
      runs 行「沿用 version_stamp」:跑这局的代码版本 + 决策注册表内容
      指纹;模块级常量 :data:`_CODE_COMMIT`/:data:`_REGISTRY_FINGERPRINT`,
      进程内恒定)——runs 退役后策略版本戳的唯一在档载体;
    - 终局快照七读数(level/hp/gold/streak/plane/round_num/node_kind)= 写入
      时点各域现值直读入载荷;字段级来源注记**随快照行自带**(行内嵌完整
      state + 逐字段 prov,§3.2.3 来源注记面),本结构不重复携带;
    - ``duration_s`` = 段级对局时长(容器创建 → 局终判定;恢复局跨段 = 各段
      各行,跨段总时长由判读侧按段序聚合,禁在行内猜)。
    """

    final_type: str
    at_version: int
    code_commit: str = ''
    registry_fingerprint: str = ''
    plane: int | None = None
    round_num: int | None = None
    node_kind: str | None = None
    level: int | None = None
    hp: int | None = None
    gold: int | None = None
    streak: int | None = None
    duration_s: float | None = None
    backfilled: bool = False
    cw4_counters: dict[str, int] | None = None
    # 策略行为观测计数局终聚合(R5 W4 键收编载体,ADR-0650;键全集登记
    # 单一源 = 封闭锁 sr-od-test test_cw4_key_closure,底稿 = W4 逐键审计
    # 256 字面+16 闭族+9 开放族,全部=策略行为键,零效果域键)。取值 =
    # 调用方收口时点自策略 state 容器(mandate_v1 MandateState.cw4_counters)
    # 现读;写口落载荷时浅拷贝一份(本结构不持有容器引用,后写不串)。
    # None = 无策略载体/历史段补写无源(诚实缺省,判读按「无计数载体」
    # 分型);空 dict = 局内真实零计数——两型可辨,沿旧流装配语义
    # (match_archive v7 顶层字段同一分型契约,该流面已随 W4 退役)。
    # 旧档案局终行缺本键 = W4 前数据,按缺键读。


# ============================================================ 缺陷台账挂点(§2.3)

#: 缺陷行缓冲(进程内,供装配点取走/测试断言);容量截断防长局堆积。
_DEFECT_BUFFER: list[dict] = []
_DEFECT_BUFFER_CAP: int = 200
#: 逐行外送钩子(生产装配点接遥测;**缺省关** = 只缓冲不外送——测试纪律
#: 「缺省关+显式接通」,生产武装点挂迁移批次二装配面)。
_DEFECT_SINK: Callable[[dict], None] | None = None


def set_defect_sink(fn: Callable[[dict], None] | None) -> None:
    """注入缺陷台账外送钩子(None = 关,缺省态;注入槽模式)。"""
    global _DEFECT_SINK
    _DEFECT_SINK = fn


def consume_defect_sink() -> list[dict]:
    """取走并清空缺陷行缓冲(装配点消费口;防跨局残留)。"""
    rows = list(_DEFECT_BUFFER)
    _DEFECT_BUFFER.clear()
    return rows


def _emit_defect(*, field_name: str, expected: Any, actual: Any,
                 evidence: str | None,
                 kind: str = 'observe_vs_logic_mismatch') -> None:
    """缺陷台账留证(§2.3 观察赢):观察覆盖 logic 值失配 = 推算 bug,
    留证后修推算代码(ADR-0651;不做运行时挂账对账)。best-effort:
    外送钩子异常不阻塞观察主链。"""
    row: dict = {'kind': kind, 'field': field_name,
                 'expected': expected, 'actual': actual,
                 'observed_evidence': evidence}
    _DEFECT_BUFFER.append(row)
    if len(_DEFECT_BUFFER) > _DEFECT_BUFFER_CAP:
        del _DEFECT_BUFFER[:len(_DEFECT_BUFFER) - _DEFECT_BUFFER_CAP]
    if _DEFECT_SINK is not None:
        try:
            _DEFECT_SINK(dict(row))
        except Exception as e:  # noqa: BLE001  留证 best-effort
            log.debug(f'[cw-bs] defect sink skip: {e}')
    log.warning(f'[cw!][bs] 观察覆盖 logic 失配:{field_name} '
                f'预期[{expected}] 实读[{actual}](§2.3 观察赢)')


# ============================================================ 状态流水 sink(R1 §3.2.3)

#: 状态流水外送钩子(进程内单槽;行落盘的在场门——journal 本体无条件常开
#:(R5 W1/ADR-0634:无开关,生产装配单点 = currency_war_app 装配段),本槽
#: 缺省 None 只表示「无落盘实例」(单元测试/工具环境),此时**写路径照常
#:(Field 写入与版本分配不受影响),仅行不外送**——记录被动,不分支行为。
#: 落盘实现与装配口 =
#: :mod:`sr_od.application.currency_war.kernel.cw_state_journal`)。
#: 槽契约:接收一行完整行 dict(自足快照行,§3.2.3),自担序列化/缓冲/落盘。
_STATE_JOURNAL_SINK: Callable[[dict], None] | None = None

#: run 归属供给槽(依赖倒置:kernel 禁依 telemetry——桶依赖矩阵锁
#: sr-od-test test_cw_package_layout.LEGAL_EDGES;行内 run_id 由装配点注入
#: 读取函数,生产武装点 = currency_war_app 装配段传 telemetry 现读口)。
_RUN_ID_PROVIDER: Callable[[], str] | None = None


def set_state_journal_sink(fn: Callable[[dict], None] | None) -> None:
    """接通/复位状态流水外送钩子(None = 无落盘实例,缺省态;同
    :func:`set_defect_sink` 注入槽模式)。生产装配单点 = currency_war_app
    装配段(经 ``cw_state_journal.install_state_telemetry``,无条件常开)。
    本槽不是行为开关:sink 缺席 = 行不落,Field 写入与版本分配照常。"""
    global _STATE_JOURNAL_SINK
    _STATE_JOURNAL_SINK = fn


def set_run_id_provider(fn: Callable[[], str] | None) -> None:
    """注入 run 归属读取函数(None = 关;缺省态 = 视为局外全拒写——不写假行)。"""
    global _RUN_ID_PROVIDER
    _RUN_ID_PROVIDER = fn


def _current_run_id_safe() -> str:
    """run 归属现读(经供给槽;槽缺席/读取失败 = 视为局外,拒写假行)。"""
    if _RUN_ID_PROVIDER is None:
        return ''
    try:
        return str(_RUN_ID_PROVIDER() or '')
    except Exception:   # noqa: BLE001  归属读取失败 = 视为局外(拒写假行)
        return ''


# ============================================================ 派生计算(不存储)


def slot_occupies(kind: str) -> bool:
    """槽位占席谓词(§3.2.5 实机真值):unit/supply_box/tome 占 1 槽,
    empty 不占。席满判定/席空数同源派生的底座。"""
    return kind != 'empty'


def bench_free_slots(bs: BoardState) -> int | None:
    """席空数(§3.2.5 派生计算,不入 schema)。bench 从未观察 → None
    (= 不确定,**禁猜 0**);已观察 → max(capacity − 占席槽数, 0)。"""
    view = bs.bench.value
    if view is None:
        return None
    used = sum(1 for s in view.slots if slot_occupies(s.kind))
    return max(view.capacity - used, 0)


def bench_is_full(bs: BoardState) -> bool | None:
    """席满判定 = 同源派生(席空数==0,§3.2.5;含商店开态满栏买牌判定)。
    bench 未观察 → None(不确定);「备战席已满」警告 OCR 不做识别
    (玩家裁定 2026-09-09,现役 read_bench_full 通道退役挂批次二)。"""
    free = bench_free_slots(bs)
    return None if free is None else free == 0


def board_next_tier_of(board_factions: dict[str, int]) -> dict[str, int]:
    """board 下档阈值派生(§3.2.6/§8.8 准入③:计算函数不存储)。

    语义 = 左面板「X/Y」的 Y:对注册表 ``FACTIONS[].tiers`` 取 >当前人数
    的最小档,无更高档不计入。**本函数 = 该推导的 kernel 单一源**——
    迁移批次二起,obs computed 支(cw_observation read_game_state)与
    sim 观测键(engine_p1._board_next_tier_of,ADR-0488 硬依赖键供给)
    均委托至此,禁第三份推导(sim 侧旧注释「与 obs computed 支同一式」
    的对齐义务由委托结构保证)。
    """
    from sr_od.application.currency_war.data.cw_factions import FACTIONS
    out: dict[str, int] = {}
    for _f, _c in board_factions.items():
        _tiers = FACTIONS[_f].tiers if _f in FACTIONS else ()
        _nt = next((t for t in _tiers if t > _c), 0)
        if _nt:
            out[_f] = _nt
    return out


# ============================================================ cost_source 三值归并(§3.3.1/§8.6-9)

#: cost_source 消费词表二值(§3.3.1):badge=徽章直读 / registry=注册表查表。
COST_SOURCE_BADGE: str = 'badge'
COST_SOURCE_REGISTRY: str = 'registry'


def cost_source_group(cost_source: str) -> str:
    """cost_source 三值 → 消费二值归并(§8.6-9,迁移批次二)。

    存储侧保三值不折叠(roster_fallback 的「徽章失读」证据分级禁丢,
    P2-4 落地审);消费侧归并 = 对**费用数值**的可信度只分两域——badge
    徽章直读与 registry 注册表查表(含 roster_fallback 失读退查)给出的
    都是角色招募费真值,按费用消费的分支(估价/卖价/合成费用档)无需
    区分后两者。归并不丢证据:原值仍在 :attr:`ShopCard.cost_source`,
    失配归因/缺陷台账按原值分档。未知值保守归 registry(与 reader 缺省
    语义同向;词表外值 = 上游漂移信号,归因时看原值)。
    """
    return COST_SOURCE_BADGE if cost_source == COST_SOURCE_BADGE \
        else COST_SOURCE_REGISTRY


# ============================================================ 双 ShopCard 映射单一源(W5 类型去重)
# 方案正本 = docs/develop/sr_od/application/currency_war/changes/
# 2026-09-06-redesign/w5-透传域建模方案.md §2.5:唯一容器类型 =
# :class:`ShopCard`(本模块);旧容器版(cw_state 侧同名类,带点击坐标 x
# 与 merge_preview)随 W8 GameState 本体退役波消亡,过渡期两类型并存合法、
# **转换只许在本节两个映射函数发生**(喂入面/合成口/消费视图/合成引擎
# 统一经此,禁散落内联转换——双源漂移温床)。本节 = kernel 内旧类型的
# 唯一合法引用面(静态锁辖域,测试锁 test_cw_w5_* 守)。

def shop_card_to_container(card) -> ShopCard:
    """旧容器牌 → 容器牌(喂入口/sim 合成口的值构造单一源)。

    字段映射(name/faction/cost/star/cost_source)原值透传不折叠;
    x/merge_preview 是旧版独有的执行/读取器域字段,容器不入存储
    (坐标单一真相源 = screen_info;merge_preview = 派生核对信号)。
    """

    return ShopCard(name=str(getattr(card, 'name', '') or ''),
                    faction=str(getattr(card, 'faction', '') or ''),
                    cost=int(getattr(card, 'cost', 0) or 0),
                    star=int(getattr(card, 'star', 1) or 1),
                    cost_source=str(getattr(card, 'cost_source', '')
                                    or 'roster'))


def shop_cards_to_legacy(cards: list[ShopCard],
                         frame_cards: list | None = None) -> list:
    """容器牌列表 → 旧容器牌列表(消费视图/合成引擎边界的值构造单一源)。

    - 五记录字段(name/faction/cost/star/cost_source)自容器透传;
    - ``x``(点击坐标)置 0 不消费:决策消费不用坐标,执行侧 buy 发射
      从 screen_info「商店牌-N」区域现取(黑板帧链自持 x,不经本函数);
    - ``merge_preview`` 不转换(派生计算不入存储,✦ 读取器降级核对
      信号的消费方自算或吃同帧 raw);
    - ``frame_cards`` = 同帧 raw 牌列表(可选):长度一致时按下标对齐
      透传 x/merge_preview 两执行/读取器域字段——容器 payload 与 raw 帧
      出自同一观察帧时序(喂入口保序),失配窗(失读帧/跨帧)置缺省 0,
      语义申报 = 执行域字段引导窗,不影响记录值。

    :param cards: 容器牌列表(:attr:`ShopPayload.cards`);
    :param frame_cards: 同帧 raw 牌(旧容器 ShopCard)列表或 None。
    """
    from sr_od.application.currency_war.kernel.cw_state import (
        ShopCard as _LegacyShopCard,
    )
    out: list = []
    n = len(cards)
    aligned = (frame_cards is not None and len(frame_cards) == n)
    for i, c in enumerate(cards):
        fr = frame_cards[i] if aligned else None
        out.append(_LegacyShopCard(
            x=int(getattr(fr, 'x', 0) or 0) if fr is not None else 0,
            faction=str(c.faction or ''),
            name=str(c.name or ''),
            cost=int(c.cost or 0),
            star=int(c.star or 1),
            merge_preview=int(getattr(fr, 'merge_preview', 0) or 0)
            if fr is not None else 0,
            cost_source=str(c.cost_source or 'roster')))
    return out


# ============================================================ 刷新执行事实组(§3.3.5-§3.3.9)

def record_refresh_execution(bs: BoardState, *, free: bool,
                             frame: str = '') -> None:
    """RefreshShop op 执行回执 → 刷新计数组逻辑写入(§3.3.6-§3.3.8,
    写入=仅逻辑;接线点 = cw_op_buy_cards 执行落地门,迁移批次二)。

    行为口径(§4 RefreshShop 行为申报配套):
    - total_refresh_count 恒 +1(§3.3.8:付费+免费全量);
    - free=True(免费帧):**不写** paid_refresh_count(§3.3.7 该键=付费
      累计,长线利好触发载体,免费帧混入即计数毒化)并消耗免费余额
      (§3.3.6 余额 −1,下限 0);
    - free=False:paid_refresh_count +1;
    - 计数从未写过(值 None)按 0 基线起算——计数器是局内单调累计,
      0 基线是构造事实非观察兜底(与「禁兜底改值」的观察域无关)。

    免费判定输入 = 调用方(执行侧按免费余额/效果账本判定后传入;
    余额未建模局恒 paid = 现状保守形态,行为与接线前逐位一致)。
    frame = 轮键留证(写入 evidence)。
    """
    _ev = f'refresh_exec@{frame}' if frame else 'refresh_exec'
    # 渠道②签名(§3.2.1:actor = 执行动作的 op 类名;组 id = 同一次刷新
    # 执行的三笔计数写共享 act 组;R5 W1 起签名必填,ADR-0634)。
    _sig = ChannelSig(family='logic_action', actor='CwOpBuyCards',
                      mode='compute',
                      group_id=f'act:CwOpBuyCards@{bs.write_seq + 1}')
    total = bs.total_refresh_count.value or 0
    bs.write_logic(bs.total_refresh_count, int(total) + 1,
                   produced_by='RefreshShop', evidence=_ev, sig=_sig)
    if free:
        balance = bs.free_refresh_balance.value or 0
        bs.write_logic(bs.free_refresh_balance, max(int(balance) - 1, 0),
                       produced_by='RefreshShop', evidence=_ev, sig=_sig)
    else:
        paid = bs.paid_refresh_count.value or 0
        bs.write_logic(bs.paid_refresh_count, int(paid) + 1,
                       produced_by='RefreshShop', evidence=_ev, sig=_sig)


# ============================================================ 动作回执域(R2 §3.1.1-4/§3.2.5)

#: 动作回执滚动窗容量(§3.1.1-4:有界列表,先进先出;容量 8 = 单节点动作
#: 批的量级上界,失败可见性窗——回执蒸发窗下限,过窗历史归流水行行自足)。
RECEIPTS_WINDOW_CAP: int = 8


def board_state_from_ctx(ctx: object) -> BoardState | None:
    """ctx → 局 BoardState(cw_match.session 旁表现读;无局/解析失败 = None)。

    动作 op 写入点的统一供给口(R2):调用方零判空负担——无局(独立跑/
    测试桩)静默 None,写入点自行跳过。"""
    try:
        match = getattr(ctx, 'cw_match', None)
        session = getattr(match, 'session', None) if match is not None else None
        if session is None:
            return None
        return board_state_of(session)
    except Exception:   # noqa: BLE001  供给口不炸调用链
        return None


def note_action_receipt(bs: BoardState, *, op: str, applied: bool,
                        reason: str = '', detail: str = '',
                        screen: str = '',
                        actor: str, extra: dict | None = None) -> None:
    """动作执行回执写入(receipts 域**唯一写点**,渠道② logic_action;
    §3.1.1-4/§3.2.5:各动作 op 执行回执处的普通 ``write_logic`` 写入)。

    - **发出即簿记,不是验证**(M1③ 用户裁定):``applied`` = 动作 op
      自身「是否发出」的机械事实透传,本口零成败判定——禁读屏核验、禁
      落地推断(落地判定归观察侧 reconcile);失败动作也产行(applied=
      false + reason),exec_events「正在蒸发的失败数据」教训的收编位;
    - 回执记录 = ``{op, applied, reason, detail?, screen?, **extra}`` 普通
      字典:op = 动作 op 名(类型名,exec_events 动作族承接);reason =
      未发出/受阻原因码('' = 正常发出);detail = 机械执行摘要(做了什么
      的人读面,恒透传);extra = 执行面结构化字段(plan_truncated/
      refresh_skipped/blocked 等,§3.2.1 质量词表执行面);
    - 滚动窗 = :data:`RECEIPTS_WINDOW_CAP` 条先进先出,整窗帧替换写入
      (普通 Field 域,非专用行机制,E3);窗序 = 写入序,同态同形;
    - 渠道签名:family=logic_action + actor(登记面在册,§3.2.1 ②类属 =
      执行动作的 op 类名)+ group_id = ``act:<actor>@<seq>``(§3.2.1 ②
      组标识格式);sig.screen 恒 None(逻辑计算无画面),画面桶由回执
      记录 screen 字段承接(exec_events 词表);
    - **常开化后的落盘语义**(R5 W1 影子闸折叠,ADR-0634):回执写入无条件
      (journal 常开,记录被动不分支);行落盘另以 sink 在场与 run_id 在场
      为准(无落盘实例/局外 = 行不落而回执域照常入账)。best-effort:异常
      不阻塞动作链(记录层故障不毒化执行)。
    """
    try:
        receipt: dict = {'op': str(op), 'applied': bool(applied),
                         'reason': str(reason or '')}
        if detail:
            receipt['detail'] = str(detail)
        if screen:
            receipt['screen'] = str(screen)
        if extra:
            receipt.update(dict(extra))
        old = bs.receipts.value or []
        window = (list(old) + [receipt])[-RECEIPTS_WINDOW_CAP:]
        seq = bs.write_seq + 1
        sig = ChannelSig(family='logic_action', actor=actor, mode='compute',
                         group_id=f'act:{actor}@{seq}')
        bs.write_logic(bs.receipts, window, produced_by=actor, sig=sig)
    except Exception as e:  # noqa: BLE001  记录层 best-effort,不毒化动作链
        log.debug(f'[cw-bs] action receipt skip: {e}')


# ============================================================ 账本→字段桥(§5.1/§3.2.5/§3.3.5-6,迁移批次三 B1)

def _bridge_sig(bs: BoardState) -> ChannelSig:
    """效果桥写入的渠道③签名(单一构造点;§3.2.1 ③组 id =
    hook:<登记名>@<seq>;R5 W1 起签名必填,ADR-0634)。"""
    return ChannelSig(family='logic_hook', actor='EffectLedgerBridge',
                      mode='compute',
                      group_id=f'hook:EffectLedgerBridge@{bs.write_seq + 1}')


def apply_effect_burst_grant(bs: BoardState, spec: Any, *,
                             frame: str = '') -> None:
    """桥·burst 形态(选卡一次性):登记时点把效果声明的免费刷新额度一次
    性累加进余额(§3.3.5 burst 族:免费午餐 11/及时雨 4/固定理财即时段 2
    等;载体 = payload.free_refresh_burst)。只在本挂点累加一次——「一次性」
    语义由登记时点单次调用承载,其余挂点不得重复调本函数。

    采样点 = 选卡登记挂点(CwScreenInvestStrategy 确认落地,登记成功后
    紧随调用);写入 = write_logic(§3.3.6 余额写入=仅逻辑)。额度 0 或
    payload 无此字段(如 BattlefieldEffect 族)= no-op。
    """
    n = int(getattr(getattr(spec, 'payload', None), 'free_refresh_burst', 0) or 0)
    if n <= 0:
        return
    _ev = f'effect_burst@{frame}' if frame else 'effect_burst'
    balance = bs.free_refresh_balance.value or 0
    bs.write_logic(bs.free_refresh_balance, int(balance) + n,
                   produced_by='EffectLedgerBridge', evidence=_ev,
                   sig=_bridge_sig(bs))


def grant_effect_node_refresh_balance(bs: BoardState, *,
                                      frame: str = '') -> None:
    """桥·per_node + 条件判定形态(每节点发放):节点边界一次,把全部在场
    条目声明的每节点免费刷新额度累加进余额(§3.3.5-§3.3.6)。载体两族:

    - **静态每节点**:EconomyEffect.free_refresh_per_node(加油站/搜打撤=1)
      + BattlefieldEffect.free_refresh_on_node_enter(双手狸开键盘!=2),
      payload 按鸭子属性读、缺省 0(两族并存条目求和);
    - **条件判定**(本金充裕/+,EconomyEffect 条件三元组,§3.3.6「结构化后
      经同一桥自动生效」):按 bs.gold 现值评估——金 > free_refresh_cond_gold_above
      时每额外 free_refresh_cond_gold_step 金 +1 次、至多 free_refresh_cond_cap;
      三字段齐备(>0)才激活,半配对保守 no-op。金未读(None)= 条件不可
      评估 → 该条目本拍零授予(禁猜;下一节点金可读时恢复评估,授予量
      随当拍现值,不补发历史拍)。

    采样点 = 节点 tick 挂点(cw_loop 备战分支),**仅在 advance_node 返回
    advanced=True 时调用**(每节点恰一次,重复调用即双计;条件形态与静态
    形态同闸门——授予量随当拍金现值变化,触发时点恒为节点边界一次);
    写入 = write_logic(§3.3.6)。静态活载体 = 双手狸(2/节点);条件活载体 =
    本金充裕/+(50/10/3)。固定理财位面开始段(PLANE_START)不属本形态,
    未建模挂账不改本桥。
    """
    per_node = 0
    gold = bs.gold.value
    for e in bs.effects.entries:
        payload = e.spec.payload
        per_node += int(getattr(payload, 'free_refresh_per_node', 0) or 0)
        per_node += int(getattr(payload, 'free_refresh_on_node_enter', 0) or 0)
        above = int(getattr(payload, 'free_refresh_cond_gold_above', 0) or 0)
        step = int(getattr(payload, 'free_refresh_cond_gold_step', 0) or 0)
        cap = int(getattr(payload, 'free_refresh_cond_cap', 0) or 0)
        if above > 0 and step > 0 and cap > 0 and gold is not None:
            surplus = int(gold) - above
            if surplus > 0:
                per_node += min(surplus // step, cap)
    if per_node <= 0:
        return
    _ev = f'effect_per_node@{frame}' if frame else 'effect_per_node'
    balance = bs.free_refresh_balance.value or 0
    bs.write_logic(bs.free_refresh_balance, int(balance) + per_node,
                   produced_by='EffectLedgerBridge', evidence=_ev,
                   sig=_bridge_sig(bs))


def project_effect_capacity(bs: BoardState) -> None:
    """桥·容量投影(§3.2.5):按账本在册容量时限声明回写备战席容量——
    激活期 capacity=N、条目到期移除后自动回默认 9。

    声明契约:容量条目的 payload 携带 ``capacity_limit: int``(激活期容量;
    注册表现零条目携带——§5.2 缺口登记「禁到注册表找规格」,载体归注册表
    建模批候选,声明字段名由此钉死,首批容量条目入册即自动生效)。多声明
    取 min(叠加收紧向)。当前零携带 → 投影恒等于默认 9(幂等 no-op,行为
    与接线前逐位一致)。

    采样点 = 备战帧观察后(cw_loop 备战分支,**每 pass 重锚**):观察构造器
    (bench_view_from_obs)按默认容量建视图,会覆盖投影值,故观察后须重锚;
    bench 从未观察(值 None)= 无容器可写,跳过(容量随 bench 首帧进入
    记录)。建模批补首张容量条目时须同批补观察构造器的容量感知,防观察
    覆盖 logic 值刷缺陷台账(本桥 docstring 即该义务的挂点)。
    """
    limits = [int(getattr(e.spec.payload, 'capacity_limit', 0) or 0)
              for e in bs.effects.entries]
    limits = [n for n in limits if n > 0]
    target = min(limits) if limits else BENCH_CAPACITY_DEFAULT
    view = bs.bench.value
    if view is None or view.capacity == target:
        return
    bs.write_logic(bs.bench,
                   BenchView(slots=list(view.slots), capacity=target),
                   produced_by='EffectLedgerBridge',
                   evidence='capacity_project', sig=_bridge_sig(bs))


# ============================================================ 备战席观察写端(§3.2.5)


def bench_view_from_obs(bench_chars: list) -> BenchView | None:
    """备战席 SIFT 读链 → BenchView(观察写端的值构造;§3.2.5 观察写端=本屏)。

    - **空集 = 失读非全空**(P2-1 批次二落地审):overlay 残留/动画帧/识别
      退化都会产空集,≠实席真清空——返 None,调用方走 carried(§2.2 处置①;
      先例 = 商店空牌面「宁缺勿造不写」),禁把「9 槽全空」当 observation
      入记录(席空数派生误报 free=9 会污染席满决策);
    - 槽位越界条目丢弃并 log 留证(物理槽 1..capacity 外 = 读链漂移信号,
      静默丢弃 = 身份静默丢失);
    - 非 None 返回 = 槽位保序映射(下标 i = 物理槽 i+1,与 sim 合成口同构)。
    """
    if not bench_chars:
        return None
    slots: list[BenchSlot] = [BenchSlot(kind='empty')] * BENCH_CAPACITY_DEFAULT
    for bc in bench_chars:
        s = int(getattr(bc, 'slot', 0) or 0)
        if 1 <= s <= BENCH_CAPACITY_DEFAULT:
            slots[s - 1] = BenchSlot(kind='unit', unit=Unit(
                char_id=str(getattr(bc, 'char_id', '') or ''),
                star=int(getattr(bc, 'star', 1) or 1),
                equips=list(getattr(bc, 'equips', None) or []),
                slot=s))
        else:
            log.warning('[cw!][bs-bench] 备战席读链槽位越界丢弃:'
                        'slot=%s char=%s(SIFT/星级读链漂移信号)',
                        s, getattr(bc, 'char_id', '?'))
    return BenchView(slots=slots, capacity=BENCH_CAPACITY_DEFAULT)


def deployed_rows_from_obs(deployed_chars: list) -> tuple[list[Unit], list[Unit]] | None:
    """上场席位 SIFT 读链 → (front_row, back_row)(观察写端的值构造;§3.2.3/§3.2.4)。

    - **空集 = 失读非全空**(与 :func:`bench_view_from_obs` P2-1 同款纪律):
      overlay 残留/动画帧/识别退化都会产空集——返 None,调用方走 carried
      (§2.2 处置①),禁把「全场无人」当 observation 入记录;
    - 坐标系换算(设计 §8.2,换算归映射层):SIFT 产 BenchChar.slot =
      行内 1 基画面槽号(前排 1..4/后排 1..N),Unit.slot 同系直传(仅
      信息位);分排 = 按 ``position_pref``('front'/'back')路由;
    - 装备不入本观察:SIFT 身份链不读 below-avatar 装备(备战席负探针在
      案;上场位装备读在 read_row_equipped 独立通道,接线挂装备建模批),
      Unit.equips 恒空表,不造假值。
    """
    if not deployed_chars:
        return None
    front: list[Unit] = []
    back: list[Unit] = []
    for bc in deployed_chars:
        cid = str(getattr(bc, 'char_id', '') or '')
        if not cid:
            continue   # 未识别槽不进记录(宁缺勿造,与 SIFT 产出契约同)
        row = str(getattr(bc, 'position_pref', '') or '')
        unit = Unit(char_id=cid,
                    star=int(getattr(bc, 'star', 1) or 1),
                    equips=[],
                    slot=int(getattr(bc, 'slot', 0) or 0))
        (front if row == 'front' else back).append(unit)
    if not front and not back:
        return None   # 全部条目无身份 = 失读形态
    return front, back


def bench_slots_to_legacy(view: BenchView) -> list:
    """BenchView(容器备战席)→ GameState.bench 槽位表(视图收编换算单一源)。

    下标语义两端同构(容器 slots[i] = 物理槽 i+1,旧表下标 i = 物理槽
    i+1,ADR-0316),逐槽 1:1;Unit → BenchChar:阵营不入容器(§3.2.3),
    经角色注册表查表派生(唯一例外开拓者形态随排,由 char_id 自带形态
    名承载);备战席装备 = 容器 Unit.equips(本域观察恒空表,见
    :func:`deployed_rows_from_obs` 边界申报)。槽位越界/空槽 → None。
    """
    from sr_od.application.currency_war.data.cw_chars import get_char
    from sr_od.application.currency_war.kernel.cw_state import BenchChar
    out: list = []
    for i, slot in enumerate(view.slots):
        u = getattr(slot, 'unit', None)
        if getattr(slot, 'kind', 'empty') != 'unit' or u is None:
            out.append(None)
            continue
        ch = get_char(str(u.char_id or ''))
        out.append(BenchChar(
            slot=i + 1,
            char_id=str(u.char_id or ''),
            faction=(ch.factions[0] if (ch is not None and ch.factions)
                     else ('' if ch is not None else '?')),
            star=int(u.star or 1),
            equips=list(u.equips or []),
        ))
    return out


def unit_rows_to_deployed(front_row: list[Unit], back_row: list[Unit]) -> list:
    """(front_row, back_row)(容器席位)→ GameState.deployed 槽位表(ADR-0392
    0 基:0-3 前排/4-9 后排;视图收编换算单一源)。

    坐标系换算(设计 §8.2 注):Unit.slot = 行内 1 基画面槽号(信息位)→
    旧表下标 = 前排 slot-1 / 后排 3+slot;slot 缺席(0)按占用序顺延兜底
    (与旧紧缩构造兼容)。阵营派生同 :func:`bench_slots_to_legacy`。
    """
    from sr_od.application.currency_war.data.cw_chars import get_char
    from sr_od.application.currency_war.kernel.cw_state import (
        DEPLOYED_CAPACITY,
        BenchChar,
    )
    out: list = [None] * DEPLOYED_CAPACITY

    def _place(units: list[Unit], base: int) -> None:
        cursor = 0
        for u in units:
            ch = get_char(str(u.char_id or ''))
            bc = BenchChar(
                slot=int(u.slot or 0),
                char_id=str(u.char_id or ''),
                faction=(ch.factions[0] if (ch is not None and ch.factions)
                         else ('' if ch is not None else '?')),
                star=int(u.star or 1),
                position_pref='front' if base == 0 else 'back',
                equips=list(u.equips or []),
            )
            idx = (int(u.slot or 0) - 1 + base) if (int(u.slot or 0) >= 1) else -1
            if not (base <= idx < base + (4 if base == 0 else DEPLOYED_CAPACITY - 4)) \
                    or out[idx] is not None:
                while cursor < (4 if base == 0 else DEPLOYED_CAPACITY) \
                        and out[cursor] is not None:
                    cursor += 1
                idx = cursor if cursor < (4 if base == 0 else DEPLOYED_CAPACITY) \
                    else -1
                cursor += 1
            if idx >= 0:
                out[idx] = bc
    _place(list(front_row or []), 0)
    _place(list(back_row or []), 4)
    return out


# ============================================================ 局终归档快照(§6.2/§8.8)

def archive_snapshot(bs: BoardState) -> dict:
    """局终 BoardState 归档快照(§6.2 局终归档喂遥测,先于连刷重建;
    §8.8 遥测行形状正本的两键:bs_prov/bs_extra)。

    - bs_prov = 非默认来源注记(稀疏化,不逐字段灌满):source 非
      observation、或 observation 带 evidence 的字段才入——默认 observation
      无注记的字段 = 「本帧真读」语义,键面留白;
    - bs_extra = 工程结构(schema 版本/域版本/心跳/效果账本规模)+
      全部非 None 字段值(JSON 安全形态,供离线判读)。
      (bs_pending 挂起预期摘要已随两态制废除退役——ADR-0651。)

    返回 dict 直接入档(由局终装配器并档);序列化失败逐字段跳过
    (归档 best-effort,不阻塞局终流转)。
    """
    prov: dict[str, dict] = {}
    extra_values: dict[str, object] = {}
    for f in dataclasses.fields(bs):
        val = getattr(bs, f.name, None)
        if not isinstance(val, Field):
            continue
        if val.value is not None:
            with contextlib.suppress(Exception):
                extra_values[f.name] = _json_safe(val.value)
        if val.source != 'observation' or val.evidence is not None:
            prov[f.name] = {'source': val.source, 'evidence': val.evidence}
    return {
        'schema_version': bs.schema_version,
        'bs_prov': prov,
        'bs_extra': {
            'values': extra_values,
            'bs_schema': dict(bs.bs_schema),
            'write_seq': bs.write_seq,
            'frame_obs': bs.frame_obs,
            'effects_count': len(getattr(bs.effects, 'effects', []) or []),
        },
    }


def _json_safe(value: Any) -> Any:
    """归档值的 JSON 安全化(dataclass → dict;容器递归;其余原样)。"""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {k: _json_safe(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


# ============================================================ 合成升星逻辑直写构造源(§3.2.18 窟窿一,修法 a)

def bench_view_of_slots(bench_list: list) -> BenchView:
    """GameState.bench 槽位表(0 基下标 + None 洞)→ BenchView(记录模型
    形状契约;槽 i = 物理槽 i+1,与 sim 合成口同构映射)。投影面用
    (BuyCard 升星投影的逻辑直写值构造源,ADR-0651)。"""
    slots: list[BenchSlot] = []
    for i, bc in enumerate(bench_list or []):
        if bc is None:
            slots.append(BenchSlot(kind='empty'))
        else:
            slots.append(BenchSlot(kind='unit', unit=Unit(
                char_id=str(getattr(bc, 'char_id', '') or ''),
                star=int(getattr(bc, 'star', 1) or 1),
                equips=list(getattr(bc, 'equips', None) or []),
                slot=i + 1)))
    while len(slots) < BENCH_CAPACITY_DEFAULT:
        slots.append(BenchSlot(kind='empty'))
    return BenchView(slots=slots, capacity=BENCH_CAPACITY_DEFAULT)


def detect_merge_upgrade(cur: Any, proj: Any) -> bool:
    """BuyCard 投影是否发生 3 合 1 升星(§3.2.18 修法 a 触发判定;纯函数)。

    判据 = 同名角色投影后最高星级 > 投影前同名最高星——3 份合成是该
    签名的唯一来源(星级只经合成上升;买新卡不抬同名最高星)。合成域 =
    全场(bench+deployed,``cw_state._merge_bench`` 同口径)。级联合并
    (3×1★→2★→…)只看「有抬升」真值,层级数不影响本判定。
    """
    def _max_star(st: Any) -> dict[str, int]:
        best: dict[str, int] = {}
        for c in (list(getattr(st, 'bench', None) or [])
                  + list(getattr(st, 'deployed', None) or [])):
            if c is not None:
                cid = str(getattr(c, 'char_id', '') or '')
                if not cid:
                    continue
                s = int(getattr(c, 'star', 1) or 1)
                if s > best.get(cid, 0):
                    best[cid] = s
        return best
    before, after = _max_star(cur), _max_star(proj)
    return any(after.get(cid, 0) > s for cid, s in before.items())


# ============================================================ 结算覆盖写端(§3.5.1)

def apply_settlement_cover(bs: BoardState, *, hp_after: int | None,
                           streak_after: int | None,
                           killed: bool | None = None,
                           progress_delta: int | None = None,
                           gold: int | None = None,
                           level: int | None = None,
                           xp: tuple[int, int] | None = None,
                           note: str = '') -> None:
    """结算屏真值覆盖(§3.5.1;接线点 = cw_screen_battle_wait 结算块,
    迁移批次二任务书件 8)。

    本屏同时是这些字段的覆盖写端:hp(§3.2.13)/streak 带方向真值
    (§3.2.12:备战幅度读数无方向,带方向值只有本写端与逻辑推进)/
    金币仅胜局(§3.2.9,败局结算屏无收入面板)/等级/经验仅胜局结算页
    可读(cw_settlement_obs.py:118-135)。伤害不入本结构(遥测面,
    字段准入①)。全部 observation 写入(真值覆盖)。

    - note = settlement 域行注记透传(行注记 = 结算事实的判读面;
      R5 W1 起承载旧 battle_done 外生行的「出节点」语义——接线点传
      ``battle_done:<node_type>``,ADR-0634;hp/gold 等逐字段行不带注记);
    - 渠道签名(§3.2.1 ①类属 = 画面 op 类名):写端 = CwScreenBattleWait,
      R5 W1 起签名必填,ADR-0634。
    """
    _sig = ChannelSig(family='obs', actor='CwScreenBattleWait', mode='read')
    if hp_after is not None:
        bs.observe(bs.hp, int(hp_after), sig=_sig)
    if streak_after is not None:
        bs.observe(bs.streak, int(streak_after), sig=_sig)
    if gold is not None:
        bs.observe(bs.gold, int(gold), sig=_sig)
    if level is not None:
        bs.observe(bs.level, int(level), sig=_sig)
    if xp is not None:
        bs.observe(bs.xp, (int(xp[0]), int(xp[1])), sig=_sig)
    bs.observe(bs.settlement, Settlement(
        hp_after=hp_after, streak_after=streak_after, killed=killed,
        progress_delta=progress_delta, gold=gold, level=level,
        xp=(int(xp[0]), int(xp[1])) if xp is not None else None),
        sig=_sig, note=note)


# ============================================================ 局终行写口(§3.6.1 runs 收编;ADR-0630 修订节)

#: 局终行落盘事件监听槽(复盘触发器挂点;缺省 None = 关,与缺陷/流水 sink
#: 同构的「缺省关 + 启动点显式接通」纪律)。消费契约:接收一行事件 dict
#: (run_id/final_type/plane/round_num/version/backfilled),自担节流与
#: 落盘;**触发语义 = 写口受理成功即触发**(行落盘另以 sink 武装与 run_id
#: 在场为准——未武装/局外 = 行不落而事件照发,事件 run_id='' 形态,消费方
#: 自滤;详 :meth:`write_match_final` docstring)。复盘流程本体不挂本批
#: (终局行 = 复盘入口,retirement.md §7 消费面行 9 触发面:runs 兜底与
#: Δ池再生触发改挂局终域行落盘事件,挂接线批)。
_MATCH_FINAL_LISTENER: Callable[[dict], None] | None = None


def set_match_final_listener(fn: Callable[[dict], None] | None) -> None:
    """接通/复位局终行落盘监听(None = 关,缺省态;装配点显式接通)。"""
    global _MATCH_FINAL_LISTENER
    _MATCH_FINAL_LISTENER = fn


def write_match_final(bs: BoardState, *, final_type: str,
                      plane: int | None = None,
                      round_num: int | None = None,
                      node_kind: str | None = None,
                      level: int | None = None,
                      hp: int | None = None,
                      gold: int | None = None,
                      streak: int | None = None,
                      duration_s: float | None = None,
                      backfilled: bool = False,
                      cw4_counters: dict[str, int] | None = None,
                      note: str = '') -> bool:
    """局终收口写口(局终域 **唯一写点**,渠道③ logic_hook 家族、
    actor=MatchClose;§3.6.1 runs 收编载体,表 3-3 局终域③格;持久裁定锚
    = ADR-0630 修订节)。

    - **同版本原子**:终局类型 + 时点版本 id + 版本戳(code_commit/
      registry_fingerprint,模块级常量) + 终局快照 + 段级时长一次逻辑
      写入装配成单笔 :class:`MatchFinal` 载荷,经一次 ``_swap`` 落一行
      (行内全量 state = 终局快照,字段来源注记随快照行自带);
    - ``cw4_counters`` = 策略行为观测计数局终聚合(R5 W4 键收编载体,
      ADR-0650;载体语义/None 与空 dict 分型见 :class:`MatchFinal` 字段
      注)。快照副本由调用方在收口时点现读传入,本写口不触策略容器;
    - **写前查重 = 段内幂等**(§3.6.2 终局防重读门 G12 收编,运行时控制面
      读口豁免类,载体 = 内存字段现读):本段已有终局行 → no-op 返 False;
    - **异常终局 = 补写形态**(G8):``backfilled=True`` 时版本 id 照常分配
      (写入口正常路径),行载荷 final_type='abnormal' + backfilled 位 +
      行注记缺省 'recovered' 显影(判读可辨真伪)。**辖域 = 段内补写**
      (哨兵收口兜底/在线路径异常形态,行挂当前段);启动扫描的**历史段**
      补写禁走本口——本口 run_id 取供给槽现读,历史段行必被挂到现读段键
      (错归属),须走专用装配通道(读流→构造→按显式 run_id 落行,遥测
      正本 §3.2.2 规则 6②;先例 = recover_dangling_run_summaries,挂接线
      批批首);
    - duration_s 缺省 = 段级时长自算(容器创建 → 本调用,段级;恢复局跨段
      = 各段各行,聚合归判读侧);
    - 落盘语义:行落盘受 sink 在场/run_id 在场辖(缺实例/局外 = 版本照耗、
      Field 照写、行不外送——与全部写入口一致);**监听器 = 写口受理成功
      (过封闭集与段内幂等门)即触发**,行落盘与否另以 sink/run_id 在场为准
      (缺实例/局外 = 行不落而事件照发,事件 run_id='' 形态)——消费方按此
      自滤;监听 best-effort,异常不毒化终局流转。

    返回 True = 本调用落了终局行;False = 本段已收口(幂等跳过)。
    """
    if final_type not in MATCH_FINAL_TYPES:
        raise ValueError(
            f'终局类型 {final_type!r} 集外(封闭集 = {MATCH_FINAL_TYPES};'
            f'局终域行载荷词表)')
    if bs.match_final.value is not None:
        return False   # 段内幂等(G12 写前查重):同段恰一行
    if duration_s is None:
        duration_s = max(time.monotonic() - bs.created_monotonic, 0.0)
    if not note and backfilled:
        note = 'recovered'   # G8 补写行显影(判读按注记分型,防混计)
    payload = MatchFinal(
        final_type=final_type,
        at_version=bs.write_seq + 1,   # 本行自身版本 id(与行头 v 恒等)
        code_commit=_CODE_COMMIT,
        registry_fingerprint=_REGISTRY_FINGERPRINT,
        plane=plane, round_num=round_num, node_kind=node_kind,
        level=level, hp=hp, gold=gold, streak=streak,
        duration_s=duration_s, backfilled=bool(backfilled),
        cw4_counters=(dict(cw4_counters) if cw4_counters is not None else None))
    seq = bs.write_seq + 1
    sig = ChannelSig(family='logic_hook', actor='MatchClose', screen=None,
                     mode='compute', group_id=f'hook:MatchClose@{seq}')
    bs.write_logic(bs.match_final, payload, produced_by='MatchClose',
                   sig=sig, note=note)
    fn = _MATCH_FINAL_LISTENER
    if fn is not None:
        try:
            fn({'run_id': _current_run_id_safe(),
                'final_type': final_type,
                'plane': plane, 'round_num': round_num,
                'version': payload.at_version,
                'backfilled': bool(backfilled)})
        except Exception as e:  # noqa: BLE001  挂点 best-effort
            log.debug(f'[cw-bs] match_final listener skip: {e}')
    return True


# ============================================================ 单例宿主


_BS_BY_SESSION: weakref.WeakKeyDictionary[object, BoardState] = \
    weakref.WeakKeyDictionary()
#: 桩面兜底第二级:属性不可写对象(__slots__ 族)的 id() 键 dict
#: (同 cw_exec_state 桩面存储两级结构;挂对象属性优先)。
_BS_BY_SESSION_ID: dict[int, BoardState] = {}
_BS_ATTR = '_cw_board_state'


def board_state_of(session: object) -> BoardState:
    """BoardState 单例访问口(session 旁表;弱引用表 + 桩面兜底,与
    ``cw_exec_state.exec_state_of`` 同构)。

    - session = 局身份:新 session 对象 = 新局 = 新 BoardState(§1 每局新建);
    - None → 一次性空载体(不缓存——None 的 id 恒定,缓存即跨调用串染);
    - 裸 session(测试/sim 桩)→ 惰性建并挂对象自身属性(生命周期随对象)。
    """
    if session is None:
        return BoardState(schema_version=BS_SCHEMA_VERSION)
    try:
        bs = _BS_BY_SESSION.get(session)
    except TypeError:   # 不可弱引用对象(测试桩)
        bs = getattr(session, _BS_ATTR, None)
        if bs is None:
            bs = BoardState(schema_version=BS_SCHEMA_VERSION)
            try:
                setattr(session, _BS_ATTR, bs)
            except (AttributeError, TypeError):
                _BS_BY_SESSION_ID[id(session)] = bs
        return bs
    if bs is None:
        bs = BoardState(schema_version=BS_SCHEMA_VERSION)
        _BS_BY_SESSION[session] = bs
    return bs


# ============================================================ BoardState 单例


@dataclass
class BoardState:
    """局内记录:当前局内状态的唯一一份快照(单例,只描述此刻,§8.4)。

    写入纪律(§2.4):op 层一律经 observe/carry/write_prior/write_logic
    API 写入,不直接摸字段;写点以写时刻的单例现引用为基底构造新帧
    (frozen 帧替换——旧 Field 引用保持旧值,持旧引用的读者不被污染)。

    字段集 = §8.4 目标 dataclass + §8.6-3/4 缺口域(迁移批次一补齐):
    开局初值域(§3.1)/十事件屏 chosen_*(§3.4)/商店刷新计数组(§3.3.6-9)/
    节点屏刷新计数组(§3.4.1-4)/持久账本组(§3.2.15/16/19)/board(§3.2.6)/
    level_up_cost(§3.2.11)/back_layout(§3.2.7)/spheres(§3.2.8)/分类子态
    (§3.2.17)/对局类型(§3.1.2)/节点序列台账(§3.2.2)/hp 保底事件位(§3.5.3)。
    """

    schema_version: int              # 行级版本,无默认值(§3.7.1;新局必显式申报)

    # —— 节点 ——
    node: Field[NodeKey] = field(default_factory=Field)          # 当前节点(§3.2.1)
    node_path: Field[list[str]] = field(default_factory=Field)   # 节点类型序台账(§3.2.2;备战帧 node_path 现读=权威写端)

    # —— 单位域(含星级与装备)——
    front_row: Field[list[Unit]] = field(default_factory=Field)  # 前排成员(§3.2.3)
    back_row: Field[list[Unit]] = field(default_factory=Field)   # 后排成员(§3.2.4)
    bench: Field[BenchView] = field(default_factory=Field)       # 备战席统一槽位视图(§3.2.5;capacity 随效果改写)
    back_layout: Field[int] = field(default_factory=Field)       # 后台格数(值域 6-9:平常 6,宝钻/召唤物扩展,上限 9;6/7/8 已交互建档,9 档坐标未建档——域外按 8 格超集运行+evidence superset 标记,§3.2.7)

    # —— 经济与成长 ——
    gold: Field[int] = field(default_factory=Field)              # None=不可读(§3.2.9)
    level: Field[int] = field(default_factory=Field)             # 等级(§3.2.10;启发式兜底值禁入——非真读走 carried)
    xp: Field[tuple[int, int]] = field(default_factory=Field)    # (当前级已攒, 升下一级所需)(§3.2.10;同文本两分量成对存)
    streak: Field[int] = field(default_factory=Field)            # 带符号:正=连胜/负=连败(§3.2.12)
    hp: Field[int] = field(default_factory=Field)                # 写入闸 §3.2.13:非真读帧不经 observe(§8.8 假值防线)
    level_up_cost: Field[int] = field(default_factory=Field)     # 单击买经验价(§3.2.11;None=未读到禁兜底)
    # [索引定义] deploy_cap = 部署容量识别真值(= level + 财富宝钻数,可叠加)。
    # 坐标系 = 「X/Y」指示的 Y 人数口径;取值时机 = 备战帧观察期快照(ADR-0420
    # 双帧一致采信门输出,写端 = cw_observation._feed_board_state spec 门
    # 'deploy_cap' 键,防抖核 = cw_observation._debounce_cap 单一源)。
    # W5 定谳入容器(W5-透传域建模方案 §2.3;推翻设计正本 §3.2.7「现场实时
    # 读值豁免」在册前提,正本更新义务见方案稿 §2.3):与 back_layout 双存
    # 属 §8.8 在册例外形态(识别口径 vs 推导口径各有消费面,先例 = board、
    # level_up_cost)——cap=识别源(采信门输出),back_layout=三信号裁决结果
    # (cw_back_layout);理论关系 back_layout ≈ 6+(cap−level) 仅域内成立,
    # 域外态 back_layout 是 8 格超集,反推会把近似当真值,故不派生改双存。
    # 两域冲突走缺陷台账,不互改。
    deploy_cap: Field[int] = field(default_factory=Field)

    # —— 局级事实 ——
    selected_difficulty: Field[str] = field(default_factory=Field)   # 职级,开局写定恒稳(§3.1.1)
    game_mode: Field[str] = field(default_factory=Field)             # 对局类型:标准/超频博弈(§3.1.2;两屏无建档,接线前补档)
    enemy_difficulty: Field[int] = field(default_factory=Field)      # 非单调(§3.2.14)
    plane_bosses: Field[list[str | None]] = field(default_factory=Field)  # 三位面 boss 名,None=该位面无身份(ADR-0398)
    active_env: Field[str | None] = field(default_factory=Field)     # 已选投资环境(§3.2.20/§3.4.3)
    enemy_affixes: Field[list[str]] = field(default_factory=Field)   # 当前词缀名单(§3.1.3;≠投资环境)
    active_strategies: Field[list[str]] = field(default_factory=Field)   # 持有投资策略名单(§3.4.4;品质锚挂建模批)
    board: Field[dict[str, int]] = field(default_factory=Field)      # 上阵羁绊计数(§3.2.6;下档阈值=派生不存储)
    shop_refresh_cost: Field[int] = field(default_factory=Field)     # 刷新费,动态(§3.3.4/ADR-0622 现场 OCR;免费帧不写,None≠0)

    # —— 商店刷新计数组(§3.3.6-§3.3.9;写入=仅逻辑,无 UI 观察通道)——
    free_refresh_balance: Field[int] = field(default_factory=Field)  # 未消耗免费刷新次数(§3.3.6)
    paid_refresh_count: Field[int] = field(default_factory=Field)    # 累计付费刷新(§3.3.7;长线利好触发计数载体)
    total_refresh_count: Field[int] = field(default_factory=Field)   # 累计全部刷新(§3.3.8;二手市场/采购专员计数载体)
    prev_node_spent: Field[bool] = field(default_factory=Field)      # 上节点是否花费(§3.3.9;存款回报条件输入,观察需求)

    # —— 节点屏刷新计数组(P1-2 批次一落地审补;§3.4.1-§3.4.4;字段先入
    # schema,**写端未接**——遭遇/补给刷新已用现役走 exec_state 侧标
    # (cw_exec_state._encounter_refresh_used/_supply_refresh_used),四字段
    # 零写端;接线挂批次三/建模批申报,零写端期间禁按字段值做决策)——
    encounter_refresh_used: Field[int] = field(default_factory=Field)    # 遭遇刷新已用(§3.4.1;cw_screen_encounter 置位口径)
    supply_refresh_used: Field[int] = field(default_factory=Field)       # 补给刷新已用(§3.4.2;「无布局局原生可刷」收窄待证,字段位先申报禁静默)
    env_refresh_used: Field[int] = field(default_factory=Field)          # 环境刷新已用(§3.4.3;观察通道在册 cw_node_obs「剩余次数」)
    strategy_refresh_used: Field[dict[str, int]] = field(default_factory=Field)  # 投资策略逐卡刷新已用(§3.4.4)。**键口径显式申报(迁移批次二)**:键 = 注册表规范卡名(normalize_invest_name 归一后;选名不选 spec.id 的理由 = 效果注册表 STRATEGY_EFFECTS 即以规范名为键,写端 OCR 名经同一归一函数入键,免双坐标系换算)。值域纪律:基线每卡 1 次、例外三族(银金彩环境+2/投资卡族=3/期货族=0/远见=0)以注册表官方全文为唯一口径,禁按基线做核对预期

    # —— 持久账本组(跨画面保留)——
    # ⚠️ 免战牌不在本组(§8.6-3 载体归一,迁移批次二):激活态+剩余次数
    # 正本 = effect_inventory.remaining_uses(§5.1,ActiveEffect.remaining_
    # uses「次数类余量(免战牌×2 等)」,同型躺平/节省工位;批次一骨架的
    # skip_battle_active/remaining 两 Field 已按正本归一移除,消费走
    # bs.effects 查询)。
    equips: Field[list[str]] = field(default_factory=Field)          # 装备库存(§3.2.15)
    consumables: Field[list[str]] = field(default_factory=Field)     # 消耗品库存(§3.2.16)

    # —— 奖励球(§3.2.8,不占席)——
    spheres: Field[SphereSight] = field(default_factory=Field)

    # —— 交互状态 ——
    prep_substate: Field[str] = field(default_factory=Field)     # 分类子态四档(§3.2.17;恢复锁定=会话推断档,写端=接管协议 §6.3)
    event_overlay: Field[str | None] = field(default_factory=Field)  # 'none'=确认无浮层;None=没读到(§3.6.1 双义禁令)

    # —— 画面附加域(当前画面的 payload,非当前画面=None,§2.2 例外)——
    shop: Field[ShopPayload | None] = field(default_factory=Field)
    encounter: Field[EncounterPayload | None] = field(default_factory=Field)
    supply: Field[SupplyPayload | None] = field(default_factory=Field)

    # —— 十事件屏选择结果(§3.4/§4 事件选择:chosen_* 由选择 handler 单次逻辑写入)——
    chosen_encounter: Field[tuple[int, str] | None] = field(default_factory=Field)   # (难度档, 奖励文本)
    chosen_supply: Field[tuple[str, str, bool] | None] = field(default_factory=Field)  # (角色, 装备, 有钻石)
    chosen_megastar: Field[str | None] = field(default_factory=Field)   # 盛会之星(§3.4.5)
    chosen_partner: Field[str | None] = field(default_factory=Field)    # 伙伴(候选阵营)
    chosen_wish: Field[str | None] = field(default_factory=Field)       # 祈愿试炼目标文本(档=货币战争-祈愿试炼,写端=cw_screen_wish_trial)
    chosen_fortune: Field[str | None] = field(default_factory=Field)    # 命运卜者(暂无画面建档)
    chosen_hack: Field[str | None] = field(default_factory=Field)       # 骇入策划(暂无画面建档)
    chosen_expert: Field[str | None] = field(default_factory=Field)     # 专家邀请函
    chosen_tome: Field[str | None] = field(default_factory=Field)       # 星徽秘典弹窗卡名
    chosen_equip: Field[str | None] = field(default_factory=Field)      # 装备三选一(暂无画面建档)

    # —— 结算(战斗后真值覆盖的数据源)——
    settlement: Field[Settlement | None] = field(default_factory=Field)
    hp_floor_triggered: Field[bool] = field(default_factory=Field)   # hp 保底触发事件位(§3.5.3;纯观察登记,无判据载体)

    # —— 逻辑态派生域与画面上下文域(R1 §3.1.4;bs_schema 域 'derivation')——
    # 写点准入:上下文对与顶栏原文唯一写点 = ①观察汇聚
    # (observe_screen_context,观察层);node_ord 唯一写点 = 派生规则
    # (四腿全部 write_logic 逻辑层——备战腿=解析顶栏文本成序键,同样是
    # 「从观察数据计算逻辑值」,用户终裁 2026-09-11 字段层次终极版)——
    # 其余渠道写入 = 越格。
    prev_screen: Field[str] = field(default_factory=Field)       # 上一次分派观察的画面标识(开局前 '')
    current_screen: Field[str] = field(default_factory=Field)    # 最近一次分派观察的画面标识(派生规则输入面)
    # [索引定义] top_bar_raw = 备战帧顶栏原始文本(如「备战阶段 1-3」OCR
    # 原文)。**观察层字段**(唯一 observe() 写点 = 观察汇聚,source=
    # observation):只落画面原始读数,禁写派生值(用户终裁 2026-09-11 字段
    # 层次终极版:序键是逻辑层,原文才是观察层)。原文缺读 = 不写(禁猜);
    # 取值时机 = 备战帧观察期快照。生产透传(读链暴露原文)候漏斗接线批。
    top_bar_raw: Field[str] = field(default_factory=Field)
    # [索引定义] node_ord = 节点序 ord=(plane-1)*9+round(基 1,与效果账本
    # advance_node 同坐标系)。**逻辑层字段(用户终裁 2026-09-11 字段层次
    # 终极版)**——四条腿(备战规则=解析顶栏文本成序键/弹窗规则/0q/0p)全部
    # 是「从观察数据计算逻辑值」的派生规则,全部经 write_logic() 写逻辑层
    # (source=logic),无 observe() 写序键的例外;类型派生同在逻辑层。
    # 生效序读口 = :func:`effective_node_ord`(派生计算,非存储字段);
    # None = 未定。取值时机 = 派生写入期快照;写端 = 派生规则。
    node_ord: Field[int] = field(default_factory=Field)

    # —— 动作回执域(R2 §3.1.1-4/§3.2.5;bs_schema 域 'receipts')——
    # [索引定义] receipts 值 = 动作执行回执的滚动窗:list 下标 i = 第 i 条
    # 存活回执(窗序 = 写入序,先进先出,容量 = :data:`RECEIPTS_WINDOW_CAP`);
    # 取值时机 = 写入期快照(帧替换,禁就地改窗内条目)。唯一写点 =
    # :func:`note_action_receipt`(渠道② logic_action);失败动作也产行
    # (applied=false + reason)——exec_events「失败可见性」收编载体。
    receipts: Field[list[dict]] = field(default_factory=Field)

    # —— 局终域(R5 W2;§3.6.1 runs 收编载体;bs_schema 域 'match_final')——
    # [索引定义] match_final 值 = :class:`MatchFinal` 终局行载荷(一段一行,
    # 恢复局跨段 = 多行;game 级聚合取段序末行)。取值时机 = 局终判定成立
    # 的当前 swap(单版本原子);None = 本段未收口。唯一写点 =
    # :func:`write_match_final`(渠道③ actor=MatchClose);写前查重即本
    # 字段现读(段内幂等,G12 收编)。
    match_final: Field[MatchFinal | None] = field(default_factory=Field)

    # ---- 持续型效果账本(§5.1):不走 Field 封装 ----
    # 存储形态 = ActiveEffect 记录列表(现役 cw_effect_inventory 同构)。
    # session 级可变账本,不参与 frozen 帧替换(帧替换管观察/逻辑字段)。
    effects: ActiveEffectInventory = field(default_factory=ActiveEffectInventory)

    # ---- 工程结构(非 Field,§2.4 关键结构 + 心跳观察者)----
    # 域粒度版本映射(§3.7.1;缺域键 = 该域未建模)。
    bs_schema: dict[str, int] = field(
        default_factory=lambda: dict(DEFAULT_BS_SCHEMA))
    # 帧观察完整度标注(full/view/none)——消费即清,不当停更哨兵(§2.4)。
    frame_obs: FrameObsLevel = 'none'
    # 心跳载体:写点序号,只增不减(§2.4 停更检测哨兵)。
    write_seq: int = 0
    # 心跳观察者上次采样值(None=未采样);stall 计数 = 连续零推进次数。
    hb_prev_seq: int | None = None
    hb_stall_count: int = 0
    # [索引定义] node_hist_ord = 本 run 已见最大有效节点序 effective_ord
    # (effective_ord = :func:`effective_node_ord` 生效序读口现值,坐标系 =
    # (plane-1)*9+round 基 1,与效果账本 advance_node 同键);派生规则推进
    # 去重键 (run_id, effective_ord) 的 run 内载体(设计 v3.1-N2)——同序
    # 恰一次推进,先到腿越 hist 即推进,后到腿同序零推进。取值时机 = 派生
    # 写入期单调推进;None = 本 run 尚无派生推进。写端 = 派生规则。
    node_hist_ord: int | None = None
    # 段级时长锚(局终域 duration_s 自算源):容器创建时刻的 monotonic 读数
    #(每局新建 = 天然段起点;恢复局跨段 = 各段各锚,聚合归判读侧)。
    created_monotonic: float = 0.0

    def __post_init__(self) -> None:
        """构造守卫(任务书件 5/§8.6-5):schema_version 正整数 + Field
        冻结不变式断言(帧替换语义的结构前提,破即构造炸错不静默)。"""
        if not isinstance(self.schema_version, int) or self.schema_version <= 0:
            raise ValueError('schema_version 必须为正整数(§3.7.1)')
        if not self.created_monotonic:
            object.__setattr__(self, 'created_monotonic', time.monotonic())
        probe = Field(value=None)
        try:
            probe.value = 1  # type: ignore[misc]  # 刻意触发冻结守卫
        except dataclasses.FrozenInstanceError:
            pass
        else:
            raise RuntimeError('Field 必须保持 frozen(§2.4 帧替换语义被破坏)')

    # —— 写入 API(op 层经此写,不直接摸字段;§8.4)——

    def _field_name(self, target: Field) -> str:
        """现引用 → 字段名(身份匹配)。传非本单例的字段实例 = 调用错,
        显式炸错(禁静默写丢)。"""
        for f in dataclasses.fields(self):
            if getattr(self, f.name) is target:
                return f.name
        raise KeyError('target 不是本 BoardState 的字段现引用'
                       '(须传 bs.xxx;跨单例引用 = 写丢事故)')

    def _swap(self, name: str, new_field: Field, *,
              sig: ChannelSig,
              note: str = '') -> None:
        """帧替换写点 + 版本 id 分配 + 状态流水行装配(R1 §3.2.2 规则 1:
        单点分配——分配与状态变更同临界区,先变更后落行,同一函数内)。

        - sig = 显式渠道签名(必填;R5 W1 起 legacy 合成签名路径已随直迁
          裁定退役——影子期「缺位合成」过渡语义不复存在,行 actor 恒在册
          非空,ADR-0634;调用方已过 :func:`_validate_sig` 渠道面校验);
        - note = 可选行注记(权威纠偏记录/battle_done 等结算事实语义)。
        """
        old = getattr(self, name)
        same_value = old.value == new_field.value
        setattr(self, name, new_field)
        self.write_seq += 1
        if _STATE_JOURNAL_SINK is None:
            return
        try:
            run_id = _current_run_id_safe()
            if not run_id:
                return   # 局外写入拒绝(§3.2.3):不写假行,诚实缺失
            _journal_emit({
                'v': self.write_seq,
                'ts': datetime.now().isoformat(timespec='seconds'),
                'run_id': run_id,
                'row': 'write',
                'field': name,
                'after': _json_safe(new_field.value),
                'same_value': bool(same_value),
                'state': self.full_state_snapshot(),
                'sig': sig.to_json(),
                'note': note,
                'evidence_refs': [],
            })
        except Exception as e:  # noqa: BLE001  记录层 best-effort,不毒化写入链
            log.debug(f'[cw-bs] journal row skip: {e}')

    def note_obs_event(self, event: str, field_name: str, observed: Any, *,
                       sig: ChannelSig,
                       verdict: str = '', obs_phase: str = '',
                       evidence_refs: list | None = None) -> None:
        """观察事件行(§3.2.3 行型 2;**零状态变更**的观察证据)。

        - 同流、**占版本**、内嵌当时 state(v3.1-N1:obs_event 与写入行同流
          同序,「run 段内行序 = 版本序」不变量覆盖全部行型);不触任何
          Field(行行自足,查询不分行型);
        - event 词表 = :data:`OBS_EVENT_EVENTS` 封闭集(arbitrate|miss|popup),
          集外显式炸错;
        - 产生面 = 登记清单(非全量;obs_conflict 汇点收编已接——R5 W1/
          ADR-0634);
        - sig = 渠道①签名(观察证据属 obs 族;必填,R5 W1 起缺位合成路径
          已退役,ADR-0634)。
        """
        _validate_sig(sig, ('obs',))
        if event not in OBS_EVENT_EVENTS:
            raise ValueError(
                f'obs_event 事件 {event!r} 集外(封闭集 = {OBS_EVENT_EVENTS};'
                f'§3.2.3 行型 2 产生面登记清单,硬约束 2 同纪律)')
        if _STATE_JOURNAL_SINK is None:
            return
        try:
            run_id = _current_run_id_safe()
            if not run_id:
                return   # 局外写入拒绝(§3.2.3)
            self.write_seq += 1   # 占版本(无状态变更;v3.1-N1)
            _journal_emit({
                'v': self.write_seq,
                'ts': datetime.now().isoformat(timespec='seconds'),
                'run_id': run_id,
                'row': 'obs_event',
                'event': event,
                'field': field_name,
                'observed': _json_safe(observed),
                'verdict': verdict,
                'obs_phase': obs_phase,
                'state': self.full_state_snapshot(),
                'sig': sig.to_json(),
                'note': '',
                'evidence_refs': list(evidence_refs or []),
            })
        except Exception as e:  # noqa: BLE001  记录层 best-effort,不毒化写入链
            log.debug(f'[cw-bs] obs_event row skip: {e}')

    def current_version(self) -> int:
        """策略侧版本读口(§3.2.2 规则 5:读不写、不占版本)= 已分配的最大
        版本号(write_seq 升格值,心跳哨兵载体语义不变)。"""
        return self.write_seq

    def full_state_snapshot(self) -> dict:
        """写入后完整 state 快照(§3.2.3 自足行的行内 state;JSON 安全化 +
        序列化规范化——effects 按 spec id 排序,同态同形)。含 values(非 None
        字段值)/ prov(非默认来源注记)/ effects(就地可变域整窗)/ 工程结构。
        (pending_expected 挂起预期摘要键已随两态制废除退役——ADR-0651。)"""
        values: dict[str, object] = {}
        prov: dict[str, dict] = {}
        for f in dataclasses.fields(self):
            val = getattr(self, f.name, None)
            if not isinstance(val, Field):
                continue
            if val.value is not None:
                values[f.name] = _json_safe(val.value)
            if val.source != 'observation' or val.evidence is not None:
                prov[f.name] = {'source': val.source, 'evidence': val.evidence}
        effects = sorted(
            ({
                'spec_id': str(getattr(e.spec, 'id', '')),
                'spec_name': str(getattr(e.spec, 'name', '')),
                'source': getattr(e, 'source', ''),
                'acquired_t': getattr(e, 'acquired_t', None),
                'remaining_nodes': getattr(e, 'remaining_nodes', None),
                'remaining_uses': getattr(e, 'remaining_uses', None),
                'counters': dict(getattr(e, 'counters', None) or {}),
            } for e in self.effects.entries),
            key=lambda d: d['spec_id'])
        return {
            'schema_version': self.schema_version,
            'values': values,
            'prov': prov,
            'effects': effects,
            'frame_obs': self.frame_obs,
            'write_seq': self.write_seq,
            'node_hist_ord': self.node_hist_ord,
            'bs_schema': dict(self.bs_schema),
        }

    def observe(self, target: Field, value: Any, *,
                evidence: str | None = None,
                sig: ChannelSig,
                note: str = '') -> None:
        """观察写入:亲眼看,覆盖旧值(§2.1 observation)。

        - value=None 拒绝(§2.2 硬边界:失读不是观察值,走 :meth:`carry`
          或画面附加域 :meth:`leave_screen`;字段一旦有过正式值任何失读
          不得清成 None);
        - 覆盖 logic 来源值且失配 → 缺陷台账留证(§2.3 观察赢;失配 =
          推算 bug,修推算代码——ADR-0651);
        - sig = 渠道①签名(必填;R5 W1 起缺位合成路径已退役,ADR-0634);
        - note = 可选行注记(结算事实等语义,ADR-0634 battle_done 收编)。
        """
        if value is None:
            raise ValueError('observe 不接受 None(§2.2:失读走 carry/'
                             'leave_screen,禁清正式值)')
        _validate_sig(sig, ('obs',))
        name = self._field_name(target)
        if target.source == 'logic' and target.value is not None \
                and target.value != value:
            _emit_defect(field_name=name, expected=target.value,
                         actual=value, evidence=evidence)
        self._swap(name, Field(value=value, source='observation',
                               evidence=evidence),
                   sig=sig, note=note)

    def carry(self, target: Field, *, frame: str,
              sig: ChannelSig) -> None:
        """失读处置①(§2.2):沿用上次好值,evidence = carried:<来源帧>。
        字段从未读过(处置②机制性 None)→ 保持 None 不写(不换帧不产行
        不占版本,§3.2.2 规则 4)。sig 必填(R5 W1,ADR-0634)。"""
        if target.value is None:
            return
        _validate_sig(sig, ('obs',))
        name = self._field_name(target)
        self._swap(name, Field(value=target.value, source='carried',
                               evidence=f'carried:{frame}'),
                   sig=sig)

    def write_prior(self, target: Field, value: Any, *,
                    evidence: str,
                    sig: ChannelSig) -> None:
        """先验写入(§2.1 prior 类,§3.1.6 开局 hp):evidence 必带
        ``prior:`` 前缀;本类仅限显式申报条目,禁扩散。sig 必填(R5 W1)。"""
        if not evidence.startswith('prior:'):
            raise ValueError('prior 写入 evidence 必带 prior: 前缀(§2.1)')
        _validate_sig(sig, ('obs',))
        name = self._field_name(target)
        self._swap(name, Field(value=value, source='prior', evidence=evidence),
                   sig=sig)

    def leave_screen(self, target: Field,
                     sig: ChannelSig) -> None:
        """画面附加域离屏(§2.2 显式例外):置 None 是结构事实非失读,
        不受 carried 硬边界辖。仅 shop/encounter/supply 三域合法,整局
        字段禁走此口(显式炸错防误用扩散)。sig 必填(R5 W1)。"""
        _validate_sig(sig, ('obs',))
        name = self._field_name(target)
        if name not in _PAYLOAD_DOMAINS:
            raise ValueError(f'{name} 非画面附加域,禁离屏清值(§2.2 硬边界)')
        self._swap(name, Field(value=None, source='observation',
                               evidence='left_screen'),
                   sig=sig)

    def write_logic(self, target: Field, value: Any, *,
                    produced_by: str, evidence: str | None = None,
                    sig: ChannelSig,
                    note: str = '') -> None:
        """逻辑直写(两态制标准写通道,ADR-0651):决策动作按游戏规则推算
        的预期效果**直接写入字段**(source=logic),策略器立即可读——
        「在观察态到来之前供决策使用」是逻辑态的全部职能。

        - 历史「仅限显式申报豁免写端」的限制随 expect/confirm 两步机制
          废除一并解除(ADR-0651):凡逻辑推算写入统一走本口,不再有
          「记待核实预期→核对转正」的第二步;
        - 非免检通道:字段值之后仍受观察覆盖辖(§2.3 观察赢),推算与
          实读失配 = 推算代码 bug,缺陷台账留证后修推算代码——运行时
          不挂账、不对账兜底;
        - produced_by = 产生者标识(op/handler 名,留证用);
        - evidence = 可选来源注记(如刷新执行的轮键 refresh_exec@p1-r2);
        - sig = 渠道②③签名(必填;派生规则与流程 hook 系统的 ③ 写入走
          本同一口,family=logic_hook——写入口不感知触发机制,零接口预留;
          R5 W1 起 legacy 合成已退役,ADR-0634);
        - note = 可选行注记(权威纠偏记录等,§3.4.2)。
        """
        _validate_sig(sig, ('logic_action', 'logic_hook'))
        name = self._field_name(target)
        self._swap(name, Field(value=value, source='logic', evidence=evidence),
                   sig=sig, note=note)

    def relay(self, target: Field, value: Any,
              sig: ChannelSig) -> bool:
        """载体中继(§2.1,**不设第五来源类**;迁移批次二收敛)。

        接管/初始化把会话已知事实补写进**从未写过的字段**:
        - source = logic + evidence = 'session_carrier'(中继是已核实事实
          的搬运,非本帧观察,禁标 observation);
        - **已有正式值的字段一律跳过**(返回 False)——禁把 handler 已写的
          logic 翻成 observation(§8.1),真写端(write_logic/观察覆盖)优先;
        - **会话侧值已确立闸**(§2.1 空值=未知态禁中继):字符串非空、
          列表/元组非空才中继——会话载体的默认空值(''/[])是「未知」不是
          「已知事实」,中继空值会把未知固化成正式值(遮蔽帧值、拦截后到
          真值、持卡名单 [] 为假事实);恢复局新 session 的镜像字段停在
          空默认,靠本闸拒写,真值后到时字段仍未写过、可正常落;
        - sig = 渠道③签名(§3.2.4 relay 契约 family=logic_hook;必填,
          R5 W1 起 legacy 合成已退役——ADR-0634)。
        """
        if target.value is not None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
        if isinstance(value, (list, tuple, dict, set)) and not value:
            return False
        _validate_sig(sig, ('logic_hook',))
        name = self._field_name(target)
        self._swap(name, Field(value=value, source='logic',
                               evidence='session_carrier'),
                   sig=sig)
        return True

    def logic_written_fields(self) -> list[str]:
        """全部 logic 来源字段名(已直写、尚未被观察重锚——对账巡检用,§8.4)。"""
        return [f.name for f in dataclasses.fields(self)
                if isinstance(getattr(self, f.name), Field)
                and getattr(self, f.name).source == 'logic']

    def observe_screen_context(self, screen_name: str, *,
                               phase_round: tuple[int, int] | None = None,
                               resumed: bool = False,
                               top_raw: str | None = None,
                               sig: ChannelSig | None = None) -> None:
        """画面上下域写入 + 节点推进派生(R1 §3.1.4/§3.4;观察汇聚模块唯一
        写点,生产接线 = read_game_state 漏斗 ``_feed_board_state``,随分派
        观察调用 + cw_loop 开局链分支写点)。

        - 上下文对(渠道①):旧 ``current_screen`` 转 ``prev_screen`` 后写
          新值,成对变更同 group(§3.1.4);
        - 顶栏原文观察层(用户终裁 2026-09-11 字段层次终极版):top_raw 非
          空 ∧ 干净备战帧 → ``observe(top_bar_raw)`` 落画面**原始读数**
          (观察层唯一落点;序键经派生写逻辑层,禁 observe 直写序键);
        - 派生(逻辑层,同临界区——「先推进后选卡」时序语义由写入顺序自然
          保证,§3.4.1):四规则组终版(实现 = R1.2,纯 _swap 内管线无 hook
          框架),固定次序 = 节点域判定 → 类型派生:**四条腿全部
          write_logic 写逻辑层**(备战规则=解析顶栏文本成序键,同属「从观察
          数据计算逻辑值」):①备战腿(:func:`_derive_node_observed`)在干净
          备战帧 ∧ 顶栏可读时落权威值;②位面过渡腿
          (:func:`_derive_node_plane_transition`)在 0q 被采到时推进
          (plane+1, 1);③BOSS简报腿(:func:`_derive_node_boss_brief`)在
          0p 被采到时推进 当前+1 并随屏直定 boss 类型;④弹窗腿
          (:func:`_derive_node_inferred`)在守卫通过时推断 +1;类型派生
          (:func:`_write_derived_node_type`)对专属屏(遭遇/补给/策略)直定
          节点类型,商店面板未定型零写(查链接口 :func:`chain_node_type`
          预留,接线候件 B 实施批)。派生行各占版本、渠道签名 = logic_hook;
        - phase_round = 本帧顶栏 (plane, round) 读数(备战腿直读输入;弹窗腿
          缓存守卫输入,判定方案 R3 规则二③;规则②位面来源优先级第一位);
        - top_raw = 本帧顶栏原始文本(如「备战阶段 1-3」;观察层落点,缺读
          = None 不写禁猜;生产读链透传候漏斗接线批);
        - resumed = 恢复局标记(真值随恢复检测接线批带入;真 = 弹窗腿禁用
          不猜,R3 规则六)。

        上下文/派生写入无条件(journal 常开,R5 W1 影子闸折叠——ADR-0634;
        行落盘另以 sink 在场/run_id 在场为准,记录被动不分支写路径)。
        """
        if not screen_name:
            raise ValueError('observe_screen_context 拒绝空画面标识'
                             '(§2.2 同义硬边界:无观察不写)')
        seq = self.write_seq + 1
        if sig is None:
            sig = ChannelSig(family='obs', actor='cw_observation',
                             screen=screen_name, mode='read',
                             group_id=f'obs:cw_observation@{seq}')
        else:
            _validate_sig(sig, ('obs',))
        prev_val = self.current_screen.value or ''
        self._swap('prev_screen',
                   Field(value=prev_val, source='observation'),
                   sig=sig)
        self._swap('current_screen',
                   Field(value=screen_name, source='observation'),
                   sig=sig)
        # —— 观察层:顶栏原始文本(只落原始读数,禁派生值;字段层次终极版)——
        if screen_name == SCREEN_PREP_FRAME and top_raw:
            self.observe(self.top_bar_raw, top_raw, sig=sig)
        # —— 派生规则(渠道③;四规则组终版 §3.4.1,固定次序 = 节点域判定
        # → 类型派生;纯 _swap 内管线,无订阅/回调框架,用户 2026-09-10 裁)——
        if screen_name == SCREEN_PREP_FRAME and phase_round is not None:
            _derive_node_observed(
                self, node_ordinal_of(*phase_round),
                trigger_screen=screen_name, seq=seq)
        elif (screen_name in SCREEN_CONTEXT_POPUP_FAMILY
                and prev_val in SCREEN_CONTEXT_GUARD_PREV):
            _derive_node_inferred(
                self, prev_screen=prev_val, trigger_screen=screen_name,
                phase_round=phase_round, resumed=resumed, seq=seq)
        if screen_name == SCREEN_PLANE_TRANSITION:
            # 规则②·位面过渡腿(确定性腿;与④互斥按屏身份分流,判定互不
            # 依赖——④的弹窗族不含 0q,守卫交互只经 hist 去重键)
            _derive_node_plane_transition(
                self, phase_round=phase_round, seq=seq)
        elif screen_name == SCREEN_BOSS_BRIEFING:
            # 规则③·BOSS 简报腿(确定性腿;推进+boss 类型同批,返回值 =
            # 类型目标节点序,供固定次序的类型段复用)
            _derive_node_boss_brief(self, seq=seq)
        # —— 类型派生(专属画面直定半部;节点域之后同临界区)——
        # 弹窗族专属屏(遭遇/补给/策略)类型目标 = 推进后 hist(弹窗屏属
        # 即将进入的节点);0p 的类型已随规则③同批落账,此处跳过防双写。
        _direct_kind = SCREEN_NODE_TYPE_DIRECT.get(screen_name)
        if _direct_kind is not None and screen_name != SCREEN_BOSS_BRIEFING \
                and self.node_hist_ord is not None:
            _write_derived_node_type(
                self, _direct_kind, target_ord=self.node_hist_ord,
                actor='derive_node_type',
                trigger_screen=screen_name, seq=seq)

    # —— 心跳观察者(§2.4 关键结构 2)——

    def heartbeat(self) -> int:
        """单调推进量现值(写点序号,只增不减);停更检测哨兵的唯一合法
        载体——帧观察完整度标注消费即清,当不了哨兵。"""
        return self.write_seq

    def mark_frame_obs(self, level: FrameObsLevel) -> None:
        """标注本帧观察完整度(写入端;消费即清语义见 consume)。"""
        if level not in ('full', 'view', 'none'):
            raise ValueError(f'非法帧观察完整度:{level}')
        self.frame_obs = level

    def consume_frame_obs(self) -> FrameObsLevel:
        """消费帧观察完整度(消费即清 → 'none');不影响心跳计数。"""
        cur = self.frame_obs
        self.frame_obs = 'none'
        return cur


# ============================================================ 节点推进派生规则(R1 §3.4;渠道③)

def _derive_write(bs: BoardState, target: Field, value: int | NodeKey, *,
                  actor: str, trigger_screen: str, seq: int,
                  note: str = '') -> None:
    """派生规则写入(逻辑层统一形态):签名 family=logic_hook、
    actor=规则登记名、screen=关联画面、组 id = 'hook:<登记名>@<seq>'。
    value = 序值(int,node_ord 逻辑层)或节点键(NodeKey,
    类型派生经节点域写 node.kind,§3.1.3 节点域③格)。"""
    sig = ChannelSig(family='logic_hook', actor=actor, screen=trigger_screen,
                     mode='compute', group_id=f'hook:{actor}@{seq}')
    bs.write_logic(target, value, produced_by=actor, sig=sig, note=note)


def effective_node_ord(bs: BoardState) -> int | None:
    """生效序读口(派生计算,非存储字段;判定基准读口,非决策消费切换目标
    ——「node 投影改读派生域」M4 工作项已作废:cw_bs_view 现读 bs.node 镜像
    合规,无切换义务,ADR-0630 修订节 2/正本消费面申报)
    = max(node_ord 字段现值, node_hist_ord)——单字段双值结构(ADR-0630 修订
    节 2):字段现值 = 最近一次派生写入(四腿全逻辑层 write_logic),hist =
    run 内已见最大值(跃迁去重键 ``(run_id, effective_ord)`` 载体);两者之
    差仅存在于纠偏写序中间态,取 max 即生效语义,None 安全(双空 = 未定);
    消费面恒逻辑层,观察层(top_bar_raw)不参与序比较。"""
    vals = [v for v in (bs.node_ord.value, bs.node_hist_ord)
            if v is not None]
    return max(vals) if vals else None


def _derive_node_observed(bs: BoardState, candidate: int, *,
                          trigger_screen: str, seq: int) -> None:
    """备战腿·逻辑层(§3.4.1 规则二,本体照搬判定方案 R3 规则二/三):
    干净备战帧 ∧ 顶栏可读 → 解析顶栏文本成序键 → ``write_logic(node_ord)``
    (用户终裁 2026-09-11 字段层次终极版:备战规则同样是「从观察数据计算
    逻辑值」的派生规则,四腿全部写逻辑层,无 observe() 写序键的例外——
    顶栏原文的观察层落点 = ``top_bar_raw`` 字段,由观察汇聚 observe() 写)。

    跃迁判定与推进去重(设计 v3.1-N2,去重键 = ``(run_id, effective_ord)``):
    - candidate > hist → 推进写入(去重键未占,本腿越过 hist);
    - candidate == hist → 同序照写(去重键已占,不构成第二次跃迁;值未变
      行自然带 ``same_value=true``,§3.2.3 体积申报 M1 实测);
    - candidate < hist → 倒退读数,不写字段静默跳过(R3 规则三倒退免疫;
      v3.2-G10:倒退丢弃 obs_event 留证——拒读类证据占版本内嵌当时 state,
      事件词表 'arbitrate',actor 保留触发规则登记名归因,family 走 obs 族
      留证契约,同类型直定冲突先例)。
    """
    hist = bs.node_hist_ord
    if hist is not None and candidate < hist:
        # v3.2-G10 倒退留证:零状态变更,占版本(obs_event 行型 2)
        bs.note_obs_event(
            'arbitrate', 'node_ord',
            {'candidate': candidate, 'hist': hist},
            verdict='倒退读数丢弃留证(R3 规则三倒退免疫;候选 < hist 不写字段)',
            sig=ChannelSig(family='obs', actor='derive_node_observed',
                           screen=trigger_screen, mode='read',
                           group_id=f'hook:derive_node_observed@{seq}'))
        return   # 倒退读数:不写字段(R3 规则三倒退免疫)
    _derive_write(bs, bs.node_ord, candidate,
                  actor='derive_node_observed',
                  trigger_screen=trigger_screen, seq=seq)
    if hist is None or candidate > hist:
        bs.node_hist_ord = candidate   # 去重键占位:同序恰一次推进(v3.1-N2)


def _derive_node_inferred(bs: BoardState, *, prev_screen: str,
                          trigger_screen: str,
                          phase_round: tuple[int, int] | None,
                          resumed: bool, seq: int) -> None:
    """弹窗腿·逻辑层(§3.4.1 规则一,本体照搬判定方案 R3 规则二/三):
    上画面 ∈ 前驱守卫族 ∧ 当前 ∈ 弹窗族 → ``write_logic(node_ord)`` 推进 +1
    (首局无前值且非恢复局 → 1)。

    - 守卫族 = :data:`SCREEN_CONTEXT_GUARD_PREV`(中性名,语义 = 「本节点
      备战帧未被分派过」= 结算窗 ∪ 开局链,成员终版 0p/0q 出族——专用腿
      ②③,用户终裁 2026-09-11/攻击 R5 高-1);弹窗族 =
      :data:`SCREEN_CONTEXT_POPUP_FAMILY`;
    - 缓存守卫(R3 规则二③本体):弹窗帧无进度屏显,顶栏读数 = 缓存 c——
      要求 c == hist 才推断 +1;c 缺位或 ≠ hist → 零触发交腿 A 兜底;
    - 恢复局禁用(R3 规则六):hist 空 ∧ resumed → 不猜;
    - 推进去重(v3.1-N2):候选 ≤ hist 不写不锚(重入拒绝;去重键 =
      (run_id, effective_ord) 已占,同序恰一次推进)。
    """
    hist = bs.node_hist_ord
    effective = effective_node_ord(bs)
    if hist is None:
        if resumed:
            return   # 恢复局腿 B 禁用不猜(R3 规则六),消化后备战帧腿 A 接管
        candidate = 1
    else:
        if phase_round is None:
            return   # 缓存守卫输入缺位:禁用不猜(交腿 A 兜底)
        if node_ordinal_of(*phase_round) != hist:
            return   # c != hist(缓存滞后/超前):零触发,交腿 A 兜底(R3 规则二③)
        candidate = (effective + 1) if effective is not None else 1
        if candidate <= hist:
            return   # 推进去重(v3.1-N2:候选 ≤ hist 不写不锚,去重键已占)
    _derive_write(bs, bs.node_ord, candidate,
                  actor='derive_node_inferred',
                  trigger_screen=trigger_screen, seq=seq)
    if hist is None or candidate > hist:
        bs.node_hist_ord = candidate   # 去重键占位(同序恰一次推进)


def _node_key_for_ord(ordinal: int, kind: str) -> NodeKey:
    """节点序 → 节点键(坐标系公式反解,§3.4.1 v3.2-G9:ord=(plane-1)*9+round
    基 1;反解与正解同式自洽,位面切换 9→10 连续)。类型派生定位目标节点用
    ——派生域只持单序,类型落 node.kind 需 (plane, round) 键。"""
    return NodeKey(plane=(ordinal - 1) // 9 + 1,
                   round_num=(ordinal - 1) % 9 + 1,
                   kind=kind)


def _write_derived_node_type(bs: BoardState, kind: str, *, target_ord: int,
                             actor: str, trigger_screen: str, seq: int) -> None:
    """类型派生写入(§3.4.1 类型派生;经节点域③格写 bs.node,§3.1.3):
    专属画面直定该节点类型,(plane, round) 由目标序公式反解。

    - 冲突纪律(G10 同簇):镜像现值已在目标节点且类型不一致 → obs_event
      留证(event='arbitrate',禁静默覆盖)+ 最新直定值落位(最新观察 =
      真相);直定证据 = 画面现身锚,属观察级事实,sig 走 obs 族
      (note_obs_event 契约),actor = 触发规则登记名保留归因;
    - 已知边界(申报):弹窗族屏重入/缓存滞后形态下目标 = hist,若历史
      推进与屏所属节点错位,类型暂挂错节点——后续备战帧真读类型经观察
      覆盖纠偏(§2.3 观察赢,失配缺陷行显影),禁在派生段预判屏-节点错位
      (无判据,猜即第二错源);
    - 商店面板块不专属 → 不入直定映射(observe_screen_context 分流),
      类型「未定型」零写;查现行链接口 = :func:`chain_node_type`。
    """
    key = _node_key_for_ord(target_ord, kind)
    cur = bs.node.value
    if cur is not None and cur.plane == key.plane \
            and cur.round_num == key.round_num and cur.kind != kind:
        bs.note_obs_event(
            'arbitrate', 'node',
            {'old_kind': cur.kind, 'new_kind': kind, 'node_ord': target_ord},
            verdict='类型直定冲突留证(同节点两直定值不一致,最新直定赢)',
            sig=ChannelSig(family='obs', actor=actor, screen=trigger_screen,
                           mode='read',
                           group_id=f'hook:{actor}@{seq}'))
    _derive_write(bs, bs.node, key, actor=actor,
                  trigger_screen=trigger_screen, seq=seq)


def _derive_node_plane_transition(bs: BoardState, *,
                                  phase_round: tuple[int, int] | None,
                                  seq: int) -> None:
    """位面过渡腿(§3.4.1 规则二·R1.2;actor=derive_node_plane_transition):
    0q 被采到 → 逻辑节点 = (当前位面+1, 1),经节点序坐标系公式落单整数
    写入 ``node_ord``(逻辑层)。

    - 「当前位面」来源优先级:①调用方顶栏读数 phase_round(测试/未来漏斗
      直读形态;生产 cw_loop 分支写点不带)②bs.node 观察镜像 plane(顶栏
      权威链遗产)③hist 反解((hist-1)//9+1)——三源全缺 = 「当前位面」
      不可知(开局过渡屏形态),禁猜不写,交规则①④计数;
    - 共同语义:候选 ≤ hist 不写不锚(重复 0q loop pass 重入拒绝,去重键
      =(run_id, effective_ord) 已占,同序恰一次推进);
    - 零类型写:过渡屏链 = 离开位面链(件 B v1.1 §3.1.1 F1 定谳),下位面
      节点类型不可自定——新节点类型由后继专属屏/备战帧链读链承接。
    """
    hist = bs.node_hist_ord
    plane: int | None = None
    if phase_round is not None:
        plane = int(phase_round[0])
    elif bs.node.value is not None:
        plane = int(bs.node.value.plane)
    elif hist is not None:
        plane = (hist - 1) // 9 + 1
    if plane is None or plane < 1:
        return   # 当前位面不可知:禁猜(R3 禁猜纪律;开局过渡屏交①④计数)
    candidate = plane * 9 + 1        # (plane+1, 1) = (plane+1-1)*9+1
    if hist is not None and candidate <= hist:
        return   # 重入拒绝(v3.1-N2:候选 ≤ hist 不写不锚,去重键已占)
    _derive_write(bs, bs.node_ord, candidate,
                  actor='derive_node_plane_transition',
                  trigger_screen=SCREEN_PLANE_TRANSITION, seq=seq)
    bs.node_hist_ord = candidate     # 去重键占位(同序恰一次推进)


def _derive_node_boss_brief(bs: BoardState, *, seq: int) -> int | None:
    """BOSS 简报腿(§3.4.1 规则三·R1.2;actor=derive_node_boss_brief):
    0p 被采到 → 逻辑节点 = 当前节点 + 1,类型 = BOSS 随简报证据自带
    (禁写死 round=9——boss 序位随位面格数/环境加节点漂移,序位只由
    「当前+1」承载)。双写 node_ord(逻辑层)+ node.kind(类型派生经节点域,
    §3.4.1 规则三动作面),同 actor 同批 = 同 group。

    - 当前节点 = effective_ord(max 双派生字段);未知 → +1 不可计算,
      禁猜不写(交腿 A/④计数);
    - 重复触发判别(幂等锚):本腿推进时同批把镜像写为 boss 节点键
      (类型随简报自带 = 本腿的工作回执)——镜像已锚在 hist 且类型 boss
      = 本简报节点已被计数 → 零写返回 hist(简报屏多 loop pass 重入不
      重推;候选 effective+1 以移动中的 effective 为基,单独 ≤ hist 判不
      出本腿自身推进后的重入,锚即判别器)。残余边界(申报):镜像 boss
      类型经读链继承窗延续到后续节点且恰停 hist 的形态可致假锚漏推一次
      ——漏推由腿 A 备战帧顶栏兜底计数,节点键无永久偏斜;
    - 返回值 = 类型目标节点序(observe_screen_context 固定次序的预留读
      位),不可推进时返回 None。
    """
    hist = bs.node_hist_ord
    effective = effective_node_ord(bs)
    if effective is None:
        return None   # 当前节点未知:禁猜
    cur = bs.node.value
    if cur is not None and cur.kind == 'boss' \
            and node_ordinal_of(cur.plane, cur.round_num) == hist:
        return hist   # 幂等锚命中:本简报节点已计数,零写(防重推)
    candidate = effective + 1
    if hist is not None and candidate <= hist:
        return hist   # 去重键已占(先行腿已推进):boss 节点 = hist
    _derive_write(bs, bs.node_ord, candidate,
                  actor='derive_node_boss_brief',
                  trigger_screen=SCREEN_BOSS_BRIEFING, seq=seq)
    bs.node_hist_ord = candidate     # 去重键占位(同序恰一次推进)
    _write_derived_node_type(bs, 'boss', target_ord=candidate,
                             actor='derive_node_boss_brief',
                             trigger_screen=SCREEN_BOSS_BRIEFING, seq=seq)
    return candidate


# ============================================================ 现行链查询接口(件 B 设计 v1.1 §3.4 语义预留,R1.2)

@dataclass(frozen=True)
class ChainQuery:
    """现行链单点查询返回值(件 B 设计 v1.1 §3.4 接口语义;R1.2 只落形态,
    查链接线归件 B 实施批 B-2/B-3):

    - token = 现行链该位**原值,零内建回落**——None = 「现行链不知道」
      (链缺/位越界/本帧未辨/past 位),语义是不知道,不是「该位不存在」;
      调用方按自身仲裁序兜底(回落序归消费方规则本体,§3.8-C1/C2);
    - hu_dist = 现行链读数残差(置信参考;token=None 时恒 None)。
    """

    token: str | None = None
    hu_dist: float | None = None


def chain_node_type(bs: BoardState, plane: int, round_num: int) -> ChainQuery:
    """现行链节点类型查询(件 B 设计 v1.1 §3.4 接口预留;只读,零读屏零
    OCR,查询面 = ``node_path`` 现行链帧事实字段)。

    - 本批态:链写端(备战帧链识别升格)归件 B 实施批,生产零写端 → 恒
      token=None(诚实缺位;**零内建回落**禁把基线/台账当兜底,件 B F2
      回落废除裁定);
    - 链在位时位寻址 = seq[i] 第 i+1 轮(round 基 1,与本位面跨度语义一致,
      件 B F9);位越界/链跨位面错配 = None。NodeChain 精化与基线/改写位
      两接口(chain_baseline/chain_rewritten)归件 B 实施批,本口不预纳;
    - 商店面板块类型「未定型」查现行链的接线候件 B 实施批(本批不接——
      未定型 = 零写,禁猜)。
    """
    chain = bs.node_path.value
    if not chain:
        return ChainQuery(token=None)
    idx = int(round_num) - 1
    if idx < 0 or idx >= len(chain):
        return ChainQuery(token=None)
    token = str(chain[idx]) if chain[idx] is not None else None
    return ChainQuery(token=token)


# ============================================================ 心跳观察者


def note_board_state_heartbeat(ctx_or_session: object) -> None:
    """心跳观察者采样(§2.4;生产接线点 = cw_loop 备战分支)。

    读单调推进量现值并与上次采样比对:连续 ≥2 次零推进 = 观察断流诊断
    (log.warning 留痕,**不停机**——停更处置交既有守卫链;首个备战环只
    建基线不计数)。宿主可传 ctx(取 ctx.cw_match.session)或 session 本体
    (测试/sim)。
    """
    match = getattr(ctx_or_session, 'cw_match', None)
    session = (getattr(match, 'session', None) if match is not None
               else ctx_or_session)
    if session is None:
        return
    bs = board_state_of(session)
    if bs.hb_prev_seq is None:
        pass    # 首采:只建基线
    elif bs.write_seq == bs.hb_prev_seq:
        bs.hb_stall_count += 1
        if bs.hb_stall_count >= 2:
            log.warning('[cw!][bs-heartbeat] BoardState 观察断流:连续 %d 次'
                        '采样零推进(写点序号 %d)——检查 read_game_state '
                        '观察链是否被跳过', bs.hb_stall_count, bs.write_seq)
    else:
        bs.hb_stall_count = 0
    bs.hb_prev_seq = bs.write_seq


# ============================================================ sim 合成口


def synthesize_from_game_state(bs: BoardState, st: GameState, *,
                               at_round: str = '') -> None:
    """sim 合成口:GameState 真值 → BoardState 观察(§2.1)。

    - sim 无识别过程 = 恒真值帧:可读字段全记 observation,evidence 恒带
      ``sim:synthesized``(at_round 非空时并入轮键后缀
      ``sim:synthesized@p{plane}-r{round}``,供遥测定位合成时点——P2-6
      落地审:参数必有消费);真值 None/未建模域不写(保持 None,禁合成假值);
    - **bench 槽位保序映射**(§3.2.5 任务书件 7):GameState.bench 的
      0 基下标 1:1 映射物理槽位(BenchChar → kind='unit',None → 'empty'),
      记录模型按实机真值箱占席——sim「无箱实体」只是内部口径约定,
      不进记录模型(占席谓词 = :func:`slot_occupies`,箱/秘典占席);
    - at_round = 轮键('p{plane}-r{round}' 形,登记期快照);
    - **payload 域离屏分支**(§2.2 例外):shop 真值缺席 = 结构离屏(置
      None+left_screen,等价 leave_screen);encounter/supply 两域 sim 不建模,
      恒离屏口径——三 payload 域在合成帧恒反映「当前画面事实」,禁旧
      payload 连旧 evidence 残留。**空表与 None 同判 = 离屏**(边界申报):
      sim 真值域无 OCR 失读态,GameState.shop 空表 = 「不在商店」的真值
      形态(开店帧恒有五张);与 live 观察链「空牌面 = OCR 失读不写、非本
      画面才离屏」的语义分叉是有意申报(真值域 vs 识别域)。
    """
    _ev = f'{SIM_SYNTHESIZED}@{at_round}' if at_round else SIM_SYNTHESIZED
    # sim 合成签名(R1 §3.2.1:obs 族子模 mode='synthesized'——sim 真值合成
    # 与实机真读可分;actor = 本口登记名,质量语义与 evidence 标记同源)
    _synth_sig = ChannelSig(family='obs', actor='synthesize_from_game_state',
                            mode='synthesized')
    # node_type None(裸 GameState 未建模该帧)不写 node——禁 'prep' 占位
    # 假值(P1-1 同型泛化;engine 路径 node_type 恒引擎真值不受影响)
    _node_type = getattr(st, 'node_type', None)
    if _node_type is not None:
        bs.observe(bs.node,
                   NodeKey(plane=int(getattr(st, 'plane', 1) or 1),
                           round_num=int(getattr(st, 'round_num', 1) or 1),
                           kind=str(_node_type)),
                   evidence=_ev, sig=_synth_sig)
    else:
        _prev_node = bs.node.value
        if _prev_node is not None:
            bs.observe(bs.node,
                       NodeKey(plane=int(getattr(st, 'plane', 1) or 1),
                               round_num=int(getattr(st, 'round_num', 1) or 1),
                               kind=_prev_node.kind),
                       evidence='kind_inherited', sig=_synth_sig)
        # 无现值且未读:node 不写,保持 None(诚实缺位)
    if getattr(st, 'gold_readable', True) and st.gold is not None:
        bs.observe(bs.gold, int(st.gold), evidence=_ev, sig=_synth_sig)
    if getattr(st, 'level_readable', True):
        bs.observe(bs.level, int(st.level), evidence=_ev, sig=_synth_sig)
    if st.xp_progress is not None:
        bs.observe(bs.xp, tuple(st.xp_progress), evidence=_ev, sig=_synth_sig)
    if st.streak is not None:
        bs.observe(bs.streak, int(st.streak), evidence=_ev, sig=_synth_sig)
    if st.hp is not None:
        bs.observe(bs.hp, int(st.hp), evidence=_ev, sig=_synth_sig)
    # deploy_cap(§2.3 W5 入容器):sim 真值直写;None(未建模帧)不写。
    if st.deploy_cap is not None:
        bs.observe(bs.deploy_cap, int(st.deploy_cap), evidence=_ev,
                   sig=_synth_sig)
    # back_layout(back_max 语义裁决·闸门二,sim 合成口扩员——W5 §2.6
    # 清单增补第八域,与实机喂入口域覆盖集对齐):sim 真值直写(动态真值
    # = GameState.back_max,场景侧设定;实机写端 = 选档裁决链,两写端
    # 同域不同源,sim 无识别过程故恒真值);缺席不写(禁合成假值,同
    # 七域纪律)。
    if st.back_max is not None:
        bs.observe(bs.back_layout, int(st.back_max), evidence=_ev,
                   sig=_synth_sig)
    # 开局域/席位/装备(W5 合成口与实机喂入口域覆盖集对齐;§2.6):
    # sim 无识别过程,真值域恒 observation + evidence=sim:synthesized。
    if st.plane_bosses:
        bs.observe(bs.plane_bosses, list(st.plane_bosses), evidence=_ev,
                   sig=_synth_sig)
    if st.enemy_affixes:
        bs.observe(bs.enemy_affixes, list(st.enemy_affixes), evidence=_ev,
                   sig=_synth_sig)
    if st.active_env:
        bs.observe(bs.active_env, str(st.active_env), evidence=_ev,
                   sig=_synth_sig)
    if st.equips:
        bs.observe(bs.equips, list(st.equips), evidence=_ev, sig=_synth_sig)
    # front_row/back_row:sim 槽位表(0 基 0-3 前/4-9 后)→ 行内 Unit
    # (行内 1 基 slot 信息位;阵营不入容器,装备随 BenchChar 透传)。
    _front_u: list[Unit] = []
    _back_u: list[Unit] = []
    for _i, _bc in enumerate(st.deployed or []):
        if _bc is None or not getattr(_bc, 'char_id', ''):
            continue
        _u = Unit(char_id=str(_bc.char_id),
                  star=int(getattr(_bc, 'star', 1) or 1),
                  equips=list(getattr(_bc, 'equips', None) or []),
                  slot=(_i + 1) if _i < 4 else (_i - 3))
        (_front_u if _i < 4 else _back_u).append(_u)
    if _front_u or _back_u:
        bs.observe(bs.front_row, _front_u, evidence=_ev, sig=_synth_sig)
        bs.observe(bs.back_row, _back_u, evidence=_ev, sig=_synth_sig)
    bench_slots: list[BenchSlot] = []
    for i, bc in enumerate(st.bench):
        if bc is None:
            bench_slots.append(BenchSlot(kind='empty'))
        else:
            bench_slots.append(BenchSlot(
                kind='unit',
                unit=Unit(char_id=str(getattr(bc, 'char_id', '') or ''),
                          star=int(getattr(bc, 'star', 1) or 1),
                          equips=list(getattr(bc, 'equips', None) or []),
                          slot=i + 1)))
    # 输出补齐到容量:定长槽位表是记录模型的形状契约(§3.2.5/ADR-0316 同构),
    # 兼容旧紧缩构造(前缀顺延占用)不丢槽位语义。
    while len(bench_slots) < BENCH_CAPACITY_DEFAULT:
        bench_slots.append(BenchSlot(kind='empty'))
    bs.observe(bs.bench,
               BenchView(slots=bench_slots, capacity=BENCH_CAPACITY_DEFAULT),
               evidence=_ev, sig=_synth_sig)
    if getattr(st, 'board_readable', True) and st.board:
        bs.observe(bs.board, dict(st.board), evidence=_ev, sig=_synth_sig)
    if st.shop:
        # 牌转换 = 映射单一源(W5 双 ShopCard 归一;cost_source 原值透传
        # 不折叠,roster_fallback 的「徽章失读」证据分级禁丢)
        cards = [shop_card_to_container(c) for c in st.shop]
        probs = ({int(k): float(v) for k, v in st.refresh_probs.items()}
                 if st.refresh_probs else {})
        bs.observe(bs.shop, ShopPayload(cards=cards, refresh_probs=probs),
                   evidence=_ev, sig=_synth_sig)
    else:
        # 画面附加域离屏分支(§2.2 显式例外):sim 真值
        # 帧无商店牌 = 「不在商店」的结构事实——非当前画面置 None(等价
        # leave_screen,evidence=left_screen),禁沿用旧 payload 连旧 evidence
        # (残留会把离屏帧误读成「商店仍开着」)。此为「空则不写」的漏申报
        # 面补口:payload 域的语义 = 当前画面的 payload(§8.4)。
        bs.leave_screen(bs.shop, sig=_synth_sig)
    # encounter/supply 两 payload 域:sim 的 GameState 不建模这两域(attr
    # 缺席 = sim 模型里结构离屏)——同口径置 left_screen,保持「三 payload
    # 域在合成帧恒反映当前画面事实」的域语义;观察真值不进合成(sim 无
    # 识别过程),禁合成假值。
    bs.leave_screen(bs.encounter, sig=_synth_sig)
    bs.leave_screen(bs.supply, sig=_synth_sig)
    if st.active_strategies:
        bs.observe(bs.active_strategies, list(st.active_strategies),
                   evidence=_ev, sig=_synth_sig)
    bs.mark_frame_obs('full')
