"""货币战争 GameState 局内记录(迁移批次一骨架)。

**正本入口** = ``docs/develop/sr_od/application/currency_war/game_state/README.md``(总纲);
**字段级规格正本** = ``docs/develop/sr_od/application/currency_war/game_state/fields.md``
(本文注释所引节号体系 §1-§8 的解析归宿)。
GameState(正名前暂名 BoardState,ADR-0630 后果节+W8 候裁7)= 当前仍为真的局内已知事实快照:单例,每局新建,
只描述「此刻」;画面 op 与决策 op 写,策略器读(设计 §1)。历史序列归遥测,
不经本结构。

**与推演内核帧 CwSimFrame 的关系**:平行表示,不是镜像——本容器 =
实机真值记录模型(只记录实机会产生的已知事实);``CwSimFrame``
(kernel/cw_vocab)= sim 侧局面帧类型(sim 转移/检查/离线重建面载体)。
生产写入 = **引擎直写**(sim 引擎内部工作态即本容器,经渠道签名写入口
落字,渠道族封闭集见下文遥测段);容器值禁回写帧字段(策略与引擎经容器
读口读值为合法)。逐字段映射对账正本 =
docs/develop/sr_od/application/currency_war/game_state/fields.md §9。
字段准入按设计 §8.8 治理三件:派生量(席空数/席满判定/board 下档阈值)
是计算函数不存储;识别质量位是写入闸门不存储(失读统一口径 =
§2.2 carried/机制性 None)。

**两个关键结构**(设计 §2.4;预期条目表已随两态制废除):
1. 帧观察完整度标注 + 心跳——标注(full/view/none)消费即清;停更检测
   哨兵用只增不减的写点序号 :attr:`GameState.write_seq`,不用标注现值。
2. gs_schema——域粒度版本映射(缺域键 = 该域未建模,§3.7.1)。

**两态直写**(ADR-0651,2026-09-11 用户裁定):字段来源只保留 observation
与 logic 两种——逻辑推算值经 :meth:`GameState.write_logic` 直接写字段
(source=logic,策略器立即可读),expect/confirm 两步机制(预期条目表/
PendingEntry/confirm 转正/discard_expected)全套废除;逻辑态错误 =
代码 bug(修推算代码,不靠运行时挂账对账兜底)。观察赢原则不变(§2.3):
下一帧实读覆盖 logic,失配缺陷台账留证。

**逻辑随机态**(来源 logic_rand,:meth:`GameState.write_logic_rand` 直写):
逻辑态的随机效果扩展——**效果随机的动作采样链**写入:上报函数真掷
随机,把采样结果当真实发生走完整确定性链;值 = 一个可能世界的快照
(采样值/未变标记/确定外壳三形态),真值结构上不可由推算钉死(实机上
采样是猜测,sim 里采样即世界真值——同一上报函数两副面孔)。与逻辑态的
两条语义分界:①观察覆盖差异 = 随机效果落地,**预期内非 bug**——只落
``logic_rand_outcome`` 台账行留证(无告警无停机,随机模型校准遥测面),
不进失配三分流;②策略器消费前**必须重观察**(查询口 =
:meth:`GameState.logic_rand_fields`;跨动作污染经
:meth:`GameState.any_logic_rand` 入口判定继承)。

**单例宿主** = session 旁表(:func:`game_state_of`;同 ``cw_exec_state``
旁表模式,弱引用表 + 桩面兜底)——session 对象 = 局身份,新局新 session
即天然新建,符合「单例,每局新建」(§1/§6.2)。

**帧→容器合成口** = :func:`synthesize_from_game_state`(正式入口包装 =
:func:`feed_sim_truth`):CwSimFrame 真值合成时记 observation,evidence
恒带 ``sim:synthesized``(§2.1)——生产 sim 引擎已直写容器(见上段),
本口现役消费面 = 离线/测试构造(生产零调用);
bench 槽位保序映射——记录模型按实机真值箱占席(§3.2.5),不采 sim
「无箱实体」的内部口径约定。

**统一 state 遥测升级(R5 W1 常开化后形态)**:写入 API 全部带**必填**渠道签名
(:class:`ChannelSig`,渠道族封闭集 obs/logic_action/logic_hook + 字段级
质量元数据;R5 迁移规划 W1/ADR-0634,集内无空 actor 行);:attr:`GameState.write_seq`
升格为**版本 id**(每次写入单调分配,不重不漏,:meth:`GameState.current_version`
读口);每次写入落一行**自足状态流水**(行 = 改了什么 + 渠道签名 + 版本 id +
写入后完整 state 快照,行行自足查询直接读——无快照锚/无对账自检/无前溯推导,
禁回归)。落盘由 :mod:`sr_od.application.currency_war.kernel.cw_state_journal`
承载,**无条件常开**(生产装配 = currency_war_app 装配段 + 局容器单例建立点
兜底——遥测装配 = game state 职责(用户裁定 2026-09-15 精化令):触发
只钉 :func:`game_state_of` 建立路径,GameState 构造器零装配逻辑;无开关;
行落盘另以 sink 在场与 run_id 在场为准,sink 缺席 = 行不落而写路径照常——
记录被动,不改写路径语义)。新增**逻辑态
派生域与画面上下文域**(ADR-0630 决策 1+修订节 2;字段面 as-built =
``docs/develop/sr_od/application/currency_war/game_state/node-domain.md`` §2):``prev_screen``/``current_screen``
(①观察汇聚写)+ ``top_bar_raw``(顶栏原文,**观察层**,observe() 只落原始
读数)+ ``node_ord``(**逻辑层序键**,派生规则唯一写点;用户终裁 2026-09-11
字段层次终极版:观察层只放画面原始读数,序键是逻辑层字段,四条腿全部
write_logic,无 observe 写序键的例外)。
四规则组:①备战腿顶栏权威/②位面过渡腿 0q→(plane+1,1)/③BOSS简报腿
0p→当前+1+boss 类型/④弹窗腿守卫族;推进去重键 =(run_id, effective_ord),
类型派生 = 专属画面直定+商店面板查现行链(已接线,链观察落地批
2026-09-16:载体 TokenCell/NodeChain,写端 = 过渡屏 transition_row/
transition_snapshot + 备战帧 prep_row,字段 node_path/node_path_baseline)。本段持久正本 =
``docs/develop/sr_od/application/currency_war/decisions/0630-unified-state-journal.md``
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
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # 选项类宿主 = cw_events(其模块级 import 本模块,反向 import 即循环;
    # 终态契约契约 g:TYPE_CHECKING 承载,运行时零依赖)
    from sr_od.application.currency_war.kernel.cw_events import (
        EncounterOption,
        MegastarOption,
        PartnerOption,
        PlannerOption,
        SupplyOption,
    )
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    ActiveEffectInventory,
)
from sr_od.application.currency_war.kernel.cw_encounter_selection import (
    EncounterLog,
    SettlementRing,
)

# 失配处置策略(豁免注册表 + 安灯钩子槽;kernel→kernel 单向依赖,
# 对方零依赖本模块)。observe() 失配三分流路由消费(见 _route_logic_mismatch)。
from sr_od.application.currency_war.kernel.cw_mismatch_policy import (
    fire_reconcile_andon,
    lookup_mismatch_exempt,
)
from sr_od.application.currency_war.kernel.cw_registry import DEFAULT_REGISTRY

# 同桶直调(kernel→kernel 合法;遥测装配 = game state 初始化职责,用户
# 裁定 2026-09-15)。本模块无反向模块级 import(其 kernel 依赖均为函数内
# 惰性),模块级 import 不成环。
from sr_od.application.currency_war.kernel.cw_state_journal import (
    ensure_journal_assembly,
)

if TYPE_CHECKING:
    # 仅类型注解引用(项目规范);运行时按鸭子类型读 CwSimFrame 属性,
    # 避免与 cw_state 建立运行时依赖(cw_state 将来消费本模块时不成环)。
    from sr_od.application.currency_war.kernel.cw_vocab import (
        CwSimFrame,
        ShopCard,
    )


# ============================================================ 常量

#: 备战席容量默认恒 9,不随等级/职级变化(§3.2.5;现役同口径常量 =
#: ``cw_state.BENCH_CAPACITY``)。唯一改写源 = 节省工位时限效果(激活期 3、
#: 3 节点后自动回 9,经效果账本 §5.1 逻辑写入)。
BENCH_CAPACITY_DEFAULT: int = 9

#: 行级 schema 版本(§3.7.1)。域版本映射见 ``DEFAULT_GS_SCHEMA``。
GAME_STATE_SCHEMA_VERSION: int = 1

#: 域粒度版本映射的当前全集(缺域键 = 该域未建模,禁建「None=未建模」占位
#: 字段,§2.2/§8.8)。域增删或字段语义破坏性变更时 bump 对应域版本。
DEFAULT_GS_SCHEMA: dict[str, int] = {
    'node': 2,              # node/node_path/node_path_baseline(§3.2.1/§3.2.2;域版本 2 =
                            # node_path 值形 list[str] → NodeChain 载体(逐格 TokenCell 元数据)
                            # + 新增基线链字段 node_path_baseline,链观察落地批 2026-09-16)
    'units': 1,             # front_row/back_row/bench/back_layout(§3.2.3-§3.2.7)
    'economy': 1,           # gold/level/xp/streak/hp/level_up_cost(§3.2.9-§3.2.13)
    'match_facts': 2,       # 职级/对局类型/敌人难度/boss/词缀/环境/持卡/board/接管恢复旗标(§3.1/§3.2.6/§3.2.14/§3.2.20;域版本 2 =
                            # 接管/恢复三字段(resumed_match/takeover_collect_done/
                            # takeover_tries)迁入,渠道③接管协议 logic_hook)
    # (refresh_counters 域已随 2026-09-18 用户裁决迁出容器:三字段住效果
    #  账本 ActiveEffectInventory(统一计算,写端 = 刷新上报函数),域版本
    #  面退役,考古走 git。)
    'node_screen_refresh': 2,  # 节点屏刷新计数组(§3.4.1-§3.4.4;遭遇/补给/环境/策略逐卡)
                               # 域版本 2 = 新增顶层字段 encounter_refreshed_in_visit
                               # (encounter 刷新建议 per-visit 位,终态契约)
    'invest_opts': 1,          # 投资双画面候选槽(§3.4 终态契约八新槽;str 原文名)
    'megastar_opts': 1,        # 盛会之星候选槽(list[MegastarOption],typed)
    'partner_opts': 1,         # 列车同行候选槽(list[PartnerOption],typed)
    'planner_opts': 1,         # 骇入策划候选槽(list[PlannerOption],typed)
    'star_tome_opts': 1,       # 星徽秘典候选槽(str)
    'wish_trial_opts': 1,      # 祈愿试炼候选槽(str)
    'box_card_opts': 1,        # 武装箱候选槽(str)
    'fortune_opts': 1,         # 命运卜者强化候选槽(str;契约扩员 12→15)
    'expert_invite': 1,        # 专家邀请函选卡载体(ExpertInvitePayload;契约扩员 12→15)
    'equip_pick_opts': 1,      # 选择装备候选槽(str;契约扩员 12→15)
    'inventory': 1,         # equips/consumables/免战牌(§3.2.15/§3.2.16/§3.2.19〔勘误:免战牌正本=effect_inventory.remaining_uses,§8.6-3——本域不含其字段〕)
    'spheres': 1,           # 晶矿(§3.2.8,不占席)
    'substate': 1,          # 分类子态/事件浮层(§3.2.17/§3.6.1)
    'shop': 1,              # 商店开态 payload(§3.3)
    'encounter': 2,         # 遭遇屏 payload(§3.4.1;域版本 2 = options 形状
                            # 升级 typed EncounterOption,终态契约)
    'supply': 2,            # 补给屏 payload(§3.4.2;域版本 2 = options 形状
                            # 升级 typed SupplyOption,终态契约)
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
    'round_ledger': 1,      # 轮内新鲜度账(round_fresh_buys;渠道②动作上报,
                            # 值形状 {'phase': (plane, round_num)|None,
                            # 'names': list[str]},经 record_fresh_buy 单口)
}

#: 画面附加域(§2.2 显式例外):语义 = 「当前画面的 payload,非当前画面
#: =None」——离开画面置 None 是结构事实非失读,不受 carried 硬边界辖。
#: 值 = (属屏, route_clearable) 二元组(终态契约路由清点:属屏 = 分发键
#: 建档屏名;route_clearable=False = 挂点跳过,清点源独占)。`shop` 保留
#: 映射内 False(leave_screen 域守卫依赖,清点由既有两处显式口独占);
#: `prep_obs` 不入映射(语义豁免)。
_PAYLOAD_DOMAINS: dict[str, tuple[str, bool]] = {
    'shop': ('货币战争-备战-开商店', False),
    'encounter': ('货币战争-遭遇节点', True),
    'supply': ('货币战争-补给', True),
    'invest_strategy_opts': ('货币战争-投资策略', True),
    'invest_env_opts': ('货币战争-投资环境', True),
    'megastar_opts': ('货币战争-盛会之星', True),
    'partner_opts': ('货币战争-列车同行', True),
    'planner_opts': ('货币战争-骇入策划', True),
    'star_tome_opts': ('货币战争-星徽秘典弹窗', True),
    'wish_trial_opts': ('货币战争-祈愿试炼', True),
    'box_card_names': ('货币战争-备战-武装箱选择', True),
    'fortune_opts': ('货币战争-命运卜者强化', True),
    'expert_invite': ('货币战争-备战-专家邀请函', True),
    'equip_pick_opts': ('货币战争-选择装备', True),
}


# ---- 画面上下文域常量(R1 §3.1.4/§3.4;派生规则输入面)----

#: 干净备战帧画面标识(画面建档 screen_name;备战腿触发面)。
SCREEN_PREP_FRAME: str = '货币战争-备战'

#: 商店面板块画面标识(弹窗族成员;节点类型「未定型」零直定——商店对任意
#: 节点类型都开,类型来源 = 类型派生四②「商店查现行链」,链观察落地批
#: 2026-09-16 接线)。
SCREEN_SHOP_PANEL: str = '货币战争-备战-开商店'

#: 弹窗族清单(R1 §3.4.1 规则一;成员照搬判定方案 R3 §3.3 规则一四类:
#: 遭遇/投资策略/补给/商店面板——「按下一节点类型自动弹」中有独立分发分支
#: 的四类;巨星/祈愿非节点边界标记不入清单,R3 §5-③.1 残留申报)。
SCREEN_CONTEXT_POPUP_FAMILY: frozenset[str] = frozenset({
    '货币战争-遭遇节点',
    '货币战争-投资策略',
    '货币战争-补给',
    SCREEN_SHOP_PANEL,
})

#: 弹窗腿守卫集(§3.4.1 规则四;语义 = 「本节点备战帧未被分派过」的画面侧
#: 判据。**成员终版 = 结算窗 ∪ 开局链,0p/0q 出族**(用户终裁 2026-09-11,
#: ADR-0630 修订节·守卫族终版:守卫族残留 0p/0q 会与专用腿②③构成级联双推进——专用腿推进
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
#: 节点类型都开(非专属)→ 类型「未定型」零直定写;其类型来源 = 规则四②
#: 「商店查现行链」(:func:`chain_node_type`,链观察落地批接线,见派生步
#: 商店分支)。目标节点坐标系 = 专属屏所属节点(弹窗族屏 = 即将
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

#: 来源五分类字面量(§2.1;observation/logic = 两态制本态,logic_rand =
#: 逻辑随机态扩展,carried/prior = obs 族来源子模)。
FieldSource = Literal['observation', 'logic', 'logic_rand', 'carried', 'prior']

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
OBS_EVENT_EVENTS: tuple[str, ...] = ('arbitrate', 'miss', 'popup', 'chain_diff')

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
    'CwScreenPlaneTransition',  # 位面过渡 op(过渡屏链观察写点:基线链
                               # transition_row/离场快照 transition_snapshot,
                               # 链观察落地批 2026-09-16)
    'CwScreenBattleWait',      # 战斗/结算画面 op(结算覆盖写端,§3.5.1)
    'CwScreenBookcard',        # 星徽秘典弹窗(chosen_tome 选择写点)
    'CwScreenBriefing',        # 简报(enemy_difficulty 恒稳基线写端,终态契约 §B)
    'CwScreenEncounter',       # 遭遇弹窗(chosen_encounter/刷新计数写点)
    'CwScreenExpertInvite',    # 专家邀约(chosen_expert 选择写点;
                               # expert_invite 弹窗载体写点,普查迁移批 2)
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
    'synthesize_from_game_state',  # sim 合成口(§2.1;波 5 起为直写喂入口写入实现)
    'feed_sim_truth',             # sim 真值直写喂入口(波 5 喂入反转正式入口)
    'EvolutionEngine',            # 阵容演进引擎(事务发射行 receipts 写点,波 5 接线)
    # —— R2 动作 op 写入接线(渠道② logic_action,§3.2.1 登记类属 =
    # 「动作 op / handler 类名」;actor = 执行动作的 op 类,动作身份由
    # 回执记录 op 字段承载)——
    'PrepActionExecutor',      # 备战动作执行器(动作全集唯一分派点)
    'CwScreenBuyCards',            # 商店单动作循环(run_buy_waves;含刷新执行
                               # 事实组 record_refresh_execution 的计数写入)
    # —— 动作 op 重组批③(design.md §1.1):CwActionXxxOp(SrOperation)
    # 自上报,actor = type(self).__name__,随 op 类名单体登记 ——
    'CwActionBuyCardOp',
    'CwActionRefreshShopOp',
    'CwActionCloseShopOp',
    'CwActionSellBenchOp',
    'CwActionLevelUpOp',
    'CwActionDeployMoveOp',
    'CwActionSellDeployedOp',
    'CwActionWearEquipOp',
    'CwActionCollectOreOp',
    'CwActionOpenBoxOp',
    'CwActionOpenTomeOp',
    'CwActionOpenBookcardOp',
    'CwActionToolUseOp',
    'CwActionStartBattleOp',
    'CwActionOpenShopOp',
    'CwActionPickEncounterOp',
    'CwActionPickSupplyOp',
    'CwActionPickMegastarOp',
    'CwActionPickPartnerOp',
    'CwActionPickPlannerOp',
    'CwActionObsOp',           # 环内重观察(自上报零写占位;容器更新通道 =
                               # 观察漏斗本体,actor 登记 = 回执统一形态)
    'CwOpOpenShop',            # 开商店原子(op 函数与独立壳同名登记)
    'CwOpCloseShop',           # 关商店原子
    'CwFlowStrategy',          # 商店序列驱动器·基类缺省(逻辑态直写,波 4)
    'MandateV1Strategy',       # 商店序列驱动器·mandate 覆写(逻辑态直写,波 4)
    'CwLoop',                  # 外循环(开局链分支标识写点,obs 族 ①)
    'EffectLedgerBridge',      # 效果账本→字段桥(容量逻辑态直写/增额授予;v3.2-G4
                               # §3.2.1 登记类属补项;R5 W1 起显式签名)
    'SimEngineP1',             # sim P1 引擎(外部事件 obs 族写点
                               # ——收入/结算/回合初始化/开局播种/装备发放/
                               # 部署代理;动作应用走 logic_action 族转移函数)
    'CwReconcile',             # 对账模块(kernel/cw_reconcile;观察态
                               # 锚定写点——屏幕真值写回成功置
                               # tracked_account_observed=True)
    'CwDeployLogic',           # 轮内新鲜度账单口(kernel/cw_deploy_logic.
                               # record_fresh_buy 的 round_fresh_buys
                               # 容器 Field 写点,渠道②动作上报)
    # —— 策略器终态契约预登记(landing §3.1;纯增量零行为——写端接线
    # 归终态切换批,先登记防 _validate_sig 在册校验炸)——
    'CwScreenPlanner',         # 骇入策划(planner_opts 写点,现役唯一
                               # 未登记的新写端之一)
    'CwScreenBoxPick',         # 武装箱选择(box_card_names 写点,同上)
    'CwScreenFortune',         # 命运卜者强化(fortune_opts 写点,契约扩员 12→15)
    'CwScreenEquipPick',       # 选择装备(equip_pick_opts 写点,契约扩员 12→15)
    'cw_loop_route_clear',     # 外循环路由清点挂点(离屏置 None 写端,
                               # sig family/mode 同 CwActionCloseShopParam 腿清点行,
                               # actor 单列供 journal 行过滤)
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
        log.debug(f'[cw-gs] journal row skip: {e}')


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
    """一个字段:值 + 来源 + 可选源注记。只存正式值——来源两态 + 随机扩展
    (observation/logic,ADR-0651;logic_rand = 逻辑随机态,carried/prior =
    obs 族来源子模,见 §2.1)。

    - observation = 亲眼看到的(识别结果/sim 真值合成,evidence 恒带标记);
    - logic = 决策动作按游戏规则推算的预期效果,经
      :meth:`GameState.write_logic` 直接写入(策略器立即可读),**保持
      logic 不翻 observation**(§8.1),直到下一次观察覆盖(失配 = 推算
      bug,缺陷台账留证,修推算代码);
    - logic_rand = 逻辑随机态:效果随机动作的**采样链**写入口径(值 =
      可能世界快照:采样值/未变标记/确定外壳),经
      :meth:`GameState.write_logic_rand` 写入;观察覆盖差异 = 预期内
      (随机效果落地),不进失配三分流;策略消费前必须重观察;
    - carried = 沿用上次好值,evidence 必带 ``carried:<来源帧>``
      (§2.1/§2.2 失读处置①);
    - prior = 历史遥测先验(开局 hp,§3.1.6),evidence 必带 ``prior:<来源>``;
      仅限显式申报条目,禁扩散。

    frozen = 帧替换语义的结构保证(§2.4):写入只能经 GameState API 以
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
    """备战席一槽:五种内容之一(统一槽位视图,占位真值一份,§3.2.5)。

    占席真值 = :func:`slot_occupies`:unit/supply_box/tome/bookcard 占 1 槽、
    empty 不占(晶矿不占席——它是点击目标不是席位居民,§3.2.5)。sim 合成
    帧「箱不占席」= sim 无箱实体的内部口径约定,**记录模型按实机真值**。
    bookcard = 书册卡细分(开卡动作的策略器发射臂按 kind 分派,用户裁定
    2026-09-19 开卡时机归策略实现管——原先统一降级 supply_box,策略器开箱
    臂会对着卡槽发 OpenBox 必败,由入口清场先于观察 masking)。
    """

    kind: Literal['unit', 'supply_box', 'tome', 'bookcard', 'empty'] = 'empty'
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
class OreSight:
    """晶矿观察面(§3.2.8):数量/颜色——交互机会信号,**不占席**。

    colors 为画面读取到的颜色标签元组(词表随识别线建线批定型,先以
    不透明字符串承载);count None = 未读到。
    """

    count: int | None = None
    colors: tuple[str, ...] = ()
    # [索引定义] points = 点击目标载荷(迭代 2026-09-18-prep-obs-retirement
    # 阶段 3.4 扩充):每项 (color, x, y, r) 平铺元组——晶矿为自由位置识别物
    # 无槽号,像素坐标必须随识别进容器(总纲坐标契约;点击列由 kernel
    # ``ore_click_targets_of`` 还原消费)。取值时机 = 备战入口 heavy
    # 每帧实读覆盖(两态制,观察赢;两帧持存防抖留观察链);写入端单一
    # 源 = CwScreenPrep 观察写端。CwActionCollectOreParam 逻辑态按载荷坐标精确摘除。
    points: tuple[tuple[str, int, int, int], ...] = ()


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
    (cw_obs_core.shop_card_click_points);入存储的是**槽号**(观察事实,
    见 slot 字段),执行侧按槽号从 screen_info 现取坐标。
    """

    name: str = ''
    faction: str = ''
    cost: int = 0
    star: int = 1
    # 信源位(§3.3.1):**原值透传不折叠**(P2-4 落地审:证据分级禁丢)——
    # 词表 = 现役 CwSimFrame.ShopCard.cost_source 三值:badge=费用徽章直读 /
    # roster=注册表查表(sim/replay 构造缺省) / roster_fallback=徽章失读
    # 退查表。设计的两值口径(badge=徽章直读 vs registry=注册表查表)的
    # 归并消费归批次二,消费前必须保住 roster_fallback 的「徽章失读」分级。
    cost_source: str = 'badge'
    # [索引定义] 物理槽位 = 商店牌行 1-5(左→右;坐标系 = screen_info
    # 「商店牌-N」area 序号,1 基);取值时机 = 生成期快照(进店观察帧,
    # 写入端 = 读链 read_shop_cards);0 = 未知(sim/replay 构造缺省)。
    # 为什么必须入存储:payload 是紧凑列表(空槽跳过),而游戏买入后不压缩
    # 剩余卡位(牌行打洞)——紧凑下标 ≠ 物理槽位,执行点击按下标取固定槽
    # 坐标会落空槽框(实机局实证:「买牌点击不注册」根因;布局双源同族 =
    # ADR-0646 bench 布局错位的商店牌行版)。
    slot: int = 0


@dataclass(frozen=True)
class ShopSlot:
    """商店一槽:三态之一(定长五槽的元素,用户三态裁定 2026-09-13)。

    kind='content' 时 card 有效;empty=识别确证无内容(占位带);
    unknown=应为内容但识别失败(必携缺陷台账,决策一律跳过)。
    物理槽位 = 数组下标 + 1(1 基,= screen_info「商店牌-N」序号);
    本类型无 slot 字段——定长数组下标即槽位,紧凑下标≠物理槽位的
    历史病灶类(ADR-0646 同族)在本模型下结构性消失。
    与 BenchSlot(kind + unit|None)同构。
    """

    kind: Literal['content', 'empty', 'unknown'] = 'empty'
    card: ShopCard | None = None   # kind='content' 时有效


@dataclass(frozen=True)
class ShopPayload:
    """商店开态附加(§3.3):五张牌与概率条。非当前画面 = None(§2.2 例外)。"""

    #: 定长 5(下标 0-4 ↔ 物理槽 1-5,用户三态裁定 2026-09-13):
    #: 买光 = [empty×5](合法真值,≠ None 离屏);unknown 槽决策一律跳过。
    cards: list[ShopSlot] = field(default_factory=list)
    refresh_probs: dict[int, float] = field(default_factory=dict)  # 费用档→概率(§3.3.2 契约)


def shop_payload_content_cards(payload: ShopPayload | None) -> list:
    """ShopPayload → 内容牌紧缩视图(消费点兼容读,三态裁定 2026-09-13)。

    返回 content 槽 card 的紧缩列表(序 = 槽序);empty/unknown 槽跳过——
    即帧时代紧缩读语义(旧列表从不含空位),消费点行为零漂移。坐标系:
    列表下标 = content 序(≠ 物理槽);物理槽直取 = 候选带槽号改造时切换
    (商店域消费点审计 D 项清单批2 面)。
    """
    if payload is None:
        return []
    return [s.card for s in payload.cards
            if s.kind == 'content' and s.card is not None]


# —— 选项类宿主 = cw_events(反向 import 循环禁,TYPE_CHECKING 承载见文件头)——


@dataclass(frozen=True)
class EncounterPayload:
    """遭遇屏附加(§3.4.1):分支选项。options 元素 = EncounterOption
    (终态契约形状升级:裸 tuple(int,str) → typed;写端接线归终态切换批,
    迁移期 tuple 形态仍可赋值——dataclass 无运行时类型校验,零行为)。"""

    options: list[EncounterOption] = field(default_factory=list)


@dataclass(frozen=True)
class SupplyPayload:
    """补给屏附加(§3.4.2):列数动态——通常4选1,效果改写3-5,勿写死(cw_node_obs.py:279-282)。options 元素 = SupplyOption(终态契约形状升级:裸 tuple(str,str,bool) → typed;迁移期同上零行为)。"""

    options: list[SupplyOption] = field(default_factory=list)


@dataclass(frozen=True)
class ExpertInvitePayload:
    """专家邀请函弹窗附加(契约扩员 12→15 新槽;普查迁移批 2):选卡
    决策双输入载体(kernel ``choose_expert_index`` 的两参打包)。

    [索引定义] card_bonds = 四卡区羁绊解析,坐标系 = 画面「卡-1..卡-4」
    物理区序(0 基下标即判据返回的卡下标,恒稳);取值时机 = 弹窗帧
    OCR 解析期快照,写入端 = CwScreenExpertInvite。board = 弹窗帧羁绊
    面板现读计数;读数失败 = {}(判据侧据此落现金为王兜底,语义复刻)。"""
    card_bonds: list[str | None] = field(default_factory=list)
    board: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Settlement:
    """结算屏真值组(§3.5.1):战斗后覆盖更新的数据源。

    伤害不入本结构(遥测面;字段准入注释修订——遭遇选档判据的结算观测消费走 GameState 平级新结构 settlement_ring/encounter_log 见下,本域仍只承载 hp/streak/killed/进度/金等级经验覆盖组,设计 §3.5.1 的准入边界不变);
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
#: 桶依赖矩阵禁 kernel→telemetry(分层纪律,归 review 与代码规范守卫),
#: 故同口径就地落常量,取值与 telemetry/version_stamp 单一源同源同值;
#: 落账面由 match_final 载荷版本戳断言承压。
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
    # 底稿 = W4 逐键审计 256 字面+16 闭族+9 开放族,全部=策略行为键,零
    # 效果域键;键封闭性防线原由测试仓封闭锁承载,该锁随 09-13 有损清理
    # 删除且裁定(源码扫描形态)不恢复,防漂移归 review 与代码
    # 规范)。取值 =
    # 调用方收口时点自策略 state 容器(mandate_v1 StrategyState.cw4_counters)
    # 现读;写口落载荷时浅拷贝一份(本结构不持有容器引用,后写不串)。
    # None = 无策略载体/历史段补写无源(诚实缺省,判读按「无计数载体」
    # 分型);空 dict = 局内真实零计数——两型可辨,沿旧流装配语义
    # (match_archive v7 顶层字段同一分型契约)。
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


#: 观察覆盖 logic 失配告警的抑制登记面(裁定 A/裁定 4 申报表
#: 的代码化):evidence 命中前缀的失配缺陷**不落 buffer 不告警**。
#: 语义:sim 链自身的对账差异归 sim 质量面,不进生产缺陷台账——
#: 'sim:engine' = sim 引擎外部事件写(obs 族)覆盖动作逻辑态直写是 sim
#: 建模的结构形态,事件注入(收入/结算/回声)对逻辑态的推进不是「推算
#: bug」,留证无判读价值;xp 即时结转(逻辑态直写)vs sim 轮末延迟结转
#: (引擎账本)= 申报差异(裁定 4 明点)。'sim:synthesized' = 合成口/
#: 喂入口真值合成的同性质差异(生产台账曾混入约 18.6 万行,迭代
#: 2026-09-16-unified-obs-reconcile 并列入表分流)。生产实机链零 sim
#: 前缀写点,抑制面对实机失配零触达。
_MISMATCH_SUPPRESS_PREFIXES: tuple[str, ...] = ('sim:engine', SIM_SYNTHESIZED)


def _rows_unit_key(u: Any) -> tuple[str, int, tuple[str, ...]]:
    """行写端单位多重集键(board 派生重算与纯重排吸收共用;键 =
    (char_id, star, 装备集排序元组)。槽位号/行内顺序**不在键内**——
    游戏侧行内重排只改 slot 信息位,键相等 = 同单位多重集;装备集入键 =
    穿戴变化(星徽/卡带贡献面)不算纯重排,交回真失配分流。"""
    return (str(getattr(u, 'char_id', '') or ''),
            int(getattr(u, 'star', 1) or 1),
            tuple(sorted(str(e) for e in (getattr(u, 'equips', None) or []))))


def _row_unit_tags(u: Any, row: str) -> tuple[str, ...]:
    """行内单位的羁绊标签(board 派生重算单一源;标签函数单一源 =
    ``cw_bond_equips.unit_bond_tags``)。Unit 无 position_pref 位(排归属
    由所在行承载),本口按行名补 shim:前排=front/后排=back(开拓者形态
    随排归一的坐标系输入)。

    **未知身份零贡献(刻意,禁 faction 兜底)**:身份不在注册表(注册表
    外单位如狸狸/姵姵,或 OCR 误读名)时标签为空,容器派生路径**不回退
    faction**——Unit 不存阵营(防注册表双源),shim 复活 faction 位 =
    双源复活。「未知身份回退 faction」口径的单一源 =
    ``cw_bond_equips._recount_board``(faction 字段所在载体,装备授予表
    BenchChar);容器侧的对应漂移由 board 观察覆盖采新收敛
    (:meth:`GameState._absorb_board_derived`)。"""
    from types import SimpleNamespace

    from sr_od.application.currency_war.kernel.cw_bond_equips import (
        unit_bond_tags,
    )
    return unit_bond_tags(SimpleNamespace(
        char_id=str(getattr(u, 'char_id', '') or ''),
        position_pref=('front' if row == 'front_row' else 'back'),
        equips=list(getattr(u, 'equips', None) or [])))


def _route_logic_mismatch(*, field_name: str, expected: Any, actual: Any,
                          observed_evidence: str | None,
                          logic_evidence: str | None,
                          sig: ChannelSig) -> None:
    """观察覆盖 logic 失配三分流路由(observe() 失配比对处接线;迭代
    2026-09-16-unified-obs-reconcile)。按序判定命中即停:

    1. 豁免命中(键 = 观察侧 sig.screen × 字段 × 逻辑写端 evidence 前缀,
       注册表 = cw_mismatch_policy.EXEMPT_REGISTRY)→ 落 ``exempt_mismatch``
       台账行(与真失配行同构仅 kind 不同),无告警无停机;
    2. sim 证据命中(:data:`_MISMATCH_SUPPRESS_PREFIXES` 前缀)→ 不落生产
       台账直接返回(现役抑制语义);
    3. 真失配 → 缺陷行 + ``[cw!]`` 告警 + 安灯钩子(槽缺省关)。

    覆盖照常(观察赢),本函数只管留证与处置;处置序设计取舍见迭代
    design.md §2.3。"""
    entry = lookup_mismatch_exempt(sig.screen, field_name, logic_evidence)
    if entry is not None:
        _emit_defect(field_name=field_name, expected=expected, actual=actual,
                     evidence=observed_evidence, sig=sig,
                     logic_evidence=logic_evidence, kind='exempt_mismatch')
        return
    if observed_evidence is not None and any(
            observed_evidence.startswith(p)
            for p in _MISMATCH_SUPPRESS_PREFIXES):
        return
    _emit_defect(field_name=field_name, expected=expected, actual=actual,
                 evidence=observed_evidence, sig=sig,
                 logic_evidence=logic_evidence)


def _emit_defect(*, field_name: str, expected: Any, actual: Any,
                 evidence: str | None,
                 sig: ChannelSig,
                 logic_evidence: str | None = None,
                 kind: str = 'observe_vs_logic_mismatch') -> None:
    """缺陷台账留证(§2.3 观察赢):观察覆盖 logic 值失配 = 推算 bug,
    留证后修推算代码(ADR-0651;不做运行时挂账对账)。best-effort:
    外送钩子异常不阻塞观察主链。抑制登记面见
    :data:`_MISMATCH_SUPPRESS_PREFIXES`(路由层
    :func:`_route_logic_mismatch` 与本发射口双重消费——吸收族
    (board 派生/纯重排/外部授予/边界金/备战环收入)不经路由层,
    发射口兜底保证 sim 证据行无论如何不入生产台账;豁免行除外,
    其落行处置序归路由层(豁免→抑制→真失配,design §2.3)。

    行形状(ts/sig 维度为迭代 2026-09-16-unified-obs-reconcile 补齐):
    ``kind / field / expected / actual / observed_evidence / ts /
    screen / actor / group_id / logic_evidence``——ts = journal 行同款
    秒级时刻;screen/actor/group_id = 观察侧渠道签名;logic_evidence =
    逻辑侧写端注记(豁免注册表第三维,归因回溯用)。
    真失配 kind 行落盘后同步触发安灯钩子(:func:`fire_reconcile_andon`,
    行落盘先于钩子——证据在场不依赖钩子成败);豁免行无告警无停机。"""
    # 抑制登记面发射口兜底:吸收族落台账行不经 _route_logic_mismatch
    # 路由层,observed_evidence 命中抑制前缀的行(sim 链自身对账差异)
    # 归 sim 质量面,不落 buffer 不落 sink 不告警——生产实机链零 sim
    # 前缀写点,生产台账曾混入约 18.6 万行 sim 行才立此面(语义见
    # _MISMATCH_SUPPRESS_PREFIXES 注),发射口兜底防绕行。豁免行不辖:
    # sim 证据+豁免条目同击时路由层已裁定豁免先行落行(处置序 =
    # 豁免→抑制→真失配),发射口再抑制即翻转该裁定。
    if kind != 'exempt_mismatch' and evidence is not None and any(
            evidence.startswith(p)
            for p in _MISMATCH_SUPPRESS_PREFIXES):
        return
    row: dict = {'kind': kind, 'field': field_name,
                 'expected': expected, 'actual': actual,
                 'observed_evidence': evidence,
                 'ts': datetime.now().isoformat(timespec='seconds'),
                 'screen': sig.screen, 'actor': sig.actor,
                 'group_id': sig.group_id, 'logic_evidence': logic_evidence}
    _DEFECT_BUFFER.append(row)
    if len(_DEFECT_BUFFER) > _DEFECT_BUFFER_CAP:
        del _DEFECT_BUFFER[:len(_DEFECT_BUFFER) - _DEFECT_BUFFER_CAP]
    if _DEFECT_SINK is not None:
        try:
            _DEFECT_SINK(dict(row))
        except Exception as e:  # noqa: BLE001  留证 best-effort
            log.debug(f'[cw-gs] defect sink skip: {e}')
    if kind != 'observe_vs_logic_mismatch':
        return   # 豁免等非真失配行:留证即止,无告警无停机
    log.warning(f'[cw!][gs] 观察覆盖 logic 失配:{field_name} '
                f'预期[{expected}] 实读[{actual}](§2.3 观察赢)')
    fire_reconcile_andon(dict(row))


# ============================================================ 状态流水 sink(R1 §3.2.3)

#: 状态流水外送钩子(进程内单槽;行落盘的在场门——journal 本体无条件常开
#:(R5 W1/ADR-0634:无开关,生产装配 = currency_war_app 装配段 + 局容器
#: 单例建立点兜底,见 :func:`game_state_of`),本槽
#: 缺省 None 只表示「无落盘实例」(单元测试/工具环境),此时**写路径照常
#:(Field 写入与版本分配不受影响),仅行不外送**——记录被动,不分支行为。
#: 落盘实现与装配口 =
#: :mod:`sr_od.application.currency_war.kernel.cw_state_journal`)。
#: 槽契约:接收一行完整行 dict(自足快照行,§3.2.3),自担序列化/缓冲/落盘。
_STATE_JOURNAL_SINK: Callable[[dict], None] | None = None

#: run 归属供给槽(依赖倒置:kernel 禁依 telemetry——桶依赖矩阵分层纪律,
#: 归 review 与代码规范守卫;行内 run_id 由装配点注入
#: 读取函数,生产武装点 = currency_war_app 装配段传 telemetry 现读口)。
_RUN_ID_PROVIDER: Callable[[], str] | None = None


def set_state_journal_sink(fn: Callable[[dict], None] | None) -> None:
    """接通/复位状态流水外送钩子(None = 无落盘实例,缺省态;同
    :func:`set_defect_sink` 注入槽模式)。生产装配 = currency_war_app
    装配段 + GameState 初始化兜底(经 ``cw_state_journal.install_state_
    telemetry``,无条件常开)。
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


def current_run_id_safe() -> str:
    """run 归属现读公开口(本槽唯一定义的跨模块读面)。

    消费方 = 同桶策略侧决策行发射面(kernel/cw_decision_trace):两文件
    模型①②同 run 段归属,run_id 单一来源 = 本供给槽,禁第二读取实现。
    """
    return _current_run_id_safe()


# ============================================================ 派生计算(不存储)


def slot_occupies(kind: str) -> bool:
    """槽位占席谓词(§3.2.5 实机真值):unit/supply_box/tome/bookcard
    占 1 槽,empty 不占。席满判定/席空数同源派生的底座。"""
    return kind != 'empty'


def bench_free_slots(gs: GameState) -> int | None:
    """席空数(§3.2.5 派生计算,不入 schema)。bench 从未观察 → None
    (= 不确定,**禁猜 0**);已观察 → max(capacity − 占席槽数, 0)。"""
    view = gs.bench.value
    if view is None:
        return None
    used = sum(1 for s in view.slots if slot_occupies(s.kind))
    return max(view.capacity - used, 0)


def bench_is_full(gs: GameState) -> bool | None:
    """席满判定 = 同源派生(席空数==0,§3.2.5;含商店开态满栏买牌判定)。
    bench 未观察 → None(不确定);「备战席已满」警告 OCR 不做识别
    (玩家裁定 2026-09-09,现役 read_bench_full 通道退役挂批次二)。"""
    free = bench_free_slots(gs)
    return None if free is None else free == 0


def board_next_tier_of(board_factions: dict[str, int]) -> dict[str, int]:
    """board 下档阈值派生(§3.2.6/§8.8 准入③:计算函数不存储)。

    语义 = 左面板「X/Y」的 Y:对注册表 ``FACTIONS[].tiers`` 取 >当前人数
    的最小档,无更高档不计入。**本函数 = 该推导的 kernel 单一源**——
    迁移批次二起,obs computed 支(cw_observation read_game_state)
    委托至此,禁第三份推导。
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
# 方案语义正本 = docs/develop/sr_od/application/currency_war/game_state/fields.md §3.3.1
# (双 ShopCard 映射):唯一容器类型 =
# :class:`ShopCard`(本模块);帧版(cw_vocab 侧同名类,带点击坐标 x
# 与 merge_preview)是观测/执行域卡(OCR 产物带点击坐标,黑板帧链自持 x)
# 兼 sim 机制卡,**随推演内核收编长期并存**——两类型并存为长期形态,
# **转换只许在本节两个映射函数发生**(喂入面/合成口/消费视图/合成引擎
# 统一经此,禁散落内联转换——双源漂移温床)。本节 = kernel 内帧版类型的
# 唯一合法引用面(静态锁辖域,测试锁 test_cw_w5_* 守)。

def shop_card_to_container(card) -> ShopCard:
    """旧容器牌 → 容器牌(喂入口/sim 合成口的值构造单一源)。

    字段映射(name/faction/cost/star/cost_source)原值透传不折叠;
    x/merge_preview 是旧版独有的执行/读取器域字段,容器不入存储
    (坐标单一真相源 = screen_info;merge_preview = 派生核对信号);
    slot(物理槽号,观察事实)透传——执行点击按槽号取坐标的唯一依据。
    """

    return ShopCard(name=str(getattr(card, 'name', '') or ''),
                    faction=str(getattr(card, 'faction', '') or ''),
                    cost=int(getattr(card, 'cost', 0) or 0),
                    star=int(getattr(card, 'star', 1) or 1),
                    cost_source=str(getattr(card, 'cost_source', '')
                                    or 'roster'),
                    slot=int(getattr(card, 'slot', 0) or 0))


def shop_cards_to_legacy(cards: list[ShopCard],
                         frame_cards: list | None = None) -> list:
    """容器牌列表 → 旧容器牌列表(消费视图/合成引擎边界的值构造单一源)。

    - 五记录字段(name/faction/cost/star/cost_source)自容器透传;
    - ``slot``(物理槽号)自容器透传(执行/点击域事实,click_pts 按
      槽号取坐标的依据);
    - ``x``(点击坐标)置 0 不消费:决策消费不用坐标,执行侧 buy 发射
      从 screen_info「商店牌-N」区域按 slot 现取(黑板帧链自持 x,不经
      本函数);
    - ``merge_preview`` 不转换(派生计算不入存储,✦ 读取器降级核对
      信号的消费方自算或吃同帧 raw);
    - ``frame_cards`` = 同帧 raw 牌列表(可选):长度一致时按下标对齐
      透传 x/merge_preview 两执行/读取器域字段——容器 payload 与 raw 帧
      出自同一观察帧时序(喂入口保序),失配窗(失读帧/跨帧)置缺省 0,
      语义申报 = 执行域字段引导窗,不影响记录值。

    :param cards: 容器牌列表(:attr:`ShopPayload.cards`);
    :param frame_cards: 同帧 raw 牌(旧容器 ShopCard)列表或 None。
    """
    from sr_od.application.currency_war.kernel.cw_vocab import (
        ShopCard as _LegacyShopCard,
    )
    out: list = []
    n = len(cards)
    aligned = (frame_cards is not None and len(frame_cards) == n)
    for i, c in enumerate(cards):
        fr = frame_cards[i] if aligned else None
        out.append(_LegacyShopCard(
            x=int(getattr(fr, 'x', 0) or 0) if fr is not None else 0,
            slot=int(c.slot or 0),
            faction=str(c.faction or ''),
            name=str(c.name or ''),
            cost=int(c.cost or 0),
            star=int(c.star or 1),
            merge_preview=int(getattr(fr, 'merge_preview', 0) or 0)
            if fr is not None else 0,
            cost_source=str(c.cost_source or 'roster')))
    return out


# ============================================================ 动作回执域(R2 §3.1.1-4/§3.2.5)

#: 动作回执滚动窗容量(§3.1.1-4:有界列表,先进先出;容量 8 = 单节点动作
#: 批的量级上界,失败可见性窗——回执蒸发窗下限,过窗历史归流水行行自足)。
RECEIPTS_WINDOW_CAP: int = 8


def game_state_from_ctx(ctx: object) -> GameState | None:
    """ctx → 局 GameState(cw_match.session 旁表现读;无局/解析失败 = None)。

    动作 op 写入点的统一供给口(R2):调用方零判空负担——无局(独立跑/
    测试桩)静默 None,写入点自行跳过。"""
    try:
        match = getattr(ctx, 'cw_match', None)
        session = getattr(match, 'session', None) if match is not None else None
        if session is None:
            return None
        return game_state_of(session)
    except Exception:   # noqa: BLE001  供给口不炸调用链
        return None


def note_action_receipt(gs: GameState, *, op: str, applied: bool,
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
        old = gs.receipts.value or []
        window = (list(old) + [receipt])[-RECEIPTS_WINDOW_CAP:]
        seq = gs.write_seq + 1
        sig = ChannelSig(family='logic_action', actor=actor, mode='compute',
                         group_id=f'act:{actor}@{seq}')
        gs.write_logic(gs.receipts, window, produced_by=actor, sig=sig)
    except Exception as e:  # noqa: BLE001  记录层 best-effort,不毒化动作链
        log.debug(f'[cw-gs] action receipt skip: {e}')


# ============================================================ 账本→字段桥(§5.1/§3.2.5/§3.3.5-6,迁移批次三 B1)

def _bridge_sig(gs: GameState) -> ChannelSig:
    """效果桥写入的渠道③签名(单一构造点;§3.2.1 ③组 id =
    hook:<登记名>@<seq>;R5 W1 起签名必填,ADR-0634)。"""
    return ChannelSig(family='logic_hook', actor='EffectLedgerBridge',
                      mode='compute',
                      group_id=f'hook:EffectLedgerBridge@{gs.write_seq + 1}')


def apply_effect_burst_grant(gs: GameState, spec: Any, *,
                             frame: str = '') -> None:
    """桥·burst 形态(选卡一次性):登记时点把效果声明的免费刷新额度一次
    性累加进余额(§3.3.5 burst 族:免费午餐 11/及时雨 4/固定理财即时段 2
    等;载体 = payload.free_refresh_burst)。只在本挂点累加一次——「一次性」
    语义由登记时点单次调用承载,其余挂点不得重复调本函数。

    采样点 = 选卡登记挂点(CwScreenInvestStrategy 确认落地,登记成功后
    紧随调用);记账 = 效果账本(2026-09-18 迁入裁决:免费余额住
    ActiveEffectInventory,经 grant_free_refreshes 统一出口)。额度 0 或
    payload 无此字段(如 BattlefieldEffect 族)= no-op。
    """
    n = int(getattr(getattr(spec, 'payload', None), 'free_refresh_burst', 0) or 0)
    if n <= 0:
        return
    _ev = f'effect_burst@{frame}' if frame else 'effect_burst'
    gs.effects.grant_free_refreshes(n)


def grant_effect_node_refresh_balance(gs: GameState, *,
                                      frame: str = '') -> None:
    """桥·per_node + 条件判定形态(每节点发放):节点边界一次,把全部在场
    条目声明的每节点免费刷新额度累加进余额(§3.3.5-§3.3.6)。载体两族:

    - **静态每节点**:EconomyEffect.free_refresh_per_node(加油站/搜打撤=1)
      + BattlefieldEffect.free_refresh_on_node_enter(双手狸开键盘!=2),
      payload 按鸭子属性读、缺省 0(两族并存条目求和);
    - **条件判定**(本金充裕/+,EconomyEffect 条件三元组,§3.3.6「结构化后
      经同一桥自动生效」):按 gs.gold 现值评估——金 > free_refresh_cond_gold_above
      时每额外 free_refresh_cond_gold_step 金 +1 次、至多 free_refresh_cond_cap;
      三字段齐备(>0)才激活,半配对保守 no-op。金未读(None)= 条件不可
      评估 → 该条目本拍零授予(禁猜;下一节点金可读时恢复评估,授予量
      随当拍现值,不补发历史拍)。

    采样点 = 节点 tick 挂点(cw_loop 备战分支),**仅在 advance_node 返回
    advanced=True 时调用**(每节点恰一次,重复调用即双计;条件形态与静态
    形态同闸门——授予量随当拍金现值变化,触发时点恒为节点边界一次);
    记账 = 效果账本(2026-09-18 迁入裁决)。静态活载体 = 双手狸(2/节点);
    条件活载体 = 本金充裕/+(50/10/3)。固定理财位面开始段(PLANE_START)不
    属本形态,未建模挂账不改本桥。
    """
    per_node = 0
    gold = gs.gold.value
    for e in gs.effects.entries:
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
    gs.effects.grant_free_refreshes(per_node)


def project_effect_capacity(gs: GameState) -> None:
    """桥·容量逻辑态直写(§3.2.5):按账本在册容量时限声明回写备战席容量——
    激活期 capacity=N、条目到期移除后自动回默认 9。

    声明契约:容量条目的 payload 携带 ``capacity_limit: int``(激活期容量;
    注册表现零条目携带——§5.2 缺口登记「禁到注册表找规格」,载体归注册表
    建模批候选,声明字段名由此钉死,首批容量条目入册即自动生效)。多声明
    取 min(叠加收紧向)。当前零携带 → 直写恒等于默认 9(幂等 no-op,行为
    与接线前逐位一致)。

    采样点 = 备战帧观察后(cw_loop 备战分支,**每 pass 重锚**):观察构造器
    (bench_view_from_obs)按默认容量建视图,会覆盖逻辑态直写值,故观察后须重锚;
    bench 从未观察(值 None)= 无容器可写,跳过(容量随 bench 首帧进入
    记录)。建模批补首张容量条目时须同批补观察构造器的容量感知,防观察
    覆盖 logic 值刷缺陷台账(本桥 docstring 即该义务的挂点)。
    """
    limits = [int(getattr(e.spec.payload, 'capacity_limit', 0) or 0)
              for e in gs.effects.entries]
    limits = [n for n in limits if n > 0]
    target = min(limits) if limits else BENCH_CAPACITY_DEFAULT
    view = gs.bench.value
    if view is None or view.capacity == target:
        return
    gs.write_logic(gs.bench,
                   BenchView(slots=list(view.slots), capacity=target),
                   produced_by='EffectLedgerBridge',
                   evidence='capacity_project', sig=_bridge_sig(gs))


# ============================================================ 备战席观察写端(§3.2.5)


def bench_view_from_obs(bench_chars: list,
                        item_kind_by_slot: dict[int, str] | None = None,
                        ) -> BenchView | None:
    """备战席 SIFT 读链 → BenchView(观察写端的值构造;§3.2.5 观察写端=本屏)。

    - **空集 = 失读非全空**(P2-1 批次二落地审):overlay 残留/动画帧/识别
      退化都会产空集,≠实席真清空——返 None,调用方走 carried(§2.2 处置①;
      先例 = 商店空牌面「宁缺勿造不写」),禁把「9 槽全空」当 observation
      入记录(席空数派生误报 free=9 会污染席满决策);
    - 槽位越界条目丢弃并 log 留证(物理槽 1..capacity 外 = 读链漂移信号,
      静默丢弃 = 身份静默丢失);
    - ``is_item_slot`` 占位件(读链道具位,箱/典籍/书册卡)→ supply_box
      槽位往返保旗标(占 1 席、非可卖燃料;与 :func:`bench_slots_to_legacy`
      的重建分支配对)。``item_kind_by_slot``(迭代 2026-09-18-prep-obs-
      retirement 阶段 3.5)= 槽号 → 'supply_box'/'tome'/'bookcard' 细分
      映射(观察链用同帧 read_supply_boxes/read_tomes/find_bookcards
      槽号集构造;缺省 None = 旧行为逐位不变,占位件恒 supply_box);
    - 非 None 返回 = 槽位保序映射(下标 i = 物理槽 i+1,与 sim 合成口同构)。
    """
    if not bench_chars:
        return None
    _kind_map = item_kind_by_slot or {}
    slots: list[BenchSlot] = [BenchSlot(kind='empty')] * BENCH_CAPACITY_DEFAULT
    for bc in bench_chars:
        s = int(getattr(bc, 'slot', 0) or 0)
        if 1 <= s <= BENCH_CAPACITY_DEFAULT:
            if bool(getattr(bc, 'is_item_slot', False)):
                # 占位件保旗标(与 bench_view_of_slots 的 supply_box 映射配对):
                # 恒映射 'unit' 会把占位件退化成 '' 1★ 可卖燃料,腾席守卫失守
                #(波 4 落码审 A 组探针同款形态)。细分映射缺省 supply_box,
                # 典籍槽(同帧 read_tomes 槽号集)精确为 'tome'。
                slots[s - 1] = BenchSlot(
                    kind=_kind_map.get(s, 'supply_box'))
                continue
            slots[s - 1] = BenchSlot(kind='unit', unit=Unit(
                char_id=str(getattr(bc, 'char_id', '') or ''),
                star=int(getattr(bc, 'star', 1) or 1),
                equips=list(getattr(bc, 'equips', None) or []),
                slot=s))
        else:
            log.warning('[cw!][gs-bench] 备战席读链槽位越界丢弃:'
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
    """BenchView(容器备战席)→ CwSimFrame.bench 槽位表(视图收编换算单一源)。

    下标语义两端同构(容器 slots[i] = 物理槽 i+1,旧表下标 i = 物理槽
    i+1,ADR-0316),逐槽 1:1;Unit → BenchChar:阵营不入容器(§3.2.3),
    经角色注册表查表派生(唯一例外开拓者形态随排,由 char_id 自带形态
    名承载);备战席装备 = 容器 Unit.equips(本域观察恒空表,见
    :func:`deployed_rows_from_obs` 边界申报)。槽位越界/空槽 → None。
    """
    from sr_od.application.currency_war.data.cw_chars import get_char
    from sr_od.application.currency_war.kernel.cw_exec_state import BenchChar
    out: list = []
    for i, slot in enumerate(view.slots):
        u = getattr(slot, 'unit', None)
        kind = getattr(slot, 'kind', 'empty')
        if kind in ('supply_box', 'tome', 'bookcard'):
            # 占位件往返重建(与 bench_view_of_slots 的 supply_box 映射
            # 配对;tome/bookcard 分支 = kind 细分配对——reviewer r1 #1
            # 申报的「单边破裂」处置):is_item_slot=True 的 BenchChar,
            # 守卫线(占位恒拒)与部署装配点识别线消费同旗标。
            out.append(BenchChar(slot=i + 1, char_id='', star=1,
                                 is_item_slot=True))
            continue
        if kind != 'unit' or u is None:
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
    """(front_row, back_row)(容器席位)→ CwSimFrame.deployed 槽位表(ADR-0392
    0 基:0-3 前排/4-9 后排;视图收编换算单一源)。

    坐标系换算(设计 §8.2 注):Unit.slot = 行内 1 基画面槽号(信息位)→
    旧表下标 = 前排 slot-1 / 后排 3+slot;slot 缺席(0)按占用序顺延兜底
    (与旧紧缩构造兼容)。阵营派生同 :func:`bench_slots_to_legacy`。
    """
    from sr_od.application.currency_war.data.cw_chars import get_char
    from sr_od.application.currency_war.kernel.cw_exec_state import (
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


def deployed_slots_to_rows(slots: list) -> tuple[list[Unit], list[Unit]]:
    """CwSimFrame.deployed 槽位表(ADR-0392,0-3 前/4-9 后)→ 容器席位行
    (:func:`unit_rows_to_deployed` 的逆换算;转移函数单源化新增,
    v2 动作族腿「槽表中间形态→整表 write_logic」平移契约的写回端)。

    Unit.slot = 行内 1 基槽号(信息位,与 :func:`deployed_rows_from_obs`
    同系);空槽与未识别(char_id 空)不入行(宁缺勿造,容器席位域语义,
    与喂入口 :func:`game_state_from_ctx` 系同口径);往返 =
    :func:`unit_rows_to_deployed`(front, back) 逐槽还原( slot-1 定位,
    无歧义)。阵营不入行(§3.2.3),装备随 Unit 透传。
    """
    front: list[Unit] = []
    back: list[Unit] = []
    for i, d in enumerate(slots or []):
        if d is None or not getattr(d, 'char_id', ''):
            continue
        unit = Unit(char_id=str(getattr(d, 'char_id', '') or ''),
                    star=int(getattr(d, 'star', 1) or 1),
                    equips=list(getattr(d, 'equips', None) or []),
                    slot=(i + 1) if i < 4 else (i - 3))
        (front if i < 4 else back).append(unit)
    return front, back


# ============================================================ 局终归档快照(§6.2/§8.8)

def archive_snapshot(gs: GameState) -> dict:
    """局终 GameState 归档快照(§6.2 局终归档喂遥测,先于连刷重建;
    §8.8 遥测行形状正本的两键:gs_prov/gs_extra)。

    - gs_prov = 非默认来源注记(稀疏化,不逐字段灌满):source 非
      observation、或 observation 带 evidence 的字段才入——默认 observation
      无注记的字段 = 「本帧真读」语义,键面留白;
    - gs_extra = 工程结构(schema 版本/域版本/心跳/效果账本规模)+
      全部非 None 字段值(JSON 安全形态,供离线判读)。

    返回 dict 直接入档(由局终装配器并档);序列化失败逐字段跳过
    (归档 best-effort,不阻塞局终流转)。
    """
    prov: dict[str, dict] = {}
    extra_values: dict[str, object] = {}
    for f in dataclasses.fields(gs):
        val = getattr(gs, f.name, None)
        if not isinstance(val, Field):
            continue
        if val.value is not None:
            with contextlib.suppress(Exception):
                extra_values[f.name] = _json_safe(val.value)
        if val.source != 'observation' or val.evidence is not None:
            prov[f.name] = {'source': val.source, 'evidence': val.evidence}
    return {
        'schema_version': gs.schema_version,
        'gs_prov': prov,
        'gs_extra': {
            'values': extra_values,
            'gs_schema': dict(gs.gs_schema),
            'write_seq': gs.write_seq,
            'frame_obs': gs.frame_obs,
            'effects_count': len(getattr(gs.effects, 'effects', []) or []),
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
    """CwSimFrame.bench 槽位表(0 基下标 + None 洞)→ BenchView(记录模型
    形状契约;槽 i = 物理槽 i+1,与 sim 合成口同构映射)。逻辑态面用
    (CwActionBuyCardParam 升星逻辑态直写的值构造源,ADR-0651)。"""
    slots: list[BenchSlot] = []
    for i, bc in enumerate(bench_list or []):
        if bc is None:
            slots.append(BenchSlot(kind='empty'))
        elif bool(getattr(bc, 'is_item_slot', False)):
            # 占位件(补给箱/秘典等,``BenchChar.is_item_slot`` 旗标,sell_gate
            # 占位恒拒防线与部署装配点识别线共用)→ supply_box kind 往返
            # 保旗标——恒映射 'unit' 会让占位件在容器决策面退化成 '' 1★
            # 可卖燃料(腾席守卫失守,波 4 落码审 A 组探针实证)。
            # ⚠️ 类型降级申报(阶段 3.5):本口输入是 is_item_slot 布尔,
            # 无 box/tome 类型信息,占位件恒 supply_box——kind 细分的权威
            # 写端 = bench_view_from_obs 的 item_kind_by_slot(生产观察链);
            # 本口仅 sim 合成/逻辑态面(占位件稀有路径),细分降级 = 已知
            # 边界非缺陷。
            slots.append(BenchSlot(kind='supply_box'))
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
    """CwActionBuyCardParam 逻辑态直写是否发生 3 合 1 升星(§3.2.18 修法 a 触发判定;纯函数)。

    判据 = 同名角色直写后最高星级 > 直写前同名最高星——3 份合成是该
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

def apply_settlement_cover(gs: GameState, *, hp_after: int | None,
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
      R5 W1 起签名必填,ADR-0634;
    - **hp_after 写入序定谳**(现场证据 = 本写端 + reconcile_hp 现役形态):
      本口 = hp 的战局唯一结算真值入口,无条件观察覆盖(观察赢,仅调用方
      置信度门)。旧 ADR-0282「读不到保旧沿用 last_hp_real」三层已随
      终态契约 §A 整体退役(ADR 档案目录已删,原文 = git 历史
      docs/develop/currency_war/decisions/0282-hp-three-layers.md),读侧
      reconcile_hp 简化为「真值直传/开局先验(ADR-0559)/None 诚实未知」
      ——不存在沿用锚遮蔽结算真值的先后序问题。唯一能与本覆盖失配的 =
      逻辑态推算写端(宝物加血,write_logic(gs.hp)),该失配按两态制
      §2.3 = 推算 bug 显影,非「保旧」。窗内消费(battle_wait killed
      hp 对比兜底)先行于本写端,读到的是上一结算真值,即正确序。
    """
    _sig = ChannelSig(family='obs', actor='CwScreenBattleWait', mode='read')
    if hp_after is not None:
        gs.observe(gs.hp, int(hp_after), sig=_sig)
    if streak_after is not None:
        gs.observe(gs.streak, int(streak_after), sig=_sig)
    if gold is not None:
        # 金币不走 observe 失配链:节点收入由游戏侧结算前入账,账本与
        # 真值的差 = 预期边界收入(非推算 bug),经 settle_truth 无条件
        # 收口 + 差值台账留证(机理见 settle_truth docstring)。
        gs.settle_truth(gs.gold, int(gold), sig=_sig)
    if level is not None:
        gs.observe(gs.level, int(level), sig=_sig)
    if xp is not None:
        gs.observe(gs.xp, (int(xp[0]), int(xp[1])), sig=_sig)
    gs.observe(gs.settlement, Settlement(
        hp_after=hp_after, streak_after=streak_after, killed=killed,
        progress_delta=progress_delta, gold=gold, level=level,
        xp=(int(xp[0]), int(xp[1])) if xp is not None else None),
        sig=_sig, note=note)


# ============================================================ 商店动作逻辑态直写
# (波 4 黑板容器化;设计件 = unified-state 迭代 商店黑板容器化方案 §2.1-2/§4-M1/M5(git 历史可溯))

#: 逻辑态公式语义源锁的登记面(设计件 §4-M5:直写域集/None 跳写清单/
#: executed 回执字段集/支持动作集随本锁登记;未登记写点 = 缺陷,禁扩静默):
#: - **域集封闭**(gold / bench / shop payload / xp 四域;CwActionCloseShopParam 的
#:   leave_screen 为同域通道形态);
#: - **支持动作集** = CwActionBuyCardParam / CwActionSellBenchParam / CwActionLevelUpShopParam(is-a CwActionLevelUpParam) /
#:   CwActionRefreshShopParam / CwActionCloseShopParam(商店单动作循环在产动作面;fields.md §4.2
#:   逐 op 行;CwActionSellDeployedParam/CwActionDeployMoveParam 不写逻辑态——等观察
#:   覆盖,申报 = 商店 visit 在产动作集外);
#: - **None 跳写清单**(域级独立跳写,禁缺省值参与计算):gold /
#:   xp+level(升级推进对,同进退——任一未读则推进对整体跳写)/
#:   刷新费(paid=None 整动作跳写);
#: - **executed 回执字段集** = bought_count(CwActionBuyCardParam 实购张数,满栏多买
#:   k 执行期确定)/ levelup_clicks(CwActionLevelUpShopParam 实际击数)/ refresh_paid
#:   (CwActionRefreshShopParam 实付刷新费,免费帧 0);回执缺字段 = 该动作本轮不写逻辑态。
#: **扩面申报表**(扩面须逐批显式登记于本表,
#: 原「禁扩静默」条款由本表承接):
#: - 支持动作集扩:v2 动作族 CwActionSellDeployedParam / CwActionSwapDeployParam
#:   (语义源 = simulate 对应分支逐腿平移,直锁 test_cw_transfer_golden
#:   钉住);
#:   CwActionDeployMoveParam 不入(围栏部署 = 结算期代理,obs 通道申报对齐);
#: - 域集扩:front_row / back_row(v2 腿与合成连锁全场域写回,deployed
#:   域语义)、board(**派生量**:行写端挂钩 ``_resync_board_delta``
#:   自动重算,禁独立手写;单一源见该方法注)、equips(卖出回收腿);
#: - 域集扩(2026-09-18):level(CwActionLevelUpShopParam 升档直写;语义源 = prep 腿
#:   买经验上报(report_action_level_up_param)同款,推进单一源 =
#:   ``cw_economy.xp_apply_clicks`` 跨级连跳含内)。依据 = 等级滞留使
#:   下一击按旧级重算(花金零等级推进),而等级 = 席位 cap 解锁地板
#:   (``max_units_of`` 经读口跟随,消费位零改动)。域级跳写对 =
#:   (level, xp) 同进退:任一未读则推进对整体跳写,禁缺省 1 参与
#:   推进计算。
#: - 扩面依据:单一转移函数 = sim 引擎动作应用的唯一形态(裁定 A:
#:   logic_action 族,与 live 同函数同渠道),域覆盖须对齐 simulate
#:   对应分支的字段转移全集。
SHOP_PROJECTION_DOMAINS: tuple[str, ...] = (
    'gold', 'bench', 'shop', 'xp', 'level',
    'front_row', 'back_row', 'board', 'equips')


@dataclass(frozen=True)
class LogicOutcome:
    """动作状态应用的显式结果出参(转移函数单源化;详设 §3
    「转移结果通道」)。

    拒绝判定由腿内既有判定填充(simulate 对应分支的拒绝语义逐腿平移:
    stale_proposal / 满栏非合成拒买 / 同名拒上),
    拒绝 = applied=False + reason + **零容器写**;引擎侧拒绝账本转录读出参
    驱动,禁在引擎自判拒绝(§2.1 单一源红线)。live 调用点忽略本出参
    (返回值不接 = 行为零变化)。

    - bought_count = CwActionBuyCardParam 实际应用张数的权威回声(两路径恒填充:
      executed 回执给定 or 函数自算;k 与金账扣减、payload 移除同源)。
    - income = CwActionSellDeployedParam 卖出回金;fill_cost 字段保留为出参契约位
      (现役恒 None)。
    """

    applied: bool
    reason: str = ''
    income: int | None = None
    fill_cost: int | None = None
    bought_count: int | None = None


@dataclass(frozen=True)
class ShopActionExecuted:
    """商店动作执行落地门回执(上报函数族 executed 形参)。

    执行期决定量以落地门回执为准,禁按动作对象预估(设计件 §2.1-2):
    CwActionBuyCardParam 满栏多买 k 张(CwActionLevelUpParam 满栏例外一击多张)与 CwActionLevelUpShopParam
    实际击数(循环点击至 level+1)均由执行侧回执;缺字段(None)= 该
    动作本轮不写逻辑态,等观察覆盖。

    **Optional 语义(详设 §3 修订)**:executed 整体可缺省
    (None = 理想执行)——live 传执行回执(参数化不变);sim 引擎传
    None,函数自算执行期决定量(CwActionBuyCardParam k 自算,满栏合成买 k 从
    :func:`_apply_full_bench_merge_buy` 应用面出)。executed 只辖 k 等
    决定量**来源**,不辖应用面位置——合成连锁/满栏合成买的应用两路径
    同在转移函数内(单源本义)。executed 与自算值的关系核对归调用方
    守卫面(本函数不判)。
    """

    #: CwActionBuyCardParam 实购张数(满栏多买 k;单一源 = 执行侧 merge_buy_k 计数)
    bought_count: int | None = None
    #: CwActionLevelUpShopParam 实际击数(单动作形态恒 1;腾席链多击以回执为准)
    levelup_clicks: int | None = None
    #: CwActionRefreshShopParam 实付刷新费(免费帧 = 0 → gold 不写,fields.md §3.3.4)。
    #: 现役喂入方 = sim/replay 驱动器(flow/bridge decide_shop_screen,按
    #: 动作 cost 派生);生产落地门(cw_op_buy_cards.apply_action_outcome)
    #: **暂不喂本字段**——商店线 CwActionRefreshShopParam 是终结 op,生产逻辑态直写门对终结
    #: 动作整体跳写(期望态按下段入口重观察作废,终结不写逻辑态为申报过渡
    #: 语义),单接本字段不可达;接线(含终结直写语义改)与 receipts 接线
    #: 同批评估(批首清单候选,波 5 sim 反转时裁决)。
    refresh_paid: int | None = None


def mutate_bench_deployed_local(bench, deployed, action,
                                shop=None) -> None:
    """``cw_state.mutate_bench_deployed`` 惰性转发(本模块与 cw_state 的
    运行时依赖纪律 = 函数级懒 import);shop 视图透传(满栏合成买分支
    ``_apply_full_bench_merge_buy`` 的素材消费源)。"""
    from sr_od.application.currency_war.kernel.cw_vocab import mutate_bench_deployed
    mutate_bench_deployed(bench, deployed, action, shop=shop)


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


def write_match_final(gs: GameState, *, final_type: str,
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
    if gs.match_final.value is not None:
        return False   # 段内幂等(G12 写前查重):同段恰一行
    if duration_s is None:
        duration_s = max(time.monotonic() - gs.created_monotonic, 0.0)
    if not note and backfilled:
        note = 'recovered'   # G8 补写行显影(判读按注记分型,防混计)
    payload = MatchFinal(
        final_type=final_type,
        at_version=gs.write_seq + 1,   # 本行自身版本 id(与行头 v 恒等)
        code_commit=_CODE_COMMIT,
        registry_fingerprint=_REGISTRY_FINGERPRINT,
        plane=plane, round_num=round_num, node_kind=node_kind,
        level=level, hp=hp, gold=gold, streak=streak,
        duration_s=duration_s, backfilled=bool(backfilled),
        cw4_counters=(dict(cw4_counters) if cw4_counters is not None else None))
    seq = gs.write_seq + 1
    sig = ChannelSig(family='logic_hook', actor='MatchClose', screen=None,
                     mode='compute', group_id=f'hook:MatchClose@{seq}')
    gs.write_logic(gs.match_final, payload, produced_by='MatchClose',
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
            log.debug(f'[cw-gs] match_final listener skip: {e}')
    return True


# ============================================================ 单例宿主


_GS_BY_SESSION: weakref.WeakKeyDictionary[object, GameState] = \
    weakref.WeakKeyDictionary()
#: 桩面兜底第二级:属性不可写对象(__slots__ 族)的 id() 键 dict
#: (旁表自身既有结构;挂对象属性优先)。
_GS_BY_SESSION_ID: dict[int, GameState] = {}
_GS_ATTR = '_cw_game_state'


def _establish_singleton_journal(
        run_id_provider: Callable[[], str] | None) -> None:
    """局容器单例建立点的遥测装配触发(正主单例建立路径专属)。

    用户裁定 2026-09-15(精化令):装配触发只钉本建立点——GameState
    构造器零装配逻辑,画面解析草稿容器的直构路径(planner/invest_strategy
    防御视图/env_economy 导入期探针)结构性不可能触发遥测。provider =
    建立调用方(生产注入漏斗 = establish_new_match 容器建立点)显式注入
    的 run 归属读取函数(kernel 禁依 telemetry,依赖倒置);None = 不装配
    (sim/测试/一次性视图口径)。幂等已装配零成本直过——「未初始化容器
    首写前装配已发生」的行为等价锚;装配失败不阻塞容器建立,与行落盘同
    best-effort 纪律。
    """
    if run_id_provider is None:
        return
    try:
        ensure_journal_assembly(run_id_provider)
    except Exception as e:  # noqa: BLE001  装配失败不阻塞容器建立
        log.warning('[cw!][gs] journal 装配失败(不阻塞): %s', e)


def gs_of_ctx(ctx: object, session: object) -> GameState:
    """容器取口(终态契约 §2.6/T-4 ops 桶):优先 ``ctx.cw_match.gs`` 持有
    引用;kernel fallback(:func:`game_state_of`,桶 3)**暂留至 3.5 注入化
    时统一删除**。值同一实例(持有引用与旁表单例同对象),行为零变化。
    ctx 无 match / match 无 gs(桩面)→ fallback 兜底,调用方零改。
    """
    _m = getattr(ctx, 'cw_match', None)
    if _m is not None and getattr(_m, 'gs', None) is not None:
        return _m.gs
    return game_state_of(session)


def game_state_of(session: object, *,
                  run_id_provider: Callable[[], str] | None = None) -> GameState:
    """GameState 单例访问口(session 旁表;弱引用表 + 桩面兜底)。

    - session = 局身份:新 session 对象 = 新局 = 新 GameState(§1 每局新建);
    - None → 一次性空载体(不缓存——None 的 id 恒定,缓存即跨调用串染);
    - 裸 session(测试/sim 桩)→ 惰性建并挂对象自身属性(生命周期随对象);
    - run_id_provider = 局容器单例建立时点的遥测装配注入(用户裁定
      2026-09-15:装配 = game state 职责,触发只钉本建立点;经
      :func:`_establish_singleton_journal`,GameState 构造器零装配逻辑),
      仅辖**新建**时点(已存在直读不触装配——幂等兜底对已装配进程本就
      零成本);session=None 一次性空载体(局外,不缓存)不装配——装配是
      进程级副作用,不属一次性视图。缺省 None = 不装配(sim/测试/局外
      防御视图构造口径;生产注入漏斗 = establish_new_match)。
    """
    if isinstance(session, GameState):
        return session   # 终态契约 §2.6:本体直通(身份透传)
    if session is None:
        return GameState(schema_version=GAME_STATE_SCHEMA_VERSION)   # 局外一次性:不装配
    try:
        gs = _GS_BY_SESSION.get(session)
    except TypeError:   # 不可弱引用对象(测试桩)
        gs = getattr(session, _GS_ATTR, None)
        if gs is None:
            _establish_singleton_journal(run_id_provider)
            gs = GameState(schema_version=GAME_STATE_SCHEMA_VERSION)
            try:
                setattr(session, _GS_ATTR, gs)
            except (AttributeError, TypeError):
                _GS_BY_SESSION_ID[id(session)] = gs
        return gs
    if gs is None:
        _establish_singleton_journal(run_id_provider)
        gs = GameState(schema_version=GAME_STATE_SCHEMA_VERSION)
        _GS_BY_SESSION[session] = gs
    return gs


def tracked_unobserved(session: object) -> bool:
    """tracked 主账是否处于未观察态(判定单一源;策略商店门与执行侧
    跳过留痕/熔断消费)。

    判据 = 容器字段 :attr:`GameState.tracked_account_observed` 显式 False
    (接管/重置/账失效写);None(从未写,缺省可信)与 True(已锚定)均
    为已观察。session 经容器读口解析,字段从未写(缺省)不视为未观察。
    """
    return game_state_of(session).tracked_account_observed.value is False


# ============================================================ GameState 单例


@dataclass
class TrackedBooks:
    """tracked 主账簿记(game state 层容器簿记组)。

    bench/deployed = pad 态定长槽位表(list[BenchChar | None],ADR-0316/
    0392)。**执行侧簿记容器**:写端 = kernel reconcile_tracking(观察边界
    锚定写回)+ 动作随动同步(部署/卖出/溢出腿);**策略禁读**——观察
    状态与策略消费口 = GameState.tracked_account_observed +
    bench/front_row/back_row 席位视图。
    """

    bench: list = field(default_factory=list)
    deployed: list = field(default_factory=list)


class NodeBooks:
    """节点序列探针簿记组(容器内独立宿主组;非 Field,不进快照流水;
    终态契约 §A′ 收编:自 session 宿主迁入——写读经本组单一源)。

    [索引定义] plane_node_table = 开局帧实读槽序表(list[str],当前位面
    槽序,位面内恒定);plane_node_table_plane = 表归属位面号(1-based,
    每位面首帧重写时更新);plane_lengths_seen = 已揭晓位面长度序列
    (下标 i = 第 i+1 位面,进表即自适应)。取值时机 = cw_screen_prep
    每位面首帧采集写入(store_plane_table,唯一写端);读端 =
    kernel/cw_plane_table(经 game_state_of 桥)。局级生命周期
    (新局新容器 = 天然清零)。
    """

    plane_node_table: list[str] | None = None
    plane_node_table_plane: int | None = None
    plane_lengths_seen: list[int] | None = None


@dataclass(frozen=True)
class TokenCell:
    """链观察单格读数(链正本 = game_state/chain-observation.md §2;逐格
    元数据随读数落载体)。

    token = 类型 token(封闭集 battle/supply/encounter/reward/boss + 仅标签
    通道 elite/megastar/invest;None = 本帧未辨)。channel = 产出通道封闭集
    {hu, label, sift, none, dim}:hu = 模板形状匹配 / label = OCR 标签 /
    sift = boss 命中 / none = 未辨 / dim = 已过暗格(不认类型)。
    hu_dist = Hu 残差/置信(SIFT 命中格记好匹配数;标签格照记)。
    """

    token: str | None
    channel: str
    hu_dist: float | None = None


@dataclass(frozen=True)
class NodeChain:
    """链值载体(链正本 §2):本位面节点类型链,值自带位面防切换窗读陈旧链。

    [索引定义] ``seq`` 下标 i(0-based)= 该位面第 i+1 轮的读数单元,与
    判读侧台账 ``PlaneNodeLedger.seq_by_plane`` 同下标语义;取值时机 =
    生成期帧快照(现行链 = 最新权威读数**整帧覆盖**,不按位合并;基线链 =
    位面入口写定,本位面内不被链读覆盖);写入端 = 备战帧入口 heavy 链读
    (prep_row)/ 过渡屏观察段(transition_row / transition_snapshot),
    链观察落地批 2026-09-16 起。
    """

    plane: int
    seq: list[TokenCell] = field(default_factory=list)


@dataclass
class PlaneNodeLedger:
    """本局 per-plane 节点序列台账 + 逐帧校验的去重/豁免状态。

    宿主:``GameState.plane_node_sequences``(本模块;非 Field 簿记——
    整行快照语义、逐位合并写、低频重写,Field 化收益低;经
    :func:`sr_od.application.currency_war.kernel.cw_exec_state.get_node_ledger`
    惰性解析。容器每局新建 = 天然清零,无跨局污染)。
    """

    #: 键 = 位面号(1-based);值 = 节点类型序列,**下标 i(0-based)= 该位面第 i+1 轮**
    #: 的类型 token(battle/supply/encounter/reward/boss,与
    #: ``cw_node_reader.NodeSlot.node_type`` / ``CwSimFrame.node_type`` 同词汇表;
    #: None = 该位次未识别占位,合并时被后续非 None 读数覆盖)。
    #: 取值时机:写入端每次整行重读时快照(见各写入端);读端 = 备战帧查
    #: ``seq[round_num - 1]``。
    #: 写入端:①位面详情采集(CwScreenPlaneIntel,进位面时的两源互证产物);
    #: ②投资环境选择完成后重读备战节点行(CwScreenInvestEnv,变异窗后的权威刷新)。
    seq_by_plane: dict[int, list[str | None]] = field(default_factory=dict)

    #: 每序列的写入来源('plane_detail' = 位面详情采集 / 'prep_row' = 备战节点行),
    #: 判读侧区分表值的采集通道用(位面详情=彩色渲染态全量,备战行=含 past 遮挡)。
    seq_source: dict[int, str] = field(default_factory=dict)

    #: 位面 → 位面详情底部明文「敌人难度 N」参考值。**只存参考**——生产难度
    #: 主源 = 备战旗牌两级管线(ADR-0449),本字段供离线对拍/缺口排查。
    difficulty_ref: dict[int, int] = field(default_factory=dict)

    #: 投资环境变异窗豁免截止(time.monotonic 时刻;0.0 = 无窗)。窗内查表与
    #: 逐帧校验的不一致**不落**缺陷台账——环境选择到节点行重读之间节点行
    #: 正在合法变异(用户口述:投资环境是唯一变异源),不一致是预期而非识别错误。
    #: 写入端:CwScreenInvestEnv 确认前开窗、重读刷新台账后关窗(置 0)。
    env_grace_until: float = 0.0

    #: 已落过缺陷的 (plane, round) 键集(逐帧校验每帧都会跑,同一不一致只落一行)。
    defect_seen: set[str] = field(default_factory=set)


@dataclass
class GameState:
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
    # [索引定义] node_path.seq 下标 = 该位面第 i+1 轮(0-based,与
    # PlaneNodeLedger.seq_by_plane 同下标语义);取值时机 = 生成期帧快照
    # (整帧覆盖,不按位合并);写入端 = 备战帧入口 heavy 链读(prep_row)/
    # 过渡屏观察段(transition_snapshot),见 NodeChain 注(链正本 §2/§3)。
    node_path: Field[NodeChain | None] = field(default_factory=Field)          # 现行链(§3.2.2)
    node_path_baseline: Field[NodeChain | None] = field(default_factory=Field)  # 基线链(链正本 §2/§3:位面入口写定,本位面内不被链读覆盖)

    # —— 单位域(含星级与装备)——
    front_row: Field[list[Unit]] = field(default_factory=Field)  # 前排成员(§3.2.3)
    back_row: Field[list[Unit]] = field(default_factory=Field)   # 后排成员(§3.2.4)
    bench: Field[BenchView] = field(default_factory=Field)       # 备战席统一槽位视图(§3.2.5;capacity 随效果改写)
    back_layout: Field[int] = field(default_factory=Field)       # 后台格数(值域 6-9:平常 6,宝钻/召唤物扩展,上限 9;6/7/8/9 四档均已交互建档——9 档凭据=cw_back_layout._LAYOUT_PREFIX 与 screen_info 后排9槽-1..9;>9 域外按 8 格超集运行+evidence superset 标记,§3.2.7)
    # [索引定义] tracked_account_observed = tracked 主账(bench+deployed 两
    # 面,同帧锚定)的观察状态(用户裁定「观察状态落 game state 字段,
    # 策略消费只走 game state」;三态语义:None = 从未写 = 缺省可信——正常
    # 新局 0 件即屏幕真值,且不经失效事件的 sim/离线入口不受误伤;False =
    # 显式失效(接管/重置/账失效)后未锚定,值不可消费;True = 备战环
    # heavy 观察(observe_full → reconcile_tracking)屏幕真值写回成功 =
    # 已锚定)。取值时机 = 事件驱动(非逐帧)。写入端:False = cw_loop
    # ._mark_session_resumed(接管检测确认点;重置/账失效类事件同口写);
    # True = kernel reconcile_tracking 的 bench 侧屏幕真值写回成功点
    #(唯一锚定写端;bench 读失败/双空读守卫/槽号健康门拒绝均不写 = 保持
    # 未观察)。消费面:策略商店门(flow.decide_shop_action,未观察 →
    # CwActionCloseShopParam 交回外循环走备战重锚定;判定单一源 = 本模块
    # tracked_unobserved)。tracked 主账宿主 = 容器簿记 tracked_books
    #(reconcile 输入/输出与动作随动同步),无面向策略的读口。
    tracked_account_observed: Field[bool] = field(default_factory=Field)

    # —— 经济与成长 ——
    gold: Field[int] = field(default_factory=Field)              # None=不可读(§3.2.9)
    level: Field[int] = field(default_factory=Field)             # 等级(§3.2.10;启发式兜底值禁入——非真读走 carried)
    xp: Field[tuple[int, int]] = field(default_factory=Field)    # (当前级已攒, 升下一级所需)(§3.2.10;同文本两分量成对存)
    streak: Field[int] = field(default_factory=Field)            # 带符号:正=连胜/负=连败(§3.2.12)
    hp: Field[int] = field(default_factory=Field)                # 写入闸 §3.2.13:非真读帧不经 observe(§8.8 假值防线)
    level_up_cost: Field[int] = field(default_factory=Field)     # 单击买经验价(§3.2.11;None=未读到禁兜底)
    # [索引定义] deploy_cap = 部署容量识别真值(= level + 财富宝钻数,可叠加)。
    # 坐标系 = 「X/Y」指示的 Y 人数口径;取值时机 = 备战帧观察期快照(ADR-0420
    # 双帧一致采信门输出,写端 = cw_observation.read_game_state spec 门
    # 'deploy_cap' 键,防抖核 = cw_observation._debounce_cap 单一源)。
    # W5 定谳入容器(W5-透传域建模方案 §2.3;推翻设计正本 §3.2.7「现场实时
    # 读值豁免」在册前提,正本更新义务见方案稿 §2.3):与 back_layout 双存
    # 属 §8.8 在册例外形态(识别口径 vs 推导口径各有消费面,先例 = board、
    # level_up_cost)——cap=识别源(采信门输出),back_layout=三信号裁决结果
    # (cw_back_layout);理论关系 back_layout ≈ 6+(cap−level) 仅域内成立,
    # 域外态(>9)back_layout 是 8 格超集,反推会把近似当真值,故不派生改双存。
    # 两域冲突走缺陷台账,不互改。
    deploy_cap: Field[int] = field(default_factory=Field)

    # —— 局级事实 ——
    selected_difficulty: Field[str] = field(default_factory=Field)   # 职级,开局写定恒稳(§3.1.1)
    game_mode: Field[str] = field(default_factory=Field)             # 对局类型:标准/超频博弈(§3.1.2;两屏无建档,接线前补档)
    enemy_difficulty: Field[int] = field(default_factory=Field)      # 非单调(§3.2.14)

    # —— 接管/恢复局旗标组(渠道③接管协议 logic_hook,relay 契约同族先例;
    # match_facts 域扩展,域版本 2)——局级生命周期,新局新容器 = 天然缺省
    # None 恒假。
    # [索引定义] resumed_match: True = 本局为恢复对局(新 match 但游戏在中局
    # 续跑)——弹窗腿在派生 hist 空时禁用不猜(防把恢复局首弹窗误推断成开局
    # 节点 1),消化后备战帧腿 A 权威接管。写入端单一源 = cw_loop 恢复检测两
    # 确认点(_iter==1 战斗帧恢复检测 / 备战帧 resume_candidate 确认,
    # ``_mark_session_resumed`` 单口);读端 = cw_observation.read_game_state
    # (经 observe_screen_context(resumed=…) 进派生规则,读值不落旗标——
    # 一次性会话语义,非消费即清)。None = 未写(正常新局恒假语义,开局推断
    # 合法不受误伤)。
    resumed_match: Field[bool] = field(default_factory=Field)
    # [索引定义] takeover_collect_done: 接管采集已完成(节点内一次性)。
    # 写入端 = cw_screen_prep 接管补采段三点(门读/放弃置位/成功置位),
    # actor = ResumeAttach(接管协议登记名);None = 未写(恒假语义)。
    takeover_collect_done: Field[bool] = field(default_factory=Field)
    # [索引定义] takeover_tries: 接管采集重试计数(单调递增,单口累加;
    # 值 None 按 0 基线读——计数器是局内累计,0 基线是构造事实非观察兜底)。
    # 唯一写读点 = cw_screen_prep 接管补采段(每轮次 +1,>2 放弃)。
    takeover_tries: Field[int] = field(default_factory=Field)

    # —— 遭遇选档观测面(E-2 平级新结构;非 Settlement 域字段,准入注释见该域)——
    # 结算观测环:产结算屏节点的 RoundOutcome 消费子集,深度 10,同场去重合并,
    # 生命周期 = 局(开局清空;relaunch 残留行由写入端 residual 排除)。判据与
    # 经验层读源单一源(遭遇选档迭代设计 §8)。
    settlement_ring: SettlementRing = field(default_factory=SettlementRing)
    # 遭遇经验表:本局全量遭遇行(其五/六 Δ 无源档的经验正证据通道;跨局
    # 持久化挂账另行立项)。
    encounter_log: EncounterLog = field(default_factory=EncounterLog)
    plane_bosses: Field[list[str | None]] = field(default_factory=Field)  # 三位面 boss 名,None=该位面无身份(ADR-0398)
    active_env: Field[str | None] = field(default_factory=Field)     # 已选投资环境(§3.2.20/§3.4.3)
    enemy_affixes: Field[list[str]] = field(default_factory=Field)   # 当前词缀名单(§3.1.3;≠投资环境)
    active_strategies: Field[list[str]] = field(default_factory=Field)   # 持有投资策略名单(§3.4.4;品质锚挂建模批)
    board: Field[dict[str, int]] = field(default_factory=Field)      # 上阵羁绊计数(§3.2.6;下档阈值=派生不存储)
    shop_refresh_cost: Field[int] = field(default_factory=Field)     # 刷新费,动态(§3.3.4/ADR-0622 现场 OCR;免费帧不写,None≠0)

    # (商店刷新计数组三字段——free_refresh_balance/paid_refresh_count/
    #  total_refresh_count——已随 2026-09-18 用户裁决迁出容器,住效果账本
    #  ActiveEffectInventory(统一计算,写端 = 刷新上报函数;消费方 =
    #  env_economy 选卡评估/免费闸),考古走 git。prev_node_spent 不属
    #  迁出面,保留原位。)
    prev_node_spent: Field[bool] = field(default_factory=Field)      # 上节点是否花费(§3.3.9;存款回报条件输入,观察需求)

    # —— 节点屏刷新计数组(§3.4.1-§3.4.4;渠道② logic_action,写入=仅逻辑)——
    # 写端现状:encounter/strategy = on_outcome 发射型钩子(发射即 +1,唯一
    # 写点);supply = live CwScreenSupplyNode 刷新分支单点 + sim observe
    # 通道(两源同域);**env_refresh_used = 零写端申报不动**(观察通道在册
    # cw_node_obs「剩余次数」,字段位先申报禁静默,禁按字段值做决策)。
    encounter_refresh_used: Field[int] = field(default_factory=Field)    # 遭遇刷新已用(§3.4.1;写端 = CwScreenEncounter on_outcome 发射型钩子)
    supply_refresh_used: Field[int] = field(default_factory=Field)       # 补给刷新已用(§3.4.2;live 写端 = CwScreenSupplyNode 刷新分支单点;「无布局局原生可刷」收窄待证)
    env_refresh_used: Field[int] = field(default_factory=Field)          # 环境刷新已用(§3.4.3;观察通道在册 cw_node_obs「剩余次数」)
    strategy_refresh_used: Field[dict[str, int]] = field(default_factory=Field)  # 投资策略逐卡刷新已用(§3.4.4;写端 = CwScreenInvestStrategy on_outcome 发射型钩子)。**键口径显式申报(迁移批次二)**:键 = 注册表规范卡名(normalize_invest_name 归一后;选名不选 spec.id 的理由 = 效果注册表 STRATEGY_EFFECTS 即以规范名为键,写端 OCR 名经同一归一函数入键,免双坐标系换算)。值域纪律:基线每卡 1 次、例外三族(银金彩环境+2/投资卡族=3/期货族=0/远见=0)以注册表官方全文为唯一口径,禁按基线做核对预期

    # —— 轮内新鲜度账(「本轮已买」半边;渠道② logic_action,写入=仅逻辑)——
    # [索引定义] 值形状 = {'phase': (plane, round_num) | None,
    # 'names': list[str]}:names = 发射位买入时逐名写入的轮内新鲜买入名集
    # (dict 内集合已按容器 JSON 序列化安全形存 list,record_fresh_buy 内部
    # 转形,读端成员判断在个位数量级无性能面);phase 失配 = 跨轮整体作废
    #(读取零销账,无逐名生命周期面);None = 本局未登记。写端 = shop.
    # _emit_buy 全部 CwActionBuyCardParam 发射位,经
    # cw_deploy_logic.record_fresh_buy 单口(渠道②动作上报,actor =
    # 'CwDeployLogic' 登记面在册);读端 =
    # cw_deploy_logic.fresh_buys_of(换出守卫)+ fresh_buys_sell_face
    #(L1 卖侧闩,fail-closed,ADR-0611 §3-1;写读单口不变)。
    round_fresh_buys: Field[dict | None] = field(default_factory=Field)

    # —— 持久账本组(跨画面保留)——
    # ⚠️ 免战牌不在本组(§8.6-3 载体归一,迁移批次二):激活态+剩余次数
    # 正本 = effect_inventory.remaining_uses(§5.1,ActiveEffect.remaining_
    # uses「次数类余量(免战牌×2 等)」,同型躺平/节省工位;批次一骨架的
    # skip_battle_active/remaining 两 Field 已按正本归一移除,消费走
    # gs.effects 查询)。
    equips: Field[list[str]] = field(default_factory=Field)          # 装备库存(§3.2.15)
    # [索引定义] occupied_equips:已穿装备位置(装备域姊妹面,迭代
    # 2026-09-18-prep-obs-retirement 阶段 3.2 立域)。键坐标系 =
    # 'front:1'/'back:2' 形态字符串(row ∈ front|back,slot = 画面物理槽位
    # 1-based,前排 1-4/后排 1-选档 N,与机械动作参数同域——坐标系正本 =
    # cw_prep_actions.PrepObservation.occupied_equips 声明;tuple 键 JSON
    # 序列化不安全故字符串化);值 = 件名列表。取值时机 = 备战 heavy 观察
    # 每入口帧实读覆盖(两态制,观察赢);写入端单一源 = CwScreenPrep 观察
    # 写端(与 equips 同点同环);未观察(None) = 识别域未就绪,M7 装备计划
    # 按 fail 门保守关(与旧黑板 None 语义同映射)。
    occupied_equips: Field[dict[str, list[str]]] = field(default_factory=Field)
    consumables: Field[list[str]] = field(default_factory=Field)     # 消耗品库存(§3.2.16)

    # —— 晶矿(§3.2.8,不占席)——
    # 域名 spheres = 晶矿域既定名(本义即晶矿球,非旧名残留;2026-09-20
    # ore 改名收口裁定不辖容器域名,fields.md §3.2.8 声明)。
    spheres: Field[OreSight] = field(default_factory=Field)

    # —— 交互状态 ——
    prep_substate: Field[str] = field(default_factory=Field)     # 分类子态四档(§3.2.17;恢复锁定=会话推断档,写端=接管协议 §6.3)
    event_overlay: Field[str | None] = field(default_factory=Field)  # 'none'=确认无浮层;None=没读到(§3.6.1 双义禁令)

    # —— 备战席溢出(§3.2.20;2026-09-15 实机建档 prep.md 告警/溢出节)——
    # [索引定义] overflow_warning:告警横幅「备战席已满」在场 = 存在未安置
    # 溢出角色(此刻出战点击被游戏忽略——launch_dead 三连停机实证;策略
    # 消费门 = mandate 溢出门,先卖腾位再出战)。取值时机 = 备战 heavy
    # 观察每入口帧实读覆盖(两态制,观察赢);写入端单一源 = CwScreenPrep
    # 观察写端(渠道①)。CwActionSellBenchParam 溢出腿(卖出自上报)落地
    # 后 logic 直写 False(推算消亡,下帧实读覆盖);落地同帧容器 bench
    # 回占入位卡 + 执行侧 tracked 主账对称吸收(session 在场;
    # 缺吸收 = 守卫播种期双账分叉实机停机)。
    overflow_warning: Field[bool] = field(default_factory=Field)
    # [索引定义] overflow_card:溢出位(固定停车位,建档 area「区域-溢出角色」,
    # 1080p rect 1352,710-1465,805)上的角色身份。'' = 溢出位无卡或身份未
    # 识别(与 overflow_warning 配对解读:True ∧ '' = 有卡未识别);值语义
    # = CwActionSellBenchParam 溢出腿的入位对象身份(char_id;星级缺读按 1 兜底,下帧
    # heavy 实读覆盖修正)。写入端单一源 = 同上观察写端;溢出腿落地后
    # logic 直写 ''(入位消费)。
    overflow_card: Field[str] = field(default_factory=Field)

    # —— tracked 主账簿记宿主 ——
    # [索引定义] tracked_books.bench/deployed = tracked 槽位表(list[BenchChar
    # | None],pad 态定长 9/10 槽含 None,ADR-0316/0392)。**簿记容器,非
    # Field 观察面**(先例 = settlement_ring/encounter_log:不经 observe/
    # write_logic 通道,无观察赢仲裁,写端直改;元素 BenchChar 沿用既有
    # 就地变异语义——shop mutate/部署装备回写)。**策略禁读**(消费口只有
    # game state 的观察态字段 tracked_account_observed 与席位视图
    # bench/front_row/back_row);合法写端 = kernel reconcile_tracking(观察
    # 边界锚定写回)+ 动作随动同步(prep 执行器/溢出腿/部署装备回写/
    # 商店 mutate)。观察状态(未观察/已观察)= 上方 tracked_account_observed。
    tracked_books: TrackedBooks = field(default_factory=TrackedBooks)
    # —— 节点序列探针簿记宿主(非 Field;终态契约 §A′ 自 session 迁入,
    # 成员与访问纪律见 :class:`NodeBooks` 类注)——
    node_books: NodeBooks = field(default_factory=NodeBooks)
    # (备战黑板帧宿主 prep_obs 已随黑板退役删除——迭代
    #  2026-09-18-prep-obs-retirement 阶段 3.5:名单/装备/占用/晶矿全部
    #  容器域承载,策略器唯读容器契约归位。)

    # —— 帧触发代次双槽(非 Field 簿记;终态契约 §B:session
    # prep_frame_class/shop_frame_class 退役迁此,两槽互不相干禁合并——
    # 标注对象分别为「最近一次备战域/商店域容器观察写点」)。
    # [值域] 'full' | 'view' | 'none',缺省 'none'。消费协议 = 读后即清
    # 'none'(读协议半部,防同帧重复刷新);写端 = 备战/商店域观察装配点。
    # 非 Field 理由 = 纯过程信号(无观察赢仲裁、无 journal 面秒级生命周期),
    # 容器每局新建 = 天然清零。
    frame_class_prep: str = 'none'
    frame_class_shop: str = 'none'

    # —— 局级节点序列台账(非 Field 簿记,非域字段,工程结构组单列申报)——
    # [索引定义] 值 = :class:`PlaneNodeLedger`(本模块;seq_by_plane 键为
    # 1-based 位面号,序列下标 0-based = 该位面第 i+1 轮,取值时机 = 写入端
    # 整行重读快照,定义详注在类头)。非 Field 理由 = 整行快照语义、逐位
    # 合并写、低频重写,Field 化收益低;
    # 容器每局新建 = 天然清零。**访问单一源 = cw_exec_state 三访问函数**
    # (get_node_ledger / ledger_node_type / ledger_update_plane),读写禁
    # 直摸本字段——消费面(画面 op 三写入端 + kernel 判据/遥测读端)零改动
    # 由此闭合。
    plane_node_sequences: PlaneNodeLedger = field(
        default_factory=PlaneNodeLedger)

    # —— 画面附加域(当前画面的 payload,非当前画面=None,§2.2 例外)——
    shop: Field[ShopPayload | None] = field(default_factory=Field)
    encounter: Field[EncounterPayload | None] = field(default_factory=Field)
    supply: Field[SupplyPayload | None] = field(default_factory=Field)
    # —— 选择族动作化 payload 槽(终态契约 landing §3.1;八新槽,纯增量
    #    零消费——写端接线归 3.4/3.5,现役无写无读)——
    invest_strategy_opts: Field[list[str] | None] = field(default_factory=Field)
    invest_env_opts: Field[list[str] | None] = field(default_factory=Field)
    megastar_opts: Field[list[MegastarOption] | None] = field(default_factory=Field)
    partner_opts: Field[list[PartnerOption] | None] = field(default_factory=Field)
    planner_opts: Field[list[PlannerOption] | None] = field(default_factory=Field)
    star_tome_opts: Field[list[str] | None] = field(default_factory=Field)
    wish_trial_opts: Field[list[str] | None] = field(default_factory=Field)
    box_card_names: Field[list[str] | None] = field(default_factory=Field)
    # —— 契约扩员 12→15 新槽(普查迁移批 2;写端 = 各画面 handler 写槽,
    #    消费 = flow 三新零参入口 decide_fortune/expert_invite/equip_pick)——
    fortune_opts: Field[list[str] | None] = field(default_factory=Field)
    expert_invite: Field[ExpertInvitePayload | None] = field(default_factory=Field)
    equip_pick_opts: Field[list[str] | None] = field(default_factory=Field)
    # encounter 刷新建议 per-visit 位(契约:写 False = 各决策路径首调前置,
    # 写 True = 刷新发射同步直写,均 fail-loud;读侧 None 缺省 False;
    # journal 归属 = write_logic 常规规则,不适用刷新计数组豁免类)
    encounter_refreshed_in_visit: Field[bool] = field(default_factory=Field)

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

    # —— 逻辑态派生域与画面上下文域(R1 §3.1.4;gs_schema 域 'derivation')——
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

    # —— 动作回执域(R2 §3.1.1-4/§3.2.5;gs_schema 域 'receipts')——
    # [索引定义] receipts 值 = 动作执行回执的滚动窗:list 下标 i = 第 i 条
    # 存活回执(窗序 = 写入序,先进先出,容量 = :data:`RECEIPTS_WINDOW_CAP`);
    # 取值时机 = 写入期快照(帧替换,禁就地改窗内条目)。唯一写点 =
    # :func:`note_action_receipt`(渠道② logic_action);失败动作也产行
    # (applied=false + reason)——exec_events「失败可见性」收编载体。
    receipts: Field[list[dict]] = field(default_factory=Field)

    # —— 局终域(R5 W2;§3.6.1 runs 收编载体;gs_schema 域 'match_final')——
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
    gs_schema: dict[str, int] = field(
        default_factory=lambda: dict(DEFAULT_GS_SCHEMA))
    # 帧观察完整度标注(full/view/none)——消费即清,不当停更哨兵(§2.4)。
    frame_obs: FrameObsLevel = 'none'
    # 心跳载体:写点序号,只增不减(§2.4 停更检测哨兵)。
    write_seq: int = 0
    # [索引定义] node_hist_ord = 本 run 已见最大有效节点序 effective_ord
    # (effective_ord = :func:`effective_node_ord` 生效序读口现值,坐标系 =
    # (plane-1)*9+round 基 1,与效果账本 advance_node 同键);派生规则推进
    # 去重键 (run_id, effective_ord) 的 run 内载体(设计 v3.1-N2)——同序
    # 恰一次推进,先到腿越 hist 即推进,后到腿同序零推进。取值时机 = 派生
    # 写入期单调推进;None = 本 run 尚无派生推进。写端 = 派生规则。
    node_hist_ord: int | None = None
    # [索引定义] node_path_diff_pending = 链 diff 两帧确认门的待确认候选
    # (链观察落地批):上一 clean 备战帧相对基线的差异链快照,下一 clean
    # 帧读数与其一致才落 chain_diff 行(单帧翻转不产行,链正本 §4);
    # None = 无待确认候选。写端 = :func:`maybe_emit_chain_diff`(备战帧
    # 链写端);离场快照与变异窗豁免路径会清候选。
    node_path_diff_pending: NodeChain | None = None
    # 段级时长锚(局终域 duration_s 自算源):容器创建时刻的 monotonic 读数
    #(每局新建 = 天然段起点;恢复局跨段 = 各段各锚,聚合归判读侧)。
    created_monotonic: float = 0.0
    def __post_init__(self) -> None:
        """构造守卫(任务书件 5/§8.6-5):schema_version 正整数 + Field
        冻结不变式断言(帧替换语义的结构前提,破即构造炸错不静默)。
        零装配逻辑(精化令 2026-09-15:装配触发只钉正主单例建立路径
        = :func:`game_state_of` 局容器建立点;画面解析草稿容器的直构路径
        ——planner/invest_strategy 防御视图/env_economy 导入期探针——结构性
        不可能触发遥测)。"""
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
        raise KeyError('target 不是本 GameState 的字段现引用'
                       '(须传 gs.xxx;跨单例引用 = 写丢事故)')

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
            log.debug(f'[cw-gs] journal row skip: {e}')

    def note_obs_event(self, event: str, field_name: str, observed: Any, *,
                       sig: ChannelSig,
                       verdict: str = '', obs_phase: str = '',
                       evidence_refs: list | None = None) -> None:
        """观察事件行(§3.2.3 行型 2;**零状态变更**的观察证据)。

        - 同流、**占版本**、内嵌当时 state(v3.1-N1:obs_event 与写入行同流
          同序,「run 段内行序 = 版本序」不变量覆盖全部行型);不触任何
          Field(行行自足,查询不分行型);
        - event 词表 = :data:`OBS_EVENT_EVENTS` 封闭集(arbitrate|miss|popup|chain_diff),
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
            log.debug(f'[cw-gs] obs_event row skip: {e}')

    def current_version(self) -> int:
        """策略侧版本读口(§3.2.2 规则 5:读不写、不占版本)= 已分配的最大
        版本号(write_seq 升格值,心跳哨兵载体语义不变)。"""
        return self.write_seq

    def full_state_snapshot(self) -> dict:
        """写入后完整 state 快照(§3.2.3 自足行的行内 state;JSON 安全化 +
        序列化规范化——effects 按 spec id 排序,同态同形)。含 values(非 None
        字段值)/ prov(非默认来源注记)/ effects(就地可变域整窗)/ 工程结构。
"""
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
            # 装备效果进度侧栏快照捕获(接线批追加;effects 逐条序列化不含
            # 侧栏,遥测/重放面缺口由本行收口)。键 =
            # 侧栏键 (装备名, 装备者) 序列化为「装备名|装备者」串(JSON
            # 安全);空侧栏 = 空 dict,行形状稳定。
            'equip_progress': {f'{k[0]}|{k[1]}': v
                               for k, v
                               in self.effects.equip_progress.items()},
            'frame_obs': self.frame_obs,
            'write_seq': self.write_seq,
            'node_hist_ord': self.node_hist_ord,
            'gs_schema': dict(self.gs_schema),
        }

    def observe(self, target: Field, value: Any, *,
                evidence: str | None = None,
                sig: ChannelSig,
                note: str = '') -> None:
        """观察写入:亲眼看,覆盖旧值(§2.1 observation)。

        - value=None 拒绝(§2.2 硬边界:失读不是观察值,走 :meth:`carry`
          或画面附加域 :meth:`leave_screen`;字段一旦有过正式值任何失读
          不得清成 None);
        - 覆盖 logic 来源值且失配 → 三分流处置(§2.3 观察赢;失配 =
          逻辑态被实读证伪 = bug,豁免/抑制/安灯三分流——
          :func:`_route_logic_mismatch`;失配默认安灯停机,修推算代码);
        - 覆盖 logic_rand 来源值且差异 → **预期内**(随机效果落地,非
          bug):只落 ``logic_rand_outcome`` 台账行留证(无告警无停机,
          随机模型校准遥测面;sim 证据行由 :func:`_emit_defect` 发射口
          抑制面兜底),覆盖照常 = 随机结果采新;
        - sig = 渠道①签名(必填;R5 W1 起缺位合成路径已退役,ADR-0634);
        - note = 可选行注记(结算事实等语义,ADR-0634 battle_done 收编)。
        """
        if value is None:
            raise ValueError('observe 不接受 None(§2.2:失读走 carry/'
                             'leave_screen,禁清正式值)')
        _validate_sig(sig, ('obs',))
        name = self._field_name(target)
        if target.source == 'logic_rand' and target.value is not None \
                and target.value != value:
            # 逻辑随机态被观察覆盖:差异 = 随机效果落地,预期内非 bug
            # ——不进三分流,只落台账行留证(等值 = 零新信息不产行,
            # settle_truth 同纪律;发射口抑制面兜底 sim 证据行)。
            _emit_defect(field_name=name, expected=target.value,
                         actual=value, evidence=evidence, sig=sig,
                         logic_evidence=target.evidence,
                         kind='logic_rand_outcome')
        elif target.source == 'logic' and target.value is not None \
                and target.value != value:
            if self._absorb_slot_reorder(name, target, value,
                                         evidence, sig):
                pass   # 行内纯重排吸收已落台账行,覆盖照常 = 采新
            elif self._absorb_board_derived(name, target, value,
                                            evidence, sig):
                pass   # board 派生漂移观察覆盖采新已落台账行,跳过三分流
            else:
                _route_logic_mismatch(field_name=name, expected=target.value,
                                      actual=value, observed_evidence=evidence,
                                      logic_evidence=target.evidence, sig=sig)
        self._swap(name, Field(value=value, source='observation',
                               evidence=evidence),
                   sig=sig, note=note)

    def _absorb_slot_reorder(self, field_name: str, target: Field,
                             value: Any, observed_evidence: str | None,
                             sig: ChannelSig) -> bool:
        """行槽位纯重排吸收(§2.3 失配分支前置;front_row/back_row 专属)。
        游戏侧会在**行内自行重排**已上阵单位(排序规则游戏私有,非 bot
        动作,无逻辑写端)——同单位多重集的排列差异是机制性结构差异,不是
        推算 bug。命中条件全列(缺一不可):字段 ∈ {front_row, back_row};
        新旧值均为非空 list 且长度相等;单位多重集相等(键 =
        :func:`_rows_unit_key`,槽位号不在键内,装备集在键内——穿戴变化
        不算重排)。命中 → ``deploy_slot_reorder`` 台账行(无告警无停机,
        豁免 ≠ 消失同纪律)后覆盖照常 = 采新(游戏侧排序为画面事实),
        与对账纠漂(tracked 主账采新)两面同向;形状不符(缺员/多员/
        星级差/装备差)返回 False 交回三分流照真失配停,真投影 bug 不被
        吞。返回 True = 已吸收(调用方跳过失配分流)。"""
        if field_name not in ('front_row', 'back_row'):
            return False
        old, new = target.value, value
        if not isinstance(old, list) or not isinstance(new, list) \
                or not old or not new or len(old) != len(new):
            return False
        old_keys = list(map(_rows_unit_key, old))
        new_keys = list(map(_rows_unit_key, new))
        if Counter(old_keys) != Counter(new_keys):
            return False
        _emit_defect(field_name=field_name, expected=old, actual=new,
                     evidence=observed_evidence, sig=sig,
                     logic_evidence=target.evidence,
                     kind='deploy_slot_reorder')
        log.info(f'[cw][gs] 行内纯重排吸收:{field_name} 同单位多重集 '
                 f'排列差异采新(游戏侧行内重排无逻辑写端,'
                 f'deploy_slot_reorder 留证)')
        return True

    def _absorb_board_derived(self, field_name: str, target: Field,
                              value: Any, observed_evidence: str | None,
                              sig: ChannelSig) -> bool:
        """board 派生漂移观察覆盖采新(observe() 失配分支前置,与纯重排/
        外部授予吸收族同列):board 是上阵单位集合的**派生量**,其对账
        语义区别于独立字段——独立字段失配 = 动作推算被实读证伪(修推算
        代码),board 失配的三种已知形态全是「观察层读数噪声/建模结构
        缺口」类,不是动作推算 bug:

        - 环境卡星徽等装备羁绊贡献只显于面板、容器行未建模(增量口径
          刻意保留的基座),佩戴者被移出后派生侧无从减除 → 幽灵计数
          (20260918-reconcile 第 5 例停局族,run_20260918_045918);
        - 注册表外/OCR 误读身份单位入行:Unit 不存阵营(禁注册表双源),
          容器派生路径对其零贡献(:func:`_row_unit_tags`),面板照显其
          羁绊;
        - badge OCR 单帧误读(第 5 例定谳:坏读数在观察侧)。

        「上阵单位集合」这一真不变量由 front_row/back_row 自身的失配/
        纯重排吸收面独立把守,board 对动作推算 bug 无独立检出力 → 命中
        即落 ``board_derived_adopt`` 台账行(无告警无停机,豁免 ≠ 消失
        同纪律)后覆盖照常采新:派生量以观察为真值源,坏读数显影于台账
        与观察侧 obs_conflict 留证链、由下一帧观察自愈(与 obs→obs 直采
        语义同向)。辖域 = evidence 前缀 ``proj_board_resync``(派生挂钩
        唯一合法写端,单一源 = :meth:`_resync_board_delta`):独立手写
        board = 越格契约违反,照真失配安灯(本吸收面不得沦为 board 全面
        赦免)。返回 True = 已吸收(调用方跳过三分流)。"""
        if field_name != 'board':
            return False
        if target.evidence is None or \
                not target.evidence.startswith('proj_board_resync'):
            return False
        _emit_defect(field_name=field_name, expected=target.value,
                     actual=value, evidence=observed_evidence, sig=sig,
                     logic_evidence=target.evidence,
                     kind='board_derived_adopt')
        log.info(f'[cw][gs] board 派生漂移观察覆盖采新:board '
                 f'{target.value} → 实读 {value}(派生量以观察为真值源,'
                 f'board_derived_adopt 留证;单位集合不变量由行域失配面'
                 f'独立把守)')
        return True

    def _resync_board_delta(self, field_name: str, old_value: Any, *,
                            produced_by: str, sig: ChannelSig,
                            rand: bool = False) -> None:
        """board 派生重算单一源(front_row/back_row 逻辑写端挂钩;本方法
        是「羁绊/阵营计数 = 上阵单位集合的派生量」的落码位,写入口 =
        :meth:`_write_logic_frame` 行域写后自动触发(write_logic/
        write_logic_rand 共用),禁绕过手写 board)。rand = 继承行域写入
        来源:行域为随机态时 board 派生写同标随机态(行域真值形态随采样
        奖励而变,board 为其派生,污染沿派生链传递)。

        语义 = **观察基座 + 行变更增量**:board 现值为 None(板未读过)
        时无派生基座,跳过等观察首读;否则对本次行写做单位多重集差
        (键 = :func:`_rows_unit_key`),新增单位逐个加其羁绊标签
        (:func:`_row_unit_tags`,L1 全集+装备贡献),移除单位逐个减、
        减至 0 摘键(面板语义:无成员不显行),差为零不写。增量口径
        (非全量重算)的依据:观察基座含左面板真值的装备羁绊贡献,而
        容器行单位未必携带穿戴建模(实机 2026-09-18 run_20260918_045918:
        环境卡授予的星徽穿戴只出现在面板,行单位 equips 为空)——全量
        重算会把基座真值抹掉,增量只施加本次动作的差,基座贡献保留。
        派生漂移由下一备战帧观察覆盖收敛,注释与接线一致:失配经
        :meth:`_absorb_board_derived` 采新留证(``board_derived_adopt``,
        安灯不响)——派生量以观察为真值源,观察侧坏读数显影于台账与
        obs_conflict 留证链、由下一帧观察自愈。"""
        board = self.board.value
        if board is None:
            return
        new_value = getattr(self, field_name).value
        old_counter = Counter(map(_rows_unit_key, list(old_value or [])))
        new_counter = Counter(map(_rows_unit_key, list(new_value or [])))
        added = new_counter - old_counter
        removed = old_counter - new_counter
        if not added and not removed:
            return
        new_board = dict(board)
        for u in list(new_value or []):
            k = _rows_unit_key(u)
            if added.get(k, 0) > 0:
                added[k] -= 1
                for t in _row_unit_tags(u, field_name):
                    new_board[t] = new_board.get(t, 0) + 1
        for u in list(old_value or []):
            k = _rows_unit_key(u)
            if removed.get(k, 0) > 0:
                removed[k] -= 1
                for t in _row_unit_tags(u, field_name):
                    v = new_board.get(t, 0) - 1
                    if v > 0:
                        new_board[t] = v
                    else:
                        new_board.pop(t, None)
        if new_board == dict(board):
            return
        write = self.write_logic_rand if rand else self.write_logic
        write(self.board, new_board, produced_by=produced_by,
              evidence='proj_board_resync', sig=sig)


    def settle_truth(self, target: Field, value: Any, sig: ChannelSig) -> None:
        """结算屏真值收口(金币专用;无条件观察赢,不走失配三分流)。

        为什么不经 observe():节点收入由游戏侧在结算屏展示前入账,bot 无
        逻辑写端,账本与结算真值的差 = **预期边界收入**而非推算 bug,
        三分流(安灯停机)不辖——经 observe 失配链则每场战斗必停局
        (2026-09-18 全夜停局病态);收入分量(基础奖励/利息/连胜)由
        结算屏「获得金币总览」面板公示,当前读链未消费 = 已申报读缺口。
        收口语义:差值落 ``boundary_income_credited`` 台账行留证(金额
        可审计,豁免 ≠ 消失同纪律),覆盖照常 = 真值入账;等值观察零
        新信息不产行。
        边界:仅限结算屏覆盖写端(:func:`apply_settlement_cover`)调用;
        其余画面/字段的失配仍走 observe 三分流照真失配停。
        """
        _validate_sig(sig, ('obs',))
        name = self._field_name(target)
        if target.source == 'logic' and target.value is not None \
                and target.value != value:
            _emit_defect(field_name=name, expected=target.value,
                         actual=value, evidence=None, sig=sig,
                         logic_evidence=target.evidence,
                         kind='boundary_income_credited')
            log.info(f'[cw][gs] 结算真值收口:gold 逻辑 {target.value} → '
                     f'结算屏 {value}(+{int(value) - int(target.value)},'
                     f'边界收入随结算入账,boundary_income_credited 留证)')
        self._swap(name, Field(value=value, source='observation',
                               evidence=None), sig=sig)

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
        随机效果口径走 :meth:`write_logic_rand`(逻辑随机态,失配预期内),
        确定面仍走本口。

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
        self._write_logic_frame(target, value, source='logic',
                                produced_by=produced_by, evidence=evidence,
                                sig=sig, note=note)

    def write_logic_rand(self, target: Field, value: Any, *,
                         produced_by: str, evidence: str | None = None,
                         sig: ChannelSig,
                         note: str = '') -> None:
        """逻辑随机直写(逻辑随机态标准写通道):**效果随机的动作采样链**
        写入字段(source=logic_rand),策略器立即可读。

        值语义 = **一个可能世界的快照**,三形态(不承诺真值):

        - 采样值:上报函数真掷随机后按采样结果走完整确定性链(如晶矿
          掉落角色 → 落位 → 3合1连锁)——实机上采样是猜测,sim 里采样
          即世界真值(同一上报函数两副面孔);
        - 未变标记:未抽中类型的域值原样、仅翻来源——实机不知道真奖励
          是哪种,凡可能被本动作随机效果改动的域都要标;
        - 确定外壳:确定部分照算、随机细节兜底的形态。

        与 :meth:`write_logic` 的两条语义分界:

        - 观察覆盖差异 = 随机效果落地,**预期内非 bug**——只落
          ``logic_rand_outcome`` 台账行留证(无告警无停机),不进失配
          三分流(差异出 :meth:`observe`);
        - 策略器消费前必须重观察(查询口 = :meth:`logic_rand_fields`;
          消费门先例 = hp 可信位 ``cw_hp_policy.hp_readable`` 只认
          observation/carried,logic_rand 自然落入不可信侧)。

        污染传递:采样链上全部写入标随机态(含终值受随机分支影响的
        联动写,如晶矿摘除);跨动作由上报入口判定(:meth:`any_logic_rand`)
        继承。边界:gold 结算屏真值收口(:meth:`settle_truth`)不经
        随机面,logic_rand gold 与结算真值的差不落 boundary_income 行。
        其余契约(produced_by/evidence/sig/note、域级跳写、行域 board
        派生挂钩继承随机态)与 write_logic 同一条。
        """
        _validate_sig(sig, ('logic_action', 'logic_hook'))
        self._write_logic_frame(target, value, source='logic_rand',
                                produced_by=produced_by, evidence=evidence,
                                sig=sig, note=note)

    def _write_logic_frame(self, target: Field, value: Any, *,
                           source: FieldSource, produced_by: str,
                           evidence: str | None,
                           sig: ChannelSig, note: str) -> None:
        """逻辑族落帧共用体(write_logic/write_logic_rand 单一实现;
        source 由调用方定,family 校验已在其各自入口完成)。

        - 行域写旧值快照必须在换帧前取(§2.4 禁就地改);
        - board 派生重算单一源(行域写后自动触发;羁绊/阵营计数 = 上阵
          单位集合的派生量,独立手写 board = 越格,见方法注)。派生写
          **继承行域写入来源**:行域随机态时 board 派生行同标随机态
          (行域真值形态随采样奖励而变,board 为其派生,污染沿派生链
          传递);行域确定 logic 时 board 仍 logic。"""
        name = self._field_name(target)
        old_row_value = target.value if name in ('front_row', 'back_row') \
            else None
        self._swap(name, Field(value=value, source=source, evidence=evidence),
                   sig=sig, note=note)
        if name in ('front_row', 'back_row'):
            self._resync_board_delta(name, old_row_value,
                                     produced_by=produced_by, sig=sig,
                                     rand=(source == 'logic_rand'))

    def relay(self, target: Field, value: Any,
              sig: ChannelSig) -> bool:
        """载体中继(§2.1,**不设专用中继来源类**——中继复用 logic 来源)。

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
        """全部 logic 来源字段名(已直写、尚未被观察重锚——对账巡检用,§8.4)。
        逻辑随机态字段不辖(随机口径非严格推算承诺,不进对账巡检面;
        查询口 = :meth:`logic_rand_fields`)。"""
        return [f.name for f in dataclasses.fields(self)
                if isinstance(getattr(self, f.name), Field)
                and getattr(self, f.name).source == 'logic']

    def logic_rand_fields(self) -> list[str]:
        """全部 logic_rand 来源字段名(逻辑随机态,效果随机待重观察——
        策略消费门用):决策消费这些字段的值前必须安排重观察(值是随机
        口径不是真值,见 :meth:`write_logic_rand` 注)。被观察覆盖后
        字段翻 observation,自然移出本清单。"""
        return [f.name for f in dataclasses.fields(self)
                if isinstance(getattr(self, f.name), Field)
                and getattr(self, f.name).source == 'logic_rand']

    def any_logic_rand(self, field_names: list[str]) -> bool:
        """任一名字段现来源为 logic_rand(**跨动作污染判定入口**):动作
        上报入口检查「本次要读的输入域中是否有随机态」→ 有则本动作
        全部产出标随机态(采样世界的下游计算同为可能世界,污染沿动作
        链传递直到观察收口)。field_names = 容器 Field 字段名子集;
        未在册名字跳过(容错,不炸)。"""
        for n in field_names:
            f = getattr(self, n, None)
            if isinstance(f, Field) and f.source == 'logic_rand':
                return True
        return False

    def observe_screen_context(self, screen_name: str, *,
                               phase_round: tuple[int, int] | None = None,
                               resumed: bool = False,
                               top_raw: str | None = None,
                               sig: ChannelSig | None = None) -> None:
        """画面上下域写入 + 节点推进派生(R1 §3.1.4/§3.4;观察汇聚模块唯一
        写点,生产接线 = read_game_state 漏斗,随分派
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
        elif screen_name == SCREEN_SHOP_PANEL:
            # 规则四②·商店查现行链(链观察落地批):商店对任意节点类型
            # 都开(非专属,不入直定映射)→ 类型查现行链——链在位 = 直定写
            # (actor 同族),链缺/位越界/未辨 = 零写(禁猜,链正本 §6 零
            # 内建回落)。目标节点 = 生效序与观察镜像的最新者(店开帧可在
            # 推进腿未计数的新节点上,镜像已由读链写新序键——目标只取
            # hist 会把类型回写上一节点,run_20260918_074040 第 11 例病理;
            # 仿 :func:`_derive_node_plane_transition` 位面反解式)。
            _shop_target = _shop_panel_type_target(self)
            if _shop_target is not None:
                _shop_plane = (_shop_target - 1) // 9 + 1
                _shop_round = (_shop_target - 1) % 9 + 1
                _chain_q = chain_node_type(self, _shop_plane, _shop_round)
                if _chain_q.token is not None:
                    _write_derived_node_type(
                        self, _chain_q.token, target_ord=_shop_target,
                        actor='derive_node_type',
                        trigger_screen=screen_name, seq=seq)
        # —— 效果推进段(迁移迭代 design §2.1;管线尾段同临界区)。prep_frame 闸
        # = 备战帧:金结算仅备战帧触发,0q/0p/弹窗推进帧递延(攻击 F1 错窗防护;
        # 补给节点无备战帧,其轮首收入由下一备战帧观察直接捕获,用户裁定)。
        tick_effect_boundary(self, prep_frame=(screen_name == SCREEN_PREP_FRAME))

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

def _derive_write(gs: GameState, target: Field, value: int | NodeKey, *,
                  actor: str, trigger_screen: str, seq: int,
                  note: str = '') -> None:
    """派生规则写入(逻辑层统一形态):签名 family=logic_hook、
    actor=规则登记名、screen=关联画面、组 id = 'hook:<登记名>@<seq>'。
    value = 序值(int,node_ord 逻辑层)或节点键(NodeKey,
    类型派生经节点域写 node.kind,§3.1.3 节点域③格)。"""
    sig = ChannelSig(family='logic_hook', actor=actor, screen=trigger_screen,
                     mode='compute', group_id=f'hook:{actor}@{seq}')
    gs.write_logic(target, value, produced_by=actor, sig=sig, note=note)


def effective_node_ord(gs: GameState) -> int | None:
    """生效序读口(派生计算,非存储字段;判定基准读口,非决策消费切换目标
    ——「node 逻辑态改读派生域」M4 工作项已作废:决策面现读容器 gs.node 镜像
    合规,无切换义务,ADR-0630 修订节 2/正本消费面申报)
    = max(node_ord 字段现值, node_hist_ord)——单字段双值结构(ADR-0630 修订
    节 2):字段现值 = 最近一次派生写入(四腿全逻辑层 write_logic),hist =
    run 内已见最大值(跃迁去重键 ``(run_id, effective_ord)`` 载体);两者之
    差仅存在于纠偏写序中间态,取 max 即生效语义,None 安全(双空 = 未定);
    消费面恒逻辑层,观察层(top_bar_raw)不参与序比较。"""
    vals = [v for v in (gs.node_ord.value, gs.node_hist_ord)
            if v is not None]
    return max(vals) if vals else None


def _obs_node_ordinal(gs: GameState) -> int | None:
    """node 观察镜像的节点序(派生计算:镜像 NodeKey (plane, round) 正解
    序;镜像空 = None)。镜像由读链在非备战帧也写(店开帧 votes 读),
    可领先推进水位——它是「当前节点」的观察权威源。"""
    cur = gs.node.value
    if cur is None:
        return None
    return node_ordinal_of(cur.plane, cur.round_num)


def _shop_panel_type_target(gs: GameState) -> int | None:
    """商店查链类型派生的目标节点序 = 生效序与观察镜像的最新者
    (双源全空 = 目标不可知,禁猜零写)。

    为什么不单取 hist:店开帧读链可把镜像写到推进腿尚未计数的新序键
    (备战帧未过,弹窗腿/备战腿都未触发),目标只取 hist 会把类型直定
    回写上一节点——后续备战帧真读新节点与被回写的 logic 值类型失配,
    统一观察对账安灯照停(run_20260918_074040 未投影族第 11 例病理)。
    取 max = 「当前节点」语义;弹窗腿先推进的形态下 max 仍取推进值,
    行为与旧 hist 单源一致。"""
    ords = [v for v in (effective_node_ord(gs), _obs_node_ordinal(gs))
            if v is not None]
    return max(ords) if ords else None


def _derive_node_observed(gs: GameState, candidate: int, *,
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
    hist = gs.node_hist_ord
    if hist is not None and candidate < hist:
        # v3.2-G10 倒退留证:零状态变更,占版本(obs_event 行型 2)
        gs.note_obs_event(
            'arbitrate', 'node_ord',
            {'candidate': candidate, 'hist': hist},
            verdict='倒退读数丢弃留证(R3 规则三倒退免疫;候选 < hist 不写字段)',
            sig=ChannelSig(family='obs', actor='derive_node_observed',
                           screen=trigger_screen, mode='read',
                           group_id=f'hook:derive_node_observed@{seq}'))
        return   # 倒退读数:不写字段(R3 规则三倒退免疫)
    _derive_write(gs, gs.node_ord, candidate,
                  actor='derive_node_observed',
                  trigger_screen=trigger_screen, seq=seq)
    if hist is None or candidate > hist:
        gs.node_hist_ord = candidate   # 去重键占位:同序恰一次推进(v3.1-N2)


def _derive_node_inferred(gs: GameState, *, prev_screen: str,
                          trigger_screen: str,
                          phase_round: tuple[int, int] | None,
                          resumed: bool, seq: int) -> None:
    """弹窗腿·逻辑层(§3.4.1 规则一,本体照搬判定方案 R3 规则二/三):
    上画面 ∈ 前驱守卫族 ∧ 当前 ∈ 弹窗族 → ``write_logic(node_ord)`` 推进 +1
    (首局无前值且非恢复局 → 1)。

    - 守卫族 = :data:`SCREEN_CONTEXT_GUARD_PREV`(中性名,语义 = 「本节点
      备战帧未被分派过」= 结算窗 ∪ 开局链,成员终版 0p/0q 出族——专用腿
      ②③,用户终裁 2026-09-11,ADR-0630 修订节·守卫族终版);弹窗族 =
      :data:`SCREEN_CONTEXT_POPUP_FAMILY`;
    - 缓存守卫(R3 规则二③本体):弹窗帧无进度屏显,顶栏读数 = 缓存 c——
      要求 c == hist 才推断 +1;c 缺位或 ≠ hist → 零触发交腿 A 兜底;
    - 恢复局禁用(R3 规则六):hist 空 ∧ resumed → 不猜;
    - 推进去重(v3.1-N2):候选 ≤ hist 不写不锚(重入拒绝;去重键 =
      (run_id, effective_ord) 已占,同序恰一次推进)。
    """
    hist = gs.node_hist_ord
    effective = effective_node_ord(gs)
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
    _derive_write(gs, gs.node_ord, candidate,
                  actor='derive_node_inferred',
                  trigger_screen=trigger_screen, seq=seq)
    if hist is None or candidate > hist:
        gs.node_hist_ord = candidate   # 去重键占位(同序恰一次推进)


def _node_key_for_ord(ordinal: int, kind: str) -> NodeKey:
    """节点序 → 节点键(坐标系公式反解,§3.4.1 v3.2-G9:ord=(plane-1)*9+round
    基 1;反解与正解同式自洽,位面切换 9→10 连续)。类型派生定位目标节点用
    ——派生域只持单序,类型落 node.kind 需 (plane, round) 键。"""
    return NodeKey(plane=(ordinal - 1) // 9 + 1,
                   round_num=(ordinal - 1) % 9 + 1,
                   kind=kind)


def tick_effect_boundary(gs: GameState, *, prep_frame: bool) -> None:
    """效果推进段(迁移迭代 changes/2026-09-15-effect-ledger-self-advance
    design §2.1 a-f;接线位 = :meth:`observe_screen_context` 尾段,本函数
    独立可调供直测/sim)。

    - 推进闸:effective None → 整段跳过(「未观察不当真进节点」守卫,禁虚耗
      余期/虚累余额);
    - 账本推进(内置去重兜底同序幂等)→ 到期留证 → 刷新发放(advanced 位闸)
      → 容量重锚;
    - 经济参数 = 容器直读 active_strategies(空/None → 聚合缺省);
    - 异常边界:吞 Exception 记 warning 不上抛(不毒化派生链)。
    """
    try:
        _tick_effect_boundary_impl(gs, prep_frame=prep_frame)
    except Exception as e:   # noqa: BLE001  best-effort 不毒化派生链
        log.warning(f'[cw][effect] 效果推进段失败(不阻塞): {e}')


def _tick_effect_boundary_impl(gs: GameState, *, prep_frame: bool) -> None:
    effective = effective_node_ord(gs)
    if effective is None:
        return
    frame = f'p{(effective - 1) // 9 + 1}-r{(effective - 1) % 9 + 1}'
    advanced, expired = gs.effects.advance_node(effective)
    for _eff in expired:
        log.warning('[cw!][effect] 效果到期移除:%s(尾款触发面;金面走观察覆盖兜底)',
                    _eff.spec.name)
    if advanced:
        grant_effect_node_refresh_balance(gs, frame=frame)
    project_effect_capacity(gs)


def _write_derived_node_type(gs: GameState, kind: str, *, target_ord: int,
                             actor: str, trigger_screen: str, seq: int) -> None:
    """类型派生写入(§3.4.1 类型派生;经节点域③格写 gs.node,§3.1.3):
    专属画面直定该节点类型,(plane, round) 由目标序公式反解。

    - 倒退免疫(R3 规则三同簇,20260918-reconcile 第 11 例收口):镜像
      现值序 > 目标序 = 镜像比派生目标鲜活(读链已在店开帧写新节点),
      直定旧节点会把新节点回写旧键 → 丢弃留证不写(obs_event
      arbitrate),类型由镜像源(读链 votes/后继帧)承接;
    - 冲突纪律(G10 同簇):镜像现值已在目标节点且类型不一致 → obs_event
      留证(event='arbitrate',禁静默覆盖)+ 最新直定值落位(最新观察 =
      真相);直定证据 = 画面现身锚,属观察级事实,sig 走 obs 族
      (note_obs_event 契约),actor = 触发规则登记名保留归因;
    - 已知边界(申报):弹窗族屏重入/缓存滞后形态下目标 = hist,若历史
      推进与屏所属节点错位,倒退免疫丢弃留证(不落错键);目标序 ≥ 镜像
      序的错位形态(弹窗屏属下一节点)类型照落,后续备战帧真读类型经
      观察覆盖核对(§2.3 观察赢)——真失配才走三分流;
    - 商店面板块不专属 → 不入直定映射(observe_screen_context 分流),
      类型「未定型」零写;查现行链接口 = :func:`chain_node_type`。
    """
    key = _node_key_for_ord(target_ord, kind)
    cur = gs.node.value
    if cur is not None and node_ordinal_of(cur.plane, cur.round_num) > target_ord:
        gs.note_obs_event(
            'arbitrate', 'node',
            {'mirror': f'{cur.plane}-{cur.round_num}-{cur.kind}',
             'target_ord': target_ord, 'target_kind': kind},
            verdict='类型直定倒退丢弃留证(R3 规则三倒退免疫;镜像序 > '
                    '目标序,不回写旧节点)',
            sig=ChannelSig(family='obs', actor=actor, screen=trigger_screen,
                           mode='read',
                           group_id=f'hook:{actor}@{seq}'))
        return
    if cur is not None and cur.plane == key.plane \
            and cur.round_num == key.round_num and cur.kind != kind:
        gs.note_obs_event(
            'arbitrate', 'node',
            {'old_kind': cur.kind, 'new_kind': kind, 'node_ord': target_ord},
            verdict='类型直定冲突留证(同节点两直定值不一致,最新直定赢)',
            sig=ChannelSig(family='obs', actor=actor, screen=trigger_screen,
                           mode='read',
                           group_id=f'hook:{actor}@{seq}'))
    _derive_write(gs, gs.node, key, actor=actor,
                  trigger_screen=trigger_screen, seq=seq)


def _derive_node_plane_transition(gs: GameState, *,
                                  phase_round: tuple[int, int] | None,
                                  seq: int) -> None:
    """位面过渡腿(§3.4.1 规则二·R1.2;actor=derive_node_plane_transition):
    0q 被采到 → 逻辑节点 = (当前位面+1, 1),经节点序坐标系公式落单整数
    写入 ``node_ord``(逻辑层)。

    - 「当前位面」来源优先级:①调用方顶栏读数 phase_round(测试/未来漏斗
      直读形态;生产 cw_loop 分支写点不带)②gs.node 观察镜像 plane(顶栏
      权威链遗产)③hist 反解((hist-1)//9+1)——三源全缺 = 「当前位面」
      不可知(开局过渡屏形态),禁猜不写,交规则①④计数;
    - 共同语义:候选 ≤ hist 不写不锚(重复 0q loop pass 重入拒绝,去重键
      =(run_id, effective_ord) 已占,同序恰一次推进);
    - 零类型写:过渡屏链 = 离开位面链(件 B v1.1 §3.1.1 F1 定谳),下位面
      节点类型不可自定——新节点类型由后继专属屏/备战帧链读链承接。
    """
    hist = gs.node_hist_ord
    plane: int | None = None
    if phase_round is not None:
        plane = int(phase_round[0])
    elif gs.node.value is not None:
        plane = int(gs.node.value.plane)
    elif hist is not None:
        plane = (hist - 1) // 9 + 1
    if plane is None or plane < 1:
        return   # 当前位面不可知:禁猜(R3 禁猜纪律;开局过渡屏交①④计数)
    candidate = plane * 9 + 1        # (plane+1, 1) = (plane+1-1)*9+1
    if hist is not None and candidate <= hist:
        return   # 重入拒绝(v3.1-N2:候选 ≤ hist 不写不锚,去重键已占)
    _derive_write(gs, gs.node_ord, candidate,
                  actor='derive_node_plane_transition',
                  trigger_screen=SCREEN_PLANE_TRANSITION, seq=seq)
    gs.node_hist_ord = candidate     # 去重键占位(同序恰一次推进)


def _derive_node_boss_brief(gs: GameState, *, seq: int) -> int | None:
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
    hist = gs.node_hist_ord
    effective = effective_node_ord(gs)
    if effective is None:
        return None   # 当前节点未知:禁猜
    cur = gs.node.value
    if cur is not None and cur.kind == 'boss' \
            and node_ordinal_of(cur.plane, cur.round_num) == hist:
        return hist   # 幂等锚命中:本简报节点已计数,零写(防重推)
    candidate = effective + 1
    if hist is not None and candidate <= hist:
        return hist   # 去重键已占(先行腿已推进):boss 节点 = hist
    _derive_write(gs, gs.node_ord, candidate,
                  actor='derive_node_boss_brief',
                  trigger_screen=SCREEN_BOSS_BRIEFING, seq=seq)
    gs.node_hist_ord = candidate     # 去重键占位(同序恰一次推进)
    _write_derived_node_type(gs, 'boss', target_ord=candidate,
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


def chain_node_type(gs: GameState, plane: int, round_num: int) -> ChainQuery:
    """现行链节点类型查询(链正本 = game_state/chain-observation.md §6;
    只读,零读屏零 OCR,查询面 = ``node_path`` 现行链帧事实字段)。

    - 载体 = :class:`NodeChain`(链观察落地批 2026-09-16 起;list[str] 旧形
      为 journal 只读历史档,读面不认)——链未写/位面不匹配/位越界/该格
      token None → None(诚实缺位;**零内建回落**禁把基线/台账当兜底);
    - 链在位时位寻址 = seq[i] 第 i+1 轮(round 基 1);位越界/链跨位面错配
      = None。基线/改写位两接口(chain_baseline/chain_rewritten)仍归后续
      批,本口不预纳;
    - 消费方 = 节点域类型派生规则四②「商店查现行链」(商店面板块未定型
      时的类型来源;消费侧执行兜底序与改写位禁令)。
    """
    chain = gs.node_path.value
    if not isinstance(chain, NodeChain):
        return ChainQuery(token=None)
    if int(chain.plane) != int(plane):
        return ChainQuery(token=None)
    idx = int(round_num) - 1
    if idx < 0 or idx >= len(chain.seq):
        return ChainQuery(token=None)
    cell = chain.seq[idx]
    token = str(cell.token) if cell is not None and cell.token else None
    return ChainQuery(token=token)


#: 仅标签通道 token 集(链正本 §4 通道受限差判定:基线通道 hu、现行通道
#: label 且现行 token ∈ 本集 = 两写端识别能力集不同,非环境改写)。
_LABEL_ONLY_TOKENS: frozenset[str] = frozenset({'elite', 'megastar', 'invest'})


@dataclass(frozen=True)
class ChainDiff:
    """基线链 vs 现行链的结构差异(链正本 §4;数学单一源,实机与 sim 共用)。

    rewrites = 改写位集(双 token 非 None 且不等,且差非通道受限);
    channel_limited = 通道受限差位集(基线 hu、现行 label 且现行 token ∈
    仅标签集——识别能力集差异,非改写);length_changed = 链长差(环境/
    策略增删节点);first_diff_pos = 首个 token 差异位(0 基;无 = None);
    baseline_coverage = 基线 None 洞位集(基线首写帧未辨位,保「基线 =
    入口快照」时间语义)。
    """

    rewrites: tuple[int, ...]
    channel_limited: tuple[int, ...]
    length_changed: bool
    first_diff_pos: int | None
    baseline_coverage: tuple[int, ...]


def chain_diff(baseline: NodeChain, current: NodeChain) -> ChainDiff:
    """基线链 vs 现行链结构差异(纯函数,实机与 sim 共用;链正本 §4)。"""
    rewrites: list[int] = []
    limited: list[int] = []
    coverage: list[int] = []
    first: int | None = None
    n = max(len(baseline.seq), len(current.seq))
    for i in range(n):
        in_b = i < len(baseline.seq)
        b = baseline.seq[i] if in_b else None
        c = current.seq[i] if i < len(current.seq) else None
        bt = b.token if b is not None else None
        ct = c.token if c is not None else None
        if in_b and bt is None:
            coverage.append(i)
        if bt is not None and ct is not None and bt != ct:
            if first is None:
                first = i
            if b.channel == 'hu' and c.channel == 'label' \
                    and ct in _LABEL_ONLY_TOKENS:
                limited.append(i)
            else:
                rewrites.append(i)
    return ChainDiff(rewrites=tuple(rewrites), channel_limited=tuple(limited),
                     length_changed=len(baseline.seq) != len(current.seq),
                     first_diff_pos=first,
                     baseline_coverage=tuple(coverage))


def _chain_cells_payload(chain: NodeChain) -> list[dict]:
    """链载荷序列化(逐格 token/channel/hu_dist;diff 行内嵌用)。"""
    return [{'token': c.token, 'channel': c.channel, 'hu_dist': c.hu_dist}
            for c in chain.seq]


def maybe_emit_chain_diff(gs: GameState, *, snapshot: bool,
                          in_mutation_window: bool,
                          sig: ChannelSig) -> bool:
    """链 diff 触发面(链正本 §4/§5):基线在场 ∧ 差异非空才评估。

    触发纪律:备战帧触发须连续两个 clean 帧读数一致才落行(待确认候选 =
    ``node_path_diff_pending``,单帧翻转不产行);离场快照豁免两帧门;
    变异窗内豁免并清候选(窗关后按两帧确认补比对)。发射 = note_obs_event
    'chain_diff'(verdict 留空——改写身份归因 = 消费侧 join
    active_env/active_strategies 同帧快照,链正本 §5,观察层不猜);
    journal sink 缺省关 = 零副作用。返回是否落行。
    """
    baseline = gs.node_path_baseline.value
    current = gs.node_path.value
    if baseline is None or current is None:
        return False
    diff = chain_diff(baseline, current)
    if not (diff.rewrites or diff.channel_limited or diff.length_changed):
        gs.node_path_diff_pending = None
        return False
    if in_mutation_window:
        gs.node_path_diff_pending = None
        return False
    if not snapshot:
        if gs.node_path_diff_pending != current:
            gs.node_path_diff_pending = current   # 首见候选,等下帧确认
            return False
        gs.node_path_diff_pending = None   # 连续两帧一致 → 落行

    payload = {
        'baseline': {'plane': baseline.plane,
                     'seq': _chain_cells_payload(baseline)},
        'current': {'plane': current.plane,
                    'seq': _chain_cells_payload(current)},
        'rewrites': list(diff.rewrites),
        'channel_limited': list(diff.channel_limited),
        'length_changed': diff.length_changed,
        'first_diff_pos': diff.first_diff_pos,
        'baseline_coverage': list(diff.baseline_coverage),
        'snapshot': snapshot,
    }
    gs.note_obs_event('chain_diff', 'node_path', payload, verdict='',
                      sig=sig)
    return True


# ============================================================ sim 合成口


def synthesize_from_game_state(gs: GameState, st: CwSimFrame, *,
                               at_round: str = '',
                               shop_empty_off_screen: bool = True,
                               shop_open: bool = False) -> None:
    """CwSimFrame 真值 → 容器域写入(帧→容器合成口的写入实现)。

    生产 sim 引擎已直写容器(引擎内部工作态即容器,渠道签名写入口),不再
    经本口喂入;经 :func:`feed_sim_truth` 调本函数与直接调用现役 = 离线/
    测试构造面(识别域调用方传 ``shop_empty_off_screen=False``,理由见下方
    payload 域分支)。原「sim 合成口」域覆盖口径不变:

    - sim 无识别过程 = 恒真值帧:可读字段全记 observation,evidence 恒带
      ``sim:synthesized``(at_round 非空时并入轮键后缀
      ``sim:synthesized@p{plane}-r{round}``,供遥测定位合成时点——P2-6
      落地审:参数必有消费);真值 None/未建模域不写(保持 None,禁合成假值);
    - **bench 槽位保序映射**(§3.2.5 任务书件 7):CwSimFrame.bench 的
      0 基下标 1:1 映射物理槽位(BenchChar → kind='unit',None → 'empty'),
      记录模型按实机真值箱占席——sim「无箱实体」只是内部口径约定,
      不进记录模型(占席谓词 = :func:`slot_occupies`,箱/秘典占席);
    - at_round = 轮键('p{plane}-r{round}' 形,登记期快照);
    - **payload 域离屏分支**(§2.2 例外):shop 真值缺席 = 结构离屏(置
      None+left_screen,等价 leave_screen);encounter/supply 两域 sim 不建模,
      恒离屏口径——三 payload 域在合成帧恒反映「当前画面事实」,禁旧
      payload 连旧 evidence 残留。**空表与 None 同判 = 离屏**只辖 sim 真值域
      (``shop_empty_off_screen=True`` 缺省):sim 真值域无 OCR 失读态,
      CwSimFrame.shop 空表 = 「不在商店」的真值形态(开店帧恒有五张)。
      实机识别域(``shop_empty_off_screen=False``,店开相位喂入)同形空表 =
      买空/OCR 失读窗,画面结构仍在店(画面锚 = 外循环 0n 三 id_mark,
      phase=PHASE_PREP_SHOP_OPEN)——照 live 观察漏斗口径「空牌面不写、
      保现值」(失读窗沿用,决策侧照旧决策、执行侧核对兜底),**禁按离屏
      清 None**(2026-09-13 实机事故:买空店重进被真值口径清 None,
      ``decide_shop_action`` 在屏前置 shop=None 契约崩循环,journal 铁证 =
      current_screen 开商店同帧 prov.shop evidence=left_screen)。
    """
    _ev = f'{SIM_SYNTHESIZED}@{at_round}' if at_round else SIM_SYNTHESIZED
    # sim 合成签名(R1 §3.2.1:obs 族子模 mode='synthesized'——sim 真值合成
    # 与实机真读可分;actor = 本口登记名,质量语义与 evidence 标记同源)
    _synth_sig = ChannelSig(family='obs', actor='synthesize_from_game_state',
                            mode='synthesized')
    # node_type None(裸 CwSimFrame 未建模该帧)不写 node——禁 'prep' 占位
    # 假值(P1-1 同型泛化;engine 路径 node_type 恒引擎真值不受影响)
    _node_type = getattr(st, 'node_type', None)
    if _node_type is not None:
        gs.observe(gs.node,
                   NodeKey(plane=int(getattr(st, 'plane', 1) or 1),
                           round_num=int(getattr(st, 'round_num', 1) or 1),
                           kind=str(_node_type)),
                   evidence=_ev, sig=_synth_sig)
    else:
        _prev_node = gs.node.value
        if _prev_node is not None:
            gs.observe(gs.node,
                       NodeKey(plane=int(getattr(st, 'plane', 1) or 1),
                               round_num=int(getattr(st, 'round_num', 1) or 1),
                               kind=_prev_node.kind),
                       evidence='kind_inherited', sig=_synth_sig)
        # 无现值且未读:node 不写,保持 None(诚实缺位)
    if getattr(st, 'gold_readable', True) and st.gold is not None:
        gs.observe(gs.gold, int(st.gold), evidence=_ev, sig=_synth_sig)
    if getattr(st, 'level_readable', True):
        gs.observe(gs.level, int(st.level), evidence=_ev, sig=_synth_sig)
    if st.xp_progress is not None:
        gs.observe(gs.xp, tuple(st.xp_progress), evidence=_ev, sig=_synth_sig)
    if st.streak is not None:
        gs.observe(gs.streak, int(st.streak), evidence=_ev, sig=_synth_sig)
    if st.hp is not None:
        gs.observe(gs.hp, int(st.hp), evidence=_ev, sig=_synth_sig)
    # deploy_cap(§2.3 W5 入容器):sim 真值直写;None(未建模帧)不写。
    if st.deploy_cap is not None:
        gs.observe(gs.deploy_cap, int(st.deploy_cap), evidence=_ev,
                   sig=_synth_sig)
    # back_layout(back_max 语义裁决·闸门二,sim 合成口扩员——W5 §2.6
    # 清单增补第八域,与实机喂入口域覆盖集对齐):sim 真值直写(动态真值
    # = CwSimFrame.back_max,场景侧设定;实机写端 = 选档裁决链,两写端
    # 同域不同源,sim 无识别过程故恒真值);缺席不写(禁合成假值,同
    # 七域纪律)。
    if st.back_max is not None:
        gs.observe(gs.back_layout, int(st.back_max), evidence=_ev,
                   sig=_synth_sig)
    # 开局域/席位/装备(W5 合成口与实机喂入口域覆盖集对齐;§2.6):
    # sim 无识别过程,真值域恒 observation + evidence=sim:synthesized。
    if st.plane_bosses:
        gs.observe(gs.plane_bosses, list(st.plane_bosses), evidence=_ev,
                   sig=_synth_sig)
    if st.enemy_affixes:
        gs.observe(gs.enemy_affixes, list(st.enemy_affixes), evidence=_ev,
                   sig=_synth_sig)
    if st.active_env:
        gs.observe(gs.active_env, str(st.active_env), evidence=_ev,
                   sig=_synth_sig)
    if st.equips:
        gs.observe(gs.equips, list(st.equips), evidence=_ev, sig=_synth_sig)
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
        gs.observe(gs.front_row, _front_u, evidence=_ev, sig=_synth_sig)
        gs.observe(gs.back_row, _back_u, evidence=_ev, sig=_synth_sig)
    # bench 写门(对齐上方 board_readable 先例):未读域≠真空域。v1 漏斗
    # (read_game_state)不读 bench 身份,其帧 bench 恒默认空表——无门合成
    # 会把容器内 prep 装配环 bench 观察块(cw_screen_prep heavy 块,唯一
    # 实机漏斗写端)的真读覆盖成「9 槽全空」假真空(违 read_game_state
    # 席位通道声明的「禁拿 CwSimFrame 兜底默认值当观察」;历史事故面 =
    # 商店段入口双账对账对撞,该对账已退役,本门的防覆盖
    # 语义独立存续——真读被兜底默认值覆盖本身就是观察面破坏)。sim 真值
    # 帧恒可读(缺省 True)不受影响;真真空写路径由 sim 帧承载。
    if getattr(st, 'bench_readable', True):
        bench_slots: list[BenchSlot] = []
        for i, bc in enumerate(st.bench):
            if bc is None:
                bench_slots.append(BenchSlot(kind='empty'))
            elif bool(getattr(bc, 'is_item_slot', False)):
                # 占位件旗标往返(同 bench_view_of_slots 口径;sim 假环境经
                # 观察面直喂占位件,恒 'unit' 映射会让腾席守卫在容器面失守)
                bench_slots.append(BenchSlot(kind='supply_box'))
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
        gs.observe(gs.bench,
                   BenchView(slots=bench_slots, capacity=BENCH_CAPACITY_DEFAULT),
                   evidence=_ev, sig=_synth_sig)
    if getattr(st, 'board_readable', True) and st.board:
        gs.observe(gs.board, dict(st.board), evidence=_ev, sig=_synth_sig)
    if st.shop:
        # 牌转换 = 映射单一源(W5 双 ShopCard 归一;cost_source 原值透传
        # 不折叠,roster_fallback 的「徽章失读」证据分级禁丢)。
        # 定长槽映射:帧卡 x = 抽牌序 i = 物理槽-1,按 x 对槽(缺位 empty)——
        # 紧凑列表顺延映射会错位槽几何(用户三态裁定 2026-09-13)。
        slots: list[ShopSlot] = [ShopSlot(kind='empty') for _ in range(5)]
        for c in st.shop:
            _i = int(getattr(c, 'x', 0) or 0)
            if 0 <= _i < 5:
                slots[_i] = ShopSlot(kind='content',
                                     card=shop_card_to_container(c))
        probs = ({int(k): float(v) for k, v in st.refresh_probs.items()}
                 if st.refresh_probs else {})
        gs.observe(gs.shop, ShopPayload(cards=slots, refresh_probs=probs),
                   evidence=_ev, sig=_synth_sig)
    elif shop_open and shop_empty_off_screen:
        # 店开显式位(sim 真值域调用方声明;帧模型空表无法区分离屏/买空
        # ——正是三态定长根治的塌缩病灶,用户三态裁定 2026-09-13):
        # 买光 = [empty×5] 合法真值,店开即写,None 仅离屏。
        gs.observe(gs.shop,
                   ShopPayload(cards=[ShopSlot(kind='empty')
                                      for _ in range(5)], refresh_probs={}),
                   evidence=_ev, sig=_synth_sig)
    elif shop_empty_off_screen:
        # 画面附加域离屏分支(§2.2 显式例外):sim 真值域空表 = 「不在商店」
        # 的结构事实——非当前画面置 None(等价 leave_screen,evidence=
        # left_screen),禁沿用旧 payload 连旧 evidence(残留会把离屏帧误读
        # 成「商店仍开着」)。识别域(shop_empty_off_screen=False)不走此支:
        # 空表 = 买空/OCR 失读窗,保现值(分支语义见函数 docstring)。
        gs.leave_screen(gs.shop, sig=_synth_sig)
    # encounter/supply 两 payload 域:sim 的 CwSimFrame 不建模这两域(attr
    # 缺席 = sim 模型里结构离屏)——同口径置 left_screen,保持「三 payload
    # 域在合成帧恒反映当前画面事实」的域语义;观察真值不进合成(sim 无
    # 识别过程),禁合成假值。
    gs.leave_screen(gs.encounter, sig=_synth_sig)
    gs.leave_screen(gs.supply, sig=_synth_sig)
    if st.active_strategies:
        gs.observe(gs.active_strategies, list(st.active_strategies),
                   evidence=_ev, sig=_synth_sig)
    gs.mark_frame_obs('full')


def feed_sim_truth(gs: GameState, st: CwSimFrame, *,
                   at_round: str = '', shop_open: bool = False) -> None:
    """sim 真值直写喂入口(帧→容器合成口的正式入口包装)。

    生产写入 = **引擎直写**(sim 引擎内部工作态即 session 容器,经渠道签名
    写入口落字,消费端一律经 ``game_state_of(session)`` 直读容器——禁再造
    桥装箱一次性视图);本口的现役消费面 = 离线/测试构造(生产引擎零调用)。
    写入实现 = :func:`synthesize_from_game_state`(域覆盖/evidence/
    payload 离屏口径单一源,本口零第二实现)。

    - best-effort:记录层故障不毒化 sim(与 note_action_receipt 同纪律),
      异常 log 留痕后返回,容器保持上一拍帧;
    - sim 真值入容器唯一写端 = 本口,消费端一律 :func:`game_state_of`
      直读。
    """
    try:
        synthesize_from_game_state(gs, st, at_round=at_round,
                            shop_open=shop_open)
    except Exception as e:   # noqa: BLE001  记录层 best-effort,不毒化 sim
        log.warning('[cw-gs][feed] sim 真值直写跳过(at_round=%s): %r',
                    at_round, e)


def restore_state_snapshot(gs: GameState, snap: dict) -> None:
    """行内 state 快照 → 容器域恢复(波 5 回放/Δ池 journal 切源的
    离线判读面;序列化 = :meth:`GameState.full_state_snapshot`)。

    - 直 setattr 重建 Field(绕 _swap:零流水行、零版本分配——恢复是
      离线读面非生产写路径);values 键缺位 = 域保持 None(快照只存
      非 None 值的口径往返一致);
    - 复杂域按字段名重建(node/front_row/back_row/bench/shop/plane_bosses;
      _json_safe 无类型标,恢复表 = 字段名单一源),其余域直透
      (标量/list/dict 形态值);
    - source/evidence 取 prov 面(缺 = observation/None 缺省);
    - write_seq/工程结构不恢复(判读面不需要版本续接)。
    """
    values = snap.get('values') if isinstance(snap, dict) else None
    if not isinstance(values, dict):
        return
    prov = snap.get('prov') if isinstance(snap.get('prov'), dict) else {}

    def _unit(d: dict) -> Unit:
        return Unit(char_id=str(d.get('char_id') or ''),
                    star=int(d.get('star') or 1),
                    equips=list(d.get('equips') or []),
                    slot=int(d.get('slot') or 1))

    def _bench_view(d: dict) -> BenchView:
        slots: list[BenchSlot] = []
        for sd in d.get('slots') or []:
            sd = sd if isinstance(sd, dict) else {}
            u = sd.get('unit')
            slots.append(BenchSlot(
                kind=str(sd.get('kind') or 'empty'),
                unit=_unit(u) if isinstance(u, dict) else None))
        return BenchView(slots=slots,
                         capacity=int(d.get('capacity')
                                      or BENCH_CAPACITY_DEFAULT))

    def _shop_payload(d: dict) -> ShopPayload:
        # 三态定长(用户三态裁定 2026-09-13):cards 元素 = {kind, card}
        # 槽字典;旧扁平卡字典兼容读(过渡期快照)按 content 顺延。
        def _slot(c):
            if isinstance(c, dict) and 'kind' in c:
                cc = c.get('card')
                card = ShopCard(
                    name=str((cc or {}).get('name') or ''),
                    faction=str((cc or {}).get('faction') or '?'),
                    cost=int((cc or {}).get('cost') or 1),
                    star=int((cc or {}).get('star') or 1),
                    cost_source=str((cc or {}).get('cost_source') or ''),
                    slot=int((cc or {}).get('slot') or 0),
                ) if isinstance(cc, dict) and cc.get('name') else None
                return ShopSlot(kind=str(c.get('kind') or 'empty'),
                                card=card)
            if isinstance(c, dict) and c.get('name'):
                return ShopSlot(kind='content', card=ShopCard(
                    name=str(c.get('name') or ''),
                    faction=str(c.get('faction') or '?'),
                    cost=int(c.get('cost') or 1),
                    star=int(c.get('star') or 1),
                    cost_source=str(c.get('cost_source') or ''),
                    slot=int(c.get('slot') or 0)))
            return ShopSlot(kind='empty')

        cards = [_slot(c) for c in d.get('cards') or []
                 if isinstance(c, dict)]
        while len(cards) < 5:
            cards.append(ShopSlot(kind='empty'))
        probs = {int(k): float(v)
                 for k, v in (d.get('refresh_probs') or {}).items()}
        return ShopPayload(cards=cards, refresh_probs=probs)

    rebuild = {
        'node': lambda d: NodeKey(plane=int(d.get('plane') or 1),
                                  round_num=int(d.get('round_num') or 1),
                                  kind=str(d.get('kind') or '')),
        'front_row': lambda lst: [_unit(u) for u in lst
                                  if isinstance(u, dict)],
        'back_row': lambda lst: [_unit(u) for u in lst
                                 if isinstance(u, dict)],
        'bench': _bench_view,
        'shop': _shop_payload,
    }
    for name, raw in values.items():
        target = getattr(gs, name, None)
        if not isinstance(target, Field):
            continue
        fn = rebuild.get(name)
        try:
            value = fn(raw) if fn is not None else raw
        except (TypeError, ValueError, KeyError, AttributeError):
            continue   # 畸形域诚实跳过(宽容读契约同向)
        p = prov.get(name) if isinstance(prov.get(name), dict) else {}
        setattr(gs, name, Field(value=value,
                                source=str(p.get('source') or 'observation'),
                                evidence=p.get('evidence')))


# ============================================================ 决策面公共读口
# (迁移批次三·W6 波1:kernel 决策簇签名切 GameState 后的值读单一源。
#  旧 CwSimFrame 标量字段的缺省值形态(非 Optional:int 0/1)在容器侧是
#  None(未观察),读口负责镜像旧缺省,禁各消费点自写兜底造成第二源。)


def plane_of(gs: GameState) -> int:
    """位面读口(旧 ``CwSimFrame.plane`` 缺省 1 的镜像;未观察帧 = 引导窗)。"""
    node = gs.node.value
    return int(node.plane) if node is not None else 1


def round_num_of(gs: GameState) -> int:
    """轮次读口(旧 ``CwSimFrame.round_num`` 缺省 1 的镜像)。"""
    node = gs.node.value
    return int(node.round_num) if node is not None else 1


def node_kind_of(gs: GameState) -> str | None:
    """节点类型读口(旧 ``CwSimFrame.node_type``:None=未识别)。"""
    node = gs.node.value
    return str(node.kind) if node is not None else None


def gold_of(gs: GameState) -> int:
    """金读口(旧 ``CwSimFrame.gold`` 非 Optional 缺省 0 的镜像;可读保真位
    另经 :attr:`Field.source` 判,读口只供值)。"""
    v = gs.gold.value
    return int(v) if v is not None else 0


def level_of(gs: GameState) -> int:
    """等级读口(旧 ``CwSimFrame.level`` 非 Optional 缺省 1 的镜像)。"""
    v = gs.level.value
    return int(v) if v is not None else 1


def deployed_slots_of(gs: GameState) -> list:
    """上阵席位读口(波1 公共读口单一源):front_row/back_row(容器席位)
    → ADR-0392 定长 10 槽表(0-3 前/4-9 后,元素 BenchChar|None)。

    换算单一源 = :func:`unit_rows_to_deployed`;两行全未观察 = 旧
    ``CwSimFrame.deployed`` 缺省形态([None]×10)。
    """
    front = gs.front_row.value
    back = gs.back_row.value
    if front is None and back is None:
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            DEPLOYED_CAPACITY,
        )
        return [None] * DEPLOYED_CAPACITY
    return unit_rows_to_deployed(list(front or []), list(back or []))


def bench_slots_of(gs: GameState) -> list:
    """备战席读口(波1 公共读口单一源):BenchView → 定长 9 槽表
    (元素 BenchChar|None,下标 i = 物理槽 i+1)。换算单一源 =
    :func:`bench_slots_to_legacy`;未观察 = 旧 ``CwSimFrame.bench`` 缺省
    形态([None]×9)。"""
    view = gs.bench.value
    if view is None:
        from sr_od.application.currency_war.kernel.cw_exec_state import BENCH_CAPACITY
        return [None] * BENCH_CAPACITY
    return bench_slots_to_legacy(view)


def back_capacity_of(gs: GameState) -> int:
    """后排格数读口(旧 ``CwSimFrame.back_max`` 容器版,波3 立口):
    back_layout 真值(值域 6-9,平常 6/宝钻扩展 7/8/9,>9 域外 8 格超集);
    未观察帧退机制基线 6(与旧字段缺省同源)。

    ⚠️ 语义修正申报(W6 波3,调研草案 §4/风险 7):旧 ``CwSimFrame.back_max``
    静态 6 与实局 7/8 不符,本读口起消费面拿到动态真值——cap 封顶与
    后排容量门输出随之修正,行为差由 cap 域锁(test_cw_cap_domain/
    test_cw_cap_override_link)重推语义辖。单一源:``max_units_of`` 封顶
    域与本读口同式,禁消费面内联第二份。"""
    back = gs.back_layout.value
    return int(back) if back is not None else 6


def deployed_count_of(gs: GameState) -> int:
    """上阵占用数读口(旧 ``CwSimFrame.deployed_count`` 逐式镜像,波3 立口;
    换算单一源 = :func:`deployed_slots_of` + ``cw_state.deployed_occupied``,
    ADR-0392 占用数口径非 len)。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import deployed_occupied
    return deployed_occupied(deployed_slots_of(gs))


def front_count_of(gs: GameState) -> int:
    """前排人数读口(旧 ``CwSimFrame.front_count`` 逐式镜像,波3 立口):
    按 ``BenchChar.position_pref == 'front'`` 计(与旧法同式,非按槽段
    计——BenchChar 站位偏好与所在排可短暂不一致,镜像以旧口径为准)。"""
    return sum(1 for c in deployed_slots_of(gs)
               if c is not None and c.position_pref == 'front')


def back_count_of(gs: GameState) -> int:
    """后排人数读口(旧 ``CwSimFrame.back_count`` 逐式镜像,波3 立口;
    口径同 :func:`front_count_of`)。"""
    return sum(1 for c in deployed_slots_of(gs)
               if c is not None and c.position_pref == 'back')


def max_units_of(gs: GameState) -> int:
    """可上阵数容器版派生(波1 公共读口单一源;旧 ``CwSimFrame.max_units``
    逐式镜像):deploy_cap 真值(≥level 才采信,ADR-0286 防抖漏网兜底
    level)封顶 = 前排恒 4 + back_layout 动态真值(缺省 6 = 机制基线,
    值域 6-9,与旧 back_max 字段缺省同源;封顶域单一源 =
    :func:`back_capacity_of`)。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        DEPLOYED_FRONT_CAPACITY,
    )
    level = level_of(gs)
    cap = gs.deploy_cap.value
    base = cap if (cap is not None and cap >= level) else level
    return min(base, DEPLOYED_FRONT_CAPACITY + back_capacity_of(gs))


def scalar_projection_state(gold: int, level: int, hp: int, plane: int,
                            round_num: int,
                            strategies: list[str] | None = None) -> GameState:
    """无 session 标量投影容器(一次性视图)。

    服务「只有标量、无 session/无现成容器」的调用面。现役唯一消费 =
    ``cw_economy.get_node_goal`` 全参支。语义契约:

    - **ADR-0598 结构性豁免不扩修**:投影判据链以 session=None 求值 →
      息帽 resolved 链恒 base 口径、节点日程走缺表回退先验——契约不变,
      扩修挂该调用面的 session 通道批;
    - **字段契约自辖于本 docstring**:
      node = NodeKey(plane, round_num, kind='')(帧未
      识别的忠实镜像,禁写词表值冒充真值);gold/level/hp 观察直写;
      back_layout = 机制基线 6(旧帧 back_max 缺省);bench = 全空视图
      (旧帧 pad 缺省);shop/encounter/supply = 离屏;shop_refresh_cost =
      刷新基价(旧帧字段缺省,单一源 = cw_economy.REFRESH_COST_BASE);
      active_strategies 非空才写;xp/streak/deploy_cap/board/plane_bosses/
      enemy_affixes/active_env/equips/level_up_cost/selected_difficulty =
      不写(保持 None);
    - 一次性视图禁向状态流水落行(行 = 改了什么的局内账,投影非局内
      事实;与桥同款:单线程写路径,沉挂全局 sink 后还原);
    - actor 复用 sim 合成签名登记名(已在 REGISTERED_ACTORS 在册,投影
      行为语义与合成口同族,零新登记面)。
    """
    gs = GameState(schema_version=GAME_STATE_SCHEMA_VERSION)
    global _STATE_JOURNAL_SINK
    _saved_sink = _STATE_JOURNAL_SINK
    _STATE_JOURNAL_SINK = None
    try:
        _ev = SIM_SYNTHESIZED
        _sig = ChannelSig(family='obs', actor='synthesize_from_game_state',
                          mode='synthesized')
        gs.observe(gs.node,
                   NodeKey(plane=int(plane), round_num=int(round_num),
                           kind=''),
                   evidence=_ev, sig=_sig)
        gs.observe(gs.gold, int(gold), evidence=_ev, sig=_sig)
        gs.observe(gs.level, int(level), evidence=_ev, sig=_sig)
        gs.observe(gs.hp, int(hp), evidence=_ev, sig=_sig)
        gs.observe(gs.back_layout, 6, evidence=_ev, sig=_sig)
        gs.observe(gs.bench,
                   BenchView(slots=[BenchSlot(kind='empty')]
                             * BENCH_CAPACITY_DEFAULT,
                             capacity=BENCH_CAPACITY_DEFAULT),
                   evidence=_ev, sig=_sig)
        gs.leave_screen(gs.shop, sig=_sig)
        gs.leave_screen(gs.encounter, sig=_sig)
        gs.leave_screen(gs.supply, sig=_sig)
        if strategies:
            gs.observe(gs.active_strategies, list(strategies),
                       evidence=_ev, sig=_sig)
        from sr_od.application.currency_war.kernel.cw_economy import (
            REFRESH_COST_BASE,
        )
        gs.observe(gs.shop_refresh_cost, int(REFRESH_COST_BASE),
                   evidence=_ev, sig=_sig)
        gs.mark_frame_obs('full')
    finally:
        _STATE_JOURNAL_SINK = _saved_sink
    return gs


