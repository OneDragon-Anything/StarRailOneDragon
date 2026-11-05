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

**文末附加段**:账本→字段桥与结算收束诸段——板面重写(:func:`apply_board_rewrite`)、
装备改写写端(写端桥/贡献算术,装备申报面 = cw_affix_effects
EQUIP_REWRITE_DECLARATIONS × EQUIP_WRITE_SIDES)、节点边界金结算载体
(贡献算术的组合写收尾 + 精密扳手获得回执窗)、穿域特权化分支(特权赋予卡
拖角色入账分支,归工具执行批)、拷贝仪参与计数载体(装备效果进度侧栏)——把
效果声明翻译成 GameState 字段写入归属,宿主放本侧的原因与惰性 import
纪律见各段头注。
"""
from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log

# 装备注册表 = data 叶模块(单向依赖零环,机制层「零 import 包内模块」契约
# 辖 kernel 包内;池常量需注册表派生,同 cw_gain_effects/cw_ore_reward 先例)。
from sr_od.application.currency_war.data.cw_equipment_data import EQUIPMENTS

if TYPE_CHECKING:
    # 仅类型注解引用(项目规范允许);运行时 payload 按对象持有,
    # 类型一致性校验在 cw_investments 构建层(那里有真类)做 isinstance。
    # GameState 仅注解用:cw_game_state 模块头反向 import 本模块(状态容器
    # effects 字段载体),模块级 import 会成环;文末诸桥运行期
    # 经函数内惰性 import 取真类。cw_economy 仅注解用(LostNodeRef):
    # 它模块头拉 cw_investments → 后者 import 本模块,模块级 import 成环。
    from sr_od.application.currency_war.kernel.cw_economy import LostNodeRef
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchView,
        ChannelSig,
        GameState,
        ShopPayload,
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
    LEVEL_UP = 'level_up'          # 升级时(节节高升;商业间谍战场段)
    ON_REFRESH = 'on_refresh'      # 每次刷新时(淘金客/概率事件/采购专员计数)
    ON_MERGE = 'on_merge'          # 合成时(角色3星合成共用本触发面〔星星相印〕:两域生产点分离+payload字段判别零交叉,fields.md §5.3;武力刷新=装备合成域)
    CONDITIONAL = 'conditional'    # 条件窗口(躺平冻结/经验就是财富改道/成长基金到级)
    SUPPLY_PHASE = 'supply_phase'  # 进入补给阶段时(打捞人才库族「每次进入补给阶段后」;
                                   # 发放源 = 上一阶段选定时刻未选列快照,见
                                   # check_strategy_supply_salvage)


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
    bench_reroll: str = ''                  # 备战席区间重掷(乱成一锅粥族;已登记
                                            # 条目 = 乱成一锅粥/乱成一锅粥+,词表
                                            # BENCH_REROLL_*)
    equips_reroll: str = ''                 # 物品栏装备同品质变异(公司军火更新族,
                                            # 取值 = EQUIPS_REROLL_SAME_QUALITY;
                                            # 金/彩未建条目;写归属 = 观察收尾)
    counter_every: int = 0                  # 每 N 次刷新计数门槛(采购专员金 7/彩 5)
    first_merge_equip_junk: float = 0.0     # 每位面首次合成进阶装备变垃圾袋概率(变宝为废=0.5;
                                            # 随机面→不建逻辑写,观察收尾)
    salvage_unchosen_supply: bool = False   # 进入补给阶段时发放上一补给阶段未选列(打捞人才库:
                                            # 发放物 = 状态副本既有列 SupplyOption 结构,非注册表池;
                                            # 不入 EconomyEffect——避开经济三分类闭集义务)
    capacity_limit: int = 0                 # 激活期备战席容量(效果账本容量逻辑态桥
                                            # project_effect_capacity 的声明契约字段,字段名
                                            # 由该桥 docstring 钉死;首个携带条目 = 节省工位 3;
                                            # 0 = 非容量条目;注册期常量)
    expiry_simple_equips: int = 0           # 条目到期拍发放的简易装备件数(到期发放条目 =
                                            # apply_effect_expiry_grants;件数非索引,
                                            # 注册期常量;0 = 无到期发放)
    supply_option_delta: int = 0            # 补给屏可选项数修饰(负值 = 减少;全都要·银
                                            # = -2。声明载体:live 读链按实屏识别列数跟随
                                            # (补给 op 模块头「列数以 read_supply_options
                                            # 实际识别为准,禁写死」),本字段零消费插入位置;
                                            # sim 列数面零建模不接数 = M18 简化域上游缺口)
    salvage_all_unchosen_supply: bool = False   # 下 1 个补给阶段选择后发放全部未选列
                                            # (全都要·银;一次性语义 = DurationKind.ONCE
                                            # + 事件消耗一次性标志位承载,字段名不带 once 尾注——
                                            # 配额不必恒 1,族后继复用免改名;消费端 =
                                            # check_strategy_take_all_supply 直查
                                            # active_strategies,本字段为登记申报载体)
    free_refresh_burst: int = 0             # 选卡一次性免费刷 N 次(大裁员=6)。与
                                            # free_refresh_on_node_enter 同值域、发放
                                            # 插入位置不同:登记拍单次(burst 桥
                                            # apply_effect_burst_grant)vs 节点边界;
                                            # 战场载体载数值发放字段非首例
                                            # (steal_on_level_up/free_refresh_on_node_
                                            # enter 同域先例),burst 桥鸭子类型读取自动兼容
    equips_transform: str = ''              # 物品栏装备固定变换(分解万物:全部进阶装备变物质分解液;取值 =
                                            # EQUIPS_TRANSFORM_ADVANCED_MATTER;与 equips_reroll 互不复用——
                                            # 变异 = 同品质随机重掷/变换 = 固定目标具名件;变换面零执行端
                                            # (游戏侧自动改写),写归属 = 观察收尾)


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
      None 直到实采定案;消费端见 pending=True 必须走
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
                                  # 权威版本=ActiveEffect.remaining_uses,§8.6-3);恒稳
                                  # (注册期常量,登记时拷入 ActiveEffect.remaining_uses)
    pending: bool = False         # True=效果文本有二义未实采定案
    verdict: str | None = None    # 实采定案回填('改道吞引擎XP' 等);None=未定案
    notes: str = ''               # 语义出处与歧义内容(pending 条目必写保守支)


# ===== 计数器键常量(键名不散落字符串,防漂移)=====
class CounterKey:
    REFRESH = 'refresh'   # 刷新计数(采购专员门槛/Gemi狸;按策略触发面)
    BUY = 'buy'           # 购买计数(返利系每 3 张 5 费)
    REFRESH_TOTAL = 'refresh_total'   # 刷新全量累计(免费+付费;二手市场阈值评估)
    REFRESH_PAID = 'refresh_paid'     # 付费刷新累计(长线利好「花费金币进行30次刷新」)
    XP_GRANTED = 'xp_granted'   # 升级窗口已发放节点数(成功经验;写端唯一 = 发放桥 grant_effect_node_xp,窗口耗尽判定读本键)
    LOST = 'lost'   # 超发货币负债额快照(拿卡拍持有金;写端唯一 = 获得链登记分支播值 kernel/cw_gain_chain.gain_invest_strategy,登记帧金读数,禁猜测写;消费端 = sim 清零/回流两条实现状态副本真值)
    SHIELD_BANK = 'shield_bank'   # 现金为王护盾记忆量快照(出售退款合计×1000;写端唯一 = 板面重写桥出售支 apply_board_rewrite,与退款权威写入同闸,空场/出售域未全读零记账;伴生数值型状态副本真值记账,现役零代码消费面)
    INTEREST_TOPUP = 'interest_topup'   # 开源节流条件息顶满待消费额(resolved 帽;写端唯一 = cw_gain_chain 捕获函数置数,消费 = sim 节点窗读后清零——置数语义禁累加,窗口异常未消费时累加会放大错发)


# ===== 效果来源词表(ActiveEffect.source 取值;防散落字符串)=====
# 适用范围:策略源=选卡登记(register_strategy);词缀源=敌人词缀改写源,结构化
# 注册=kernel/cw_affix_effects.AFFIX_EFFECT_SPECS(register_affix 登记);
# 环境源=投资环境适用范围,结构化条目=ENV_PORTAL_EFFECTS(经济环境)+未入模
# 占位(register_portal_from_env 登记,登记面纪律 = game_state/effect-domain.md §7.3)。
SOURCE_STRATEGY: str = 'strategy'
SOURCE_PORTAL: str = 'portal'
SOURCE_AFFIX: str = 'affix'


# ===== 板面重写语义词表(BattlefieldEffect.board_rewrite 取值;防散落字符串)=====
# 已登记条目 = 全员晋升/人力重组/大裁员/降本增效/现金为王(cw_investments
# .STRATEGY_EFFECTS,官方文 cw_invest_data.py:67/:68/:134/:136/:200);写入
# 归属单一源 = docs/develop/sr_od/application/currency_war/game_state
# /effect-domain.md §8 同名条(全员晋升/人力重组/大裁员/降本增效/现金为王)。
BOARD_REWRITE_UPGRADE_ALL: str = 'upgrade_all_cost+1'   # 整场上阵替换:全场升为
                                                        # 高 1 费随机角色(最大 5 费)
# 出售支按「卡文是否携带发牌条目」两值细分:出售 = 语义本体(清场退款),
# 发牌条目 = 人力重组卡文附加面、非出售语义固有——素出售卡(大裁员/降本增效/
# 现金为王)复用 SELL_ALL 值,具发牌条目卡(人力重组)用 _DEAL 值声明;sim 发牌
# 条目判据集 = 过滤 _DEAL 值派生(cw_sim_backend.SELL_ALL_REWRITE_STRATEGIES),
# 素出售卡注册不入集,sim 局零假发牌。
BOARD_REWRITE_SELL_ALL: str = 'sell_all'                # 全场出售(素语义):清场退款,
                                                        # 无发牌面
BOARD_REWRITE_SELL_ALL_DEAL: str = 'sell_all_deal'      # 全场出售+发牌条目:清场退款后
                                                        # 再按卡文档发 2★ 随机角色进席
                                                        # (人力重组:2★3费×1+2★2费×2
                                                        # +2★1费×2)


# ===== 备战席区间重掷语义词表(BattlefieldEffect.bench_reroll 取值;防散落字符串)=====
# 已登记条目 = 公司人才流动(右 3)+ 乱成一锅粥(左 6)(cw_investments
# .STRATEGY_EFFECTS,官方文 cw_invest_data.py:60/:351);重掷面 = 随机分支零逻辑
# 写、观察收尾,写归属单一源 =
# docs/develop/sr_od/application/currency_war/game_state/effect-domain.md
# §6.3/§6.4 与 §8 同名条。姊妹乱成一锅粥+(352102)未建条目(单卡纪律,
# 族级展开批另落)。
BENCH_REROLL_RIGHT3: str = 'right3_same_cost'   # 备战席最右 3 位变为随机同费角色
BENCH_REROLL_LEFT6: str = 'left6_same_cost'     # 备战席最左 6 位变为随机同费角色
                                                # (已登记:乱成一锅粥)


# ===== 物品栏装备同品质变异语义词表(BattlefieldEffect.equips_reroll 取值;
# 防散落字符串)=====
# 已登记条目 = 公司军火更新·银(cw_investments.STRATEGY_EFFECTS,官方文
# cw_invest_data.py:86);变异面 = 随机分支零逻辑写、观察收尾,写归属单一源 =
# docs/develop/sr_od/application/currency_war/game_state/effect-domain.md
# §6.3/§6.4 与 §8 同名条。「同品质」语义先验 = 同 category(冶金炉
# furnace_mutate_pool 已登记先例,tool_use 域),未证零消费。银/金/彩三卡
# 变异条目同文共用本常量(银/金/彩三卡 SE 条目全建,差异全在发放条目)。
EQUIPS_REROLL_SAME_QUALITY: str = 'same_quality_all'   # 物品栏全部装备变为
                                                       # 同品质的其他装备


# ===== 物品栏装备固定变换语义词表(BattlefieldEffect.equips_transform 取值;
# 防散落字符串)=====
# 已登记条目 = 分解万物(cw_investments.STRATEGY_EFFECTS,官方文
# cw_invest_data.py:324);变换面 = 游戏侧自动改写(卡文「本局游戏中」持续
# 标记),bot 零执行端、备战帧 equips 整表观察收真值,写归属单一源 =
# docs/develop/sr_od/application/currency_war/game_state/effect-domain.md
# §6.3/§6.4 与 §8 同名条。与 EQUIPS_REROLL_SAME_QUALITY 互不复用(语义
# 顶替禁制:变异 = 同品质随机重掷,变换 = 固定目标具名件,两语义异型)。
EQUIPS_TRANSFORM_ADVANCED_MATTER: str = 'advanced_to_matter_all'   # 物品栏全部进阶装备变为物质分解液


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
                               # 结构化条目=ENV_PORTAL_EFFECTS)
    acquired_key: tuple[int, int] | None
    # 登记时点;(位面,轮) 节点序位元组(cw_node_schedule.NodePos 同形;
    # 本模块零 import 包内模块纪律,类型就地写 tuple)。登记期快照
    # (登记端 = _portal_acquired_key / register_affixes_from_names)
    remaining_nodes: int | None  # N_NODES 类余期;**自然数计数非索引**;None=不限;
                                 # 插入位置(tick_node)现读递减
    remaining_uses: int | None   # 次数类余量(免战牌×2 等);插入位置现读递减
    anchor_pos: tuple[int, int] | None = None
    # 条件窗口达成位伴生基准(成功经验「升到8级后,进入接下来3个节点」首例;
    # 首例 = T-38 设计稿 §2.5,载体辨析权威版本):坐标系 = (位面,轮) 节点序位
    # 元组(cw_node_schedule.NodePos 同形,与 acquired_key 同键);写入端唯一
    # = 伴生基准方法 :meth:`ActiveEffectInventory.set_xp_window_anchor`(发放桥
    # grant_effect_node_xp / 主插入位置 _record_lv8_window_start 经它写,零旁路直改
    # ——effect-domain.md「写端全部经 inventory 方法」纪律);一次性语义:
    # 已设置拒绝重写(达成位单调不可改);None = 未达成/未记录。窗口剩余 =
    # payload 窗口节点数 − counters[CounterKey.XP_GRANTED],计算侧导出,
    # 禁另播「剩余」存储键(单调计数器模型,effect-domain.md §3)。
    counters: dict[str, int] = field(default_factory=dict)   # CounterKey 键 → 计数


class ActiveEffectInventory:
    """在场效果清单(宿主 = GameState.effects)。纯数据 + 读端/追踪端;零 import 包内模块(可离线单测)。

    写端(插入位置)生产接入调用(设计 §5.1/§次三;单一实例 =
    GameState.effects,session 无独立字段——历史兼容读口 property 已撤,
    写读直经 game_state_of(session).effects,载体归一防双账本):选卡登记 =
    获得链登记分支(kernel/cw_gain_chain.py,选卡上报函数族驱动;免战牌同口
    自动登记);节点 tick = cw_loop 备战分支(进节点边界);计数 bump =
    动作上报链(购买 = cw_action_report/buy_card 的 on_buy 回调,刷新 =
    cw_action_report/refresh_shop 经 record_refresh 唯一入口);跳过递减 = kernel
    出战 op 自上报(report_action_start_battle_param)
    runner 包络上报,上报时递减——出战域重设计);升级标记 =
    prep_actions._level_up
    (既有);结算插入位置 = CwScreenBattleWait 结算观察写端(_record_round_outcome
    非 telemetry_only 分支,apply_settlement_cover 同分支同时序;现役注册表
    零战斗结算触发条目 = 零效果条目推进,零条目 = 零驱动,effect-domain
    §7.4)。
    """

    def __init__(self) -> None:
        self.entries: list[ActiveEffect] = []
        # 事件标记:键 → 计数(_EVENT_* 常量);on_level_up/on_battle_end 写
        self._events: dict[str, int] = {}
        # 节点 tick 去重键(最近已推进的节点序位 (位面,轮);None=未推进
        # 过)。插入位置每备战环采样,同节点多次调用只推进一次——去重键是
        # tick 幂等性的载体,随清单实例走(session 级生命周期,新局天然
        # 清零)。
        self._last_tick_key: tuple[int, int] | None = None
        # 装备效果进度侧栏(拷贝仪参与计数载体首用):键 = (装备名,装备者
        # char_id),值 = 单调计数器。装备源效果无 EffectSpec 实例(
        # 申报面纪律:装备写端 = 桥/贡献算术直读 GameState),其进展量
        # 无实例可挂,落本册侧栏——session 级生命周期与实例清单同源,
        # 计数语义同 §3 单调计数器模型(从 0 起、事件 +1、永不重置)。
        self.equip_progress: dict[tuple[str, str], int] = {}
        # 刷新计数组(2026-09-18 用户裁定住效果账本统一计算;写端 =
        # 刷新上报函数 report_action_refresh_shop_param 统一触发,
        # 消费方 = env_economy 选卡评估通道 + 免费闸;
        # 2026-09-21 用户裁定 Field 化:免费刷新剩余次数升格状态容器字段
        # gs.free_refresh_left,本账本留在两计数):
        self.refresh_total: int = 0           # 全量累计(免费+付费)
        self.refresh_paid: int = 0            # 付费累计(长线利好阈值型)
        # 利息累计账(T-27 公司契约条件分支「累计获得40利息后获得托帕&账账」):
        # 累计入账利息金 = 统一公式 interest 分量全分支累计(**含息 flat
        # 修饰**,economy.md §10.1 收入口径)。写端 = sim 收入应用两处
        # (cw_sim_backend.apply_round_start_income/扑满结算分支)经
        # record 唯一入口 + live 三来源计数刻(来源 A 结算面板息行/来源 B
        # 败局推算/来源 C 补给推算);消费方 = check_env_interest_grants。
        # 不入快照(与 refresh_total 同现状,快照序列化只含 entries +
        # equip_progress)⟹ 接管局计数归零 = 晚发/不发。
        self.interest_earned: int = 0
        # 晶矿开启累计(战技点契约条件分支「打开20个晶矿后」;随 refresh
        # 双计数/interest_earned 同族直挂计数器,同宿效果账本):写端 =
        # 采晶矿上报函数 report_action_collect_ore_param 唯一入口(批内开成
        # 点数一次入账,席满/缺级跳点不入账 = 「点开才计数」);消费方 =
        # 战技点契约触发器 check_env_ore_open_grants。计数语义 = 全量
        # (不限矿色/来源/奖励类型)。
        # 不入快照(与 refresh_total 同现状,快照序列化只含 entries +
        # equip_progress)⟹ 接管局计数归零 = 晚发/不发。
        self.ore_open_total: int = 0

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
                  acquired_key: tuple[int, int] | None) -> ActiveEffect:
        """登记端共用体:spec + 来源 + 登记时点入清单(acquired_key 坐标系见
        ActiveEffect.acquired_key;余期播种见 _seed_progress)。"""
        remaining_nodes, remaining_uses = self._seed_progress(spec)
        entry = ActiveEffect(
            spec=spec, source=source, acquired_key=acquired_key,
            remaining_nodes=remaining_nodes, remaining_uses=remaining_uses,
        )
        self.entries.append(entry)
        return entry

    def register_strategy(self, spec: EffectSpec,
                          acquired_key: tuple[int, int] | None) -> ActiveEffect:
        """策略获得 → 入清单。"""
        return self._register(spec, SOURCE_STRATEGY, acquired_key)

    def register_affix(self, spec: EffectSpec,
                       acquired_key: tuple[int, int] | None) -> ActiveEffect:
        """词缀效果获得 → 入清单(source=affix;结构化注册 =
        kernel/cw_affix_effects.AFFIX_EFFECT_SPECS,spec.id = 词缀名)。

        生产登记插入位置已接入调用:简报读链(``operations/cw_screen/cw_screen_briefing.py``
        ::CwScreenBriefing.observe 词缀读链登记段,开局首读)与位面详情补采通道
        (``operations/cw_screen/cw_screen_plane_intel.py`` 上报节点词缀登记段,
        中断恢复对局补采)经共用登记体 cw_affix_effects.register_affixes_from_names 调本方法
        (幂等 + 注册表命中才登记,best-effort 不阻塞读链主链)。词缀改写面
        写端仍一律观察覆盖兜底(写入归属单一源 = 各 spec.notes 与
        cw_affix_effects.EQUIP_REWRITE_DECLARATIONS 申报面);本方法承诺
        登记语义与策略源同轨(余期播种/推进/到期共用同一套插入位置逻辑)。
        """
        return self._register(spec, SOURCE_AFFIX, acquired_key)

    def register_portal(self, spec: EffectSpec,
                        acquired_key: tuple[int, int] | None) -> ActiveEffect:
        """投资环境效果获得 → 入清单(source=portal;结构化条目 =
        :func:`ENV_PORTAL_EFFECTS`(经济环境),未入模环境走
        :func:`register_portal_from_env` 运行期构造的 UnitBuffRef 占位
        spec——两类条目同经本方法入册,登记语义与策略/词缀源同轨
        (余期播种/推进/到期共用同一套插入位置逻辑)。

        生产登记插入位置 = CwScreenInvestEnv._decide_and_act 确认链
        (active_env 写入同址;best-effort
        失败不阻塞确认链,effect-domain.md §7.3 登记面纪律同词缀源)。
        """
        return self._register(spec, SOURCE_PORTAL, acquired_key)

    # —— 查表端(形状保证;决策消费归后续)——
    def by_source(self, source: str) -> list[ActiveEffect]:
        """按来源词表(SOURCE_*)过滤——词缀源读端(消费接入调用归后续)。"""
        return [e for e in self.entries if e.source == source]

    def first(self, spec_id: str) -> ActiveEffect | None:
        for e in self.entries:
            if e.spec.id == spec_id:
                return e
        return None

    def counter(self, spec_id: str, key: str) -> int:
        """按 (spec_id, key) 读计数——多策略同 key 天然隔离,不串账。"""
        e = self.first(spec_id)
        return e.counters.get(key, 0) if e is not None else 0

    # —— 追踪端(插入位置调用;纯逻辑,sim 与生产同一实现)——
    def advance_node(self, node_key: tuple[int, int] | None = None
                     ) -> tuple[bool, list[ActiveEffect]]:
        """进节点边界推进(§5.1「节点推进=倒计时递减」「到期=移除+触发
        尾款」),返回 ``(是否真实推进, 本次到期移除的条目)``。

        - **是否真实推进**(advanced)是账本→字段桥的余额累加闸门(批次三
          B1):per-node 形态(§3.3.5)每节点恰累加一次,靠本位判——同节点
          重复调用 advanced=False,调用方跳过累加(与余期递减同一去重键)。
        - ``node_key`` 给定时做**同节点去重**:插入位置每备战环采样,同节点
          多次调用只推进一次(键 = (位面,轮) 节点序位元组,
          cw_node_schedule.NodePos 同形——生产写端传 GameState 生效序位
          读口现值,与 ActiveEffect.acquired_key 同键);None = 无条件推进
          (测试/sim 直调)。
        - **登记当节点不推进**(acquired_key >= node_key 的条目跳过,元组
          字典序比较——与旧序数 >= 比较逐值等价,字典序=全序):
          「持续/接下来 N 个节点」读作登记节点的**后继** N 节点(躺平
          「持续3个节点」/节省工位「在接下来3个节点」的卡文口径);登记
          节点当拍即计数会吞掉第一个受效节点。该读法待实采定案,证伪时
          改守卫即单点。
        - 到期条目 = 尾款触发面:调用方据 payload 做到期观测留存证据;尾款金面
          走观察覆盖兜底(设计 §4.1 九卡纠偏:躺平类延迟金不经 instant_gold
          消费进字段,禁此处 logic 直写金币防双计),不设第五写端。

        余期是自然数计数(非索引):登记 3 → 三次有效推进后移除(躺平 3 节点)。
        """
        if node_key is not None and node_key == self._last_tick_key:
            return False, []
        self._last_tick_key = node_key
        expired: list[ActiveEffect] = []
        for e in list(self.entries):
            if e.remaining_nodes is None:
                continue
            if (node_key is not None and e.acquired_key is not None
                    and e.acquired_key >= node_key):
                continue
            e.remaining_nodes -= 1
            if e.remaining_nodes <= 0:
                self.entries.remove(e)
                expired.append(e)
        return True, expired

    def tick_node(self, node_key: tuple[int, int] | None = None
                  ) -> list[ActiveEffect]:
        """兼容口:仅返回到期条目(忽略 advanced 位;余额累加等桥插入位置用
        :meth:`advance_node` 取推进有效性)。"""
        return self.advance_node(node_key)[1]

    def consume_use(self, spec_id: str) -> int | None:
        """次数类余量递减(插入位置 = 跳过执行落地,§3.2.19/§5.1「插入位置现读递减」)。

        remaining_uses −1;归零移除(用尽 = 效果离场;「用尽后按钮恢复
        出战」待实机验,设计 §3.2.19 挂观察工作清单)。无已登记条目或该
        条目非次数类 → 返回 None 且零动作——递减插入位置与登记插入位置解耦:
        登记面缺位的局不炸执行链(保守端 = 记录缺失,不虚构递减)。
        """
        e = self.first(spec_id)
        if e is None or e.remaining_uses is None:
            return None
        e.remaining_uses -= 1
        if e.remaining_uses <= 0:
            self.entries.remove(e)
        return e.remaining_uses

    def consume_uses_up_to(self, spec_id: str, n: int) -> int:
        """次数类余量批量递减(免费购买条目「接下来 N 次购买免费」;插入位置 =
        买牌上报单点,免战牌出战上报递减同族)。逐张语义的批量扣减:至
        n 张扣完或余量耗尽,返回实际覆盖张数 = min(n, 递减前余量)——
        k 张购买按张计(k 张 = k 次),部分免费 = 免余量张、余张照付。
        未登记/非次数类 → 0 零动作(:meth:`consume_use` 保守端同纪律,
        递减插入位置与登记插入位置解耦)。归零移除语义与 consume_use 一致
        (用尽 = 效果离场):批量扣减后单次移除,不做循环 consume_use——
        归零移除下 first() 返 None,循环形余量耗尽即踩空。"""
        e = self.first(spec_id)
        if e is None or e.remaining_uses is None:
            return 0
        free = min(max(0, int(n)), e.remaining_uses)
        e.remaining_uses -= free
        if e.remaining_uses <= 0:
            self.entries.remove(e)
        return free

    def on_level_up(self) -> None:
        """升级事件标记(插入位置 = prep_actions._level_up 成功返回处)。"""
        self._events[_EVENT_LEVEL_UP] = self._events.get(_EVENT_LEVEL_UP, 0) + 1

    def on_buy(self, card, star: int, k: int = 1) -> None:
        """购买回调(形态镜像 on_level_up;插入位置 = 买牌上报函数
        report_action_buy_card_param 获取计算完时点——落位 + 合成连锁 +
        升星分支全毕后触发,回调可见购买后的席面/升星事实;live 与 sim 同经
        上报函数唯一入口,两面同源)。

        - 计数 = bump ``CounterKey.BUY``(返利族「每购 3 张 5 费」门槛面),
          满栏合成一击多买按实际张数 k 计 k 次;
        - ``card``/``star`` = 购买族效果分派预留位入参(现役零消费——
          按触发类型过滤的触发谓词表未建模前,分派面不展开,与
          :meth:`bump_key` 同款「只推进不解释」纪律)。
        """
        self.bump_key(CounterKey.BUY, n=max(1, int(k)))

    def on_battle_end(self) -> None:
        """战斗结算事件标记(生产插入位置 = CwScreenBattleWait 结算观察写端
        _record_round_outcome 非 telemetry_only 分支——真实结算才标记,
        败局页 telemetry-only 补录不标记,与 apply_settlement_cover 同口径;
        原 on_round_end 候选宿主已删除)。"""
        self._events[_EVENT_BATTLE_END] = self._events.get(_EVENT_BATTLE_END, 0) + 1

    def event_count(self, kind: str) -> int:
        return self._events.get(kind, 0)

    def set_xp_window_anchor(self, spec_id: str,
                             pos: tuple[int, int]) -> bool:
        """条件窗口达成位伴生基准写入(一次性:已设置拒绝重写;载体申报 =
        ``ActiveEffect.anchor_pos`` 字段注)。

        条目在场且 anchor_pos 为 None → 写入返回 True;条目不在场或已设置
        → 零动作返回 False(达成位单调不可改,重复检测/重复上报天然幂等)。
        写端 = 发放桥 grant_effect_node_xp 兜底检测 + 主插入位置
        _record_lv8_window_start(购买经验上报尾段),两端同经本方法,
        零旁路直改。
        """
        e = self.first(spec_id)
        if e is None or e.anchor_pos is not None:
            return False
        e.anchor_pos = pos
        return True

    def bump(self, spec_id: str, key: str, n: int = 1) -> None:
        """计数器自增(按 (spec_id, key) 定点;测试/定向修正用)。

        生产插入位置按键定位:REFRESH/BUY = 动作上报链(on_buy/record_refresh),
        XP_GRANTED = 升级窗口发放桥 grant_effect_node_xp(每发放一节点 +1,
        窗口耗尽判定与剩余导出的计数源,cw_game_state 发放桥区)。
        """
        e = self.first(spec_id)
        if e is not None:
            e.counters[key] = e.counters.get(key, 0) + n

    def set_counter(self, spec_id: str, key: str, value: int) -> None:
        """计数器置数(覆盖写非自增;条目不在场零动作,bump 同款静默形)。

        适用 = 「条件评估结果」类单拍快照键(现役 = INTEREST_TOPUP 开源节流
        条件息顶满待消费额):每拍覆写 0↔帽,与自增形(bump)语义分立——
        置数键禁走 bump(窗口异常未消费时累加会把单拍值放大成错发)。
        """
        e = self.first(spec_id)
        if e is not None:
            e.counters[key] = value

    def bump_key(self, key: str, n: int = 1) -> None:
        """动作侧全量计数推进(插入位置 = 刷新上报函数,§5.1「刷新=计数累加」;
        生产单点 = report_action_refresh_shop_param 统一触发)。

        对全部**声明过记账义务**(duties.track=True)的已登记条目推进
        counters[key]:计数消费按 (spec_id, key) 隔离读(:meth:`counter`),
        无关条目的同键计数零消费面。「谁要记账」的声明单一源 =
        EffectSpec.duties.track,本方法只推进不解释——按触发类型过滤
        (如只推进 ON_REFRESH 条目)需每键一份触发→条目谓词表,在注册表
        未结构化触发谓词前属过度建模。n 默认 1 = 单次动作。生产插入位置 =
        刷新上报函数(REFRESH=刷新回执)/ 商店落地门(BUY=购买回执,未
        落地不计数)。
        """
        for e in self.entries:
            if not e.spec.duties.track:
                continue
            e.counters[key] = e.counters.get(key, 0) + n

    def record_refresh(self, free: bool) -> None:
        """刷新执行计数统一入账(触发点 = 刷新上报函数
        report_action_refresh_shop_param,生产 = 刷新 op 自上报,sim 与
        生产同一段 op 代码同口自上报,落地门零重复触发)。

        行为口径(2026-09-21 Field 化收窄:免费余额分支迁状态容器字段
        ``gs.free_refresh_left``,扣减由上报函数 write_logic 承载;本方法
        只留两计数累计,``free`` 形参保留 = 调用方判定语义不变):
        - refresh_total 恒 +1(付费+免费全量);
        - free=True(免费帧):**不动** refresh_paid(付费累计,长线利好
          阈值型「花费金币进行30次刷新」的计数载体,免费帧混入即毒化);
        - free=False:refresh_paid +1;
        - 同帧推进按策略触发计数(bump_key(CounterKey.REFRESH),采购专员
          族门槛面)——「一次刷新,账本一处入账」。
        """
        self.refresh_total += 1
        self.bump_key(CounterKey.REFRESH)
        if not free:
            self.refresh_paid += 1

    def record_interest_earned(self, amount: int) -> None:
        """利息入账统一唯一入口(写端纪律同 record_refresh:计数只经唯一入口
        推进,禁调用方旁路直加——双写面 = 漂移温床)。写端全集见
        ``interest_earned`` 字段注释(sim 两处 + live 三来源)。

        - ``amount < 0`` 拒收 raise(单调累计账无递减语义,
          bump_equip_progress 同款防线;息分量恒非负,负值 = 调用错);
        - 0 合法(息 0 轮照常入账,零增量——保持「每收入刻必过唯一入口」
          的写端纪律,便于对账覆盖度核查)。
        """
        if amount < 0:
            raise ValueError(f'amount 须为非负数(累计账只增),得 {amount}')
        self.interest_earned += amount

    def record_ore_open(self, n: int) -> None:
        """晶矿开成入账统一唯一入口(写端纪律同 record_refresh:计数只经
        唯一入口推进,禁调用方旁路直加;写端唯一 = 采晶矿上报函数尾部,
        席满/缺级跳点不入账 = 「点开才计数」)。

        - ``n <= 0`` 拒收 raise(单调计数器无递减语义,
          bump_equip_progress 同款防线;开成点数恒正,非正 = 调用错);
        - 不进快照(接管局计数从 0 起,接受面 = 刷新计数同款)。
        """
        if n <= 0:
            raise ValueError(f'n 须为正数(单调计数器只增),得 {n}')
        self.ore_open_total += n

    def bump_equip_progress(self, equip_name: str, wearer: str,
                            n: int = 1) -> int:
        """装备效果进度推进(单调计数器,§3 模型:事件发生就 +1、永不递减
        永不重置)。返回推进后的累计值;n 非正数 = 调用错显式炸错(单调
        计数器无递减语义)。同 (装备名,装备者) 键天然隔离,不串账;
        同名装备多件同主合并计数(实例区分无观察基准,合并 = 少发不多发,
        保守向——见 :func:`settle_copy_machine_participation` 申报)。"""
        if n <= 0:
            raise ValueError(f'n 须为正数(单调计数器只增),得 {n}')
        key = (equip_name, wearer)
        self.equip_progress[key] = self.equip_progress.get(key, 0) + n
        return self.equip_progress[key]


# ============================================================ portal 登记端(环境源)
# (投资环境确认落地的效果登记;生产插入位置 =
# CwScreenInvestEnv._decide_and_act 确认链,active_env 写入同址,best-effort
# 不阻塞确认链。结构化条目 = 经济环境(ENV_ECONOMY 命中),payload 复用
# ENV_ECONOMY 表内同一实例(单一源,不复制数值——与 STRATEGY_EFFECTS payload
# 引 STRATEGY_ECONOMY 同实例的纪律同款);未入模环境登记 UnitBuffRef 占位
# (效果原文存档,可见性优先,bot 零响应),G 组(ENV_GIFTS)占位 notes 附
# GiftGrant 摘要。查询口 = inventory 现有
# 遍历(by_source/first;原 ``by_category``/``by_trigger``/``predict_for``
# 查询口已随死代码清偿移除);本登记端零决策消费——经济判据接登记
# 数据归后续批。
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
        # (成长基金到级同族先例)。**不走 N_NODES 余期通道**:登记时点
        #(开局选环境)≠条件达成时点(lv8),余期从登记起递减会提前耗尽——
# 窗口状态 = 条目 anchor_pos 达成位 + XP_GRANTED 单调计数(载体与
        # 发放单一源 = kernel/cw_game_state 发放桥 grant_effect_node_xp),
        # duration=PERMANENT 保占位(环境 = 选定后整局在场)。
        '成功经验': EffectSpec(
            id='138', name='成功经验', trigger=TriggerKind.CONDITIONAL,
            duration=DurationKind.PERMANENT, category=EffectKind.ECONOMY,
            payload=ENV_ECONOMY['成功经验'],
            notes='条件窗口:升8级后3节点每节点+12XP;期限排程已落地(载体 = 本条目'
                  'anchor_pos 达成位 + XP_GRANTED 单调计数,剩余计算侧导出;发放 = '
                  'kernel 发放桥 grant_effect_node_xp 节点边界每拍检查,达成当拍不计、'
                  '后继 3 节点各计;主挂点 = 购买经验上报尾段记达成位)'),
        # 每取一张策略 +2×已持有数(id 147):触发面 = 每次取投资策略,TriggerKind
        # 无 ON_PICK 值 → 占 CONDITIONAL + notes 声明(禁私加枚举值——触发词表
        # 扩值须同步插入位置面评审,登记端零消费不构成扩值依据)。
        '策略大师': EffectSpec(
            id='147', name='策略大师', trigger=TriggerKind.CONDITIONAL,
            duration=DurationKind.PERMANENT, category=EffectKind.ECONOMY,
            payload=ENV_ECONOMY['策略大师'],
            notes='触发面 = 每次取投资策略(词表无 ON_PICK 值,占 CONDITIONAL 声明);'
                  '金面 = +2×含本张已持有数(用户裁定 2026-10-26;第 k 张到手'
                  '发 2k,首张 2)'),
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
    环境(结构化补表未跟上 spec)走占位登记不炸(登记端对 3.3
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
    - G 组(ENV_GIFTS 命中)占位 notes 附 GiftGrant 摘要(发放形状字段
      全量渲染,10 字段中 9 渲染 + sell_value_note 显式排除,清单闭合;
      渲染登记形状静态值,不渲染运行期采样身份,「判读面可读」口径);
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
        # 发放形状字段全量渲染(段名 = 通道语义;清单闭合声明:sell_value_
        # note = 注释性估值注记(【注】下界)非发放形状,渲染进占位 notes
        # 是噪声,现值全仓零登记,排除无行为差)
        _parts = ['GiftGrant']
        if grant.chars_immediate:
            _parts.append(f"即时[{'、'.join(grant.chars_immediate)}]")
        if grant.chars_conditional:
            _parts.append('条件[' + ';'.join(
                f'{c}:{note}' for c, note in grant.chars_conditional) + ']')
        if grant.items_immediate:
            _parts.append(f"道具[{'、'.join(grant.items_immediate)}]")
        if grant.items_scheduled:
            _parts.append('定时道具[' + ';'.join(
                f'{item}@{node_key}'
                for node_key, item in grant.items_scheduled) + ']')
        if grant.chars_random_immediate:
            _parts.append('随机[' + ';'.join(
                (f'{s.cost}费' if s.cost is not None else f'阵营{s.faction}')
                + f'@{s.star}星'
                for s in grant.chars_random_immediate) + ']')
        if grant.equips_random_immediate:
            _parts.append(f"随机装备[{'、'.join(grant.equips_random_immediate)}]")
        if grant.equips_immediate:
            _parts.append(f"即时装备[{'、'.join(grant.equips_immediate)}]")
        if grant.advisor:
            _parts.append('advisor=顾问入商店')
        if grant.replaces_opening_supply:
            _parts.append('开局替换')
        _notes = ('未入模占位(效果原文存档,bot 零响应);'
                  + ' '.join(_parts))
    else:
        _notes = '未入模占位(效果原文存档,bot 零响应)'
    _pid = (_env.source.split(':', 1)[1]
            if _env.source.startswith('plaza:') else _env.source)
    return EffectSpec(
        id=_pid, name=_env.name, trigger=TriggerKind.PLANE_START,
        duration=DurationKind.PERMANENT, category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=_env.effect), notes=_notes)


def register_portal_from_env(session: object, env_name: str) -> EffectSpec | None:
    """投资环境确认落地 → portal 源登记(登记端共用体;
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
    - acquired_key = 登记时点节点序位快照((位面,轮) 元组;GameState
      节点单例;节点未观察(引导窗)= None 缺位,last_state 帧回退已停用删除);
    - 返回本次登记的 spec(幂等跳过/未知名返回 None,调用侧日志留存证据)。

    game_state_of 运行期函数内 import:GameState 状态容器模块头反向 import
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
    effects.register_portal(_spec, _portal_acquired_key(gs, session))
    return _spec


def _portal_acquired_key(gs: object, session: object) -> tuple[int, int] | None:
    """登记时点节点序位快照((位面,轮) 元组;register_affixes_from_names
    同式):GameState 节点单例直接取 (plane, round_num)——键表示下零坐标
    换算(编号正解已停用),与推进入账(advance_node 键)同键
    契约(cw_effect_inventory「登记当节点不推进」守卫由同键保证)。节点
    未观察(引导窗)= None(登记期快照缺位不炸登记面;last_state 帧回退
    已停用,session 参数保留签名兼容,不再消费)。"""
    _nd = getattr(gs, 'node', None)
    _nd_val = _nd.value if _nd is not None else None
    if _nd_val is not None:
        return int(_nd_val.plane), int(_nd_val.round_num)
    return None


# ============================================================ 账本→字段桥·板面重写
# (GameState 数据结构设计 §5 全员晋升/人力重组两行;effect-domain.md §8 同名条。
# 与 cw_game_state 的 apply_effect_burst_grant 等三桥同族,但宿主不在
# cw_game_state——其模块头 import 本模块,桥落本侧可免模块级成环;
# ChannelSig/BenchView 运行期函数内惰性取。插入位置 = 选卡时点(设计 §3.2.3
# 「效果写端(选卡时点、非 op)」),生产接入调用(投资两屏迁移起)= 获得链
# kernel/cw_gain_chain.py::gain_invest_strategy 登记分支(register_strategy/
# apply_effect_burst_grant 同点);原 CwScreenInvestStrategy 画面 op 写点
# 已停用。)


# ===== 现金为王单卡判别/换算常量(板面重写桥出售支记账门用)=====
# 条目判别键与换算系数集中此处防字面量散落(消费端 = 本桥出售支记账段;
# 与注册表 cw_investments.STRATEGY_EFFECTS['现金为王'].id 的一致性由键×id
# 对拍测试直锁,同 cw_investments.HYPEREMIT_SPEC_ID 先例——本模块「模块头
# 零包内 import」契约禁反向引注册表,常量故宿本侧)。
CASH_KING_SPEC_ID: str = '250301'
#: 卡文「护盾量等同于该次出售角色所获得总金币数*1000」的换算系数直读
#(金币→护盾量;数值单一源在此,桥记账与测试对拍共用,禁散落副本)。
CASH_KING_SHIELD_PER_GOLD: int = 1000


@dataclass(frozen=True)
class BoardRewriteReport:
    """板面重写桥执行报告(留存证据/测试用;零决策消费)。"""

    rewrite: str                   # board_rewrite 语义值(BOARD_REWRITE_* 词表)
    refund_gold: int               # sell_all 出售面退款合计(sell_refund 口径,
                                   # 只含已读单位);该值是否已入金看
                                   # partial_read 与金字段本身(部分读时仅在
                                   # 此留存证据、未入金);upgrade_all 恒 0(无出售面)
    sold_units: int                # sell_all 已读出的出售单位数(前台+后台+备战席;
                                   # 字段从未观察 = 0,不代表实际卖数)
    cleared_fields: tuple[str, ...] = ()   # 实际执行逻辑清空的 GameState 字段名
    partial_read: bool = False     # True = 出售域未全读(deployed/bench
                                   # 任一从未观察)→ 退款公式输入不完整,退款
                                   # 零写入等观察收尾(effect-domain.md §6.3);
                                   # upgrade_all 恒 False(无出售面)


def apply_board_rewrite(gs: GameState, spec: EffectSpec, *,
                        frame: str = '') -> BoardRewriteReport | None:
    """桥·板面重写形态(选卡时点一次性):按设计 §5 写入归属两行落
    EffectSpec.board_rewrite 的语义。返回执行报告;非板面重写条目(payload
    无 board_rewrite 或为空)返回 None 零动作。

    **归属两行(单一源 = GameState 数据结构设计 §5)**:
    - 全员晋升(BOARD_REWRITE_UPGRADE_ALL):替换面 = 随机(全场升为高 1 费
      随机角色),不可准确算 → **零逻辑写端,观察收尾**(§5.3 归属判据随机
      分支)——本桥对它零写入,报告作负写端留存证据;附带「获得 2 个拆装扳手」
      = 装备库存精确增量,已结构化出列(策略卡获得效果条目 =
      cw_gain_effects.PICK_INVEST_EFFECTS['全员晋升'],具名装备授予工厂经
      gain_equipment 直写 gs.equips,精密金面前置 fail-closed 申报在工厂
      docstring),不在本桥建模——本桥只辖板面重写句,装备句经获得链
      ③段效果体分派(两条效果条目状态容器域不相交,板面 equips)。
    - 出售支(BOARD_REWRITE_SELL_ALL 素出售/BOARD_REWRITE_SELL_ALL_DEAL
      兼发牌条目):出售面 = 确定性 → 逻辑写(§5.3
      归属判据确定性分支;状态容器清空写经锚定标志择道,未锚定期走随机态,
      见清空写段注释)——前台/后台/备战席清空 + 退款按卖价公式入金
      (退款单一源 = cw_economy.sell_refund,费用查表单一源 =
      cw_economy.bench_char_cost,未知 char_id 退中费 3)。发牌面 = 随机
      → **不建逻辑写,进席落位 live 走观察覆盖、sim 由后端发牌条目承接**
      ——本桥禁替发牌面造单位;发牌条目是人力重组卡文附加面非出售语义固有
      (大裁员/降本增效/现金为王素出售无发牌),具发牌条目卡以 _DEAL 值
      声明。护盾记忆量(现金为王单卡):退款权威写入同闸记账实例
      counters[CounterKey.SHIELD_BANK] = 退款 × CASH_KING_SHIELD_PER_GOLD
      (spec-id 门控,见记账段注释;空场/出售域未全读零记账等观察收尾,
      禁部分记账)。

    **字段从未观察(value=None)= 无状态容器可写,跳过**(同族先例 =
    project_effect_capacity):选卡后的下一备战帧观察必全量重读板面,
    跳过不损真值到达。**出售域未全读**(deployed/bench 任一
    value=None,典型 = 中断恢复对局/观察缺口局)= 退款公式的输入不完整(未读
    域实际卖数未知,refund 只是已读面的部分值)→ 不满足归属判据确定性
    分支「确定性公式+已知输入」的前提(effect-domain.md §6.3)→ 退款
    零写入留存证据(报告 partial_read=True + 日志),等观察收尾——禁把部分
    退款以 logic 标写成权威值(观察帧覆盖前记录层留错误金)。gold 未读
    (None)= 无累加基座,跳过金写入(禁把退款当余额);退款合计为 0
    (出售域全未读/空场)同样跳过——禁把观察金翻标成 logic(§2.1 来源
    标记到字段)。bench 清空保留现容量(节省工位类容量改写归容量逻辑态
    直写桥适用范围,两桥互不越界)。

    **sim 语义申报(适用性/对齐)**:本桥本体不接 sim——sim 状态副本事实由
    后端状态副本写入分支真值直写(evidence `sim:` 族,
    `cw_sim_base.SIM_EVIDENCE_PREFIX`)。板面重写族五注册卡按面分述:
    人力重组/大裁员/降本增效/现金为王出售面 = **实机和模拟器两边同链已通**(本桥经获得链在 sim 局真实
    执行,存量锁钉死;现金为王护盾记账在本桥出售支段内,实机和模拟器两边随链自动
    一致);人力重组发牌面(2★ 三档随机)= sim 由后端发牌条目
    承接(`cw_sim_backend.apply_strategy_pick_sell_all_deal`,判据集 =
    具发牌条目语义值派生,挂 `_on_invest_picked` 选卡落地拍,授予出口派生
    桶直写,live 零假发牌——本桥「禁替发牌面造单位」裁定对实机和模拟器两边维持);
    大裁员/降本增效/现金为王素出售无发牌面(卡文无发牌句,不入发牌判据集,sim 局零假发
    牌),大裁员/降本增效卖价 ×2 修饰 = 全族缺口低估申报(退款按基础公式记,口径待
    实采;现金为王卡文无「双倍」句,退款 = 标准卖价);全员晋升替换面 = 维持 sim 零建模(穿戴装备归属未采证,禁猜;
    其拆装扳手×2 装备条目经获得链 sim 同链生效,不在本申报面)。残余未建模
    申报面 = sim-design §8.2「板面重写族」行。

    **未知语义值 = 保守 no-op + 留存证据**(禁猜):新板面重写卡入册时须同步
    扩本桥归属分支,防注册表声明了语义而写端静默丢。
    """
    rewrite = str(getattr(getattr(spec, 'payload', None), 'board_rewrite', '')
                  or '')
    if not rewrite:
        return None
    if rewrite not in (BOARD_REWRITE_UPGRADE_ALL, BOARD_REWRITE_SELL_ALL,
                       BOARD_REWRITE_SELL_ALL_DEAL):
        log.warning('[cw!][effect-bridge] 未知板面重写语义 %r(spec=%s)'
                    ' → 保守 no-op(禁猜;扩归属分支后生效)', rewrite, spec.name)
        return None

    if rewrite == BOARD_REWRITE_UPGRADE_ALL:
        # 整场上阵替换形态:随机面零逻辑写端(设计 §5 全员晋升行),报告
        # 仅作负写端留存证据;本分支禁新增任何写入。
        return BoardRewriteReport(rewrite=rewrite, refund_gold=0, sold_units=0)

    # —— sell_all 族(素出售 + 兼发牌条目):全场出售形态 ——
    # 出售面两语义值同段执行;发牌面不归本桥(live 观察覆盖/sim 后端
    # 发牌条目,判据按语义值细分,见词表注)。
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
        anchor_aware_write,
    )

    front = gs.deployed.value
    view = gs.bench.value
    bench_units = [s.unit for s in view.slots
                   if s.kind == 'unit' and s.unit is not None] \
        if view is not None else []
    from sr_od.application.currency_war.kernel.cw_game_state import (
        deployed_rows_of_view,
    )
    _front_units, _back_units = deployed_rows_of_view(front)
    sold = _front_units + _back_units + bench_units
    refund = sum(sell_refund(int(u.star), bench_char_cost(u, gs))
                 for u in sold)
    # 出售域全读判据:front/back 均已读且 bench view 已读,退款公式的输入
    # (实际卖数)才完整——任一子域从未观察时 refund 只是已读面的部分值,
    # 归属判据确定性分支「确定性公式+已知输入」前提不成立
    # (effect-domain.md §6.3),该退款禁入金(等观察收尾)。
    partial_read = front is None or view is None

    ev = f'effect_board_rewrite@{frame}' if frame else 'effect_board_rewrite'
    # 组签名:一次出售清空 = 一次逻辑计算,组内行同 group(§3.2.1 group_id
    # 语义);actor 复用同族写入者名 EffectLedgerBridge。
    sig = ChannelSig(family='logic_hook', actor='EffectLedgerBridge',
                     mode='compute',
                     group_id=f'hook:EffectLedgerBridge@{gs.write_seq + 1}')

    cleared: list[str] = []
    # 状态容器清空写经锚定标志择道(rand=False = 锚定后按本桥确定性语义):
    # 未锚定 = 未验证推算走随机态,首观察静默覆盖不触发失配告警;
    # 锚定后走 write_logic,失配网生效(择道单一源 = anchor_aware_write)。
    # deployed 清空 = 规范形空视图:front_slots 定长 4 / back_slots 按
    # 现视图容量(缺省 6)——空列表违反定长不变量,且会让前排直址写
    #(deploy_move 前排分支)IndexError(评审 需修-1)。
    write = anchor_aware_write(gs, rand=False)
    if front is not None:
        from sr_od.application.currency_war.kernel.cw_game_state import (
            DEPLOYED_BACK_CAPACITY_DEFAULT,
            DEPLOYED_FRONT_CAPACITY_DEFAULT,
            DeployedView,
        )
        _back_len = len(getattr(front, 'back_slots', None) or []) \
            or DEPLOYED_BACK_CAPACITY_DEFAULT
        write(gs.deployed,
              DeployedView(front_slots=[None] * DEPLOYED_FRONT_CAPACITY_DEFAULT,
                           back_slots=[None] * _back_len),
              produced_by='EffectLedgerBridge',
              evidence=ev, sig=sig)
        cleared.append('deployed')
    if view is not None:
        write(
            gs.bench,
            # 槽位表原位清空:槽数保持观察现值,全槽置空;容量保留现值
            #(容量改写适用范围 = 容量逻辑态直写桥 project_effect_capacity,互不越界)。
            BenchView(slots=[BenchSlot(kind='empty')] * len(view.slots),
                      capacity=view.capacity),
            produced_by='EffectLedgerBridge', evidence=ev, sig=sig)
        cleared.append('bench')
    # 金写入门三条件齐备才 write_logic:基座已读 + 退款非零 + 出售域全读。
    # 零退款(出售域从未读过/空场)无可入账增量;partial_read 时输入不完整
    # (§6.3)——两种情形金字段都保持原来源不动,禁把观察金翻标成 logic
    # (§2.1 来源标记到字段);部分读的已读面退款在报告留存证据(refund_gold ×
    # partial_read)。
    if partial_read and refund > 0:
        log.warning(
            '[cw!][effect-bridge] 板面重写出售域部分读(deployed=%s'
            '/bench=%s)→ 退款 %d 零写入等观察收口(§6.3 输入不完整)',
            front is not None, view is not None, refund)
    if gs.gold.value is not None and refund > 0 and not partial_read:
        gs.write_logic(gs.gold, int(gs.gold.value) + refund,
                       produced_by='EffectLedgerBridge', evidence=ev, sig=sig)
    # 护盾记忆量记账(现金为王单卡,spec-id 门控;写端唯一 = 本段):与退款
    # 权威写入同闸(出售域全读 ∧ 退款非零)——空场(退款零)/出售域未全读
    #(partial_read,输入不完整 §6.3)两态护盾随退款同拍零记账等观察收尾,
    # 禁部分记账(护盾量 = 退款合计的一次性函数,按部分退款记账即记错量)。
    # 登记分支每局至多一次(投资单选族选卡即耗),无重入闸;系数 = 卡文明写
    # ×1000(CASH_KING_SHIELD_PER_GOLD 单一源);实例 = 获得链登记分支先行
    # 注册的同 id 条目,缺席(直调桥未登记形态)静默跳过。
    if spec.id == CASH_KING_SPEC_ID and not partial_read and refund > 0:
        _shield_entry = gs.effects.first(spec.id)
        if _shield_entry is not None:
            _shield_entry.counters[CounterKey.SHIELD_BANK] = \
                refund * CASH_KING_SHIELD_PER_GOLD
    return BoardRewriteReport(rewrite=rewrite, refund_gold=refund,
                              sold_units=len(sold),
                              cleared_fields=tuple(cleared),
                              partial_read=partial_read)


# ============================================================ 账本→字段桥·装备改写写端
# (写入归属申报单一源 = kernel/cw_affix_effects.py EQUIP_REWRITE_DECLARATIONS
# × EQUIP_WRITE_SIDES;归属判据 = GameState 数据结构设计 §5.3 / 权威版本
# docs/develop/sr_od/application/currency_war/game_state/effect-domain.md §6.3。宿主放本侧与
# 板面重写桥同理:申报模块 cw_affix_effects 头 import 本模块,桥落本侧免
# 模块级成环;GameState 真类运行期函数内惰性取,维持「模块头零包内
# import」契约。)
#
# **窗口独占性分形**(确定性面两种实现形的分界):观察覆盖字段的 logic 直写,
# 只有「写入 → 下一次观察」窗口内无其他同字段变更源时才是完全预测,失配才
# 等价推算 bug(§2.3 以实际观察为准);窗口内有未接写端的共享变更源(节点边界金面与
# 轮首收入三支同窗——live 写端载体未指派,设计 §8.7 尾批行)时,直写=系统性
# 失配刷缺陷台账。故装备确定性面按触发窗口独占性分两形实现:
# - **写端桥**(apply_/spawn_/grant_/transform_ 前缀):触发窗口天然独占
#   (获得回执/工具拖拽回执/选定回执),write_logic 直写,下一观察覆盖核实;
# - **贡献算术**(equip_*_gold 前缀纯函数):触发窗口与未接写端共享(节点
#   边界金/获得时点战利品),零直写——组合写归节点边界金结算载体与获得
#   结算载体(接入调用批取各贡献合计一次写入),先落单独直写必刷缺陷台账;
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
#: 进阶→特权装备映射后缀(注册表 36 进阶 ↔ 36 特权全量双射,覆盖率由测试
#: 对 cw_equipment_data 钉死;特权赋予卡确定性变换的映射单一源)。
EQUIP_PRIVILEGE_SUFFIX: str = '·特权'


def held_equip_count(gs: GameState, name: str) -> int:
    """装备持有件数单一源(贡献算术/组合写的计数基础):前排已穿 + 后排已穿
    + 备战席已穿(记录内)+ 装备库存,四源求和。

    - 边界:备战席装备图标观察面=负探针(机制恒空,设计 §3.2.18「窟窿二」),
      记录内备战席单位 equips 通常为空表——持有可能被低估,盲区随观察面
      建模收窄,消费侧对账按真值归因;
    - 字段从未观察(value None)= 该源跳过(不猜);
    - 纯读零写入(write_seq 不动)。
    """
    total = 0
    from sr_od.application.currency_war.kernel.cw_game_state import (
        deployed_rows_of,
    )
    for units in deployed_rows_of(gs):
        for u in units:
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
    """装备已穿件数(「装备者」口径计数基础):前排 + 后排已穿。

    备战席已穿不计——负探针盲区同 :func:`held_equip_count` 边界;装备库存
    (未穿)不计——「装备者」语义 = 穿戴者。纯读零写入。
    """
    total = 0
    from sr_od.application.currency_war.kernel.cw_game_state import (
        deployed_rows_of,
    )
    for units in deployed_rows_of(gs):
        for u in units:
            total += sum(1 for e in (u.equips or []) if e == name)
    return total


def equip_node_gold_grant(gs: GameState) -> int:
    """贡献算术·财富金面(进新节点 +4×持有件数):节点边界金结算载体的
    合计项之一,纯算术零直写。

    零直写的依据:节点边界窗口与轮首收入三支共享且其 live 写端未指派
    (设计 §8.7 尾批行),单独直写=系统性失配刷缺陷台账;组合写归该载体
    (接入调用批取各贡献合计一次写入),落地前金面维持观察覆盖兜底。
    持有口径 = :func:`held_equip_count`——官方文无「装备者」限定(对比宝钻
    金面明写),未穿戴是否生效待实采;宽口径(持有即计)使多计进对账可见,
    优于漏计静默。
    """
    return held_equip_count(gs, '财富') * WEALTH_GOLD_PER_NODE


def equip_diamond_phase_gold(gs: GameState, *, phases_elapsed: int) -> int:
    """贡献算术·财富宝钻金面(装备者每 3 备战阶段 +1 金×已穿件数):
    节点边界金结算载体的合计项,纯算术零直写(依据同 :func:`equip_node_gold_grant`)。

    - ``phases_elapsed`` = 穿戴起累计备战阶段数(自然数,接入调用批逐件进度
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
    - hp 从未读(None)= 无累加基座,跳过零写入返回 0(hp 写入闸覆盖:不可信
      不写,禁造假基座;同族先例 = 板面重写桥金面跳过);
    - 生产插入位置 = 获得回执(接入调用批);接入调用前观察覆盖兜底,与现状零行为差。
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
    """桥·装备族单位入席分支(共享):把复制/发放单位落进备战席第一个空槽,
    write_logic 直写(确定性→逻辑写,归属判据确定性分支)。服务面 =
    数据拷贝仪族计数分支(成熟回执,无门)——员工/完美投影仪消费已停用
    (tool-gain-report 迭代:投影仪复制改走获得链
    ``cw_gain_chain.gain_character`` 统一时序,登记面映射 =
    cw_affix_effects.EQUIP_WRITE_SIDES report: 形;本桥留在只覆盖计数分支)。
    (分身墨镜系获得发放分支已改覆盖
    apply_equip_acquire_consequence——获得后果全渠道统一,本桥不再服务
    该两行;数据拷贝仪Max 行保持本桥覆盖计数分支,其获得后果由后果函数按
    数据行统一覆盖,不经登记表双登记。)

    - ``cost``/``cost_gate``:拖动目标费用与其门(>0 时 cost 超门拒落 =
      游戏端拒拖拽语义;员工投影仪 =3,无门传 0);费用查表单一源在调用侧
      (cw_state.bench_char_cost 同源域);
    - 席满(无空槽,与派生 bench_free_slots==0 同源)或 bench 从未观察
      → False 零写入:游戏端拒落/无状态容器,落位真值由观察给出(§3.2.8
      「席满点不动」同源);
    - star 集 1..3 外 = 调用错,显式炸错(禁静默写错;银狼LV.999 星级已
      随获得后果定案为 1★[口述·权威 2026-09-18],走后果函数不入本桥);
    - 落位单位位置 = 落位物理槽(slots[i] ↔ 槽 i+1,BenchView 坐标系;
      Unit 无槽位信息位,位置 = 子表下标纯派生——)。
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
                                                  equips=[]))
    ev = f'equip_spawn@{frame}' if frame else 'equip_spawn'
    gs.write_logic(gs.bench,
                   BenchView(slots=slots, capacity=view.capacity),
                   produced_by='EffectLedgerBridge', evidence=ev,
                   sig=_equip_bridge_sig(gs))
    return True


def grant_equip_item(gs: GameState, name: str, *, frame: str = '') -> bool:
    """桥·装备单件入区(好运令牌选定回执等「选定后确定」面):装备库存
    追加一件,write_logic 直写。库存从未观察(None)= 无状态容器,跳过返回
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


#: 锻冶专家:刃卡规范名(刃锻特权化次数账门①持卡判定键;登记面 =
#: STRATEGY_GRANTS/STRATEGY_BINDINGS 同名条目在册零改动,卡文 =
#: data/cw_invest_data.py id 360601)。
FORGE_PRIVILEGE_CARD: str = '锻冶专家:刃'
#: 该卡辖域角色(卡面「【刃】的装备栏」/「【刃】在场上或备战席」;
#: 与 STRATEGY_GRANTS 同卡条目 chars_immediate 单成员一致,快照锁钉死)。
FORGE_PRIVILEGE_CHAR: str = '刃'
#: 扩次阈值(卡面「每获得10件任意装备,额外可生效一次」)。
FORGE_PRIVILEGE_GAINS_PER_CHARGE: int = 10


def record_forge_privilege_gain(gs: GameState, *, write: Callable[..., None],
                                sig: ChannelSig, producer: str) -> None:
    """刃锻特权化装备获得计数(锻冶专家:刃腿3 机制件;唯一调用点 =
    获得链 ``gain_equipment`` 原语尾段,本函数 = 装备域行为面单一宿主,
    与特权化桥同文件)。门①持卡 ∧ 刃在场门控,双门全过才计数:

    - 门①持卡:active_strategies 现值含 :data:`FORGE_PRIVILEGE_CARD`
      (穿报刃锻支同键,单一源);无卡局零行为差;
    - 在场门控:计数时点刃 ∈ deployed(front_slots/back_slots)∪bench
      容器现值判定——离场期间获得不计数不补计(卡文字面直辖);容器
      未观察(None)= 无真值基座按不在场计;bench 侧经
      ``cw_exec_state.bench_slot_unit`` 解包读口(消费端唯一合法入口,
      禁内联 kind 判断),deployed 侧 = 子表列表成员现值。

    计数口径 = 经原语的获得即 1 件(「获得」= 净新增字面直辖):合成
    产物(穿报内联不经原语)/冶金炉变异产物(变异面不走获得链)/特权化
    替换件(原位变换非获得)天然不计;装备获得转换拦截的装备分支目标
    经原语净新增入栏照计,占席道具分支不入装备栏不计;好运令牌选定
    回执桥 ``grant_equip_item`` 直写不经原语 = 在码漏计差集(申报制,
    不在本钩覆盖)。计数写通道随获得写通道(``write`` = 该次获得已择道
    的写分支,获得为猜测写(logic_rand)时计数同语义),达
    :data:`FORGE_PRIVILEGE_GAINS_PER_CHARGE` 整倍数 → 充能笔
    (charges_left +1)。零 rng:门序与计数全确定。
    """
    if FORGE_PRIVILEGE_CARD not in (gs.active_strategies.value or []):
        return
    present = False
    view = gs.deployed.value
    if view is not None:
        for unit in list(view.front_slots or []) + list(view.back_slots
                                                        or []):
            if unit is not None and unit.char_id == FORGE_PRIVILEGE_CHAR:
                present = True
                break
    if not present:
        bench_view = gs.bench.value
        if bench_view is not None:
            # 运行期惰性取(模块头零包内 import 契约,解包读口单一源)。
            from sr_od.application.currency_war.kernel.cw_exec_state import (
                bench_slot_unit,
            )
            for slot in bench_view.slots:
                unit = bench_slot_unit(slot)
                if unit is not None and unit.char_id == FORGE_PRIVILEGE_CHAR:
                    present = True
                    break
    if not present:
        return
    count = int(gs.forge_privilege_gained_count.value or 0) + 1
    write(gs.forge_privilege_gained_count, count, produced_by=producer,
          evidence='forge_privilege_gain', sig=sig)
    if count % FORGE_PRIVILEGE_GAINS_PER_CHARGE == 0:
        charges = int(gs.forge_privilege_charges_left.value or 0) + 1
        write(gs.forge_privilege_charges_left, charges,
              produced_by=producer, evidence='forge_privilege_recharge',
              sig=sig)


def privilege_counterpart(name: str) -> str:
    """进阶 → 对应特权装备名(:data:`EQUIP_PRIVILEGE_SUFFIX` 后缀映射;
    36 进阶 ↔ 36 特权全量双射由测试对注册表钉死,非进阶名入参得到
    无意义拼接,调用侧保证键域)。"""
    return name + EQUIP_PRIVILEGE_SUFFIX


def transform_equip_to_privilege(gs: GameState, source_name: str, *,
                                 frame: str = '') -> str | None:
    """桥·进阶装备特权化(特权赋予卡,拖装备回执 = 库存分支):装备库存中
    名为 ``source_name`` 的件替换为对应·特权名,write_logic 直写(确定性
    变换→逻辑写)。库存未观察/无此件 → None 零写入。

    拖角色入账分支(已穿进阶随机一件变特权)= 穿域改写,归工具执行批——现役
    执行侧对工具零操作(equipment_mechanics.md §经济账框架),两条分支接入调用前
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
# (装备申报面三贡献算术的组合写收尾,归属判据 = effect-domain.md §6.3
# 确定性分支:轮首收入三支与装备贡献全部确定性可算 → 逻辑写,且同窗变更
# 源必须合并为**单次**金面写入(窗口独占性分形段头注:节点边界窗曾与未接
# 写端的轮首收入共享,本载体即该窗的 live 写端收束——收入公式已收束
# cw_economy.round_start_income,本载体消费之,禁第二份收入算术;生产插入位置
# = 备战分支进节点边界,接入调用归覆盖批,接入调用前金面维持观察覆盖兜底)。
#
# 两窗结构(按触发窗口分形,同宿主一段):
# - **节点边界窗**(:func:`settle_node_boundary_gold`):轮首收入三支
#   (supply/reward/loss_comp/combat,分支派发与值分量单一源 =
#   round_start_income)+ 财富贡献(equip_node_gold_grant)+ 宝钻贡献
#   (调用侧折算增量传入)→ 单次 write_logic;
# - **获得回执窗**(:func:`settle_wrench_duplicate_gold`):精密扳手重复
#   获得金(申报行「组合写归获得结算载体」的实现位)——获得回执 → 下一次
#   金读数之间无其他金变更源,窗口独占,直接 +1 直写(与极·阿瓦隆获得 hp
#   桥同形)。到账战利品的金面仍走观察覆盖(§4 CwActionCollectOreParam),本载体不
#   吸收——随机/观察收尾面不进组合写。
#)


@dataclass(frozen=True)
class NodeBoundarySettlement:
    """节点边界金结算载体的执行报告(留存证据/测试用;零决策消费)。"""

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
    write_logic),实机 live 写端收束。

    - **收入面**:值分量与分支派发全部经 :func:`cw_economy.round_start_income`
      (收入收敛单一源,禁第二份);利息计算基数 = **结算前**金现值(本函数读
      ``gs.gold`` 后传入,调用方无须自取——单一金基座防息算双读);
      ``lost_node``/倍率/息修饰由调用方按其适用范围契约传入(败态消费、
      aggregate_economy 聚合归接入调用批)。
    - **装备贡献面**:财富 = :func:`equip_node_gold_grant` 现读现算;宝钻 =
      ``diamond_gold``(穿戴起逐件进度折算的**本拍增量**,由调用侧进度
      载体供给——进度载体缺位属缺口申报面,本载体禁内发明第二份,
      缺省 0 = 保守零授予,与现状观察覆盖零行为差)。
    - **单次写入**:全部同窗增量合并为一次 write_logic(窗口独占完全预测,
      失配等价推算 bug,§2.3);金未读(None)= 无累加基座,整拍跳过零
      写入(禁造假基座,板面重写桥金面同族先例);合计 0 同样跳过(无可
      入账增量,禁把观察金翻标成 logic,§2.1 来源标记到字段)。
    - **适用范围排除**:到期尾款金(effect-domain.md §7.3 禁 logic 直写防双计)、
      事件金、STRATEGY_ECONOMY 的 gold_per_node 族(
      「'invest' 键单列」)不在本载体——各自接入调用面另批;sim 收入路径
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
    :func:`equip_wrench_duplicate_gold` 的组合写收尾)。

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


# ============================================================ 工具执行批·穿域特权化分支
# (特权赋予卡拖角色入账分支的实现位:官方文「拖动到一个角色上使用,从角色已
# 穿戴的进阶装备中选择一件变为特权装备」——选定后变换确定性(36 进阶 ↔
# 36 特权后缀映射,:func:`privilege_counterpart`)→ 逻辑写;「选择」面 =
# bot 决策/回执事实,归调用侧,本载体只管选定后的写端。**本分支现役留在
# 不接**(tool-gain-report 迭代:用户裁定 2026-09-21 特权卡按不能拖角色
# 处理待实机测试,判据面只产库存分支、上报侧 char 分支 fail-closed 留存证据;
# 实机证可拖即升格接入调用,本桥为既定写端)。库存分支的 live 写端 =
# 工具上报合并单笔消费(cw_action_report/tool_use,映射桥同源)。)


def transform_worn_equip_to_privilege(gs: GameState, target: Unit,
                                      worn_name: str, *,
                                      frame: str = '') -> str | None:
    """桥·穿域特权化(特权赋予卡拖角色入账分支):已穿进阶装备单件原位变换为
    对应·特权名,write_logic 直写所在状态容器(前台/后台列表或备战席视图)。

    - ``target`` = 拖动目标单位(调用侧从**当前**观察态取得;按 frozen
      dataclass 全字段相等定位——状态已变则定位失败,零写入返回 None,
      禁按陈旧快照盲写);
    - ``worn_name`` = 选定的已穿进阶装备名;不在 target.equips = 调用错,
      显式炸错(「选择一件」的合法输入域 = 该单位已穿名单;进阶类别
      校验归调用侧分派入口,机制层零注册表依赖);
    - 单件语义 = 只变换**首个**命中件(官方「选择一件」;同名多件余件
      原样);单位不可在席间复制出现(槽位唯一),相等命中恰一个;
    - 定位成功但目标所在状态容器从未观察 = 不可能(单位对象来自状态容器现值);
      返回变换后的特权名;零写入分支返回 None。
    """
    if worn_name not in target.equips:
        raise ValueError(
            f'worn_name 须为 target 已穿装备(「选择一件」合法输入域),'
            f'得 {worn_name!r} ∉ {target.equips!r}')
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
        BenchView,
    )
    counterpart = privilege_counterpart(worn_name)

    def _replaced(unit: Unit) -> Unit:
        equips = list(unit.equips)
        equips[equips.index(worn_name)] = counterpart
        # dataclasses.replace 复制(未指定字段保留原值):本桥 = 同实体
        # 变换(docstring「全字段相等定位/槽位唯一」),实例号 uid 必须随行
        # ——手动三字段新构造会清零 uid,被环境上场锁锁住的单位经特权
        # 换装即丢身份,sim 端守卫提前放行(T-30 V2-1 修法)。
        return replace(unit, equips=equips)

    ev = f'equip_worn_transform@{frame}' if frame else 'equip_worn_transform'
    from dataclasses import replace as _dc_replace

    dep_view = gs.deployed.value
    if dep_view is not None:
        for sub_name in ('front_slots', 'back_slots'):
            units = getattr(dep_view, sub_name, None)
            if units is None:
                continue
            for i, u in enumerate(units):
                if u == target:
                    new_units = list(units)
                    new_units[i] = _replaced(u)
                    new_view = _dc_replace(dep_view, **{sub_name: new_units})
                    gs.write_logic(gs.deployed, new_view,
                                   produced_by='EffectLedgerBridge',
                                   evidence=ev,
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
# 载体(「拷贝仪参与计数进度载体」的实现位):参与计数 =
# 装备效果进度侧栏(:meth:`ActiveEffectInventory.bump_equip_progress`,
# 单调计数器模型 §3);成熟判定 = 计数 ÷ 阈值整除(每 N 场一次,§3 规则 3
# 计算侧);成熟写端 = 入席桥 :func:`spawn_equip_bench_unit`(申报行
# 「成熟回执时点窗口独占」,1★ 自身复制)。**现值观察面**:参与事实由
# 当前观察态现读(战斗结算时点的前台+后台已登记单位 = 参战者;备战席未
# 上场不参战),不建独立参战事实字段。生产插入位置 = 战斗结算覆盖带(接入调用
# 归覆盖批;接入调用前零调用零行为差)。随机分支(「任意方式获得装备者时 30%
# 概率获得复制」)与伤害增幅分支 = 零建模/观察收尾,不在本载体——申报面 =
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
    """拷贝仪成熟入席结果(留存证据/测试用;零决策消费)。"""

    equip: str       # 装备名(COPY_MACHINE_MATURE_BATTLES 键)
    wearer: str      # 装备者 char_id(复制母本)
    count: int       # 成熟时点的参与计数(阈值整倍数)
    placed: bool     # 是否成功入席;False = 席满/席未观察(成熟已消费——
                     # 参与计数是事实推进,不因落位失败回退,单调不重置)


def settle_copy_machine_participation(gs: GameState, *,
                                      frame: str = '') -> list[CopyMachineSpawn]:
    """拷贝仪参与计数载体·战斗参与结算:扫描**现值观察面**(前台+后台
    已登记单位)上的拷贝仪穿戴者,逐件推进参与计数;计数整除阈值 = 成熟,
    成熟即经入席桥落一个穿戴者 1★ 复制进备战席。返回成熟结果列表
    (零成熟返回空表)。

    - 参战者口径 = 前台 + 后台(上场单位站两排、两排皆参战,§3.2.7);
      备战席单位未上场不计;行字段从未观察(None)= 该排无参战读数,
      跳过不猜;
    - 进度键 = (装备名,装备者 char_id):跨排移动计数随键延续(单调,
      §3 永不重置);同名装备多件同主合并计数(实例区分无观察基准,合并
      = 成熟放慢的少发向,不多发——多发会造 phantom 单位刷缺陷台账);
    - 成熟落位失败(席满/席未观察)不回退计数——该次成熟已消费,落位
      真值由下一观察帧给出(报告 placed=False 留存证据);
    - 同拍多穿戴者逐件独立结算(入席桥逐次写,先后落不同空槽)。
    """
    matured: list[CopyMachineSpawn] = []
    for equip_name, threshold in COPY_MACHINE_MATURE_BATTLES.items():
        wearers: list[str] = []
        from sr_od.application.currency_war.kernel.cw_game_state import (
            deployed_rows_of,
        )
        for units in deployed_rows_of(gs):
            for u in units:
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
# (送角色入账分支建模为装备数据行的获得后果——
# 获得分身墨镜/分身墨镜Max/数据拷贝仪Max 时,赠送的银狼族单位直接进备战
# 席,效果与商店购买完全一致(可触发合成/升星)。后果应用函数 = 全渠道
# 装备入栏的统一后置钩子:确定性通道(获得时件名已知)随 write_logic 入栏
# 同链应用;随机通道(骇客改件采样链)在链内应用、随链 write_logic_rand。
# 登记面 = cw_affix_effects.EQUIP_WRITE_SIDES(分身墨镜系两行
# bridge:apply_equip_acquire_consequence;数据拷贝仪Max 行保持
# spawn_equip_bench_unit 覆盖计数的分支,其获得后果由本函数按数据行统一覆盖,
# 不经登记表双登记)。星级按卡文定案[口述·权威 2026-09-18]:
# 分身墨镜→1星银狼 / 分身墨镜Max→2星银狼 / 数据拷贝仪Max→1星银狼LV.999。)

#: 获得后果表(件名 → (送出单位名,星级);表外件 = 无获得后果声明,
#: 后果函数零写零行为——好运令牌等非专属渠道同基准零差)。
#: 协作注(tool-gain-report):冶金炉变异面不走获得链,但采样命中本表
#: 键集 → 上报侧落 ``furnace_mutate_consequence_candidate`` 留存证据行,
#: 供实机局判读比对「变异产物是否触发后果」——推翻「变异不触发」即把
#: 炉变异产物升格 ``on_equipment_gained``。
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
                        orig_view: BenchView | None = None,
                        merge_facts_out: list[tuple[str, int]] | None = None
                        ) -> int:
    """合成级联写(设计 §2.0/§2.1③ 共用消费体;调用方持工作列表副本)
    ——全员 merge_simulate 正常推演(与普通单位同语义;费用档不同时
    存在定案,分组键 (char_id, star) 无跨档歧义)。

    P1 状态容器原生形状:``work_bench`` = list[BenchSlot | None](工作槽表)/
    ``work_dep`` = list[Unit | None](定长 10 下标工作表,§2.3;窗口期桥,视图同源派生);逐级合并后受影响域各落一行
    (:meth:`cw_merge_simulate._merge_bench` on_step 范式;行域载体在场上 =
    bench + deployed 两行——deployed 单字段视图整值替换,合一写):
    rand=False 走 write_logic(确定面),rand=True 走 write_logic_rand
    (采样链内);
    - ``orig_view`` = bench 原观察帧(容量随原观察;None = 默认容量);
    - ``merge_facts_out`` = 升星事实采集出参(每完成一级合并追加
      ``(角色名, 新星级)``,与合并升星触发发放采集共用;None = 现行为,
      既有调用方零改动);
    - 返回落行数(测试/留存证据用)。
    """
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
            from sr_od.application.currency_war.kernel.cw_game_state import (
                deployed_view_of_indexed,
            )
            write(gs.deployed,
                  deployed_view_of_indexed(work_dep, gs.deployed.value),
                  produced_by=producer, evidence=ev, sig=sig)
            last_ds = ds
            rows += 1

    def on_merge(cid: str, new_star: int) -> None:
        # 升星事实采集(合并升星触发发放;纯追加,与步写无顺序耦合)
        if merge_facts_out is not None:
            merge_facts_out.append((cid, new_star))

    _merge_bench(work_bench, work_dep, on_step=on_step, on_merge=on_merge,
                 gs=gs)
    return rows


@dataclass(frozen=True)
class BenchGrantResult:
    """单位入席+级联应用结果(留存证据/测试用;零决策消费)。"""

    placed: bool     # 是否成功落位(False = 席满/席未观察零写)
    merge_steps: int  # 级联合并级数(拒落路径恒 0)
    detail: str = ''  # 拒落因:'' / 'bench_unobserved' / 'bench_full'


def grant_bench_unit_cascade(gs: GameState, name: str, star: int, *,
                             rand: bool = False, evidence: str = 'bench_grant',
                             producer: str = 'EffectLedgerBridge',
                             sig: ChannelSig | None = None) -> BenchGrantResult:
    """单位入席+合成级联共用核心(获得后果/投资效果函数单一实现体)。

    单位落备战席首空槽(bench_place,状态容器原生 BenchSlot 直落)→
    :func:`merge_cascade_write` 级联(全员正常推演)→ 逐步各落一行 →
    合并升星触发发放收尾(级联采集到的升星事实交给
    ``cw_env_grants.check_env_merge_grants`` 检查发放,best-effort:触发
    分支异常 log 不阻塞入席主链,沿 buy_card on_buy 回调分支同纪律)。
    P1 状态容器原生:工作副本 = BenchView 槽序 + 行域下标派生表(§2.1);
    占位件槽位 kind 随工作表原样保留(零换形降级)。
    ``rand`` = 写通道(False = write_logic 确定面 / True =
    write_logic_rand 采样链);``sig`` 缺省 = 装备桥 logic_hook 签名,
    动作报告上下文传入动作 sig 使链行同组。bench 未观察/席满 → 零写
    拒落(落位真值由观察给出,拒落路径无级联无事实零发火)。
    """
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_place,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
        Unit,
        bench_view_of_working,
        deployed_indexed_of_view,
    )
    orig_view = gs.bench.value
    if orig_view is None:
        return BenchGrantResult(placed=False, merge_steps=0,
                                detail='bench_unobserved')
    work_bench = list(orig_view.slots)
    work_dep = deployed_indexed_of_view(gs.deployed.value)
    if bench_place(work_bench, BenchSlot(
            kind='unit', unit=Unit(char_id=name, star=star))) is None:
        return BenchGrantResult(placed=False, merge_steps=0,
                                detail='bench_full')
    write = gs.write_logic_rand if rand else gs.write_logic
    _sig = sig if sig is not None else _equip_bridge_sig(gs)
    write(gs.bench, bench_view_of_working(work_bench, orig_view),
          produced_by=producer, evidence=evidence, sig=_sig)
    merge_facts: list[tuple[str, int]] = []
    steps = merge_cascade_write(gs, work_bench, work_dep, rand=rand,
                                evidence=evidence, producer=producer,
                                sig=_sig, orig_view=orig_view,
                                merge_facts_out=merge_facts)
    if merge_facts:
        # 合并升星触发发放(级联写毕后发火,gs 一致;触发分支 best-effort
        # 不阻塞入席主链)。kernel 反向模块级零 import 契约:函数内惰性取。
        try:
            from sr_od.application.currency_war.kernel.cw_env_grants import (
                check_env_merge_grants,
            )
            check_env_merge_grants(gs, tuple(merge_facts), sig=_sig)
        except Exception as e:  # noqa: BLE001  触发分支失败不阻塞(留 log)
            log.warning('[cw-effect] 合并升星触发发放分支失败(不阻塞):'
                        f'{merge_facts} {e}')
        # 策略卡合成触发发放条目(「合成2星2费角色时获得砂金」族,注册表 =
        # STRATEGY_MERGE_GRANTS):事件源 = 既有 merge_facts 采集复用,
        # 判据 = 产物星级+费用双匹配。函数内自门 sim 装配(live 零写);
        # 与上方条目独立 try 互不短路。best-effort:发放分支异常不阻塞入席
        # 主链(上方条目同纪律)。
        try:
            from sr_od.application.currency_war.kernel.cw_gain_chain import (
                check_strategy_merge_grants,
            )
            check_strategy_merge_grants(gs, tuple(merge_facts), sig=_sig)
        except Exception as e:  # noqa: BLE001  触发分支失败不阻塞(留 log)
            log.warning('[cw-effect] 策略卡合成发放分支失败(不阻塞):'
                        f'{merge_facts} {e}')
    # —— 条件形态专家触发分支(「首次获得 X 时,顾问入商店」族,首例 =
    #    特邀专家:银狼,设计 = 迭代 2026-09-23-invest-effects-calc T-42
    #    §2.3):入席 + merge_cascade_write 级联 + 触发发放分支全毕后判据
    #    一次(「全毕后触发」与购买链同款时序;装备获得后果确定性通道
    #    数据拷贝仪Max 送银狼LV.999 由此承接)。rand 透传(采样链内获得
    #    与本写同窗);状态写沿主链零吞错——与上方触发发放分支 best-effort
    #    分层(发放可弃,状态写不可静默失败)。拒落路径(bench 未观察/
    #    席满)上方早退不可达本段。kernel 反向模块级零 import 契约:
    #    函数内惰性取(cw_gain_chain 模块级 import 本模块,反向取须惰性;
    #    spawn_equip_bench_unit 真类惰性取同款纪律)。
    from sr_od.application.currency_war.kernel.cw_gain_chain import (
        expert_conditional_trigger,
    )
    expert_conditional_trigger(gs, name, rand=rand, sig=_sig,
                               evidence=evidence)
    return BenchGrantResult(placed=True, merge_steps=steps)


@dataclass(frozen=True)
class EquipAcquireReport:
    """获得后果应用结果(留存证据/测试用;零决策消费)。"""

    item: str        # 入栏装备名(调用侧传入)
    granted: str     # 送出单位名('' = 表外件无后果声明)
    star: int        # 送出单位星级(表外件 0)
    merge_steps: int  # 级联合并级数(拒落路径恒 0)
    performed: bool  # 是否发生字段写(授予分支或级联行;False = 表外件/
                     # 席满/席未观察零写)
    detail: str = ''


def apply_equip_acquire_consequence(gs: GameState, item: str, *,
                                    frame: str = '', rand: bool = False,
                                    sig: ChannelSig | None = None) -> EquipAcquireReport:
    """桥·装备获得后果应用(全渠道统一后置钩子;design §2.2)。

    件名查 :data:`EQUIP_ACQUIRE_CONSEQUENCES`:命中 → 送出单位经
    :func:`grant_bench_unit_cascade` 入席+级联(正常推演);表外件 →
    零写零行为(非专属渠道同基准零差,含好运令牌
    grant_equip_item 渠道)。

    - ``rand`` = 调用通道:False = 确定性入栏通道(write_logic,同源);
      True = 随机采样链内(write_logic_rand,观察覆盖差异 = 预期内);
    - ``sig`` = 写入签名(缺省 = 装备桥 logic_hook 签名;动作报告上下文
      传入动作 sig 使链行同组);
    - 装备入栏(equips 追加)不在本函数覆盖——入栏写端归各渠道宿主,本
      函数只覆盖「获得即送」的后果分支。
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


# ===== 打捞人才库族:进入补给阶段时点检查(策略域状态副本发放首例)=====
# 卡面(id 100701,官方原文 cw_invest_data.PLAZA_AUGMENTS):「每次进入
# 补给阶段后，随机获得一个未被选择的角色及其携带的装备。」——发放域 =
# 补给未选列(状态副本既有列,SupplyOption 具名结构,非注册表池)。触发语义
# 按 R-entry 读法建模(披露键 strategy_salvage_trigger_entry_reading):
# 进入补给阶段 N+1 后的首个成功观察帧消费阶段 N 选定时刻的未选列快照;
# 局内首个补给阶段无源零发。通道构型 = 检查函数 + 单点接入调用覆盖实机和模拟器两边
# (环境域刷新触发发放同构先例):唯一插入位置 = 观察上报
# report_screen_supply_node_obs 函数体尾部(live 补给 op 直调 / sim
# 呈现与刷新 / sim op 观察改道链全过本口),读缺帧早退在插入位置之前 =
# 刻意不发放(无画面证据帧不发放,实际触发时点 = 首个成功观察帧)。
# sim 面 fail-closed 零发放:未选集场字段写端 = live 补给 op 真选分支
# (限机械执行态),sim 局不种本域(sim 补给 char 面未建模 = 同一上游
# 缺口族,真值对齐归 sim 补给真值专项)→ 本函数第 2 门恒早退,零发放
# 零接入调用(披露键 strategy_salvage_sim_failclosed_decision_leg)。

#: 持卡判定名单集(集合任一成员 ∈ active_strategies 即持卡,精确名单
#: 匹配):基础卡「打捞人才库」(id 100701)+ 展开卡「打捞人才库+」
#:(id 100702,主条目同模式,+卡成员 = T-95 批接入调用)。集合语义天然防同持
#: 双发(命中即发放一次,非逐名发放)。
_SALVAGE_STRATEGY_NAMES: tuple[str, ...] = ('打捞人才库', '打捞人才库+')

#: 未选列抽样的采样分支具名键(解析口 = cw_action_report
#: .action_sampling_rng,注入槽优先缺省回退自掷;先例 =
#: ENV_MERGE_GRANT_RNG_TOOL 同形态)。禁为 sim 装配本流键:sim 局恒在
#: 第 2 门早退,流键只服务 live 与测试(无谓消耗 sim 采样序列引漂移)。
STRATEGY_SALVAGE_RNG_TOOL: str = 'strategy_salvage'

#: 发放列角色入席星级先验(获取面单位恒 1★,升星仅经合成;与补给选定
#: 上报 pick_supply._SUPPLY_GRANT_STAR 同款先验。发放条目整体 rand=True
#: 随机态,先验错 = 观察覆盖纠偏不响灯,披露键 strategy_salvage_star_prior)。
_SALVAGE_GRANT_STAR: int = 1

#: 建模假设档披露键(静态常量已登记,无运行时 setdefault 动作;同区先例 =
#: HACKER_MOD/ORE/ENV_RANDOM_CHAR_GRANT 等 ASSUMPTION_KEYS 常量族):
#: - trigger_entry_reading:触发语义按 R-entry 读法(卡面「进入…后」措辞
#:   + 全都要·银同域显式「选择后」的官方文本对照);裁 R-choice 则改值/
#:   退役;实采判据 = 持卡局选定后至下一阶段进入前 bench 是否已多出单位。
#: - uniform_over_unchosen:「随机」分布未标,未选列均匀 v0 采样先验
#:   例外;校准源 = logic_rand_outcome 行按随机写 evidence 前缀
#:   ``strategy_salvage:`` / ``strategy_salvage_equip:`` 归组。
#: - star_prior:发放列角色星级卡面未标 → 1★ 先验(rand=True 下先验错
#:   不响灯)。
#: - sim_failclosed_decision_leg:sim 局未选集恒 None → 检查恒第 2 门
#:   早退零发放;sim 补给 char 面未建模为同一上游缺口族。
STRATEGY_SALVAGE_ASSUMPTION_KEYS: tuple[str, ...] = (
    'strategy_salvage_trigger_entry_reading',
    'strategy_salvage_uniform_over_unchosen',
    'strategy_salvage_star_prior',
    'strategy_salvage_sim_failclosed_decision_leg',
)


def check_strategy_supply_salvage(gs: GameState, sig: ChannelSig) -> None:
    """打捞人才库族·进入补给阶段时点检查(发放被掷未选列,消费即清)。

    门序(顺序即短路序,前门不过后门不触):

    1. **持卡判定**:名单集(:data:`_SALVAGE_STRATEGY_NAMES`)任一成员
       ∈ ``gs.active_strategies`` 现值 → 过,否则零写早退。直查状态容器
       不消费效果账本条目(登记与消费分离现役形态);
    2. ``gs.unchosen_supply.value`` 空/None → 零写早退(None = 无未选定
       案:未记录/已消费/兜底轮;sim 局恒此门早退 = fail-closed 零发放);
    3. **均匀掷 1 列**:未选列上均匀 v0(「随机」分布未标,采样先验例外;
       披露键 strategy_salvage_uniform_over_unchosen)。rng =
       ``action_sampling_rng(STRATEGY_SALVAGE_RNG_TOOL, None)`` 函数内
       解析——注入槽优先,缺省回退自掷 = live 猜测口径;
    4. **发放被掷列**,原语与补给选定上报(report_action_pick_supply_param)
       同构:char 非空 → :func:`grant_bench_unit_cascade`(rand=True
       随机态——掷骰是对游戏 RNG 的猜测,下一备战帧 bench/equips 整表
       观察覆盖差异自动纠偏;producer 显式传观察上报同写端归属值,防
       缺省归因混淆;席满/席未观察 = 原语现役拒落零写
       detail='bench_full'/'bench_unobserved',角色条目拒落不阻断装备条目,
       单级合成级联保留);装备条目 = 未选列名保持 OCR 原文(归一仅发生于
       被选列选定窗),逐件先 :func:`normalize_registry_equip_name`
       归一(两段式):命中 → ``owned += 规范名``(write_logic_rand
       随机态)+ :func:`apply_equip_acquire_consequence`(获得即后果,
       rand=True);归一失败('')件逐件禁猜 → equips 值不变翻来源 +
       缺陷留证 fail-closed(错名不入账,观察覆盖自愈),已解析件照常
       入账;char-only 列(char 非空 ∧ 装备名全空)= 合法形态,仅角色
       条目零装备写零缺陷(补给选定上报零装备名分支同构——件名全失读
       子况的失配仍由 equips 观察整表覆盖暴露);
    5. **消费即清**:``gs.unchosen_supply`` 写回 None(逻辑态)——同
       阶段观察上报多次(刷新重进重读)第 2 次起字段已清零发,重入幂等。

    ``sig`` = 全部写共用渠道签名,必须 logic_action / logic_hook 族
    (唯一插入位置传入观察上报内部的 logic_action 签名,天然满足)。
    效果串落点 = 随机写 evidence 串本身(char 条目
    ``strategy_salvage:<名>@<star>star`` / 装备条目
    ``strategy_salvage_equip:<件>``)——本函数不在获得链、无
    GainOutcome.effects 载体,logic_rand_outcome 行归组键 = 原随机写
    evidence(状态容器 logic_evidence 携带)。
    """
    strategies = gs.active_strategies.value or []
    if not any(name in strategies for name in _SALVAGE_STRATEGY_NAMES):
        return
    unchosen = gs.unchosen_supply.value
    if not unchosen:
        return
    # kernel 反向模块级零 import 契约:action_sampling_rng 住上报函数族
    # 包,函数内惰性取(单向破环先例 = 环境合并触发发放)。
    from sr_od.application.currency_war.kernel.cw_action_report import (
        action_sampling_rng,
    )
    from sr_od.application.currency_war.kernel.cw_events import (
        normalize_registry_equip_name,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        _emit_defect,
    )
    roll_rng = action_sampling_rng(STRATEGY_SALVAGE_RNG_TOOL, None)
    col = roll_rng.choice(unchosen)
    if col.char:
        grant_bench_unit_cascade(
            gs, col.char, _SALVAGE_GRANT_STAR, rand=True,
            evidence=(f'strategy_salvage:{col.char}'
                      f'@{_SALVAGE_GRANT_STAR}star'),
            producer='CwScreenSupplyNode', sig=sig)
    equip_texts = (col.equip, *col.extra_equips)
    if not any(equip_texts):
        # 零装备名分支(char-only 列 / 件名全失读,两形态读链不可分):
        # 装备域零写零缺陷(补给选定上报同构;失配由 equips 观察整表
        # 覆盖下一帧暴露,fail-visible)。直接跳到消费即清。
        pass
    else:
        for text in equip_texts:
            norm = normalize_registry_equip_name(text) if text else ''
            if norm:
                # 装备入账:owned += 规范名(账面恒标准名;单一源 =
                # gs.equips 现读-改写-回写)+ 获得后果链(获得即送,
                # 随机态通道与主链一致)。
                owned = list(gs.equips.value or [])
                owned.append(norm)
                gs.write_logic_rand(
                    gs.equips, owned, produced_by='CwScreenSupplyNode',
                    evidence=f'strategy_salvage_equip:{norm}', sig=sig)
                apply_equip_acquire_consequence(gs, norm,
                                                frame='strategy_salvage',
                                                rand=True, sig=sig)
            else:
                # 装备名未解析:禁猜,equips 值不变翻来源 + 留证
                # fail-closed(分层归一多/零命中 = 件名不可辨,错名不入
                # 账由观察覆盖自愈;未选列不经选定窗验证,归一失败率
                # 天然高于被选列)。
                if gs.equips.value is not None:
                    gs.write_logic_rand(
                        gs.equips, gs.equips.value,
                        produced_by='CwScreenSupplyNode',
                        evidence='strategy_salvage_name_unresolved',
                        sig=sig)
                _emit_defect(field_name='equips',
                             expected='strategy_salvage_equip_name',
                             actual='unresolved',
                             evidence='strategy_salvage_landing',
                             sig=sig, kind='strategy_salvage_name_unresolved')
    gs.write_logic(gs.unchosen_supply, None,
                   produced_by='CwScreenSupplyNode',
                   evidence='strategy_salvage_consumed', sig=sig)


# ===== 全都要族:补给选定时点检查(R-choice 插入位置;族模式卡 = 全都要·银)=====
# 族卡面(官方原文 cw_invest_data.PLAZA_AUGMENTS,姊妹卡同构唯配额差异):
# 银(id 131001)「本局游戏中，补给阶段的可选项减少2个。下1个补给阶段选择
# 后，额外获得所有未选择的角色及装备。」/ 金(id 203501)「……下2个补给
# 阶段选择后……」/ 彩(id 331701)「……补给阶段选择后……」——「下 N 个」
# N = 配额格数(银 1/金 2;彩卡面无限定词 = recurring 每次选择后无配额
# 域),单一源 =
# :data:`_TAKE_ALL_SUPPLY_QUOTA`)。各卡两句两条效果条目分治,登记载体 = 每卡两条
# EffectSpec(cw_investments.STRATEGY_EFFECTS:canon 键归发放条目,申报键
# ``'<规范名>#supply_delta'`` 归列数修饰条目,申报键约定权威版本 = 该表全都要·银
# 条目注释):
# - 条目1(列数修饰 -2)= :attr:`BattlefieldEffect.supply_option_delta` 声明
#   载体,live 读链按实屏识别列数跟随(补给 op 模块头「列数以
#   read_supply_options 实际识别为准,禁写死」已登记),零消费插入位置;sim 列数面
#   零建模(M18 简化域上游缺口,真值对齐归 sim 补给真值专项,打捞族裁决同型)。
# - 条目2(配额 N 逐事件全捞)= 本检查函数。插入位置 = 补给选定上报
#   report_action_pick_supply_param 三个 applied 出口前(R-choice 时点——
#   卡面「下 N 个……选择后」字面自证;与打捞人才库 R-entry 插入位置分立,两卡
#   触发面读法各有字面依据互不冲突:打捞 = 进入时点,本族 = 选定后时点,官方
#   文本对照已在打捞条目注册注释背书)。
# 配额消耗制 = **事件消耗制**:每个 applied 选择事件耗 1 格(含内容全未知
# 兜底轮——兜底轮是游戏侧真实选择,配额随之消耗;模型无源零发放,漏记列由
# 下一备战帧观察覆盖入账 fail-visible,与打捞兜底轮同族口径)。备选「可记录
# 消耗制」(仅源可记录才耗)会让兜底顺延后的次轮补发成游戏未发生的幻影写,
# 被已登记禁猜硬裁定压住不采(保守支申报 = STRATEGY_EFFECTS 条目2 条目
# pending notes)。
# 配额封账 = ``strategy_conditional_done`` 共域计数一次性标志位(键 =
# ``take_all#<卡名>#<已耗事件序>``,每耗 1 格追加一键;键形先例 =
# first_buy_xp#<费用> 费用桶复合键,域单调追加契约保持——判定只数前缀,
# 不依赖序号取值)。**禁布尔形(键存在 = 已耗)与计数形并存同域**:配额 >1
# 时布尔判定把部分耗尽(已耗 1 格、尚剩格)误判耗尽 = 静默漏发,族内统一
# 计数形;全都要·彩(id 331701,recurring 每次选择后)= None 配额卡——
# recurring 无配额域,恒放行零闩格零 done 键(封账制只对 int 配额卡存在)。
# 双持(银+金)= 同一选择事件两卡各耗各的 1 格、各发各的
# 未选列(发放域内容同源,重复发放 = 卡面叠加语义零判重闸,姊妹双持族先例)。
# 与打捞人才库族共存边界(共享场字段 ``unchosen_supply`` 双消费者):本族
# R-choice 先消费清空 → 打捞条目下一补给进入 R-entry 后到早退零写——两卡同持
# 时打捞条目饿死 = desc 未写明的交互域,由 rand=True 猜测写 + 观察覆盖承接。
# 条目1 压缩本条目发放域:选择拍在屏列已被 −2,未选域常态 ≤1 列、实测下限局
# 0 列空转(发放域规模随条目1 联动,族级注记)。

#: 族一次性标志位键前缀(strategy_conditional_done 域内本族键空间,与纯卡名键 /
#: first_buy_xp# 复合键空间互不相交):完整键 = ``<前缀><卡名>#<已耗序号>``。
_TAKE_ALL_LATCH_PREFIX: str = 'take_all#'

#: 持卡判定与配额单一源(值形 map 泛化,先例 = 打捞族名单集 tuple 同位):
#: 键 = 卡规范名,值两形——int = 卡面「下 N 个补给阶段选择后」的配额格数
#:(全都要·银 id 131001 = 1、全都要·金 id 203501 = 2),None = 无界(卡面
#: 无「下 N 个」限定词 = recurring 每次选择后,无配额域,恒放行零闩格;
#: 防「未配置」误读——None 是显式无界非缺省)。全都要·彩(id 331701)=
#: None。判定与配额读取合一防两抄本
#: 漂移;不并入打捞集——发放语义异构(全列逐事件 vs 随机单列 recurring),
#: 合并 = 名单集语义耦合(独立双函数)。map 键集与 STRATEGY_EFFECTS name
#: 集的一致性锁 = 测试仓表域锁(防写表人笔误形,不入 import 校验——治理
#: 口径先例 = 打捞族)。
_TAKE_ALL_SUPPLY_QUOTA: dict[str, int | None] = {
    '全都要·银': 1, '全都要·金': 2, '全都要·彩': None,
}

#: 发放列角色入席星级先验(获取面单位恒 1★,升星仅经合成;与
#: :data:`_SALVAGE_GRANT_STAR` 同款先验。发放条目整体 rand=True 随机态,
#: 先验错 = 观察覆盖纠偏不响灯)。
_TAKE_ALL_GRANT_STAR: int = 1

#: 建模假设档披露键(静态常量已登记,无运行时 setdefault 动作;先例 =
#: :data:`STRATEGY_SALVAGE_ASSUMPTION_KEYS` 同形):
#: - unchosen_diamond_pending:未选钻列的钻本体归属 desc 未写明(「角色及
#:   装备」无「钻」字;选定列的钻走 sim ``_on_supply_picked`` 派生,未选列
#:   无对应机制文)→ 零建模,列内装备随列发放;实采判据 = 持卡局让钻列
#:   留选,对照 diamond_count 轨迹。
#: - sim_failclosed_decision_leg:sim 局决策条目未接 → 未选集恒 None →
#:   发放侧恒零发放(事件消耗一次性标志位 int 配额卡照设 = 一笔无害簿记写,
#:   彩 None 配额卡零闩格;承打捞族同族语义,
#:   独立键因函数/名单集分立)。
STRATEGY_TAKE_ALL_ASSUMPTION_KEYS: tuple[str, ...] = (
    'strategy_take_all_unchosen_diamond_pending',
    'strategy_take_all_sim_failclosed_decision_leg',
)


def check_strategy_take_all_supply(gs: GameState, sig: ChannelSig) -> None:
    """全都要族·补给选定时点检查(事件消耗制:每事件耗 1 格,发放即清)。

    门序(顺序即短路序,前门不过后门不触):

    1. **持卡判定**:配额 map(:data:`_TAKE_ALL_SUPPLY_QUOTA`)任一键 ∈
       ``gs.active_strategies`` 现值 → 过,否则零写零一次性标志位早退(未持卡
       局全链零变化;直查状态容器不消费效果账本条目,登记与消费分离现役形态);
    2. **配额计数一次性标志位门**:逐持卡数域内 ``take_all#<卡名>#`` 前缀键数 =
       已耗格数,全部 ≥ 各自配额 → 零写早退(配额耗尽后同窗重复出口/
       后续补给选择全静默;耗尽残迹 = done 键簿记留域,审计可考);None
       配额卡(recurring 无配额域)无此门——恒放行无耗尽态;
    3. **事件消耗一次性标志位**:逐未耗尽卡追加 ``take_all#<卡名>#<已耗+1>`` 键
       (write_logic)——事件消耗制在此统一处理:不论源可否记录,每个
       applied 选择事件即耗 1 格(插入位置三个 applied 出口都会到达本函数,
       兜底轮亦然);None 配额卡跳过写入(零闩格零 done 键,recurring 无
       封账面,发放分支照常走);
    4. **源检查**:``gs.unchosen_supply.value`` 空/None → 零发放早退(None =
       无未选定案:未记录/兜底轮;sim 局恒此形态 = fail-closed 零发放);
    5. **全未选列逐卡逐列发放**(每未耗尽卡各发一遍,双持重复发放 = 卡面
       叠加语义零判重闸;「所有」= 零采样,全链无 rng 消费——不接
       action_sampling_rng,sim 采样序列零扰动):char 非空 →
       :func:`grant_bench_unit_cascade`(rand=True 随机态——未选列内容未经
       游戏动作确认,归一仅发生于被选列,读链内容是模型侧读数非游戏确认
       回执;猜测写由下一备战帧 bench/equips 整表观察覆盖差异自动纠偏;
       producer = 'CwScreenSupplyNode' 未选域发放写端家族值,与打捞条目同
       归属防缺省归因混淆;席满/席未观察 = 原语现役拒落零写
       detail='bench_full'/'bench_unobserved',单列拒落不阻断本列装备条目与
       后续列);装备条目 = 逐件 :func:`normalize_registry_equip_name` 归一
       两段式(命中 → ``owned += 规范名`` write_logic_rand +
       :func:`apply_equip_acquire_consequence` rand=True;失败 '' 件禁猜 →
       equips 值不变翻来源 + 缺陷留证 fail-closed,kind=
       ``strategy_take_all_name_unresolved``,已解析件照常入账;char-only
       列 = 合法形态,零装备写零缺陷);
    6. **消费即清**:``gs.unchosen_supply`` 写回 None(逻辑态)——重入幂等。

    效果串落点 = 随机写 evidence 串本身(char 条目
    ``strategy_take_all:<名>@<star>star`` / 装备条目
    ``strategy_take_all_equip:<件>``;logic_rand_outcome 行归组键 = 原随机写
    evidence,状态容器 logic_evidence 携带)。``sig`` = 全部写共用渠道签名
    (logic_action 族,插入位置传入上报内部签名)。
    """
    strategies = gs.active_strategies.value or []
    held = tuple(n for n in _TAKE_ALL_SUPPLY_QUOTA if n in strategies)
    if not held:
        return
    done = tuple(gs.strategy_conditional_done.value or ())
    # 计数形配额一次性标志位门(门 2):前缀键数 = 已耗格数,< 配额放行。布尔形
    # (键存在 = 已耗)会把配额 >1 卡的部分耗尽误判耗尽 = 静默漏发,族内
    # 统一计数形禁两形并存。None 配额卡(recurring 无配额域)不入 spent——
    # due 判定恒真恒放行,无耗尽态。
    spent = {n: sum(1 for k in done
                    if k.startswith(f'{_TAKE_ALL_LATCH_PREFIX}{n}#'))
             for n in held if _TAKE_ALL_SUPPLY_QUOTA[n] is not None}
    due = tuple(n for n in held
                if _TAKE_ALL_SUPPLY_QUOTA[n] is None
                or spent[n] < _TAKE_ALL_SUPPLY_QUOTA[n])
    if not due:
        return
    # 事件消耗一次性标志位(门 3):逐未耗尽卡追加一键,先于发放分支——兜底轮(源不可
    # 记录)也在此封账;序号 = 写入时点「已耗+1」快照(审计可读,判定只数
    # 前缀不依赖序号);evidence 与 char 条目同族前缀(账面归组一致)。
    # None 配额卡跳过(零闩格零 done 键——recurring 无封账面,发放照常)。
    for name in due:
        if _TAKE_ALL_SUPPLY_QUOTA[name] is None:
            continue
        latch = f'{_TAKE_ALL_LATCH_PREFIX}{name}#{spent[name] + 1}'
        gs.write_logic(gs.strategy_conditional_done, done + (latch,),
                       produced_by='CwScreenSupplyNode',
                       evidence=f'strategy_take_all:{name}', sig=sig)
        done = done + (latch,)
    unchosen = gs.unchosen_supply.value
    if not unchosen:
        return
    # kernel 反向模块级零 import 契约:函数内惰性取(打捞条目同款先例)。
    from sr_od.application.currency_war.kernel.cw_events import (
        normalize_registry_equip_name,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        _emit_defect,
    )
    # 门 5 逐卡逐列发放:多卡同持各发各的(银+金+彩),内容同源重复 = 卡面叠加语义。
    for _name in due:
        for col in unchosen:
            if col.char:
                grant_bench_unit_cascade(
                    gs, col.char, _TAKE_ALL_GRANT_STAR, rand=True,
                    evidence=(f'strategy_take_all:{col.char}'
                              f'@{_TAKE_ALL_GRANT_STAR}star'),
                    producer='CwScreenSupplyNode', sig=sig)
            equip_texts = (col.equip, *col.extra_equips)
            if not any(equip_texts):
                # 零装备名分支(char-only 列 / 件名全失读,两形态读链不可分):
                # 装备域零写零缺陷,失配由 equips 观察整表覆盖暴露(打捞条目同构)。
                continue
            for text in equip_texts:
                norm = normalize_registry_equip_name(text) if text else ''
                if norm:
                    # 装备入账:owned += 规范名(单一源 = gs.equips 现读-改写-
                    # 回写)+ 获得后果链(获得即送,随机态通道与主链一致)。
                    owned = list(gs.equips.value or [])
                    owned.append(norm)
                    gs.write_logic_rand(
                        gs.equips, owned, produced_by='CwScreenSupplyNode',
                        evidence=f'strategy_take_all_equip:{norm}', sig=sig)
                    apply_equip_acquire_consequence(gs, norm,
                                                    frame='strategy_take_all',
                                                    rand=True, sig=sig)
                else:
                    # 装备名未解析:禁猜,equips 值不变翻来源 + 留证
                    # fail-closed(未选列不经选定窗验证,归一失败率天然高于
                    # 被选列;错名不入账由观察覆盖自愈)。
                    if gs.equips.value is not None:
                        gs.write_logic_rand(
                            gs.equips, gs.equips.value,
                            produced_by='CwScreenSupplyNode',
                            evidence='strategy_take_all_name_unresolved',
                            sig=sig)
                    _emit_defect(field_name='equips',
                                 expected='strategy_take_all_equip_name',
                                 actual='unresolved',
                                 evidence='strategy_take_all_landing',
                                 sig=sig,
                                 kind='strategy_take_all_name_unresolved')
    gs.write_logic(gs.unchosen_supply, None,
                   produced_by='CwScreenSupplyNode',
                   evidence='strategy_take_all_consumed', sig=sig)


# ===== 合成事件发放条目:穿戴 applied 出口检查(策略源 ON_MERGE 首接入调用)=====
# 卡面(官方原文 cw_invest_data.PLAZA_AUGMENTS):「合成装备时，获得2次
# 刷新。」——插入位置 = 穿戴上报函数 report_action_wear_equip_param applied
# 出口(穿着即合成规则住上报 = kernel 单一源,live 动作 op 与 sim 动作
# 注入同口,单点覆盖实机和模拟器两边);合成次数 = 输入件数−输出件数(插入位置现算,
# 三拒绝分支 applied=False 早退恒不达 = 零发放天然成立)。装备栏内主动
# 合成 bot 零执行零辖域(未来接入调用须接同款发放检查并申报);角色升星域
# 显式排除——ON_MERGE 词表语义 = 合成时,装备合成与角色升星两事件域按
# 插入位置分开计数,本条目只认装备合成(fields.md §5.3 禁混账)。

#: 发放条目持卡判定名单集(账本条目名精确匹配;先例 =
#: :data:`_SALVAGE_STRATEGY_NAMES` 同形):现役成员 = 武力刷新
#:(id 101801),装备合成触发经济卡现役仅此一张。名单钉卡而非
#: trigger/category 字段匹配:事件域零歧义(同触发面的词缀源条目
#: 变宝为废是 BATTLEFIELD 载体,不在名单天然隔离);后继同触发经济卡
#: 随其建模批入名单并复用同一检查。
_ON_MERGE_REFRESH_STRATEGY_NAMES: tuple[str, ...] = ('武力刷新',)

#: 建模假设档披露键(静态常量已登记,无运行时 setdefault 动作;先例 =
#: STRATEGY_SALVAGE_ASSUMPTION_KEYS 同形)。登记两件实机未证事实:
#: - live_timing_and_value:实机「合成装备时 +2 刷新」的到账时点与数值
#:   真值未实采(逻辑账以本发放条目为准;商店帧观察锚定兜底可校验,漏发
#:   可纠偏但时点漂移);
#: - junked_still_grants:变宝为废垃圾化实际发生时合成事件是否照发
#:   (kernel 按配方命中计数、垃圾化不改计数,两效果同事件独立结算;
#:   实机若判「垃圾化取消合成事件」则改判)。
#: 退役条件 = 实机对局采得合成帧免费刷轨迹(journal ``effects`` +
#: ``free_refresh_left`` 轨迹)定案后回填 verdict 式记录。
STRATEGY_ON_MERGE_LIVE_UNVERIFIED: tuple[str, ...] = (
    'strategy_on_merge_live_timing_and_value',
    'strategy_on_merge_junked_still_grants',
)


def apply_on_merge_refresh_grant(gs: GameState, *, merges: int,
                                 frame: str = '') -> None:
    """合成事件发放条目(策略侧 ON_MERGE 首接入调用;插入位置 = 穿戴上报函数
    applied 出口)。``merges`` = 本次动作内装备合成次数(自然数;插入位置按
    输入件数−输出件数现算)。逐账本 ON_MERGE 经济条目(名单集
    :data:`_ON_MERGE_REFRESH_STRATEGY_NAMES` 精确匹配;登记分支缺位 =
    零命中保守零动作)累计 ``payload.refresh_per_compose × merges``,
    write_logic 累加进 ``gs.free_refresh_left``(三写端之发放登记,
    None 基 = 0 起算,写签名复用 :func:`_equip_bridge_sig` 单一构造点)。
    ``merges <= 0`` 或零命中 = no-op(零 Field 行);payload 无
    refresh_per_compose 字段的条目(未来同触发异载体卡)鸭子缺省 0
    天然零发放。sim 自主局零穿戴 = 零触发(装备域 sim 未建模既有边界,
    不补建模);动作注入与 live 同经穿戴上报函数,状态副本真值同口。"""
    if merges <= 0:
        return
    total = 0
    srcs: list[str] = []
    for e in gs.effects.entries:
        if e.spec.name not in _ON_MERGE_REFRESH_STRATEGY_NAMES:
            continue
        n = int(getattr(e.spec.payload, 'refresh_per_compose', 0) or 0)
        if n > 0:
            total += n * merges
            srcs.append(e.spec.name)
    if total <= 0:
        return
    left = gs.free_refresh_left.value
    gs.write_logic(gs.free_refresh_left,
                   (0 if left is None else int(left)) + total,
                   produced_by=('EffectLedgerBridge:' + '+'.join(srcs))
                   if srcs else 'EffectLedgerBridge',
                   evidence=(f'effect_on_merge@{frame}' if frame
                             else 'effect_on_merge'),
                   sig=_equip_bridge_sig(gs))


# ===== 刷新出对条件金条目:策略源 ON_REFRESH 经济发放首接入调用 =====
# 卡面(官方原文 cw_invest_data.PLAZA_AUGMENTS,id 102901):「刷新商店时，
# 若刷新的角色中出现2个相同的角色，获得1金币。获得4次免费刷新。」——金条目 =
# 刷新事件条件金(插入位置 = 刷新上报函数随机态实现后,手动动作唯一生产点;burst
# 条目归获得链登记分支,本函数零辖)。「刷新商店时」辖域 = 仅手动刷新(刷新触发
# 闭集 = 节点切换 + 手动,docs/game/currency_war/research/economy.md;节点窗
# 自动全刷 = sim deal_shop 另口,不经刷新上报),残余不确定性走披露键实采。
# 仅 sim 装配态执行:sim 采样即状态副本真值、判定成立经观察通道发金;live 采样是
# 猜测,金面禁猜测直写(零写,金真值 = 下一商店入口观察覆盖兜底)。

#: 发金观察笔证据串(判读可辨;刻意不带 ``sim:engine`` 前缀——该前缀语义 =
#: sim 后端状态副本写入分支外部事件写,本条目是 kernel 条件发放非后端事件,形态先例 =
#: cw_env_grants._DIAMOND_EVIDENCE 同款申报)。正规流程下金位在每次刷新动作前
#: 经商店入口观察锚定(source=observation),本笔覆盖不触失配对账;若未来出现
#: 无观察衔接的连续刷新链,本笔与扣费条目 logic 写的窗口内差异会照真走失配
#: 三分流(信号正确:流程跳过了入口观察)。
_REFRESH_PAIR_GOLD_EVIDENCE: str = 'strategy_refresh_pair_gold'

#: 建模假设档披露键(静态常量已登记,无运行时 setdefault 动作;先例 =
#: STRATEGY_CAPACITY_EXPIRY_ASSUMPTION_KEYS 同形)。登记两件实机未证/感知边界
#: 事实:- strategy_refresh_pair_scope_unverified:「刷新商店时」辖域 = 仅手动
#:   刷新为已登记口径推得(触发闭集 + 插入位置架构),节点切换自动全刷是否同触发未
#:   实采——实采法 = 结算对账帧金差 vs 手动刷新帧金差分离,证伪后补 deal_shop
#:   侧同款检查(后继批,不回改本插入位置);- strategy_refresh_pair_live_lag:
#:   live 条件金感知滞后窗——多次刷新出对未重进商店时 gs.gold 读数滞后于游戏
#:   真值,下次商店入口观察锚定收敛(策略账面归兜底再锚定,shop_session
#:   已登记决策;drift 侦测可见,非缺陷)。退役条件 = 实机金轨迹定案辖域后
#:   回填 verdict。
STRATEGY_REFRESH_PAIR_SCOPE_UNVERIFIED: tuple[str, ...] = (
    'strategy_refresh_pair_scope_unverified',
    'strategy_refresh_pair_live_lag',
)


def apply_on_refresh_pair_gold_grant(gs: GameState, payload: ShopPayload, *,
                                     frame: str = '') -> None:
    """刷新出对条件金条目(策略源 ON_REFRESH 经济发放首接入调用;插入位置 =
    刷新上报函数随机态实现之后、仅 sim 装配态调用——live 采样是猜测,
    金面禁猜测直写,live 金真值归观察覆盖兜底)。

    - 判定 = payload 5 槽非空 card 按 name 计数,存在任意名 ≥2 即成立、
      单次刷新至多一笔(卡面「若刷新的角色中出现2个相同的角色，获得1金币」
      条件式单数语义直读;按对数多发 = 无文本依据的编造规则;星级不参与
      判定——同名即同角色,采样面直出恒 1★,异 star 直构形态为语义完备性
      覆盖非现役行为);
    - 逐账本条目过滤 = trigger==ON_REFRESH ∧ category==ECONOMY(双过滤,
      未来同触发经济卡自动入账零名单维护;淘金客 STATE/采购专员
      BATTLEFIELD 天然隔离;payload 无 gold_per_refresh_pair 字段的条目
      鸭子缺省 0 零授予);发金额 = Σ条目 gold_per_refresh_pair;
    - 发金 = ``gs.observe(gs.gold, 现值 + Σ)``,sig 函数内自构 obs 族
      (observe 渠道校验只收 obs 族;本模块零包内模块级 import 契约,
      ChannelSig 惰性取,``cw_env_grants.on_diamond_acquired`` 同口径
      ——sim 状态副本数值面 = 观察通道,禁 logic 写);
    - gold 现值 None → 宁缺勿造跳过(条件逐刷独立,本条目无 done 一次性标志位,下次
      刷新自动重查,重试零成本);
    - 零 rng:判定输入 = 随机态实现已采 payload,本条目不另掷点。
    """
    counts: dict[str, int] = {}
    for slot in payload.cards:
        card = slot.card
        if slot.kind != 'content' or card is None:
            continue
        name = str(card.name or '')
        if not name:
            continue
        counts[name] = counts.get(name, 0) + 1
    if not any(c >= 2 for c in counts.values()):
        return
    total = 0
    for e in gs.effects.entries:
        if e.spec.trigger is not TriggerKind.ON_REFRESH \
                or e.spec.category is not EffectKind.ECONOMY:
            continue
        n = int(getattr(e.spec.payload, 'gold_per_refresh_pair', 0) or 0)
        if n > 0:
            total += n
    if total <= 0:
        return
    g = gs.gold.value
    if g is None:
        return
    from sr_od.application.currency_war.kernel.cw_game_state import ChannelSig
    gs.observe(gs.gold, int(g) + total,
               evidence=(f'{_REFRESH_PAIR_GOLD_EVIDENCE}@{frame}' if frame
                         else _REFRESH_PAIR_GOLD_EVIDENCE),
               sig=ChannelSig(family='obs', actor='StrategyRefreshPairGrant',
                              mode='synthesized',
                              group_id='strategy:refresh-pair-gold'))


# ===== 到期发放条目:tick 到期段首个消费客户端(策略源 N_NODES 到期面)=====
# 卡面(官方原文 cw_invest_data.PLAZA_AUGMENTS,id 101901):「在接下来3个
# 节点只有3个备战席位置。随后，获得3件简易装备。」——容量窗本体 = 效果账本
# 条目(N_NODES×3)+ 容量逻辑态直写桥 project_effect_capacity(插入位置 = 节点
# 边界 tick 尾段);「随后」= 条目到期移除拍,构造性锁步(单一载体:到期列表
# 由 advance_node 返回,条目移除即不可重入,零第二账本/零一次性标志位)。到期装备发放
# 落本条目而非延时队列第二登记:窗口条目本身即载体,双账本同闸锁步的协调成本
# 无收益;金面禁 tick 直写防双计的裁定不辖装备——装备无金面双计风险。

#: 到期发放条目·简易装备池(category='简易' 全集,字母序确定性;池口径随装备
#: 注册表传导)。与晶矿 cw_ore_reward._SIMPLE_EQUIP_POOL 同表达式同口径,
#: 两处独立定义互指不跨模块引私有名(公共化归族级待办;口径漂移由测试侧
#: 同集断言守住;策略侧随机装备条目不走本地池 = equips_by_category 注册表
#: 派生单源)。
_EXPIRY_SIMPLE_EQUIP_POOL: tuple[str, ...] = tuple(sorted(
    name for name, eq in EQUIPMENTS.items() if eq.category == '简易'))

#: 建模假设档披露键(静态常量已登记,无运行时 setdefault 动作;先例 =
#: STRATEGY_SALVAGE_ASSUMPTION_KEYS 同形)。登记三件 desc 未载/未证事实:
#: - capacity_window_node_reading:窗口读法继承 advance_node 现役「后继 N
#:   节点」算术(kernel 全族待实采旗,躺平同旗;证伪改守卫单点时本键改值/
#:   退役);
#: - expiry_grant_simple_pool_uniform:到期 3 件 = 简易池逐件独立均匀 v0、
#:   可重复(desc 未标「随机」;校准源 = logic_rand_outcome 行按
#:   ``strategy_grant_expiry:`` 前缀归组);
#: - bench_capacity_shrink_overflow_unmodeled:进窗占席 >3 的压缩行为未建模
#:   (桥不截断占席 + 留证、读链容量外命中丢弃 + 留证;desc 未写压缩行为,
#:   禁猜,实机命中即缺陷台账 + 缺口登记升级)。
STRATEGY_CAPACITY_EXPIRY_ASSUMPTION_KEYS: tuple[str, ...] = (
    'strategy_capacity_window_node_reading',
    'strategy_expiry_grant_simple_pool_uniform',
    'bench_capacity_shrink_overflow_unmodeled',
)


def apply_effect_expiry_grants(gs: GameState, expired: list[ActiveEffect], *,
                               frame: str = '',
                               rng: random.Random | None = None) -> None:
    """到期发放条目(策略源 N_NODES 到期面首个消费客户端;插入位置 = 节点边界
    tick 到期段 ``_tick_effect_boundary_impl``,整段在 tick_effect_boundary
    的 try/except best-effort 内,条目内异常不毒化派生链)。

    逐到期条目读 ``payload.expiry_simple_equips``(鸭子缺省 0 = 无到期发放,
    同窗异 payload 条目天然零发放),>0 逐件自简易池
    (:data:`_EXPIRY_SIMPLE_EQUIP_POOL`)独立均匀采样,经
    :func:`gain_equipment`(rand=True 随机态通道,继承获得后果链;装备栏
    未观察 = 原语现役拒落零写)入栏;evidence 前缀 ``strategy_grant_expiry:``
    (随机态校准归组面),producer = EffectLedgerBridge(写签名复用
    :func:`_equip_bridge_sig` 单一构造点)。

    一次性由构造保证:到期即从账本移除(advance_node),到期列表每条目至多
    出现一次——无重入面,不设一次性标志位;同卡双持现役选卡排除集下不可达,可达性
    变化时重派逐次授予、现役不设防。

    ``rng`` 注入形参(缺省 None = 函数内缺省 ``random.Random()``):kernel
    tick 无流键注入点,sim 批量该条目不可按 seed 复现(非战斗/非收入面,统计
    影响限装备库存面;披露键 strategy_expiry_grant_simple_pool_uniform);
    注入槽供测试钉样与后续接流键留口。
    """
    # kernel 反向模块级零 import 契约:cw_gain_chain 模块级依赖 cw_game_state
    #(后者 import 本模块),反向模块级即环——函数内惰性取(合成事件条目
    # action_sampling_rng 同款先例)。
    from sr_od.application.currency_war.kernel.cw_gain_chain import (
        gain_equipment,
    )
    if rng is None:
        rng = random.Random()
    for eff in expired:
        n = int(getattr(eff.spec.payload, 'expiry_simple_equips', 0) or 0)
        for _ in range(max(0, n)):
            item = rng.choice(_EXPIRY_SIMPLE_EQUIP_POOL)
            evidence = f'strategy_grant_expiry:{item}'
            if frame:
                evidence = f'{evidence}@{frame}'
            gain_equipment(gs, item, rand=True, sig=_equip_bridge_sig(gs),
                           evidence=evidence, producer='EffectLedgerBridge')
