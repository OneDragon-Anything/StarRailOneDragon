"""货币战争 策略插件机制(CwStrategy ABC + StrategySession + CurrencyWarMatch)。

把货币战争的「决策大脑」抽象成**可替换的 ``CwStrategy`` 对象**(对标 app 插件):
换对象 = 换打法,不动框架。唯一内置具现 = ``DecisionV2Strategy``(注册桥在
``strategies/decision_v2_strategy.py``;default 栈已退役,ADR-0466)。

设计见 ``docs/develop/currency_war/strategy/07_plugin.md``;决策见
``docs/develop/sr_od/application/currency_war/decisions/INDEX.md`` 。本模块**纯逻辑**:所有钩子只吃
``CwSimFrame``/选项 + 出 ``Action``/``Pick``,**绝不碰屏幕 / ``ctx.controller``**(读屏与点击
是框架职责)→ 策略可离线 unit 测、可 replay。

四个组件(本模块 3 个 + manager):
- ``CwStrategy`` —— ABC,大脑接口(契约形状见 ADR-0583:每局冷建 2
  + 分画面决策入口 11 = abstract 12,外加非 abstract 工厂 ``create_state``
  1 = 保留总成员 13;零策略专属语义——方向重估节拍/意向 target 机器
  是具体策略实现的私事,不在基类契约面上)。
- ``StrategySession`` —— 每局跨步状态(框架新建 / 局终销毁;策略读写)。
- ``CurrencyWarMatch`` —— 运行时持有 strategy+session 的轻容器,挂 ``ctx.cw_match``。
- ``StrategyManager``(``cw_strategy_manager.py``)—— 约定式文件扫描发现 + 去重 + 实例化。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, Literal, TypeVar

from sr_od.application.currency_war.kernel.cw_events import (
    EncounterOption,
    EncounterPick,
    MegastarOption,
    MegastarPick,
    PartnerOption,
    PartnerPick,
    PlannerOption,
    PlannerPick,
    SupplyOption,
    SupplyPick,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    ExecState,
    bind_exec_state,
)
from sr_od.application.currency_war.kernel.cw_vocab import Action, PickEvent
from sr_od.application.currency_war.kernel.cw_strategy_session import StrategySession

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState
    from sr_od.application.currency_war.kernel.cw_prep_actions import PrepAction
    from sr_od.context.sr_context import SrContext

# 注解中的 ``CurrencyWarConfig`` 刻意不 import 真类型:config 属 app 桶,本模块
# 归 strategies 包实现层,与 cw_strategy_manager 同层(策略统一迁移批二勘误落位:接口是
# ops/sim/impl 三方共享契约,非实现本体;本模块禁依 app 桶);config 实例由调用方按参
# 注入,下面绑定只是注解名的文档性占位(字符串;「刻意字符串注解」先例 =
# 期 0b kernel/cw_strategy_session 的 SrContext 处理)。
CurrencyWarConfig = 'CurrencyWarConfig'

#: 策略器私有状态的泛型参数(设计正本 §1/§8.5/§8.6-6,迁移批次三「下沉
#: 策略实现层」):StrategyState 归**策略实现层私有**,框架策略器基类仅以
#: 泛型参数携带(本 ABC = 设计所称「策略器基类」,``BaseStrategy[TState]``
#: 形态的落位),框架(kernel/one_dragon)不感知具体类型、零 import 具体
#: 类——具体绑定由各策略实现在自己的类声明上完成(内置 =
#: ``strategies/impl/mandate_v1/mandate_state.StrategyState``,经
#: CwFlowStrategy 链绑定)。布局守卫 = sr-od-test 布局/泛型约束锁。
_TState = TypeVar('_TState')


class CwStrategy(ABC, Generic[_TState]):
    """一整套货币战争局内打法(可替换的决策大脑;/§11.3)。

    **无状态策略**:实例**不持有可变的每局状态**,所有跨步状态走 ``StrategySession``(框架每局
    新建、传入每个契约调用点、局终销毁)。收益:实例可反复 instantiate、可 unit 测(喂构造好的
    state)、无隐藏实例状态 → 不会跨局泄漏。

    契约形状(ADR-0583):基类 = 「每局冷建(create_session/create_state)+ 分画面决策入口
    (备战 1 / 商店 1 / pick 族 9)」;方向重估时机、意向状态机、事件钩子等策略内部构造**不在
    契约面**(旧 ``update_target``/生命周期钩子族已随 ADR-0583 出基类)。本 ABC 契约成员全
    abstract(纯接口,ABC 自身不含内置逻辑;``create_state`` 工厂除外,非 abstract)。自定义
    策略:继承 ``CwStrategy`` 实现全部契约成员,或继承 ``CwFlowStrategy`` 只覆盖关心的几个。

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

    # ===== 每局冷建(唯一冷建口 + 状态工厂;ADR-0583 生命周期收编)=====

    @abstractmethod
    def create_session(self, config: CurrencyWarConfig) -> StrategySession:
        """每局开始(run loop)调一次。返回空白 ``StrategySession``(rng 留默认,由 run loop 按
        ``config.strategy_seed`` 覆盖)。策略可覆盖以注入自己的 session 子类 / 初始 memory。
        **唯一冷建口**(ADR-0583):策略器状态经 ``create_state`` 工厂在此接线
        (flow 具现),live 初值一并在此落位;不存在第二状态冷建路径。"""

    def create_state(self, config: CurrencyWarConfig) -> _TState | None:
        """策略器状态对象工厂(session.md as-designed §3.1/§5.1;设计正本
        §8.5:返回类型 = 本策略实现的私有状态类型,经泛型参数 :data:`_TState`
        承载,基类不感知具体字段)。

        每局冷建一局存活的策略器状态对象,写入 ``session.strategy_state``
        (黑盒契约:框架只搬运引用,不读不写内部;所有权归策略器)。
        **非 abstract 契约成员,基类缺省返回 None**(第三方兼容条款 B4,收缩
        口径见 ADR-0563:缺省 None 不炸构造与 create_session;工厂实现
        契约 = 可忽略 config/容忍 None——sim 注入桩面传 None);内置
        mandate_v1 覆写返回其 StrategyState(改名归位,§8.6-6)。"""
        return None

    # ===== 分画面决策入口(ADR-0517 目标模型:op 的策略接触面 = 入口观察
    #       + 策略器单动作循环;入口按画面塑形,方向重估时机是实现私事)=====

    @abstractmethod
    def decide_prep_screen(self, session: StrategySession,
                           config: CurrencyWarConfig) -> list[PrepAction]:
        """备战画面黑板决策接口——**序列契约 v1**(序列决策契约,
        2026-09-03 冻结;前身 = ``decide_prep_action`` 单动作,W971 §2 黑板模式)。

        - 输入:``session`` 唯一数据总线——备战观察结果由观察层写入
          ``session.prep_obs_frame``;跨步状态(defer 计数/phase 位等)同 session。
        - 返回:``list[PrepAction]``,**执行序 = 列表序**(契约 §1;与商店线
          ``decide_shop_screen`` 同构的裸 list,Decision/AtomOp 层不进生产接口)。
          序列语义(契约 §2/§3/§4):
          - **帧稳定域**:序列内第 i+1 个动作不得依赖第 i 个动作执行后的新观察;
            发射时逐动作判「执行后画面状态能否静态推出」,推不出即在该动作处
            截断(该动作可作序列最后一个动作发出)。截断规则初始枚举 = 契约 §3。
          - **fail-stop 归流程侧**:任一动作未落地 → 流程侧丢弃余下动作并
            heavy 重观察后重调本接口;参数非法(F3 拒绝)与执行失败同型。
          - **逐动作验证保留**:期望态对账/执行验证照跑(执行侧记账,不依赖
            重新决策)。
          - **空序列合法** = 「本帧无动作可发」;备战线空批处理归流程侧框架
            (重观察,stall 兜底由流程侧定义),策略器**禁用空批表达控制流**。
          - 控制流走词表内特殊动作(``DeferSpheres`` 族;defer 计数归框架),
            不进 execute 验证链。
          - 生命周期机制(幂等键 ``action_key``/连败→恢复→屏蔽/stall 门/强制
            出战)归框架,策略器不自实现。
        - 契约:同 ``decide_prep_action``(F1/F3/F4);「观察帧缺失即抛错」
          ——黑板模式下决策读到 None 帧 = 观察层失约,禁静默按空观察决策。
        - 迁移期并行使能(契约 §1):现役单动作核包一层**长度 1 序列**的适配器,
          行为与现状逐动作重决策等价;新核 = 同接口替换,切换前后对流程侧零感知。
        """

    @abstractmethod
    def decide_shop_action(self, session: StrategySession,
                           config: CurrencyWarConfig) -> Action:
        """商店单动作决策入口(ADR-0517 决策 1/2/5;ADR-0583 升格入契约面,
        本批前为 flow 中间层成员)。全函数恒可用终结 = ``CloseShop``;
        生产执行侧单动作循环逐帧调用(sim/回放经 ``decide_shop_screen``
        驱动器循环化消费,该驱动器非契约成员)。观察帧缺失 = 观察层失约,
        实现须抛错(禁静默按空态决策)。
        """

    @abstractmethod
    def decide_invest(self, kind: Literal["strategy", "env"], options: list[str],
                      bs: GameState, session: StrategySession,
                      config: CurrencyWarConfig) -> PickEvent:
        """投资策略/投资环境 3 选 1(``kind`` 区分;P1 两 kind 走同一默认实现)。``options``=OCR 卡名列表。"""

    @abstractmethod
    def decide_supply(self, options: list[SupplyOption], bs: GameState,
                      session: StrategySession, config: CurrencyWarConfig,
                      refresh_used: bool = False) -> SupplyPick:
        """补给选装备/出钻。⚠️ OCR 未就绪(契约成员存在 + 默认委托,handler 不 rewire,随阶段5)。"""

    @abstractmethod
    def decide_encounter(self, options: list[EncounterOption], bs: GameState,
                         session: StrategySession, config: CurrencyWarConfig,
                         refresh_used: bool = False) -> EncounterPick:
        """遭遇难度选(其一易/其四难 二选一)。✅ 已接 ``CwScreenEncounter``(L55 调)+ ``cw_events.decide_encounter``
        (非平凡:未成型→低难保生存 / 成型+词缀利→高难拿奖励 / 全克→刷新换批)+ ``read_encounter_options``
        (OCR 卡标题→difficulty)。affix 分支 N/A(选项 UI 不显词缀,战后才显)。原「dormant 无选项UI」过期(2026-08-12 核实)。"""

    @abstractmethod
    def decide_megastar(self, options: list[MegastarOption], bs: GameState,
                        session: StrategySession, config: CurrencyWarConfig) -> MegastarPick:
        """巨星选候选。⚠️ OCR 未就绪(契约成员存在 + 默认委托,handler 不 rewire,候选 char_id 空 → idx=0)。"""

    @abstractmethod
    def decide_partner(self, options: list[PartnerOption], bs: GameState,
                       session: StrategySession, config: CurrencyWarConfig) -> PartnerPick:
        """选择伙伴。⚠️ OCR 未就绪(契约成员存在 + 默认委托,handler 不 rewire,char_id 空 → idx=0)。"""

    @abstractmethod
    def decide_planner(self, options: list[PlannerOption], bs: GameState,
                       session: StrategySession, config: CurrencyWarConfig) -> PlannerPick:
        """银狼策划事件 3 选 1(r104 接入;ADR-0583 补入契约面)。``options`` = 选项卡 OCR 文本。"""

    @abstractmethod
    def decide_star_tome(self, options: list[str], bs: GameState,
                         session: StrategySession, config: CurrencyWarConfig) -> int:
        """星徽典籍四选一,返回 options 索引(r104 接入;ADR-0583 补入契约面)。"""

    @abstractmethod
    def decide_wish_trial(self, options: list[str], bs: GameState,
                          session: StrategySession, config: CurrencyWarConfig) -> int:
        """祈愿试炼选卡,返回 options 索引(r104 接入;ADR-0583 补入契约面)。"""

    @abstractmethod
    def decide_box_card(self, names: list[str], bs: GameState,
                        session: StrategySession, config: CurrencyWarConfig) -> int:
        """武装箱/节点弹窗装备卡 4 选 1,返回 names 索引(r104 接入;ADR-0583 补入契约面)。"""


@dataclass
class CurrencyWarMatch:
    """运行时持有 strategy + session 的轻容器,挂 ``ctx.cw_match``(子 op 都拿得到 ``self.ctx``)。

    生命周期:``CwLoop.__init__`` 每局创建 → 挂 ctx → 每个契约调用点收到的 session 就是它 →
    局终置 ``ctx.cw_match = None``(防跨局污染)。
    """
    strategy: CwStrategy
    session: StrategySession
    # 执行层状态载体(session.md §2.4/§5.5;22 具名,生命周期 = 一局;
    # 账外收编账本 = ADR-0563「落位裁量」节)。
    # 访问口与旁表绑定单一源见 kernel/cw_exec_state.py。
    exec_state: ExecState = field(default_factory=lambda: ExecState())

    def __post_init__(self) -> None:
        # session→执行侧载体旁表绑定(单一源;kernel/策略器/sim 无 ctx
        # 面经 exec_state_of(session) 解析到同一实例)。
        bind_exec_state(self.session, self.exec_state)
        # 策略器状态兜底附着:策略未覆写 create_session(直用裸 session)
        # 而状态工厂已注册(mandate_v1 在场)→ 附着当局状态对象。恢复局
        # 冷启动契约(session.md §3.2)不变——附着的是**新建**状态对象;
        # 第三方策略无工厂注册 → 保持 None(其策略器沿用惰性建模式)。
        from sr_od.application.currency_war.kernel.cw_strategy_session import (
            ensure_strategy_state_attached,
        )
        ensure_strategy_state_attached(self.session)


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
    """结算 HP 新鲜度门(r68/r69;门本体已下沉 kernel 政策层,本函数 =
    **薄委托**,签名与调用面不变、行为零变化)。

    本体归宿 = ``kernel/cw_hp_policy.apply_hp_freshness_gate``(单一源;
    窗口政策两常量 ``HP_FRESH_GAP_TRUSTED``/``HP_FRESH_GAP_UNTRUSTED_MAX``
    随本体入政策层)。kernel 决策簇 hp 消费**禁经本函数**(kernel 禁反向
    import 策略实现层)——kernel 侧统一走 ``kernel/cw_hp_policy
    .decision_hp`` 决策读口;本函数只辖策略实现层既有调用点(写侧预施门
    + 消费侧 2 点)。

    语义(逐位等价,详见本体 docstring):锚缺任一 → 恒等返回现读;锚全时
    ``gap=now_t-last_t``——现读可信仅 gap==1 结算值可覆盖,不可信放宽到
    gap≤3,窗外保持现读;None 现读非恒等豁免(锚全时窗内同样被结算值
    覆盖);门幂等。时基契约:now_t 与结算锚写点
    (``cw_screen_battle_wait`` 的 last_hp_t)同经
    ``cw_plane_table.node_t_of`` 派生(schedule 真值;回退态与旧字面量
    ``(plane-1)*9+round_num`` 逐位相同),禁单侧改式;迁移期 prep 写侧
    预施门两处暂留旧式,申报见 ``cw_hp_policy.apply_hp_freshness_gate``
    时基契约节。

    实调点申报纪律(全仓 grep 口径;新增调用点先对账「是否该直走政策层
    读口」):cw_screen_prep 环入口×2(端口路径/读屏路径,写侧预施门,
    W5 收编后保留至旧链删除)+ cw_screen_prep 终饰×2(观察终饰+lifecycle
    payload 终饰,同写侧)+ mandate_v1 adapter decision_state×1(消费侧,
    视图真值)+ mandate_v1 encounter λ 键读点×1(消费侧,_hp_gate_state,
    W5 补门读点域)。旧注「shop.py buy 前」系 ADR-0583 内化前代码形态
    残留,商店线 buy 前吃门已由环入口终饰承载,shop.py 零调用。同门纪律:
    先调方用假 hp 判 pivot、后调方真 hp 反向 pivot,同节点两次方向相反
    换线(r68 实证)。方向重估(ADR-0583 内化进策略器决策入口)消费的是
    **已被本门覆写后的帧 state**(cw_screen_prep 环入口终饰在决策入口
    之前执行)→ 驱动输入恒为同门 hp,见 gated 门锁
    (test_cw_blackboard.py::TestDirectionRhythmL1L2L3L7::test_l7)。
    """
    from sr_od.application.currency_war.kernel.cw_hp_policy import (
        apply_hp_freshness_gate,
    )
    return apply_hp_freshness_gate(
        current_hp, getattr(session, 'last_hp', None),
        getattr(session, 'last_hp_t', None), now_t, current_readable)
