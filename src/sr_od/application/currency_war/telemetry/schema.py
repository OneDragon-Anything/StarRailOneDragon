"""遥测 schema:序列化纯函数与账本行 dataclass(自 cw_telemetry 拆出,分包期6)。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sr_od.application.currency_war.kernel.cw_state import (
    Action,
    BuyCard,
    GameState,
    _bench_char_cost,
    sell_refund,
)

# 符号解耦(处死计划批 0 第 1 项):本模块消费的注册数据/序列化符号权威
# 副本迁 knowledge/(cw_engine_facts/cw_line_facts/cw_serialize),
# 不再依赖 kernel/cw_deploy_logic、kernel/cw_intention(死刑判据文件)
from sr_od.application.currency_war.knowledge.cw_engine_facts import TRANSITION_TRAITS
from sr_od.application.currency_war.knowledge.cw_line_facts import (
    SEELE_SYSTEM,
    _bond_members,
)
from sr_od.application.currency_war.knowledge.cw_serialize import _to_jsonable

# 默认 replay 目录单一源已下沉 kernel/cw_observe(分包期 3:sim 桶消费它而
# sim 禁依 telemetry;本模块经上行 import 取用)。replay 序列化符号
# (_to_jsonable/serialize_intention)权威副本已迁 knowledge/cw_serialize
# (处死计划批 0)。
SCHEMA_VERSION: int = 1   # 决策迹 schema 版本(字段名稳定;改 schema 升版本号)



# ===== ρ 实测观测面(w919 R-A 批1;设计=同目录设计件 §2.1 辅通道口径)=====

RHO_SYSTEM_KEYS: tuple[str, ...] = (
    *(b for b, _t in TRANSITION_TRAITS),
    SEELE_SYSTEM,
)
"""ρ 实测的体系键域(四过渡体系:TRANSITION_TRAITS 三羁绊 + 希儿系;
派生自单一源,不手写名单)。"""

RHO_SHOP_OBS_FIELDS: tuple[str, ...] = ('systems', 'pair', 'n_shop')
"""shop_snapshots 行 ``rho_obs`` 键面单一源(测试锁面;语义见 rho_shop_obs)。"""


P26_PREP_OBS_FIELDS: tuple[str, ...] = ('node_type_next',)
"""decisions 行 ``p26_prep_obs`` 键面单一源(P26 采集批测试锁面;语义见
DecisionTrace.p26_prep_obs 注)。禁第二语义键——键集扩条只改本元组。"""


def rho_shop_obs(shop: list, pair: str = '') -> dict[str, Any]:
    """shop 单帧 ρ 实测分子:各体系「当前可买且对 form 有贡献」的在店件数。

    - 口径出处:R-A 设计件 §2.1——ρ(s,t)=观测窗 W 内体系 s 成员在店帧
      占比(P31① 辅通道)。本函数只记**单帧分子计数**;W 窗占比由读端
      按帧聚合,窗口假设不进采集点。消费=理论口径(E_rounds 超几何)
      的对拍与牌池结构变化检出,决策消费主通道不经此。
    - 成员判定 = ``knowledge.cw_line_facts._bond_members``(阵营∪流派全成员;
      多标签件在各命中体系各计 1,Σ systems 可超 n_shop——与
      OutcomeRecord.board_before 人次口径同判据)。
    - ``pair`` = 当前方向标签(p1_pair 优先次 transition_pair;''=空窗),
      读端 join decisions 行 sess_p1_pair 对齐方向与供给。
    - 纯函数契约:只读 shop 元素 name;未识别卡不属任何体系(只进 n_shop)。
    """
    names = [str(getattr(c, 'name', None)
                 if not isinstance(c, dict) else c.get('name')) or ''
             for c in (shop or [])]
    systems: dict[str, int] = {}
    for key in RHO_SYSTEM_KEYS:
        members = _bond_members(key)
        systems[key] = sum(1 for n in names if n in members)
    return {'systems': systems, 'pair': str(pair or ''),
            'n_shop': len(names)}



# ===== F7 / D_ε 判读面观察键(判前锁 v6 挂账行 7/11/13;键语义单一源=
# 本文件键声明;清单与登记键节原文已删档,取回口径=ADR-0644)=====
# 本段是**判读面键名声明**(v6 text 行判据=键名在本文件可检索),
# 非记录端接线:三键的行为面/计数端载体分别在 decision 层计数器与
# audit/provisional.py 槽位(判读批只产建议事件,编排器/人工单点注入),
# 判读器与本文件只消费键名与语义,禁自造第二语义。

F7_CONTINGENCY_ARMED: str = 'f7_contingency_armed'
"""F7 应急中间姿态独立分键(判前锁 v6 行 7,行判据=ab_core_swap._v6_row_specs)。

- 语义:应急期 F7 恢复需求的行为耦合开关——置位=「验收级门红事件
  [速率门∨有效性门] ∧ 归因批未结案」的机械判据,归因结案自动复位;
  与 `advisor_lambda_shadow_armed` 影子键分键上报,禁复用。
- 行为面载体 = audit/provisional.py 槽位(与开臂判据同槽);判读批只
  产出置位/复位**建议事件**(报告字段),置位/复位由编排器/人工经
  该槽位单点注入——判读器直写生产控制态=跨层耦合,禁。
- sim 判读批与实机生产批共用同一槽位,两侧置位语义不分叉。
"""

DEPSILON_ADVISOR_VIOLATION: str = 'depsilon_advisor_violation'
"""D_ε 顾问违例键 = 实现漂移哨兵(判前锁 v6 行 11;R56-2 定谳)。

- 语义:键 >0 ⇔ 门/检测两路实现漂移(检测侧=对遥测快照独立重评检测域
  的瞬时谓词重算,非共享单条谓词函数)。合法态下非豁免族顾问动作发射
  ⇒ 门 latch off ⇒ 本帧瞬时乘积 >η ⇒ 不落瞬时检测域 ⇒ 键=0;故
  阈=0 即红=完全检出力。键≡0 只证两路一致,不证约束满足(约束满足
  的 1−α 命题由成因④第七通道账承载)。
- 计数对象(现行,R59-1 收窄)= 非豁免族顾问动作发射
  [canonical (a) arm2 延迟/(b) 守息提前;(c) F7 排除] ∧ 瞬时检测域;
  F7 豁免发射帧不计入本键,走 `f7_exempt_emission`。signal-only 帧单
  独分键 `depsilon_signal_only`(观察级),与本键禁合并判读。
- 本键退出验收门三面合取红判据腿;三面合取结构=「速率面+有效性面+
  漂移哨兵(健康性)」。
"""

F7_EXEMPT_EMISSION: str = 'f7_exempt_emission'
"""F7 豁免发射计量观察键(判前锁 v6 行 13;R59-1)。

- 计数对象 = 真濒死帧[R40-1 三支完备式,含其与 D_ε 交]上 F7 越过
  D_ε 门的动作发射,分键含真濒死∧D_ε 子态。= R58-1 授权账已追认
  (2026-09-02,用户裁定)条目的观测载体(R41-2 确认条件内容可辨的
  计量面)。
- 观察级不进门;禁复用 `depsilon_advisor_violation`/
  `f7_uncovered_interest_sell`/`f7_contingency_armed`——三者分别系
  恒 0 实现漂移哨兵/默认姿态未覆盖帧凑息卖出计数/应急中间姿态开关,
  均非豁免发射计数(R59-1 分键纪律)。
- 行为锚:豁免发射帧 `depsilon_advisor_violation` 不计而本键 +1
  (原设计件测试位⑱(e),原文已删档,取回=ADR-0644);授权账追认判读报告含其频度/量级字段。
"""

F7_DEPSILON_OBS_KEYS: tuple[str, ...] = (
    F7_CONTINGENCY_ARMED,
    DEPSILON_ADVISOR_VIOLATION,
    F7_EXEMPT_EMISSION,
)
"""F7/D_ε 判读面观察键域(v6 挂账行 7/11/13 的 text 锚对象)。"""

F7_CONTINGENCY_ARMED_EVENT_FIELDS: tuple[str, ...] = (
    'gate_red_event_id',
    'attribution_batch_id',
    'ts',
)
"""f7_contingency_armed 置位/复位事件判前锁记录格式字段单一源
(判前锁 v6 行 7「置位/复位事件进判前锁记录格式(门红事件 id+归因批
id+时间戳)」;键节原文已删档,取回=ADR-0644)。

- 置位事件 = {gate_red_event_id[速率门∨有效性门],
  attribution_batch_id, ts};复位事件 = {结案结论, (a)-(d) 处置分支}
  (字段名异于置位三件,复位不带本元组)。判读批报告须含置位/复位
  事件字段(行 7 落地判据)。
"""


# ===== 序列化(dataclass → JSON-safe dict)=====

def salvageable_1star_value(state: GameState) -> int:
    """出口财富口径的「可回收 1★ 值」:手上(deployed+bench)全部 star==1
    件的卖出回金和。

    - 口径出处:P10④「出口『财富』= 袋子金 + 可回收 1★ 值」——
      ``docs/develop/sr_od/application/currency_war/proofs/p10-exit-gold-floor.md``
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



def terminal_state_summary(st: dict[str, Any] | None) -> dict[str, Any]:
    """轮「战后终态」板面计数(档案逐轮 ``terminal`` 列的单一源;纯函数)。

    - 背景(w936_deploy_fill 移交①):档案逐轮 deployed/bench/equips 列取自
      「决策帧」(``_best_decision_frame``,决策时点快照),而 CwOpDeploy/
      CwOpEquipAll 在决策之后的同备战期执行——复盘把决策帧当战后板面读 =
      快照时序误读(实证:g_20260831_032006 r9 决策帧 4/6,实机执行后 6/6)。
      本函数与决策帧列并列,读端一眼区分「决策时」vs「执行后」。
    - 取值时机:输入 = 该轮决策迹流内**最晚 ts 帧**的 state(该轮备战执行后、
      战斗前);战斗不改板面,故该帧板面 = 该轮战后终态。取帧在装配端
      (match_archive._last_decision_frame),本函数只做计数。⚠️ 边界(w943
      审计 P2-5):步进帧记录于动作执行前,异常出口收口的轮最晚帧滞后一个
      动作——可信度由档案逐轮 terminal_closure 区分(start_battle=执行后
      定型 / mid_prep=执行前末观察),本函数不判收口。
    - 坐标系:deployed_count = state.deployed 定长槽位表占用数(None 剔除,
      ADR-0392 紧缩口径);bench_count = state.bench 槽位表占用数(ADR-0316);
      equips_worn = Σ deployed[].equips 件数(已穿上身);equips_owned =
      state.equips 件数(list/dict 均按元素数;未穿上身 owned 池)。
    - 输入是 serialize_state 产物 dict;缺键/非 dict 安全退化 0/空
      (旧数据与残缺帧不炸)。
    """
    out: dict[str, Any] = {'deployed_count': 0, 'bench_count': 0,
                           'equips_worn': 0, 'equips_owned': 0}
    if not isinstance(st, dict):
        return out
    dep = st.get('deployed')
    if isinstance(dep, list):
        out['deployed_count'] = sum(1 for d in dep if d is not None)
        # worn 计数下探元素内字段类型(w943 审计 P3-6):残缺帧的 equips
        # 可能是标量——非 list/dict 计 0(str 不得按字符数计,len(int) 不炸)。
        for d in dep:
            if d is None or not isinstance(d, dict):
                continue
            eq = d.get('equips')
            if isinstance(eq, (list, dict)):
                out['equips_worn'] += len(eq)
    bench = st.get('bench')
    if isinstance(bench, list):
        out['bench_count'] = sum(1 for b in bench if b is not None)
    owned = st.get('equips')
    if isinstance(owned, (list, dict)):
        out['equips_owned'] = len(owned)
    return out


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
    """单 Action → JSON-safe dict(带 type 标签,便于复盘识别)。

    BuyCard 决策帧富化(观察层数据移交批,纯观测零行为):顶层平铺
    ``char_id`` 与 ``cost``——此前买入角色只以 OCR 原名嵌在
    ``card.name`` 里,跨流对账(spend_ledger 采购账/补给行/ BenzChar
    char_id 侧)拿不到注册表规范名,费用也要下钻 card 嵌套。
    - ``char_id`` = ``data.cw_chars.CHARACTERS`` 规范名(OCR 名精确
      命中注册表才写,未命中/查询失败 = ''——诚实缺省,不猜);
    - ``cost`` = ``ShopCard.cost`` 平铺(OCR 真值;0 = OCR 失读,
      消费方按缺口对待,不用注册表值冒充——多源混写是 board_before
      人次口径已付过的学费)。
    富化只加键不改既有键:旧读端(下钻 card.* 的 query_supply/
    query_economy)零波及,旧记录缺键 .get 兼容。
    """
    d = _to_jsonable(action)
    d["__type__"] = type(action).__name__
    if isinstance(action, BuyCard):
        d['cost'] = int(getattr(action.card, 'cost', 0) or 0)
        d['char_id'] = ''
        try:
            from sr_od.application.currency_war.data.cw_chars import get_char
            _ch = get_char(str(getattr(action.card, 'name', '') or ''))
            if _ch is not None:
                d['char_id'] = str(_ch.name)
        except Exception:   # noqa: BLE001  观测 best-effort,不阻断落盘
            pass
    return d



# ===== 动作计划理由溯源(统一state R4;ADR-0630 策略侧决策行动作计划
# 逐项理由溯源,判据名持久索引)=====

ACTION_REASON_SOURCE_KEYS: tuple[str, ...] = (
    'reason', 'route_tag', 'auth_basis', 'convert_reason',
)
"""动作项理由溯源提取键序单一源(测试锁面 = test_cw_decision_trace_r4 锁②e)。

- 语义:决策行 actions 逐项附 ``reason`` 键(判据命中 id 持久索引),取值 =
  按本键序从**现役决策构建链已有字段**提取首个非空值——纯提取禁新算
  (理由事实是决策时点记录,代码演进后重跑不可靠;留事实,不重算过程值)。
- 键序依据:动作自带归因字段优先(reason = 买入臂/卖出通道/刷新触发源/
  控制流原因),发射臂标签次之(route_tag = mandate_v1 Emitted.reason 经
  bridge.decide_from_turn 透传),授权/豁免记录兜底(LevelUp.auth_basis /
  SellBench.convert_reason,「记录非指令」形态)。
- 键集扩条只改本元组;各键的值域闭集归其定义模块(sell_gate/
  cw_prep_actions.SELL_BENCH_REASONS 等),本元组不做第二登记。
"""


def action_reason_of(item: dict[str, Any]) -> str:
    """序列化动作项 dict → 理由溯源串(纯函数;键序单一源见上)。"""
    for k in ACTION_REASON_SOURCE_KEYS:
        v = item.get(k)
        if v:
            return str(v)
    return ''


def apply_action_reason(item: dict[str, Any]) -> dict[str, Any]:
    """给序列化动作项归一附 ``reason`` 键(只加键不改既有键;原地返回)。

    接线点 = ``TelemetryRecorder.record_decision``(decisions 行写路径
    单一点);op_journal 等其他流的 serialize_action 产物不经本函数,
    变更面严格限于决策行。
    """
    item['reason'] = action_reason_of(item)
    return item



def p1_pair_label(ist: Any) -> str:
    """P1 配方对 → 遥测标签串('A+B' 体系键串;空窗/无意向 = '')。

    - 来源 = ``cw_intention.IntentionState``:配方锁局取 ``p1_pair``
      (锁定产物),①资格锁局取 ``transition_pair``(受保护副方向,
      与 scoring._vd_p1_pair 同式优先序);两字段同口径派生、同帧至多
      一侧非空,故按 p1_pair 优先取其一。
    - 体系键域/二元组语义见 cw_intention.IntentionState.p1_pair 注释;
      tuple/None/非 dataclass 输入一律安全退化空串(纯观测不阻塞环)。
      dict 形态(serialize_intention 产物,recorder 经 extra/快照取用)
      同口径支持(w919 rho_obs.pair 消费)。
    """
    _get = (lambda k: (ist or {}).get(k)) if isinstance(ist, dict) \
        else (lambda k: getattr(ist, k, ()))
    pair = tuple(_get('p1_pair') or ()) or tuple(_get('transition_pair') or ())
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
    hp: int | None = 0                            # 决策时 HP(冗余于 state,便于快速筛;r1 备战帧读失败=None 诚实未知——r1 血量固定但不恒 100,默认 100 兜底在 r1 是错误值,写入口径见 recorder.record_decision)
    hp_readable: bool = True                      # hp 值来源可读位(True 可信度等同真读:①真读=OCR 备战 HP 区;②结算=结算屏经新鲜度门;False=读不到,ADR-0282/0491:hp=None 即无真值帧(沿用帧例外),100 兜底已废止)
    gold: int = 0                                 # 决策时 gold(冗余,便于 gold 轨迹)
    gold_readable: bool = True                    # gold 真读到?(ADR-0282:cw_screen_prep「gold 不可信」日志升级为字段,对齐 hp_readable)
    level_readable: bool = True                   # level 真读到?(对齐 hp_readable;False=纯 _expected_level 启发式兜底帧——「兜底 4」与「真读 4」判读可分;旧档案缺省 True=按现有判读处理)
    # —— live 观测扩容(strategy/05_observation;全部可选,回放/影子对齐)——
    active_strategies: list[str] = field(default_factory=list)   # 持卡(台账/效果解回放)
    shop_rejects: dict[str, str] = field(default_factory=dict)   # 商店波未买牌拒因串({牌名: 拒因};生产端=cw4/shop.shop_unbought_reasons,旧行缺省空 dict)
    refresh_trigger: dict[str, int] = field(default_factory=dict)  # 刷新触发源分键({reason: 次数};生产端=recorder 自决策行 actions 统计(sim 账本行同名键同语义),'' 归 other 桶;旧行缺省空 dict)
    dp_posture: dict[str, Any] = field(default_factory=dict)     # 影子 DP 姿态(tag/level_up/refresh_budget/v)
    # (ledger_fingerprint 台账指纹已随 DP 世界模型退役删除——写端恒缺键、
    #  全域零读端;旧语料行该键按缺键读,schema 兼容。)
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
    ev_arm: str = ""                               # 臂位(R1-1:skeleton_only/full;仅 mandate_v1 写,legacy 恒空——判栈二元组 (strategy_id, ev_arm) 第二维)
    v2_mode: str = ""                             # economy/war(滞回当前模式)
    v2_locked_line: str = ""                      # 锁定线 id(""=未锁)
    v2_bridge: str = ""                           # 当前桥线 id(""=无)
    # (sess_v2_state v2 相位机元组(r359 回放忠实化采集,ADR-0231)已随
    #  v2 退役链删除——生产写端 v2_state 恒 None、全域零读端;旧语料行
    #  该键按缺键读 None,schema 兼容。)
    # —— 迁移审计 w114(git 历史)/ADR-0346 相位影子观测(经济循环总模型步①;零消费):
    # phase(v2 相位机退役,无写端恒缺省)/form_ok(sim71 批死镜像处置后
    # 写端 = write_shop_mirrors 接 readiness_form_ok 板面现读;旧记录
    # 均为退役恒 False)。可选,旧记录缺省不破坏 schema。
    phase: str = ""
    form_ok: bool = False
    # 已退役字段(历史数据只读):form_score 旧口径(min(2, engines+
    # 0.3×frac)/2 连续量)在决策关键帧恒常数零方差、预测力为零,
    # 已由 b_t 替代披露;新写端不再写,读历史账本仍取到原值。
    form_score: float = 0.0
    # B_t 板面目标线承重计数(form_score 替代披露口径;kernel
    # cw_deploy_logic.board_target_line_weight 单一源,禁第二实现)。
    # 纯遥测观测面,不进判据(ADR-0353 纯遥测口径延续);旧记录缺省 0。
    b_t: int = 0
    # ADR-0343 成型停手态(层2 写;检查器豁免/判读锚点)——补挂
    # DecisionTrace 字段:shop/cw_screen_prep 均已在 extra 传
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
    # 取值 = 本 record 调用时点的 strategy_state_of(session).v3_intention 配方对(非空
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
    # 血预算停手·停升级拒付计数(strategy_state_of(session).v3_blood_budget_rejects 透传;
    # 写入端=arbiter/remediation 拒付面,局首清零)。
    sess_blood_budget_rejects: int | None = None
    # 血预算停手·搜索型刷新停付拒付计数(strategy_state_of(session).v3_blood_budget_refresh_rejects
    # 透传;写入端=arbiter refresh 收尾,局首清零)。
    sess_blood_budget_refresh_rejects: int | None = None
    # 血预算停手·终止分支决策位。⚠️ 与 sim 账本行键 terminal_release 同名
    # 不同体(两键口径):本 schema 字段 = recorder 侧实机透传位,写入面已
    # 接回 terminal_release_bit 单一源(recorder.py;判据 =
    # sim/checks/segments.terminal_release_bit;设计 W659 v2 §5.1 R4;
    # ADR-0469)。读实机豁免位读本字段;sim 账本行键 terminal_release 为
    # sim 侧行键(engine_p1 轮入口),判读对账注意两键粒度。
    sess_terminal_release: bool | None = None
    # P1-a 末窗支出降格触发面:取值=本 record 调用时点按 state +
    # DEFAULT_REGISTRY + match session(闩位含位面内触发闩,ADR-0469)
    # 现算(生产 DecisionV2Strategy() 缺省即 DEFAULT_REGISTRY;sim A/B
    # 注入臂行不带此语义保证,判读按 strategy_id 分栈)。None=现算失败/
    # 依赖缺失。
    p1_downgrade_active: bool | None = None
    # 经验期望账本快照(exec_state_of(session).xp_expect_ledger=cw_screen_prep.XpLedger 正式
    # 字段,此处平铺 dict 便于判读;None=未锚定/无账本)。
    xp_expect_ledger: dict[str, Any] | None = None
    # —— `w611_econ_cycle/` 储备/义务披露(经济循环总模型;ADR-0445 实机验证队列
    # 「死时带金/闲置金」判读的帧级数据源;接出点同 `w603_telemetry_wiring/` 汇点)——
    # None/缺省 = 无 match 注册或 decide_prep 未跑(离线/测试/default 栈)。
    # 储备线 R*(=息线+窗口排程升级费;strategy_state_of(session).v3_reserve_cap 透传)。
    sess_reserve_cap: int | None = None
    # 溢余 (g−R*)+(义务压力原料;闲置金判据=本字段的帧均值)。
    sess_reserve_overflow: int | None = None
    # 当轮 release 义务预算(金;0=无 release 帧或零预算结转帧)。
    sess_release_budget: int | None = None
    # 义务来源(''/'flip'/'crisis'/'third_path'/'reserve_admission'/
    # 'must_spend';'crisis'=危机金出口臂 ADR-0503,判读兑换率分域勿漏
    # 此值;'must_spend'=必花域帧写点,T-88 批新增值域——shop 必花域段
    # 帧内 last-wins,轮界清零在装配键戳,ADR-0571。现役 mandate_v1
    # 只产 ''/'must_spend',其余值为历史来源,存量数据按旧口径读)。
    sess_release_reason: str | None = None
    # 当轮 release 帧实际消费(金;strategy_state_of(session).v3_release_spent 透传,每轮
    # 入口清零,清零承载 = 策略状态 v3_disclosure_key 键戳)。
    # 口径(T-88 收窄申报,ADR-0571):首版只计**刷新实花**(记账位 =
    # cw_op_buy_cards 执行回执位;决策帧值 = 轮内截至采样时点累计)——
    # 买牌/升级是否计入「全渠道义务实花」在 mandate_v1 语义下未经证明,
    # 裁决前收窄防虚高(宁窄勿虚;旧 authorize_release_refresh/
    # _accrue_release_frame_spend 机制退役史与口径裁决归 ADR-0571)。
    # ADR-0503 开臂判据②的「实花面分项账」数据源:危机帧兑换按本字段计,
    # sess_release_budget 记账面(预算许可)不作兑现证据。
    sess_release_spent: int | None = None
    # (位面 2 支出授权历史字段 sess_p2_auth_intercept/sess_p2_auth_water
    #  已删(ADR-0492 定谳清理链收尾:写端早已随机制删除,全域零读端);
    #  旧语料行该两键按缺键读 None,schema 兼容。)
    # (支出门·买侧收门拒因枚举计数 sess_spend_gate_block 已随
    #  spend_gate 开关族删除——旧方案清退批,清查报告 OLD_MIX_AUDIT
    #  §1.3;存量 runs.jsonl 判读脚本按缺键读 None。)
    # 预算-回执契约·对账门声明(w921_rd_design DESIGN §1.1-C;
    # strategy_state_of(session).v3_posture_unfulfilled 透传):{auth_id, channel, reason,
    # channels, action}——授权未兑现帧的显式归档(reason=四枚举
    # no_premise/no_channel/no_candidate/no_budget;action=allocator/
    # crisis_release/downgrade)。None=无未兑现帧/开关关/无 match 注册。
    # 开臂判读主判据「授权未兑现帧占比」的数据源(判前预注册
    # .debug/temp/currency_war/w937_rd_batch1/PREREG.md)。
    posture_unfulfilled: dict[str, Any] | None = None
    # (sess_pv_bench_block 已随件价值整机制删除,ADR-0497;存量 runs.jsonl
    #  判读脚本如遇旧键按历史台账读,新数据不再写。)
    # —— w919 R-A 批1 方向重估决策面观测(纯观测零行为;设计=.debug/temp/
    # currency_war/w919_ra_obs/DESIGN.md 采集点2,P31 方向供给感知批1)——
    # 辖域=plane==1 ∧ 有意向状态机;P2+ 方向=locked_comp 已由 v3_intention
    # 嵌套行携带不重复平铺。缺省 None=无意向/采集失败/旧记录(不破坏 schema)。
    # (w919 方向重估三观测键(sess_dir_candidate/switch/supply_drought)的
    #  写入面已随兑现链方向侧开关族删除——旧方案清退批,清查报告
    #  OLD_MIX_AUDIT §1.3;字段按历史数据只读口径保留,新数据恒 None。)
    # 补给轮决策行采集(观察层数据移交批):补给节点选卡确认后的合成
    # 决策帧(extra.phase='supply_pick')携带的选定快照——
    # {char, equip, has_diamond, refreshed, options:[{char,equip,has_diamond}...],
    # n_options},形状与 telemetry.state 暂存槽/set_last_supply_pick 一致
    # (单一形状,不造第二套)。None=非补给帧/兜底点卡路径(决策帧照写,
    # 读端按 None 分型)。此前决策行只有空壳快照,「补给选了什么/牌面给
    # 了什么」要等 outcomes 合成行 join 才可读;平铺进决策行后单行自足。
    # 可选末尾追加字段,旧记录缺省 None 不破坏 schema。
    supply_pick: dict[str, Any] | None = None
    # —— 决策时点挂起期望态快照(W971 期望态 infra 遥测批;**写入端已随
    # ADR-0651 两态制退役**:expected_state 条目表拆除,新数据恒 None——
    # 字段按历史数据只读口径保留,旧行读端分型不变)——
    # 历史快照语义 = record 调用时点 exec_state_of(session).expected_state
    # 未确认条目摘要 [{path, value, produced_by, at_round, kind}]。读端三态:
    # 旧行无此键 = 迁移前数据(不修复);旧行 [] = 无挂起期望;旧行非空 =
    # 决策基于含期望推进值的画面。可选末尾追加字段,旧记录缺省 None 不破坏
    # schema。
    expected_paths: list[dict[str, Any]] | None = None
    # —— P26 备战帧无条件采集(math_proofs P26 双挂账采集批;纯观测零行为)——
    # 19 号稿 §2.3-4 裁定:P26 标定样本面须另立采集点(备战帧无条件采样),
    # 非 D-D 尾部帧计数位。本字段 = 该采集点:每备战决策帧一行平铺
    # ``node_type_next``(下一节点类型标签 = P26 的 L_node 标签维度;来源
    # 单一源 = 位面节点台账 ``cw_state.ledger_node_type`` 同源读链,即
    # flow 掉血回落同表;**原始 token 不映射不猜**——battle/encounter/boss/
    # elite/supply/reward/...,查不到 = '' 诚实缺省,分桶映射归离线标定批)。
    # 键面单一源 = ``P26_PREP_OBS_FIELDS``;禁第二语义键。
    # hp 边界(00_framework §3 硬闸门):本钩子**不采任何 hp/战力量**——
    # L_node 分位口径(条件败面伤害尾部)走既有结算三项遥测授权面
    # (outcomes 行 damage_base/damage_unfinished_progress/hp_after),
    # 本批只申报离线 join,不加新 hp 读链。
    # None = 无 match 注册(离线/测试缺省);dict 且 node_type_next='' =
    # session 在场但台账未命中(不猜)。可选末尾追加字段,旧记录缺省 None。
    p26_prep_obs: dict[str, Any] | None = None
    # —— 统一state R4 策略侧遥测演进(ADR-0630 策略侧 state_ref 版本钉;
    # 返工方案 A 钉读点 = 决策读取完成时点)——
    # 决策行关联流程侧账本版本钉:``state_ref = '{run_id}#{v}'``,v =
    # 「决策读取完成时点」的 ``kernel.cw_board_state.board_state_of(session)
    # .current_version()``(读口:读不写、不占版本)。捕获时点 = 段入口观察
    # 完成处(决策开始依据该 state 版本计算),由调用方捕获经
    # ``record_decision(state_ref_version=)`` 传入落钉——观察完成与行落盘
    # 之间段内动作回执会推进版本,钉值不得漂移到落盘时点(ADR-0630 关联
    # 序:决策行钉版本 ≤ 其动作的落地行版本;观察与落盘间零写入交错的
    # 调用点,recorder 入口现读等价)。回溯语义 = 直接读该 run 记录流中
    # v 行的 state 字段(行行自足,零重放);行缺失(清理淘汰/崩溃丢失窗/
    # 影子关)= unverified,不猜。'' = 无 match 注册(离线/测试)或读取
    # 失败——诚实缺省。可选末尾追加字段,旧记录缺省 '' 不破坏 schema
    # (判读读面宽容)。
    state_ref: str = ""



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
    hp_after: int | None = 0   # None 仅收口终局行携带(见 match_result 注);缺省 0=旧记录字段缺位
    hp_confidence: float = 1.0
    enemy_hp_after: int | None = None
    damage_dealt: int | None = None
    killed: bool | None = None
    progress_delta: int | None = None   # 结算屏「挑战进度 ±N」(2026-08-18:胜负+扣血真值,输轮也记)
    streak: int | None = None           # 连胜/连败带符号(r68:RoundOutcome 有此字段但序列化丢弃 → 补)
    # —— 结算三项遥测(docs/develop/currency_war/strategy/05_observation.md §3.1(迭代工作面原稿 SETTLE_OCR_DESIGN §3;镜像 cw_performance.RoundOutcome 同名字段)——
    # progress_fill_ratio:挑战进度条填充率 [0,1](幅度绝对值;±N 在 progress_delta);
    # damage_base/damage_unfinished_progress:掉血说明 tooltip 两分量(tooltip 进页瞬态,
    # miss=None=删失显式可辨);damage_breakdown_visible:tooltip 在场与否(区分
    # 「不在场」vs「在场解析失败」)。旧记录缺字段,读取端 .get 容忍。
    progress_fill_ratio: float | None = None
    damage_base: int | None = None
    damage_unfinished_progress: int | None = None
    damage_breakdown_visible: bool = False
    # —— T-83 补链(ADR-0609):tooltip 第三行「长线作战」战斗回血分量(恒 ≥0,
    # 实机常量 +2/场,ADR-0241 口述+连胜轨迹实证)。此前解析器已读但本 schema
    # 缺字段 → 静默丢弃,L_node 判读「tooltip 幅度 = hp 链差 + 2」偏移只能靠
    # 猜。补齐后偏移可直接从行内验证:链差(净变化)= 掉血两分量 + heal_longline。
    # 可选字段追加(关键字序列化,位置无关),旧记录缺省 None 不破坏 schema
    # (读取端 .get 容忍)。
    heal_longline: int | None = None
    # —— r339 板深快照(板深→胜率模型校准数据源;复盘发现 sim
    # 天花板 8%>=60 vs 实机 3/3 达标的矛盾根因=模型缺板深机制,
    # 而逐轮板面×掉血对就是拟合数据):战前板面+上阵深度。
    # board_before 语义(match archive 二期③④文档化):{阵营: 人次}——
    # **不是板深**。多标签角色在每个命中阵营各计 1,Σ人数 ≥ 实际在场数;
    # 板深粗代理 = Σ人数(下界),精确在场数 = state.deployed 占用数
    # (decisions 帧)。读端拿它做板深校准时按人次口径降权
    # (telemetry-reading「已知缺口」同一判据)。
    board_before: dict[str, int] = field(default_factory=dict)   # 战前 {阵营:人数}
    bench_count: int = 0               # 战前 bench 数(板深第二维;ADR-0316 占用数口径)
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
    # refreshed=exec_state_of(session)._supply_refresh_used 时点值(该次确认前是否已刷新重掷);
    # gold=完成时点 last_state.gold(gold_readable=False 缺省不写,不冒认真值)。
    # W306c:options=[{char,equip,has_diamond}...] + n_options=实际识别列数
    # (动态探测,通常 4/augment 3-5,逐列内容不假定结构;漏读审计与对拍源)。
    # dict 键缺失容忍(兜底点卡路径无 options → 只有 gold);None=非补给行/旧记录。
    supply_pick: dict[str, Any] | None = None
    # —— T-185 收口终局行标记(实机末轮 outcome 采集补全):''=普通结算行
    # (屏面真值/'recovered'/'synthetic_supply');'stopped'/'abandoned'=
    # 对局收口终局行(对局循环中止收口时补写,写点 = cw_loop._write_terminal_
    # outcome_row)。终局行 killed 语义切换为**对局级**:False = 对局终了时
    # 通关击杀未达成(中止局可证未通关,ADR-0306 权威口径可判),**不是该轮
    # 战斗结算**(该轮战斗可能根本未打完);hp_after 恒 None、hp_confidence
    # 恒 0.0(不发任何 hp/战斗真值——Δ池配对按 hp_after=None 前置剔除、
    # hp 步进链按可信门退出,零新过滤)。可选字段追加(关键字序列化,位置
    # 无关),旧记录缺省 '' 不破坏 schema(读取端 .get 容忍)。
    match_result: str = ""



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
    # —— 策略版本戳(match archive 二期②):本段 run 实际跑的代码版本,
    # recorder.record_run_summary 写入时点打戳(单一源=telemetry/version_stamp;
    # 装配端只透传不重算)。''=未采/旧记录(消费端读空 = 版本未知,不猜)。
    code_commit: str = ""
    registry_fingerprint: str = ""



@dataclass
class ExecEvent:
    """执行事件(exec_events.jsonl;27 号能力画像数据源,2026-08-17)。

    cw_screen_prep 的 _fail_counts/_blocked/bail 原因本来局终即弃——落盘后跨局聚合
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
    # (detail 只放一行人读摘要);hp_pay(ADR-0577,T-100 批1)= 血购执行回执
    # (prep_actions.record_hp_pay_event 两通道共用写点,粒度=击数),载荷在
    # choice:{plane/round_num/currency/hp_delta/mode/clicks/basis='modeled'};
    # **遥测禁入决策输入**(隔离申报同 ADR)。
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
    unit_seq: int = 0               # 轮内单元序(1 起;按 (plane,round) 键重计,run() 重入不清——同轮多单元恒递增)
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

