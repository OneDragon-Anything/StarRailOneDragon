"""货币战争 策略插件机制(CwStrategy ABC + StrategySession + CurrencyWarMatch)。

把货币战争的「决策大脑」抽象成**可替换的 ``CwStrategy`` 对象**(对标 app 插件):
换对象 = 换打法,不动框架。唯一内置具现 = ``DecisionV2Strategy``(注册桥在
``strategies/decision_v2_strategy.py``;default 栈已退役,ADR-0466)。

设计见 ``docs/develop/currency_war/strategy/07_plugin.md``;决策见
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

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from sr_od.application.currency_war.kernel.cw_events import (
    EncounterOption,
    EncounterPick,
    MegastarOption,
    MegastarPick,
    PartnerOption,
    PartnerPick,
    SupplyOption,
    SupplyPick,
)
from sr_od.application.currency_war.kernel.cw_performance import (
    RoundOutcome,
)
from sr_od.application.currency_war.kernel.cw_state import (
    Action,
    GameState,
    MatchOutcome,
    PickEvent,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import StrategySession

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

# 注解中的 ``CurrencyWarConfig`` 刻意不 import 真类型:config 属 app 桶,本模块
# 归 decision 桶,分包依赖矩阵禁 decision→app;config 实例由调用方按参注入,
# 下面绑定只是注解名的文档性占位(字符串;「刻意字符串注解」先例 = 期 0b
# kernel/cw_strategy_session 的 SrContext 处理)。
CurrencyWarConfig = 'CurrencyWarConfig'


class CwStrategy(ABC):
    """一整套货币战争局内打法(可替换的决策大脑;/§11.3)。

    **无状态策略**:实例**不持有可变的每局状态**,所有跨步状态走 ``StrategySession``(框架每局
    新建、传入每个钩子、局终销毁)。收益:实例可反复 instantiate、可 unit 测(喂构造好的 state)、
    无隐藏实例状态 → 不会跨局泄漏。

    本 ABC 的钩子**全 abstract**(纯接口,ABC 自身不含内置逻辑);唯一内置具现见
    ``decision_v2/strategy.py``。自定义策略:继承 ``CwStrategy`` 实现全部钩子,或继承
    ``DecisionV2Strategy`` 只覆盖关心的几个。

    **构造无参**(继承默认 ``object.__init__``):策略跨局跨账号复用,**不收 ctx/config** —— 配置每次
    调用按参传入;``StrategyManager`` 经 ``cls()`` 实例化。可变每局状态一律走 ``session``,非实例属性。
    """

    # ===== 元数据(类属性;扫描时读,无 _const.py sidecar —— 策略比应用简单)=====
    STRATEGY_ID: str = ""        # 唯一 id(如 "default"/"aggressive_rush"),去重键;空 = 中间辅助 ABC 不注册
    STRATEGY_NAME: str = ""      # GUI 显示名(如 "内置默认策略")
    AUTHOR: str = ""             # 参赛者/作者
    VERSION: str = "0.1"         # 语义化版本
    DESCRIPTION: str = ""        # 一句话描述打法
    # 扫描器内部:True = 中间辅助 ABC,不注册;非展示元数据(§11.5)
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
        """战略层:选/转型 target_comp。框架在每个备战回合 ``decide_shop_screen`` **之前**调一次。
        实现写 ``session.target_comp``(首轮选;其后按信号 pivot;无强信号保持)。"""

    @abstractmethod
    def decide_prep_action(self, obs, session: StrategySession,
                           config: CurrencyWarConfig):
        """备战决策环步级决策(doc 15 / ADR-0123,P1 新增):看 ``obs`` 出**一个**动作。

        - ``obs``: ``PrepObservation``(框架观察层产出;P1 ``overlay_state``/``shop_cards`` 恒空)。
        - 返回: 一个 ``PrepAction``(``prep_actions.py``;原子为主,P1 含 Run* 组合过渡)。
          控制流动作(``DeferSpheres``/``BailToOuter``)是框架信号,不走 execute 验证链。
        - 契约: 无状态策略 —— 跨步意图(defer 计数等)走 ``session``;框架保证每步先观察再决策
          (F1),动作合法性由框架校验(F3),验证失败/stall 屏蔽对策略透明(F4)。

        ⚠️ **deprecated(兼容期,P2 黑板模式)**:黑板接口 =
        :meth:`decide_prep_screen`(W971 §2)。本钩子保留为薄委托形态
        (旧签名 → 写 ``session.prep_obs_frame`` → 同一决策核),供存量
        测试/影子路径过渡;调用方迁移完后随 P5 删除。
        """

    @abstractmethod
    def decide_prep_screen(self, session: StrategySession,
                           config: CurrencyWarConfig):
        """备战画面黑板决策接口(W971 §2 黑板模式;前身 = ``decide_prep_action``)。

        - 输入:``session`` 唯一数据总线——备战观察结果由观察层写入
          ``session.prep_obs_frame``;跨步状态(defer 计数/phase 位等)同 session。
        - 返回:一个 ``PrepAction``(词表与 ``decide_prep_action`` 同)。
        - 契约:同 ``decide_prep_action``(F1/F3/F4);新增「观察帧缺失即抛错」
          ——黑板模式下决策读到 None 帧 = 观察层失约,禁静默按空观察决策。
        """

    @abstractmethod
    def decide_shop_screen(self, session: StrategySession,
                           config: CurrencyWarConfig) -> list[Action]:
        """商店开画面黑板决策接口(W971 §2/§4.1 amendment;前身 = ``decide_prep``)。

        - 输入:``session`` 唯一数据总线——商店融合观察态由商店观察段写入
          ``session.shop_state_frame``;战略导向 ``session.target_comp`` 同 session。
        - 返回:动作 list;词表 = {BuyCard, **LevelUpShop**, RefreshShop, SellBench,
          SellDeployed, CompTransaction}——升级意图用商店屏专用 ``LevelUpShop``
          (W970 §4.1.3 拆分,LevelUpShop is-a LevelUp,执行器/账本零改动)。
        - 终止语义:返回空序列 = 决策完成(流程层触发关店)。
        - 契约:观察帧缺失即抛错(同 ``decide_prep_screen``)。
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
        """遭遇难度选(其一易/其四难 二选一)。✅ 已接 ``CwScreenEncounter``(L55 调)+ ``cw_events.decide_encounter``
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
class CurrencyWarMatch:
    """运行时持有 strategy + session 的轻容器,挂 ``ctx.cw_match``(子 op 都拿得到 ``self.ctx``)。

    生命周期:``CwLoop.__init__`` 每局创建 → 挂 ctx → 每个钩子收到的 session 就是它 →
    局终置 ``ctx.cw_match = None``(防跨局污染)。
    """
    strategy: CwStrategy
    session: StrategySession


#: obs 读口注入槽(缺省关):清 obs 模块级 last-known-good 缓存的回调。
#: 分包依赖矩阵禁 decision→obs 直依,生产装配点 = app/decision_assembly
#: ``install_obs_ports()``(CurrencyWarApp.__init__ 接通);未注入 = 跳过
#: 缓存清理(容器弃置语义不受影响,session 全量重建承担状态隔离)。
_RESET_PHASE_ROUND_CACHE: Callable[[], None] | None = None


def set_obs_reset_hook(reset_phase_round_cache: Callable[[], None]) -> None:
    """装配点注入 obs 缓存清理回调(幂等,可重复调用覆盖)。"""
    global _RESET_PHASE_ROUND_CACHE
    _RESET_PHASE_ROUND_CACHE = reset_phase_round_cache


def discard_stale_match_container(ctx: SrContext, reason: str) -> bool:
    """上一局残留的 match 容器在**新局开始信号**处丢弃(迁移审计 w289(git 历史)/ADR-0419)。

    背景(迁移审计 w285(git 历史) 抽样判读):正常流程局终回大厅会置 ``ctx.cw_match = None``(cw_loop
    分支 3c),下一局 ``RunLoop.handle_init`` 见 None 新建 session —— 状态天然全新。但
    **异常路径**(run 被停机/崩溃在上局对局中、进程未重启)残留非 None 的旧容器;此时
    下一次入口链 ``CwEntryStart`` 开的是一局**新对局**,而
    ``handle_init`` 的续跑判定(``ctx.cw_match is None``)会把旧 session 整体延用:
    level 单调守卫拿上局 ``last_level_obs=5`` 打新局 plane1 的真读(迁移审计 w285(git 历史) cap_vs_level
    抽样 4/4 实证)、tracked 角色/streak/hp 对账锚全部跨局带毒——obs_conflict 三层
    (level/cap_vs_level/phase_round)329 张的残留源。

    本函数只在「确凿是新一局」的调用点用(难度确认/模式选择/简报三屏只在无保存局的
    新局路径出现;「继续进度」恢复同一物理局不触发)→ 把容器置 None,随后的
    handle_init 走新建分支实现**全量重置 by construction**(StrategySession 每字段
    回默认值,不存在漏清字段面);模块级观测缓存(plane/round last-known-good)由
    handle_init 既有的 ``reset_phase_round_cache()`` 清。

    Returns: True = 发现已弃置(本局起为全新 session);False = 无残留(幂等直过)。
    """
    if getattr(ctx, 'cw_match', None) is None:
        return False
    from one_dragon.utils.log_utils import log as _log
    _log.warning('[cw-entry] 检测到上一局残留 match 容器(%s)→ 弃置,'
                 '本局 session 全量重建(ADR-0419)', reason)
    ctx.cw_match = None
    if _RESET_PHASE_ROUND_CACHE is not None:
        _RESET_PHASE_ROUND_CACHE()
    return True


def gated_hp(current_hp: int | None, session: StrategySession,
             now_t: int | None,
             current_readable: bool = True) -> int | None:
    """结算 HP 新鲜度门(r68/r69,单源 helper):结算真值仅在**可信窗口**内覆盖现读。

    - 现读可信(``current_readable=True``)→ 仅紧邻上一节点(gap==1)的结算值可覆盖
      (结算屏「小队生命值NN」权威;防陈 hp 冻结毒化)。
    - 现读不可信(``False`` = 无真值/沿用帧,``hp_readable=False``;W823 None 化后
      现读基准可为 None,门只决定「是否被结算值覆盖」,不产兜底值)→ 放宽到 gap≤3:hp 只在
      战斗结算变,非战斗节点(奖励/补给/选卡)隔断时结算值本就仍真(r69 实证:r5 非战斗
      + r6 现读失败 → 旧 gap==1 判陈旧回退 100 假值喂 pivot);窗口 3 外(结算连失,
      如 boss conf=0 冻结场景)仍拒 → 保持兜底值。

    消费点:shop.py(buy 前)+ cw_screen_prep(环入口,传 obs.state.hp_readable)+
    策略层 ``_pseudo_state`` —— 同门,否则先调方用假 hp 判 pivot、后调方真 hp
    反向 pivot,同节点两次方向相反换线(r68 实证)。
    """
    last_hp = getattr(session, 'last_hp', None)
    last_t = getattr(session, 'last_hp_t', None)
    if last_hp is None or now_t is None or last_t is None:
        return current_hp
    gap = now_t - last_t
    if gap == 1 or (not current_readable and 1 < gap <= 3):
        return last_hp
    return current_hp
