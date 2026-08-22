# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 策略插件机制(CwStrategy ABC + StrategySession + CurrencyWarMatch)。

把货币战争的「决策大脑」抽象成**可替换的 ``CwStrategy`` 对象**(对标 app 插件):
换对象 = 换打法,不动框架。内置具现 ``DefaultCwStrategy``(``strategies/default_strategy.py``)
= 今天打法(薄委托既有模块函数,P1 零行为变化)。

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
    # last_hp 的全局节点号((plane-1)*9+round;r68 review):结算 hp 只在「紧邻上一节点」才可覆盖
    # prep 现读 —— 低 conf 结算轮(boss 胜利屏 hp 裸数字常读不到)last_hp 残留陈值,无条件覆盖
    # = 陈 hp 冻结毒化每回合 prep(保血/转型永不触发;P1 boss 赢→hp1 进 P2 秒死 ×3 的观测链根因)。
    last_hp_t: int | None = None
    # r70 过渡框架(仙舟/列车,''=未定):双轨期买/上/卖三侧的统一临时 target
    # (cw_transition.pick_framework 按 board+bench+shop 持有选定;update_target 每轮刷新)。
    transition_framework: str = ''
    # r73 review RC3:双轨期标志**单一源在 session**(state.dual_track_phase 是每循环
    # 新建对象的默认 False,写在那里的值活不过一次 read_game_state —— ADR-0209 双轨
    # 买门/stash 放行/DP 攒息压制因此在实跑买牌路径从未执行)。update_target 写此,
    # shop 循环态/Director/plan 消费方每轮从此拷贝回 state(消费接口不变)。
    dual_track_phase: bool = False
    # 最近 node_type 真值(r7 review P0-①:商店开态帧节点行被遮 → read_node_type 恒 None,plan 路径
    # 1700/1706 行 None 实证 → boss 判定(cw_plan boss_spend/cw_evaluate 两处)全死码。Director 在
    # shop 关态 heavy 读到时写此;shop.py 喂 plan 前拷入 —— 仿 last_hp 模式)。
    last_node_type: str | None = None
    # r265:节点行 current 槽的识别类型(read_node_sequence: Hu 模板+OCR 标签,
    # 备战画面权威源)——prep_director 每次备战读节点行时写;battle_loop
    # on_round_end 消费(节点类型分层的遥测/复盘输入;替代 r260 结算屏
    # OCR 二手推断——'基础奖励'金币区误判实锤)。None=未读到(退普通战斗)。
    node_type_current: str | None = None
    # r266:上帧 upcoming 槽类型序列(idx 升序)——current 高亮态 Hu 不匹配
    # (恒 None 实锤)时左移推断用:本轮 current = 上帧 upcoming[0]
    # (节点行固定序列左移一位)。
    upcoming_types: list[str] | None = None
    # r306(用户指路):开局帧完整槽序——**离线统计源**(跨局累积
    # 建「位面典型节点表」进 sim 骨架/策略知识)+ 左移兜底参照。
    # 决策主源 = 实时识别(每备战帧读节点行,应对策略改节点)。
    # r363(审计 P0-1):battle_loop 首节点兜底消费此表——写入端
    # 在 prep_director._probe_node_type 首帧(此前 r362 修复无写
    # 入者,审计实锤死读)。
    plane_node_table: list[str] | None = None
    # r363(审计 P0-2):左移推断的轮次锚——同轮多次 probe 不重做
    # 左移(防 current 超前一位写下一节点类型)。
    nodeseq_probe_anchor: tuple | None = None
    # 上回合结算 streak(带符号 连胜+/连败-;on_round_end 从结算「连胜×N」写)。给下回合 economy C 杠杆读
    # (连胜保连胜 / 连败 fold;fixture 核实 2026-08-11:语义在前缀,备战 read_streak 无方向故改结算源)。
    last_streak: int = 0
    # r93 审计 46336415:腾席链 DeployMove 失败记忆(char_id → 失败计数)。同一角色拖拽被
    # 游戏拒(同名在场/行限制等预检漏网的落点)→ 重试同目标 = 白烧环步(第14局 r9 藿藿
    # 5 连败实证);失败过的角色跳过,优先下一个候选(拖失败本身不消费 bench,下轮还在)。
    deploy_fail_counts: dict = field(default_factory=dict)
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
    # r3 review④:动态 setattr 升正式字段(asdict/repr 完整;getattr 兜底随之可删)
    # r358d(遥测接线,ADR-0229 缺口):选择类 handler 写 → read_game_state
    # 回写 state 同名字段(复盘维度:巨星绑定/伙伴选择与 comp 匹配)。
    chosen_megastar: str = ''
    chosen_partner: str = ''
    pivot_cooldown_until: int = 0                      # r7 pivot 冷却(转线后 N 轮封信号 1/2;保命豁免在调用侧)
    drought_excluded: list[str] = field(default_factory=list)   # r20 极端 drought 弃线名单(r7 review:单槽会被第二条死线覆盖→振荡;死线不复活,局级=session 新建)
    commit_signals: object = None   # ADR-0209 CommitSignals(定型信号累积器;惰性建——default_factory 会引环形导入,update_target 首调时建)
    stash_comp: object = None       # ADR-0209 双轨期信号领先线 comp(囤牌方向;update_target 每回合刷新)
    commit_flip_pending: bool = False   # ADR-0209 定型边沿(卖散上限放宽;decide_prep 一次性消费)
    focus_factions: set[str] = field(default_factory=set)   # ADR-0209 flex 收敛白名单(已铺 flex top2)
    last_candidate_scores: dict[str, float] = field(default_factory=dict)   # 选线轮的 top-3 实际排序分(r6 遥测补)
    last_candidate_scores_round: int = -1              # 分数轮次戳(shop 侧判陈旧清空)
    _supply_refresh_used: bool = False                 # 补给刷新 1 次已用(r2#2 跨实例)
    # —— 策略 v2(LineStrategy)扩展态——正式字段(评审 B-bg:动态
    # setattr 会在「session 新建而 on_match_start 未走」路径崩;
    # 且 asdict/telemetry 看不见动态属性——升正式,r3 review④ 同判例)——
    # 默认值 None(评审 B1:default 局遥测 v2_* 应全空可区分——
    # 不能用元组默认,否则 default 呈现假 economy 污染 AB 对拍)
    v2_state: tuple | None = None
    # cw_phase_machine 状态元组(None=default 未初始化;
    # LineStrategy.on_match_start 用 initial_state() 规范化)
    locked_line: str | None = None                     # 锁定线 id(None=未锁)
    bridge_id: str | None = None                       # 当前桥线 id(None=无)
    # r246:普通战斗败检测的上一轮 HP(r246 P2 三连败实锤——
    # hp_after 降幅 ≥10 = 节点实际打输,喂 E1_miss 攒滞回)
    v2_prev_hp: int | None = None
    # r23 空板出战守卫重试计数(部署持续失败时防 phase 循环;≥2 放行交 Director stall 兜底)
    prep_phase_retry: int = 0
    # star 回退停机钩子计数(用户 2026-08-17:star2/3 识别担心;char → 连续回退次数;
    # 连续 2 节点回退 = 真识别问题(特效遮挡过渡帧一节点内消)→ 停机保画面排查;读回恢复即清零)
    star_regression_count: dict[str, int] = field(default_factory=dict)
    # star 回退防抖(char → 已见次数;2026-08-18 离线复现:274 存证 36/40 同图重读 2★,
    # live 读 1★ = 3合1 合成动画窗)—— 首次回退 star 保旧不写回,连续第二次才采新确认。
    star_pending_regression: dict[str, int] = field(default_factory=dict)
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


def gated_hp(current_hp: int, session: StrategySession, now_t: int | None,
             current_readable: bool = True) -> int:
    """结算 HP 新鲜度门(r68/r69,单源 helper):结算真值仅在**可信窗口**内覆盖现读。

    - 现读可信(``current_readable=True``)→ 仅紧邻上一节点(gap==1)的结算值可覆盖
      (结算屏「小队生命值NN」权威;防陈 hp 冻结毒化)。
    - 现读不可信(``False`` = 100 兜底,``hp_readable=False``)→ 放宽到 gap≤3:hp 只在
      战斗结算变,非战斗节点(奖励/补给/选卡)隔断时结算值本就仍真(r69 实证:r5 非战斗
      + r6 现读失败 → 旧 gap==1 判陈旧回退 100 假值喂 pivot);窗口 3 外(结算连失,
      如 boss conf=0 冻结场景)仍拒 → 保持兜底值。

    消费点:shop.py(buy 前)+ prep_director(环入口,传 obs.state.hp_readable)+
    default_strategy ``_pseudo_state`` —— 同门,否则先调方用假 hp 判 pivot、后调方真 hp
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
