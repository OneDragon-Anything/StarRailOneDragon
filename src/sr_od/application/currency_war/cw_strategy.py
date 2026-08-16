# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 策略插件机制(CwStrategy ABC + StrategySession + CurrencyWarMatch)。

把货币战争的「决策大脑」抽象成**可替换的 ``CwStrategy`` 对象**(对标 app 插件):
换对象 = 换打法,不动框架。内置具现 ``DefaultCwStrategy``(``strategies/default_strategy.py``)
= 今天打法(薄委托既有模块函数,P1 零行为变化)。

设计见 ``docs/develop/currency_war/strategy/11_strategy_plugin.md``;决策见
``docs/develop/currency_war/decisions/INDEX.md`` 。本模块**纯逻辑**:所有钩子只吃
``GameState``/选项 + 出 ``Action``/``Pick``,**绝不碰屏幕 / ``ctx.controller``**(读屏与点击
是框架职责)→ 策略可离线 unit 测、可 replay。

四个组件(本模块 3 个 + manager):
- ``CwStrategy`` —— ABC,大脑接口(3 生命周期 + 8 决策 + create_session = 12 钩子,全 abstract;
  ``decide_prep_action`` = 备战决策环步级决策,P1 新增,见 doc 15/ADR-0123)。
- ``StrategySession`` —— 每局跨步状态(框架新建 / 局终销毁;策略读写)。
- ``CurrencyWarMatch`` —— 运行时持有 strategy+session 的轻容器,挂 ``ctx.cw_match``。
- ``StrategyManager``(``cw_strategy_manager.py``)—— 约定式文件扫描发现 + 去重 + 实例化。
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from sr_od.application.currency_war.cw_events import (
    EncounterOption,
    EncounterPick,
    MegastarOption,
    MegastarPick,
    PartnerOption,
    PartnerPick,
    SupplyOption,
    SupplyPick,
)
from sr_od.application.currency_war.cw_performance import (
    PerformanceTracker,
    RoundOutcome,
)
from sr_od.application.currency_war.cw_state import (
    Action,
    BenchChar,
    GameState,
    MatchOutcome,
    PickEvent,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
    from sr_od.application.currency_war.cw_comps import Comp


class CwStrategy(ABC):
    """一整套货币战争局内打法(可替换的决策大脑;/§11.3)。

    **无状态策略**:实例**不持有可变的每局状态**,所有跨步状态走 ``StrategySession``(框架每局
    新建、传入每个钩子、局终销毁)。收益:实例可反复 instantiate、可 unit 测(喂构造好的 state)、
    无隐藏实例状态 → 不会跨局泄漏。

    本 ABC 的钩子**全 abstract**(纯接口,ABC 自身不含内置逻辑);内置具现见 ``DefaultCwStrategy``。
    自定义策略两条路:① 继承 ``CwStrategy`` 自己实现全部钩子(完整自研打法);② 继承
    ``DefaultCwStrategy`` 只覆盖关心的几个(其余继承内置,低门槛、比赛友好)。

    **构造无参**(继承默认 ``object.__init__``):策略跨局跨账号复用,**不收 ctx/config** —— 配置每次
    调用按参传入;``StrategyManager`` 经 ``cls()`` 实例化。可变每局状态一律走 ``session``,非实例属性。
    """

    # ===== 元数据(类属性;扫描时读,无 _const.py sidecar —— 策略比应用简单)=====
    STRATEGY_ID: str = ""        # 唯一 id(如 "default"/"aggressive_rush"),去重键;空 = 中间辅助 ABC 不注册
    STRATEGY_NAME: str = ""      # GUI 显示名(如 "内置默认策略")
    AUTHOR: str = ""             # 参赛者/作者
    VERSION: str = "0.1"         # 语义化版本
    DESCRIPTION: str = ""        # 一句话描述打法
    # 扫描器内部:True = 中间辅助 ABC(如 RushBase(DefaultCwStrategy)),不注册;非展示元数据(§11.5)
    _abstract: bool = False

    # ===== 生命周期钩子 =====

    @abstractmethod
    def create_session(self, config: CurrencyWarConfig) -> StrategySession:
        """每局开始(run loop)调一次。返回空白 ``StrategySession``(rng 留默认,由 run loop 按
        ``config.strategy_seed`` 覆盖)。策略可覆盖以注入自己的 session 子类 / 初始 memory。"""

    @abstractmethod
    def on_match_start(self, state: GameState, session: StrategySession,
                       config: CurrencyWarConfig) -> None:
        """每局开始(loop 首次截图后)。初始化跨步状态(如设初始 target 意向)。P1 默认 no-op。"""

    @abstractmethod
    def on_round_end(self, state: GameState, session: StrategySession,
                     config: CurrencyWarConfig, obs: RoundOutcome) -> None:
        """每场战斗后(观测驱动)。默认 ``session.performance.record(obs)``。
        ✅ 已接线(2026-08-07 起):loop._record_round_outcome 每轮胜结算调用。"""

    @abstractmethod
    def on_match_end(self, session: StrategySession, config: CurrencyWarConfig,
                     outcome: MatchOutcome) -> None:
        """每局结束。局终收尾(策略可学习/记日志;比赛评分钩子)。P1 默认 no-op(outcome 桩)。"""

    # ===== 决策钩子 =====

    @abstractmethod
    def update_target(self, state: GameState, session: StrategySession,
                      config: CurrencyWarConfig) -> None:
        """战略层:选/转型 target_comp。框架在每个备战回合 ``decide_prep`` **之前**调一次。
        实现写 ``session.target_comp``(首轮选;其后按信号 pivot;无强信号保持)。"""

    @abstractmethod
    def decide_prep(self, state: GameState, session: StrategySession,
                    config: CurrencyWarConfig) -> list[Action]:
        """备战 shop 计划(买/升/D牌/deploy/卖)。读 ``session.target_comp`` 作战略导向、
        ``session.rng`` 作蒙特卡洛。"""

    @abstractmethod
    def decide_prep_action(self, obs, session: StrategySession,
                           config: CurrencyWarConfig):
        """备战决策环步级决策(doc 15 / ADR-0123,P1 新增):看 ``obs`` 出**一个**动作。

        - ``obs``: ``PrepObservation``(框架观察层产出;P1 ``overlay_state``/``shop_cards`` 恒空)。
        - 返回: 一个 ``PrepAction``(``prep_actions.py``;原子为主,P1 含 Run* 组合过渡)。
          控制流动作(``DeferSpheres``/``BailToOuter``)是框架信号,不走 execute 验证链。
        - 契约: 无状态策略 —— 跨步意图(defer 计数等)走 ``session``;框架保证每步先观察再决策
          (F1),动作合法性由框架校验(F3),验证失败/stall 屏蔽对策略透明(F4)。
        """

    @abstractmethod
    def decide_invest(self, kind: Literal["strategy", "env"], options: list[str],
                      state: GameState, session: StrategySession,
                      config: CurrencyWarConfig) -> PickEvent:
        """投资策略/投资环境 3 选 1(``kind`` 区分;P1 两 kind 走同一默认实现)。``options``=OCR 卡名列表。"""

    @abstractmethod
    def decide_supply(self, options: list[SupplyOption], state: GameState,
                      session: StrategySession, config: CurrencyWarConfig,
                      refresh_used: bool = False) -> SupplyPick:
        """补给选装备/出钻。⚠️ OCR 未就绪(P1 钩子存在 + 默认委托,handler 不 rewire,随阶段5)。"""

    @abstractmethod
    def decide_encounter(self, options: list[EncounterOption], state: GameState,
                         session: StrategySession, config: CurrencyWarConfig,
                         refresh_used: bool = False) -> EncounterPick:
        """遭遇难度选(其一易/其四难 二选一)。✅ 已接 ``HandleEncounter``(L55 调)+ ``cw_events.decide_encounter``
        (非平凡:未成型→低难保生存 / 成型+词缀利→高难拿奖励 / 全克→刷新换批)+ ``read_encounter_options``
        (OCR 卡标题→difficulty)。affix 分支 N/A(选项 UI 不显词缀,战后才显)。原「dormant 无选项UI」过期(2026-08-12 核实)。"""

    @abstractmethod
    def decide_megastar(self, options: list[MegastarOption], state: GameState,
                        session: StrategySession, config: CurrencyWarConfig) -> MegastarPick:
        """巨星选候选。⚠️ OCR 未就绪(P1 钩子存在 + 默认委托,handler 不 rewire,候选 char_id 空 → idx=0)。"""

    @abstractmethod
    def decide_partner(self, options: list[PartnerOption], state: GameState,
                       session: StrategySession, config: CurrencyWarConfig) -> PartnerPick:
        """选择伙伴。⚠️ OCR 未就绪(P1 钩子存在 + 默认委托,handler 不 rewire,char_id 空 → idx=0)。"""


@dataclass
class StrategySession:
    """一局货币战争的跨步状态(框架每局新建,局终销毁;策略读写;/§11.4)。

    策略实例无状态,所有可变每局状态放这。``rng`` 可种子化(公平/replay);``performance`` 是观测
    反馈(掉血/胜负);``memory`` 是策略私有 scratch(连胜计数/「这轮攒金升8」意图等 escape hatch)。
    """
    target_comp: Comp | None = None        # 战略层目标阵容(update_target 维护)
    # 最近一次备战 read_game_state 快照(board/deployed/bench;BuyShopCards 每回合写)。给**节点 overlay
    # handler**(遭遇/补给/巨星/伙伴)读 comp 成型度 —— overlay 时 board 不可读,用上次备战读的近似。
    last_state: GameState | None = None
    # 弃 target 重选(防 commit 锁死不可达 target:update_target 重选;live round6 HP4 死于此)。
    target_drought: int = 0
    # 替代旧 DeployBench naive 填位(从槽0拖全部,不看 position_pref)。用户反复要求接入决策。
    pending_deploys: list = field(default_factory=list)
    # 改用结算 HP(结算屏「小队生命值NN」可靠)给下回合 prep state.hp(HP 结算→下回合 prep 不变)。
    last_hp: int | None = None
    # 最近 node_type 真值(r7 review P0-①:商店开态帧节点行被遮 → read_node_type 恒 None,plan 路径
    # 1700/1706 行 None 实证 → boss 判定(cw_plan boss_spend/cw_evaluate 两处)全死码。Director 在
    # shop 关态 heavy 读到时写此;shop.py 喂 plan 前拷入 —— 仿 last_hp 模式)。
    last_node_type: str | None = None
    # 上回合结算 streak(带符号 连胜+/连败-;on_round_end 从结算「连胜×N」写)。给下回合 economy C 杠杆读
    # (连胜保连胜 / 连败 fold;fixture 核实 2026-08-11:语义在前缀,备战 read_streak 无方向故改结算源)。
    last_streak: int = 0
    # level 单调守卫(read_level OCR 间歇误读 5/6→4;等级局内只升不降,读出<上次=误读用上次)。新局默认 0。
    last_level_obs: int = 0
    # 防 new RunMegastarNode instance 重置 instance flag → re-click toggle 反选 → confirm 无候选 → 卡死)。
    megastar_candidate_clicked: bool = False
    # 已持有投资策略(局中选,可多张;live 修复 2026-08-15:宿主=session 持久,read_game_state
    # 拷贝到 state 供 _refresh_cap 等消费 —— 原接线只加 GameState 字段而 handler 写 session,
    # 停机隔离期从未 live 跑过,首跑暴露 AttributeError)。
    active_strategies: list[str] = field(default_factory=list)
    # —— 备战决策环(PrepDirector,doc 15 / ADR-0123)计数宿主 ——
    # defer_count:奖励球留置计数(环级 —— **Director 每次环入口清零**,非局级;球留置是本轮决定。
    # 策略/框架经 DeferSpheres +1;门=2(§5.1 规则 3 防规则 2↔3 空转环)。)
    defer_count: int = 0
    # prep_phase:默认策略主流程推进位(0=买牌前/1=买完/2=部署完/3=装备完→出战;环级,Director
    # 环入口清零,同 defer_count 宿主模式 —— 策略无状态,主流程阶段只能住 session,F6)。
    prep_phase: int = 0
    # r23 空板出战守卫重试计数(部署持续失败时防 phase 循环;≥2 放行交 Director stall 兜底)
    prep_phase_retry: int = 0
    # bail_reason_counts:BailToOuter 同因计数(局级,环重建不清零 —— ping-pong 诊断用;≥3 记 [cw!])。
    bail_reason_counts: dict[str, int] = field(default_factory=dict)
    rng: random.Random = field(default_factory=random.Random)  # 可种子化(公平/replay);蒙特卡洛 D 牌用
    performance: PerformanceTracker = field(default_factory=PerformanceTracker)  # 观测反馈(双侧 OCR)
    # ⚖️ memory/plane/round_num/pending_deploys 已删(2026-08-16 review D1/D2/TOP4:0 读者;
    # 进度真源 = session.last_state(每回合框架刷新);策略私有 scratch 无消费者)。
    # 简报词缀(对局开始 debuff/boss 词缀;loop __init__ 从 ctx.cw_briefing_affixes copy;mechanics_fit 输入)
    briefing_affixes: list[str] = field(default_factory=list)
    # 本局职级(A1..A8;StartCurrencyWarMatch 难度确认屏读 → ctx.cw_selected_difficulty → loop copy 到此;
    # default_strategy 填 state.selected_difficulty → effective_hp_threshold D-32 保血阈值;3.5.1 接线)
    selected_difficulty: str = ""
    # 敌人难度数值(简报「敌人难度N」读 → ctx.cw_enemy_difficulty → loop copy;read_game_state 填 state;3.5.2)
    enemy_difficulty: int | None = None
    # 简报首领(3 位面 boss 名;loop __init__ 从 ctx.cw_briefing_bosses copy;boss_fit 输入)
    briefing_bosses: list[str] = field(default_factory=list)
    active_env: str = ""
    # deploy/sell 同步待补(deploy=DeployBench 位置式 / sell=_handle_bench_full 位置式,后续接)。
    tracked_bench: list[str] = field(default_factory=list)
    tracked_bench_chars: list[BenchChar] = field(default_factory=list)
    tracked_deployed: list[BenchChar] = field(default_factory=list)


@dataclass
class CurrencyWarMatch:
    """运行时持有 strategy + session 的轻容器,挂 ``ctx.cw_match``(子 op 都拿得到 ``self.ctx``)。

    生命周期:``CurrencyWarRunLoop.__init__`` 每局创建 → 挂 ctx → 每个钩子收到的 session 就是它 →
    局终置 ``ctx.cw_match = None``(防跨局污染)。
    """
    strategy: CwStrategy
    session: StrategySession
