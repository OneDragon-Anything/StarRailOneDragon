"""货币战争 策略会话载体(分包期 0b 自 cw_strategy.py 下沉,§3.3-①c)。

`StrategySession` = 一局跨步状态载体(纯 dataclass 字段,零行为;
框架每局新建、局终销毁;策略读写)。下沉理由:cw_intention/cw_line_switch
等 kernel 判据层以类型注解消费本类,留 decision 桶会成 kernel→decision
断环边(§3.3-①c)。核对清单已过:类体逐字段核对无 app 引用——本模块
运行时 import 面仅 cw_effect_inventory/cw_performance(kernel 桶);
BuyExpect/XpLedger(PrepDirector,app 桶)仅注解引用,TYPE_CHECKING 承载,
不拖入运行时。

"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    ActiveEffectInventory,
)
from sr_od.application.currency_war.kernel.cw_performance import PerformanceTracker

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp
    from sr_od.application.currency_war.kernel.cw_state import BenchChar, GameState

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
    # ADR-0282(hp 三层·对账层,用户设计 2026-08-23):备战屏血量**最后真值**
    # (read_game_state 真值帧经 reconcile_hp 写;shop 开态血量区物理为空 →
    # 读不到=保旧沿用此值,**不是兜底 100**)。与 last_hp(结算屏真值,gated_hp
    # 新鲜度门消费)分工:本字段是备战现读域的对账锚。开局首真值帧前为 None。
    last_hp_real: int | None = None
    # last_hp_real 写入时的全局节点号((plane-1)*9+round,ADR-0431):
    # hp_trusted 帧龄门的坐标系锚——与当前节点号相等=同节点内沿用
    # (帧间无战斗,值必然未变 → 可信);跨节点=期间可能发生未观测战斗
    # → 沿用值降不可信。None=旧真值无节点锚(帧龄门按不可信保守处理)。
    last_hp_real_node: int | None = None
    # hp 下行拒信复现确认通道状态(ADR-0431):{'value': 拒信读数,
    # 'node': 首拒帧节点号, 'count': 连续复现真值帧数}。守卫拒信一次
    # 下行读数时建/刷新;误读确认(读数回旧值)或真掉血确认(连续
    # HP_SUSPECT_CONFIRM_FRAMES 帧低位)即清除。None=无活跃 suspect。
    hp_suspect: dict | None = None
    # r70 过渡框架(仙舟/列车,''=未定):双轨期买/上/卖三侧的统一临时 target
    # (cw_transition.pick_framework 按 board+bench+shop 持有选定;update_target 每轮刷新)。
    transition_framework: str = ''
    # 迁移迁移批 2(方向层接管)(方向层接管) 方向层接管(`w628_migration_b2/`):committed 权威 = cw_intention.committed_authority
    # 派生(读端 = decision_v2.prep_brain.committed_from);本字段降级为
    # 兼容残留——读点已归零(grep 守卫锁),写端(老栈 update_target/
    # shop 循环态/回放恢复)随老栈退役退役批(ADR-0466/0467/0469) 清除。
    dual_track_phase: bool = False
    # 最近 node_type 真值(r7 review P0-①:商店开态帧节点行被遮 → read_node_type 恒 None,
    # boss 判定全死码实证。Director 在
    # shop 关态 heavy 读到时写此;shop.py 喂决策前拷入 —— 仿 last_hp 模式)。
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
    # ADR-0368(迁移审计 w169(git 历史)):plane_node_table 是哪位面的表(每位面首帧重写时更新;
    # 同位面内不覆写)。None=尚未写过。修生产 write-once 守卫使 P2 的 7 槽
    # 真值表永不落盘(P1 陈旧表整局滞留,nodes_of_plane/日程在生产 P2 恒 9)。
    plane_node_table_plane: int | None = None
    # ADR-0368(迁移审计 w169(git 历史)):本局已揭晓的位面轮数序列(随 plane_node_table 每位面
    # 首帧 append;P1=9/P2=7/P3 进表即自适应)——cw_plane_table.schedule_of 的
    # 真值源(DP 位面日程);跨位面仍可知历史位面真值(P3 期知 P2=7)。
    plane_lengths_seen: list[int] | None = None
    # r363(审计 P0-2):左移推断的轮次锚——同轮多次 probe 不重做
    # 左移(防 current 超前一位写下一节点类型)。
    nodeseq_probe_anchor: tuple | None = None
    # r364(局47 死循环):腾席链 b 的 gold 真值等待计数(>1 次无
    # 进展 → 放弃等待落链 c;环入口清零)。
    free_bench_gold_wait: int = 0
    # 上回合结算 streak(带符号 连胜+/连败-;on_round_end 从结算「连胜×N」写)。给下回合 economy C 杠杆读
    # (连胜保连胜 / 连败 fold;fixture 核实 2026-08-11:语义在前缀,备战 read_streak 无方向故改结算源)。
    last_streak: int = 0
    # r93 审计 46336415:腾席链 DeployMove 失败记忆(char_id → 失败计数)。同一角色拖拽被
    # 游戏拒(同名在场/行限制等预检漏网的落点)→ 重试同目标 = 白烧环步(第14局 r9 藿藿
    # 5 连败实证);失败过的角色跳过,优先下一个候选(拖失败本身不消费 bench,下轮还在)。
    deploy_fail_counts: dict = field(default_factory=dict)
    # 出战发射连败计数(prep_actions._start_battle 写;**跨环重入存活** —— 环级计数随
    # Director 重建清零,挡不住 round_fail → 外环重入的僵尸循环)。只计「未落地」型
    # 失败(激活窗口重发后仍不落地 = 窗口输入通道死);发射成功清零。达
    # PrepActionExecutor.LAUNCH_DEAD_LIMIT → 停机留证(hook:cw_launch_dead)。
    launch_dead_streak: int = 0
    # level 单调守卫(read_level OCR 间歇误读 5/6→4;等级局内只升不降,读出<上次=误读用上次)。新局默认 0。
    last_level_obs: int = 0
    # 防 new RunMegastarNode instance 重置 instance flag → re-click toggle 反选 → confirm 无候选 → 卡死)。
    megastar_candidate_clicked: bool = False
    # 已持有投资策略(局中选,可多张;live 修复 2026-08-15:宿主=session 持久,read_game_state
    # 拷贝到 state 供 _refresh_cap 等消费 —— 原接线只加 GameState 字段而 handler 写 session,
    # 停机隔离期从未 live 跑过,首跑暴露 AttributeError)。
    active_strategies: list[str] = field(default_factory=list)
    # 在场效果清单(`w612_effect_inventory/` 骨架批):spec 注册表在 cw_investments.STRATEGY_EFFECTS,
    # 机制 = cw_effect_inventory.ActiveEffectInventory(纯数据+读端)。写端现状仅
    # 升级挂点(prep_actions._level_up);选卡/进节点/结算挂点接线归后续批。
    # 本批零决策消费——任何决策路径不读本字段(`w612_effect_inventory/` 交付门)。
    effect_inventory: ActiveEffectInventory = field(
        default_factory=lambda: ActiveEffectInventory())
    # owned 穿戴池快照(迁移审计 w148(git 历史),ADR-0358,迁移审计 w92(git 历史) 修法 A):EquipAll 每轮 read_equips 后写
    # (仅穿戴类,工具类过滤同 equip_all._TOOL_CATEGORIES);_pseudo_state 拷入决策
    # state.equips → decisions 遥测可见。修「持有面有读点、无写链、决策/遥测全盲」
    # (迁移审计 w92(git 历史) 实证:3,061 条 decisions 里 state.equips 0 条非空)。
    last_owned_equips: list[str] = field(default_factory=list)
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
    # (r7 pivot 冷却宿主字段 pivot_cooldown_until 与 r20 drought 弃线名单
    #  drought_excluded 已随 default 栈退役删除(唯一写端=default update_target);
    #  消费侧 getattr 带兜底,maybe_pivot 挂账层/cw_line_switch 残余读点惰性化)
    commit_signals: object = None   # ADR-0209 CommitSignals(定型信号累积器;惰性建——default_factory 会引环形导入,update_target 首调时建)
    stash_comp: object = None       # ADR-0209 双轨期信号领先线 comp(囤牌方向;update_target 每回合刷新)
    commit_flip_pending: bool = False   # ADR-0209 定型边沿(卖散上限放宽;decide_prep 一次性消费)
    focus_factions: set[str] = field(default_factory=set)   # ADR-0209 flex 收敛白名单(已铺 flex top2)
    last_candidate_scores: dict[str, float] = field(default_factory=dict)   # 选线轮的 top-3 实际排序分(r6 遥测补)
    last_candidate_scores_round: int = -1              # 分数轮次戳(shop 侧判陈旧清空)
    _supply_refresh_used: bool = False                 # 补给刷新 1 次已用(r2#2 跨实例)
    # —— 策略 v2 扩展态——正式字段(评审 B-bg:动态 setattr 会在
    # 「session 新建而 on_match_start 未走」路径崩;且 asdict/telemetry
    # 看不见动态属性——升正式,r3 review④ 同判例)——
    # 默认值 None(评审 B1:default 局遥测 v2_* 应全空可区分——
    # 不能用元组默认,否则 default 呈现假 economy 污染 AB 对拍)
    # ⚠️ ADR-0336:LineStrategy 已删——v2_state/locked_line/bridge_id/
    # v2_prev_hp 是 v1 遗留字段,decision_v2 不写(恒 None/空),保留
    # 仅作遥测 schema 与历史回放兼容;v2_round_*/v2_seed_bought/
    # v2_remedy_used 被 decision_v2 消费(保留);v2_ever_full_interest
    # 自 迁移审计 w119(git 历史)(ADR-0347,E6 latch 退场)起仅 default 栈消费(v2 走
    # ev.levelup_ev_authorized 总账)。
    v2_state: tuple | None = None
    # cw_phase_machine 状态元组(None=未初始化;v1 遗留,ADR-0336)
    locked_line: str | None = None                     # 锁定线 id(None=未锁;v1 遗留)
    bridge_id: str | None = None                       # 当前桥线 id(None=无;v1 遗留)
    # r406(ADR-0266,压测经济批 [12]/①残差):本局**曾达满息**(时点金≥50)
    # 标志。迁移审计 w119(git 历史)/ADR-0347 起 decision_v2 不再消费(E6 latch 随 [12] 门
    # 收编 EV 总账退场);default 栈仍读写(冻结)——字段保留。
    v2_ever_full_interest: bool = False
    # r246:普通战斗败检测的上一轮 HP(v1 遗留,ADR-0336 后无人写)
    v2_prev_hp: int | None = None
    # r408(ADR-0267,F1 振荡):同轮已买集(round-scoped)——
    # key=(plane, round_num),轮变更时由 decision_v2.decide_prep 重置;
    # 卖通道对集内卡名禁卖(3合1 让位豁免见 decision_v2.discipline)。
    # 重启/重放丢 session → 空集保守(只失去互斥,不引入新行为)。
    v2_round_key: tuple | None = None
    v2_round_bought: set[str] = field(default_factory=set)
    # r408 对称臂:同轮已卖集——engine_seed 对集内卡名禁买(防
    # 「卖通道刚卖→st2 见未持有→同 call 买回」的缩幅永动机,1 对/轮)。
    v2_round_sold: set[str] = field(default_factory=set)
    # ADR-0289 §5 裁决(红项 127/300,ADR-0294 件1):engine_seed
    # 购入轮登记——char_id → ((plane, round_num), 同轮份数);卖通道
    # ≤2 轮年龄豁免(decision_v2.discipline 种子年龄)的单一数据源。
    # 同轮 ≥2 份=3合1 素材语境豁免(镜像 check_engine_seed_not_
    # resold);旧 session 反序列化缺字段 → 空 dict 保守(只失去豁免)。
    v2_seed_bought: dict[str, tuple[tuple[int, int], int]] = \
        field(default_factory=dict)
    # —— 决策框架 v2 载体批(迁移审计 w35(git 历史),ADR-0309)扩展态:意向分层/演进/纪律 ——
    # (新载体 decision_v2 的跨步状态;None=未初始化——旧策略局全空可区分)
    v3_intention: object = None      # cw_intention.IntentionState(锁线/撤销状态机)
    v3_evolution: object = None      # cw_evolution.EvolutionState(中断恢复/谷底回滚)
    v3_hoard: object = None          # cw_intention.HoardTarget(囤货目标集,买侧唯一消费面)
    v3_core_names: set = field(default_factory=set)   # 意向核心名集(line_carry 标签裁决)
    v3_mode: str = ''                # 本轮模式('economy'|'war';纪律族每轮写)
    v3_alarm: object = None          # discipline.BloodAlarmTracker(掉血三臂)
    v3_pending_rollback: object = None   # 谷底回滚待发动作(on_round_end→下轮 decide_prep)
    v3_prev_hp: int | None = None        # 掉血三臂的上一节点 HP(结算真值链)
    v3_last_intention_event: str = ''    # 意向事件去重(判读日志锚)
    v3_intention_key: tuple | None = None   # 意向状态机驱动轮键(段级重入守卫)
    # 血预算停手·停升级拒付计数(设计件 12/ADR-0448):决策层拒付披露
    # (arbiter 约束/remediation 两臂写入;局首 on_match_start 清零)
    v3_blood_budget_rejects: int = 0
    # 血预算停手·搜索型刷新停付拒付计数(设计件 12 §2.3-P1-c/§3.2/
    # ADR-0451):refresh 收尾授权前置拒付披露(arbiter 写入;
    # 局首 on_match_start 清零;模式对齐上行停升级拒付计数)
    v3_blood_budget_refresh_rejects: int = 0
    # 血预算停手·终止分支位面内触发闩(设计 W659 v2 §2.3 R7;ADR-0469):
    # 本位面首次 S0≤ε 触发后恒释放(防 S0 邻域抖动半释放);位面切换由
    # v3_terminal_release_plane 键控清零。账本决策位(R4)消费面=
    # discipline.terminal_release_bit(单一址),检查器禁复算 S0。
    v3_terminal_release: bool = False
    v3_terminal_release_plane: int | None = None
    # 换线存活门决策位(W665 DESIGN v2 §3-2/R3;帧级:坐标系=本轮意向
    # 驱动帧,update_intention 每帧入口清零、cw_intention._switch_gate_open
    # 评估点写入;本轮未做换线辖域评估的帧=False。消费=sim 账本行/
    # 生产 decisions 行透传,检查器只做位一致性核验、禁复算门判据式):
    # - v3_line_gate_blocked = 拦截位(门拦=True;仅门开时有「拦」语义)
    # - v3_line_gate_cf_blocked = 反事实判定位 P(f)=[R<need](off 臂=
    #   gate_counterfactual 反事实记账;on 臂=门判定本身,不重复算)
    v3_line_gate_blocked: bool = False
    v3_line_gate_cf_blocked: bool = False
    # 换线门滞回闩(W665 DESIGN v3 §3-3 R-A;门感知滞回,取代已被 W683
    # 推翻并废弃的 N=2 计数回锁):本位面首次门拦截置闩 → 闩置位帧一次性
    # 回锁原线(恢复 prev_lock_layer)→ 闩存续期(同位面)抑制撤销出口①②
    #(locked=吸收态,砍断周期环驱动源)。坐标系=位面内闩(与
    # v3_terminal_release 同型):置位时记 v3_line_gate_latch_plane,
    # update_intention 入口检测位面切换清零,并同步清 tracks miss_count
    # 与 ist.prev_lock_layer(陈旧断供证据不跨位面)。
    v3_line_gate_latch: bool = False
    v3_line_gate_latch_plane: int | None = None
    # `w224_handoff/`/ADR-0399:P2 承接快照(decision_v2.handoff.HandoffSnapshot,
    # 纯观测零行为)——plane>=2 本位面首帧 decide_prep 入口算一次;
    # None=未进 P2/未计算。v3_handoff_plane=已采样位面(同位面不覆写)。
    v3_handoff: object = None
    v3_handoff_plane: int | None = None
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
    # ⚠️ 显式种子化(w910_sim_determinism/REPORT):default 禁止 OS 熵种子
    # (原 default_factory=random.Random 无参构造 = 每次构造取 urandom,裸
    # 构造点得到不可复现流)。现 default=固定种子 0 的独立实例:确定
    # 性由构造保证;真实随机面由消费方显式注入——生产 run loop 按
    # cw_config.strategy_seed 覆盖(operations/battle_loop.py),sim 引擎
    # 从局 seed 派生(sim/engine_p1.py)。当前决策层无 rng 消费点
    # (grep 证),本字段是公开随机接口的种子契约锚。
    rng: random.Random = field(default_factory=lambda: random.Random(0))
    performance: PerformanceTracker = field(default_factory=PerformanceTracker)  # 观测反馈(双侧 OCR)
    # ⚖️ memory/plane/round_num/pending_deploys 已删(2026-08-16 review D1/D2/TOP4:0 读者;
    # 进度真源 = session.last_state(每回合框架刷新);策略私有 scratch 无消费者)。
    # 简报词缀(对局开始 debuff/boss 词缀;loop __init__ 从 ctx.cw_briefing_affixes copy;mechanics_fit 输入)
    briefing_affixes: list[str] = field(default_factory=list)
    # 变宝为废·位面首次合成判定消耗记账(kernel/cw_junk_first.py 消费;
    # 机制真值=affix_effects_data「每个位面开始时,首次合成的进阶装备会有
    # 50% 的概率变成垃圾袋」→ 每位面判定一次。坐标系=位面序;None=未消耗,
    # -1=位面不可读态下已消耗(整局一次降级哨兵);写入端 =
    # junk_first_allocation 发射牺牲合成或推迟后记账当前 state.plane)。
    junk_first_done_plane: int | None = None
    # 本局职级(A1..A8;StartCurrencyWarMatch 难度确认屏读 → ctx.cw_selected_difficulty → loop copy 到此;
    # 策略层填 state.selected_difficulty → effective_hp_threshold D-32 保血阈值;3.5.1 接线)
    selected_difficulty: str = ""
    # 敌人难度数值(简报「敌人难度N」读 → ctx.cw_enemy_difficulty → loop copy;read_game_state 填 state;3.5.2)
    enemy_difficulty: int | None = None
    # 位面序 boss 真值(3 位面 boss 名;写入端 = battle_loop 首个稳定备战帧 copy 自
    # 简报 LCS 清洗读数(`w522_briefing_rulings/`,ADR-0397 勘误:简报排列=位面序)+ CollectPlaneIntel
    # 实采(接管场景重采/对账真值源);boss_fit 输入。
    # 元素可为 None = 该位面徽章态采不到身份(迁移审计 w221(git 历史)/ADR-0398)——**保位勿滤**,
    # 滤掉会让后续位面名字左移错位)
    briefing_bosses: list[str | None] = field(default_factory=list)
    active_env: str = ""
    # deploy/sell 同步待补(deploy=DeployBench 位置式 / sell=_handle_bench_full 位置式,后续接)。
    tracked_bench: list[str] = field(default_factory=list)
    tracked_bench_chars: list[BenchChar] = field(default_factory=list)
    tracked_deployed: list[BenchChar] = field(default_factory=list)
    # 买牌单元期望态(prep_director.BuyExpect;`w536_merge_expect/` 引入)。坐标系 = 哪次购买:
    # 一次 RunBuyPhase 单元的购买意图经 compute_buy_expect 建的「单元执行后
    # 应然态」(bench/deployed 槽位表)。取值时机 = 购买意图落账——shop.py
    # 单元收尾(含卖出/未识别牌则不建,保持 None)写入;消费 = PrepDirector
    # 主环下一轮 heavy 定型帧对账(buy_expect_mismatch)后立即清回 None,
    # 跨单元不残留。None = 无挂起期望。此前为动态属性(单元收尾暂存、
    # getattr 消费,`w536_merge_expect/` 受文件面限制未落声明),升正式字段后 asdict/telemetry
    # 可见且读写两端免 getattr 兜底(r3 review④ 同判例)。
    pending_buy_expect: 'BuyExpect | None' = None   # 注解字符串(app 桶 prep_director 类型,kernel 零 app import)
    # 经验期望账本(prep_director.XpLedger;纯记账+对账,零决策)。此前为动态
    # setattr 属性(_xp_ledger 惰性建),升正式字段后 asdict/遥测可见且读写两端
    # 免 getattr 兜底(pending_buy_expect 同判例)。坐标系/取值时机/写入端 =
    # XpLedger 字段定义注释(prep_director);None = 本局未锚定(账本未建)。
    xp_expect_ledger: 'XpLedger | None' = None       # 同上
    # —— 预算-回执契约(w921_rd_design DESIGN 批1;开关
    # spend_receipt_gate_enabled 默认关)——
    # v3_spend_auth:本帧授权包快照(attach_spend_authorization 写;
    # {auth_id(轮标识,跨轮唯一/轮内多段共用), level_up, refresh_budget,
    # buy_budget, buy_obligation(许可型买授权=False,义务型保留位),
    # premises, suppressed},suppressed=产出侧拒发的前提 token 列表)。
    # 开关关恒 None。
    v3_spend_auth: dict | None = None
    # v3_posture_receipt:执行层支出回执(SpendReceipt.as_dict;
    # 每次仲裁收口覆写,轮内多段 last-wins)。开关关恒 None。
    v3_posture_receipt: dict | None = None
    # v3_posture_unfulfilled:对账门「授权未兑现」声明({auth_id,
    # channel, reason, channels, action};action=allocator/crisis_release/
    # downgrade——分配器辖域/危机帧只记录,常规帧 downgrade=姿态
    # tag 降级+显式声明)。**帧级全量重算语义**(w943_audit5 P1-1 复位
    # 契约):每次仲裁入口 attach 无条件清 None,段尾 reconcile 覆写
    # ——「无未兑现帧=None」承诺逐帧成立,无跨轮/跨帧滞留。
    # 开关关恒 None。
    v3_posture_unfulfilled: dict | None = None

