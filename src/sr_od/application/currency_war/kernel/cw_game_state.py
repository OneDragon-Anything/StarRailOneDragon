"""货币战争 GameState 局内记录(迁移批次一骨架)。

**正本入口** = ``docs/develop/sr_od/application/currency_war/game_state/README.md``(总纲);
**字段级规格正本** = ``docs/develop/sr_od/application/currency_war/game_state/fields.md``
(本文注释所引节号体系 §1-§8 的解析归宿)。
GameState(正名前暂名 BoardState,后果节+ 待裁决7)= 当前仍为真的局内已知事实快照:单例,每局新建,
只描述「此刻」;画面 op 与决策 op 写,策略器读(设计 §1)。历史序列归遥测,
不经本结构。

**局面表示单一载体**(benchchar-retirement P5 起):本容器 = 实机真值
记录模型(只记录实机会产生的已知事实),sim 后端/实机操作链/策略决策
同吃容器。旧推演内核帧与帧→容器合成口已停用(benchchar-retirement P5)——生产写入 = **写入口直写**(sim 世界腿
obs 写点与动作腿 logic_action 上报函数族,统一经渠道签名写入口落字,
渠道族封闭集见下文遥测段);
测试种子 = 测试仓 builder 直写容器域(与观察链同写入口)。逐字段映射
对账正本(game_state/fields.md §9)随帧通道停用失去载体(P8 承接)。字段准入按设计 §8.8 治理三件:派生量(席空数/席满判定/board
下档阈值)是计算函数不存储;识别质量位是写入闸门不存储(失读统一口径 =
§2.2 carried/机制性 None)。

**两个关键结构**(设计 §2.4;预期条目表已废,勿复活):
1. 帧观察完整度标注 + 心跳——标注(full/view/none)消费即清;停更检测
   哨兵用只增不减的写点序号 :attr:`GameState.write_seq`,不用标注现值。
2. gs_schema——域粒度版本映射(缺域键 = 该域未建模,§3.7.1)。

**两态直写**(2026-09-11 用户裁定):字段来源只保留 observation
与 logic 两种——逻辑推算值经 :meth:`GameState.write_logic` 直接写字段
(source=logic,策略器立即可读),expect/confirm 两步机制(预期条目表/
PendingEntry/confirm 转正/discard_expected)全套废除;逻辑态错误 =
代码 bug(修推算代码,不靠运行时待办对账兜底)。以实际观察为准原则不变(§2.3):
下一帧实读覆盖 logic,失配缺陷台账留存证据。

**逻辑随机态**(来源 logic_rand,:meth:`GameState.write_logic_rand` 直写):
逻辑态的随机效果扩展——**效果随机的动作采样链**写入:上报函数真掷
随机,把采样结果当真实发生走完整确定性链;值 = 一个可能世界的快照
(采样值/未变标记/确定外壳三形态),真值结构上不可由推算钉死(实机上
采样是猜测,sim 里采样即世界真值——同一上报函数两副面孔)。与逻辑态的
两条语义分界:①观察覆盖差异 = 随机效果落地,**预期内非 bug**——只落
``logic_rand_outcome`` 台账行留存证据(无告警无停机,随机模型校准遥测面),
不进失配三分流;②策略器消费前**必须重观察**(查询口 =
:meth:`GameState.logic_rand_fields`;跨动作污染经
:meth:`GameState.any_logic_rand` 入口判定继承)。

**开局种子底座与锚定标志**:局容器经 :func:`game_state_of` 缓存单例支冷建
即以开局初值播种 A 类字段(:func:`seed_opening_state`,随机态通道——
确定值外壳未验证,首观察静默覆盖,差异只落 ``logic_rand_outcome`` 台账
行);:attr:`GameState.prep_anchored` = 锚定标志,首次备战 heavy 锚定成功
置位(生产唯一写点 = reconcile 同点,粘性无复位),未锚定期容器逻辑写
通道规则的解析读口 = :func:`prep_anchored_of`、择道口 =
:func:`anchor_aware_write`;carry 失读沿用对随机态
来源不适用(随机态值不是「上次好值」,不洗白)。

**单例宿主** = session 旁表(:func:`game_state_of`;同 ``cw_exec_state``
旁表模式,弱引用表 + 桩面兜底)——session 对象 = 局身份,新局新 session
即天然新建,符合「单例,每局新建」(§1/§6.2)。

**统一 state 遥测升级(常开化后形态)**:写入 API 全部带**必填**渠道签名
(:class:`ChannelSig`,渠道族封闭集 obs/logic_action/logic_hook + 字段级
质量元数据;R5 迁移规划,集内无空 actor 行);:attr:`GameState.write_seq`
升格为**版本 id**(每次写入单调分配,不重不漏,:meth:`GameState.current_version`
读口);每次写入落一行**自足状态流水**(行 = 改了什么 + 渠道签名 + 版本 id +
写入后完整 state 快照,行行自足查询直接读——无快照锚/无对账自检/无前溯推导,
禁回归)。落盘由 :mod:`sr_od.application.currency_war.kernel.cw_state_journal`
承载,**无条件常开**(生产装配 = currency_war_app 装配段 + 局容器单例建立点
兜底——遥测装配 = game state 职责(用户裁定 2026-09-15 精化令):触发
只钉 :func:`game_state_of` 建立路径,GameState 构造器零装配逻辑;无开关;
行落盘另以 sink 在场与 run_id 在场为准,sink 缺席 = 行不落而写路径照常——
记录被动,不改写路径语义)。新增**逻辑态
派生域与画面上下文域**(字段面 as-built =
``docs/develop/sr_od/application/currency_war/game_state/node-domain.md`` §2):``prev_screen``/``current_screen``
(①观察汇聚写)+ ``top_bar_raw``(顶栏原文,**观察层**,observe() 只落原始
读数)+ ``node_pos``(**两态序键**,迭代 2026-09-20-node-advance-action-report:
观察锚定态 = observe_node_anchor 直写 observation / 推进未确认态 = 终结
动作上报 write_logic——「禁 observe 直写序键」旧裁决随本迭代推翻,改判
依据 = 该迭代 design §2.2/§2.7-7;值载体 = ``(位面, 轮)`` 元组键
(:data:`cw_node_schedule.NodePos`),全局编号表示已废弃,迭代
2026-10-12-abolish-node-ordinal)。
**节点推进触发模型(动作上报化,四推断腿已停用)**:序位前进唯一
落账入口 = 推进生效原语 :func:`advance_node_effective`(动作上报
:func:`report_node_advance` / 观察锚定补推 :func:`observe_node_anchor`
两路径,效果推进尾段同临界区);跨位面由后继原语
:func:`cw_node_schedule.sequence_next` 承载;推进去重键 =(run_id,
生效序位)。类型派生 = BOSS 简报屏直定
(经 ``kernel/cw_screen_report/boss_briefing.py``,目标 = 现 hist)+商店
面板查现行链(``observe_screen_context`` 商店分支;链观察落地批
2026-09-16:载体 TokenCell/NodeChain,写端 = 过渡屏 transition_row/
transition_snapshot + 备战帧 prep_row,字段 node_path/node_path_baseline)。
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
    # LostNodeRef 宿主 = cw_economy(其运行时 import 本模块,反向即循环;
    # pending_loss 字段类型面 TYPE_CHECKING 承载)
    from sr_od.application.currency_war.kernel.cw_economy import LostNodeRef

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

# 失配处置策略(豁免注册表 + 失配告警钩子槽;kernel→kernel 单向依赖,
# 对方零依赖本模块)。observe() 失配三分流路由消费(见 _route_logic_mismatch)。
from sr_od.application.currency_war.kernel.cw_mismatch_policy import (
    fire_reconcile_andon,
    lookup_mismatch_exempt,
)
from sr_od.application.currency_war.kernel.cw_node_schedule import (
    PLANE_NODE_TABLES,
    NodePos,
    sequence_next,
)
from sr_od.application.currency_war.kernel.cw_ore_reward import (
    OreReward,
)
from sr_od.application.currency_war.kernel.cw_overlay_register import (
    ScreenChanges,
)
from sr_od.application.currency_war.kernel.cw_registry import DEFAULT_REGISTRY

# 同桶直调(kernel→kernel 合法;遥测装配 = game state 初始化职责,用户
# 裁定 2026-09-15)。本模块无反向模块级 import(其 kernel 依赖均为函数内
# 惰性),模块级 import 不成环。
from sr_od.application.currency_war.kernel.cw_state_journal import (
    ensure_journal_assembly,
)
from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl

if TYPE_CHECKING:
    pass


# ============================================================ 常量

#: 备战席容量默认恒 9,不随等级/职级变化(§3.2.5;现役同口径常量 =
#: ``cw_state.BENCH_CAPACITY``)。唯一改写源 = 节省工位时限效果(激活期 3、
#: 3 节点后自动回 9,经效果账本 §5.1 逻辑写入)。
BENCH_CAPACITY_DEFAULT: int = 9

#: 上阵前排物理槽位数(恒 4;同值常量 = ``cw_exec_state.DEPLOYED_FRONT_CAPACITY``,
#: 3.1 容器合并起容器侧自有单一源,换算层停用后唯一)。
DEPLOYED_FRONT_CAPACITY_DEFAULT: int = 4
#: 上阵后排基线槽位数(动态容量 6-9 的下限;同值常量 =
#: ``cw_exec_state.DEPLOYED_BACK_CAPACITY``)。定长 10 下标工作表(3.1
#: 窗口期桥/tracked 主账坐标系)的后排段长 = 本值,扩展格 7-9 超出其
#: 表示域(既有 tracked 硬上限边界,3.2 随 tracked 停用续覆盖)。
DEPLOYED_BACK_CAPACITY_DEFAULT: int = 6

#: 行级 schema 版本(§3.7.1)。域版本映射见 ``DEFAULT_GS_SCHEMA``。
#: 版本 2 = 上阵域合卷(front_row/back_row 两紧凑行域 → deployed 单字段
#: DeployedView 完整槽位表旧档 restore 经迁移函数
#: 单次转换,见 ``restore_state_snapshot``)。
GAME_STATE_SCHEMA_VERSION: int = 2

#: 域粒度版本映射的当前全集(缺域键 = 该域未建模,禁建「None=未建模」占位
#: 字段,§2.2/§8.8)。域增删或字段语义破坏性变更时 bump 对应域版本。
DEFAULT_GS_SCHEMA: dict[str, int] = {
    'node': 2,              # node/node_path/node_path_baseline(§3.2.1/§3.2.2;域版本 2 =
                            # node_path 值形 NodeChain 载体(逐格 TokenCell 元数据)
                            # + 基线链字段 node_path_baseline)
    'units': 2,             # deployed(单字段 DeployedView 完整槽位表)/bench/back_layout
                            # (§3.2.3-§3.2.7;域版本 2 = front_row/back_row 两紧凑行域
                            # 合卷为 deployed 单字段(容器合并,
                            # 空槽 None 显式、位置 = 子表下标派生);版本 1 = 紧凑行域两字段)
    'economy': 1,           # gold/level/xp/streak/hp/level_up_cost(§3.2.9-§3.2.13)
    'match_facts': 6,       # 职级/对局类型/敌人难度/boss/词缀/环境/持卡/定时道具队列/board
                            # (§3.1/§3.2.6/§3.2.14/§3.2.20;域版本 6 = 新增
                            # pending_item_grants 定时道具发放队列;域版本 5 =
                            # 恢复局旗标 resumed_match 已停用删除(零逻辑消费,勿复活);
                            # 域版本 4 = 新增 lv999_cost_tier 银狼LV.999 当前费用档;域版本 3 =
                            # 接管补采计数/完成标志两字段停用——补采编排归
                            # CwEntryPlaneIntel,真值经写门落
                            # plane_bosses/enemy_affixes;域版本 2 = 接管/恢复字段迁入,
                            # 渠道③接管协议 logic_hook)
    # (refresh_counters 域不在容器:三字段住效果
    #  账本 ActiveEffectInventory(统一计算,写端 = 刷新上报函数)。)
    'node_screen_refresh': 4,  # 节点屏刷新计数组(§3.4.1-§3.4.4;遭遇/补给/环境/策略逐卡)
                               # 域版本 4 = encounter 侧换剩余语义(旧「已用」计数与
                               # per-visit 位停用,新增顶层字段 encounter_refresh_left);
                               # 域版本 3 = supply 侧换剩余语义(旧「已用」计数停用,
                               # 新增顶层字段 supply_refresh_left)
    'invest_opts': 1,          # 投资双画面候选槽(§3.4 终态契约八新槽;str 原文名)
    'megastar_opts': 2,        # 盛会之星候选槽(list[MegastarOption],typed)
                               # 域版本 2 = MegastarOption 扩 xy 点击坐标
                               # 字段(选择坐标观察上报,fields.md §3.4.5a
                               # B 类 typed 域版本 bump 契约)
    'partner_opts': 1,         # 列车同行候选槽(list[PartnerOption],typed)
    'planner_opts': 1,         # 骇入策划候选槽(list[PlannerOption],typed)
    'star_tome_opts': 1,       # 星徽秘典候选槽(str)
    'star_tome_opts_xy': 1,    # 星徽秘典选项坐标伴随域(选择坐标观察上报,fields.md §3.4.5a)
    'wish_trial_opts': 1,      # 祈愿试炼候选槽(str)
    'wish_trial_opts_xy': 1,   # 祈愿试炼选项坐标伴随域(选择坐标观察上报,fields.md §3.4.5a)
    'box_card_names': 1,       # 武装箱候选槽(str)
    'box_card_names_xy': 1,    # 武装箱选项坐标伴随域(键名随名字域 box_card_names;选择坐标观察上报,fields.md §3.4.5a)
    'fortune_opts': 1,         # 命运卜者强化候选槽(str;契约扩员 12→15)
    'fortune_opts_xy': 1,      # 命运卜者强化选项坐标伴随域(选择坐标观察上报,fields.md §3.4.5a)
    'expert_invite': 2,        # 专家邀请函选卡载体(ExpertInvitePayload;域版本 2 =
                               # payload 扩选项坐标字段 card_points/cash_point
                               # (选择坐标观察上报,fields.md §3.4.5a);版本 1 =
                               # 契约扩员 12→15)
    'inventory': 1,         # equips/consumables/免战牌(§3.2.15/§3.2.16/§3.2.19〔勘误:免战牌正本=effect_inventory.remaining_uses,§8.6-3——本域不含其字段〕)
    'spheres': 1,           # 晶矿(§3.2.8,不占席)
    'ore_rewards': 1,       # 矿附着奖励域(
                            # 随机态,键 = 矿身份最新观察坐标 'x,y')。独立键
                            # 不并入 spheres bump——spheres 本体未变,bump 会
                            # 对旧档谎报域内容变更
    'ore_declared_pending': 1,  # 声明待兑现队列(同迭代;元素 (env, plane, gold),
                                # 电平入队/消费/过期三口,详设 ore-reward-channel §5)
    'ore_declared_done': 1,     # 声明已消费标记(同迭代;幂等守卫第二腿,
                                # 元素 (env, plane),位面过渡随 pending 同清理)
    'env_grants_done': 1,       # 环境条件发放已发标记(迭代
                                # 2026-10-10-env-conditional-grants;元素
                                # (env,条件键),发放刻追加局内恒存,详设
                                # env-conditional-grant §1)。独立键版本 1
                                # 不并入他域 bump——他域本体未变,先例 =
                                # ore_rewards 不并入 spheres
    'node_seq_by_plane': 1,     # 逐位面节点序列场字段(「人身意外险」设计迭代:
                                # 键 = 位面 1 基,值 = 节点类型序;逻辑态,
                                # 写点唯一 = gain_invest_env 尾段,注册后
                                # 恒全量。独立键版本 1,同 env_grants_done
                                # 先例不并入他域 bump)
    'substate': 1,          # 分类子态/事件浮层(§3.2.17/§3.6.1)
    'shop': 2,              # 商店开态 payload(§3.3;域版本 2 = ShopPayload 扩
                            # 牌行点击坐标字段 card_points(选择坐标观察上报,
                            # fields.md §3.3.1/§3.4.5a))
    'encounter': 2,         # 遭遇屏 payload(§3.4.1;域版本 2 = options 形状
                            # 升级 typed EncounterOption,终态契约)
    'supply': 3,            # 补给屏 payload(§3.4.2;域版本 3 = SupplyOption
                            # 扩 extra_equips 附加装备元组(列 = 角色+装备组,
                            #  过剩经费;typed 选项结构扩字段 = 值形状变更,
                            # fields.md §3.4.5a bump 契约);域版本 2 = options
                            # 形状升级 typed SupplyOption,终态契约)
    'event_choices': 1,     # 十事件屏 chosen_*(§3.4/§4 事件选择)
    'settlement': 1,        # 结算真值组 + hp 保底事件位(§3.5)
    'effects': 1,           # 在场效果激活账本(§5.1,非 Field 载体)
    'derivation': 5,        # 逻辑态派生域与画面上下文域(R1 §3.1.4;域版本 5 =
                            # 节点域换键(迭代 2026-10-12-abolish-node-ordinal
                            # design §2.2:序键字段整体停用换 (位面,轮) 元组键
                            # node_pos/node_hist_pos 承载);历史:4 = node_ord
                            # 两态生命周期 + 四推断腿整体停用(切换批
                            # 2026-09-20-node-advance-action-report:推进 =
                            # 终结动作上报/观察锚定,弹窗/位面过渡/BOSS简报/
                            # 备战四腿与守卫族常量删除);
                            # 3 = 字段层次终极版,1=R1 双腿双字段,2=单字段双层)
    'receipts': 1,          # 动作回执域(R2 §3.1.1-4/§3.2.5:普通 Field 域滚动窗,唯一写点 = note_action_receipt)
    'match_final': 1,       # 局终域(§3.6.1 runs 并入载体:一段一行,
                            # 恢复局跨段 = 多行,game 级聚合取段序末行;唯一
                            # 写点 = write_match_final,actor=MatchClose)
    'round_ledger': 1,      # 轮内新鲜度账(round_fresh_buys;渠道②动作上报,
                            # 值形状 {'phase': (plane, round_num)|None,
                            # 'names': list[str]},经 record_fresh_buy 单口)
}

#: 画面附加域(§2.2 显式例外):语义 = 「当前画面的 payload,非当前画面
#: =None」——离开画面置 None 是结构事实非失读,不受 carried 硬边界覆盖。
#: 值 = (属屏, route_clearable) 二元组(终态契约路由清点:属屏 = 分发键
#: 建档屏名;route_clearable=False = 挂点跳过,清点源独占)。`shop` 保留
#: 映射内 False(leave_screen 域守卫依赖,清点由既有两处显式口独占);
#: `prep_obs` 不入映射(语义豁免)。选项坐标伴随域(`*_opts_xy` 族 /
#: payload 坐标字段,选择坐标观察上报 = fields.md §3.4.5a)与名字域同属屏、
#: 同 route_clearable 已登记——离屏清场坐标域与名字域同格,防跨屏携陈值。
_PAYLOAD_DOMAINS: dict[str, tuple[str, bool]] = {
    'shop': ('货币战争-备战-开商店', False),
    'encounter': ('货币战争-遭遇节点', True),
    'supply': ('货币战争-补给', True),
    'invest_strategy_opts': ('货币战争-投资策略', True),
    'invest_env_opts': ('货币战争-投资环境', True),
    'megastar_opts': ('货币战争-盛会之星', True),
    'partner_opts': ('货币战争-列车同行', True),
    'planner_opts': ('货币战争-银狼升星', True),
    'star_tome_opts': ('货币战争-星徽秘典弹窗', True),
    'star_tome_opts_xy': ('货币战争-星徽秘典弹窗', True),
    'wish_trial_opts': ('货币战争-祈愿试炼', True),
    'wish_trial_opts_xy': ('货币战争-祈愿试炼', True),
    'box_card_names': ('货币战争-备战-武装箱选择', True),
    'box_card_names_xy': ('货币战争-备战-武装箱选择', True),
    'fortune_opts': ('货币战争-命运卜者强化', True),
    'fortune_opts_xy': ('货币战争-命运卜者强化', True),
    'expert_invite': ('货币战争-备战-专家邀请函', True),
}


# ---- 画面上下文域常量(R1 §3.1.4/§3.4;观察汇聚漏斗的画面标识映射面)----
# (弹窗腿守卫族/弹窗族清单/位面过渡腿触发面/专属画面类型直定映射四组
#  常量已停用——见 2026-09-20-node-advance-action-report design §2.5 停用清单。)

#: 干净备战帧画面标识(画面建档 screen_name;漏斗 prep_clean/全量路径的
#: 上下文对画面标识,亦是备战锚定写端 ``observe_node_anchor`` 的
#: trigger_screen)。
SCREEN_PREP_FRAME: str = '货币战争-备战'

#: 商店面板块画面标识(节点类型「未定型」零直定——商店对任意节点类型
#: 都开,类型来源 = observe_screen_context 商店分支「查现行链」
#: (:func:`chain_node_type`))。
SCREEN_SHOP_PANEL: str = '货币战争-备战-开商店'

#: 战斗/结算段内相位 token(观察阶段键 battle_or_transit 的上下文对标识;
#: 段内多物理屏,观察阶段键无法细分到建档名,按分支级记录)。
BATTLE_WAIT_CONTEXT: str = '货币战争-战斗等待'

#: BOSS 简报画面标识(BOSS 类型直定的 trigger_screen;类型直定写端 =
#: ``kernel/cw_screen_report/boss_briefing.py``,目标 = 现 hist——去证据门
#: 后上报先于下一节点任何画面渲染恒成立,简报 op 被分派 ⇒ hist 已被
#: settle_confirm 推进至 boss 节点,用户裁定 2026-09-21)。
SCREEN_BOSS_BRIEFING: str = '货币战争-BOSS简报'

#: 结算屏画面标识(动作后果声明 ``next_screen`` 值;档名权威 =
#: currency_war_settlement.yml,与 sim 后端呈现屏同档名,声明化迭代
#: 对照表 #3/#4)。kernel 侧消费 = 出战/遭遇上报的声明构造。
SCREEN_SETTLE: str = '货币战争-结算'


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

#: obs_event 事件词表封闭集(§3.2.3 行型 2:arbitrate=拒读/仲裁拒绝留存证据 /
#: miss=失读留存证据 / popup=弹窗类流程异常留存证据)。集外值 = 红(硬约束 2 同纪律:
#: 事件面漂移要在登记点暴露,禁自由串)。
OBS_EVENT_EVENTS: tuple[str, ...] = ('arbitrate', 'miss', 'popup', 'chain_diff')

#: logic 两族子模:恒 compute(逻辑计算,无观察质量语义)。
LOGIC_MODES: tuple[str, ...] = ('compute',)


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
    """显式签名的写入口校验(§3.2.4 硬约束 2):渠道族须匹配该 API 的合法族;
    违反显式炸错(禁静默收下——渠道面漂移要在写点暴露)。actor 仅作遥测/
    台账行的动作身份标注,不设白名单闸:上报方是一方代码,写错身份 = 错账,
    由观察对账兜住(账实不符 → 失配告警 → 根因调查)。"""
    if sig.family not in allowed_families:
        raise ValueError(
            f'渠道族 {sig.family!r} 不属本写入口合法族 {allowed_families}'
            f'(§3.2.4 硬约束 2 渠道封闭集)')


@dataclass(frozen=True)
class ChannelSig:
    """渠道签名(§3.2.1):每次写入携带的「谁写的、从哪写的、质量如何」
    结构化标注,随状态流水行落盘。

    - family = 渠道族(:data:`CHANNEL_FAMILIES` 封闭集,构造期校验);
    - actor = 写入者身份标注(op 类名/模块名,随行落台账供对账过滤;
      不设白名单闸);
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
    (observation/logic;logic_rand = 逻辑随机态,carried/prior =
    obs 族来源子模,见 §2.1)。

    - observation = 亲眼看到的(识别结果/sim 真值合成,evidence 恒带标记);
    - logic = 决策动作按游戏规则推算的预期效果,经
      :meth:`GameState.write_logic` 直接写入(策略器立即可读),**保持
      logic 不翻 observation**(§8.1),直到下一次观察覆盖(失配 = 推算
      bug,缺陷台账留存证据,修推算代码);
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
    由 char_id+当前排推导。禁在 Unit 另存阵营(防注册表双源)。

    **槽位不存**(原 slot 信息位停用):位置 =
    所在子表下标纯派生(deployed = DeployedView.front_slots/back_slots
    下标;bench = BenchView.slots 下标),单位跨域流动时位置由动作载荷
    携带(DeployMove(to_row, to_slot) 等参数即此)。
    """

    char_id: str
    star: int                       # 星级 1..3(合成上限;观察期快照)
    equips: list[str] = field(default_factory=list)


#: 后排物理格数上限(布局值域 {6..9} 的上界;用户口述 2026-09-11
#: 重申:平常 6,宝钻/召唤物最多 9。观察写端槽位合法性的硬边界——
#: 超此即读链漂移,丢弃留存证据)。
DEPLOYED_BACK_CAPACITY_MAX: int = 9


@dataclass(frozen=True)
class DeployedView:
    """上阵统一槽位视图(同族先例 = BenchView / ShopPayload.cards;
    容器合并:front_row/back_row 两紧凑行域合卷)。

    - front_slots[i] = 前排物理槽 i+1(定长 4,下标 = 前排物理槽-1);
    - back_slots[j] = 后排物理槽 j+1(动态容量 6-9,随布局扩容;容量变化
      = 整视图结构性写,先例 = BenchView.capacity 随效果改写);
    - 空槽 = None 显式:槽位直址 = (子表,下标),「紧凑下标 ≠ 物理槽位」
      家族病灶(席位第二账的存在理由)在本模型下结构性消失;
    - 一次写 = 一次完整语义变更(换排/替换/空槽上场 = 单字段整值替换,
      frozen 帧替换,先例 = wear_equip 的域整表重建写法)。
    """

    front_slots: list[Unit | None] = field(default_factory=list)
    back_slots: list[Unit | None] = field(default_factory=list)


def deployed_view_of_hits(front_hits: list, back_hits: list,
                          back_capacity: int | None = None) -> DeployedView:
    """观察读链命中 → 上阵视图(观察写端值构造单一源;读侧仍分排读屏)。

    - hits 元素 = ``(排内 1 基槽号, Unit)``(identify_slots 直产,槽位对
      携带——Unit 本体无槽位信息位,位置只在读链局部存在);
    - back_capacity = 后排读到的槽位数(布局选档产物);缺省按 6 基线
      (布局未知帧只读前排时保持 6 槽基线容量),合法命中(≤ 布局值域
      上界 9)可越给定提示扩容;
    - 槽位越界命中(>前排 4 / 后排 > 布局上界 9 或 <1)丢弃并 log 留存证据
      (读链漂移信号,与 _bench_view_of 同纪律:静默丢弃 = 身份静默丢失)。
    """
    front: list[Unit | None] = [None] * DEPLOYED_FRONT_CAPACITY_DEFAULT
    for s, u in (front_hits or []):
        if 1 <= int(s) <= DEPLOYED_FRONT_CAPACITY_DEFAULT:
            front[int(s) - 1] = u
        else:
            log.warning('[cw!][identity] 上阵读链前排槽位越界丢弃:'
                        'slot=%s char=%s(SIFT/星级读链漂移信号)',
                        s, getattr(u, 'char_id', ''))
    cap = max(int(back_capacity or 0), 6)
    back: list[Unit | None] = [None] * cap
    for s, u in (back_hits or []):
        _s = int(s)
        if 1 <= _s <= DEPLOYED_BACK_CAPACITY_MAX:
            while len(back) < _s:
                back.append(None)   # 合法命中越提示容量 → 扩容落位
            back[_s - 1] = u
        else:
            log.warning('[cw!][identity] 上阵读链后排槽位越界丢弃:'
                        'slot=%s char=%s(>布局上界 9,读链漂移信号)',
                        s, getattr(u, 'char_id', ''))
    return DeployedView(front_slots=front, back_slots=back)


def deployed_view_sequential(front_units, back_units,
                             back_capacity: int | None = None) -> DeployedView:
    """紧缩单位序 → 上阵视图(顺延落位:第 k 个单位落槽 k)。

    测试种子与旧档迁移的落位语义承接(原紧凑行域列表的「顺序即占位」
    口径:紧凑序第 k 位 ↔ 物理槽 k)。前排恒 4 容量;后排容量 = 给定值
    或 max(单位数, 6)。"""
    front: list[Unit | None] = list(front_units or [])
    while len(front) < DEPLOYED_FRONT_CAPACITY_DEFAULT:
        front.append(None)
    cap = int(back_capacity or 0) or max(len(list(back_units or [])), 6)
    back: list[Unit | None] = list(back_units or [])
    while len(back) < cap:
        back.append(None)
    return DeployedView(front_slots=front, back_slots=back)


def deployed_rows_of_view(view: DeployedView | None,
                          ) -> tuple[list[Unit], list[Unit]]:
    """上阵视图 → 紧缩单位行(前排在前;空槽跳过)。"""
    if view is None:
        return [], []
    return ([u for u in (view.front_slots or []) if u is not None],
            [u for u in (view.back_slots or []) if u is not None])


def deployed_indexed_of_view(view: DeployedView | None,
                             ) -> list[Unit | None]:
    """上阵视图 → 定长 10 下标工作表(合成仿真/满栏买计数的工作副本
    坐标系;3.2 裁定保留:消费方 = merge 级联族与 merge_buy_k 等工作
    副本构造,非 tracked 残留)。

    下标 0-3 = 前排槽 1-4 直取;4-9 = 后排槽 1-6(后排 7-9 扩展格超出
    动作坐标系表示域,截断丢弃——动作坐标系 10 槽硬上限为既有边界)。"""
    view = view if view is not None else DeployedView()
    back = list(view.back_slots or [])[:DEPLOYED_BACK_CAPACITY_DEFAULT]
    while len(back) < DEPLOYED_BACK_CAPACITY_DEFAULT:
        back.append(None)
    return list(view.front_slots or []) + back


def deployed_view_of_indexed(dep: list[Unit | None] | None,
                             orig: DeployedView | None = None,
                             ) -> DeployedView:
    """定长 10 下标工作表 → 上阵视图(``deployed_indexed_of_view`` 逆桥;
    合成/迁移工作副本落回容器的构造单一源)。

    后排容量继承 ``orig``(工作表不覆盖容量——容量变化 = 整视图结构性写,
    只经观察/布局改写);orig 缺席按 6。工作表触不到的后排 7-9 扩展格
    原样保留 orig 值。"""
    dep = list(dep or [])
    orig = orig if orig is not None else DeployedView()
    front = [dep[i] if i < len(dep) else None
             for i in range(DEPLOYED_FRONT_CAPACITY_DEFAULT)]
    back_len = max(len(orig.back_slots or []),
                   DEPLOYED_BACK_CAPACITY_DEFAULT)
    back = [dep[DEPLOYED_FRONT_CAPACITY_DEFAULT + j]
            if DEPLOYED_FRONT_CAPACITY_DEFAULT + j < len(dep)
            else None
            for j in range(DEPLOYED_BACK_CAPACITY_DEFAULT)]
    _orig_back = list(orig.back_slots or [])
    while len(_orig_back) < len(back):
        _orig_back.append(None)
    for j in range(DEPLOYED_BACK_CAPACITY_DEFAULT, back_len):
        back.append(_orig_back[j])
    return DeployedView(front_slots=front, back_slots=back)


@dataclass(frozen=True)
class BenchSlot:
    """备战席一槽:五种内容之一(统一槽位视图,占位真值一份,§3.2.5)。

    占席真值 = :func:`slot_occupies`:unit/supply_box/tome/bookcard 占 1 槽、
    empty 不占(晶矿不占席——它是点击目标不是席位居民,§3.2.5)。sim 合成
    帧「箱不占席」= sim 无箱实体的内部口径约定,**记录模型按实机真值**。
    bookcard = 书册卡细分(开卡动作的策略器发出分支按 kind 分派,用户裁定
    2026-09-19 开卡时机归策略实现管——原先统一降级 supply_box,策略器开箱
    分支会对着卡槽发 OpenBox 必败,由入口清场先于观察 masking)。
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
    ↔ 1 基屏幕槽位,与现役 ``cw_state.bench`` 下标语义同构)。
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
    # [索引定义] points = 点击目标载荷(黑板帧停用
    # 阶段 3.4 扩充):每项 (color, x, y, r) 平铺元组——晶矿为自由位置识别物
    # 无槽号,像素坐标必须随识别进容器(总纲坐标契约;点击列由 kernel
    # ``ore_click_targets_of`` 还原消费)。取值时机 = 备战入口 heavy
    # 每帧实读覆盖(两态制,以实际观察为准;两帧持存防抖留观察链);写入端单一
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
    merge_mechanics §2.7 口径);✦ 读取器读数仅核对信号(降级)。
    牌位点击坐标不入存储——坐标单一真相源 = screen_info「商店牌-N」区域
    (cw_obs_core.shop_card_click_points);入存储的是**槽号**(观察事实,
    见 slot 字段),执行侧按槽号从 screen_info 现取坐标。
    """

    name: str = ''
    faction: str = ''
    cost: int = 0
    star: int = 1
    # 信源位(§3.3.1):**原值透传不折叠**(P2-4 审查证据分级禁丢)——
    # 词表 = ShopCard.cost_source 三值:badge=费用徽章直读 /
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
    # bench 布局错位的商店牌行版)。
    slot: int = 0


@dataclass(frozen=True)
class ShopSlot:
    """商店一槽:三态之一(定长五槽的元素,用户三态裁定 2026-09-13)。

    kind='content' 时 card 有效;empty=识别确证无内容(占位带);
    unknown=应为内容但识别失败(必携缺陷台账,决策一律跳过)。
    物理槽位 = 数组下标 + 1(1 基,= screen_info「商店牌-N」序号);
    本类型无 slot 字段——定长数组下标即槽位,紧凑下标≠物理槽位的
    历史病灶类(同族)在本模型下结构性消失。
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
    # [索引定义] card_points = 牌行点击坐标,坐标系 = 数组下标 + 1 = 物理槽
    # (1-5,与 ShopSlot 既有槽位坐标系同格;BuyCard 词表 slot(1 基)直接作
    # 键零换算);取值时机 = 进店观察期快照,动作执行期恒稳。写入端 = 入口
    # 观察上报(与 cards 同门一并写;op-layer.md §1.1 选择坐标观察上报,
    # fields.md §3.3.1/§3.4.5a);上报接线未落地前 = 未观察 None;上报后
    # 定长 5(与 cards 定长不变量对齐)。sim 无画面识别不建模,恒 None。
    card_points: tuple[tuple[int, int], ...] | None = None


def shop_payload_content_cards(payload: ShopPayload | None) -> list:
    """ShopPayload → 内容牌紧缩视图(消费点兼容读,三态裁定 2026-09-13)。

    返回 content 槽 card 的紧缩列表(序 = 槽序);empty/unknown 槽跳过——
    即帧时代紧缩读语义(旧列表从不含空位),消费点行为零漂移。坐标系:
    列表下标 = content 序(≠ 物理槽);物理槽直取 = 候选带槽号改造时切换
    (商店域消费点审计面)。
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
    """补给屏附加(§3.4.2):列数动态——通常4选1,效果改写3-5,勿写死
    (读链 = obs/cw_node_obs.read_supply_options,角色锚点定列、列 = 选项)。
    options 元素 = SupplyOption(终态契约形状升级:裸 tuple(str,str,bool) →
    typed;extra_equips 附加装备元组 additive,列 = 角色+装备组)。"""

    options: list[SupplyOption] = field(default_factory=list)


@dataclass(frozen=True)
class ExpertInvitePayload:
    """专家邀请函弹窗附加(契约扩员 12→15 新槽):选卡
    决策双输入载体(kernel ``choose_expert_index`` 的两参打包)。

    [索引定义] card_bonds = 四卡区羁绊解析,坐标系 = 画面「卡-1..卡-4」
    物理区序(0 基下标即判据返回的卡下标,恒稳);取值时机 = 弹窗帧
    OCR 解析期快照,写入端 = CwScreenExpertInvite。board = 弹窗帧羁绊
    面板现读计数;读数失败 = {}(判据侧据此落现金为王兜底,语义复刻)。"""
    card_bonds: list[str | None] = field(default_factory=list)
    board: dict[str, int] = field(default_factory=dict)
    # [索引定义] card_points = 四卡区点击坐标,坐标系 = 「卡-1..卡-4」区序
    # (0 基下标 = card_bonds 同一卡下标坐标系,与选卡词表 param.idx 同序
    # 零换算);取值时机 = 弹窗帧观察期快照(观察期 area 中心解析,动作执行
    # 期恒稳)。写入端 = 专家邀请函观察上报(与 card_bonds 同门一并写;
    # op-layer.md §1.1 选择坐标观察上报,fields.md §3.4.5a);cash_point =
    # 词表特形 idx=-1(现金为王)的独立坐标,不进列表防 -1 负下标歧义。
    # 二者 sim 无画面识别不建模恒 None;观察写端接线未落地前亦恒 None。
    card_points: list[tuple[int, int]] | None = None
    cash_point: tuple[int, int] | None = None


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


# ============================================================ 局终域(§3.6.1 runs 并入载体)

#: 终局类型词表封闭集(retirement.md §2 runs 行:局终收束一行;并入映射 =
#: 现役 runs result 词表 win/loss/stopped + 非完结/无收束行 = abnormal)。
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
    kernel→telemetry import,就地复刻;等值性由局终交叉核对钉住):
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
#: 版本戳,沿用 version_stamp」;runs 停用后 = 策略版本戳唯一在档载体,
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
      (哨兵叫停/进程死亡等无正常收束路径的形态,**段内补写**落行——哨兵
      收束兜底路径按段尾账面补写,``backfilled`` = True + 行注记
      ``recovered`` 暴露,判读按注记区分真伪,§3.6.1 runs 行 G8 谓词;
      启动扫描的**历史段**补写不经本载荷的运行时写口,走专用装配通道,
      遥测正本 §3.2.2 规则 6②);
    - ``at_version`` = 本行自身版本 id(:meth:`write_match_final` 装配时点
      即将分配的 write_seq,与行头 ``v`` 恒等——终局时点的账面版本锚);
    - ``code_commit``/``registry_fingerprint`` = 写入时点版本戳(§3.6.1
      runs 行「沿用 version_stamp」:跑这局的代码版本 + 决策注册表内容
      指纹;模块级常量 :data:`_CODE_COMMIT`/:data:`_REGISTRY_FINGERPRINT`,
      进程内恒定)——runs 停用后策略版本戳的唯一在档载体;
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
    # 策略行为观测计数局终聚合(键并入载体;键全集登记
    # 底稿 =  逐键审计 256 字面+16 闭族+9 开放族,全部=策略行为键,零
    # 效果域键;键封闭性防线原由测试仓封闭测试承载,该测试随 09-13 有损清理
    # 删除且裁定(源码扫描形态)不恢复,防漂移归 review 与代码
    # 规范)。取值 =
    # 调用方收束时点自策略 state 容器(mandate_v1 StrategyState.cw4_counters)
    # 现读;写口落载荷时浅拷贝一份(本结构不持有容器引用,后写不串)。
    # None = 无策略载体/历史段补写无源(诚实缺省,判读按「无计数载体」
    # 分型);空 dict = 局内真实零计数——两型可辨,沿旧流装配语义
    # (match_archive v7 顶层字段同一分型契约)。
    # 旧档案局终行缺本键 =  前数据,按缺键读。


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
#: 'sim:engine' = sim 后端世界腿外部事件写(obs 族)覆盖动作逻辑态直写
#: 是 sim 建模的结构形态,事件注入(收入/结算/回声)对逻辑态的推进不是
#: 「推算 bug」,留存证据无判读价值;xp 即时结转(逻辑态直写)vs sim 轮末
#: 延迟结转(后端世界腿)= 申报差异(裁定 4 明点)。'sim:synthesized' = 合成口/
#: 喂入口真值合成的同性质差异(生产台账曾混入约 18.6 万行,迭代
#: 2026-09-16-unified-obs-reconcile 并列入表分流)。生产实机链零 sim
#: 前缀写点,抑制面对实机失配零触达。
_MISMATCH_SUPPRESS_PREFIXES: tuple[str, ...] = ('sim:engine', SIM_SYNTHESIZED)


def _rows_unit_key(u: Any) -> tuple[str, int, tuple[str, ...]]:
    """行写端单位多重集键(board 派生重算与纯重排吸收共用;键 =
    (char_id, star,装备集排序元组)。槽位号/行内顺序**不在键内**——
    游戏侧行内重排只改 slot 信息位,键相等 = 同单位多重集;装备集入键 =
    穿戴变化(星徽/卡带贡献面)不算纯重排,返回主循环真失配分流。"""
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
    ``cw_bond_equips._recount_board``(faction 字段载体,装备授予/
    sim 代理面);容器侧的对应漂移由 board 观察覆盖采新收敛
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
    3. 真失配 → 缺陷行 + ``[cw!]`` 告警 + 失配告警钩子(槽缺省关)。

    覆盖照常(以实际观察为准),本函数只管留存证据与处置;处置序设计取舍见
    game_state/README.md 观察对账与失配告警节。"""
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
    """缺陷台账留存证据(§2.3 以实际观察为准):观察覆盖 logic 值失配 = 推算 bug,
    留存证据后修推算代码(不做运行时待办对账)。best-effort:
    外送钩子异常不阻塞观察主链。抑制登记面见
    :data:`_MISMATCH_SUPPRESS_PREFIXES`(路由层
    :func:`_route_logic_mismatch` 与本发出口双重消费——吸收族
    (board 派生/纯重排/外部授予/边界金/备战环收入)不经路由层,
    发出口兜底保证 sim 证据行无论如何不入生产台账;豁免行除外,
    其落行处置序归路由层(豁免→抑制→真失配,design §2.3)。

    行形状(ts/sig 维度为迭代 2026-09-16-unified-obs-reconcile 补齐):
    ``kind / field / expected / actual / observed_evidence / ts /
    screen / actor / group_id / logic_evidence``——ts = journal 行同款
    秒级时刻;screen/actor/group_id = 观察侧渠道签名;logic_evidence =
    逻辑侧写端注记(豁免注册表第三维,归因回溯用)。
    真失配 kind 行落盘后同步触发失配告警钩子(:func:`fire_reconcile_andon`,
    行落盘先于钩子——证据在场不依赖钩子成败);豁免行无告警无停机。"""
    # 抑制登记面发出口兜底:吸收族落台账行不经 _route_logic_mismatch
    # 路由层,observed_evidence 命中抑制前缀的行(sim 链自身对账差异)
    # 归 sim 质量面,不落 buffer 不落 sink 不告警——生产实机链零 sim
    # 前缀写点,生产台账曾混入约 18.6 万行 sim 行才立此面(语义见
    # _MISMATCH_SUPPRESS_PREFIXES 注),发出口兜底防绕行。豁免行不覆盖:
    # sim 证据+豁免条目同击时路由层已裁定豁免先行落行(处置序 =
    # 豁免→抑制→真失配),发出口再抑制即翻转该裁定。
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
        except Exception as e:  # noqa: BLE001  留存证据 best-effort
            log.debug(f'[cw-gs] defect sink skip: {e}')
    if kind != 'observe_vs_logic_mismatch':
        return   # 豁免等非真失配行:留存证据即止,无告警无停机
    log.warning(f'[cw!][gs] 观察覆盖 logic 失配:{field_name} '
                f'预期[{expected}] 实读[{actual}](§2.3 观察赢)')
    fire_reconcile_andon(dict(row))


# ============================================================ 状态流水 sink(R1 §3.2.3)

#: 状态流水外送钩子(进程内单槽;行落盘的在场门——journal 本体无条件常开
#:(/:无开关,生产装配 = currency_war_app 装配段 + 局容器
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

    消费方 = 同桶策略侧决策行动作发出面(kernel/cw_decision_trace):两文件
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
    (玩家裁定 2026-09-09,现役 read_bench_full 通道停用挂批次二)。"""
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
    P2-4 审查);消费侧归并 = 对**费用数值**的可信度只分两域——badge
    徽章直读与 registry 注册表查表(含 roster_fallback 失读退查)给出的
    都是角色招募费真值,按费用消费的分支(估价/卖价/合成费用档)无需
    区分后两者。归并不丢证据:原值仍在 :attr:`ShopCard.cost_source`,
    失配归因/缺陷台账按原值分档。未知值保守归 registry(与 reader 缺省
    语义同向;词表外值 = 上游漂移信号,归因时看原值)。
    """
    return COST_SOURCE_BADGE if cost_source == COST_SOURCE_BADGE \
        else COST_SOURCE_REGISTRY


# ============================================================ 双 ShopCard 映射单一源(类型去重)
# 方案语义正本 = docs/develop/sr_od/application/currency_war/game_state/fields.md §3.3.1
# (双 ShopCard 映射):唯一容器类型 =
# :class:`ShopCard`(本模块);帧版(cw_vocab 侧同名类,带点击坐标 x)是
# 观测/执行域卡(OCR 产物带点击坐标,黑板帧链自持 x)
# ——两类型并存为长期形态,
# **转换只许在本节两个映射函数发生**(喂入面/消费视图
# 统一经此,禁散落内联转换——双源漂移温床)。本节 = kernel 内帧版类型的
# 唯一合法引用面(静态测试适用范围,测试 test_cw_w5_* 守)。

def shop_card_to_container(card) -> ShopCard:
    """旧容器牌 → 容器牌(喂入口的值构造单一源)。

    字段映射(name/faction/cost/star/cost_source)原值透传不折叠;
    x 是旧版独有的执行域字段,容器不入存储(坐标单一真相源 = screen_info);
    slot(物理槽号,观察事实)透传——执行点击按槽号取坐标的唯一依据。
    """

    return ShopCard(name=str(getattr(card, 'name', '') or ''),
                    faction=str(getattr(card, 'faction', '') or ''),
                    cost=int(getattr(card, 'cost', 0) or 0),
                    star=int(getattr(card, 'star', 1) or 1),
                    cost_source=str(getattr(card, 'cost_source', '')
                                    or 'roster'),
                    slot=int(getattr(card, 'slot', 0) or 0))


def shop_cards_to_legacy(cards: list[ShopCard]) -> list:
    """容器牌列表 → 旧容器牌列表(消费视图边界的值构造单一源)。

    - 五记录字段(name/faction/cost/star/cost_source)自容器透传;
    - ``slot``(物理槽号)自容器透传(执行/点击域事实,click_pts 按
      槽号取坐标的依据);
    - ``x``(点击坐标)置 0 不消费:决策消费不用坐标,执行侧 buy 发出
      从 screen_info「商店牌-N」区域按 slot 现取(黑板帧链自持 x,不经
      本函数)。

    :param cards: 容器牌列表(:attr:`ShopPayload.cards`)。
    """
    from sr_od.application.currency_war.kernel.cw_vocab import (
        ShopCard as _LegacyShopCard,
    )
    out: list = []
    for c in cards:
        out.append(_LegacyShopCard(
            x=0,
            slot=int(c.slot or 0),
            faction=str(c.faction or ''),
            name=str(c.name or ''),
            cost=int(c.cost or 0),
            star=int(c.star or 1),
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

    - **发出即簿记,不是验证**(R2 报告重构期的『发出即簿记非验证』
      裁定):``applied`` = 动作 op
      自身「是否发出」的机械事实透传,本口零成败判定——禁读屏核验、禁
      落地推断(落地判定归观察侧 reconcile);失败动作也产行(applied=
      false + reason),exec_events「正在蒸发的失败数据」教训的并入位;
    - 回执记录 = ``{op, applied, reason, detail?, screen?, **extra}`` 普通
      字典:op = 动作 op 名(类型名,exec_events 动作族承接);reason =
      未发出/受阻原因码('' = 正常发出);detail = 机械执行摘要(做了什么
      的人读面,恒透传);extra = 执行面结构化字段(plan_truncated/
      refresh_skipped/blocked 等,§3.2.1 质量词表执行面);
    - 滚动窗 = :data:`RECEIPTS_WINDOW_CAP` 条先进先出,整窗帧替换写入
      (普通 Field 域,非专用行机制,E3);窗序 = 写入序,同态同形;
    - 渠道签名:family=logic_action + actor(§3.2.1 ②类属 =
      执行动作的 op 类名)+ group_id = ``act:<actor>@<seq>``(§3.2.1 ②
      组标识格式);sig.screen 恒 None(逻辑计算无画面),画面桶由回执
      记录 screen 字段承接(exec_events 词表);
    - **常开化后的落盘语义**(影子闸折叠):回执写入无条件
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


# ============================================================ 账本→字段桥(§5.1/§3.2.5/§3.3.5-6)

def _bridge_sig(gs: GameState) -> ChannelSig:
    """效果桥写入的渠道③签名(单一构造点;§3.2.1 ③组 id =
    hook:<登记名>@<seq>;签名必填)。"""
    return ChannelSig(family='logic_hook', actor='EffectLedgerBridge',
                      mode='compute',
                      group_id=f'hook:EffectLedgerBridge@{gs.write_seq + 1}')


def apply_effect_burst_grant(gs: GameState, spec: Any, *,
                             frame: str = '') -> None:
    """桥·burst 形态(选卡一次性):登记时点把效果声明的免费刷新额度一次
    性累加进免费刷新剩余次数(§3.3.5 burst 族:免费午餐 11/及时雨 4/固定
    理财即时段 2 等;载体 = payload.free_refresh_burst)。只在本挂点累加
    一次——「一次性」语义由登记时点单次调用承载,其余挂点不得重复调本
    函数。

    采样点 = 选卡登记挂点(CwScreenInvestStrategy 确认落地,登记成功后
    紧随调用);记账 = 容器字段 ``gs.free_refresh_left`` write_logic 逻辑
    直写(2026-09-21 Field 化:免费次数升格容器字段,观察锚定/动作扣减/
    发放登记三写端同格;None 基 = 0 起算——开局无免费次数 = 机制真值,
    发放即首次落值)。额度 0 或 payload 无此字段(如 BattlefieldEffect
    族)= no-op(零 Field 行)。
    """
    n = int(getattr(getattr(spec, 'payload', None), 'free_refresh_burst', 0) or 0)
    if n <= 0:
        return
    _ev = f'effect_burst@{frame}' if frame else 'effect_burst'
    left = gs.free_refresh_left.value
    gs.write_logic(gs.free_refresh_left, (0 if left is None else int(left)) + n,
                   produced_by=(f'EffectLedgerBridge:'
                                f'{getattr(spec, "name", "") or "unknown"}'),
                   evidence=_ev, sig=_bridge_sig(gs))


def grant_effect_node_refresh_balance(gs: GameState, *,
                                      frame: str = '') -> None:
    """桥·per_node + 条件判定形态(每节点发放):节点边界一次,把全部在场
    条目声明的每节点免费刷新额度累加进免费刷新剩余次数(§3.3.5-§3.3.6)。
    载体两族:

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
    记账 = 容器字段 ``gs.free_refresh_left`` write_logic 逻辑直写(2026-09-21
    Field 化:免费次数升格容器字段,观察锚定/动作扣减/发放登记三写端同格;
    None 基 = 0 起算,开局无免费次数 = 机制真值)。静态活载体 = 双手狸
    (2/节点);条件活载体 = 本金充裕/+(50/10/3)。固定理财位面开始段
    (PLANE_START)不属本形态——该未建模腿的单一登记点 =
    ``cw_investments.STRATEGY_ECONOMY_PENDING_MODELING``,本桥不另记。
    """
    per_node = 0
    srcs: list[str] = []
    gold = gs.gold.value
    for e in gs.effects.entries:
        payload = e.spec.payload
        n_e = int(getattr(payload, 'free_refresh_per_node', 0) or 0)
        n_e += int(getattr(payload, 'free_refresh_on_node_enter', 0) or 0)
        above = int(getattr(payload, 'free_refresh_cond_gold_above', 0) or 0)
        step = int(getattr(payload, 'free_refresh_cond_gold_step', 0) or 0)
        cap = int(getattr(payload, 'free_refresh_cond_cap', 0) or 0)
        if above > 0 and step > 0 and cap > 0 and gold is not None:
            surplus = int(gold) - above
            if surplus > 0:
                n_e += min(surplus // step, cap)
        if n_e > 0:
            per_node += n_e
            srcs.append(e.spec.name)
    if per_node <= 0:
        return
    left = gs.free_refresh_left.value
    gs.write_logic(gs.free_refresh_left,
                   (0 if left is None else int(left)) + per_node,
                   produced_by=('EffectLedgerBridge:' + '+'.join(srcs))
                   if srcs else 'EffectLedgerBridge',
                   evidence=f'effect_node@{frame}' if frame else 'effect_node',
                   sig=_bridge_sig(gs))


def project_effect_capacity(gs: GameState) -> None:
    """桥·容量逻辑态直写(§3.2.5):按账本已登记容量时限声明回写备战席容量——
    激活期 capacity=N、条目到期移除后自动回默认 9。

    声明契约:容量条目的 payload 携带 ``capacity_limit: int``(激活期容量;
    注册表现零条目携带——§5.2 缺口登记「禁到注册表找规格」,载体归注册表
    建模批候选,声明字段名由此钉死,首批容量条目入册即自动生效)。多声明
    取 min(叠加收紧向)。当前零携带 → 直写恒等于默认 9(幂等 no-op,行为
    与接线前逐位一致)。

    采样点 = 备战帧观察后(cw_loop 备战分支,**每 pass 重锚**):观察链
    直产视图按默认容量建(bench_view 容量恒 9),会覆盖逻辑态直写值,故
    观察后须重锚;
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
#
# 语义声明:本域无换形层——观察读链(obs/cw_identity_obs.read_bench_view /
# read_deployed_rows)直接产容器形状,观察写门直写;占位件 kind 细分
# 权威源在读链识别期定(_bench_item_kind_by_slot)。历史换形值构造器
# 与紧缩表适配族随角色形中间载体停用删除(design §2.4)。


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

def detect_merge_upgrade(cur: Any, proj: Any) -> bool:
    """CwActionBuyCardParam 逻辑态直写是否发生 3 合 1 升星(§3.2.18 修法 a 触发判定;纯函数)。

    判据 = 同名角色直写后最高星级 > 直写前同名最高星——3 份合成是该
    签名的唯一来源(星级只经合成上升;买新卡不抬同名最高星)。合成域 =
    全场(bench+deployed,``cw_state._merge_bench`` 同口径)。级联合并
    (3×1★→2★→…)只看「有抬升」真值,层级数不影响本判定。

    条目身份读协议 = ``cw_merge_simulate._entry_identity``(容器单形状:
    bench 侧 BenchSlot / deployed 侧 Unit;非容器形状 = None fail-closed)。"""
    from sr_od.application.currency_war.kernel.cw_merge_simulate import (
        _entry_identity,
    )

    def _max_star(st: Any) -> dict[str, int]:
        best: dict[str, int] = {}
        for x in (list(getattr(st, 'bench', None) or [])
                  + list(getattr(st, 'deployed', None) or [])):
            ident = _entry_identity(x)
            if ident is None or not ident[0]:
                continue
            cid, s = ident
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
      承载旧 battle_done 外生行的「出节点」语义——接线点传
      ``battle_done:<node_type>``;hp/gold 等逐字段行不带注记);
    - 渠道签名(§3.2.1 ①类属 = 画面 op 类名):写端 = CwScreenBattleWait,
      签名必填;
    - **hp_after 写入序定案**(现场证据 = 本写端 + reconcile_hp 现役形态):
      本口 = hp 的战局唯一结算真值入口,无条件观察覆盖(以实际观察为准,仅调用方
      置信度门)。「读不到保旧沿用 last_hp_real」三层已停用
      (终态契约 §A;ADR 档案目录已删,原文 = git 历史
      docs/develop/currency_war/decisions/0282-hp-three-layers.md),读侧
      reconcile_hp 简化为「真值直传/开局先验/None 诚实未知」
      ——不存在沿用锚遮蔽结算真值的先后序问题。唯一能与本覆盖失配的 =
      逻辑态推算写端(宝物加血,write_logic(gs.hp)),该失配按两态制
      §2.3 = 推算 bug 暴露,非「保旧」。窗内消费(battle_wait killed
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
        # 收束 + 差值台账留存证据(机理见 settle_truth docstring)。
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
# (登记面设计件 = 商店黑板容器化方案 §2.1-2/§4-M1/M5)

#: 逻辑态公式语义源锁的登记面(设计件 §4-M5:直写域集/None 跳写清单/
#: executed 回执字段集/支持动作集随本锁登记;未登记写点 = 缺陷,禁扩静默):
#: - **域集封闭**(gold / bench / shop payload / xp 四域;CwActionCloseShopParam 的
#:   leave_screen 为同域通道形态);
#: - **支持动作集** = CwActionBuyCardParam / CwActionSellBenchParam / CwActionLevelUpShopParam(is-a CwActionLevelUpParam) /
#:   CwActionRefreshShopParam / CwActionCloseShopParam(商店单动作循环在产动作面;fields.md §4.2
#:   逐 op 行;CwActionSellDeployedParam/CwActionDeployMoveParam 不写逻辑态——等观察
#:   覆盖,申报 = 商店 visit 在产动作集外);
#: - **None 跳写清单**(域级独立跳写,禁缺省值参与计算):gold /
#:   xp+level(升级推进对,同进退——任一未读则推进对整体跳写);
#: - **executed 回执字段集** = bought_count(CwActionBuyCardParam 实购张数,满栏多买
#:   k 执行期确定)/ levelup_clicks(CwActionLevelUpShopParam 实际击数);
#:   回执缺字段 = 该动作本轮不写逻辑态(刷新上报不消费 executed——
#:   刷新费金账扣费费用单一源 = gs.shop_refresh_cost 容器直读,
#:   cw_action_report/refresh_shop 金账扣费腿)。
#: **扩面申报表**(扩面须逐批显式登记于本表,
#: 原「禁扩静默」条款由本表承接):
#: - 支持动作集扩:v2 动作族 CwActionSellDeployedParam / CwActionSwapDeployParam
#:   (语义源 = simulate 对应分支逐腿平移,由 test_gain_chain 直接校验
#:   卖/换上报 v2 族契约节钉住);
#:   CwActionDeployMoveParam 不入(围栏部署 = 结算期代理,obs 通道申报对齐);
#: - 域集扩:deployed(原 front_row/back_row 两紧凑行域合并为单字段完整槽位表;v2 腿与合成连锁全场域写回)、
#:   board(**派生量**:行写端挂钩 ``_resync_board_delta``
#:   自动重算,禁独立手写;单一源见该方法注)、equips(卖出回收腿);
#: - 域集扩(2026-09-18):level(CwActionLevelUpShopParam 升档直写;语义源 = prep 腿
#:   买经验上报(report_action_level_up_param)同款,推进单一源 =
#:   ``cw_economy.xp_apply_clicks`` 跨级连跳含内)。依据 = 等级滞留使
#:   下一击按旧级重算(花金零等级推进),而等级 = 席位 cap 解锁地板
#:   (``max_units_of`` 经读口跟随,消费位零改动)。域级跳写对 =
#:   (level, xp) 同进退:任一未读则推进对整体跳写,禁缺省 1 参与
#:   推进计算。
#: - 扩面依据:动作逻辑态直写单一源 = 上报函数族(裁定 A:
#:   logic_action 族,与 live 同函数同渠道),域覆盖须对齐其字段转移
#:   全集。
SHOP_PROJECTION_DOMAINS: tuple[str, ...] = (
    'gold', 'bench', 'shop', 'xp', 'level',
    'deployed', 'board', 'equips')


@dataclass(frozen=True)
class LogicOutcome:
    """动作状态应用的显式结果出参(转移函数单源化;详设 §3
    「转移结果通道」)。

    拒绝判定由腿内既有判定填充(stale_proposal / 满栏非合成拒买 /
    同名拒上),
    拒绝 = applied=False + reason + **零容器写**;拒绝结论唯一出口 =
    本出参(transition 事件广播通道已停用),
    调用侧禁自判拒绝(§2.1 单一源红线)。live 调用点忽略本出参
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
    #: 动作后果声明(转移类动作 ``applied=True`` 出口必构造;拒绝/未发出
    #: = None,对齐现行「applied=False 零广播」语义;schema 与消费面 =
    #: kernel/cw_world_decl.py,构造义务契约 = 动作后果声明化迭代总纲
    #: design.md §2.2 契约 2)。缺省 None = 既有全量构造点零改动兼容。
    world_decl: WorldDecl | None = None


@dataclass(frozen=True)
class ShopActionExecuted:
    """商店动作执行落地门回执(上报函数族 executed 形参)。

    执行期决定量以落地门回执为准,禁按动作对象预估(设计件 §2.1-2):
    CwActionBuyCardParam 满栏多买 k 张(CwActionLevelUpParam 满栏例外一击多张)与 CwActionLevelUpShopParam
    实际击数(循环点击至 level+1)均由执行侧回执;缺字段(None)= 该
    动作本轮不写逻辑态,等观察覆盖。

    **Optional 语义(详设 §3 修订)**:executed 整体可缺省
    (None = 理想执行)——live 与 sim 同一段动作 op 代码传执行回执
    (bought_count 由动作 op 现算喂入;参数化不变);None = 自算执行期
    决定量(CwActionBuyCardParam k 自算,满栏合成买 k 从
    :func:`_apply_full_bench_merge_buy` 应用面出)。executed 只覆盖 k 等
    决定量**来源**,不覆盖应用面位置——合成连锁/满栏合成买的应用两路径
    同在转移函数内(单源本义)。executed 与自算值的关系核对归调用方
    守卫面(本函数不判)。

    (``refresh_paid`` 字段已退役:刷新费用单一源 = 容器
    ``gs.shop_refresh_cost`` 直读——刷新上报函数扣费腿,喂参第二来源
    已废,见 cw_action_report/refresh_shop 金账扣费腿。)
    """

    #: CwActionBuyCardParam 实购张数(满栏多买 k;单一源 = 执行侧 merge_buy_k 计数)
    bought_count: int | None = None
    #: CwActionLevelUpShopParam 实际击数(单动作形态恒 1;腾席链多击以回执为准)
    levelup_clicks: int | None = None


# (旧席位同步聚合口的惰性转发已停用:词表侧同步
#  聚合同批停用,买牌上报升星检测改用自身主工作副本的 before/after
#  交叉核对。)


def bench_view_of_working(slots: list, capacity_view=None) -> BenchView:
    """工作槽表(list[BenchSlot | None],merge/落位计算的工作副本,可能含
    None 洞)→ BenchView 记录形状(§3.2.5):None → ``kind='empty'`` 归一 +
    右侧 pad 到容量。容器写侧构造单一源(P1;占位件 kind 原样透传——
    工作表元素即容器 BenchSlot,零中间形)。``capacity_view`` = BenchView
    (随原观察容量)或 int 容量;缺省 = 默认容量 9。"""
    cap = (capacity_view.capacity
           if hasattr(capacity_view, 'capacity')
           else (capacity_view if isinstance(capacity_view, int) else None))
    cap = cap or BENCH_CAPACITY_DEFAULT
    out: list[BenchSlot] = [
        s if s is not None else BenchSlot(kind='empty') for s in slots]
    while len(out) < cap:
        out.append(BenchSlot(kind='empty'))
    return BenchView(slots=out, capacity=cap)


# ============================================================ 局终行写口(§3.6.1 runs 并入)

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
    """局终收束写口(局终域 **唯一写点**,渠道③ logic_hook 家族、
    actor=MatchClose;§3.6.1 runs 并入载体,表 3-3 局终域③格)

    - **同版本原子**:终局类型 + 时点版本 id + 版本戳(code_commit/
      registry_fingerprint,模块级常量) + 终局快照 + 段级时长一次逻辑
      写入装配成单笔 :class:`MatchFinal` 载荷,经一次 ``_swap`` 落一行
      (行内全量 state = 终局快照,字段来源注记随快照行自带);
    - ``cw4_counters`` = 策略行为观测计数局终聚合(键并入载体,
     ;载体语义/None 与空 dict 分型见 :class:`MatchFinal` 字段
      注)。快照副本由调用方在收束时点现读传入,本写口不触策略容器;
    - **写前查重 = 段内幂等**(§3.6.2 终局防重读门 G12 并入,运行时控制面
      读口豁免类,载体 = 内存字段现读):本段已有终局行 → no-op 返 False;
    - **异常终局 = 补写形态**(G8):``backfilled=True`` 时版本 id 照常分配
      (写入口正常路径),行载荷 final_type='abnormal' + backfilled 位 +
      行注记缺省 'recovered' 暴露(判读可辨真伪)。**适用范围 = 段内补写**
      (哨兵收束兜底/在线路径异常形态,行挂当前段);启动扫描的**历史段**
      补写禁走本口——本口 run_id 取供给槽现读,历史段行必被挂到现读段键
      (错归属),须走专用装配通道(读流→构造→按显式 run_id 落行,遥测
      正本 §3.2.2 规则 6②;先例 = recover_dangling_run_summaries,挂接线
      批批首);
    - duration_s 缺省 = 段级时长自算(容器创建 → 本调用,段级;恢复局跨段
      = 各段各行,聚合归判读侧);
    - 落盘语义:行落盘受 sink 在场/run_id 在场覆盖(缺实例/局外 = 版本照耗、
      Field 照写、行不外送——与全部写入口一致);**监听器 = 写口受理成功
      (过封闭集与段内幂等门)即触发**,行落盘与否另以 sink/run_id 在场为准
      (缺实例/局外 = 行不落而事件照发,事件 run_id='' 形态)——消费方按此
      自滤;监听 best-effort,异常不毒化终局流转。

    返回 True = 本调用落了终局行;False = 本段已收束(幂等跳过)。
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
        note = 'recovered'   # G8 补写行暴露(判读按注记分型,防混计)
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
    """容器取口(终态契约 §2.6/ ops 桶):优先 ``ctx.cw_match.gs`` 持有
    引用;kernel fallback(:func:`game_state_of`,桶 3)**暂留至 3.5 注入化
    时统一删除**。值同一实例(持有引用与旁表单例同对象),行为零变化。
    ctx 无 match / match 无 gs(桩面)→ fallback 兜底,调用方零改。
    """
    _m = getattr(ctx, 'cw_match', None)
    if _m is not None and getattr(_m, 'gs', None) is not None:
        return _m.gs
    return game_state_of(session)


def bind_session_container(session: object, gs: GameState) -> None:
    """显式绑定局容器单例(装配口;sim 统一迭代 3.4 运行器缝)。

    sim 后端(SimBackend)组合持有世界容器,流程侧两条取口——
    :func:`gs_of_ctx`(优先 ``ctx.cw_match.gs`` 持有引用)与
    :func:`game_state_from_ctx` → :func:`game_state_of`(session 旁表)
    ——必须同一实例,否则动作上报写进旁表懒建的「第二容器」而策略器
    读后端容器,世界分裂。本口把后端容器注册为该 session 的单例真值,
    两条取口同源。生产实机路径不经本口(establish_new_match 漏斗建支
    即注册);装配方(运行器/测试)负责 session 生命周期同弃。

    重复绑定不同容器 = 装配错误,响亮(绑定后单例取口不再懒建,静默
    覆盖会把已运行的世界换掉)。
    """
    existing = _GS_BY_SESSION.get(session)
    if existing is not None and existing is not gs:
        raise RuntimeError(
            '局容器单例重复绑定且实例不同(装配错误;禁静默换世界)')
    _GS_BY_SESSION[session] = gs


def game_state_of(session: object, *,
                  run_id_provider: Callable[[], str] | None = None) -> GameState:
    """GameState 单例访问口(session 旁表;弱引用表 + 桩面兜底)。

    - session = 局身份:新 session 对象 = 新局 = 新 GameState(§1 每局新建);
    - None → 一次性空载体(不缓存——None 的 id 恒定,缓存即跨调用串染);
    - 裸 session(测试/sim 桩)→ 惰性建并挂对象自身属性(生命周期随对象);
    - run_id_provider = 局容器单例建立时点的遥测装配注入(用户裁定
      2026-09-15:装配 = game state 职责,触发只钉本建立点;经
      :func:`_establish_singleton_journal`,GameState 构造器零装配逻辑),
      仅覆盖**新建**时点(已存在直读不触装配——幂等兜底对已装配进程本就
      零成本);session=None 一次性空载体(局外,不缓存)不装配——装配是
      进程级副作用,不属一次性视图。缺省 None = 不装配(sim/测试/局外
      防御视图构造口径;生产注入漏斗 = establish_new_match)。
    - 局容器单例冷建即含开局种子底座(:func:`seed_opening_state`,A 类
      字段随机态通道;None 一次性支与直构容器不种)。
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
            seed_opening_state(gs)   # 缓存单例冷建即含开局种子底座
            try:
                setattr(session, _GS_ATTR, gs)
            except (AttributeError, TypeError):
                _GS_BY_SESSION_ID[id(session)] = gs
        return gs
    if gs is None:
        _establish_singleton_journal(run_id_provider)
        gs = GameState(schema_version=GAME_STATE_SCHEMA_VERSION)
        seed_opening_state(gs)   # 缓存单例冷建即含开局种子底座
        _GS_BY_SESSION[session] = gs
    return gs


# ============================================================ 开局种子底座与锚定标志

#: 种子写入者身份(journal/台账过滤键单一源;判读与测试按本 actor 过滤
#: 种子行)。
_SEED_ACTOR: str = 'GsOpeningSeed'
#: 种子写入 evidence 注记单一源。
_SEED_EVIDENCE: str = 'seed:opening'
#: 种子写入渠道签名单一构造(logic_action 族恒 compute)。
_SEED_SIG: ChannelSig = ChannelSig(family='logic_action', actor=_SEED_ACTOR,
                                   screen='', mode='compute')


def seed_opening_state(gs: GameState) -> None:
    """冷建局容器开局种子底座(唯一调用点 = :func:`game_state_of` 两个缓存
    单例建支;session=None 一次性支与直构 :class:`GameState` 不种——测试/
    sim 直构域依赖未写形态)。

    A 类字段(阵容/经济/溢出/环境/刷新计数)冷建即设开局初值,经
    :meth:`GameState.write_logic_rand` 落「随机态」通道——确定值外壳、未经
    观察验证:后续首观察直接覆盖,差异只落 ``logic_rand_outcome`` 台账行
    (不进失配三分流);决策可信位消费不认(先例 = hp 可信位只认
    observation/carried)。种子值 = 容器建立时点的开局真值或基线,逐字段
    语义见各字段注释「开局种子底座」;B/C 类字段(None 为设计语义或无
    观察源)一个不种。写序契约:行域(deployed)先写,board
    派生行经行域挂钩(:meth:`GameState._resync_board_delta`)随动自动落
    ——种子空视图零差且板未读无派生基座,种子面不产 board 行,禁双写。
    """
    # 常量引用单一源(函数级懒 import 防模块环,同本模块惯例)
    from sr_od.application.currency_war.kernel.cw_economy import (
        REFRESH_COST_BASE,
        XP_TO_NEXT_LEVEL,
    )
    from sr_od.application.currency_war.kernel.cw_opening_hp import (
        OPENING_HP_BASE,
    )
    sig = _SEED_SIG

    def _seed(target: Field, value: Any) -> None:
        gs.write_logic_rand(target, value, produced_by=_SEED_ACTOR,
                            evidence=_SEED_EVIDENCE, sig=sig)

    # —— 行域先写(board 派生行随动自动落)——
    _seed(gs.deployed, DeployedView(
        front_slots=[None] * DEPLOYED_FRONT_CAPACITY_DEFAULT,
        back_slots=[None] * DEPLOYED_BACK_CAPACITY_DEFAULT))
    # —— 阵容/装备/晶矿(空底座为建立时点真值;补给在 1-1 进入时点送达,
    # 内容待实机观察,合并效应归观察覆盖)——
    _seed(gs.bench, BenchView(
        slots=[BenchSlot(kind='empty')] * BENCH_CAPACITY_DEFAULT,
        capacity=BENCH_CAPACITY_DEFAULT))
    _seed(gs.equips, [])
    _seed(gs.occupied_equips, {})
    _seed(gs.spheres, OreSight())
    # 晶矿附着奖励与声明通道三域(空底座;沿 pending_item_grants 种子族
    # 先例——域值恒非 None,幂等守卫 membership 判定与挂接入口合并写零
    # None 防御)。
    _seed(gs.ore_rewards, {})
    _seed(gs.ore_declared_pending, ())
    _seed(gs.ore_declared_done, ())
    # 环境条件发放已发标记(空底座,同上种子族先例;开局未发任何条件
    # 发放,「本局首次」守卫的初始真值 = 空集)
    _seed(gs.env_grants_done, ())
    # (node_seq_by_plane 不种:B/C 类字段契约——None = 未注册态是设计
    # 语义,设计「Field 缺省 None」,Field 声明缺省即开局真值,
    # seed_opening_state「B/C 类字段一个不种」同规。)
    # —— 经济与成长(gold=3 对齐 sim 开局模型 M01 的 OPENING_GOLD;
    # level=3 与升级表键一致,deploy_cap=level+财富宝钻数、开局宝钻 0;
    # xp 需求查升级表单一源;hp 取遥测实证基线常量)——
    _seed(gs.gold, 3)
    _seed(gs.level, 3)
    _seed(gs.xp, (0, XP_TO_NEXT_LEVEL[3]))
    _seed(gs.hp, OPENING_HP_BASE)
    _seed(gs.streak, 0)
    _seed(gs.back_layout, 6)
    _seed(gs.deploy_cap, 3)
    # —— 溢出/环境/持卡/刷新计数(开局真值)——
    _seed(gs.overflow_warning, False)
    _seed(gs.overflow_card, '')
    _seed(gs.active_env, '')
    _seed(gs.active_strategies, [])
    _seed(gs.unlocked_experts, ())
    _seed(gs.pending_item_grants, [])
    _seed(gs.enemy_affixes, [])
    _seed(gs.shop_refresh_cost, REFRESH_COST_BASE)
    _seed(gs.prev_node_spent, False)
    _seed(gs.strategy_refresh_left, {})


def prep_anchored_of(session: object) -> bool:
    """锚定标志读口(经 :func:`game_state_of` 解析,缺省 False;局外一次性
    容器每调新建恒 False)。生产唯一置位写点 = reconcile_tracking 的
    tracked_account_observed=True 写回成功点(两标志同点置位);测试/直构域
    置标志专口 = 直接赋值 ``gs.prep_anchored = True``(声明为测试/直构域
    专用,生产禁走)。"""
    return bool(game_state_of(session).prep_anchored)


def anchor_aware_write(gs: GameState, rand: bool) -> Callable[..., None]:
    """锚定感知写通道择道口(通道规则「未锚定 → 随机态」的公开单一选择
    口;获得链与效果账本桥等容器逻辑写端同源消费,禁散写
    ``write_logic_rand if rand`` 形态;住本模块防 kernel 内循环 import)。

    语义:形参 ``rand=True``(采样语义)或容器未锚定(:func:`prep_anchored_of`
    为 False,即开局种子底座窗口)→ ``write_logic_rand``——未锚定期的
    逻辑落账是「未验证推算」,走随机态让首观察静默覆盖(差异只落
    ``logic_rand_outcome`` 台账行,不进失配三分流);锚定后按形参
    (rand=False → ``write_logic`` 确定面,失配网原样生效)。入参 gs 直接
    可用(:func:`game_state_of` 对 GameState 本体直通);直构容器视同
    未锚定。
    """
    if rand or not prep_anchored_of(gs):
        return gs.write_logic_rand
    return gs.write_logic


def tracked_unobserved(session: object) -> bool:
    """tracked 主账是否处于未观察态(判定单一源;策略商店门与执行侧
    跳过留痕/熔断消费)。

    判据 = 容器字段 :attr:`GameState.tracked_account_observed` 显式 False
    (接管/重置/账失效写);None(从未写,缺省可信)与 True(已锚定)均
    为已观察。session 经容器读口解析,字段从未写(缺省)不视为未观察。
    """
    return game_state_of(session).tracked_account_observed.value is False


# ============================================================ GameState 单例


# (席位主账簿记组已停用删除:主域
#  bench/deployed 席位视图成为唯一账(3.1 合卷提供完整槽位表,槽位
#  直址 = 子表下标),第二账存在理由消失;原消费面去向 = 动作随动同步
#  腿全删 / 对账基线改主域派生 / 商店守卫 expected 侧读主域。)


class NodeBooks:
    """节点序列探针簿记组(容器内独立宿主组;非 Field,不进快照流水;
    终态契约 §A′ 并入:写读经本组单一源)。

    [索引定义] plane_node_table = 开局帧实读槽序表(list[str],当前位面
    槽序,位面内恒定);plane_node_table_plane = 表归属位面号(1-based,
    每位面首帧重写时更新);plane_lengths_seen = 已揭晓位面长度序列
    (下标 i = 第 i+1 位面,进表即自适应)。取值时机 = cw_screen_prep
    每位面首帧采集写入(store_plane_table,唯一写端);读端 =
    kernel/cw_plane_table(经 game_state_of 桥)+ predicates.py
    (mandate_v1 前窗谓词直读)+ cw_screen_battle_wait.py(L681
    前置读者)。局级生命周期(新局新容器 = 天然清零)。
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
    (prep_row)/ 过渡屏观察段(transition_row / transition_snapshot)。
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
    #: ``cw_node_reader.NodeSlot.node_type`` 同词汇表;
    #: None = 该位次未识别占位,合并时被后续非 None 读数覆盖)。
    #: 取值时机:写入端每次整行重读时快照(见各写入端);读端 = 备战帧查
    #: ``seq[round_num - 1]``。
    #: 写入端:①位面详情采集(CwScreenPlaneIntel 详情条源,boss 位按
    #: 「首领 = 位面最后节点」位置先验回填);
    #: ②投资环境选择完成后重读备战节点行(CwScreenInvestEnv,变异窗后的权威刷新)。
    seq_by_plane: dict[int, list[str | None]] = field(default_factory=dict)

    #: 每序列的写入来源('plane_detail' = 位面详情采集 / 'prep_row' = 备战节点行),
    #: 判读侧区分表值的采集通道用(位面详情=彩色渲染态全量,备战行=含 past 遮挡)。
    seq_source: dict[int, str] = field(default_factory=dict)

    #: 位面 → 位面详情底部明文「敌人难度 N」参考值。**只存参考**——生产难度
    #: 主源 = 备战画面敌方难度读数两级管线,本字段供离线交叉核对/缺口排查。
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
    # [索引定义] deployed = 上阵统一槽位视图(§3.2.3/§3.2.4 合卷):front_slots[i] = 前排物理槽 i+1(定长 4)/ back_slots[j] = 后排
    # 物理槽 j+1(动态容量 6-9 随布局扩容);空槽 = None 显式;一次写 =
    # 一次完整语义变更(换排/替换/空槽上场均单写);开局种子底座冷建即
    # 4+6 全空槽视图,首观察覆盖。
    deployed: Field[DeployedView] = field(default_factory=Field)
    bench: Field[BenchView] = field(default_factory=Field)       # 备战席统一槽位视图(§3.2.5;capacity 随效果改写;开局种子底座冷建即 9 空槽空视图——建立时点确无手牌,开局补给观察覆盖)
    back_layout: Field[int] = field(default_factory=Field)       # 后台格数(值域 6-9:平常 6,宝钻/召唤物扩展,上限 9;6/7/8/9 四档均已交互建档——9 档凭据=cw_back_layout._LAYOUT_PREFIX 与 screen_info 后排9槽-1..9;>9 域外按 8 格超集运行+evidence superset 标记,§3.2.7;开局种子底座=6 平常基线)
    # [索引定义] tracked_account_observed = 主域席位账(bench+deployed 两
    # 面,同帧锚定)的观察锚状态(用户裁定「观察状态落 game state 字段,
    # 策略消费只走 game state」;三态语义:None = 从未写 = 缺省可信——正常
    # 新局 0 件即屏幕真值,且不经失效事件的 sim/离线入口不受误伤;False =
    # 显式失效(接管/重置/账失效)后未锚定,值不可消费;True = 备战环
    # heavy 观察(observe_full → reconcile_tracking)屏幕真值对账成功 =
    # 已锚定)。取值时机 = 事件驱动(非逐帧)。写入端:False = cw_loop
    # ._invalidate_tracked_on_takeover(接管检测确认点;重置/账失效类事件同口写);
    # True = kernel reconcile_tracking 的 bench 侧对账成功点
    #(唯一锚定写端;bench 读失败/双空读守卫均不写 = 保持
    # 未观察)。消费面:策略商店门(flow.decide_shop_action,未观察 →
    # CwActionCloseShopParam 返回主循环走备战重锚定;判定单一源 = 本模块
    # tracked_unobserved)。锚定语义重定义(tracked
    # 第二账停用)——锚 = 主域(bench/deployed 席位视图)已按屏幕真值
    # 对账;观察边界对账唯一发生点不变、两态制不变(prep.md §3/§6)。
    tracked_account_observed: Field[bool] = field(default_factory=Field)

    # —— 经济与成长 ——
    gold: Field[int] = field(default_factory=Field)              # None=不可读(§3.2.9;开局种子底座=开局基线值,种子后恒有值,该 None 档生产死化)
    level: Field[int] = field(default_factory=Field)             # 等级(§3.2.10;启发式兜底值禁入——非真读走 carried;开局种子底座=开局基线级)
    xp: Field[tuple[int, int]] = field(default_factory=Field)    # (当前级已攒,升下一级所需)(§3.2.10;同文本两分量成对存;开局种子底座=(0,当前级升级所需))
    streak: Field[int] = field(default_factory=Field)            # 带符号:正=连胜/负=连败(§3.2.12;开局种子底座=0)
    # [索引定义] pending_loss = 败态待清项(上一败掉的战斗类节点引用,单项待清)。
    # 坐标系 = LostNodeRef(plane 1 基位面, round_num 位面内 1 基轮, node_type
    # 节点词表);取值时机 = 战斗结算失败腿写入、轮首收入败补支(U04 口径)
    # 消费后清回 None——非 supply/reward 节点消费,败态跨轮保留至下一战斗轮
    # (kernel round_start_income 分支序)。None = 无待办。写端(sim 世界) =
    # sim/cw_sim_backend 结算失败腿;实机可观察(结算屏败局)影响玩法(败补金),
    # 按容器字段判据入容器。
    pending_loss: Field[LostNodeRef | None] = field(default_factory=Field)
    hp: Field[int] = field(default_factory=Field)                # 写入闸 §3.2.13:非真读帧不经 observe(§8.8 假值防线;开局种子底座=实证基线值,三写端时序 种子→先验→真读)
    level_up_cost: Field[int] = field(default_factory=Field)     # 单击买经验价(§3.2.11;None=未读到禁兜底)
    # [索引定义] deploy_cap = 部署容量识别真值(= level + 财富宝钻数,可叠加)。
    # 坐标系 = 「X/Y」指示的 Y 人数口径;取值时机 = 备战帧观察期快照(
    # 双帧一致采信门输出,写端 = cw_observation.read_game_state spec 门
    # 'deploy_cap' 键,防抖核 = cw_observation._debounce_cap 单一源)。
    #  定案入容器(W5-透传域建模方案 §2.3;设计正本 §3.2.7「现场实时
    # 读值豁免」已登记前提已被推翻,正本更新义务见方案稿 §2.3):与 back_layout 双存
    # 属 §8.8 已登记例外形态(识别口径 vs 推导口径各有消费面,先例 = board、
    # level_up_cost)——cap=识别源(采信门输出),back_layout=三信号裁决结果
    # (cw_back_layout);理论关系 back_layout ≈ 6+(cap−level) 仅域内成立,
    # 域外态(>9)back_layout 是 8 格超集,反推会把近似当真值,故不派生改双存。
    # 两域冲突走缺陷台账,不互改。
    deploy_cap: Field[int] = field(default_factory=Field)        # 开局种子底座=与 level 种子一致(= level + 财富宝钻数,开局宝钻 0);识别真值观察覆盖

    # —— 局级事实 ——
    selected_difficulty: Field[str] = field(default_factory=Field)   # 职级,开局写定恒稳(§3.1.1)
    game_mode: Field[str] = field(default_factory=Field)             # 对局类型:标准/超频博弈(§3.1.2;两屏无建档,接线前补档)
    enemy_difficulty: Field[int] = field(default_factory=Field)      # 非单调(§3.2.14)

    # —— 遭遇选档观测面(E-2 平级新结构;非 Settlement 域字段,准入注释见该域)——
    # 结算观测环:产结算屏节点的 RoundOutcome 消费子集,深度 10,同场去重合并,
    # 生命周期 = 局(开局清空;relaunch 残留行由写入端 residual 排除)。判据与
    # 经验层读源单一源(遭遇选档迭代设计 §8)。
    settlement_ring: SettlementRing = field(default_factory=SettlementRing)
    # 遭遇经验表:本局全量遭遇行(其五/六 Δ 无源档的经验正证据通道;跨局
    # 持久化待办另行立项)。
    encounter_log: EncounterLog = field(default_factory=EncounterLog)
    plane_bosses: Field[list[str | None]] = field(default_factory=Field)  # 三位面 boss 名,保位 3 槽;None=简报源未读得(实采源恒全识别,识别失败响亮暴露不留 None)
    active_env: Field[str | None] = field(default_factory=Field)     # 已选投资环境(§3.2.20/§3.4.3;开局种子底座=''=未选择)
    enemy_affixes: Field[list[str]] = field(default_factory=Field)   # 当前词缀名单(§3.1.3;≠投资环境;开局种子底座=[],简报/接管位面详情覆写)
    active_strategies: Field[list[str]] = field(default_factory=Field)   # 持有投资策略名单(§3.4.4;品质锚挂建模批;开局种子底座=[]未持卡)
    unlocked_experts: Field[tuple[str, ...]] = field(default_factory=Field)  # 本局已解锁入池专家顾问规范名(economy.md §1:专家初始不参与普通商店招募,经投资环境/投资策略/专家邀请函等通道解锁后本局加入商店;池派生消费 = cw_pool 按名并入 EXPERT_COPIES_ASSUMED 副本)。开局种子底座=()未解锁;只增不减(现役解锁通道无回收语义)。写入端 = 获得链 advisor 道(cw_gain_chain.on_env_gained/on_strategy_gained)+ 装备通道(on_equipment_gained 分身墨镜族);成员闭集闸 = cw_chars.assert_expert_names
    # [索引定义] pending_item_grants = 已登记、未到点发放的定时道具队列(环境
    # 定时发放通道,迭代 2026-09-24-scheduled-env-gifts)。entry 形 =
    # {'env': 登记来源环境名, 'plane': 位面(1 基), 'round_num': 位面内轮
    # (1 基,与 node 域 plane/round_num 同坐标系), 'item': 道具名};
    # plane/round_num = 入队期从登记节点键 '位-轮' 解析好的目标节点,取值时机 =
    # 入队期快照(解析失败形态由登记表 import 校验拒收,容器内恒合法)。
    # 写端声明:唯一逻辑写端 = 获得链(on_env_gained 登记入队 /
    # discharge_due_item_grants 到点消费回写),无观察写端——队列是卡文推算
    # 知识,游戏 UI 无「待发放列表」可读;实机局不消费(队列登记后保持原样,
    # 备战真值归观察覆盖)。开局种子底座 = [](A 类)。
    pending_item_grants: Field[list[dict]] = field(default_factory=Field)
    board: Field[dict[str, int]] = field(default_factory=Field)      # 上阵羁绊计数(§3.2.6;下档阈值=派生不存储;开局种子底座不直写,随行域空行种子派生,禁双写)
    shop_refresh_cost: Field[int] = field(default_factory=Field)     # 刷新费,动态(§3.3.4/现场 OCR;免费帧不写,None≠0;开局种子底座=刷新基价)
    # [字段定义] shop_locked = 整店锁(锁定后节点切换不自动全刷)。取值时机 =
    # 恒稳局级事实;sim 写端 = 恒 False(裁定:动作词表无锁通道,首版恒
    # 解锁,字段先行占位;None 视读 = 未锁)。实机写端待实机补档(锁图标观察)。
    shop_locked: Field[bool] = field(default_factory=Field)
    # [字段定义] diamond_count = 宝钻计数(UI 可见局内货币;补给带钻选项等
    # 通道获取)。取值时机 = 获取事件后累计;None = 未观察。sim 写端 =
    # sim/cw_sim_backend 补给带钻腿;实机写端待实机补档。
    diamond_count: Field[int] = field(default_factory=Field)

    # (商店刷新计数组口径(2026-09-21 Field 化):免费刷新剩余次数升格容器
    #  字段 free_refresh_left(声明见下方 §1.4 家族块);付费/全量两计数留
    #  效果账本 ActiveEffectInventory 累计。。)
    prev_node_spent: Field[bool] = field(default_factory=Field)      # 上节点是否花费(§3.3.9;存款回报条件输入,观察需求;开局种子底座=False 开局无花费)

    # —— 节点屏刷新计数组(§3.4.1-§3.4.4;渠道② logic_action,写入=仅逻辑)——
    # 写端现状:**全域 = 剩余语义**(用户裁定 2026-09-21:game
    # state 就记录画面可观察的剩余次数——屏上数字即真值,观察写端逐访问
    # 覆盖,刷新后下帧观察直接给新真值,零动作侧记账):观察写端 = 各屏观察
    # report 摄入 OCR 读数(读缺跳写,值留观察覆盖)。
    encounter_refresh_left: Field[int] = field(default_factory=Field)     # 遭遇刷新剩余次数(§3.4.1;屏上「剩余次数：N」观察真值,None=未观察;观察写端 = report_screen_encounter_obs 摄入,读缺跳写、逐访问覆盖,无开局种子;sim 无遭遇刷新执行面 = 无 sim 写端;原「已用」计数与 per-visit 位随剩余语义化停用,闸消费与写端全迁本字段)
    supply_refresh_left: Field[int] = field(default_factory=Field)       # 补给刷新剩余次数(§3.4.2;屏上「剩余次数：N」观察真值,None=未观察;观察写端 = report_screen_supply_node_obs 摄入,读缺跳写、逐访问覆盖,无开局种子;sim 写端 = cw_sim_backend 补给节点入口初始 left 与刷新递减;原「已用」计数字段随剩余语义化停用,闸消费与写端全迁本字段)
    env_refresh_left: Field[int] = field(default_factory=Field)          # 投资环境刷新剩余次数(§3.4.3;屏上「剩余次数：N」观察真值;观察写端 = report_screen_invest_env_obs 摄入,读缺跳写;原 env_refresh_used「已用」字段随剩余语义化改名停用——零写端已登记,改名零消费断链)
    strategy_refresh_left: Field[dict[str, int]] = field(default_factory=Field)  # 投资策略逐卡刷新剩余次数(§3.4.4;键 = 注册表规范卡名 normalize_invest_name 归一后——效果注册表 STRATEGY_EFFECTS 即以规范名为键,观察写端 OCR 名经同一归一函数入键,免双坐标系换算;观察写端 = report_screen_invest_strategy_obs 摄入「刷新次数N」读数,读缺键跳写、已观察键覆盖)。原 strategy_refresh_used「已用」随剩余语义化改名停用(其注释自declared「on_outcome 发出型钩子」写端与全仓零写端现状矛盾,改名时一并清除;闸消费口径 = 剩余 ≤0 = 尽;开局种子底座={} 无持卡,与键粒度增量写端协同)

    # (商店免费刷新剩余次数 = op-layer §1.4 ``*_refresh_left`` 剩余语义
    #  家族的商店域接入(用户裁定 2026-09-21 Field 化:免费刷新次数是画面
    #  可观察的剩余次数,自效果账本 int 升格容器字段——「观察锚定 + 动作
    #  扣减 + 发放登记」三写端同格)。三写端:①观察锚定 = 入口观察漏斗
    #  商店开态段刷新钮三态(免费态锚次数/付费域锚 0/整帧判不出跳写,
    #  obs/cw_observation);②动作扣减 = 刷新上报函数
    #  report_action_refresh_shop_param(未观察 None = 保守按付费不扣减
    #  ——次数是记账面非决策闸);③发放登记 = 两桥
    #  apply_effect_burst_grant / grant_effect_node_refresh_balance
    #  (None 基 = 0 起算,开局无免费次数 = 机制真值)。失配对账 = Field
    #  机制白送(observe 覆盖 logic 失配走既有 cw_mismatch_policy 失配告警,
    #  零手写台账)。)
    free_refresh_left: Field[int] = field(default_factory=Field)         # 商店免费刷新剩余次数(屏上「免费刷新 N」观察真值,None=未观察保守按付费)

    # —— 轮内新鲜度账(「本轮已买」半边;渠道② logic_action,写入=仅逻辑)——
    # [索引定义] 值形状 = {'phase': (plane, round_num) | None,
    # 'names': list[str]}:names = 动作发出点买入时逐名写入的轮内新鲜买入名集
    # (dict 内集合已按容器 JSON 序列化安全形存 list,record_fresh_buy 内部
    # 转形,读端成员判断在个位数量级无性能面);phase 失配 = 跨轮整体作废
    #(读取零销账,无逐名生命周期面);None = 本局未登记。写端 = shop.
    # _emit_buy 全部 CwActionBuyCardParam 动作发出点,经
    # cw_deploy_logic.record_fresh_buy 单口(渠道②动作上报,actor =
    # 'CwDeployLogic');读端 =
    # cw_deploy_logic.fresh_buys_of(换出守卫)+ fresh_buys_sell_face
    #(L1 卖侧标志,fail-closed;写读单口不变)。
    round_fresh_buys: Field[dict | None] = field(default_factory=Field)

    # —— 持久账本组(跨画面保留)——
    # ⚠️ 免战牌不在本组(§8.6-3 载体归一,迁移批次二):激活态+剩余次数
    # 正本 = effect_inventory.remaining_uses(§5.1,ActiveEffect.remaining_
    # uses「次数类余量(免战牌×2 等)」,同型躺平/节省工位;批次一骨架的
    # skip_battle_active/remaining 两 Field 已按正本归一移除,消费走
    # gs.effects 查询)。
    equips: Field[list[str]] = field(default_factory=Field)          # 装备库存(§3.2.15;开局种子底座=[] 开局真值)
    # [索引定义] occupied_equips:已穿装备位置(装备域姊妹面,纯观察
    # 记录面——决策面零消费)。键坐标系 =
    # 'front:1'/'back:2' 形态字符串(row ∈ front|back,slot = 画面物理槽位
    # 1-based,前排 1-4/后排 1-选档 N,与机械动作参数同域——坐标系正本 =
    # cw_prep_actions.PrepObservation.occupied_equips 声明;tuple 键 JSON
    # 序列化不安全故字符串化);值 = 件名列表。取值时机 = 备战 heavy 观察
    # 每入口帧实读覆盖(两态制,以实际观察为准);写入端单一源 = CwScreenPrep 观察
    # 写端(与 equips 同点同环);未观察(None) = 识别域未就绪,无决策面
    # 后果——M7 装备分配容量不读本域,已穿槽位自 deployed 视图 unit.equips
    # 逻辑推导(键坐标系/空槽不入表与本观察面逐位同形,与 kernel 穿戴上限
    # 同基,自旋结构性消灭),本域保留为观察审计载体(observation_only)。
    occupied_equips: Field[dict[str, list[str]]] = field(default_factory=Field)  # 开局种子底座={} 开局真值(无穿戴),观察覆盖
    # ⚠️ consumables = 死字段:现役零读端零写端(工具件实住 equips,
    # 工具上报记账载体 = equips 合并写,不入本字段),fields.md §3.2.16
    # 申报与现实不符——字段级修复(停用/修正)归 fields 正本,本模块仅
    # 不消费(tool-gain-report 迭代裁定)。
    consumables: Field[list[str]] = field(default_factory=Field)     # 消耗品库存(§3.2.16)

    # —— 晶矿(§3.2.8,不占席)——
    # 域名 spheres = 晶矿域既定名(本义即晶矿球,非旧名残留;2026-09-20
    # ore 改名收束裁定不覆盖容器域名,fields.md §3.2.8 声明)。
    spheres: Field[OreSight] = field(default_factory=Field)      # 开局种子底座=空读面(晶矿补给在 1-1 进入时点送达,观察覆盖)
    # —— 晶矿附着奖励与声明通道(详设
    #    details/ore-reward-channel.md §1。附着值不进 OreSight.points——
    #    spheres 本体是画面真值留观察通道,附着值是随机态猜测,混进同域
    #    会让消费门(logic_rand_fields)对它失灵,故独立成域)——
    # [索引定义] ore_rewards 键 'x,y' = 矿身份**最新一次观察**的
    # (int(x), int(y)) 拼接字符串(JSON 安全,先例 = occupied_equips 键
    # 'front:1');身份连续性由挂接入口容差配对轨迹继承判定(键随轨迹
    # 重挂,精确键会被 Hough 抖动换键)。取值时机 = 矿身份首现生成刻,
    # 存续至开成摘除/消失清理;值类型 = OreReward(kernel/cw_ore_reward,
    # 唯一)。写入端 = kernel/cw_ore_channel.report_spheres_observed 单一
    # 写径(rekey/生成/清理三写,全部 write_logic_rand)+ 点击上报摘除
    # (collect_ore,3.2 覆盖)。策略层禁读(随机态域天然落消费门不可信侧)。
    ore_rewards: Field[dict[str, OreReward]] = field(default_factory=Field)
    # [索引定义] ore_declared_pending = 声明待兑现队列(逻辑态):元素 =
    # (env 投资环境规范名, plane 1 基位面号(与 NodeKey.plane 同坐标系),
    # gold 该位面声明金额卡面直读)。取值时机 = 入队电平检查刻追加
    # (check_ore_declared_level),生成刻移除(消费);「已发/未发」不可从
    # ore_rewards 现值推导(键随点击/清理/重挂消失),队列是唯一账。
    # 写入端 = cw_ore_channel(入队/消费/过期),无观察写端(声明是登记
    # 事实非观察投影)。开局种子底座 = ()(A 类)。
    ore_declared_pending: Field[tuple[tuple[str, int, int], ...]] = field(
        default_factory=Field)
    # [索引定义] ore_declared_done = 声明已消费标记(逻辑态):元素 =
    # (env, plane)(坐标系同 pending);幂等守卫第二腿——跨备战环重查不
    # 重发(op 每环重建无可失忆,守卫状态住 GameState)。取值时机 = 生成
    # 消费刻与 pending 移除同一逻辑步追加;位面过渡随 pending 同清理。
    # 恢复局随快照存续 = 离线回放不重发声明。开局种子底座 = ()(A 类)。
    ore_declared_done: Field[tuple[tuple[str, int], ...]] = field(
        default_factory=Field)

    # [索引定义] env_grants_done = 环境条件发放已发标记(逻辑态;迭代
    # 2026-10-10-env-conditional-grants,details/env-conditional-grant.md
    # §1):元素 = (env 投资环境规范名,条件键)。条件键取值清单 =
    # 'first_streak'(本局首次连胜达成)/'refresh_threshold'(刷新次数
    # 阈值触发器)两纯具名键 + 'star_grant#<装备名>'/'boss#<位面>-<轮>'
    # (劳务派遣合同:# 后载荷 = 键值扩展形态,前者为随机星徽授予的绑定
    # 键〔腿2 解析唯一源〕、后者为首领节点周期幂等键,fields.md §3.5.5)。
    # 取值时机 = 发放刻追加(check_env_streak_grants /
    # check_env_boss_grants 两写第二笔 / on_env_gained 随机装备绑定腿),
    # **局内恒存无过期清理**——「本局首次」整局有效,连胜无周期语义(与
    # 晶矿 done 的位面过渡过期清理不同;boss# 键的周期性 = 不同节点不同
    # 键,登记本身仍局内恒存)。幂等守卫:跨结算/跨观察重查不重发(结算
    # 低频天然幂等友好,电平 + done 直写,边沿/op 成员记忆已否定,取舍见
    # 详设「关键取舍」)。写入端 = 逻辑两模块:cw_env_grants 触发函数族
    # (发放刻追加)+ cw_gain_chain.on_env_gained 随机装备绑定腿
    # (placed 守卫下追加),无观察写端(发放登记事实非观察投影;直写
    # 先例 = cw_exec_state 金腿 / cw_effect_inventory 退款腿)。恢复局随
    # 快照存续 = 中断恢复对局不重发。开局种子底座 = ()(A 类)。
    env_grants_done: Field[tuple[tuple[str, str], ...]] = field(
        default_factory=Field)

    # [索引定义] node_seq_by_plane = 逐位面节点序列场字段(逻辑态;
    # 节点改写环境建模(统一注册表 = cw_node_schedule.ENV_NODE_REWRITE_
    # RULES;语义 = 本注释与 research/invest_effects.md)):
    # 键 = 位面 1 基(与 NodeKey.plane 同
    # 坐标系,恒只含键 {1,2,3}),值 = 节点类型序
    # (元素 ∈ cw_node_schedule.NODE_KINDS,与 PLANE_NODE_TABLES 同词表)。
    # 取值时机 = 环境注册刻一次性落全量(修饰表或默认表,无半态),局内
    # 恒存;**None = 未注册态**(P1 前段),消费方回退默认表(P1 内两制
    # 同值,回退无窗)。写入端 = cw_gain_chain.gain_invest_env 尾段单一
    # 写径(evidence='node_seq:env'),无观察写端——观察对账面 = 备战帧
    # 节点行动态槽数 CV 读(cw_node_reader)→ live 台账 seq_by_plane
    # (cw_exec_state),台账与本字段可逐位对照,失配留存证据不自动改写。
    # 消费面 = 节点序列正反解/next_screen 推导/观察锚定/round 值域上限
    # (node_round_cap)全部经本字段,坐标系从固定 9 制改按局修饰变长制
    # (正本 = game_state/node-domain.md §1)。开局种子底座 = None(A 类
    # 未注册口径)。恢复局随快照存续 = 修饰局接管坐标系不断。
    node_seq_by_plane: Field[dict[int, tuple[str, ...]] | None] = field(
        default_factory=Field)

    # —— 交互状态 ——
    prep_substate: Field[str] = field(default_factory=Field)     # 分类子态四档(§3.2.17;恢复锁定=会话推断档,写端=接管协议 §6.3)
    event_overlay: Field[str | None] = field(default_factory=Field)  # 'none'=确认无浮层;None=没读到(§3.6.1 双义禁令)

    # —— 备战席溢出(§3.2.20;2026-09-15 实机建档 prep.md 告警/溢出节)——
    # [索引定义] overflow_warning:告警横幅「备战席已满」在场 = 存在未安置
    # 溢出件(角色或占席道具,2026-09-24 用户确认道具同款溢出语义;此刻
    # 出战点击被游戏忽略——launch_dead 三连停机实证;策略消费门 = mandate
    # 溢出门,先卖腾位再出战)。取值时机 = 备战 heavy
    # 观察每入口帧实读覆盖(两态制,以实际观察为准);写入端 = **双写端**(观察
    # heavy 写端 CwScreenPrep 渠道① + 获得链逻辑写端 cw_gain_chain 席满
    # 溢出落位直写 True;第二逻辑写端先例 = CwActionSellBenchParam 溢出
    # 腿)。CwActionSellBenchParam 溢出腿(卖出自上报)落地
    # 后 logic 直写 False(推算消亡,下帧实读覆盖);落地同帧容器 bench
    # 回占入位件 + 执行侧 tracked 主账对称吸收(session 在场;
    # 缺吸收 = 守卫播种期双账分叉实机停机)。
    overflow_warning: Field[bool] = field(default_factory=Field)     # 开局种子底座=False 无溢出(真值观察覆盖)
    # [索引定义] overflow_card:溢出位(固定停车位,建档 area「区域-溢出角色」,
    # 1080p rect 1352,710-1465,805)上的溢出件身份,两分 = 角色 char_id /
    # 占席道具名(判据 = cw_investments.BENCH_ITEM_NAMES)。'' = 溢出位无卡
    # 或身份未识别(与 overflow_warning 配对解读:True ∧ '' = 有件未识别);
    # 值语义 = CwActionSellBenchParam 溢出腿的入位对象身份(角色星级缺读按 1 兜底,下帧
    # heavy 实读覆盖修正)。写入端 = **双写端**(观察 heavy 写端同上 +
    # 获得链逻辑写端 cw_gain_chain 席满溢出落位直写身份;第二逻辑写端
    # 先例 = 溢出腿);溢出腿落地后
    # logic 直写 ''(入位消费)。
    overflow_card: Field[str] = field(default_factory=Field)     # 开局种子底座='' 无溢出(真值观察覆盖)

    # —— (tracked 第二账簿记宿主已停用删除:
    #     3.1 容器合并后主域 bench/deployed 席位视图即唯一账,第二账
    #     无可同步;观察锚语义由 tracked_account_observed 字段独立承载。)——
    # —— overlay 登记簿记宿主(非 Field;契约
    #     C-登记/C-簿记:pending 队列 + 触发簿记,值载体与三访问口
    #     单一源 = kernel/cw_overlay_register.py)——
    screen_changes: ScreenChanges = field(default_factory=ScreenChanges)
    # —— 节点序列探针簿记宿主(非 Field;终态契约 §A′ 宿主,
    # 成员与访问纪律见 :class:`NodeBooks` 类注)——
    node_books: NodeBooks = field(default_factory=NodeBooks)
    # (备战黑板帧宿主 prep_obs 已停用:名单/装备/占用/晶矿全部
    #  容器域承载,策略器唯读容器契约归位,勿复活。)

    # —— 帧触发代次双槽(非 Field 簿记;终态契约 §B:session
    # prep_frame_class/shop_frame_class 停用迁此,两槽互不相干禁合并——
    # 标注对象分别为「最近一次备战域/商店域容器观察写点」)。
    # [值域] 'full' | 'view' | 'none',缺省 'none'。消费协议 = 读后即清
    # 'none'(读协议半部,防同帧重复刷新);写端 = 备战/商店域观察装配点。
    # 非 Field 理由 = 纯过程信号(无以实际观察为准仲裁、无 journal 面秒级生命周期),
    # 容器每局新建 = 天然清零。
    frame_class_prep: str = 'none'
    frame_class_shop: str = 'none'
    # —— 锚定标志(非 Field 簿记;工程结构组单列申报)——
    # 本局是否已完成首次成功的备战 heavy 锚定(屏幕真值写回成功)。过程信号
    # 无以实际观察为准仲裁,同 frame_class 先例不入 Field(无 journal 面语义;容器
    # 每局新建 = 天然清零,粘性位无复位)。生产唯一置位写点 = kernel
    # reconcile_tracking 写 tracked_account_observed=True 的同点(两标志同一
    # 成功条件,写失败同不置位);测试/直构域专用置标志口 = 直接赋值 True。
    # 读口 = prep_anchored_of(session),缺省 False。
    prep_anchored: bool = False

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
    # —— 选项坐标伴随域四槽(op-layer.md §1.1 选择坐标观察上报;fields.md
    #    §3.4.5a;骨架先行落定义,写端接线随各屏坐标收敛逐批落地)——
    # [索引定义] 四域同构,各伴随同名去 _xy 的名字域(star_tome_opts /
    # wish_trial_opts / box_card_names / fortune_opts):
    # 键 = 名字域列表下标 idx(0 起,左→右画面物理序,与策略器输出下标、
    #   动作词表 param.idx 同一坐标系,零换算);
    # 取值时机 = 观察期快照(进访问入口观察帧的识别产物,与名字域同一次
    #   观察同帧同源;动作执行期恒稳,禁执行期现读现算);
    # 值 = tuple[int, int](x, y,1080p 游戏空间;平铺元组 = 遥测 JSON 序列化
    #   安全形);
    # 写入端 = 观察 report 同门(与名字域同一次 report_screen_*_obs 调用、
    #   同一写门一并写,坐标单一真相源 = 观察上报;同序等长由写端构造守卫
    #   保证,读端不做长度调和;接线未落地前 = 恒未观察 None);
    # 读端唯一 = 各域动作 op(按 idx 取点执行,缺席/越界 = 守卫断言);
    # 失读/离屏语义与名字域同格(离屏清场经 _PAYLOAD_DOMAINS 已登记);
    # sim 无画面识别不建模,恒 None。
    star_tome_opts_xy: Field[list[tuple[int, int]] | None] = field(default_factory=Field)
    wish_trial_opts_xy: Field[list[tuple[int, int]] | None] = field(default_factory=Field)
    box_card_names_xy: Field[list[tuple[int, int]] | None] = field(default_factory=Field)
    fortune_opts_xy: Field[list[tuple[int, int]] | None] = field(default_factory=Field)
    # —— 契约扩员新槽(写端 = 各画面 handler 写槽,
    #    消费 = flow 零参入口 decide_fortune/expert_invite;
    #    equip_pick_opts 槽已停用删除——选择装备屏不存在,勿复活)——
    fortune_opts: Field[list[str] | None] = field(default_factory=Field)
    expert_invite: Field[ExpertInvitePayload | None] = field(default_factory=Field)

    # —— 十事件屏选择结果(§3.4/§4 事件选择:chosen_* 由选择 handler 单次逻辑写入)——
    # (遭遇例外,遭遇扩围批:chosen_encounter 写端 = 动作侧即时上报
    #  kernel/cw_action_report/pick_encounter.py,发出即写;兑现后清,单次消费。)
    chosen_encounter: Field[tuple[int, str] | None] = field(default_factory=Field)   # (难度档,奖励文本)
    # 遭遇奖励兑现记录(遭遇扩围批;语义账面:最近一次伤害达标兑现的遭遇
    # 所选值,单槽逐遭遇覆盖;写端 = 结算兑现回调 claim_encounter_reward
    # (双证判遭遇 + progress_delta>0 单判),兑现即清 chosen_encounter;
    # 无开局种子 None = 本局未兑现过,局终随容器销毁;sim 无遭遇结算回调
    # 面 = 无 sim 写端;遥测 schema 接线候批,现役消费 = 容器读端 +
    # 审计投影;数值不直写防双源——金币真值 = settle_truth 结算读数、
    # 随机4费 = bench 观察)
    encounter_reward_claimed: Field[tuple[int, str] | None] = field(default_factory=Field)
    chosen_supply: Field[tuple[str, tuple[str, ...]] | None] = field(default_factory=Field)  # (角色,装备名列表;y 序;带钻与否自列表派生)
    chosen_megastar: Field[str | None] = field(default_factory=Field)   # 盛会之星(§3.4.5)
    chosen_partner: Field[str | None] = field(default_factory=Field)    # 伙伴(候选阵营)
    chosen_wish: Field[str | None] = field(default_factory=Field)       # 祈愿试炼目标文本(档=货币战争-祈愿试炼,写端=cw_screen_wish_trial)
    chosen_fortune: Field[str | None] = field(default_factory=Field)    # 命运卜者(建档已登记 cw_fortune_picker.yml,缺三卡文本读区 = fields.md §3.4.5;写端未接线 = 先补档,fields.md §4)
    chosen_hack: Field[str | None] = field(default_factory=Field)       # 骇入策划(暂无画面建档)
    chosen_expert: Field[str | None] = field(default_factory=Field)     # 专家邀请函
    chosen_tome: Field[str | None] = field(default_factory=Field)       # 星徽秘典弹窗卡名
    chosen_equip: Field[str | None] = field(default_factory=Field)      # 装备三选一(暂无画面建档)

    # —— 特殊规则演化状态(纯逻辑态:无观察写端;写端 = 动作报告)——
    # 银狼LV.999 当前费用档,值域 {3,4,5};写端 = pick_planner 升费腿 /
    # deploy_move 上阵变费腿(仅此两个动作报告);读口唯一 =
    # cw_economy.effective_cost;未观察(None)= 未触发任何变换,语义档 =
    # 起始 3 费。同名即同档——全场同档,无 per-unit 维度。
    lv999_cost_tier: Field[int] = field(default_factory=Field)

    # —— 结算(战斗后真值覆盖的数据源)——
    settlement: Field[Settlement | None] = field(default_factory=Field)
    hp_floor_triggered: Field[bool] = field(default_factory=Field)   # hp 保底触发事件位(§3.5.3;纯观察登记,无判据载体)

    # —— 逻辑态派生域与画面上下文域(R1 §3.1.4;gs_schema 域 'derivation')——
    # 写点准入:上下文对与顶栏原文唯一写点 = ①观察汇聚
    # (observe_screen_context,观察层);node_pos 写点 = 两态生命周期
    # (锚定态 observe_node_anchor 直写 observation / 推进态
    # report_node_advance 经 advance_node_effective 写 logic——「禁 observe
    # 直写序键」旧裁决已停用,design §2.2/§2.7-7)——
    # 其余渠道写入 = 越格。
    prev_screen: Field[str] = field(default_factory=Field)       # 上一次分派观察的画面标识(开局前 '')
    current_screen: Field[str] = field(default_factory=Field)    # 最近一次分派观察的画面标识(派生规则输入面)
    # [索引定义] top_bar_raw = 备战帧顶栏原始文本(如「备战阶段 1-3」OCR
    # 原文)。**观察层字段**(唯一 observe() 写点 = 观察汇聚,source=
    # observation):只落画面原始读数,禁写派生值(序键走两态生命周期,
    # 原文才是观察层)。原文缺读 = 不写(禁猜);
    # 取值时机 = 备战帧观察期快照。生产透传(读链暴露原文)候漏斗接线批。
    top_bar_raw: Field[str] = field(default_factory=Field)
    # [索引定义] node_pos = 节点序位 (位面,轮) 二元素整数元组,1 基
    # (:data:`cw_node_schedule.NodePos`,节点身份唯一表示;字典序 = 序列
    # 全序)。**两态序键(迭代 2026-09-20-node-advance-action-report
    # design §2.2)**:观察锚定态(source=observation,写端 =
    # observe_node_anchor 直写,「禁 observe 直写序键」旧裁决已推翻)解锁
    # 下一次终结动作上报;推进未确认态(source=logic,写端 =
    # report_node_advance 经 advance_node_effective)等观察锚定翻态。
    # 生效序读口 = :func:`effective_node_pos`(派生计算,非存储字段);
    # None = 未定(开局/恢复局首锚定前,观察态门 value 守卫据此挡首次上报)。
    # 取值时机 = 写入期快照。
    node_pos: Field[tuple[int, int]] = field(default_factory=Field)

    # —— 动作回执域(R2 §3.1.1-4/§3.2.5;gs_schema 域 'receipts')——
    # [索引定义] receipts 值 = 动作执行回执的滚动窗:list 下标 i = 第 i 条
    # 存活回执(窗序 = 写入序,先进先出,容量 = :data:`RECEIPTS_WINDOW_CAP`);
    # 取值时机 = 写入期快照(帧替换,禁就地改窗内条目)。唯一写点 =
    # :func:`note_action_receipt`(渠道② logic_action);失败动作也产行
    # (applied=false + reason)——exec_events「失败可见性」并入载体。
    receipts: Field[list[dict]] = field(default_factory=Field)

    # —— 局终域(§3.6.1 runs 并入载体;gs_schema 域 'match_final')——
    # [索引定义] match_final 值 = :class:`MatchFinal` 终局行载荷(一段一行,
    # 恢复局跨段 = 多行;game 级聚合取段序末行)。取值时机 = 局终判定成立
    # 的当前 swap(单版本原子);None = 本段未收束。唯一写点 =
    # :func:`write_match_final`(渠道③ actor=MatchClose);写前查重即本
    # 字段现读(段内幂等,G12 并入)。
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
    # [索引定义] node_hist_pos = 本 run 已见最大生效节点序位(生效序位 =
    # :func:`effective_node_pos` 读口现值,(位面,轮) 元组键,与效果账本
    # advance_node 同键);派生规则推进去重键 (run_id,生效序位) 的 run 内
    # 载体(设计 v3.1-N2)——同序位恰一次推进,先到腿越 hist 即推进,后到
    # 腿同序零推进。取值时机 = 派生写入期单调推进(元组字典序);None =
    # 本 run 尚无派生推进。写端 = 派生规则。
    node_hist_pos: tuple[int, int] | None = None
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

        - sig = 显式渠道签名(必填;影子期「缺位合成」过渡语义已废,
          行 actor 非空,调用方已过 :func:`_validate_sig` 渠道面校验);
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
        - 产生面 = 登记清单(非全量;obs_conflict 汇点并入已接——);
        - sig = 渠道①签名(观察证据属 obs 族;必填,缺位合成路径
          已停用)。
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
                'acquired_key': _json_safe(getattr(e, 'acquired_key', None)),
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
            # 侧栏,遥测/重放面缺口由本行收束)。键 =
            # 侧栏键 (装备名,装备者) 序列化为「装备名|装备者」串(JSON
            # 安全);空侧栏 = 空 dict,行形状稳定。
            'equip_progress': {f'{k[0]}|{k[1]}': v
                               for k, v
                               in self.effects.equip_progress.items()},
            'frame_obs': self.frame_obs,
            'write_seq': self.write_seq,
            'node_hist_pos': _json_safe(self.node_hist_pos),
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
        - 覆盖 logic 来源值且失配 → 三分流处置(§2.3 以实际观察为准;失配 =
          逻辑态被实读证伪 = bug,豁免/抑制/失配告警三分流——
          :func:`_route_logic_mismatch`;失配默认失配告警停机,修推算代码);
        - 覆盖 logic_rand 来源值且差异 → **预期内**(随机效果落地,非
          bug):只落 ``logic_rand_outcome`` 台账行留存证据(无告警无停机,
          随机模型校准遥测面;sim 证据行由 :func:`_emit_defect` 发出口
          抑制面兜底),覆盖照常 = 随机结果采新;
        - sig = 渠道①签名(必填;缺位合成路径已停用);
        - note = 可选行注记(结算事实等语义,battle_done 并入)。
        """
        if value is None:
            raise ValueError('observe 不接受 None(§2.2:失读走 carry/'
                             'leave_screen,禁清正式值)')
        _validate_sig(sig, ('obs',))
        name = self._field_name(target)
        if target.source == 'logic_rand' and target.value is not None \
                and target.value != value:
            # 逻辑随机态被观察覆盖:差异 = 随机效果落地,预期内非 bug
            # ——不进三分流,只落台账行留存证据(等值 = 零新信息不产行,
            # settle_truth 同纪律;发出口抑制面兜底 sim 证据行)。
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
        """行槽位纯重排吸收(§2.3 失配分支前置;deployed 域专属;吸收束径
        = 详设「观察与吸收」节)。游戏侧会在**子表内自行
        重排**已上阵单位(排序规则游戏私有,非 bot 动作,无逻辑写端)——
        同子表内单元级多重集相同、排列不同 = 读数抖动,是机制性结构差异,
        不是推算 bug。命中条件全列(缺一不可):字段 = deployed;新旧值均
        为 DeployedView;两子表各自单元多重集相等(键 =
        :func:`_rows_unit_key`,槽位不在键内,装备集在键内——穿戴变化
        不算重排)。**换排(跨子表移动)多重集必不等 → 不吸收**,照真
        失配三分流(换排是我们发起的逻辑写,观察侧换排差异 = 推算与实读
        分歧的合法信号)。同口径天然覆盖「容量变化」读数(投资改槽后
        扩容帧:单元多重集不变仅尾空槽增减 = 吸收;容量变更无逻辑写端,
        属游戏侧行为)。命中 → ``deploy_slot_reorder`` 台账行(无告警无
        停机,豁免 ≠ 消失同纪律)后覆盖照常 = 采新(游戏侧排序为画面
        事实),与对账纠漂(tracked 主账采新)两面同向;形状不符(缺员/
        多员/星级差/装备差/换排)返回 False 返回主循环三分流照真失配停,真投影
        bug 不被吞。返回 True = 已吸收(调用方跳过失配分流)。"""
        if field_name != 'deployed':
            return False
        old, new = target.value, value
        if not isinstance(old, DeployedView) or not isinstance(new, DeployedView):
            return False
        for old_units, new_units in ((old.front_slots, new.front_slots),
                                     (old.back_slots, new.back_slots)):
            if Counter(map(_rows_unit_key, [u for u in old_units or []
                                            if u is not None])) != \
                    Counter(map(_rows_unit_key, [u for u in new_units or []
                                                 if u is not None])):
                return False
        _emit_defect(field_name=field_name, expected=old, actual=new,
                     evidence=observed_evidence, sig=sig,
                     logic_evidence=target.evidence,
                     kind='deploy_slot_reorder')
        log.info('[cw][gs] 行内纯重排吸收:deployed 子表内同单位多重集'
                 '排列差异采新(游戏侧行内重排无逻辑写端,'
                 'deploy_slot_reorder 留证)')
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
        - badge OCR 单帧误读(第 5 例定案:坏读数在观察侧)。

        「上阵单位集合」这一真不变量由 deployed 自身的失配/
        纯重排吸收面独立把守,board 对动作推算 bug 无独立检出力 → 命中
        即落 ``board_derived_adopt`` 台账行(无告警无停机,豁免 ≠ 消失
        同纪律)后覆盖照常采新:派生量以观察为真值源,坏读数暴露于台账
        与观察侧 obs_conflict 留存证据链、由下一帧观察自愈(与 obs→obs 直采
        语义同向)。适用范围 = evidence 前缀 ``proj_board_resync``(派生挂钩
        唯一合法写端,单一源 = :meth:`_resync_board_delta`):独立手写
        board = 越格契约违反,照真失配告警(本吸收面不得沦为 board 全面
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
        """board 派生重算单一源(deployed 逻辑写端挂钩;本方法
        是「羁绊/阵营计数 = 上阵单位集合的派生量」的实现位,写入口 =
        :meth:`_write_logic_frame` 行域写后自动触发(write_logic/
        write_logic_rand 共用),禁绕过手写 board)。rand = 继承行域写入
        来源:行域为随机态时 board 派生写同标随机态(行域真值形态随采样
        奖励而变,board 为其派生,污染沿派生链传递)。

        语义 = **观察基座 + 行变更增量**:board 现值为 None(板未读过)
        时无派生基座,跳过等观察首读;否则对本次 deployed 写做**逐子表**
        单位多重集差(键 = :func:`_rows_unit_key`;前排/后排各算各的差,
        排名随子表传入 :func:`_row_unit_tags`——开拓者形态随排的标签
        差因此自然成立),新增单位逐个加其羁绊标签
        (:func:`_row_unit_tags`,L1 全集+装备贡献),移除单位逐个减、
        减至 0 摘键(面板语义:无成员不显行),差为零不写。增量口径
        (非全量重算)的依据:观察基座含左面板真值的装备羁绊贡献,而
        容器行单位未必携带穿戴建模(实机 2026-09-18 run_20260918_045918:
        环境卡授予的星徽穿戴只出现在面板,行单位 equips 为空)——全量
        重算会把基座真值抹掉,增量只施加本次动作的差,基座贡献保留。
        派生漂移由下一备战帧观察覆盖收敛,注释与接线一致:失配经
        :meth:`_absorb_board_derived` 采新留存证据(``board_derived_adopt``,
        失配告警不响)——派生量以观察为真值源,观察侧坏读数暴露于台账与
        obs_conflict 留存证据链、由下一帧观察自愈。"""
        board = self.board.value
        if board is None:
            return
        new_view = getattr(self, field_name).value
        old_view = old_value
        new_board = dict(board)
        for sub, row_name in (('front_slots', 'front_row'),
                              ('back_slots', 'back_row')):
            old_units = [u for u in (getattr(old_view, sub, None) or [])
                         if u is not None]
            new_units = [u for u in (getattr(new_view, sub, None) or [])
                         if u is not None]
            old_counter = Counter(map(_rows_unit_key, old_units))
            new_counter = Counter(map(_rows_unit_key, new_units))
            added = new_counter - old_counter
            removed = old_counter - new_counter
            if not added and not removed:
                continue
            for u in new_units:
                k = _rows_unit_key(u)
                if added.get(k, 0) > 0:
                    added[k] -= 1
                    for t in _row_unit_tags(u, row_name):
                        new_board[t] = new_board.get(t, 0) + 1
            for u in old_units:
                k = _rows_unit_key(u)
                if removed.get(k, 0) > 0:
                    removed[k] -= 1
                    for t in _row_unit_tags(u, row_name):
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
        """结算屏真值收束(金币专用;无条件以实际观察为准,不走失配三分流)。

        为什么不经 observe():节点收入由游戏侧在结算屏展示前入账,bot 无
        逻辑写端,账本与结算真值的差 = **预期边界收入**而非推算 bug,
        三分流(失配告警停机)不覆盖——经 observe 失配链则每场战斗必停局
        (2026-09-18 全夜停局病态);收入分量(基础奖励/利息/连胜)由
        结算屏「获得金币总览」面板公示,当前读链未消费 = 已申报读缺口。
        收束语义:差值落 ``boundary_income_credited`` 台账行留存证据(金额
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
        不占版本,§3.2.2 规则 4)。现值来源为 logic_rand(逻辑随机态:开局
        种子底座/采样值)→ 同样不沿用——随机态值不是「上次好值」,失读时
        宁保持未验证态,禁被失读腿换帧洗成可信 carried(§8.8 假值防线)。
        sig 必填()。"""
        if target.value is None or target.source == 'logic_rand':
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
        ``prior:`` 前缀;本类仅限显式申报条目,禁扩散。sig 必填()。"""
        if not evidence.startswith('prior:'):
            raise ValueError('prior 写入 evidence 必带 prior: 前缀(§2.1)')
        _validate_sig(sig, ('obs',))
        name = self._field_name(target)
        self._swap(name, Field(value=value, source='prior', evidence=evidence),
                   sig=sig)

    def leave_screen(self, target: Field,
                     sig: ChannelSig) -> None:
        """画面附加域离屏(§2.2 显式例外):置 None 是结构事实非失读,
        不受 carried 硬边界覆盖。仅 shop/encounter/supply 三域合法,整局
        字段禁走此口(显式炸错防误用扩散)。sig 必填()。"""
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
        """逻辑直写(两态制标准写通道):决策动作按游戏规则推算
        的预期效果**直接写入字段**(source=logic),策略器立即可读——
        「在观察态到来之前供决策使用」是逻辑态的全部职能。
        随机效果口径走 :meth:`write_logic_rand`(逻辑随机态,失配预期内),
        确定面仍走本口。

        - 历史「仅限显式申报豁免写端」的限制随 expect/confirm 两步机制
          废除一并解除:凡逻辑推算写入统一走本口,不再有
          「记待核实预期→核对转正」的第二步;
        - 非免检通道:字段值之后仍受观察覆盖(§2.3 以实际观察为准),推算与
          实读失配 = 推算代码 bug,缺陷台账留存证据后修推算代码——运行时
          不待办、不对账兜底;
        - produced_by = 产生者标识(op/handler 名,留存证据用);
        - evidence = 可选来源注记(如刷新执行的轮键 refresh_exec@p1-r2);
        - sig = 渠道②③签名(必填;派生规则与流程 hook 系统的 ③ 写入走
          本同一口,family=logic_hook——写入口不感知触发机制,零接口预留;
           legacy 合成已停用);
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
          ``logic_rand_outcome`` 台账行留存证据(无告警无停机),不进失配
          三分流(差异出 :meth:`observe`);
        - 策略器消费前必须重观察(查询口 = :meth:`logic_rand_fields`;
          消费门先例 = hp 可信位 ``cw_hp_policy.hp_readable`` 只认
          observation/carried,logic_rand 自然落入不可信侧)。

        污染传递:采样链上全部写入标随机态(含终值受随机分支影响的
        联动写,如晶矿摘除);跨动作由上报入口判定(:meth:`any_logic_rand`)
        继承。边界:gold 结算屏真值收束(:meth:`settle_truth`)不经
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
          传递);行域确定 logic 时 board 仍 logic;
        - deployed 逻辑写尾挂值域回调级联(契约 C-回调:
          按名分解 diff → 事件/资格集/星级回调;观察写不经本方法 =
          零回调。logic/logic_rand 两通道同经,获得链递归每步语义完整)。"""
        name = self._field_name(target)
        old_row_value = target.value if name == 'deployed' else None
        self._swap(name, Field(value=value, source=source, evidence=evidence),
                   sig=sig, note=note)
        if name == 'deployed':
            self._resync_board_delta(name, old_row_value,
                                     produced_by=produced_by, sig=sig,
                                     rand=(source == 'logic_rand'))
            from sr_od.application.currency_war.kernel.cw_faction_callbacks import (
                on_deployed_logic_write,
            )
            on_deployed_logic_write(self, old_row_value, value,
                                    source=produced_by)

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
           legacy 合成已停用——)。
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
        逻辑随机态字段不覆盖(随机口径非严格推算承诺,不进对账巡检面;
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
        未登记名字跳过(容错,不炸)。"""
        for n in field_names:
            f = getattr(self, n, None)
            if isinstance(f, Field) and f.source == 'logic_rand':
                return True
        return False

    def observe_screen_context(self, screen_name: str, *,
                               top_raw: str | None = None,
                               sig: ChannelSig | None = None) -> None:
        """画面上下域写入(观察汇聚模块唯一写点,生产接线 = read_game_state
        漏斗,随分派观察调用)。

        - 上下文对(渠道①):旧 ``current_screen`` 转 ``prev_screen`` 后写
          新值,成对变更同 group(§3.1.4);
        - 顶栏原文观察层:top_raw 非 空 ∧ 干净备战帧 → ``observe(top_bar_raw)``
          落画面**原始读数**(观察层唯一落点);
        - 类型派生·商店分支:商店面板(非专属,「未定型」零直定)→ 查现行链
          (:func:`chain_node_type`)直定,链缺/位越界/未辨 = 零写(禁猜,
          链正本 §6 零内建回落)。

        **适用范围(迭代 2026-09-20-node-advance-action-report 切换批,design
        §2.4 攻击 B1 修正)**:本口已退出**推进域**(``node_pos``/
        ``node_hist_pos`` 写入与效果推进尾段随四推断腿停用)——节点推进唯一
        落账入口 = :func:`advance_node_effective`(动作上报/观察锚定);
        ``gs.node`` 观察镜像写端保留在漏斗(决策层坐标供给端,与 gold/hp
        同类的观察域写入,零派生零推进)。

        - top_raw = 本帧顶栏原始文本(如「备战阶段 1-3」;观察层落点,缺读
          = None 不写禁猜);
        - 写入无条件(journal 常开,影子闸折叠——;
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
        # —— 类型派生(商店查现行链;链观察落地批)——
        # 商店对任意节点类型都开(非专属)→ 类型查现行链——链在位 = 直定写,
        # 链缺/位越界/未辨 = 零写(禁猜,链正本 §6 零内建回落)。目标节点 =
        # 生效序与观察镜像的最新者(店开帧可在推进腿未计数的新节点上,镜像
        # 已由读链写新序键——目标只取 hist 会把类型回写上一节点,
        # run_20260918_074040 第 11 例病理)。
        if screen_name == SCREEN_SHOP_PANEL:
            _shop_target = _shop_panel_type_target(self)
            if _shop_target is not None:
                # 目标即键(键表示唯一,迭代 2026-10-12-abolish-node-ordinal
                # design §2.3: 的目标反解码半已停用)
                # ——链查询直取目标序位,零坐标换算。
                _chain_q = chain_node_type(self, _shop_target[0],
                                           _shop_target[1])
                if _chain_q.token is not None:
                    _write_derived_node_type(
                        self, _chain_q.token, target_pos=_shop_target,
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


# ============================================================ 节点类型派生与生效序读口(渠道③)

def _derive_write(gs: GameState, target: Field, value: int | NodeKey, *,
                  actor: str, trigger_screen: str, seq: int,
                  note: str = '') -> None:
    """派生写入(逻辑层统一形态):签名 family=logic_hook、
    actor=规则登记名、screen=关联画面、组 id = 'hook:<登记名>@<seq>'。
    value = 节点键(NodeKey,类型派生经节点域写 node.kind,§3.1.3 节点域
    ③格;节点序推进已不走本口——序号前进唯一入口 = advance_node_effective)。"""
    sig = ChannelSig(family='logic_hook', actor=actor, screen=trigger_screen,
                     mode='compute', group_id=f'hook:{actor}@{seq}')
    gs.write_logic(target, value, produced_by=actor, sig=sig, note=note)


def effective_node_pos(gs: GameState) -> NodePos | None:
    """生效序读口(派生计算,非存储字段;判定基准读口,非决策消费切换目标
    ——「node 逻辑态改读派生域」M4 工作项已作废:决策面现读容器 gs.node 镜像
    合规,无切换义务,/正本消费面申报)
    = max(node_pos 字段现值, node_hist_pos)——单字段双值结构(
    节 2):字段现值 = 最近一次写入(锚定直写 observation / 推进 write_logic
    两态),hist =
    run 内已见最大序位(跃迁去重键 ``(run_id, 生效序位)`` 载体);两者之
    差仅存在于纠偏写序中间态,取 max 即生效语义,None 安全(双空 = 未定);
    max = 元组字典序(= 序列全序,键表示下零序列依赖);消费面恒逻辑层,
    观察层(top_bar_raw)不参与序比较。"""
    vals = [v for v in (gs.node_pos.value, gs.node_hist_pos)
            if v is not None]
    return max(vals) if vals else None


def _obs_node_pos(gs: GameState) -> NodePos | None:
    """node 观察镜像的节点序位(派生计算:镜像 NodeKey 直接取
    (plane, round_num);镜像空 = None)。镜像由读链在非备战帧也写
    (店开帧 votes 读),可领先推进水位——它是「当前节点」的观察权威源。"""
    cur = gs.node.value
    if cur is None:
        return None
    return (int(cur.plane), int(cur.round_num))


def _shop_panel_type_target(gs: GameState) -> NodePos | None:
    """商店查链类型派生的目标节点序位 = 生效序位与观察镜像的最新者
    (双源全空 = 目标不可知,禁猜零写;max = 元组字典序)。

    为什么不单取 hist:店开帧读链可把镜像写到推进腿尚未计数的新序位
    (备战帧未过,弹窗腿/备战腿都未触发),目标只取 hist 会把类型直定
    回写上一节点——后续备战帧真读新节点与被回写的 logic 值类型失配,
    统一观察对账失配告警照停(run_20260918_074040 未投影族第 11 例病理)。
    取 max = 「当前节点」语义;弹窗腿先推进的形态下 max 仍取推进值,
    行为与旧 hist 单源一致。"""
    poss = [v for v in (effective_node_pos(gs), _obs_node_pos(gs))
            if v is not None]
    return max(poss) if poss else None


def tick_effect_boundary(gs: GameState) -> None:
    """效果推进段(现接线位 = :func:`advance_node_effective` 尾段,
    本函数独立可调供直测/sim)。

    - 推进闸:effective None → 整段跳过(「未观察不当真进节点」守卫,禁虚耗
      余期/虚累余额);
    - 账本推进(内置去重兜底同序幂等)→ 到期留存证据 → 刷新发放(advanced 位闸)
      → 容量重锚;
    - 经济参数 = 容器直读 active_strategies(空/None → 聚合缺省);
    - 异常边界:吞 Exception 记 warning 不上抛(不毒化派生链)。

    历史:prep_frame 形参(「金结算仅备战帧触发」闸)随
    ``settle_node_boundary_gold`` 生产调用点归零停用,本迭代删除形参。
    """
    try:
        _tick_effect_boundary_impl(gs)
    except Exception as e:   # noqa: BLE001  best-effort 不毒化派生链
        log.warning(f'[cw][effect] 效果推进段失败(不阻塞): {e}')


def _tick_effect_boundary_impl(gs: GameState) -> None:
    effective = effective_node_pos(gs)
    if effective is None:
        return
    # frame 只进 evidence/效果刷新余额账,语义 = 节点身份标识,随键直拼
    # (「位面-轮」统一标识,用户裁定 2026-10-12;键表示下序位恒合法,
    # 旧「超序列表总长 frame 缺位」分支随越界序位不存在而停用)。
    frame = f'{effective[0]}-{effective[1]}'
    advanced, expired = gs.effects.advance_node(effective)
    for _eff in expired:
        log.warning('[cw!][effect] 效果到期移除:%s(尾款触发面;金面走观察覆盖兜底)',
                    _eff.spec.name)
    if advanced:
        grant_effect_node_refresh_balance(gs, frame=frame)
    project_effect_capacity(gs)


# ============================================================ 节点推进动作上报(design §2.2/§2.3)

#: 动作推进 trigger 封闭集(design §2.3;集外显式炸错)。
NODE_ADVANCE_TRIGGERS: frozenset[str] = frozenset({'settle_confirm', 'supply_confirm'})

#: trigger → journal 行 actor(留存证据归因;现役 _validate_sig 只校 family,actor 为自由归因标识,攻击 R2)。
_NODE_ADVANCE_ACTORS: dict[str, str] = {
    'settle_confirm': 'CwOpSettleConfirm',
    'supply_confirm': 'CwActionPickSupplyOp',
}

#: node_advance 声明的推进分派类别(详设 world-decl.md §2 表 #1/#2;
#: 值零新词沿用归并过程名,封闭集单一源 = sim 后端 advance 分派表键集)。
_NODE_ADVANCE_DECL_TRIGGER: str = 'node_advance'

#: 位面切换优先的下一画面(推导规则第三步;档名权威 = screen_info 建档,
#: 与 sim 后端呈现屏同档名)。
_NODE_PLANE_TRANSITION_SCREEN: str = '货币战争-位面过渡'

#: 节点类型 → 下一画面档名映射(推导规则第四步;与 sim 后端
#: ``_screen_for_node`` 同映射,battle/reward 归备战档;对照测试逐值钉死)。
_NODE_KIND_NEXT_SCREENS: dict[str, str] = {
    'supply': '货币战争-补给',
    'encounter': '货币战争-遭遇节点',
    'boss': SCREEN_BOSS_BRIEFING,
    'battle': SCREEN_PREP_FRAME,
    'reward': SCREEN_PREP_FRAME,
}


def _node_advance_next_screen(gs: GameState) -> str:
    """node_advance 声明的 ``next_screen`` 推导(详设 world-decl.md §2
    推导规则;构造时点 = 推进落账**后**,``node_pos`` 已是新节点序位)。

    规则序:输入即键(键表示唯一,``total`` 求和与反解两段已停用)→
    序位位面无序列表
    = 局终('';对齐旧 eff 超总长优雅局终,现役表键 P1+P2+P3 全在,
    此臂 = 表外位面防御/OCR 位面误读形态,照常返回主循环,外循环走
    结束链)→ 位面内轮次超序列长 = 局终(modeled 位面内损坏坐标防御)
    → 位面切换优先 → 节点类型映射。推导权威源 = kernel 节点日程真值表
    (:mod:`cw_node_schedule`)+ :func:`effective_node_pos`;**禁读容器
    ``gs.node`` 作推导口**——它是观察镜像,写端(观察漏斗/类型派生/
    sim backend)都在本构造点之后,此处读到的恒是旧节点。
    """
    pos = effective_node_pos(gs)
    if pos is None:
        return ''   # 不可达(构造点保证 eff 在场;防御性诚实缺省)
    # 序列权威源 = 场字段现值(None = 未注册回退默认表,原行为):位面在表
    # 判定/长度守卫/kind 取值三处同源;禁直查 node_sequence_of 抛错——
    # 先判位面在表性再取长(表外位面 = 优雅局终非停机)。
    seqs = gs.node_seq_by_plane.value
    tables = seqs if seqs is not None else PLANE_NODE_TABLES
    seq = tables.get(pos[0])
    if seq is None:
        return ''
    if pos[1] > len(seq):
        return ''
    if pos[0] > 1 and pos[1] == 1:
        return _NODE_PLANE_TRANSITION_SCREEN
    return _NODE_KIND_NEXT_SCREENS[seq[pos[1] - 1]]


def node_screen_now(gs: GameState) -> str:
    """当前生效节点的呈现屏档名(「返回节点屏」类动作声明的
    ``next_screen`` 权威源;推导规则 = :func:`_node_advance_next_screen`
    的位面切换/类型映射两步,输入 = 生效序位现值而非推进落账——
    节点窗内压住的节点屏可能是遭遇/补给/boss 档,历史硬编码备战仅对
    battle/reward 槽成立,改节点序列环境(战争边疆 P3 遭遇槽)使其
    失真,推导单一源收口)。

    恒非空串:生效序位缺位/表外位面/槽越界(降级形态,正常对局不可达)
    回退备战档(历史口径)——声明面禁空串(空串 = 局终语义,误用会被
    对账判局终漂移)。
    """
    pos = effective_node_pos(gs)
    if pos is None:
        return SCREEN_PREP_FRAME
    seqs = gs.node_seq_by_plane.value
    tables = seqs if seqs is not None else PLANE_NODE_TABLES
    seq = tables.get(pos[0])
    if seq is None or pos[1] > len(seq):
        return SCREEN_PREP_FRAME
    if pos[0] > 1 and pos[1] == 1:
        return _NODE_PLANE_TRANSITION_SCREEN
    return _NODE_KIND_NEXT_SCREENS[seq[pos[1] - 1]]


def advance_node_effective(gs: GameState, candidate: NodePos, *,
                           actor: str, sig: ChannelSig,
                           source: FieldSource = 'logic') -> bool:
    """推进生效原语:序位前进的唯一落账入口(design §2.2;candidate =
    (位面,轮) 元组键,比较 = 元组字典序即序列全序)。

    序位前进的任何合法写点(动作上报/观察补推)都必须经本原语——账本
    ``advance_node`` 去重是序位相等判,序位前进不经效果尾段即永久漏该
    节点每节点发放(攻击 F2①)。

    - 去重守卫:candidate <= 生效序位 → 零推进返回 False(同序位幂等);
      生效序位 None = 本 run 首建,任何 candidate 放行(处置表 v=None
      首锚定行);
    - 写 node_pos:**source 由调用方定**——动作上报路径 = logic(推进未
      确认态,观察态门语义的前提);锚定补推路径 = observation(观察采新即
      确认态,否则补推后源态落 logic 会把下一次终结动作误挡一拍)。锚定
      直写不经通用 observe()(R>v 与 logic 现值失配会误入观察覆盖失配
      失配告警三分流;节点域专用口先例 = :meth:`settle_truth`);
    - hist 占位(单调水位,元组字典序)+ 效果推进尾段同临界区。
    返回 True = 实际落账推进。
    """
    if source not in ('logic', 'observation'):
        raise ValueError(f'推进原语 source 非法: {source!r}(仅 logic/observation)')
    effective = effective_node_pos(gs)
    if effective is not None and candidate <= effective:
        return False
    if source == 'logic':
        gs.write_logic(gs.node_pos, candidate, produced_by=actor, sig=sig)
    else:
        gs._swap('node_pos', Field(value=candidate, source='observation'), sig=sig)
    if gs.node_hist_pos is None or candidate > gs.node_hist_pos:
        gs.node_hist_pos = candidate
    tick_effect_boundary(gs)
    return True


def report_node_advance(gs: GameState, *, trigger: str,
                        sig: ChannelSig | None = None) -> LogicOutcome:
    """终结动作上报推进(动作路径唯一入口,design §2.3)。

    - 观察态门(design §2.2 **双条件**):node_pos value 在场 ∧ source ==
      observation 才放行——只有已被观察确认的节点值可被动作推进,重复
      上报/重试在结构上不可能。**value 守卫不可省(攻击 R1)**:Field 缺省
      source='observation',新容器 = (None, 'observation'),只查 source 会在
      开局/恢复局误放行且 candidate 在生效序位 None 时无定义;
    - 门挡 → obs_event arbitrate 留存证据零推进;
    - candidate = :func:`cw_node_schedule.sequence_next`(生效序位,场字段
      现值;终结动作语义:上一节点结束进下一节点,位面切换在后继原语内
      发生)→ 经推进生效原语落账(source=logic,推进未确认态,等观察
      锚定);
    - **终局事件式**(candidate = None:P2 末终局确认,或 live P3 锚定后的
      上报)→ 零写入(无后继序位可写)零效果 tick(无节点进入),返回
      ``applied=True, reason='match_end'`` + 声明
      ``WorldDecl(next_screen='', trigger='node_advance')``——终结动作
      落地事实即 applied(**applied 语义扩展申报**:在库「applied = 实际
      推进落账位」单点扩展为「终结动作落地事实(落地但无后继可写)」,
      迭代 2026-10-12-abolish-node-ordinal design §2.2;终局后重复上报恒
      过观察态门重复发出 match_end,零状态破坏,判读按同 run 同一终局
      事件);
    - sig 缺省 = logic_action 族按 trigger actor 构造;显式传入须同族。

    返回 :class:`LogicOutcome`(``applied`` = 实际推进落账位/终局终结
    事实;构造义务 = 动作后果声明化迭代 design.md §2.2 契约 2):落账出口
    随附 ``world_decl``(trigger = ``node_advance``,``next_screen`` 按
    :func:`_node_advance_next_screen` 推导);门挡/零推进出口 =
    ``applied=False`` 且声明 ``None``(对齐「applied=False 零声明」)。
    """
    if trigger not in NODE_ADVANCE_TRIGGERS:
        raise ValueError(f'推进 trigger 集外: {trigger!r}'
                         f'(封闭集 = {sorted(NODE_ADVANCE_TRIGGERS)})')
    actor = _NODE_ADVANCE_ACTORS[trigger]
    if sig is None:
        sig = ChannelSig(family='logic_action', actor=actor, mode='compute',
                         group_id=f'act:{actor}@{gs.write_seq + 1}')
    else:
        _validate_sig(sig, ('logic_action',))
    cur = gs.node_pos
    if cur.value is None or cur.source != 'observation':
        gs.note_obs_event(
            'arbitrate', 'node_pos',
            {'value': cur.value, 'source': cur.source, 'trigger': trigger},
            verdict='观察态门挡(value 在场且 observation 锚定态才可动作推进)',
            sig=ChannelSig(family='obs', actor=actor, mode='read',
                           group_id=f'gate:{actor}@{gs.write_seq + 1}'))
        return LogicOutcome(applied=False, reason='observation_gate_blocked')
    effective = effective_node_pos(gs)
    if effective is None:
        # 不可达(value 在场 ⇒ 生效序位在场;防御性保留)
        return LogicOutcome(applied=False, reason='no_effective_ord')
    candidate = sequence_next(effective, gs.node_seq_by_plane.value)
    if candidate is None:
        # 终局事件式:零写入零效果 tick,applied=True 只申明终结事实
        return LogicOutcome(
            applied=True, reason='match_end',
            world_decl=WorldDecl(next_screen='',
                                 trigger=_NODE_ADVANCE_DECL_TRIGGER))
    advanced = advance_node_effective(gs, candidate, actor=actor,
                                      sig=sig, source='logic')
    if not advanced:
        return LogicOutcome(applied=False, reason='advance_deduped')
    # 占卜屋直登(用户
    # 裁定:黑天鹅在前后台 → 每场战斗结算计数 +1 → 达 2 倍数弹启示卡
    # 三选一)。战斗三型都经 settle_confirm 一腿;出战阵容 = deployed
    # 现读(战斗期间板面无逻辑写路径,结算读即出战阵容);胜负不计,
    # 参与即计。上报点直登,不走值回调(结算非 deployed 写)。
    if trigger == 'settle_confirm':
        from sr_od.application.currency_war.kernel.cw_faction_callbacks import (
            _iter_field_units,
        )
        _view = gs.deployed.value
        _fortune_char = '黑天鹅'
        if any(str(u.char_id) == _fortune_char
               for _r, u in _iter_field_units(_view)):
            _sc = gs.screen_changes
            _sc.fortune_battles += 1
            if _sc.fortune_battles % 2 == 0:
                from sr_od.application.currency_war.kernel.cw_overlay_register import (
                    KIND_SCREEN_NAMES,
                    register_screen_change,
                )
                register_screen_change(
                    gs, 'fortune', KIND_SCREEN_NAMES['fortune'],
                    source=(f's4_battle_count@{_sc.fortune_battles}'
                            '@settle_confirm'))
    return LogicOutcome(
        applied=True, reason=f'node_pos→{candidate[0]}-{candidate[1]}',
        world_decl=WorldDecl(next_screen=_node_advance_next_screen(gs),
                             trigger=_NODE_ADVANCE_DECL_TRIGGER))


def clear_pending_loss(gs: GameState, *, sig: ChannelSig) -> None:
    """败态待清项消费清账(pending_loss 域专用写口)。

    轮首收入败补支(U04 口径)消费后待清项清回 None——None 写 = 待办
    结构性清空(消费事实)非失读,不经通用 observe/write_logic 的
    None 闸(§2.2「禁清正式值」覆盖的是失读形态);域专用直写口先例 =
    节点域 :func:`observe_node_anchor` 的 _swap 直写。消费判据
    (非 supply/reward 节点才消费)归调用方,本口只做清账。"""
    gs._swap('pending_loss',
             Field(value=None, source='logic', evidence='loss:consumed'),
             sig=sig)


def observe_node_anchor(gs: GameState, pos: NodePos, *,
                        trigger_screen: str, actor: str,
                        sig: ChannelSig | None = None) -> str:
    """观察锚定 helper(备战帧顶栏/补给屏节点条两写端共用;design §2.2;
    入参 = (位面,轮) 元组键,调用方零坐标换算义务;旧正解穿参通道
    已停用)。

    **位面在表守卫(前置)**:pos 位面 ∉ 序列表键集(场字段现值,缺省
    默认表)→ 不写任何水位 + obs_event arbitrate 留存证据,返回
    ``out_of_domain_dropped``——读数 = OCR 位面误读形态(如 1↔3),越域
    键写入会毒化单调水位并伪造终局(原先由 kernel 正解抛错承担的
    隐式白名单,键表示下显式化;与 prep 侧 suppress 零写入/supply 侧响亮
    抛错语义等价)。

    处置规则(R = 本帧读数,v = node_pos 现值;比较全元组字典序,跨位面
    形态 (1,10) < (2,1) 自然严格):

    - v = None → **first_anchor**:任何 R 经推进生效原语落账(observation
      确认态;E4 开局建 1/恢复局重建);
    - R > v → **advance**:采新经原语(observation;补推 = 漏上报自愈,
      序位前进同帧拿到效果尾段);
    - R == v → **reanchor**:直写同值(observation;logic 态此分支 = 动作
      推进被观察确认翻锚定态,下一终结动作由此解锁);
    - R < v → **stale_dropped**:倒退免疫,不写 + obs_event arbitrate 留存证据
      (读数误读或幻影推进残余;键表示无累积误差,偏差有界一个观察
      周期)。

    写端不经通用 observe():R>v 与 logic 现值失配会误入观察覆盖失配告警
    三分流;本 helper 直写 Field(source='observation')(节点域专用口,先例
    = :meth:`settle_truth`)。sig 缺省 = obs 族按宿主 op 登记名构造。
    返回处置 token(first_anchor/advance/reanchor/stale_dropped/
    out_of_domain_dropped)。
    """
    if sig is None:
        sig = ChannelSig(family='obs', actor=actor, screen=trigger_screen,
                         mode='read', group_id=f'anchor:{actor}@{gs.write_seq + 1}')
    else:
        _validate_sig(sig, ('obs',))
    _seqs = gs.node_seq_by_plane.value
    _tables = _seqs if _seqs is not None else PLANE_NODE_TABLES
    if int(pos[0]) not in _tables:
        gs.note_obs_event(
            'arbitrate', 'node_pos',
            {'reading': f'{pos[0]}-{pos[1]}'},
            verdict='越域读数丢弃留证(位面无序列表;OCR 位面误读形态,'
                    '禁写水位防伪造终局)',
            sig=sig)
        return 'out_of_domain_dropped'
    v = gs.node_pos.value
    if v is None:
        advance_node_effective(gs, pos, actor=actor, sig=sig,
                               source='observation')
        return 'first_anchor'
    if pos > v:
        advance_node_effective(gs, pos, actor=actor, sig=sig,
                               source='observation')
        return 'advance'
    if pos == v:
        gs._swap('node_pos', Field(value=v, source='observation'), sig=sig)
        return 'reanchor'
    gs.note_obs_event(
        'arbitrate', 'node_pos',
        {'reading': f'{pos[0]}-{pos[1]}', 'current': f'{v[0]}-{v[1]}'},
        verdict='倒退读数丢弃留证(倒退免疫;R<v 不写)',
        sig=sig)
    return 'stale_dropped'


def _write_derived_node_type(gs: GameState, kind: str, *, target_pos: NodePos,
                             actor: str, trigger_screen: str, seq: int) -> None:
    """类型派生写入(§3.4.1 类型派生;经节点域③格写 gs.node,§3.1.3):
    专属画面直定该节点类型,NodeKey 由目标序位直建(键表示唯一,迭代
    2026-10-12-abolish-node-ordinal design §2.3,反解构造已停用)。

    - 倒退免疫(R3 规则三同簇,20260918-reconcile 第 11 例收束):镜像
      现值序位 > 目标序位(元组字典序)= 镜像比派生目标鲜活(读链已在
      店开帧写新节点),直定旧节点会把新节点回写旧键 → 丢弃留存证据不写
      (obs_event arbitrate),类型由镜像源(读链 votes/后继帧)承接;
    - 冲突纪律(G10 同簇):镜像现值已在目标节点且类型不一致 → obs_event
      留存证据(event='arbitrate',禁静默覆盖)+ 最新直定值落位(最新观察 =
      真相);直定证据 = 画面现身锚,属观察级事实,sig 走 obs 族
      (note_obs_event 契约),actor = 触发规则登记名保留归因;
    - 已知边界(申报):直定屏重入/缓存滞后形态下目标 = hist,若历史
      推进与屏所属节点错位,倒退免疫丢弃留存证据(不落错键);目标序位 ≥ 镜像
      序位的错位形态类型照落,后续备战帧真读类型经
      观察覆盖核对(§2.3 以实际观察为准)——真失配才走三分流;
    - 商店面板块不专属 → 零直定(observe_screen_context 商店分支查现行链),
      类型「未定型」零写;查现行链接口 = :func:`chain_node_type`。现役专属
      画面直定写端 = BOSS 简报屏(kernel/cw_screen_report/boss_briefing)
      与商店查链两处,actor = 宿主登记名保留归因。
    """
    key = NodeKey(plane=target_pos[0], round_num=target_pos[1], kind=kind)
    cur = gs.node.value
    # 直定倒退免疫比较:元组字典序直判(键表示下零序列查询依赖)。
    if cur is not None and (int(cur.plane), int(cur.round_num)) > target_pos:
        gs.note_obs_event(
            'arbitrate', 'node',
            {'mirror': f'{cur.plane}-{cur.round_num}-{cur.kind}',
             'target_pos': f'{target_pos[0]}-{target_pos[1]}',
             'target_kind': kind},
            verdict='类型直定倒退丢弃留证(R3 规则三倒退免疫;镜像序位 > '
                    '目标序位,不回写旧节点)',
            sig=ChannelSig(family='obs', actor=actor, screen=trigger_screen,
                           mode='read',
                           group_id=f'hook:{actor}@{seq}'))
        return
    if cur is not None and cur.plane == key.plane \
            and cur.round_num == key.round_num and cur.kind != kind:
        gs.note_obs_event(
            'arbitrate', 'node',
            {'old_kind': cur.kind, 'new_kind': kind,
             'node_pos': f'{target_pos[0]}-{target_pos[1]}'},
            verdict='类型直定冲突留证(同节点两直定值不一致,最新直定赢)',
            sig=ChannelSig(family='obs', actor=actor, screen=trigger_screen,
                           mode='read',
                           group_id=f'hook:{actor}@{seq}'))
    _derive_write(gs, gs.node, key, actor=actor,
                  trigger_screen=trigger_screen, seq=seq)


# ============================================================ 现行链查询接口(件 B 设计 v1.1 §3.4 语义预留,R1.2)

@dataclass(frozen=True)
class ChainQuery:
    """现行链单点查询返回值(件 B 设计 v1.1 §3.4 接口语义;R1.2 只落形态,
    查链接线归件 B 实施):

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

    - 载体 = :class:`NodeChain`(list[str] 旧形
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
    变异窗内豁免并清候选(窗关后按两帧确认补比对)。发出 = note_obs_event
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


def _unit_from_dict(d: dict) -> Unit:
    """Unit 快照 dict 重建单一源(restore 各重建点共用;宽容读:
    缺席字段走值缺省)。"""
    return Unit(char_id=str(d.get('char_id') or ''),
                star=int(d.get('star') or 1),
                equips=list(d.get('equips') or []))


def _restore_deployed_view(d: dict) -> DeployedView:
    """快照 deployed 域重建(值形状 = DeployedView 序列化 dict;
    元素 Unit dict 缺席/畸形 → None 空槽,宽容读契约;旧档迁移腿
    传入的是已构建的 DeployedView 实例 → 直通透传)。"""
    if isinstance(d, DeployedView):
        return d
    front = [(_unit_from_dict(u) if isinstance(u, dict) else None)
             for u in (d.get('front_slots') or [])]
    while len(front) < DEPLOYED_FRONT_CAPACITY_DEFAULT:
        front.append(None)
    back = [(_unit_from_dict(u) if isinstance(u, dict) else None)
            for u in (d.get('back_slots') or [])]
    while len(back) < DEPLOYED_BACK_CAPACITY_DEFAULT:
        back.append(None)
    return DeployedView(front_slots=front, back_slots=back)


def _migrate_rows_snapshot_to_deployed(front_raw, back_raw) -> DeployedView:
    """旧档迁移函数单一实现(schema 1 紧凑行域两列表 → DeployedView;
    快照兼容:restore 兼容面 = 本函数一处,接管恢复
    行为等价)。

    旧档 Unit dict 自带 slot 信息位(1 基排内画面槽号)——按槽位落位;
    缺席(0)/越界按占用序顺延兜底(与旧 ``deployed_rows_to_indexed``
    兼容口径同向)。第二账簿记(tracked 第二账)已停用,非 Field 本就不入快照流水,无迁移面。"""
    def _place(units_raw, cap: int) -> list[Unit | None]:
        out: list[Unit | None] = [None] * cap
        cursor = 0
        for u in (units_raw or []):
            if not isinstance(u, dict):
                continue
            unit = _unit_from_dict(u)
            s = int(u.get('slot') or 0)
            idx = s - 1 if 1 <= s <= cap else -1
            if idx < 0 or out[idx] is not None:
                while cursor < cap and out[cursor] is not None:
                    cursor += 1
                idx = cursor if cursor < cap else -1
                cursor += 1
            if idx >= 0:
                out[idx] = unit
        return out

    front = _place(front_raw, DEPLOYED_FRONT_CAPACITY_DEFAULT)
    back_cap = max(DEPLOYED_BACK_CAPACITY_DEFAULT,
                   max((int(u.get('slot') or 0) for u in (back_raw or [])
                        if isinstance(u, dict)), default=0))
    back = _place(back_raw, back_cap)
    return DeployedView(front_slots=front, back_slots=back)


def restore_state_snapshot(gs: GameState, snap: dict) -> None:
    """行内 state 快照 → 容器域恢复(回放/Δ池 journal 的
    离线判读面;序列化 = :meth:`GameState.full_state_snapshot`)。

    - 直 setattr 重建 Field(绕 _swap:零流水行、零版本分配——恢复是
      离线读面非生产写路径);values 键缺位 = 域保持 None(快照只存
      非 None 值的口径往返一致);
    - 复杂域按字段名重建(node/deployed/bench/shop/ore_rewards/
      ore_declared_pending/ore_declared_done/env_grants_done/
      node_seq_by_plane/node_pos;
      _json_safe 无类型标,恢复表 = 字段名单一源),其余域直透
      (标量/list/dict 形态值);
    - **旧档迁移**(schema 1 → 2):values 携 front_row/back_row 两键而
      无 deployed 键 = 旧紧凑行域档 → 经 :func:`_migrate_rows_snapshot_
      to_deployed` 单次转换落 deployed(槽位语义等价;快照兼容面收束
      于迁移函数一处);新档两键均不现;
    - **旧编号键忽略(零迁移)**:编号表示存档的 ``node_ord`` 值键与
      ``node_hist_ord`` 顶层键不在现容器字段面(getattr 落空/顶层不读)
      自然忽略——历史语料不迁移(离线判读面裁定,键表示切换批
      2026-10-12-abolish-node-ordinal design §2.8),零迁移函数;
    - source/evidence 取 prov 面(缺 = observation/None 缺省);
    - write_seq/工程结构不恢复(判读面不需要版本续接)。
    """
    values = snap.get('values') if isinstance(snap, dict) else None
    if not isinstance(values, dict):
        return
    if 'deployed' not in values \
            and ('front_row' in values or 'back_row' in values):
        values = dict(values)
        values['deployed'] = _migrate_rows_snapshot_to_deployed(
            values.get('front_row'), values.get('back_row'))
        values.pop('front_row', None)
        values.pop('back_row', None)
    prov = snap.get('prov') if isinstance(snap.get('prov'), dict) else {}

    def _bench_view(d: dict) -> BenchView:
        slots: list[BenchSlot] = []
        for sd in d.get('slots') or []:
            sd = sd if isinstance(sd, dict) else {}
            u = sd.get('unit')
            slots.append(BenchSlot(
                kind=str(sd.get('kind') or 'empty'),
                unit=_unit_from_dict(u) if isinstance(u, dict) else None))
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
        'deployed': _restore_deployed_view,
        'bench': _bench_view,
        'shop': _shop_payload,
        # 晶矿附着奖励与声明通道三域(迭代 2026-10-10-ore-reward-attach):
        # _json_safe 无类型标(dataclass→dict/tuple→list),不登记则恢复面
        # 拿 dict-of-dicts/list-of-lists 静默类型漂移。done 随快照存续 =
        # 恢复局(离线回放)不重发声明。
        'ore_rewards': lambda d: {str(k): OreReward(**v)
                                  for k, v in d.items()},
        'ore_declared_pending': lambda d: tuple(
            (str(e[0]), int(e[1]), int(e[2])) for e in d),
        'ore_declared_done': lambda d: tuple(
            (str(e[0]), int(e[1])) for e in d),
        # 环境条件发放已发标记(迭代 2026-10-10-env-conditional-grants):
        # tuple 化重建(_json_safe 落快照为 list-of-lists),done 随快照
        # 存续 = 恢复局不重发(触发函数守卫天然闭合)。
        'env_grants_done': lambda d: tuple(
            (str(e[0]), str(e[1])) for e in d),
        # 逐位面节点序列场字段():键 int 化 + 值 tuple 化重建
        # (_json_safe 落快照为 str 键 dict-of-list);随快照存续 = 修饰局
        # 恢复坐标系不断。None 值域不在快照(只存非 None,往返一致)。
        'node_seq_by_plane': lambda d: {
            int(k): tuple(str(x) for x in v) for k, v in d.items()},
        # 节点序位两件套(键表示切换批:_json_safe 落快照为 [p, r] list,
        # tuple 化重建;NodePos = (位面,轮) 元组键)。
        'node_pos': lambda d: (int(d[0]), int(d[1])),
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
# (kernel 决策簇签名切 GameState 后的值读单一源。
#  未观察字段在容器侧是 None,读口负责返回旧决策簇契约的缺省值,
#  禁各消费点自写兜底造成第二源。)


def plane_of(gs: GameState) -> int:
    """位面读口(未观察缺省 1 = 引导窗)。"""
    node = gs.node.value
    return int(node.plane) if node is not None else 1


def round_num_of(gs: GameState) -> int:
    """轮次读口(未观察缺省 1)。"""
    node = gs.node.value
    return int(node.round_num) if node is not None else 1


def node_kind_of(gs: GameState) -> str | None:
    """节点类型读口(None = 未识别)。"""
    node = gs.node.value
    return str(node.kind) if node is not None else None


def gold_of(gs: GameState) -> int:
    """金读口(未观察缺省 0;可读保真位另经 :attr:`Field.source` 判,
    读口只供值)。"""
    v = gs.gold.value
    return int(v) if v is not None else 0


def level_of(gs: GameState) -> int:
    """等级读口(未观察缺省 1)。"""
    v = gs.level.value
    return int(v) if v is not None else 1


def deployed_rows_of(gs: GameState) -> tuple[list[Unit], list[Unit]]:
    """上阵席位行域读口(容器原生,benchchar-retirement §2.1 计算形状):
    ``deployed`` 视图 → 紧缩单位行(前排在前,空槽跳过;子表序 = 物理
    槽序),行内元素即容器 ``Unit``;视图未观察(None)按空行计(缺行 =
    空行缺省)。紧缩序不含位置信息——需要物理槽位的消费面(装备分配
    occupied 键/落位计划)改读 ``gs.deployed.value`` 视图按下标直址,
    禁从本口输出反推槽位。"""
    return deployed_rows_of_view(getattr(gs.deployed, 'value', None))


def bench_units_of(gs: GameState) -> list[Unit]:
    """备战席单位读口(容器原生):BenchView 槽序中 ``kind='unit'`` 槽的
    内嵌 ``Unit``(frozen 本体,顺序 = 物理槽序);bench 未观察 = []。
    单位域读口——占位件(kind ∈ tome/bookcard/supply_box)与空槽不计,
    占位件消费面走 ``gs.bench.value.slots`` kind 面。"""
    view = gs.bench.value
    if view is None:
        return []
    return [s.unit for s in view.slots
            if s is not None and s.kind == 'unit' and s.unit is not None]


def bench_entries_of(gs: GameState) -> list[BenchSlot]:
    """备战席占席条目读口(容器原生,紧缩序):BenchView 槽序中占席槽
    (``kind != 'empty'``,单位与占位件都在内)的 ``BenchSlot``,顺序 =
    物理槽序;bench 未观察 = []。判定/资格循环输入域(占位件恒在域内,
    由消费端按 kind 分流);只要单位身份的读数走 :func:`bench_units_of`。"""
    view = gs.bench.value
    if view is None:
        return []
    return [s for s in view.slots if s is not None and slot_occupies(s.kind)]


def bench_view_slots_of(gs: GameState) -> list[BenchSlot | None]:
    """备战席槽位表读口(容器原生,全槽含空):BenchView.slots 原序
    (slots[i] = 物理槽 i+1;空槽与占位件都在域内);bench 未观察 = []。
    守卫/对位类消费(按容器下标取槽、断言槽身份);身份读数经
    ``cw_exec_state.bench_slot_unit`` 解包。"""
    view = gs.bench.value
    return list(view.slots) if view is not None else []


def back_capacity_of(gs: GameState) -> int:
    """后排格数读口:
    back_layout 真值(值域 6-9,平常 6/宝钻扩展 7/8/9,>9 域外 8 格超集);
    未观察帧退机制基线 6。

    ⚠️ 语义修正申报(调研草案 §4/风险 7):静态 6 基线
    与实局 7/8 不符,本读口起消费面拿到动态真值——cap 封顶与
    后排容量门输出随之修正,行为差由 cap 域测试(test_cw_cap_domain/
    test_cap_override_link)重推语义覆盖。单一源:``max_units_of`` 封顶
    域与本读口同式,禁消费面内联第二份。"""
    back = gs.back_layout.value
    return int(back) if back is not None else 6


def deployed_count_of(gs: GameState) -> int:
    """上阵占用数读口(容器原生,占用数口径非 len):两行现值
    单位计数(deployed_rows_of 缺行 = 空行缺省)。"""
    front, back = deployed_rows_of(gs)
    return len(front) + len(back)


def front_count_of(gs: GameState) -> int:
    """前排人数读口(容器原生):前排行成员计数(排归属 = 容器行域,
    §2.1 排归属由行承载;占位判定 = 行成员身份,非按槽段计)。"""
    front, _ = deployed_rows_of(gs)
    return len(front)


def back_count_of(gs: GameState) -> int:
    """后排人数读口(容器原生;口径同 :func:`front_count_of`)。"""
    _, back = deployed_rows_of(gs)
    return len(back)


def max_units_of(gs: GameState) -> int:
    """可上阵数容器版派生(公共读口单一源):deploy_cap 真值(≥level
    才采信,防抖漏网兜底
    level)封顶 = 前排恒 4 + back_layout 动态真值(缺省 6 = 机制基线,
    值域 6-9;封顶域单一源 =
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

    - **结构性豁免不扩修**:投影判据链以 session=None 求值 →
      利息帽 resolved 链恒 base 口径、节点日程走缺表回退先验——契约不变,
      扩修挂该调用面的 session 通道批;
    - **字段契约自覆盖于本 docstring**:
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
    - actor = 本函数登记名(写入者身份;evidence 沿 sim 合成证据串,
      投影行为语义与 sim 真值同族)。
    """
    gs = GameState(schema_version=GAME_STATE_SCHEMA_VERSION)
    global _STATE_JOURNAL_SINK
    _saved_sink = _STATE_JOURNAL_SINK
    _STATE_JOURNAL_SINK = None
    try:
        _ev = SIM_SYNTHESIZED
        _sig = ChannelSig(family='obs', actor='scalar_projection_state',
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


