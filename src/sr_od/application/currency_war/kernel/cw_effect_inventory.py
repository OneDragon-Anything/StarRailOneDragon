"""货币战争 active effect inventory(在场效果清单)——效果模型机制层(骨架实现)。

**定位**(骨架契约经效果清单专项设计评审定稿;框架源 = 淘金客效果规格报告 Part 1):
- 本文件只放**机制**(类型 + inventory 读端/追踪端纯逻辑);
- **数据**(哪些策略是什么效果)在 ``cw_investments.STRATEGY_EFFECTS`` overlay——
  与 ``STRATEGY_ECONOMY`` 同键空间同构建校验,防两套手维护面漂移;
- 生产与 sim 同一实现(sim 结算效果时同步维护 inventory;效果规格契约);
- **零决策行为**:任何决策路径不消费本模块产出——查表接入归后续
  姿态面/执行预判面。

**EffectSpec 四元组**(每条策略 = 一条效果规格):
触发时机(trigger)× 持续期(duration)× 效果类型(category)× bot 待办(duties),
payload 承载效果数值/战场语义;经济/状态类复用 ``cw_investments.EconomyEffect``
同一实例(单一源,不复制字段)。

**上游关系**:本模块是效果规格的登记侧;消费端派生视图(DP 日程/突变聚合,
原 v0 规划)不存在,消费接缝出现时按需重建。

**文末附加段**:账本→字段桥与结算收口诸段——板面重写(:func:`apply_board_rewrite`)、
装备改写写端(写端桥/贡献算术,装备申报面 = cw_affix_effects
EQUIP_REWRITE_DECLARATIONS × EQUIP_WRITE_SIDES)、节点边界金结算载体
(贡献算术的组合写收口 + 精密扳手获得回执窗)、穿域特权化腿(特权赋予卡
拖角色腿,归工具执行批)、拷贝仪参与计数载体(装备效果进度侧栏)——把
效果声明翻译成 GameState 字段写入归属,宿主放本侧的原因与惰性 import
纪律见各段头注。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log

if TYPE_CHECKING:
    # 仅类型注解引用(项目规范允许);运行时 payload 按对象持有,
    # 类型一致性校验在 cw_investments 构建层(那里有真类)做 isinstance。
    # GameState 仅注解用:cw_game_state 模块头反向 import 本模块(容器
    # effects 字段载体),模块级 import 会成环;文末诸桥运行期
    # 经函数内惰性 import 取真类。cw_economy 仅注解用(LostNodeRef):
    # 它模块头拉 cw_investments → 后者 import 本模块,模块级 import 成环。
    from sr_od.application.currency_war.kernel.cw_economy import LostNodeRef
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchView,
        ChannelSig,
        GameState,
        Unit,
    )
    from sr_od.application.currency_war.kernel.cw_investments import (
        EconomyEffect,
        EnvEconomyEffect,
    )


class TriggerKind(StrEnum):
    """效果触发时机(语义出自效果规格设计评审定稿)。"""
    INSTANT = 'instant'            # 选卡当场结算(即时金/全场重写类)
    PLANE_START = 'plane_start'    # 每个位面开始时(固定理财)
    NODE_ENTER = 'node_enter'      # 进入节点时(特战资金/Gemi狸免费刷)
    BATTLE_END = 'battle_end'      # 战斗结算时(气氛组系)
    LEVEL_UP = 'level_up'          # 升级时(节节高升;商业间谍战场段)
    ON_REFRESH = 'on_refresh'      # 每次刷新时(淘金客/概率事件/采购专员计数)
    ON_MERGE = 'on_merge'          # 合成时(武力刷新=合成装备时,官方限定;角色升星是否同触发面待裁决——GameState 设计 §5 星星相印)
    ON_SELL = 'on_sell'            # 出售时(降本增效语义面)
    SUPPLY_PHASE = 'supply_phase'  # 补给阶段
    CONDITIONAL = 'conditional'    # 条件窗口(躺平冻结/经验就是财富改道/成长基金到级)


class DurationKind(StrEnum):
    """效果持续期。"""
    ONCE = 'once'              # 一次性
    PERMANENT = 'permanent'    # 持有期永久
    N_NODES = 'n_nodes'        # 持续 duration_nodes 个节点(躺平 3 节点)
    WHILE_HELD = 'while_held'  # 与持有绑定(策略卡缺省;独立值供词缀源对齐语义)


class EffectKind(StrEnum):
    """效果类型四分类(效果规格设计评审定纲)。"""
    ECONOMY = 'economy'          # 经济改变(金/XP/刷新/利息流)
    STATE = 'state'              # 状态改变(发给自己的经验/金/血)
    BATTLEFIELD = 'battlefield'  # 战场改变(商店改写/偷牌/板面重掷/自动操作)
    UNIT_BUFF = 'unit_buff'      # 单位强化(游戏侧自算,bot 仅登记零响应)


@dataclass(frozen=True)
class DutyFlags:
    """bot 待办标志(「识」= 识别入 inventory 是所有条目缺省义务,不设位)。"""
    track: bool = False    # 需 inventory 计数器/剩余期
    predict: bool = False  # 执行动作前置知识(shop 读牌/买牌对账须预知)
    respond: bool = False  # 决策姿态改变


@dataclass(frozen=True)
class BattlefieldEffect:
    """战场改变族 payload(只建类型;数值随条目按官方原文填,不猜)。"""
    shop_rewrite: bool = False              # 商店改写(采购专员同费面/市场干预 3 费面)
    steal_on_level_up: int = 0              # 升级时偷商店最贵 N 张(商业间谍=3)
    auto_buy_owned: bool = False            # 自动购买场上已有角色(Gemi狸)
    free_refresh_on_node_enter: int = 0     # 进节点免费刷 N 次(Gemi狸=2)
    board_rewrite: str = ''                 # 板面重写语义(取值 = 板面重写语义词表
                                            # BOARD_REWRITE_*;写归属桥 =
                                            # apply_board_rewrite)
    bench_reroll: str = ''                  # 备战席区间重掷(乱成一锅粥族;未建条目)
    counter_every: int = 0                  # 每 N 次刷新计数门槛(采购专员金 7/彩 5)
    first_merge_equip_junk: float = 0.0     # 每位面首次合成进阶装备变垃圾袋概率(变宝为废=0.5;
                                            # 随机面→不建逻辑写,观察收口)


@dataclass(frozen=True)
class UnitBuffRef:
    """单位强化引用(官方效果原文;~155 条游戏侧自算,bot 零响应;效果规格判读)。"""
    effect_text: str


@dataclass(frozen=True)
class EffectSpec:
    """一条投资策略的效果规格(四元组 + 二义标注)。

    - id/name 必须与 ``cw_invest_data.PLAZA_AUGMENTS`` 官方条目一致(构建层校验
      id+name 双匹配,改名/移除 import 即炸);环境源条目 id/name 对
      ``PLAZA_PORTALS`` 同款校验(_validate_env_portal_effects)。
    - payload 类型与 category 的对应:ECONOMY/STATE→EconomyEffect、
      BATTLEFIELD→BattlefieldEffect、UNIT_BUFF→UnitBuffRef(构建层校验);
      环境源经济条目 ECONOMY→EnvEconomyEffect(整局规则通道,与 per-node
      形态的 EconomyEffect 分型,值单一源 = cw_investments.ENV_ECONOMY)。
    - pending/verdict:效果文本二义条目 pending=True,**不拍死**——verdict 保持
      None 直到实采定谳;消费端见 pending=True 必须走
      notes 声明的保守支。
    """
    id: str                       # plaza 稳定 id(cw_invest_data 主键)
    name: str                     # 规范名(canon,=注册表键;禁昵称,如 Gemi狸 的
                                  # 官方卡名是「双手狸开键盘！」,见 204101)
    trigger: TriggerKind
    duration: DurationKind
    category: EffectKind
    payload: EconomyEffect | BattlefieldEffect | UnitBuffRef | EnvEconomyEffect
    duties: DutyFlags = DutyFlags()
    duration_nodes: int = 0       # N_NODES 类的持续节点数;**自然数计数非索引**(躺平=3);
                                  # 恒稳(注册期常量,登记时拷入 ActiveEffect.remaining_nodes)
    duration_uses: int = 0        # 次数类余量种子(免战牌=2,官方「可生效2次」;§3.2.19
                                  # 正本=ActiveEffect.remaining_uses,§8.6-3);恒稳
                                  # (注册期常量,登记时拷入 ActiveEffect.remaining_uses)
    pending: bool = False         # True=效果文本有二义未实采定谳
    verdict: str | None = None    # 实采定谳回填('改道吞引擎XP' 等);None=未定谳
    notes: str = ''               # 语义出处与歧义内容(pending 条目必写保守支)


# ===== 计数器键常量(键名不散落字符串,防漂移)=====
class CounterKey:
    REFRESH = 'refresh'   # 刷新计数(采购专员门槛/Gemi狸;按策略触发面)
    BUY = 'buy'           # 购买计数(返利系每 3 张 5 费)
    REFRESH_TOTAL = 'refresh_total'   # 刷新全量累计(免费+付费;二手市场阈值评估)
    REFRESH_PAID = 'refresh_paid'     # 付费刷新累计(长线利好「花费金币进行30次刷新」)


# ===== 效果来源词表(ActiveEffect.source 取值;防散落字符串)=====
# 辖域:策略源=选卡登记(register_strategy);词缀源=敌人词缀改写源,结构化
# 注册=kernel/cw_affix_effects.AFFIX_EFFECT_SPECS(register_affix 登记);
# 环境源=投资环境辖域,结构化条目=ENV_PORTAL_EFFECTS(经济环境)+未入模
# 占位(register_portal_from_env 登记,design.md §2.4)。
SOURCE_STRATEGY: str = 'strategy'
SOURCE_PORTAL: str = 'portal'
SOURCE_AFFIX: str = 'affix'


# ===== 板面重写语义词表(BattlefieldEffect.board_rewrite 取值;防散落字符串)=====
# 在册条目 = 全员晋升/人力重组(cw_investments.STRATEGY_EFFECTS,官方文
# cw_invest_data.py:67/:68);写入归属两行单一源 =
# docs/develop/sr_od/application/currency_war/game_state/effect-domain.md §8 同名条(全员晋升/人力重组)。
BOARD_REWRITE_UPGRADE_ALL: str = 'upgrade_all_cost+1'   # 整场上阵替换:全场升为
                                                        # 高 1 费随机角色(最大 5 费)
BOARD_REWRITE_SELL_ALL: str = 'sell_all'                # 全场出售+再发牌:清场退款,
                                                        # 再发 2★ 随机角色进席


# 事件标记键(追踪端标记,非策略计数器;下划线前缀与策略计数器空间隔离)
_EVENT_LEVEL_UP = '_event_level_up'
_EVENT_BATTLE_END = '_event_battle_end'


@dataclass
class ActiveEffect:
    """一条在场效果实例(spec + 来源 + 登记时点 + 余期/计数器)。"""
    spec: EffectSpec
    source: str                # 取值=SOURCE_* 词表('strategy'/'portal'/'affix');
                               # strategy=策略源,affix=词缀源(登记端 register_affix),
                               # portal=环境源(登记端 register_portal_from_env,
                               # 结构化条目=ENV_PORTAL_EFFECTS,design.md §2.4)
    acquired_t: int | None     # 登记时点;节点序 = (plane-1)*9+round,**基 1**;
                               # 登记期快照(与 cw_loop _now_t 同式)
    remaining_nodes: int | None  # N_NODES 类余期;**自然数计数非索引**;None=不限;
                                 # 挂点(tick_node)现读递减
    remaining_uses: int | None   # 次数类余量(免战牌×2 等);挂点现读递减
    counters: dict[str, int] = field(default_factory=dict)   # CounterKey 键 → 计数


class ActiveEffectInventory:
    """在场效果清单(宿主 = GameState.effects)。纯数据 + 读端/追踪端;零 import 包内模块(可离线单测)。

    写端(挂点)生产接线(迁移批次三,设计 §5.1/§8.7 批次三;单一实例 =
    GameState.effects,session 无独立字段——历史兼容读口 property 已撤,
    写读直经 game_state_of(session).effects,载体归一防双账本):选卡登记 = CwScreenInvestStrategy 确认落地(免战牌同点
    自动登记);节点 tick = cw_loop 备战分支(进节点边界);计数 bump =
    cw_op_buy_cards 执行落地门(刷新/购买);跳过递减 = kernel
    出战 op 自上报(report_action_start_battle_param;批④ 前身 = cw_exec_state.apply_op_effect)
    runner 包络上报,上报时递减——出战域重设计 T-286);升级标记 =
    prep_actions._level_up
    (既有);结算挂点 = CwScreenBattleWait 结算观察写端(_record_round_outcome
    非 telemetry_only 分支,apply_settlement_cover 同分支同时序;现役注册表
    零 BATTLE_END 条目 = 零效果条目推进,零条目 = 零驱动,effect-domain
    §7.4)。
    """

    def __init__(self) -> None:
        self.entries: list[ActiveEffect] = []
        # 事件标记:键 → 计数(_EVENT_* 常量);on_level_up/on_battle_end 写
        self._events: dict[str, int] = {}
        # 节点 tick 去重键(最近已推进的节点序;None=未推进过)。挂点每备战
        # 环采样,同节点多次调用只推进一次——去重键是 tick 幂等性的载体,
        # 随清单实例走(session 级生命周期,新局天然清零)。
        self._last_tick_node: int | None = None
        # 装备效果进度侧栏(拷贝仪参与计数载体首用):键 = (装备名, 装备者
        # char_id),值 = 单调计数器。装备源效果无 EffectSpec 实例(
        # 申报面纪律:装备写端 = 桥/贡献算术直读 GameState),其进展量
        # 无实例可挂,落本册侧栏——session 级生命周期与实例清单同源,
        # 计数语义同 §3 单调计数器模型(从 0 起、事件 +1、永不重置)。
        self.equip_progress: dict[tuple[str, str], int] = {}
        # 刷新计数组(2026-09-18 用户裁决:自 GameState Fields 迁入效果
        # 账本统一计算;写端 = 刷新上报函数 report_action_refresh_shop_param
        # 统一触发,消费方 = env_economy 选卡评估通道 + 免费闸):
        self.refresh_total: int = 0           # 全量累计(免费+付费)
        self.refresh_paid: int = 0            # 付费累计(长线利好阈值型)
        self.free_refresh_balance: int = 0    # 免费刷新余额(效果发放 +/刷新执行 −)

    # —— 登记端 ——
    @staticmethod
    def _seed_progress(spec: EffectSpec) -> tuple[int | None, int | None]:
        """余期播种双轨(登记端共用):N_NODES → remaining_nodes=duration_nodes;
        duration_uses>0 → remaining_uses=duration_uses(次数类,免战牌首例,
        §3.2.19)。两类维度同装一条记录(§5.1 账本形状),互不排斥。
        """
        return (
            spec.duration_nodes if spec.duration == DurationKind.N_NODES else None,
            spec.duration_uses if spec.duration_uses > 0 else None,
        )

    def _register(self, spec: EffectSpec, source: str,
                  acquired_t: int | None) -> ActiveEffect:
        """登记端共用体:spec + 来源 + 登记时点入清单(acquired_t 坐标系见
        ActiveEffect.acquired_t;余期播种见 _seed_progress)。"""
        remaining_nodes, remaining_uses = self._seed_progress(spec)
        entry = ActiveEffect(
            spec=spec, source=source, acquired_t=acquired_t,
            remaining_nodes=remaining_nodes, remaining_uses=remaining_uses,
        )
        self.entries.append(entry)
        return entry

    def register_strategy(self, spec: EffectSpec, acquired_t: int | None) -> ActiveEffect:
        """策略获得 → 入清单。"""
        return self._register(spec, SOURCE_STRATEGY, acquired_t)

    def register_affix(self, spec: EffectSpec, acquired_t: int | None) -> ActiveEffect:
        """词缀效果获得 → 入清单(source=affix;结构化注册 =
        kernel/cw_affix_effects.AFFIX_EFFECT_SPECS,spec.id = 词缀名)。

        生产登记挂点已接线:简报读链(CwScreenBriefing._read_and_advance
        开局首读)与位面详情补采通道(CwScreenPlaneIntel.close_and_report)
        经共用登记体 cw_affix_effects.register_affixes_from_names 调本方法
        (幂等 + 注册表命中才登记,best-effort 不阻塞读链主链)。词缀改写面
        写端仍一律观察覆盖兜底(写入归属单一源 = 各 spec.notes 与
        cw_affix_effects.EQUIP_REWRITE_DECLARATIONS 申报面);本方法承诺
        登记语义与策略源同轨(余期播种/推进/到期共用同一套挂点逻辑)。
        """
        return self._register(spec, SOURCE_AFFIX, acquired_t)

    def register_portal(self, spec: EffectSpec, acquired_t: int | None) -> ActiveEffect:
        """投资环境效果获得 → 入清单(source=portal;结构化条目 =
        :func:`ENV_PORTAL_EFFECTS`(经济环境),未入模环境走
        :func:`register_portal_from_env` 运行期构造的 UnitBuffRef 占位
        spec——两类条目同经本方法入册,登记语义与策略/词缀源同轨
        (余期播种/推进/到期共用同一套挂点逻辑)。

        生产登记挂点 = CwScreenInvestEnv._decide_and_act 确认链
        (active_env 写入同址,invest-env 迭代 design.md §2.4;best-effort
        失败不阻塞确认链,effect-domain.md §7.3 登记面纪律同词缀源)。
        """
        return self._register(spec, SOURCE_PORTAL, acquired_t)

    # —— 查表端(形状保证;决策消费归后续)——
    def by_source(self, source: str) -> list[ActiveEffect]:
        """按来源词表(SOURCE_*)过滤——词缀源读端(消费接线归后续)。"""
        return [e for e in self.entries if e.source == source]

    def by_category(self, category: EffectKind) -> list[ActiveEffect]:
        return [e for e in self.entries if e.spec.category == category]

    def by_trigger(self, trigger: TriggerKind) -> list[ActiveEffect]:
        return [e for e in self.entries if e.spec.trigger == trigger]

    def first(self, spec_id: str) -> ActiveEffect | None:
        for e in self.entries:
            if e.spec.id == spec_id:
                return e
        return None

    def counter(self, spec_id: str, key: str) -> int:
        """按 (spec_id, key) 读计数——多策略同 key 天然隔离,不串账。"""
        e = self.first(spec_id)
        return e.counters.get(key, 0) if e is not None else 0

    _ACTION_TRIGGER: dict[str, TriggerKind] = {
        'level_up': TriggerKind.LEVEL_UP,
        'refresh': TriggerKind.ON_REFRESH,
        'node_enter': TriggerKind.NODE_ENTER,
        'battle_end': TriggerKind.BATTLE_END,
    }

    def predict_for(self, action: str) -> list[ActiveEffect]:
        """执行动作 → 需前置知(predict)的在效果集。

        action 映射见 _ACTION_TRIGGER;未知 action 保守返回**全部** predict 条目
        (漏预知的代价是读牌/对账误判,多给不错给)。
        """
        trigger = self._ACTION_TRIGGER.get(action)
        if trigger is None:
            return [e for e in self.entries if e.spec.duties.predict]
        return [e for e in self.entries
                if e.spec.duties.predict and e.spec.trigger == trigger]

    # —— 追踪端(挂点调用;纯逻辑,sim 与生产同一实现)——
    def advance_node(self, node_ordinal: int | None = None
                     ) -> tuple[bool, list[ActiveEffect]]:
        """进节点边界推进(§5.1「节点推进=倒计时递减」「到期=移除+触发
        尾款」),返回 ``(是否真实推进, 本次到期移除的条目)``。

        - **是否真实推进**(advanced)是账本→字段桥的余额累加闸门(批次三
          B1):per-node 形态(§3.3.5)每节点恰累加一次,靠本位判——同节点
          重复调用 advanced=False,调用方跳过累加(与余期递减同一去重键)。
        - ``node_ordinal`` 给定时做**同节点去重**:挂点每备战环采样,同节点
          多次调用只推进一次(键 = 节点序 (plane-1)*9+round,基 1,与
          ActiveEffect.acquired_t 同坐标系);None = 无条件推进(测试/sim
          直调)。
        - **登记当节点不推进**(acquired_t ≥ node_ordinal 的条目跳过):
          「持续/接下来 N 个节点」读作登记节点的**后继** N 节点(躺平
          「持续3个节点」/节省工位「在接下来3个节点」的卡文口径);登记
          节点当拍即计数会吞掉第一个受效节点。该读法待实采定谳,证伪时
          改守卫即单点。
        - 到期条目 = 尾款触发面:调用方据 payload 做到期观测留证;尾款金面
          走观察覆盖兜底(设计 §4.1 九卡纠偏:躺平类延迟金不经 instant_gold
          消费进字段,禁此处 logic 直写金币防双计),不设第五写端。

        余期是自然数计数(非索引):登记 3 → 三次有效推进后移除(躺平 3 节点)。
        """
        if node_ordinal is not None and node_ordinal == self._last_tick_node:
            return False, []
        self._last_tick_node = node_ordinal
        expired: list[ActiveEffect] = []
        for e in list(self.entries):
            if e.remaining_nodes is None:
                continue
            if (node_ordinal is not None and e.acquired_t is not None
                    and e.acquired_t >= node_ordinal):
                continue
            e.remaining_nodes -= 1
            if e.remaining_nodes <= 0:
                self.entries.remove(e)
                expired.append(e)
        return True, expired

    def tick_node(self, node_ordinal: int | None = None) -> list[ActiveEffect]:
        """兼容口:仅返回到期条目(忽略 advanced 位;余额累加等桥挂点用
        :meth:`advance_node` 取推进有效性)。"""
        return self.advance_node(node_ordinal)[1]

    def consume_use(self, spec_id: str) -> int | None:
        """次数类余量递减(挂点 = 跳过执行落地,§3.2.19/§5.1「挂点现读递减」)。

        remaining_uses −1;归零移除(用尽 = 效果离场;「用尽后按钮恢复
        出战」待实机验,设计 §3.2.19 挂观察工作清单)。无在册条目或该
        条目非次数类 → 返回 None 且零动作——递减挂点与登记挂点解耦:
        登记面缺位的局不炸执行链(保守端 = 记录缺失,不虚构递减)。
        """
        e = self.first(spec_id)
        if e is None or e.remaining_uses is None:
            return None
        e.remaining_uses -= 1
        if e.remaining_uses <= 0:
            self.entries.remove(e)
        return e.remaining_uses

    def on_level_up(self) -> None:
        """升级事件标记(挂点 = prep_actions._level_up 成功返回处)。"""
        self._events[_EVENT_LEVEL_UP] = self._events.get(_EVENT_LEVEL_UP, 0) + 1

    def on_battle_end(self) -> None:
        """战斗结算事件标记(生产挂点 = CwScreenBattleWait 结算观察写端
        _record_round_outcome 非 telemetry_only 分支——真实结算才标记,
        败局页 telemetry-only 补录不标记,与 apply_settlement_cover 同口径;
        原 on_round_end 候选宿主已随 ADR-0583 删除)。"""
        self._events[_EVENT_BATTLE_END] = self._events.get(_EVENT_BATTLE_END, 0) + 1

    def event_count(self, kind: str) -> int:
        return self._events.get(kind, 0)

    def bump(self, spec_id: str, key: str, n: int = 1) -> None:
        """计数器自增(按 (spec_id, key) 定点;测试/定向修正用)。"""
        e = self.first(spec_id)
        if e is not None:
            e.counters[key] = e.counters.get(key, 0) + n

    def bump_key(self, key: str, n: int = 1) -> None:
        """动作侧全量计数推进(挂点 = 刷新上报函数,§5.1「刷新=计数累加」;
        原执行落地门,2026-09-18 迁入裁决后 = report_action_refresh_shop_param
        统一触发)。

        对全部**声明过记账义务**(duties.track=True)的在册条目推进
        counters[key]:计数消费按 (spec_id, key) 隔离读(:meth:`counter`),
        无关条目的同键计数零消费面。「谁要记账」的声明单一源 =
        EffectSpec.duties.track,本方法只推进不解释——按触发类型过滤
        (如只推进 ON_REFRESH 条目)需每键一份触发→条目谓词表,在注册表
        未结构化触发谓词前属过度建模。n 默认 1 = 单次动作。生产挂点 =
        刷新上报函数(REFRESH=刷新回执)/ 商店落地门(BUY=购买回执,未
        落地不计数)。
        """
        for e in self.entries:
            if not e.spec.duties.track:
                continue
            e.counters[key] = e.counters.get(key, 0) + n

    def record_refresh(self, free: bool) -> None:
        """刷新执行计数统一入账(2026-09-18 用户裁决:GameState 刷新三字段
        迁入效果账本,此处统一计算;触发点 = 刷新上报函数
        report_action_refresh_shop_param,生产 = 刷新 op 自上报,sim = 委托
        串直调,落地门零重复触发)。

        行为口径(原 record_refresh_execution 逐位平移):
        - refresh_total 恒 +1(付费+免费全量);
        - free=True(免费帧):**不动** refresh_paid(付费累计,长线利好
          阈值型「花费金币进行30次刷新」的计数载体,免费帧混入即毒化)并
          消耗免费余额(free_refresh_balance −1,下限 0);
        - free=False:refresh_paid +1;
        - 同帧推进按策略触发计数(bump_key(CounterKey.REFRESH),采购专员
          族门槛面)——「一次刷新,账本一处入账」。

        free 判定输入 = 调用方(刷前按钮态 UI 真值优先,失读回退余额>0;
        余额未建模局恒 paid 的保守形态由调用方承载)。
        """
        self.refresh_total += 1
        self.bump_key(CounterKey.REFRESH)
        if free:
            self.free_refresh_balance = max(self.free_refresh_balance - 1, 0)
        else:
            self.refresh_paid += 1

    def grant_free_refreshes(self, n: int) -> None:
        """免费刷新余额发放(效果发放端:选卡 burst 族/每节点族/条件族,
        发放桥 apply_effect_burst_grant / grant_effect_node_refresh_balance
        统一出口)。n 非正数 = no-op。"""
        if n <= 0:
            return
        self.free_refresh_balance += n

    def equip_progress_of(self, equip_name: str, wearer: str) -> int:
        """装备效果进度读口(侧栏键 = (装备名, 装备者 char_id))。无记录 = 0
        (计数器从 0 起,§3 规则 1)。"""
        return self.equip_progress.get((equip_name, wearer), 0)

    def bump_equip_progress(self, equip_name: str, wearer: str,
                            n: int = 1) -> int:
        """装备效果进度推进(单调计数器,§3 模型:事件发生就 +1、永不递减
        永不重置)。返回推进后的累计值;n 非正数 = 调用错显式炸错(单调
        计数器无递减语义)。同 (装备名, 装备者) 键天然隔离,不串账;
        同名装备多件同主合并计数(实例区分无观察锚,合并 = 少发不多发,
        保守向——见 :func:`settle_copy_machine_participation` 申报)。"""
        if n <= 0:
            raise ValueError(f'n 须为正数(单调计数器只增),得 {n}')
        key = (equip_name, wearer)
        self.equip_progress[key] = self.equip_progress.get(key, 0) + n
        return self.equip_progress[key]


# ============================================================ portal 登记端(环境源)
# (投资环境确认落地的效果登记,invest-env 迭代 design.md §2.4;生产挂点 =
# CwScreenInvestEnv._decide_and_act 确认链,active_env 写入同址,best-effort
# 不阻塞确认链。结构化条目 = 经济环境(ENV_ECONOMY 命中),payload 复用
# ENV_ECONOMY 表内同一实例(单一源,不复制数值——与 STRATEGY_EFFECTS payload
# 引 STRATEGY_ECONOMY 同实例的纪律同款);未入模环境登记 UnitBuffRef 占位
# (效果原文存档,可见性优先,bot 零响应),G 组(ENV_GIFTS)占位 notes 附
# GiftGrant 摘要(详设 env-value-models.md §2.3)。查询口 = inventory 现有
# 遍历(by_source/by_category/first);本登记端零决策消费——经济判据接登记
# 数据归后续批(design.md §1.3-5)。
#
# **表为什么是惰性构建函数而非模块级常量**:payload 需 cw_investments 真类
# 实例,而 cw_investments 模块头反向 import 本模块(payload 类型面),模块级
# import 它成环(文末诸桥同款约束);首调构建 + 缓存,校验沿
# ``cw_investments._validate_strategy_effects`` 同款(孤儿键/id 双匹配/
# payload↔category),测试收集期显式触发构建 = 等效 import 即炸门。)

#: 经济环境 EffectSpec 条目缓存(首调 :func:`env_portal_effects` 填充;
#: 直读禁——未构建时为 None,消费端一律走构建函数)。
_ENV_PORTAL_EFFECTS: dict[str, EffectSpec] | None = None


def env_portal_effects() -> dict[str, EffectSpec]:
    """经济环境 EffectSpec 条目表(首调构建 + 缓存 + 校验,幂等)。

    条目键 = 环境规范名;trigger/duration 按环境语义(整局/位面周期/
    一次性);payload = ``cw_investments.ENV_ECONOMY`` 表内同一实例(单一源,
    估值与登记不双份)。校验见 :func:`_validate_env_portal_effects`。
    """
    global _ENV_PORTAL_EFFECTS
    if _ENV_PORTAL_EFFECTS is not None:
        return _ENV_PORTAL_EFFECTS
    from sr_od.application.currency_war.kernel.cw_investments import ENV_ECONOMY

    specs: dict[str, EffectSpec] = {
        # 每位面开局 (6,8,12) 金晶矿(id 103):位面周期发放面 → PLANE_START
        # (词表本义「每个位面开始时(固定理财)」);整局持有 → PERMANENT。
        '增发货币': EffectSpec(
            id='103', name='增发货币', trigger=TriggerKind.PLANE_START,
            duration=DurationKind.PERMANENT, category=EffectKind.ECONOMY,
            payload=ENV_ECONOMY['增发货币'],
            notes='整局规则面:每位面开局 6/8/12 金晶矿(位面周期);payload 单一源 = ENV_ECONOMY'),
        # 选卡当场 +6 金(id 113):即时面 → INSTANT/ONCE(随机环境期望不计,
        # design §2.6 取舍)。
        '蓝海': EffectSpec(
            id='113', name='蓝海', trigger=TriggerKind.INSTANT,
            duration=DurationKind.ONCE, category=EffectKind.ECONOMY,
            payload=ENV_ECONOMY['蓝海'],
            notes='选卡当场 +6 金(一次性;随机环境期望不计)'),
        # 升 8 级后 3 节点 +12XP/节点(id 138):条件窗口型 → CONDITIONAL
        # (成长基金到级同族先例)。**不设 N_NODES 余期播种**:登记时点
        #(开局选环境)≠条件达成时点(lv8),余期从登记起递减会提前耗尽——
        # 期限语义(条件达成后 3 节点)归后续消费批排程,本登记端可见性优先,
        # duration=PERMANENT 保占位不丢。
        '成功经验': EffectSpec(
            id='138', name='成功经验', trigger=TriggerKind.CONDITIONAL,
            duration=DurationKind.PERMANENT, category=EffectKind.ECONOMY,
            payload=ENV_ECONOMY['成功经验'],
            notes='条件窗口:升8级后3节点每节点+12XP;期限不播种(登记时点≠条件达成时点,'
                  '递减会提前耗尽,归消费批排程)'),
        # 每取一张策略 +2×已持有数(id 147):触发面 = 每次取投资策略,TriggerKind
        # 无 ON_PICK 值 → 占 CONDITIONAL + notes 声明(禁私加枚举值——触发词表
        # 扩值须同步挂点面评审,登记端零消费不构成扩值依据)。
        '策略大师': EffectSpec(
            id='147', name='策略大师', trigger=TriggerKind.CONDITIONAL,
            duration=DurationKind.PERMANENT, category=EffectKind.ECONOMY,
            payload=ENV_ECONOMY['策略大师'],
            notes='触发面 = 每次取投资策略(词表无 ON_PICK 值,占 CONDITIONAL 声明);'
                  '金面 = +2×取卡前已持有数'),
    }
    _validate_env_portal_effects(specs)
    _ENV_PORTAL_EFFECTS = specs
    return specs


def _validate_env_portal_effects(specs: dict[str, EffectSpec]) -> None:
    """ENV_PORTAL_EFFECTS 构建校验(沿 ``cw_investments
    ._validate_strategy_effects`` 同款,构建期炸):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(防版本更新改名/移除后静默失联);
    ② id 双匹配:spec.id 必须等于 plaza id(改名且 id 仍在的漂移也炸);
    ③ payload↔category 一致性:本表条目一律 ECONOMY ↔ EnvEconomyEffect;
    ④ 覆盖方向:表键 ⊆ ENV_ECONOMY——结构化条目只对经济环境建,表外经济
    环境(数据批 B/C 类补表后未跟上 spec)走占位登记不炸(登记端对 3.3
    演化鲁棒:占位保守可见,零行为差),反方向(非经济环境建 spec)拒绝;
    传递得 表 ∩ ENV_GIFTS = ∅(ENV_ECONOMY ∩ ENV_GIFTS = ∅ 构建期已断言)。
    """
    from sr_od.application.currency_war.kernel.cw_investments import (
        ENV_ECONOMY,
        INVESTMENT_ENVS,
        EnvEconomyEffect,
    )

    orphans = [n for n in specs if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(f"ENV_PORTAL_EFFECTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _name, _spec in specs.items():
        if INVESTMENT_ENVS[_name].source != f"plaza:{_spec.id}":
            raise ValueError(
                f"ENV_PORTAL_EFFECTS id 漂移:{_name!r} spec.id={_spec.id} "
                f"base={INVESTMENT_ENVS[_name].source}")
        if _spec.category != EffectKind.ECONOMY or \
                not isinstance(_spec.payload, EnvEconomyEffect):
            raise ValueError(
                f"ENV_PORTAL_EFFECTS payload↔category 不一致:{_name!r} "
                f"category={_spec.category} payload={type(_spec.payload).__name__}"
                f"(本表条目一律 ECONOMY ↔ EnvEconomyEffect)")
        if _spec.pending and not _spec.notes:
            raise ValueError(f"ENV_PORTAL_EFFECTS pending 条目必须写保守支 notes:{_name!r}")
    _off_econ = set(specs) - set(ENV_ECONOMY)
    if _off_econ:
        raise ValueError(
            f"ENV_PORTAL_EFFECTS 覆盖越界(非经济环境禁建结构化条目,走占位):{sorted(_off_econ)}")


def _portal_placeholder_spec(env_name: str) -> EffectSpec | None:
    """未入模环境的 UnitBuffRef 占位 spec(运行期构造,不入注册表):

    - 效果原文存档(payload.effect_text = INVESTMENT_ENVS[name].effect 官方
      全文,可见性优先——判读面可读,bot 零响应);
    - G 组(ENV_GIFTS 命中)占位 notes 附 GiftGrant 摘要(即时/条件发放角色
      + advisor 语义,详设 env-value-models.md §2.3「判读面可读」);
    - trigger/duration 无行为消费(占位零响应),统一 PLANE_START/PERMANENT
      (环境 = 选定后整局规则面语义),notes 声明占位形;
    - id = plaza 数字 id(从 source 剥前缀;非 plaza 形 source 原样保留)。
    """
    from sr_od.application.currency_war.kernel.cw_investments import (
        ENV_GIFTS,
        INVESTMENT_ENVS,
    )
    _env = INVESTMENT_ENVS[env_name]
    grant = ENV_GIFTS.get(env_name)
    if grant is not None:
        _parts = ['GiftGrant']
        if grant.chars_immediate:
            _parts.append(f"即时[{'、'.join(grant.chars_immediate)}]")
        if grant.chars_conditional:
            _parts.append('条件[' + ';'.join(
                f'{c}:{note}' for c, note in grant.chars_conditional) + ']')
        if grant.advisor:
            _parts.append('advisor=顾问入商店')
        _notes = ('未入模占位(效果原文存档,bot 零响应;详设 env-value-models.md §2.3);'
                  + ' '.join(_parts))
    else:
        _notes = '未入模占位(效果原文存档,bot 零响应;design.md §2.4)'
    _pid = (_env.source.split(':', 1)[1]
            if _env.source.startswith('plaza:') else _env.source)
    return EffectSpec(
        id=_pid, name=_env.name, trigger=TriggerKind.PLANE_START,
        duration=DurationKind.PERMANENT, category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=_env.effect), notes=_notes)


def register_portal_from_env(session: object, env_name: str) -> EffectSpec | None:
    """投资环境确认落地 → portal 源登记(design.md §2.4 登记端共用体;
    形态先例 = cw_affix_effects.register_affixes_from_names 词缀源共用体)。

    - **结构化命中**:归一名 ∈ :func:`env_portal_effects`(经济环境)→ 该
      spec 入册(payload = ENV_ECONOMY 表内实例,单一源);
    - **未入模占位**:已知名(INVESTMENT_ENVS 命中)非经济环境 →
      :func:`_portal_placeholder_spec` 运行期构造 UnitBuffRef 占位入册
      (效果原文存档;G 组 notes 附 GiftGrant 摘要);
    - **未知名零动作**:注册表外(赛季新增/OCR 误识/锁定未命名)无效果原文
      无从占位 → None(调用侧 is_known_env 已 warning,此处不再重复告警);
    - **幂等**:portal 源已登记同名(spec.name = 归一名)跳过——环境确认链
      重入/retry 不得双登记(实例按 spec_key 唯一,effect-domain.md §9.1
      与词缀源同款纪律);
    - acquired_t = 登记时点节点序快照((plane-1)*9+round 基 1;GameState
      节点单例;节点未观察(引导窗)= None 缺位,last_state 帧回退已随链
      退役批删除);
    - 返回本次登记的 spec(幂等跳过/未知名返回 None,调用侧日志留证)。

    game_state_of 运行期函数内 import:GameState 容器模块头反向 import
    本模块(effects 字段载体),保持本函数可离线单测(惰性纪律同文末诸桥)。
    """
    from sr_od.application.currency_war.kernel.cw_investments import (
        INVESTMENT_ENVS,
        normalize_invest_name,
    )

    _name = normalize_invest_name(env_name)
    if _name not in INVESTMENT_ENVS:
        return None
    from sr_od.application.currency_war.kernel.cw_game_state import (
        game_state_of,
    )
    gs = game_state_of(session)
    effects = gs.effects
    if any(e.spec.name == _name for e in effects.by_source(SOURCE_PORTAL)):
        return None
    _spec = env_portal_effects().get(_name)
    if _spec is None:
        _spec = _portal_placeholder_spec(_name)
    effects.register_portal(_spec, _portal_acquired_t(gs, session))
    return _spec


def _portal_acquired_t(gs: object, session: object) -> int | None:
    """登记时点节点序快照((plane-1)*9+round,基 1;register_affixes_from_names
    同式):GameState 节点单例;节点未观察(引导窗)= None(登记期快照缺位
    不炸登记面;last_state 帧回退已随链退役批删除,session 参数保留签名
    兼容,不再消费)。"""
    _nd = getattr(gs, 'node', None)
    _nd_val = _nd.value if _nd is not None else None
    if _nd_val is not None:
        return (_nd_val.plane - 1) * 9 + _nd_val.round_num
    return None


# ============================================================ 账本→字段桥·板面重写
# (GameState 数据结构设计 §5 全员晋升/人力重组两行;effect-domain.md §8 同名条。
# 与 cw_game_state 的 apply_effect_burst_grant 等三桥同族,但宿主不在
# cw_game_state——其模块头 import 本模块,桥落本侧可免模块级成环;
# ChannelSig/BenchView 运行期函数内惰性取。挂点 = 选卡时点(设计 §3.2.3
# 「效果写端(选卡时点、非 op)」),生产接线 = CwScreenInvestStrategy
# ._append_confirmed_strategy 确认落地登记点(register_strategy/
# apply_effect_burst_grant 同点)。)


@dataclass(frozen=True)
class BoardRewriteReport:
    """板面重写桥执行报告(留证/测试用;零决策消费)。"""

    rewrite: str                   # board_rewrite 语义值(BOARD_REWRITE_* 词表)
    refund_gold: int               # sell_all 出售面退款合计(sell_refund 口径,
                                   # 只含已读单位);该值是否已入金看
                                   # partial_read 与金字段本身(部分读时仅在
                                   # 此留证、未入金);upgrade_all 恒 0(无出售面)
    sold_units: int                # sell_all 已读出的出售单位数(前台+后台+备战席;
                                   # 字段从未观察 = 0,不代表实际卖数)
    cleared_fields: tuple[str, ...] = ()   # 实际执行逻辑清空的 GameState 字段名
    partial_read: bool = False     # True = 出售域未全读(front_row/back_row/bench
                                   # 任一从未观察)→ 退款公式输入不完整,退款
                                   # 零写入等观察收口(effect-domain.md §6.3);
                                   # upgrade_all 恒 False(无出售面)


def apply_board_rewrite(gs: GameState, spec: EffectSpec, *,
                        frame: str = '') -> BoardRewriteReport | None:
    """桥·板面重写形态(选卡时点一次性):按设计 §5 写入归属两行落
    EffectSpec.board_rewrite 的语义。返回执行报告;非板面重写条目(payload
    无 board_rewrite 或为空)返回 None 零动作。

    **归属两行(单一源 = GameState 数据结构设计 §5)**:
    - 全员晋升(BOARD_REWRITE_UPGRADE_ALL):替换面 = 随机(全场升为高 1 费
      随机角色),不可准确算 → **零逻辑写端,观察收口**(§5.3 归属判据随机
      分支)——本桥对它零写入,报告作负写端留证;附带「获得 2 个拆装扳手」
      = 装备库存精确增量,但注册表无结构化载体(§5.2 缺口登记),经装备
      观察覆盖收口,不在本桥建模。
    - 人力重组(BOARD_REWRITE_SELL_ALL):出售面 = 确定性 → 逻辑写(§5.3
      归属判据确定性分支)——前台/后台/备战席清空 + 退款按卖价公式入金
      (单一源 = cw_state.sell_refund,费用查表单一源 = cw_state
      .bench_char_cost,未知 char_id 退中费 3);随后发牌面(2★3费×1 +
      2★2费×2 + 2★1费×2)= 随机 → **不建逻辑写,进席落位走观察覆盖**——
      本桥禁替发牌面造单位,清空后的补位真值由下一备战帧观察给出。

    **字段从未观察(value=None)= 无容器可写,跳过**(同族先例 =
    project_effect_capacity):选卡后的下一备战帧观察必全量重读板面,
    跳过不损真值到达。**出售域未全读**(front_row/back_row/bench 任一
    value=None,典型 = 接管局/观察缺口局)= 退款公式的输入不完整(未读
    域实际卖数未知,refund 只是已读面的部分值)→ 不满足归属判据确定性
    分支「确定性公式+已知输入」的前提(effect-domain.md §6.3)→ 退款
    零写入留证(报告 partial_read=True + 日志),等观察收口——禁把部分
    退款以 logic 标写成权威值(观察帧覆盖前记录层留错误金)。gold 未读
    (None)= 无累加基座,跳过金写入(禁把退款当余额);退款合计为 0
    (出售域全未读/空场)同样跳过——禁把观察金翻标成 logic(§2.1 来源
    标记到字段)。bench 清空保留现容量(节省工位类容量改写归容量逻辑态
    直写桥辖域,两桥互不越界)。

    **sim 语义申报(适用性/对齐)**:本桥不接 sim——sim 的 GameState 全量
    由 sim 引擎真值直写(evidence 恒
    sim:synthesized),若在 sim 侧调本桥,logic 值立即被下一段真值写覆盖且
    与引擎事实不一致(sim 引擎不执行出售/重写)。sim 若建模这两卡的板面
    后果,改动面 = sim 真值域(卖全场+退款+发牌),经同写入口自动
    以 observation 落记录——效果在真值层生效,记录层不插 logic 补丁。现役
    sim 对这两卡零板面建模(选卡仅记名+经济腿),属 sim 模型既有边界。

    **未知语义值 = 保守 no-op + 留证**(禁猜):新板面重写卡入册时须同步
    扩本桥归属分支,防注册表声明了语义而写端静默丢。
    """
    rewrite = str(getattr(getattr(spec, 'payload', None), 'board_rewrite', '')
                  or '')
    if not rewrite:
        return None
    if rewrite not in (BOARD_REWRITE_UPGRADE_ALL, BOARD_REWRITE_SELL_ALL):
        log.warning('[cw!][effect-bridge] 未知板面重写语义 %r(spec=%s)'
                    ' → 保守 no-op(禁猜;扩归属分支后生效)', rewrite, spec.name)
        return None

    if rewrite == BOARD_REWRITE_UPGRADE_ALL:
        # 整场上阵替换形态:随机面零逻辑写端(设计 §5 全员晋升行),报告
        # 仅作负写端留证;本分支禁新增任何写入。
        return BoardRewriteReport(rewrite=rewrite, refund_gold=0, sold_units=0)

    # —— sell_all:全场出售+再发牌形态 ——
    # 卖价/费用单一源在 cw_state(与预期态/策略侧同源);函数内 import 维持
    # 本模块「模块头零包内 import」契约(机制层离线可单测)。
    from sr_od.application.currency_war.kernel.cw_economy import (
        bench_char_cost,
        sell_refund,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
        BenchView,
        ChannelSig,
    )

    front = gs.front_row.value
    back = gs.back_row.value
    view = gs.bench.value
    bench_units = [s.unit for s in view.slots
                   if s.kind == 'unit' and s.unit is not None] \
        if view is not None else []
    sold = list(front or []) + list(back or []) + bench_units
    refund = sum(sell_refund(int(u.star), bench_char_cost(u)) for u in sold)
    # 出售域全读判据:front/back 均已读且 bench view 已读,退款公式的输入
    # (实际卖数)才完整——任一子域从未观察时 refund 只是已读面的部分值,
    # 归属判据确定性分支「确定性公式+已知输入」前提不成立
    # (effect-domain.md §6.3),该退款禁入金(等观察收口)。
    partial_read = front is None or back is None or view is None

    ev = f'effect_board_rewrite@{frame}' if frame else 'effect_board_rewrite'
    # 组签名:一次出售清空 = 一次逻辑计算,组内行同 group(§3.2.1 group_id
    # 语义);actor 复用同族写入者名 EffectLedgerBridge。
    sig = ChannelSig(family='logic_hook', actor='EffectLedgerBridge',
                     mode='compute',
                     group_id=f'hook:EffectLedgerBridge@{gs.write_seq + 1}')

    cleared: list[str] = []
    if front is not None:
        gs.write_logic(gs.front_row, [], produced_by='EffectLedgerBridge',
                       evidence=ev, sig=sig)
        cleared.append('front_row')
    if back is not None:
        gs.write_logic(gs.back_row, [], produced_by='EffectLedgerBridge',
                       evidence=ev, sig=sig)
        cleared.append('back_row')
    if view is not None:
        gs.write_logic(
            gs.bench,
            # 槽位表原位清空:槽数保持观察现值,全槽置空;容量保留现值
            #(容量改写辖域 = 容量逻辑态直写桥 project_effect_capacity,互不越界)。
            BenchView(slots=[BenchSlot(kind='empty')] * len(view.slots),
                      capacity=view.capacity),
            produced_by='EffectLedgerBridge', evidence=ev, sig=sig)
        cleared.append('bench')
    # 金写入门三条件齐备才 write_logic:基座已读 + 退款非零 + 出售域全读。
    # 零退款(出售域从未读过/空场)无可入账增量;partial_read 时输入不完整
    # (§6.3)——两种情形金字段都保持原来源不动,禁把观察金翻标成 logic
    # (§2.1 来源标记到字段);部分读的已读面退款在报告留证(refund_gold ×
    # partial_read)。
    if partial_read and refund > 0:
        log.warning(
            '[cw!][effect-bridge] 板面重写出售域部分读(front=%s/back=%s'
            '/bench=%s)→ 退款 %d 零写入等观察收口(§6.3 输入不完整)',
            front is not None, back is not None, view is not None, refund)
    if gs.gold.value is not None and refund > 0 and not partial_read:
        gs.write_logic(gs.gold, int(gs.gold.value) + refund,
                       produced_by='EffectLedgerBridge', evidence=ev, sig=sig)
    return BoardRewriteReport(rewrite=rewrite, refund_gold=refund,
                              sold_units=len(sold),
                              cleared_fields=tuple(cleared),
                              partial_read=partial_read)


# ============================================================ 账本→字段桥·装备改写写端
# (写入归属申报单一源 = kernel/cw_affix_effects.py EQUIP_REWRITE_DECLARATIONS
# × EQUIP_WRITE_SIDES;归属判据 = GameState 数据结构设计 §5.3 / 正本
# docs/develop/sr_od/application/currency_war/game_state/effect-domain.md §6.3。宿主放本侧与
# 板面重写桥同理:申报模块 cw_affix_effects 头 import 本模块,桥落本侧免
# 模块级成环;GameState 真类运行期函数内惰性取,维持「模块头零包内
# import」契约。)
#
# **窗口独占性分形**(确定性面两种落码形的分界):观察覆盖字段的 logic 直写,
# 只有「写入 → 下一次观察」窗口内无其他同字段变更源时才是完全预测,失配才
# 等价推算 bug(§2.3 观察赢);窗口内有未接写端的共享变更源(节点边界金面与
# 轮首收入三支同窗——live 写端载体未指派,设计 §8.7 尾批行)时,直写=系统性
# 失配刷缺陷台账。故装备确定性面按触发窗口独占性分两形落码:
# - **写端桥**(apply_/spawn_/grant_/transform_ 前缀):触发窗口天然独占
#   (获得回执/工具拖拽回执/选定回执),write_logic 直写,下一观察覆盖核实;
# - **贡献算术**(equip_*_gold 前缀纯函数):触发窗口与未接写端共享(节点
#   边界金/获得时点战利品),零直写——组合写归节点边界金结算载体与获得
#   结算载体(接线批取各贡献合计一次写入),先落单独直写必刷缺陷台账;
# - **负写端**(登记面 observation 形):随机面/真值同拍送达面(战斗结算 −6
#   的结算屏真值已含该效果,独立直写=双计)零直写,逐件申报见登记面。


def _equip_bridge_sig(gs: GameState) -> ChannelSig:
    """装备改写桥写入的渠道③签名(单一构造点;组 id 格式与板面重写桥一致
    = hook:<写入者名>@<seq>;actor 复用同族写入者名 EffectLedgerBridge)。
    ChannelSig 运行期惰性取(TYPE_CHECKING 面仅注解,模块头零包内 import
    契约)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import ChannelSig
    return ChannelSig(family='logic_hook', actor='EffectLedgerBridge',
                      mode='compute',
                      group_id=f'hook:EffectLedgerBridge@{gs.write_seq + 1}')


#: 极·阿瓦隆获得时点小队生命增益(官方文「获得该宝具时，获得50点小队生命值」,
#: cw_equipment_data 极·阿瓦隆条目;数值单一源在本常量,申报表不复写数值)。
TREASURE_ACQUIRE_HP: int = 50
#: 财富每节点金(官方文「进入新节点时，提供4金币」,cw_equipment_data 财富条目;
#: 轮首收入族同型,设计 §7 扫描面金面代表)。
WEALTH_GOLD_PER_NODE: int = 4
#: 财富宝钻金面周期(官方文「装备者每3个备战阶段提供1金币」——每 3 阶段 1 金,
#: 整除触发;phases_elapsed 按累计口径供给,零头阶段经整除天然结转不丢)。
DIAMOND_PHASE_STEP: int = 3
#: 员工投影仪拖动目标费用门(官方文「拖动到一个3费及以下的角色上使用」;
#: 完美投影仪无此限,同文「拖动到一个任意角色上使用」)。
STAFF_PROJECTOR_COST_GATE: int = 3
#: 进阶→特权装备映射后缀(注册表 36 进阶 ↔ 36 特权全量双射,覆盖率由测试锁
#: 对 cw_equipment_data 钉死;特权赋予卡确定性变换的映射单一源)。
EQUIP_PRIVILEGE_SUFFIX: str = '·特权'


def held_equip_count(gs: GameState, name: str) -> int:
    """装备持有件数单一源(贡献算术/组合写的计数底座):前排已穿 + 后排已穿
    + 备战席已穿(记录内)+ 装备库存,四源求和。

    - 边界:备战席装备图标观察面=负探针(机制恒空,设计 §3.2.18「窟窿二」),
      记录内备战席单位 equips 通常为空表——持有可能被低估,盲区随观察面
      建模收窄,消费侧对账按真值归因;
    - 字段从未观察(value None)= 该源跳过(不猜);
    - 纯读零写入(write_seq 不动)。
    """
    total = 0
    for units in (gs.front_row.value, gs.back_row.value):
        for u in units or []:
            total += sum(1 for e in (u.equips or []) if e == name)
    view = gs.bench.value
    if view is not None:
        for s in view.slots:
            if s.kind == 'unit' and s.unit is not None:
                total += sum(1 for e in (s.unit.equips or []) if e == name)
    inv = gs.equips.value
    if inv is not None:
        total += sum(1 for e in inv if e == name)
    return total


def worn_equip_count(gs: GameState, name: str) -> int:
    """装备已穿件数(「装备者」口径计数底座):前排 + 后排已穿。

    备战席已穿不计——负探针盲区同 :func:`held_equip_count` 边界;装备库存
    (未穿)不计——「装备者」语义 = 穿戴者。纯读零写入。
    """
    total = 0
    for units in (gs.front_row.value, gs.back_row.value):
        for u in units or []:
            total += sum(1 for e in (u.equips or []) if e == name)
    return total


def equip_node_gold_grant(gs: GameState) -> int:
    """贡献算术·财富金面(进新节点 +4×持有件数):节点边界金结算载体的
    合计项之一,纯算术零直写。

    零直写的依据:节点边界窗口与轮首收入三支共享且其 live 写端未指派
    (设计 §8.7 尾批行),单独直写=系统性失配刷缺陷台账;组合写归该载体
    (接线批取各贡献合计一次写入),落地前金面维持观察覆盖兜底。
    持有口径 = :func:`held_equip_count`——官方文无「装备者」限定(对比宝钻
    金面明写),未穿戴是否生效待实采;宽口径(持有即计)使多计进对账可见,
    优于漏计静默。
    """
    return held_equip_count(gs, '财富') * WEALTH_GOLD_PER_NODE


def equip_diamond_phase_gold(gs: GameState, *, phases_elapsed: int) -> int:
    """贡献算术·财富宝钻金面(装备者每 3 备战阶段 +1 金×已穿件数):
    节点边界金结算载体的合计项,纯算术零直写(依据同 :func:`equip_node_gold_grant`)。

    - ``phases_elapsed`` = 穿戴起累计备战阶段数(自然数,接线批逐件进度
      供给;逐件异期进度由调用方分次调用,本函数零状态不记进度——进度
      载体缺位属缺口申报面,禁在本函数内发明第二份);
    - 返回值 = 累计口径(已穿件数 × 穿戴起整除段数),非本节点增量——
      分期结算的调用方跨次调用自行做差(本次累计 − 上次累计)取增量
      入金;把返回值当「本节点应发」逐节点累加 = 每节点重付全部历史段
      (双计);
    - 装备者口径 = :func:`worn_equip_count`(前排+后排;备战席盲区同前);
    - 负值 = 调用错,显式炸错(累计数不存在负语义)。
    """
    if phases_elapsed < 0:
        raise ValueError('phases_elapsed 为穿戴起累计备战阶段数(自然数),'
                         '负值=调用错')
    return (worn_equip_count(gs, '财富宝钻')
            * (phases_elapsed // DIAMOND_PHASE_STEP))


def equip_wrench_duplicate_gold(gs: GameState) -> int:
    """贡献算术·精密拆装扳手金面(持有精密后再获得拆装扳手改 +1 金):
    获得结算载体的合计项,纯算术零直写——获得时点窗口与到账战利品共享
    (晶矿/补给内容即时入账等观察覆盖,§4 CwActionCollectOreParam),单独直写=部分预测
    刷缺陷台账。调用时机 = 拆装扳手获得回执(每次一件);返回本笔应得金
    (0 = 精密不在场,扳手照常入栏不发金)。定额与持有件数无关(官方文
    「改为获得1金币」)。"""
    return 1 if held_equip_count(gs, '精密拆装扳手') >= 1 else 0


def apply_equip_acquire_hp(gs: GameState, *, frame: str = '') -> int:
    """桥·获得时点小队生命增益(极·阿瓦隆 +50):获得回执时点 write_logic
    直写 hp + :data:`TREASURE_ACQUIRE_HP`。

    - 窗口独占(获得回执 → 下一次 hp 读数之间无其他 hp 变更源),完全预测
      ——失配等价推算 bug(§2.3);
    - hp 从未读(None)= 无累加基座,跳过零写入返回 0(hp 写入闸辖:不可信
      不写,禁造假基座;同族先例 = 板面重写桥金面跳过);
    - 生产挂点 = 获得回执(接线批);接线前观察覆盖兜底,与现状零行为差。
    """
    if gs.hp.value is None:
        return 0
    ev = f'equip_acquire_hp@{frame}' if frame else 'equip_acquire_hp'
    gs.write_logic(gs.hp, int(gs.hp.value) + TREASURE_ACQUIRE_HP,
                   produced_by='EffectLedgerBridge', evidence=ev,
                   sig=_equip_bridge_sig(gs))
    return TREASURE_ACQUIRE_HP


def spawn_equip_bench_unit(gs: GameState, char_id: str, star: int,
                           cost: int, *, cost_gate: int = 0,
                           frame: str = '') -> bool:
    """桥·装备族单位入席腿(共享):把复制/发放单位落进备战席第一个空槽,
    write_logic 直写(确定性→逻辑写,归属判据确定性分支)。服务面 =
    员工投影仪(拖拽回执,cost_gate=3)/完美投影仪(无门)/数据拷贝仪族
    计数臂(成熟回执,无门)——登记面映射单一源 =
    cw_affix_effects.EQUIP_WRITE_SIDES。(分身墨镜系获得发放腿已改辖
    apply_equip_acquire_consequence——获得后果全渠道统一,本桥不再服务
    该两行;数据拷贝仪Max 行保持本桥辖计数臂,其获得后果由后果函数按
    数据行统一辖,不经登记表双登记。)

    - ``cost``/``cost_gate``:拖动目标费用与其门(>0 时 cost 超门拒落 =
      游戏端拒拖拽语义;员工投影仪 =3,无门传 0);费用查表单一源在调用侧
      (cw_state.bench_char_cost 同源域);
    - 席满(无空槽,与派生 bench_free_slots==0 同源)或 bench 从未观察
      → False 零写入:游戏端拒落/无容器,落位真值由观察给出(§3.2.8
      「席满点不动」同源);
    - star 集 1..3 外 = 调用错,显式炸错(禁静默写错;银狼LV.999 星级已
      随获得后果定谳为 1★[口述·权威 2026-09-18],走后果函数不入本桥);
    - 落位单位 slot = 落位物理槽(slots[i] ↔ 槽 i+1,BenchView 坐标系;
      观察期快照语义,下一观察覆盖为真值)。
    """
    if not 1 <= star <= 3:
        raise ValueError(f'star 须在 1..3(Unit 星级值域),得 {star}'
                         '(星级未采证的单位禁走本桥,走观察收口)')
    if cost_gate > 0 and cost > cost_gate:
        return False
    view = gs.bench.value
    if view is None:
        return False
    # 真类运行期惰性取(模块头零包内 import 契约,板面重写桥同纪律)。
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
        BenchView,
        Unit,
    )
    slots = list(view.slots)
    idx = next((i for i, s in enumerate(slots) if s.kind == 'empty'), None)
    if idx is None:
        return False
    slots[idx] = BenchSlot(kind='unit', unit=Unit(char_id=char_id, star=star,
                                                  equips=[], slot=idx + 1))
    ev = f'equip_spawn@{frame}' if frame else 'equip_spawn'
    gs.write_logic(gs.bench,
                   BenchView(slots=slots, capacity=view.capacity),
                   produced_by='EffectLedgerBridge', evidence=ev,
                   sig=_equip_bridge_sig(gs))
    return True


def grant_equip_item(gs: GameState, name: str, *, frame: str = '') -> bool:
    """桥·装备单件入区(好运令牌选定回执等「选定后确定」面):装备库存
    追加一件,write_logic 直写。库存从未观察(None)= 无容器,跳过返回
    False。名单合法性归调用侧(机制层零数据注册表依赖;选件事实由回执
    承载,本桥不做注册表校验)。窗口独占 = 选定回执 → 下一次装备区读数。"""
    inv = gs.equips.value
    if inv is None:
        return False
    ev = f'equip_grant@{frame}' if frame else 'equip_grant'
    gs.write_logic(gs.equips, list(inv) + [name],
                   produced_by='EffectLedgerBridge', evidence=ev,
                   sig=_equip_bridge_sig(gs))
    return True


def privilege_counterpart(name: str) -> str:
    """进阶 → 对应特权装备名(:data:`EQUIP_PRIVILEGE_SUFFIX` 后缀映射;
    36 进阶 ↔ 36 特权全量双射由测试锁对注册表钉死,非进阶名入参得到
    无意义拼接,调用侧保证键域)。"""
    return name + EQUIP_PRIVILEGE_SUFFIX


def transform_equip_to_privilege(gs: GameState, source_name: str, *,
                                 frame: str = '') -> str | None:
    """桥·进阶装备特权化(特权赋予卡,拖装备回执 = 库存腿):装备库存中
    名为 ``source_name`` 的件替换为对应·特权名,write_logic 直写(确定性
    变换→逻辑写)。库存未观察/无此件 → None 零写入。

    拖角色腿(已穿进阶随机一件变特权)= 穿域改写,归工具执行批——现役
    执行侧对工具零操作(equipment_mechanics.md §经济账框架),双腿接线前
    观察覆盖兜底。"""
    inv = gs.equips.value
    if inv is None or source_name not in inv:
        return None
    target = privilege_counterpart(source_name)
    ev = f'equip_transform@{frame}' if frame else 'equip_transform'
    gs.write_logic(gs.equips, [target if n == source_name else n for n in inv],
                   produced_by='EffectLedgerBridge', evidence=ev,
                   sig=_equip_bridge_sig(gs))
    return target


# ============================================================ 节点边界金结算载体
# (装备申报面三贡献算术的组合写收口,归属判据 = effect-domain.md §6.3
# 确定性分支:轮首收入三支与装备贡献全部确定性可算 → 逻辑写,且同窗变更
# 源必须合并为**单次**金面写入(窗口独占性分形段头注:节点边界窗曾与未接
# 写端的轮首收入共享,本载体即该窗的 live 写端收口——收入公式已收口
# cw_economy.round_start_income,本载体消费之,禁第二份收入算术;生产挂点
# = 备战分支进节点边界,接线归辖批,接线前金面维持观察覆盖兜底)。
#
# 两窗结构(按触发窗口分形,同宿主一段):
# - **节点边界窗**(:func:`settle_node_boundary_gold`):轮首收入三支
#   (supply/reward/loss_comp/combat,分支派发与值分量单一源 =
#   round_start_income)+ 财富贡献(equip_node_gold_grant)+ 宝钻贡献
#   (调用侧折算增量传入)→ 单次 write_logic;
# - **获得回执窗**(:func:`settle_wrench_duplicate_gold`):精密扳手重复
#   获得金(申报行「组合写归获得结算载体」的落码位)——获得回执 → 下一次
#   金读数之间无其他金变更源,窗口独占,直接 +1 直写(与极·阿瓦隆获得 hp
#   桥同形)。到账战利品的金面仍走观察覆盖(§4 CwActionCollectOreParam),本载体不
#   吸收——随机/观察收口面不进组合写。
# )


@dataclass(frozen=True)
class NodeBoundarySettlement:
    """节点边界金结算载体的执行报告(留证/测试用;零决策消费)。"""

    branch: str            # 轮首收入分支(supply/reward/loss_comp/combat;
                           # 金未读跳过时 '')
    income_total: int      # 轮首收入三分量合计(base+息+连胜;round_start_income 口径)
    wealth_gold: int       # 财富贡献(+4×持有,equip_node_gold_grant)
    diamond_gold: int      # 宝钻贡献(调用侧进度载体折算的本拍增量,缺省 0)
    total: int             # 本拍合计增量(income_total+wealth_gold+diamond_gold)
    written: bool          # 是否发生金面 logic 写入(False=金未读/零增量跳过)


def settle_node_boundary_gold(
        gs: GameState, *, plane: int, round_num: int, node_type: str,
        streak: int, lost_node: LostNodeRef | None = None,
        win_reward_mult: float = 1.0, interest_flat: int = 0,
        interest_cap: int | None = None, diamond_gold: int = 0,
        frame: str = '') -> NodeBoundarySettlement:
    """节点边界金结算载体:轮首收入三支 + 装备贡献的组合写(单次金面
    write_logic),实机 live 写端收口。

    - **收入面**:值分量与分支派发全部经 :func:`cw_economy.round_start_income`
      (收入收口单一源,禁第二份);息基 = **结算前**金现值(本函数读
      ``gs.gold`` 后传入,调用方无须自取——单一金基座防息算双读);
      ``lost_node``/倍率/息修饰由调用方按其辖域契约传入(败态消费、
      aggregate_economy 聚合归接线批)。
    - **装备贡献面**:财富 = :func:`equip_node_gold_grant` 现读现算;宝钻 =
      ``diamond_gold``(穿戴起逐件进度折算的**本拍增量**,由调用侧进度
      载体供给——进度载体缺位属缺口申报面,本载体禁内发明第二份,
      缺省 0 = 保守零授予,与现状观察覆盖零行为差)。
    - **单次写入**:全部同窗增量合并为一次 write_logic(窗口独占完全预测,
      失配等价推算 bug,§2.3);金未读(None)= 无累加基座,整拍跳过零
      写入(禁造假基座,板面重写桥金面同族先例);合计 0 同样跳过(无可
      入账增量,禁把观察金翻标成 logic,§2.1 来源标记到字段)。
    - **辖域排除**:到期尾款金(effect-domain.md §7.3 禁 logic 直写防双计)、
      事件金、STRATEGY_ECONOMY 的 gold_per_node 族(ADR-0623 决策1
      「'invest' 键单列」)不在本载体——各自接线面另批;sim 收入路径
      不经本载体(sim 真值合成)。
    """
    gold = gs.gold.value
    if gold is None:
        return NodeBoundarySettlement(branch='', income_total=0, wealth_gold=0,
                                      diamond_gold=0, total=0, written=False)
    # 收入单一源运行期惰性取(模块头零包内 import 契约;详见段头注成环说明)。
    from sr_od.application.currency_war.kernel.cw_economy import (
        round_start_income,
    )
    income = round_start_income(plane, round_num, node_type, int(gold), streak,
                                lost_node=lost_node,
                                win_reward_mult=win_reward_mult,
                                interest_flat=interest_flat,
                                interest_cap=interest_cap)
    wealth = equip_node_gold_grant(gs)
    total = income.total + wealth + diamond_gold
    if total <= 0:
        return NodeBoundarySettlement(branch=income.branch,
                                      income_total=income.total,
                                      wealth_gold=wealth,
                                      diamond_gold=diamond_gold,
                                      total=total, written=False)
    ev = f'node_boundary_gold@{frame}' if frame else 'node_boundary_gold'
    gs.write_logic(gs.gold, int(gold) + total, produced_by='EffectLedgerBridge',
                   evidence=ev, sig=_equip_bridge_sig(gs))
    return NodeBoundarySettlement(branch=income.branch,
                                  income_total=income.total, wealth_gold=wealth,
                                  diamond_gold=diamond_gold, total=total,
                                  written=True)


def settle_wrench_duplicate_gold(gs: GameState, *, frame: str = '') -> int:
    """获得回执窗金结算:精密扳手在场的拆装扳手获得改 +1 金(贡献算术
    :func:`equip_wrench_duplicate_gold` 的组合写收口)。

    - 调用时机 = 拆装扳手获得回执(每次一件);「改为获得 1 金币」 =
      该笔获得不再进消耗品栏(消耗品处置归获得回执的调用侧,本载体只管
      金面);返回实际入账金(0 = 精密不在场/金未读,零写入——扳手照常
      入栏不发金);
    - 窗口独占(获得回执 → 下一次金读数之间无其他金 logic 写;到账战利品
      金面走观察覆盖,不与本写冲突),完全预测,失配等价推算 bug(§2.3)。
    """
    amount = equip_wrench_duplicate_gold(gs)
    if amount <= 0 or gs.gold.value is None:
        return 0
    ev = f'equip_wrench_gold@{frame}' if frame else 'equip_wrench_gold'
    gs.write_logic(gs.gold, int(gs.gold.value) + amount,
                   produced_by='EffectLedgerBridge', evidence=ev,
                   sig=_equip_bridge_sig(gs))
    return amount


# ============================================================ 工具执行批·穿域特权化腿
# (特权赋予卡拖角色腿的落码位:官方文「拖动到一个角色上使用,从角色已
# 穿戴的进阶装备中选择一件变为特权装备」——选定后变换确定性(36 进阶 ↔
# 36 特权后缀映射,:func:`privilege_counterpart`)→ 逻辑写;「选择」面 =
# bot 决策/回执事实,归调用侧,本载体只管选定后的写端。执行分派入口 =
# cw_affix_effects.apply_tool_execution_write(申报表驱动,免环落申报侧)。)


def transform_worn_equip_to_privilege(gs: GameState, target: Unit,
                                      worn_name: str, *,
                                      frame: str = '') -> str | None:
    """桥·穿域特权化(特权赋予卡拖角色腿):已穿进阶装备单件原位变换为
    对应·特权名,write_logic 直写所在容器(前台/后台列表或备战席视图)。

    - ``target`` = 拖动目标单位(调用侧从**当前**观察态取得;按 frozen
      dataclass 全字段相等定位——状态已变则定位失败,零写入返回 None,
      禁按陈旧快照盲写);
    - ``worn_name`` = 选定的已穿进阶装备名;不在 target.equips = 调用错,
      显式炸错(「选择一件」的合法输入域 = 该单位已穿名单;进阶类别
      校验归调用侧分派入口,机制层零注册表依赖);
    - 单件语义 = 只变换**首个**命中件(官方「选择一件」;同名多件余件
      原样);单位不可在席间复制出现(槽位唯一),相等命中恰一个;
    - 定位成功但目标所在容器从未观察 = 不可能(单位对象来自容器现值);
      返回变换后的特权名;零写入分支返回 None。
    """
    if worn_name not in target.equips:
        raise ValueError(
            f'worn_name 须为 target 已穿装备(「选择一件」合法输入域),'
            f'得 {worn_name!r} ∉ {target.equips!r}')
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
        BenchView,
        Unit,
    )
    counterpart = privilege_counterpart(worn_name)

    def _replaced(unit: Unit) -> Unit:
        equips = list(unit.equips)
        equips[equips.index(worn_name)] = counterpart
        return Unit(char_id=unit.char_id, star=unit.star, equips=equips,
                    slot=unit.slot)

    ev = f'equip_worn_transform@{frame}' if frame else 'equip_worn_transform'
    for row_field in (gs.front_row, gs.back_row):
        units = row_field.value
        if units is None:
            continue
        for i, u in enumerate(units):
            if u == target:
                new_units = list(units)
                new_units[i] = _replaced(u)
                gs.write_logic(row_field, new_units,
                               produced_by='EffectLedgerBridge', evidence=ev,
                               sig=_equip_bridge_sig(gs))
                return counterpart
    view = gs.bench.value
    if view is not None:
        for i, s in enumerate(view.slots):
            if s.kind == 'unit' and s.unit is not None and s.unit == target:
                slots = list(view.slots)
                slots[i] = BenchSlot(kind='unit', unit=_replaced(s.unit))
                gs.write_logic(gs.bench,
                               BenchView(slots=slots, capacity=view.capacity),
                               produced_by='EffectLedgerBridge', evidence=ev,
                               sig=_equip_bridge_sig(gs))
                return counterpart
    return None


# ============================================================ 拷贝仪参与计数载体
# (数据拷贝仪族「装备者每参与 N 场战斗,获得自身的一个 1 星复制」的进度
# 载体(「拷贝仪参与计数进度载体」的落码位):参与计数 =
# 装备效果进度侧栏(:meth:`ActiveEffectInventory.bump_equip_progress`,
# 单调计数器模型 §3);成熟判定 = 计数 ÷ 阈值整除(每 N 场一次,§3 规则 3
# 计算侧);成熟写端 = 入席桥 :func:`spawn_equip_bench_unit`(申报行
# 「成熟回执时点窗口独占」,1★ 自身复制)。**现值观察面**:参与事实由
# 当前观察态现读(战斗结算时点的前台+后台在册单位 = 参战者;备战席未
# 上场不参战),不建独立参战事实字段。生产挂点 = 战斗结算覆盖带(接线
# 归辖批;接线前零调用零行为差)。随机臂(「任意方式获得装备者时 30%
# 概率获得复制」)与伤害增幅腿 = 零建模/观察收口,不在本载体——申报面 =
# cw_affix_effects EQUIP_REWRITE_DECLARATIONS 对应行。)

#: 拷贝仪族成熟阈值(官方文「每参与 N 场战斗」;数值单一源在本表,
#: cw_equipment_data 对应条目官方原文:数据拷贝仪/Pro=3,Max=2)。
COPY_MACHINE_MATURE_BATTLES: dict[str, int] = {
    '数据拷贝仪': 3,
    '数据拷贝仪Pro': 3,
    '数据拷贝仪Max': 2,
}


@dataclass(frozen=True)
class CopyMachineSpawn:
    """拷贝仪成熟入席结果(留证/测试用;零决策消费)。"""

    equip: str       # 装备名(COPY_MACHINE_MATURE_BATTLES 键)
    wearer: str      # 装备者 char_id(复制母本)
    count: int       # 成熟时点的参与计数(阈值整倍数)
    placed: bool     # 是否成功入席;False = 席满/席未观察(成熟已消费——
                     # 参与计数是事实推进,不因落位失败回退,单调不重置)


def settle_copy_machine_participation(gs: GameState, *,
                                      frame: str = '') -> list[CopyMachineSpawn]:
    """拷贝仪参与计数载体·战斗参与结算:扫描**现值观察面**(前台+后台
    在册单位)上的拷贝仪穿戴者,逐件推进参与计数;计数整除阈值 = 成熟,
    成熟即经入席桥落一个穿戴者 1★ 复制进备战席。返回成熟结果列表
    (零成熟返回空表)。

    - 参战者口径 = 前台 + 后台(上场单位站两排、两排皆参战,§3.2.7);
      备战席单位未上场不计;行字段从未观察(None)= 该排无参战读数,
      跳过不猜;
    - 进度键 = (装备名, 装备者 char_id):跨排移动计数随键延续(单调,
      §3 永不重置);同名装备多件同主合并计数(实例区分无观察锚,合并
      = 成熟放慢的少发向,不多发——多发会造 phantom 单位刷缺陷台账);
    - 成熟落位失败(席满/席未观察)不回退计数——该次成熟已消费,落位
      真值由下一观察帧给出(报告 placed=False 留证);
    - 同拍多穿戴者逐件独立结算(入席桥逐次写,先后落不同空槽)。
    """
    matured: list[CopyMachineSpawn] = []
    for equip_name, threshold in COPY_MACHINE_MATURE_BATTLES.items():
        wearers: list[str] = []
        for units in (gs.front_row.value, gs.back_row.value):
            for u in units or []:
                if equip_name in (u.equips or []) and u.char_id not in wearers:
                    wearers.append(u.char_id)
        for wearer in wearers:
            count = gs.effects.bump_equip_progress(equip_name, wearer)
            if count % threshold != 0:
                continue
            placed = spawn_equip_bench_unit(gs, wearer, 1, 0, frame=frame)
            matured.append(CopyMachineSpawn(equip=equip_name, wearer=wearer,
                                            count=count, placed=placed))
            if not placed:
                log.warning(
                    '[cw!][effect-carrier] 拷贝仪成熟未入席(equip=%s wearer=%s'
                    ' count=%d)——席满/席未观察,成熟已消费不回退', equip_name,
                    wearer, count)
    return matured


# ============================================================ 装备获得后果应用(全渠道统一)
# (银狼闭环迭代 design.md §2.2:送角色腿建模为装备数据行的获得后果——
# 获得分身墨镜/分身墨镜Max/数据拷贝仪Max 时,赠送的银狼族单位直接进备战
# 席,效果与商店购买完全一致(可触发合成/升星)。后果应用函数 = 全渠道
# 装备入栏的统一后置钩子:确定性通道(获得时件名已知)随 write_logic 入栏
# 同链应用;随机通道(骇客改件采样链)在链内应用、随链 write_logic_rand。
# 登记面 = cw_affix_effects.EQUIP_WRITE_SIDES(分身墨镜系两行
# bridge:apply_equip_acquire_consequence;数据拷贝仪Max 行保持
# spawn_equip_bench_unit 辖计数臂腿,其获得后果由本函数按数据行统一辖,
# 不经登记表双登记)。星级按卡文定谳[口述·权威 2026-09-18]:
# 分身墨镜→1星银狼 / 分身墨镜Max→2星银狼 / 数据拷贝仪Max→1星银狼LV.999。)

#: 获得后果表(件名 → (送出单位名, 星级);表外件 = 无获得后果声明,
#: 后果函数零写零行为——好运令牌等非专属渠道同锚零差)。
EQUIP_ACQUIRE_CONSEQUENCES: dict[str, tuple[str, int]] = {
    '分身墨镜': ('银狼', 1),
    '分身墨镜Max': ('银狼', 2),
    '数据拷贝仪Max': ('银狼LV.999', 1),
}

def _slot_sig(slots: list) -> list:
    """槽表值签名(变更检测用;bench 侧 BenchSlot/占位 kind 与 deployed
    侧 Unit 双形,防共享对象原地变异导致「签名没变值已变」的假阴——
    frozen 形下引擎 replace 新构造,签名比较仅判「是否需要落一行」)。"""
    out = []
    for x in (slots or []):
        if x is None:
            out.append(None)
            continue
        kind = getattr(x, 'kind', None)
        if kind is not None:
            u = x.unit if kind == 'unit' else None
            out.append((kind, None if u is None else
                        (u.char_id, u.star, tuple(u.equips or ()))))
        else:
            out.append((x.char_id, x.star, tuple(x.equips or ())))
    return out


def merge_cascade_write(gs: GameState, work_bench: list, work_dep: list, *,
                        rand: bool, evidence: str, producer: str,
                        sig: ChannelSig,
                        orig_view: BenchView | None = None) -> int:
    """合成级联写(设计 §2.0/§2.1③ 共用消费体;调用方持工作列表副本)
    ——全员 merge_simulate 正常推演(与普通单位同语义;费用档不同时
    存在定谳,分组键 (char_id, star) 无跨档歧义)。

    P1 容器原生形状:``work_bench`` = list[BenchSlot | None](工作槽表)/
    ``work_dep`` = list[Unit | None](行域下标派生表,§2.3);逐级合并后
    受影响域各落一行(:meth:`cw_merge_simulate._merge_bench` on_step
    范式;行域载体在场上 = bench+front+back 同号三行):
    rand=False 走 write_logic(确定面),rand=True 走 write_logic_rand
    (采样链内);
    - ``orig_view`` = bench 原观察帧(容量随原观察;None = 默认容量);
    - 返回落行数(测试/留证用)。
    """
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        deployed_indexed_to_rows,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_view_of_working,
    )
    from sr_od.application.currency_war.kernel.cw_merge_simulate import (
        _merge_bench,
    )

    write = gs.write_logic_rand if rand else gs.write_logic
    rows = 0
    step_no = 0
    last_bs = _slot_sig(work_bench)
    last_ds = _slot_sig(work_dep)

    def on_step() -> None:
        nonlocal step_no, rows, last_bs, last_ds
        step_no += 1
        ev = f'{evidence}#merge{step_no}'
        bs = _slot_sig(work_bench)
        if bs != last_bs:
            write(gs.bench, bench_view_of_working(work_bench, orig_view),
                  produced_by=producer, evidence=ev, sig=sig)
            last_bs = bs
            rows += 1
        ds = _slot_sig(work_dep)
        if ds != last_ds:
            front, back = deployed_indexed_to_rows(work_dep)
            write(gs.front_row, front, produced_by=producer, evidence=ev,
                  sig=sig)
            write(gs.back_row, back, produced_by=producer, evidence=ev,
                  sig=sig)
            last_ds = ds
            rows += 2

    _merge_bench(work_bench, work_dep, on_step=on_step)
    return rows


@dataclass(frozen=True)
class BenchGrantResult:
    """单位入席+级联应用结果(留证/测试用;零决策消费)。"""

    placed: bool     # 是否成功落位(False = 席满/席未观察零写)
    merge_steps: int  # 级联合并级数(拒落路径恒 0)
    detail: str = ''  # 拒落因:'' / 'bench_unobserved' / 'bench_full'


def grant_bench_unit_cascade(gs: GameState, name: str, star: int, *,
                             rand: bool = False, evidence: str = 'bench_grant',
                             producer: str = 'EffectLedgerBridge',
                             sig: ChannelSig | None = None) -> BenchGrantResult:
    """单位入席+合成级联共用核心(获得后果/投资效果函数单一实现体)。

    单位落备战席首空槽(bench_place,容器原生 BenchSlot 直落)→
    :func:`merge_cascade_write` 级联(全员正常推演)→ 逐步各落一行。
    P1 容器原生:工作副本 = BenchView 槽序 + 行域下标派生表(§2.1);
    占位件槽位 kind 随工作表原样保留(零换形降级)。
    ``rand`` = 写通道(False = write_logic 确定面 / True =
    write_logic_rand 采样链);``sig`` 缺省 = 装备桥 logic_hook 签名,
    动作报告上下文传入动作 sig 使链行同组。bench 未观察/席满 → 零写
    拒落(落位真值由观察给出)。
    """
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_place,
        deployed_rows_to_indexed,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
        Unit,
        bench_view_of_working,
    )
    orig_view = gs.bench.value
    if orig_view is None:
        return BenchGrantResult(placed=False, merge_steps=0,
                                detail='bench_unobserved')
    work_bench = list(orig_view.slots)
    work_dep = deployed_rows_to_indexed(gs.front_row.value, gs.back_row.value)
    if bench_place(work_bench, BenchSlot(
            kind='unit', unit=Unit(char_id=name, star=star))) is None:
        return BenchGrantResult(placed=False, merge_steps=0,
                                detail='bench_full')
    write = gs.write_logic_rand if rand else gs.write_logic
    _sig = sig if sig is not None else _equip_bridge_sig(gs)
    write(gs.bench, bench_view_of_working(work_bench, orig_view),
          produced_by=producer, evidence=evidence, sig=_sig)
    steps = merge_cascade_write(gs, work_bench, work_dep, rand=rand,
                                evidence=evidence, producer=producer,
                                sig=_sig, orig_view=orig_view)
    return BenchGrantResult(placed=True, merge_steps=steps)


@dataclass(frozen=True)
class EquipAcquireReport:
    """获得后果应用结果(留证/测试用;零决策消费)。"""

    item: str        # 入栏装备名(调用侧传入)
    granted: str     # 送出单位名('' = 表外件无后果声明)
    star: int        # 送出单位星级(表外件 0)
    merge_steps: int  # 级联合并级数(拒落路径恒 0)
    performed: bool  # 是否发生容器写(授予腿或级联行;False = 表外件/
                     # 席满/席未观察零写)
    detail: str = ''


def apply_equip_acquire_consequence(gs: GameState, item: str, *,
                                    frame: str = '', rand: bool = False,
                                    sig: ChannelSig | None = None) -> EquipAcquireReport:
    """桥·装备获得后果应用(全渠道统一后置钩子;design §2.2)。

    件名查 :data:`EQUIP_ACQUIRE_CONSEQUENCES`:命中 → 送出单位经
    :func:`grant_bench_unit_cascade` 入席+级联(正常推演);表外件 →
    零写零行为(非专属渠道同锚零差,含好运令牌
    grant_equip_item 渠道)。

    - ``rand`` = 调用通道:False = 确定性入栏通道(write_logic,同源);
      True = 随机采样链内(write_logic_rand,观察覆盖差异 = 预期内);
    - ``sig`` = 写入签名(缺省 = 装备桥 logic_hook 签名;动作报告上下文
      传入动作 sig 使链行同组);
    - 装备入栏(equips 追加)不在本函数辖——入栏写端归各渠道宿主,本
      函数只辖「获得即送」的后果腿。
    """
    granted = EQUIP_ACQUIRE_CONSEQUENCES.get(item)
    if granted is None:
        return EquipAcquireReport(item=item, granted='', star=0,
                                  merge_steps=0, performed=False,
                                  detail='no_consequence_declared')
    name, star = granted
    ev = f'equip_acquire@{frame}' if frame else 'equip_acquire'
    r = grant_bench_unit_cascade(gs, name, star, rand=rand, evidence=ev,
                                 sig=sig)
    return EquipAcquireReport(item=item, granted=name, star=star,
                              merge_steps=r.merge_steps, performed=r.placed,
                              detail=r.detail)
