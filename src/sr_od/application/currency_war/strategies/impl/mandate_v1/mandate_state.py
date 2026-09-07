"""货币战争 mandate_v1 策略器状态对象(MandateState;session.md as-designed
§3.1 裁决 1 的落地载体)。

职责来源裁定(用户 2026-09-06,session.md 头注):session 只承载「从游戏
画面观察到的数据」;策略推导产生的中间状态(目标意向/定型信号/回退集/
纪律计数/遥测分键容器/推导缓存)是**策略器的内容**,由实现包私有定义、
一局内存活、自己持有。框架经 ``CwStrategy.create_state`` 工厂钩子按局
创建实例、写入 ``session.strategy_state``,此后**框架只搬运引用,不读
不写其内部**(黑盒契约);类型定义、字段、更新语义全部在本实现包。

迁移账本(session.md §2.3 28 项 + §2.6 24 项 = 52 具名字段;外加实施批
实装时按 §6.1「账外字段一律视为范围遗漏」收编的两波策略侧动态属性
共 20 个——第一波 9 个:cw4_shop_rejects/cw4_line_state/cw4_m1p_seam_
verified/drought_excluded/cw4_cap_override/v3_reserve_overflow/
v3_release_budget/v3_release_reason/v3_piggy_reward;第二波 11 个:
cw4_fuel_filler_stall_buys/cw4_m1p_arm_pending/cw4_m7_equipped_phase/
cw4_must_spend_phase/cw4_pop_slot_why/cw4_prev_line_name/
cw4_recent_sold_names/cw4_shopped_phase/cw4_stale_seen_rounds/
cw4_tools_phase/cw4_visit_bought_names。合计 72 具名,逐波归类理由见
ADR-0563「落位裁量」节账外清单)。原
``session.memory`` scratch dict 按设计 §6.3 随切换直接消解:一次性键落
本类的 ``scratch`` dict(纪律条款原样平移:键名加模块前缀、局级生命
周期、不入 decisions 遥测;高频共用/需类型与守卫的状态升本类具名字段)。

边界(kernel 消费面):kernel 判据层对策略状态的消费经
``kernel.cw_strategy_session.strategy_state_of`` 访问函数(返回
``MandateState | None``,None = 无状态对象的裸构造/第三方策略面——
调用方按原 getattr 缺省语义保守处理),kernel 不持有本类字段注解、
运行时零本包 import(TYPE_CHECKING 承载)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )


@dataclass
class MandateState:
    """mandate_v1 策略器一局状态(局首由工厂冷建,局终随 session 销毁)。

    生命周期契约(session.md §3.1 条款 2):每局新建即天然清零,禁跨局
    复用实例;意向状态机段级重入守卫(``v3_intention_key``)语义自原
    session 字段原样平移,不变。字段分组与产生者/消费者/生命周期注释
    平移自原 ``kernel/cw_strategy_session.py`` 对应字段(语义零变更,
    值域与缺省一致——含 on_match_start 原逐项初始化值,改由缺省值承载:
    状态对象每局冷建 = 天然初值,清零段整体消失)。
    """

    # ===== 意向面(update_target 策略推导;局/轮)=====
    target_comp: Comp | None = None   # 战略层目标阵容(update_target 维护)
    # 弃 target 重选(防 commit 锁死不可达 target:update_target 重选)。
    target_drought: int = 0
    # 待执行的部署意图(按 position_pref 决策落位)。
    pending_deploys: list = field(default_factory=list)
    # 过渡框架(仙舟/列车,''=未定):双轨期买/上/卖三侧的统一临时 target。
    transition_framework: str = ''

    # ===== 定型面(ADR-0209 定型信号推导;局)=====
    # CommitSignals(定型信号累积器;update_target 首调时惰性建——
    # default_factory 会引环形导入,保留 None 惰性建模式)。
    commit_signals: object = None
    # 双轨期信号领先线 comp(囤牌方向;update_target 每回合刷新)。
    stash_comp: object = None
    # 定型边沿(卖散上限放宽;decide_prep 一次性消费)。
    commit_flip_pending: bool = False
    # flex 收敛白名单(已铺 flex top2)。
    focus_factions: set[str] = field(default_factory=set)

    # ===== 遥测披露缓存(选线轮评分;轮;T-113/ADR-0579:_telemetry_ 前缀 =
    # 披露面自带隔离,禁决策消费——守卫 = 全仓命中点计数锁,恰 2 处声明 +1 写点
    # +1 读点)=====
    _telemetry_last_candidate_scores: dict[str, float] = field(default_factory=dict)
    _telemetry_last_candidate_scores_round: int = -1   # 分数轮次戳

    # ===== 相位面(v2 决策层相位元组;A2 改判迁出——活读端 =
    # cw_op_buy_cards decisions 行,活写端 = sim 初始相位注入)=====
    v2_state: tuple | None = None
    locked_line: str | None = None                     # 锁定线 id(None=未锁)
    bridge_id: str | None = None                       # 当前桥线 id(None=无)

    # ===== 意向/演进/纪律(v3 决策框架载体;局/轮)=====
    v3_intention: object = None      # cw_intention.IntentionState(锁线/撤销状态机)
    v3_evolution: object = None      # cw_evolution.EvolutionState(中断恢复/谷底回滚)
    v3_core_names: set = field(default_factory=set)   # 意向核心名集
    v3_mode: str = 'economy'         # 本轮模式('economy'|'war';纪律族每轮写)
    v3_alarm: object = None          # discipline.BloodAlarmTracker(掉血三臂)
    v3_pending_rollback: object = None   # 谷底回滚待发动作
    v3_prev_hp: int | None = None        # 掉血三臂的上一节点 HP(结算真值链)
    v3_last_intention_event: str = ''    # 意向事件去重(判读日志锚)
    v3_intention_key: tuple | None = None   # 意向状态机驱动轮键(段级重入守卫)

    # ===== 血预算拒付披露(遥测;局)=====
    v3_blood_budget_rejects: int = 0
    v3_blood_budget_refresh_rejects: int = 0

    # ===== P2 承接快照(ADR-0399;位面)=====
    v3_handoff: object = None
    v3_handoff_plane: int | None = None

    # ===== 对账门声明(帧级全量重算;帧)=====
    v3_posture_unfulfilled: dict | None = None

    # ===== 策略行为观测分键(cw4_counters.jsonl 局终快照/sim 轮差分账本
    # /A/B 披露的单一容器;遥测消费线经访问函数保持可读)=====
    cw4_counters: dict = field(default_factory=dict)

    # ===== 相位与镜像(每轮重算;write_shop_mirrors 写)=====
    # 相位观测缺省 = ''(无写端退役缺省,与原「动态属性缺席」读取语义
    # 逐字节一致;live 由 on_match_start 显式置 'FORM',sim 不调该钩子
    # → 恒 ''——两条路径的旧读数各自保真)。
    v3_phase: str = ''
    v3_form_ok: bool = False         # 镜像现读写端(write_shop_mirrors/sim 发射帧)
    v3_b_t: int = 0                  # 板面目标线承重计数(每轮重算)
    v3_dp_posture: object = None     # DP 姿态轮缓存
    v3_mirror_key: tuple | None = None   # 镜像族轮键戳(单源=write_shop_mirrors)
    v3_formed_stop: bool = False     # 成型停手(ADR-0343;行为面消费)

    # ===== 补偿/稳态簿记(ADR-0326/0378;局)=====
    v2_remedy_used: bool = False
    v2_steady_lv_used: bool = False
    v3_steady_lv_abandoned: int = 0
    v3_remedy_abandoned: int = 0

    # ===== 轮笔数披露(decisions/遥测判读面;轮)=====
    v2_round_refreshes: int = 0
    v2_round_p1_early: int = 0
    v2_round_p2_core: int = 0
    v2_round_press_exempt: int = 0
    v2_round_press_copy: int = 0

    # ===== 泄息指令与承接门(W332b/w227/ADR-0400/0403;轮)=====
    v3_release: object = None
    v3_release_round: int | None = None
    # 义务实花披露(遥测键 sess_release_spent 透传源):写端=商店执行
    # 回执位(cw_op_buy_cards.accrue_release_spent,首版只计刷新实花,
    # 「宁窄勿虚」口径申报归 ADR-0571),轮界清零承载=v3_disclosure_key
    # 键戳(assembly 装配点);读端=recorder/engine_p1 轮快照。披露面
    # 字段,禁决策判据消费(ADR-0571)。
    v3_release_spent: int = 0
    v3_handoff_gap: int = 0
    v3_handoff_hp_proj: int | None = None

    # ===== 消费侧惰性建(缺省值 = 原惰性初值)=====
    # A/B 注册表注入通道(cw_economy._registry_of 消费;None=缺省表)。
    v3_registry: object = None
    # 定向刷新消耗计数(cw_registry 名单;局级累计)。
    v3_dir_refresh_used: int = 0
    # DP 姿态轮帧缓存(每段 decide_prep 覆写;None=本轮无决策段)。
    v3_alloc_frame: dict | None = None
    # 储备线披露(遥测键 sess_reserve_cap 透传源;写端=assembly.
    # _disclose_budget 每 prep 装配帧幂等覆写;读端=recorder/engine_p1
    # 轮快照。披露面字段,禁决策判据消费,ADR-0571)。
    v3_reserve_cap: int = 0

    # ===== 账外补充(实施批按 §6.1 收编的策略侧动态属性;产生者/消费
    # 面注释见原写入/读出点)=====
    # 储备溢余披露(遥测键 sess_reserve_overflow 透传源;写端=assembly.
    # _disclose_budget,读端=recorder/engine_p1 轮快照。披露面字段,
    # 禁决策判据消费,ADR-0571)。
    v3_reserve_overflow: int = 0
    # 义务预算披露(遥测键 sess_release_budget 透传源;写端/读端同上)。
    v3_release_budget: int = 0
    # 义务来源披露(遥测键 sess_release_reason 透传源;写端=shop 必花域
    # 段「must_spend」帧内 last-wins + 装配键戳轮界清零,读端同上)。
    v3_release_reason: str = ''
    # 披露面轮键戳(T-88 轮界清零承载):坐标系=(plane, round) 二元组
    #(位面号/位面内轮次,均 1 基);取值时机=装配帧现读
    # (decision_state 的 plane/round_num);写入端=assembly._disclose_budget
    # 单一写点(商店执行回执位只比较不写)。键戳 ≠ 当前 (plane, round)
    # ⇒ v3_release_spent/v3_release_reason 清零并盖新戳。不复用
    # v3_release_round(W332b 泄息指令旧轮语义)。
    v3_disclosure_key: tuple[int, int] | None = None
    # ADR-0348 ↺ 扑满节点识别标记(T-115 复活为真写点,ADR-0580):写者
    # = mandate_v1 奖励帧判定位(shop/mandate 两栈同值幂等写,值源 =
    # kernel.cw_reward_node.is_piggy_reward_frame);读面 = engine 轮快照
    # /telemetry schema piggy_reward(恢复真值)。历史:ADR-0348 本体已
    # 随 decision_v2 删除,本字段曾为恒 False 死值(写者已死)。
    v3_piggy_reward: bool = False
    # 商店拒因遥测(shop.py 逐帧刷新;期望态即投影后真值)。
    cw4_shop_rejects: dict = field(default_factory=dict)
    # cw4 线级状态机(proof.LineState;_line_state 惰性建入口统一收口)。
    cw4_line_state: object = None
    # M1″ seam 门唯一写点(mandate.py;值源 = M1P_SEAM_VERIFIED)。
    cw4_m1p_seam_verified: bool = False
    # 换线排除集(cw4 换线判据族读;proof/line_switch 消费)。
    drought_excluded: set = field(default_factory=set)
    # 利息上限覆写注入面(cw_economy.cap_resolved_of_session 消费;
    # None=缺省回 DEFAULT_INTEREST_CAP)。
    cw4_cap_override: int | None = None

    # ===== M2 停摆续段缓存(T-82 必花臂重试风暴;段标识/结论闩/帧动作
    # token 三载体;为什么需要 = 商店/备战帧循环对「输入不变 ⇒ 拒绝不变」
    # 的腾席拒绝无记忆重推导,把一次停摆事件逐帧放大成 N 个事件帧——
    # 缓存命中帧跳过扫描且事件键不增,恢复 P60 诚实停摆的事件粒度语义)=====
    # 段序号。构成:会话态单调递增 int;置位:各段入口 +1(商店 visit
    # 开始[cw_op_buy_cards.run_buy_waves 入口=普通 visit 与发射帧仲裁段
    # 共用同一入口 / bridge.decide_shop_screen 入口=sim/replay]、备战期
    # 开始[生产 prep 访问循环入口]);比较:只作相等比较、不作阈值,
    # 递增值不承载任何决策量。段 = 停摆结论的输入不变性区间;跨段残留
    # token/闩按序号不等自动失效(域切换=必过段入口,跨域伪命中被同一
    # 比较拦截)。
    cw4_segment_serial: int = 0
    # M4 腾席拒绝结论闩:None=无结论。写入端=两决策位(shop/mandate 的
    # M2 停摆块)在「全量重推导得出腾席无候选」时写 (True, 当前段序号);
    # 有候选但不可逆护栏拒=非本结论,不写。命中判定要求闩序号 == 当前
    # 段序号(与 token 序号两道独立,任一不等即失效重推导)。
    cw4_m2_stall_latch: tuple[bool, int] | None = None
    # 帧动作记录 token(载体单一源):None=无记录。写入端=动作执行/投影
    # 层确认已执行后写 (动作型名 type().__name__, 当前段序号),物理写入
    # 位四处:①生产商店循环(cw_op_buy_cards.run_buy_waves 执行位);
    # ②sim-replay 驱动器(bridge.decide_shop_screen 投影位);③生产 prep
    # 循环主环(cw_screen_prep 决策循环 OpenShop/执行器分支合流执行位);
    # ④同文件备战席满破墙段执行位(_bench_full_break_round;破墙动作多为
    # SellBench/DeployMove ∉ 备战白名单恒不命中——登记防未来白名单扩集
    # 后此处成无人知晓的命中输入面)。调用方申报:备战期开店循环
    #(cw_screen_prep 开店分支逐动作调 decide_shop_action)无 token 写入
    # 无段序号置位 ⇒ 域内缓存恒不命中(保守端=现行为,读清单点覆盖
    # 无伪命中),收益面窄化,不接线。读清协议 = decide_shop_action 入口
    # 读取后立即清除(防重复消费);任何调用方首帧(槽空/型外/序号不等)
    # 默认全量重推导。
    cw4_frame_action_record: tuple[str, int] | None = None


    # ===== 账外补充·第二波(实施批收尾扫描按 §6.1 收编的策略侧动态
    # 属性;写入端均在 mandate_v1,消费面含执行侧经访问函数只读)=====
    # N3 闭环登记(mandate/shop 写,deploy/sim 只读):名 → 登记轮号。
    cw4_fuel_filler_stall_buys: dict = field(default_factory=dict)
    # M1″ pending 臂(mandate 写,deploy 消费后清 None)。
    cw4_m1p_arm_pending: object = None
    # M7 已穿相位(位面,轮) 元组。
    cw4_m7_equipped_phase: object = None
    # 必花域相位闩(同值重入防抖)。
    cw4_must_spend_phase: object = None
    # pop 槽否向理由留决策迹(D-lv7)。
    cw4_pop_slot_why: str = ''
    # 上一备战期线名快照(k_switched 实值化基准)。
    cw4_prev_line_name: str = ''
    # 近轮已卖名滚动账(P71 凑息卖去重)。
    cw4_recent_sold_names: list = field(default_factory=list)
    # 备战期开店闩(同一备战期内开店意图一次性)。
    cw4_shopped_phase: object = None
    # 素材滞留首见轮账(名 → 首见帧轮次)。
    cw4_stale_seen_rounds: dict = field(default_factory=dict)
    # 发射位闩相位(位面,轮) 元组。
    cw4_tools_phase: object = None
    # 本次商店访问已买名单(bridge 清账/op 落账跨层共享)。
    cw4_visit_bought_names: list = field(default_factory=list)
    # T-115 ②(b) 死金压库买入登记名集(会话级,跨轮存续;ADR-0580 Z1):
    # 写点 = shop ②(b) 臂发射位逐名登记;读点 = 凑息卖出资格集排除
    # (mandate.sell_hold_exclusions,prep 接线与 shop 消费位共用)。
    # 生命周期(F1 申报):**锁线定型时清空**——定型后 ④ 放行已收窄、
    # ③④ 静态排除集足以护持有面,残留登记只对 (b) 早期买入的燃料件
    # 造成过度禁卖(燃料 = 可逆变现资产,定型后应重新入凑息资格);
    # Early 期按名永久 = 「(b) 买入名永不回卖」设计意图,合成消耗后
    # 同名新副本罕见且代价仅利息机会损失。集载体 = set(无序,只做
    # 成员判定);局级清零由状态对象每局新建保证。
    cw4_dead_gold_bought_names: set = field(default_factory=set)

    # ===== scratch(原 session.memory 消解宿主;§6.3 纪律平移)=====
    # 策略实现层私有 scratch——临时变量不再逐个升字段。纪律:
    # ①键名加模块前缀防冲突;②生命周期 = 局级(状态对象每局新建自然
    # 清零),节点级清理归使用者;③不入 decisions 遥测;④高频共用/需
    # 类型与守卫的状态仍应升具名字段;⑤禁重复框架已提供的对局事实。
    scratch: dict[str, Any] = field(default_factory=dict)


def state_of(session: StrategySession) -> MandateState:
    """策略器侧状态读口:取 ``session.strategy_state`` 并收窄类型。

    None/异型(裸构造 session、第三方策略未覆写 create_state)→ 惰性
    冷建并写回(与原 cw_intention 惰性建同构;设计 §5.1 B4 兼容条款
    的实现面)。mandate_v1 链内统一经本函数消费状态对象。
    """
    st = getattr(session, 'strategy_state', None)
    if not isinstance(st, MandateState):
        st = MandateState()
        session.strategy_state = st
    return st


def ensure_strategy_state(strat: object, session: StrategySession,
                          initial_v2_state: tuple | None = None
                          ) -> MandateState:
    """sim 侧统一构建口(设计 §3.4-1):经被测策略工厂补建状态对象。

    - ``strat`` 按鸭子类型取 ``create_state``(注解 object:注入桩可无该
      钩子,工厂不可得 → 冷建兜底);
    - ``session.strategy_state`` 已是 MandateState → 直返(注入/进场态
      复用 session 通道);
    - 缺失 → 调 ``strat.create_state`` 工厂(与 live 同源生命周期);工厂
      不可得(注入桩)→ 冷建 MandateState 兜底。**config 实参传 None**
      (sim 面无 config 可注入)——``create_state`` 工厂契约 = 可忽略
      config/容忍 None(见 flow.CwFlowStrategy.create_state docstring),
      工厂实现禁读 config 取值;
    - ``initial_v2_state`` 非 None → 初始相位经状态对象初始化入口写入
      (原 sim 直写 session.v2_state 的替代;禁裸 setattr session)。
    """
    st = getattr(session, 'strategy_state', None)
    if not isinstance(st, MandateState):
        factory = getattr(strat, 'create_state', None)
        built = factory(None) if callable(factory) else None   # None 契约见 docstring
        st = built if isinstance(built, MandateState) else MandateState()
        session.strategy_state = st
    if initial_v2_state is not None:
        st.v2_state = initial_v2_state
    return st
