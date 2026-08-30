"""遥测 schema:序列化纯函数与账本行 dataclass(自 cw_telemetry 拆出,分包期6)。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sr_od.application.currency_war.kernel.cw_intention import _to_jsonable
from sr_od.application.currency_war.kernel.cw_state import (
    Action,
    GameState,
    _bench_char_cost,
    sell_refund,
)

# 默认 replay 目录单一源已下沉 kernel/cw_observe(分包期 3:sim 桶消费它而
# sim 禁依 telemetry;本模块经上行 import 取用)。replay 序列化符号
# (_to_jsonable/serialize_intention)同理下沉 kernel/cw_intention。
SCHEMA_VERSION: int = 1   # 决策迹 schema 版本(字段名稳定;改 schema 升版本号)



# ===== 序列化(dataclass → JSON-safe dict)=====

def salvageable_1star_value(state: GameState) -> int:
    """出口财富口径的「可回收 1★ 值」:手上(deployed+bench)全部 star==1
    件的卖出回金和。

    - 口径出处:P10④「出口『财富』= 袋子金 + 可回收 1★ 值」——
      ``docs/game/currency_war/research/proofs/p10-exit-gold-floor.md``
      §④ 与「对实现的检验点」3(判读防「袋穷板富」误读:出口金低但
      本值高 → 钱在卡上,非经济病;两字段必须并读)。
    - 计算式:Σ ``cw_state.sell_refund(1, cost)``。1★ 卖出全额退、无
      手续费(sell_refund 单一源),故值 = Σ cost;费用单一源 =
      ``cw_state._bench_char_cost``(char_id 未识别 → 3 中费保守估)。
    - 件集边界:只算 1★(2★+ 是沉没通道——合成已花成本,卖出还有
      手续费,不构成「活期金」);deployed 与 bench 并集,空槽 None
      跳过。
    - 纯函数契约:只读 state、零行为消费(挂载点见
      ``TelemetryRecorder.record_decision`` 的 handoff 富化处)。
    """
    total = 0
    for d in list(state.deployed or []) + list(state.bench or []):
        if d is None:
            continue
        if int(getattr(d, 'star', 1) or 1) != 1:
            continue
        total += sell_refund(1, _bench_char_cost(d))
    return total



def serialize_state(state: GameState) -> dict[str, Any]:
    """GameState → JSON-safe dict(剔除大且无决策价值的字段由调用方按需;默认全量)。

    ADR-0392:``deployed`` 槽位表 → **紧缩占用序**落遥测(None 空槽剔除)——
    下游视图(rounds/win_features/replay)零迁移,占用数=len 语义不变。
    """
    out = _to_jsonable(state)
    _dep = getattr(state, 'deployed', None)
    if isinstance(_dep, list):
        out['deployed'] = _to_jsonable([d for d in _dep if d is not None])
    return out



def serialize_action(action: Action) -> dict[str, Any]:
    """单 Action → JSON-safe dict(带 type 标签,便于复盘识别)。"""
    d = _to_jsonable(action)
    d["__type__"] = type(action).__name__
    return d



def p1_pair_label(ist: Any) -> str:
    """P1 配方对 → 遥测标签串('A+B' 体系键串;空窗/无意向 = '')。

    - 来源 = ``cw_intention.IntentionState``:配方锁局取 ``p1_pair``
      (锁定产物),①资格锁局取 ``transition_pair``(受保护副方向,
      与 scoring._vd_p1_pair 同式优先序);两字段同口径派生、同帧至多
      一侧非空,故按 p1_pair 优先取其一。
    - 体系键域/二元组语义见 cw_intention.IntentionState.p1_pair 注释;
      tuple/None/非 dataclass 输入一律安全退化空串(纯观测不阻塞环)。
    """
    pair = tuple(getattr(ist, 'p1_pair', ()) or ()) \
        or tuple(getattr(ist, 'transition_pair', ()) or ())
    return '+'.join(str(k) for k in pair)



def append_jsonl(path: Path | str, payload: dict[str, Any]) -> None:
    """append 一行 JSON 到指定 .jsonl 文件(ADR-0273:兜底回填/常规写共用,不依赖 recorder 单例)。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')



# ===== trace 数据结构(schema 稳定)=====

@dataclass
class DecisionTrace:
    """单回合决策迹(decisions.jsonl 一行)。schema 稳定,新字段末尾追加且可选。"""
    schema_version: int = SCHEMA_VERSION
    ts: str = ""                                  # ISO 时间戳(record 时填)
    run_id: str = ""                              # 一次 run 的 id(调用方传;join key)
    difficulty: str = ""                          # A1..A8(调用方传)
    round_num: int = 0                            # 位面内轮次
    plane: int = 0
    state: dict[str, Any] = field(default_factory=dict)        # GameState 快照
    target_comp: str = ""                         # 选中的 target comp 名
    candidate_scores: dict[str, float] = field(default_factory=dict)  # {comp_name: comp_score}
    eval_breakdown: dict[str, float] = field(default_factory=dict)    # target comp 的特征分解
    actions: list[dict[str, Any]] = field(default_factory=list)       # action plan(每项带 __type__)
    hp: int = 0                                   # 决策时 HP(冗余于 state,便于快速筛)
    hp_readable: bool = True                      # hp 真读到?(False=读不到;ADR-0282:此时 hp=沿用 last_hp_real,开局无真值才是 100 兜底)
    gold: int = 0                                 # 决策时 gold(冗余,便于 gold 轨迹)
    gold_readable: bool = True                    # gold 真读到?(ADR-0282:prep_director「gold 不可信」日志升级为字段,对齐 hp_readable)
    # —— live 观测扩容(strategy/05_observation;全部可选,回放/影子对齐)——
    active_strategies: list[str] = field(default_factory=list)   # 持卡(台账/效果解回放)
    dp_posture: dict[str, Any] = field(default_factory=dict)     # 影子 DP 姿态(tag/level_up/refresh_budget/v)
    ledger_fingerprint: str = ""                  # 台账指纹(效果感知解回放对齐)
    # —— r101 session 态快照(redesign/102 前提改造:回放 harness/快照回归库需要完整
    # 决策输入;缺这些,单帧重放 plan 会系统性偏差——session 态决定 decision_target
    # 走哪条路线/攒息门/定型判定)。全可选,旧记录缺省 None 不破坏 schema。
    sess_framework: str = ""                      # transition_framework(配方路线)
    sess_dual_track: bool | None = None           # 双轨期(定型与否)
    sess_drought: int | None = None               # target_drought(断供计数)
    # (sess_pivot_cooldown 已随 pivot 冷却宿主字段退役删除;旧语料该键经
    #  extra.get 读缺省 None,schema 兼容)
    sess_commit_scores: dict[str, float] = field(default_factory=dict)  # CommitSignals 累积分
    sess_active_env: str = ""                     # 已选投资环境(portal 偏置源)
    # —— 策略 v2(LineStrategy)字段(r226;redesign §6 遥测扩展:
    # 模式/锁线/桥——AB 对拍与三层置信的数据源)——
    strategy_id: str = ""                          # 本局策略 id(B2:分组键)
    v2_mode: str = ""                             # economy/war(滞回当前模式)
    v2_locked_line: str = ""                      # 锁定线 id(""=未锁)
    v2_bridge: str = ""                           # 当前桥线 id(""=无)
    # r359(回放忠实化,ADR-0231):v2 相位机元组(应急/追赶 latch
    # 全量)——重放 decide_prep 分支忠实还原的缺失件。可选,旧记录
    # 缺省 None;list 形态 = v2_state 元组逐位。
    sess_v2_state: list | None = None
    # —— 迁移审计 w114(git 历史)/ADR-0346 相位影子观测(经济循环总模型步①;零消费):
    # phase(FORM/HOARD/SPEND 派生相位)/form_ok(三件套谓词,裁决后
    # 无等级项)/form_score(上场阵容 rung 副指标,∈[0,1])。可选,
    # 旧记录缺省不破坏 schema。
    phase: str = ""
    form_ok: bool = False
    form_score: float = 0.0
    # ADR-0343 成型停手态(层2 写;检查器豁免/判读锚点)——补挂
    # DecisionTrace 字段:shop/prep_director 均已在 extra 传
    # 'formed_stop',但 recorder 映射缺失导致该键被静默丢弃
    # (迁移审计 w114(git 历史) 影子批接线时发现的既有缺口,随批补上;旧记录缺省 False)
    formed_stop: bool = False
    # —— 迁移审计 w119(git 历史)/ADR-0347 授权依据 trace(经济循环总模型步②「切授权」):
    # dp_posture=当轮 DP 日程表姿态 tag(存息/升级/D 预算;""=查询
    # 失败/default 栈)。EV 放行值在 decisions 行 log 的 ev_auth 键
    # (arbiter 执行 log)。可选,旧记录缺省不破坏 schema。
    dp_posture: str = ""
    # ADR-0348 ↺:扑满节点识别(过热局 reward 帧;②b 观测/实机建档
    # 数据面——识别≠深花授权)。可选,旧记录缺省 False。
    piggy_reward: bool = False
    # —— 迁移审计 w146(git 历史) v3 意向状态(cw_intention.IntentionState 全量序列化;
    # ADR-0336 后 v2_locked_line/v2_mode 恒空,锁定真值在此)——
    # None=无意向状态机(default 栈);dict 且 phase='unlocked'=有意向
    # 未锁;phase='locked' 时 locked_comp=锁定目标(COMP_LIBRARY 套名)。
    # 可选,旧记录缺省 None 不破坏 schema。
    v3_intention: dict[str, Any] | None = None
    # —— `w224_handoff/`/ADR-0399 P2 承接快照(纯观测;plane>=2 本位面首帧
    # decide_prep 入口算一次的七维向量+派生档位,decision_v2.handoff.
    # HandoffSnapshot.as_dict)。None=未进 P2/旧记录;仅 P2 首轮行非空。
    handoff: dict[str, Any] | None = None
    # —— P1 配方对平铺观测(cw_intention 配方锁产物;判读上游)——
    # 取值 = 本 record 调用时点的 session.v3_intention 配方对(非空
    # IntentionState.p1_pair,次选 transition_pair),体系键以 '+' 连接
    # (同 cw_intention last_event 'p1_pair:' 标签风格);''=未锁/空窗/
    # 无意向状态机。平铺目的是 P1 备战步进行(decisions 行)不用解析
    # 嵌套 v3_intention 即可读锁定产物。可选,旧记录缺省 '' 不破坏 schema。
    sess_p1_pair: str = ""
    # —— `w603_telemetry_wiring/` 披露键序列化(血预算停手计数/末窗降格触发面/经验账本)——
    # 三个 session 披露键此前「有写点、无遥测落盘」(decisions.jsonl 全文检索
    # 零命中,判读盲区)。接出点=recorder 统一自 _CTX_MATCH_REF 的 session 取
    # (shop.py 的 extra 通道不动;record_outcome 板深快照同款模块槽先例)。
    # None/缺省 = 无 match 注册(离线/测试)或取值失败,旧 schema 不破坏。
    # 血预算停手·停升级拒付计数(session.v3_blood_budget_rejects 透传;
    # 写入端=arbiter/remediation 拒付面,局首清零)。
    sess_blood_budget_rejects: int | None = None
    # 血预算停手·搜索型刷新停付拒付计数(session.v3_blood_budget_refresh_rejects
    # 透传;写入端=arbiter refresh 收尾,局首清零)。
    sess_blood_budget_refresh_rejects: int | None = None
    # 血预算停手·终止分支决策位(discipline.terminal_release_bit(session,
    # plane) 单一址透传;设计 W659 v2 §5.1 R4;ADR-0469)。None=无 match
    # 注册(离线/测试)。
    sess_terminal_release: bool | None = None
    # P1-a 末窗支出降格触发面:取值=本 record 调用时点按 state +
    # DEFAULT_REGISTRY + match session(闩位含位面内触发闩,ADR-0469)
    # 现算(生产 DecisionV2Strategy() 缺省即 DEFAULT_REGISTRY;sim A/B
    # 注入臂行不带此语义保证,判读按 strategy_id 分栈)。None=现算失败/
    # 依赖缺失。
    p1_downgrade_active: bool | None = None
    # 经验期望账本快照(session.xp_expect_ledger=prep_director.XpLedger 正式
    # 字段,此处平铺 dict 便于判读;None=未锚定/无账本)。
    xp_expect_ledger: dict[str, Any] | None = None
    # —— `w611_econ_cycle/` 储备/义务披露(经济循环总模型;ADR-0445 实机验证队列
    # 「死时带金/闲置金」判读的帧级数据源;接出点同 `w603_telemetry_wiring/` 汇点)——
    # None/缺省 = 无 match 注册或 decide_prep 未跑(离线/测试/default 栈)。
    # 储备线 R*(=息线+窗口排程升级费;session.v3_reserve_cap 透传)。
    sess_reserve_cap: int | None = None
    # 溢余 (g−R*)+(义务压力原料;闲置金判据=本字段的帧均值)。
    sess_reserve_overflow: int | None = None
    # 当轮 release 义务预算(金;0=无 release 帧或零预算结转帧)。
    sess_release_budget: int | None = None
    # 义务来源(''/'flip'/'third_path'/'reserve_admission';判读兑现率分域)。
    sess_release_reason: str | None = None
    # 位面 2 支出授权·拦断面普查(W757 v3 设计 §3.5;ADR-0481):金堆积
    # 候选帧逐帧拦截原因枚举(session.v3_p2_auth_intercept 透传;取值
    # ''/t1_locked/t2_form/no_t3/t4_gold/v6_active/authorized/
    # hoard_invalid;''=开关关或非 P2 无授权语义)。协议 M0 分层归因
    # 唯一数据源;None=无 decide_prep 写点(离线/测试/default 栈)。
    sess_p2_auth_intercept: str | None = None
    # 位面 2 支出授权·窗级水位观测(W757 v3.3;协议 V4 M0b 判读数据源):
    # 滚动 3 备战帧窗的 {window_start_gold, window_end_gold, window_income,
    # window_spend, rounds}(session.v3_p2_auth_water 透传;plane==2 全帧
    # 记账、开关无关,对照臂同源;None=无 decide_prep 写点/非 P2/离线)。
    sess_p2_auth_water: dict | None = None



@dataclass
class OutcomeRecord:
    """单回合观测结果(outcomes.jsonl 一行)。对应 cw_performance.RoundOutcome + join key。"""
    schema_version: int = SCHEMA_VERSION
    ts: str = ""
    run_id: str = ""
    round_num: int = 0
    plane: int = 0
    node_type: str = ""
    comp_tag: str = ""
    intentional_fold: bool = False
    hp_after: int = 0
    hp_confidence: float = 1.0
    enemy_hp_after: int | None = None
    damage_dealt: int | None = None
    killed: bool | None = None
    progress_delta: int | None = None   # 结算屏「挑战进度 ±N」(2026-08-18:胜负+扣血真值,输轮也记)
    streak: int | None = None           # 连胜/连败带符号(r68:RoundOutcome 有此字段但序列化丢弃 → 补)
    # —— r339 板深快照(板深→胜率模型校准数据源;复盘发现 sim
    # 天花板 8%>=60 vs 实机 3/3 达标的矛盾根因=模型缺板深机制,
    # 而逐轮板面×掉血对就是拟合数据):战前板面+上阵深度。
    board_before: dict[str, int] = field(default_factory=dict)   # 战前 {阵营:人数}
    bench_count: int = 0               # 战前 bench 数(板深第二维)
    # —— 迁移审计 w28(git 历史)(行来源标记,镜像 RunSummary.source/ADR-0273 惯例):''=结算屏真值行;
    # 'recovered'=relaunch 残留结算屏(启动宽限内首见,round_num 已按屏面「X-Y」
    # 尽力校正,训练侧可剔);'synthetic_supply'=补给节点合成行(无结算屏节点的
    # 遥测补行,hp 用 last_state 快照非屏面真值)。
    source: str = ""
    # —— 迁移审计 w253(git 历史) boss 身份采集(迁移审计 w244(git 历史) 数据缺口补齐)——
    # session.briefing_bosses 全量快照(位面序 3 元素;None=该位面徽章态采不到
    # 身份,**保位勿滤**——滤掉会让后续位面名字左移错位,迁移审计 w221(git 历史)/ADR-0398)。
    # boss Δ 双峰归因的数据源(迁移审计 w244(git 历史) 结论④:schema 无 boss 身份→不可分层)。
    # 记录时点快照,行间可能因实采进度而异;旧记录无此字段(读取端 .get 容忍)。
    boss_names: list[str | None] | None = None
    # 本局职级(A1..A8;session.selected_difficulty 快照,迁移审计 w244(git 历史) 难度分层缺口)。
    # ''=未采/旧记录缺字段。
    selected_difficulty: str = ""
    # 简报词缀(session.briefing_affixes 快照,迁移审计 w244(git 历史) affix 分层缺口)。空=未采。
    enemy_affixes: list[str] = field(default_factory=list)
    # —— 迁移审计 w306(git 历史) 补给选择快照(仅 source='synthetic_supply' 行携带):补给节点选定+
    # 确认时的 {char, equip, has_diamond, refreshed, gold}——choices/效果归因数据源
    # (治疗/装备生效判读原无法挂回补给轮;rounds 视图 P1 r5 全缺的语义补齐)。
    # refreshed=session._supply_refresh_used 时点值(该次确认前是否已刷新重掷);
    # gold=完成时点 last_state.gold(gold_readable=False 缺省不写,不冒认真值)。
    # W306c:options=[{char,equip,has_diamond}...] + n_options=实际识别列数
    # (动态探测,通常 4/augment 3-5,逐列内容不假定结构;漏读审计与对拍源)。
    # dict 键缺失容忍(兜底点卡路径无 options → 只有 gold);None=非补给行/旧记录。
    supply_pick: dict[str, Any] | None = None



@dataclass
class RunSummary:
    """单局 summary(runs.jsonl 一行)。"""
    schema_version: int = SCHEMA_VERSION
    ts: str = ""
    run_id: str = ""
    difficulty: str = ""
    result: str = ""                # "win" / "loss" / "abandoned" / "stopped"(迁移审计 w75(git 历史):停止路径,ADR-0335)
    plane_reached: int = 0          # 到达的最高位面
    rounds_survived: int = 0
    final_hp: int = 0
    comps_committed: list[str] = field(default_factory=list)   # commit 过的 comp 名序列(含 pivot)
    pivot_count: int = 0
    gold_trajectory: list[int] = field(default_factory=list)   # 每回合 gold(经济复盘)
    notes: str = ""
    # —— live 观测扩容(strategy/05_observation)——
    death_window: str = ""          # 39 号免费窗口登记:""=竞争局 / "must_die" / "free"(局终判定)
    strategies_held: list[str] = field(default_factory=list)   # 终局持卡(台账回放)
    # —— ADR-0273(批⑧ F2):行来源标记。''=正常终局/stop 路径写;'recovered'=
    # 兜底回填(从 outcomes/decisions 重算,盖 FAIL/崩溃/重启杀局路径)。
    source: str = ""



@dataclass
class ExecEvent:
    """执行事件(exec_events.jsonl;27 号能力画像数据源,2026-08-17)。

    prep_director 的 _fail_counts/_blocked/bail 原因本来局终即弃——落盘后跨局聚合
    出「动作族×画面×失败率」画像(能力层:实现缺陷 vs 固有难度分型)。
    """
    ts: str = ""
    run_id: str = ""
    round_num: int = 0
    action_family: str = ""         # 动作族(buy/deploy/equip/sell/levelup/refresh/...)
    screen: str = ""                # 画面/时相桶(battle_prep/supply/encounter/...)
    event: str = ""                 # "fail" / "blocked" / "bail" / "success_uncharged"
    reason: str = ""                # 原因码(识别 MISS/点击无效/状态不符/…)
    retry_count: int = 0



@dataclass
class ExogenousEvent:
    """外生事件(exogenous.jsonl;22 号预案触发频率 + 31 号 journal 外生族,2026-08-17)。

    节点类型转换/弹窗/简报/高利害条件触发——预案层的 trigger 频率统计与
    journal 常开的语料基础。
    """
    ts: str = ""
    run_id: str = ""
    round_num: int = 0
    kind: str = ""                  # node_enter/popup/briefing/event_choice/level_up(r378b 收敛到
    # 有生产者的值:前三种见 22/31 号预案;event_choice(迁移审计 w312(git 历史),遥测审计 G1)=
    # overlay 选项选择族(遭遇/巨星/伙伴/策划/命运卜者/装备选卡/祈愿)统一 kind;
    # sell_income(迁移审计 w323(git 历史),遥测审计 G2)= 卖牌执行点实收回金(shop.py SellBench
    # 执行分支,执行前后 gold 差——decisions 行的 actions 是执行前快照,
    # 实际回金只有执行点可知)。event_choice/sell_income 的结构化载荷在 choice
    # (detail 只放一行人读摘要)
    detail: str = ""
    state_snapshot: dict[str, Any] = field(default_factory=dict)   # 触发时的关键字段(hp/gold/bench…)
    choice: dict[str, Any] | None = None   # 结构化载荷(迁移审计 w312(git 历史) event_choice:{event/options/

    # n_options/pick_idx/reason};迁移审计 w323(git 历史) sell_income:{slot/char/gold_delta})。
    # 旧记录与其它 kind 恒 None(缺省兼容)。


@dataclass
class SpendUnitRecord:
    """购买单元账框架行(spend_ledger.jsonl;`w494_spend_ledger/`,纯观测)。

    一次 RunBuyPhase(开店→买牌/升级/刷新→关店)= 一个购买单元;本行只记
    director 执行边界的**单元框架事实**(边界/耗时/执行结果),plan 动作清单
    与金真值不在此复制——它们已在 decisions.jsonl(shop plan 行)与
    obs_conflicts.jsonl(gold_delta 冲突行),读端 query_spend_ledger join 三流
    成账(单一源,不建第二套金读数)。
    """
    schema_version: int = SCHEMA_VERSION
    ts: str = ""
    run_id: str = ""
    plane: int = 0
    round_num: int = 0
    unit_seq: int = 0               # 本局单元序(1 起;director run() 重入清零)
    boundary: str = "closed"        # closed=执行返回 / failed=执行返回但未进展 / aborted=执行抛异常
    progressed: bool = False        # executor.execute 的进展判定
    duration_s: float = 0.0         # execute 耗时(秒)
    detail: str = ""                # execute detail(截断;执行失败原因的下钻入口)
    # gold_before = 单元开时点 director 观察 gold。F2:director 时点店关,gold
    # 恒不可信——诚实记录不冒充真值,只作辅助对拍;trusted 恒 False 是常态而非异常。
    gold_before: int | None = None
    gold_before_trusted: bool = False
    # gold_close = 关店实读金,真值唯一来源是 shop.py 关店对拍点 read_gold
    #(经 ``set_unit_gold_close`` 暂存、单元关闭落账时消费填充;读失败=None,
    # 读端分类器记 unknown 不猜)。
    gold_close: int | None = None
    gold_close_trusted: bool = False
    # 执行侧「计划≠尝试」可见化(`w577_refresh_fee_and_andon/`,ADR-0456):生产者 = shop.py 执行循环
    #(经 set_unit_truncation 暂存、单元关闭落账时消费填充;未挂钩路径恒缺省)。
    plan_truncated: bool = False     # True=plan 里有动作未尝试(硬墙跳过/至首个 RefreshShop 截断丢弃)——口径差非执行失败
    refresh_skipped: str | None = None  # 刷新被跳过的原因:'max_cap'=MAX_REFRESH 硬墙;None=未跳过
    refresh_attempted: bool = False  # 本单元内至少点击过一次刷新
    refresh_board_changed: bool | None = None  # 刷新点击后牌面是否已变(两帧一致门+牌名集对拍);None=未尝试/不可判



@dataclass
class DefectRecord:
    """统一缺陷台账行(defect_ledger.jsonl;纯观测索引层)。

    把散在三处(obs_conflicts=感知冲突 / exec_events=执行失败 /
    spend_ledger·gold_detail=真值采集)的缺陷口径归一:每行通过
    ``evidence.refs`` 指回原流行(单一源,不复制数据)——审计先查台账,
    下钻再回原流。旧三流是原始证据层,保持原样不扩 schema。

    surface 值域:gold/bench/deployed/level_xp/hp/shop_refresh/phase_round/
    equip/strategy/confidence/node_seq/streak(未映射的新冲突字段原样落,
    消费端按字符串聚合,枚举外值不炸)。kind:perception_conflict /
    exec_fail / invariant_break。severity 为写入端初判,离线可用同一
    纯函数(judge_severity)按演进后的规则重判,不重写历史。
    """
    schema_version: int = SCHEMA_VERSION
    ts: str = ""
    run_id: str = ""                                # join key 主键(旧 obs_conflicts 缺,台账补齐)
    plane: int = 0
    round_num: int = 0
    unit_seq: int | None = None                     # 购买单元序(可空;spend 面专用)
    surface: str = ""                               # 缺陷所在观测面(见类注值域)
    kind: str = ""                                  # 三类=既有流口径归一
    expected: str = ""                              # 期望值/不变量描述
    observed: str = ""                              # 观测值
    gap: float | None = None                        # 数值化差(可空;文本面用 expected/observed 表达)
    severity: str = ""                              # L0_andon/L1_alert/L2_record(初判)
    verdict: str = ""                               # 沿用 obs_conflict verdict 语义(保旧/采新/拒信/待研)
    evidence: dict[str, Any] = field(default_factory=dict)   # {shot?, refs:[{stream,key}]}
    reader_source: str = ""                         # 沿用既有 source 词表
    note: str = ""                                  # 处理提示,一行
    # `w512_obs_surfaces/`(观测自检设计 §2.10/§5-B6):识别置信度快照,末尾追加可选字段
    #(旧记录缺省 None 兼容)。语义 = 缺陷发生时点的 reader 分数(SIFT 内点数
    # 等数值面;读空=0),不设即时告警,离线做分布监控——某 reader 读空率
    # 环比翻倍是系统性退化的最早信号(`w501_gold_read_fix/` 金读数窄区裁切类缺陷先于大额漂移
    # 在分布上暴露)。None = 该缺陷面无置信度语义。
    confidence: float | None = None



def bucket_card_texts(anchors: list[tuple[int, int]], items: list[tuple[str, int, int]],
                      y_min: int, y_max: int) -> dict[int, list[str]]:
    """投资卡 OCR 文本按卡分桶(ADR-0132;纯函数可测)。

    anchors: [(card_idx, 锚点x)](卡名行 center-x);items: [(文本, cx, cy)] 全图 OCR 条目。
    每条 item 归 **x 最近**的锚点卡;y 不在 [y_min, y_max] 描述带 → 不归。
    桶内按 y 升序(自然阅读序)。返回 {card_idx: [文本...]}。
    """
    if not anchors:
        return {}
    out: dict[int, list[tuple[int, str]]] = {i: [] for i, _x in anchors}
    for text, cx, cy in items:
        if not text or not (y_min <= cy <= y_max):
            continue
        idx = min(anchors, key=lambda a: abs(a[1] - cx))[0]
        out[idx].append((cy, text))
    return {i: [t for _y, t in sorted(v)] for i, v in out.items()}

