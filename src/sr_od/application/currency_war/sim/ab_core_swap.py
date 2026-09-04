"""换核 A/B 双臂工厂 + 门组(§6.4-R 步4/步4b;SIM_CONSUMPTION_MAP ③)。

**载体申报(让路规则)**:``sim/runner.py`` 本批时点 git status 见并行
未提交改动,按让路纪律禁编辑——双臂 harness 落本模块(复用
runner/engine 既有函数,零侵入);runner 侧正式合流入口待裁。

A/B 约束(SIM_CONSUMPTION_MAP ③/Q3):
- 环境恒等:同 seed_base/同 pool(核 pool_fingerprint)/同 planes/
  同注册表视图(``sim_decision_registry()`` 派生,两臂一致);
- rng 中立:新核不消费局内 rng 流(会话流派生注释=契约;R197 症5
  升格=测试锁 ``test_rng_neutral_static_lock``,静态扫 cw4 包零
  ``random`` 消费。运行期守卫不可行如实申报:局内 session rng 在
  引擎内按 seed 派生,臂侧不可达——同 seed 自配对对「消费 rng」
  构造性不敏感[两跑同样消费],静态锁是可实现的强形态);
- 新核 registry 属性带上(Q3 坑位①:注入策略无 registry 属性时观测键
  走回退路径,口径混)。

**预注册声明(R197 症2 裁决落地,编排者裁=方案 a;步6 判前锁 v6
前置语句的一部分)**:A/B 期两臂**换线行为恒等**——target_comp 权威
= decision_v2 意向状态机(``MandateV1Strategy.update_target`` 透传,
见 cw4/bridge.py 声明,两臂同源共用),cw4 proof 侧 should_switch/
回锁窗/干旱计数=影子面(发遥测不写 target_comp,影子机禁删);臂间
ledger diff 的归因域因此**不含换线路径**。

**归因域测量域限定(IMPL_ADV_R200 症7 落地,v6 判前锁清理批)**:
sim 引擎唯一决策入口=``strat.decide_shop_screen``(商店波),新核
prep 线(``decide_prep_screen``/prep_obs_frame)在 sim 全程零覆盖
——臂间 ledger diff 的归因域**实际=shop 决策面**(prep 面 sim 不可
达,原「diff 全部归于 prep/shop 决策面」表述的 prep 半边无测量
对象)。门组的确定性/零漂移/归因结论辖域同此收窄;B1/B2 headline
不得把 shop 面结论外推为全决策面处理效应。

门组(统一迁移批 ② 后形态;**辖域=shop 决策面——sim 测量域只有商店波,
prep 线零覆盖,IMPL_ADV_R200 症7**):
- ``new_core_self_pairing_gate``:**单臂零漂移自配对门**——mandate_v1
  同工厂双臂同 seed 同池 ledger 逐位相等(n≥10;确定性自检)。红 = 存在
  非确定性(或意外消费局内 rng 流)。基线自配对门(``baseline_self_
  pairing_gate``)与双臂相异探针(``arm_diff_probe``)已随基线臂退役
  删除(A9 裁决);**池指纹守卫**保留(指纹集非单元素 ⇒ raise)。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sr_od.application.currency_war.sim.engine_p1 import (
    sim_decision_registry,
    simulate_p1,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.bridge import (
    MandateV1Strategy,
)

#: 标定批 V1 注入值(V̄_net;值/出处/方法/状态的单一叙述源 =
#: docs/develop/currency_war/archive/redesign/reports/core_swap/CALIB_REPORT.md 与 design_telemetry
#: 「标定批」节;此处只做显式注入通道,禁散落第二处数值推导)。
V_GAP_CALIB_V1: float = 24.7
V_GAP_CALIB_V1_BAND: tuple[float, float] = (16.7, 24.7)


def apply_core_swap_calibration() -> None:
    """标定批 V1 注入(V_GAP/V_MS;④-2 分臂纪律的唯一开闸通道)。

    值 = V̄_net 24.7 金(calib_vuh_v1 合成价值链:rung 流 15.0 +
    胜率流 9.7,全部锚 = cw_registry 既有字段零新自由参数;标定带
    [16.7, 24.7] 恰括 P40 S1 边界——e2 变体[合格集条件语义,transition
    凑档命题支持]为注入值,e1 变体 16.7 为敏感带下沿)。V_MS 同值同源
    注入:provisional #2a/#2b 拆槽「同源单标定禁双源」——V_MS 消费面
    均另有 U_X/T_SEARCH_A 前置仍 fail-closed,本注入不改变其行为面。
    状态申报:``injected_form=True``(sim/A-B 驱动专用;生产开闸须标定
    批 CI 验收五件套,provisional.py 模块 docstring 纪律)。正式 A/B
    入口/活性守卫前调用本函数;重注入前 ``provisional.reset()`` 清场。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
        provisional,
    )

    val = provisional.CalibValue(
        value=V_GAP_CALIB_V1, ci_lo=V_GAP_CALIB_V1_BAND[0],
        ci_hi=V_GAP_CALIB_V1_BAND[1], injected_form=True)
    provisional.inject('V_GAP', val)
    provisional.inject('V_MS', val)


def new_core_self_pairing_gate(n: int = 10, seed_base: int = 0,
                               **sim_kwargs: Any) -> dict:
    """新臂零漂移自配对门(R197 症5;与基线门对称的确定性自检)。

    逐 seed 跑两遍 mandate_v1(同工厂派生、同 seed 同池同注册表视图),
    比对 ``SimResult.ledger`` 逐位相等。红 = 新核行为非确定(或意外
    消费局内 rng 流)——步6 配对差会把该噪声混入处理效应,先修再谈
    A/B。池指纹守卫:两次运行的指纹集须单元素,否则 raise。
    辖域限定(IMPL_ADV_R200 症7):本门的「确定性/零漂移」结论只覆
    盖 shop 决策面(sim 唯一入口=decide_shop_screen)——prep 线
    (decide_prep_screen/截断器/升档器求值位/proof 线级状态机)在
    sim 零覆盖,其确定性另由 checks/decision_v2.py 契约等价门承载。
    """
    mismatches: list[int] = []
    fps: set[str] = set()
    for i in range(n):
        seed = seed_base + i
        reg = sim_decision_registry()
        r_a = simulate_p1(seed, strategy=MandateV1Strategy(registry=reg),
                          **sim_kwargs)
        reg = sim_decision_registry()
        r_b = simulate_p1(seed, strategy=MandateV1Strategy(registry=reg),
                          **sim_kwargs)
        fps.update({r_a.pool_fingerprint, r_b.pool_fingerprint})
        if r_a.ledger != r_b.ledger:
            mismatches.append(seed)
    _require_single_fingerprint(fps, '新臂自配对')
    return {'n': n, 'mismatches': mismatches, 'ok': not mismatches,
            'pool_fingerprint': sorted(fps)[0] if fps else None}


def _require_single_fingerprint(fps: set[str], ctx: str) -> None:
    """池指纹一致性守卫(R197 症5,对齐 runner.simulate_core_ab)。

    指纹集非单元素 ⇒ 对拍/自检的环境恒等前提被破坏——显式 raise
    优于静默比较(错账比对产出无意义门读数)。
    """
    if len(fps) != 1:
        raise RuntimeError(
            f'{ctx}池指纹不一致(对拍不公平): {sorted(fps)}')


# ===== 零刷新修复批(2026-09-03)新增:正式 A/B 前置守卫组 =====
# 出处:2026-09-03 换核 A/B 零刷新事故(ZERO_REFRESH_DIAG,ab_run_20260903
# 目录)——正式 A/B 在 EV 面全未标定态开跑,mandate_v1 的 ev_arm=full 臂
# 事实上行为等同 skeleton 臂(刷新/ev_buy/升级三面齐死),B1/B2 被当作
# 处理效应误读。本守卫组把「正式 A/B 前的硬前置」代码化,防同类漏检。

#: 动作族 → ledger 动作类型名(族活性下限守卫的计数对象)。
#: 证据辖域限定(IMPL_ADV_R200 症7):sell 族的「活过」证据只覆盖
#: **shop 侧发射位**(M4 shop 版/funding 支撑/sell_for_interest);
#: prep 侧 ``m4_fuel_sell_for_m2`` 发射位无 sim 证据(同根:sim 决策
#: 入口只有 decide_shop_screen)——sell 族绿不外推为卖面全通道活。
ACTION_FAMILY_TYPES: dict[str, tuple[str, ...]] = {
    'refresh': ('RefreshShop',),
    'levelup': ('LevelUp', 'LevelUpShop'),
    'buy': ('BuyCard',),
    'sell': ('SellBench', 'SellDeployed'),
}

#: 动作族 → 其发射路径消费的 provisional 槽位(豁免推导输入)。
#: 仅登记「该族的**全部**发射路径都 fail-closed 于该槽位」的依赖:
#: refresh 族唯一发射位 r1 的 EV 输入=V_GAP(None ⇒ 构造性零刷新);
#: buy/sell 族含骨架义务路径(M2 线成员买入 / M4 腾席+支付支撑),
#: levelup 族触发信号 arm1 系结构谓词(板面可观测量,非 EV 槽位)——
#: 三者恒不豁免,饥饿即结构性病灶信号。
FAMILY_PROVISIONAL_DEPS: dict[str, tuple[str, ...]] = {
    'refresh': ('V_GAP',),
    'levelup': (),
    'buy': (),
    'sell': (),
}


#: 活性守卫升级扫描规模(FIX_REVIEW_20260903 复审返工批):首轮 n 局
#: 出现非豁免零发射族时,追加 ESC 局换 seed 段复扫——区分「低频活」
#: (sell 族实证 4/30 局:M4 腾席路径正确但受 None 期买量设计门传导
#: 低频)与「真结构死路」;升级段仍零发射才 raise。存在性证明的抽样
#: 下界随路径真实频率自适应,不再把「n=10 固定 seed 段撞不到」误判
#: 为死路(CALIB_REPORT §1 呈报的 sell 饥饿红即此形态)。
LIVENESS_ESCALATION_N: int = 40


def action_family_liveness_gate(n: int = 10, seed_base: int = 0,
                                **sim_kwargs: Any) -> dict:
    """动作族活性下限守卫(正式 A/B 前置步;2026-09-03 零刷新事故对策)。

    预跑 n 局(默认 10),每个动作族(刷新/升级/买/卖)在**每臂**上发射
    ≥1 次,或该族全部发射路径 fail-closed 于某未标定 provisional 槽位
    (从槽位状态自动推导的「本臂 fail-closed 豁免清单」)——否则进入
    **升级扫描**(追加重 seed 段的 ``LIVENESS_ESCALATION_N`` 局,仅对
    零发射族所在臂;FIX_REVIEW_20260903 复审返工批),升级段仍零发射
    才 raise「疑似结构性饥饿」。这是组合性检查对不可得的组合证明的
    实用下界:无法证明「各判据面组合后仍可达」,至少证明「每族在真实
    语料上活过」;升级段防「低频活路径」被固定 seed 段误判死路。
    边界:存在性证明而非分布断言(≥1 次不保证量级健康,量级归判前锁);
    池指纹守卫同其它门(非单元素 raise)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
        provisional,
    )

    arms: list[tuple[str, Any]] = [
        ('mandate_v1', MandateV1Strategy(registry=sim_decision_registry())),
    ]
    fps: set[str] = set()
    starved: list[str] = []
    report: dict[str, dict[str, Any]] = {}
    for label, strategy in arms:
        counts: dict[str, int] = dict.fromkeys(ACTION_FAMILY_TYPES, 0)
        for i in range(n):
            res = simulate_p1(seed_base + i, strategy=strategy,
                              **sim_kwargs)
            fps.add(res.pool_fingerprint)
            for row in (res.ledger or []):
                for act in (row.get('actions') or []
                            if isinstance(row, dict) else []):
                    t = (act.get('__type__') if isinstance(act, dict)
                         else type(act).__name__)
                    for fam, types in ACTION_FAMILY_TYPES.items():
                        if t in types:
                            counts[fam] = counts.get(fam, 0) + 1
        exempt: dict[str, str] = {}
        for fam, slots in FAMILY_PROVISIONAL_DEPS.items():
            # 豁免判据:该族依赖的槽位全部处 None 期(fail-closed 降级),
            # 任一槽位有值即豁免失效(开闸路径存在却零发射=饥饿)。
            if slots and all(provisional.is_none(s) for s in slots):
                exempt[fam] = 'fail-closed:' + ','.join(slots)
        fam_starved = sorted(
            fam for fam, c in counts.items() if c < 1 and fam not in exempt)
        escalated = 0
        if fam_starved:
            # 升级扫描(复审返工批):换 seed 段复扫,只补零发射族的
            # 存在性证据;升级段计入同一 counts/fps(池指纹守卫同辖)
            for i in range(n, n + LIVENESS_ESCALATION_N):
                res = simulate_p1(seed_base + i, strategy=strategy,
                                  **sim_kwargs)
                fps.add(res.pool_fingerprint)
                escalated += 1
                for row in (res.ledger or []):
                    for act in (row.get('actions') or []
                                if isinstance(row, dict) else []):
                        t = (act.get('__type__') if isinstance(act, dict)
                             else type(act).__name__)
                        for fam, types in ACTION_FAMILY_TYPES.items():
                            if t in types:
                                counts[fam] = counts.get(fam, 0) + 1
                fam_starved = sorted(
                    fam for fam, c in counts.items()
                    if c < 1 and fam not in exempt)
                if not fam_starved:
                    break
        report[label] = {'counts': counts, 'exempt': exempt,
                         'starved': fam_starved,
                         'escalated_runs': escalated}
        starved += [f'{label}:{fam}' for fam in fam_starved]
    _require_single_fingerprint(fps, '活性守卫')
    # 症4 强制落档:豁免清单快照随守卫产物走(判读产物消费位=
    # formal_ab_prereg_manifest;零刷新事故形态=守卫自动豁免而无落档)
    _LIVENESS_EXEMPT_DISCLOSURE.clear()
    for label, arm in report.items():
        if arm['exempt']:
            _LIVENESS_EXEMPT_DISCLOSURE[label] = dict(arm['exempt'])
    if starved:
        raise RuntimeError(
            f'疑似结构性饥饿(动作族活性下限守卫,正式 A/B 前置步): '
            f'{starved};报告={report}')
    return {'n': n, 'arms': report, 'ok': True,
            'sell_evidence_scope': 'shop 侧发射位仅(prep 侧无 sim 证据'
                                   ',IMPL_ADV_R200 症7)',
            'pool_fingerprint': sorted(fps)[0] if fps else None}


#: 批事件登记(判前锁 v6 清单中「未来批事件时间戳序」类判据的数据源;
#: 进程内易失——正式 A/B 入口脚本须先重放登记本批之前的批事件)
_BATCH_EVENTS: dict[str, float] = {}

#: v6 清单行的人工落地申报(row → 证据文本;进程内缓存,权威=落盘文件)
_V6_LANDINGS: dict[int, str] = {}

#: mark 行 evidence 的持久化落盘文件(v6 判前锁清理批增补:外部交叉
#: 评审 2026-09-03 首轮建议级落地——A/B 重跑门压在「进程内易失」最弱
#: 一环,判读产物须跨进程可审计)。jsonl 逐行 = {row, evidence,
#: recorded_at, context};重复登记以首行为准;checklist 复验从本文件
#: 回读核对(缺文件/缺 evidence 字段/纯空白 = 行红)。测试用
#: ``_V6_LANDING_FILE_OVERRIDE`` 重定向到 tmp_path(测试零真实 .debug)。
_V6_LANDING_FILE = Path('.debug/temp/currency_war/core_swap/'
                        'v6_landing.jsonl')
_V6_LANDING_FILE_OVERRIDE: Path | None = None


def _v6_landings_path() -> Path:
    return _V6_LANDING_FILE_OVERRIDE or (_repo_root() / _V6_LANDING_FILE)


def _load_v6_landings_from_disk() -> dict[int, str]:
    """回读落盘的 v6 mark 行申报(持久权威;坏行=缺 evidence/纯空白
    ⇒ 该行不入有效集 = checklist 红——测试锁的死锁形态)。"""
    import json

    p = _v6_landings_path()
    if not p.exists():
        return {}
    out: dict[int, str] = {}
    for line in p.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue  # 坏行不入有效集(该行红),不炸整个回读
        row, ev = entry.get('row'), entry.get('evidence')
        if (isinstance(row, int) and isinstance(ev, str) and ev.strip()
                and row not in out):
            out[row] = ev
    return out

#: 正式 A/B 的显式豁免批文登记(slot → 批文文本;IMPL_ADV_R200 症4)。
#: V_GAP 处 None 期要开正式 A/B,唯一合法通道 = 本登记携带非空批文
#: (豁免≠行为面开闸:CALIB_REPORT_V2 §2.2/§3——刷新族两臂恒等关闭,
#: B1/B2 含共同降级分量,headline 必须披露)。批文随 A/B 判读产物
#: 落档并强制消费(``formal_ab_prereg_manifest`` ⇒ ab_judge v6 拒读
#: 缺 prereg 块的 formal 批)。
_FORMAL_AB_EXEMPTIONS: dict[str, str] = {}

#: 活性守卫最近一次运行的豁免清单快照(臂 → {族: 豁免原因})。
#: 症4 强制消费半边:守卫自动豁免不落档 = 零刷新事故形态(守卫绿、
#: 事故配置照进判读)——正式 A/B 前置读单必须携带本快照,ab_judge
#: v6 侧对 manifest 里的豁免块与判读产物一致性设防。
_LIVENESS_EXEMPT_DISCLOSURE: dict[str, dict[str, str]] = {}


def record_formal_ab_exemption(slot: str, ruling: str) -> None:
    """登记正式 A/B 的槽位豁免批文(显式豁免通道;IMPL_ADV_R200 症4)。

    纪律同 ``record_v6_landing``:批文缺/空/纯空白 = 拒绝(raise)——
    「豁免在案」必须携带可审计批文文本(谁裁、为何豁免、披露义务),
    防随意豁免。重复登记以首次为准(批文不可事后改写)。
    """
    if not isinstance(ruling, str) or not ruling.strip():
        raise ValueError(
            f'正式 A/B 豁免批文({slot})必须携带非空 ruling'
            '(IMPL_ADV_R200 症4:空批文=不豁免)')
    _FORMAL_AB_EXEMPTIONS.setdefault(slot, ruling)


def record_batch_event(event_id: str) -> None:
    """登记一个批事件(标定批/开闸批/落码批验收时刻)。

    事件 id 约定(与 IMPL_DESIGN §5.1 v6 清单行 3/8/9/12 对应):
    ``theta_calib`` / ``p_open`` / ``eta_theta_calib`` / ``chi_calib`` /
    ``switchline_anchor_batch`` / ``bandwidth_calib`` 等;重复登记以首次
    为准(批边界不可漂移)。
    """
    import time

    _BATCH_EVENTS.setdefault(event_id, time.time())


def record_v6_landing(row: int, evidence: str, context: str = '') -> None:
    """申报 v6 清单某行已落地(带证据文本;重复申报以首次为准)。

    硬化(FIX_REVIEW_20260903 场景 B 复验项):evidence 缺/空/纯空白
    = 拒绝申报(raise)——mark 行「已落地」必须携带可审计证据文本,
    防随意标绿;checklist 侧独立复验(空证据=行红),不单靠本入口。
    持久化(v6 判前锁清理批增补,外部交叉评审 2026-09-03 首轮建议级
    落地):evidence 连同行号/时间戳/标记者语境(``context``,如批名/
    裁定出处)追加落盘 ``v6_landing.jsonl``(A/B 判读产物目录族)——
    进程内易失边界收口,跨进程 checklist 回读核对同一文件;重复登记
    以落盘首行为准(证据不可事后改写)。
    """
    import json
    import time

    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError(
            f'v6 mark 行 {row} 申报必须带非空 evidence'
            '(FIX_REVIEW_20260903 v6 硬化:evidence 缺/空=不落地)')
    _V6_LANDINGS.setdefault(row, evidence)
    if row in _load_v6_landings_from_disk():
        return  # 落盘首行为准:不追加、不改写
    p = _v6_landings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    entry = {'row': row, 'evidence': evidence,
             'recorded_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
             'context': context}
    with p.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def _repo_root() -> Any:
    from pathlib import Path

    return Path(__file__).resolve().parents[5]


def _text_of(rel: str) -> str:
    p = _repo_root() / rel
    try:
        return p.read_text(encoding='utf-8')
    except OSError:
        return ''


def _v6_row_specs() -> list[dict[str, Any]]:
    """§5.1 判前锁 v6 挂账单一源清单的逐行可执行判据。

    行号/条目=IMPL_DESIGN §5.1「判前锁 v6 挂账单一源清单」(R44-7;
    16 行)+ 行 17(V_GAP 事故防护,IMPL_ADV_R200 症4 落地——v6 判前
    锁清理批;清单单一源纪律:新增挂账条目入 §5.1 本表,本函数为可
    执行镜像)。check 类型:``text``=仓库文本锚(自动);``mark``=文档/
    流程证据的人工申报(``record_v6_landing``);``order``=批事件时间
    戳序(类条款行,R94-6:对账时点=该事件所在批验收时点,事件未到期
    不阻塞 v6 声明/正式 A/B,已到期则序违=未落地);``calib``=运行时
    标定注入态判据(行 17:V_GAP 非 None,或显式豁免批文在档——纯
    程序性前置的代码化,防护 2026-09-03 零刷新事故形态复演)。
    """
    return [
        {'row': 1, 'kind': 'text',
             'detail': 'ab_judge 词表含 mandate_v1/ev_arm',
             'ok': lambda: all(t in _text_of('tools/cw/ab_judge.py')
                            for t in ('mandate_v1', 'ev_arm'))},
        {'row': 2, 'kind': 'mark',
             'detail': '判读器迁移与 v6 变更均落地(prereg 含 v6 变更记录节)',
             # 原锚文档 2026-09 用户裁定删除(prereg 目录,主仓 84370361);
             # hint 不再读文件——判读器迁移的机器锚由行 1 承担,本行
             # 申报照常走 record_v6_landing,原文以 git 历史为准
             'hint': lambda: 'prereg 文档已删,git 历史 84370361 可溯'},
        {'row': 3, 'kind': 'order', 'before': 'theta_calib', 'after': 'p_open',
             'detail': '血线阈值标定 ≤ p 开闸(时间戳序)'},
        {'row': 4, 'kind': 'mark',
             'detail': '锚批/判读批分离(拆半方案预注册)'},
        {'row': 5, 'kind': 'mark',
             'detail': '激活率门验收口径重开+预注册(非窗口相位)'},
        {'row': 6, 'kind': 'deferred_mark',
             'detail': 'P3 fallback 9→CI 上端治本落地事件入变更记录'
                       '(批边界约束,非落地前置——R43-3 治本异步化)'},
        {'row': 7, 'kind': 'text',
             'detail': 'f7_contingency_armed 置位/复位事件进判读记录格式'
                    '(telemetry schema 含该键)',
             'ok': lambda: 'f7_contingency_armed' in _text_of(
                 'src/sr_od/application/currency_war/telemetry/schema.py')},
        {'row': 8, 'kind': 'order', 'before': 'eta_theta_calib', 'after': 'p_open',
             'detail': 'η/θ 标定 ≤ p 开闸(时间戳序)'},
        {'row': 9, 'kind': 'order', 'before': 'chi_calib',
             'after': 'switchline_anchor_batch',
             'detail': 'χ 标定 ≤ 换线判读锚批(时间戳序)'},
        {'row': 10, 'kind': 'mark',
             'detail': '激活率门锚/#T 按相位分键重开+预注册(窗口相位)'},
        {'row': 11, 'kind': 'text',
             'detail': 'depsilon_advisor_violation 漂移哨兵语义'
                    '(telemetry schema 含该键)',
             'ok': lambda: 'depsilon_advisor_violation' in _text_of(
                 'src/sr_od/application/currency_war/telemetry/schema.py')},
        {'row': 12, 'kind': 'order', 'before': 'bandwidth_calib',
             'after': 'eta_theta_calib',
             'detail': 'D_ε 带宽与 η 同批标定(时间戳一致)'},
        {'row': 13, 'kind': 'text',
             'detail': 'f7_exempt_emission 观察键(telemetry schema 含该键)',
             'ok': lambda: 'f7_exempt_emission' in _text_of(
                 'src/sr_od/application/currency_war/telemetry/schema.py')},
        {'row': 14, 'kind': 'deferred_mark',
             'detail': 'P2 段档位登记批 ≤ P2_IDLE_SWITCH_W 激活'
                       '(W=None 期判据=判读报告含 FM-1 敞口声明段,'
                       'R81-1 原文)'},
        {'row': 15, 'kind': 'deferred_mark',
             'detail': '01 §4.4 [41] S 公式物理补指针(落码批验收)'},
        {'row': 16, 'kind': 'deferred_mark',
             'detail': '01 §4.1 [17] 息律三处字面参数化核读(落码批验收)'},
        {'row': 17, 'kind': 'calib',
             'detail': 'formal A/B ⟹ V_GAP 注入态(或显式豁免批文落档)'
                       '(IMPL_ADV_R200 症4:零刷新事故防护)',
             # 豁免须绑定 V_GAP 槽位(V6_CLEANUP_REVIEW F2:对无关槽位
             # 登记批文不得解锁本行——判前锁防蓄意误用)。
             'ok': lambda: (not _vgap_is_none())
                 or ('V_GAP' in _FORMAL_AB_EXEMPTIONS)},
    ]


def _vgap_is_none() -> bool:
    from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
        provisional,
    )

    return provisional.is_none('V_GAP')


#: 预注册强制披露计数键族(CALIB_REPORT_V2 §3.2 裁决附条件①;
#: U_X/T_SEARCH_A 豁免 ⇒ EV 买/压库/M6/凑息卖面两臂恒等关闭,
#: B1/B2 含「共同降级代价」分量,headline 必须随附这些计数)。
#: ``shop_r1_`` 为前缀族(ev_unavailable/account_over_vgap/
#: no_chaseable_member 分键,shop.py 发射位现读)。
DISCLOSURE_COUNTER_KEYS: tuple[str, ...] = (
    'shop_ev_u_unavailable', 'm6_overflow_strand')
DISCLOSURE_COUNTER_PREFIXES: tuple[str, ...] = ('shop_r1_',)


def cw4_disclosure_from_session(session: Any) -> dict[str, int]:
    """从局内 session 的 cw4_counters 抽取披露计数(预注册①的数据源)。

    正式 A/B 跑批时逐臂逐局聚合(``session`` 由 simulate_p1 注入),
    结果写进批次 manifest 的 ``cw4_disclosure`` 块——ab_judge v6 判读
    强制消费(缺块拒读),与 headline 一并输出。
    """
    counters = getattr(session, 'cw4_counters', None) or {}
    return {k: v for k, v in counters.items()
            if k in DISCLOSURE_COUNTER_KEYS
            or any(k.startswith(p) for p in DISCLOSURE_COUNTER_PREFIXES)}


def formal_ab_prereg_manifest() -> dict:
    """正式 A/B 判读产物的 prereg 块(判前锁 v6 前置的落档形态)。

    内容:v6 检查单全文 + V_GAP 注入态 + 显式豁免批文 + 活性守卫豁免
    快照。症4 强制消费链:跑批侧把本块序列化进各臂批次 manifest
    (``formal_ab_prereg`` 键)——ab_judge v6 拒读缺块/未绿/豁免不一致
    的 formal 批(判读器侧防线,与本模块 require 双防线)。
    """
    rows = v6_checklist()
    return {
        'v6_rows': rows,
        'v6_ok': not [r for r in rows if r['status'].startswith('未落地')],
        'vgap_state': 'none' if _vgap_is_none() else 'injected',
        'formal_ab_exemptions': dict(_FORMAL_AB_EXEMPTIONS),
        'liveness_exempt_disclosure': {
            k: dict(v) for k, v in _LIVENESS_EXEMPT_DISCLOSURE.items()},
    }


def v6_checklist() -> list[dict[str, Any]]:
    """判前锁 v6 单一源清单的可执行对账(逐行 已落地/未落地/未到期)。

    出处:2026-09-03 零刷新事故后编排者裁定——把 §5.1 v6 清单代码化为
    正式 A/B 硬前置,防「派单漏硬前置」复发(该事故的排程层根因)。
    边界:text 行是仓库文本锚的自动判据(词表/schema 键);mark 行须
    批操作者 ``record_v6_landing(row, evidence)`` 显式申报且 **evidence
    非空**(FIX_REVIEW_20260903 v6 硬化:空/纯空白证据=行红,入口侧
    raise+本侧复验双防线;证据文本随行输出供审计);order 行按
    R94-6 类条款——事件未到期读「未到期(不阻塞)」,已到期则验序;
    deferred_mark 行(6/14/15/16)同属 R94-6 类条款镜像(判据=未来批
    事件/W=None 期披露义务,详见 checklist 分支注释)——未申报读
    「未到期(不阻塞)」,判读侧按 PREREG 披露义务消费其现状态。
    """
    rows: list[dict[str, Any]] = []
    for spec in _v6_row_specs():
        row = {'row': spec['row'], 'item': spec['detail']}
        if spec['kind'] == 'text':
            row['status'] = '已落地' if spec['ok']() else '未落地'
        elif spec['kind'] == 'mark':
            # 持久化复验(v6 清理批增补):evidence 权威=落盘文件回读
            # (v6_landing.jsonl;跨进程可审计),进程内缓存仅补文件未及
            # 行;两侧皆缺/空 ⇒ 行红,不因「申报过」即绿
            ev = _load_v6_landings_from_disk().get(spec['row'])
            if ev is None:
                ev = _V6_LANDINGS.get(spec['row'])
            landed = bool(ev and ev.strip())
            row['status'] = '已落地' if landed else '未落地'
            if ev:
                row['evidence'] = ev
            if 'hint' in spec and not landed:
                row['hint_pass'] = bool(spec['hint']())
        elif spec['kind'] == 'deferred_mark':
            # R94-6 类条款镜像补全(2026-09-03 编排者裁决,A/B 重跑
            # preflight 红行暴露):行 6/14/15/16 的落地判据系未来批事件
            # 或 W=None 期披露义务,设计原文均非 v6 声明时点硬前置——
            # 行 6=批边界约束(事件若发生不落判读批中途,R43-3 异步化);
            # 行 14=W=None 期判据=判读报告含 FM-1 敞口声明段(R81-1
            # 原文),W 激活后才验登记批时间戳序;行 15/16=R94-6/R99
            # 明文入类(落码批验收)。有 landing evidence=已落地;
            # 无=未到期(不阻塞,checklist 可见供判读披露)。
            ev = _load_v6_landings_from_disk().get(spec['row'])
            if ev is None:
                ev = _V6_LANDINGS.get(spec['row'])
            landed = bool(ev and ev.strip())
            row['status'] = '已落地' if landed else '未到期(类条款,不阻塞)'
            if ev:
                row['evidence'] = ev
        elif spec['kind'] == 'calib':
            # 行 17(症4):运行时标定注入态判据——V_GAP 非 None 或显式
            # 豁免批文在档;两读皆缺 = 未落地(零刷新事故形态,红)
            row['status'] = '已落地' if spec['ok']() else '未落地'
        else:  # order
            t_after = _BATCH_EVENTS.get(spec['after'])
            if t_after is None:
                row['status'] = '未到期(类条款,不阻塞)'
            else:
                t_before = _BATCH_EVENTS.get(spec['before'])
                ok = t_before is not None and t_before <= t_after
                row['status'] = '已落地' if ok else '未落地(序违)'
        rows.append(row)
    return rows


def require_v6_green_for_formal_ab() -> dict:
    """正式 A/B 入口判前锁 v6 检查单(未全绿 raise)。

    未落地(含序违)任一行 ⇒ raise——本批 sim 数据不得进 ab_judge 判读
    门(IMPL_DESIGN §5.1 R19 硬前置的代码化);「未到期(类条款)」行
    不阻塞(R94-6:对账时点=该事件所在批验收时点)。行 17(症4)把
    2026-09-03 零刷新事故的最小充分条件代码化:V_GAP=None 开 formal
    A/B 且无显式豁免批文 ⇒ 红。返回检查单全文 + prereg 落档块
    (供跑批侧序列化进批次 manifest,ab_judge v6 强制消费)。
    """
    rows = v6_checklist()
    bad = [r for r in rows if r['status'].startswith('未落地')]
    if bad:
        raise RuntimeError(
            '判前锁 v6 检查单未全绿,正式 A/B 不得开跑(IMPL_DESIGN '
            '§5.1 R19 硬前置): '
            + '; '.join(f"行{r['row']}:{r['item']}" for r in bad))
    return {'rows': rows, 'ok': True,
            'prereg_manifest': formal_ab_prereg_manifest()}
