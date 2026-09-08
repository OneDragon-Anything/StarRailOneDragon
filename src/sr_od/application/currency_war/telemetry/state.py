"""telemetry 模块级可变单例态簇(自 cw_telemetry 前置收敛,分包期6)。

本模块是全部模块级可变单例(run_id/recorder/暂存缓冲/安灯 handler/缺陷
复现位)的唯一拥有者:其他段(schema/recorder/defects/query/cli)一律以
``state.X`` 属性访问读取,赋值只发生在本模块内(含 global 声明的变更器
函数),防 import 绑定快照读到过期值。
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from one_dragon.utils import log_utils  # 67-P1c 指纹哨兵日志
from sr_od.application.currency_war.kernel.cw_state import (
    GameState,
    bench_occupied,
)

# 符号解耦(处死计划批 0):序列化权威副本迁 knowledge/cw_serialize,
# 不再依赖 kernel/cw_intention(死刑判据文件)
from sr_od.application.currency_war.knowledge.cw_serialize import _to_jsonable
from sr_od.application.currency_war.telemetry.schema import ExogenousEvent

if TYPE_CHECKING:
    # 惰性构造防模块级环:recorder/hooks 段在模块级依赖本模块(state),
    # 反向只允许函数内延迟 import(原单文件同命名空间直引,语义不变)。
    from sr_od.application.currency_war.telemetry.recorder import TelemetryRecorder


log = log_utils.log

        # 只写 defect_ledger 一条流:台账是「归一索引层」,spend_ledger 是
        # 「原始证据层」(单元框架事实,消费端 query_spend_ledger 按
        # SpendUnitRecord 字段解析)——缺陷行混入会被当伪单元误读。


# ===== 模块级单例 + run_id 跟踪(ops 不改签名即可采集)=====
# telemetry 是横切关注点,用模块级 recorder + current_run_id,避免给 BuyShopCards / loop
# 线程传参。run_id 铸造单点 = ensure_run_started(入口链在写任何开局遥测行前铸造,
# loop 侧认领,ADR-0588);BuyShopCards 用 current_run_id() 取,loop 在战斗后
# record_outcome、局终 record_run_summary。
# 默认 enabled=True(用户 2026-08-03 要数据调优;写 .debug/ 不入 git,I/O <1ms 不影响备战实时)。
_RECORDER: TelemetryRecorder | None = None

_CURRENT_RUN_ID: str = ""

_CURRENT_DIFFICULTY: str = ""

# ADR-0588:铸造时点的 match 容器引用 token。ensure_run_started 用「is 比较」
# 判当前 open run 是否属于这个物理对局(不用 id()——规避对象复活后 id 复用;
# 强引用滞留一个死容器,内存代价可忽略)。None = 尚未铸造或铸造时无容器
# (重启后中途进局,ctx.cw_match=None 直达投资屏的形态)。
_RUN_MATCH: object | None = None

# r339:ctx.cw_match 弱引用槽(record_outcome 板深快照源;
# cw_loop 启动 run 时注册,None=离线/测试容错)
_CTX_MATCH_REF: list = [None]


# —— 迁移审计 w306(git 历史):补给节点选择暂存槽(生产者=RunSupplyNode 选定/确认时;消费者=
# cw_loop._record_supply_outcome 合成行落账时一次消费)。
# 为什么是模块槽而不是 session 字段:StrategySession(cw_strategy.py,归属他批禁触)
# 无法加正式字段;OperationRoundResult 状态串传 dict 是解析层凑合。单线程 op 链内
# 生产→消费紧邻(选卡确认 → overlay 消失即合成),无并发风险;消费即清=残留不串轮。
_LAST_SUPPLY_PICK: dict[str, Any] | None = None



def set_last_supply_pick(char: str, equip: str, has_diamond: bool,
                         refreshed: bool,
                         options: list[dict[str, Any]] | None = None) -> None:
    """生产者:补给节点本轮选定并确认的选项(char/equip 读自 read_supply_options;
    refreshed=exec_state_of(session)._supply_refresh_used 时点值——刷新在确认前一轮发生,
    True=该选项来自重掷后的牌面)。
    options(迁移审计 w306c(git 历史)):**实际识别到的逐列内容** [{char,equip,has_diamond}...],
    列数动态探测不写死(通常 4,augment 可变 3-5);读不到选项目标路径可不传。"""
    global _LAST_SUPPLY_PICK
    _LAST_SUPPLY_PICK = {'char': str(char or ''), 'equip': str(equip or ''),
                         'has_diamond': bool(has_diamond), 'refreshed': bool(refreshed)}
    if options:
        _LAST_SUPPLY_PICK['options'] = [dict(o) for o in options]
        _LAST_SUPPLY_PICK['n_options'] = len(options)



def consume_last_supply_pick() -> dict[str, Any] | None:
    """消费者:取走暂存的选择快照并清槽(一次消费;无暂存 → None)。"""
    global _LAST_SUPPLY_PICK
    pick = _LAST_SUPPLY_PICK
    _LAST_SUPPLY_PICK = None
    return pick



# —— 金面收口:关店实读金暂存槽 ——
# 为什么是槽而不是 shop.py 直接调 record_spend_unit:spend_ledger 行的唯一
# 生产者是 director 的执行边界(行=单元框架事实),shop 只握有关店时点的
# 真值列;行在 execute 返回后才落,shop 侧无法定向补列,故经暂存槽由既有
# 落账入口消费(消费即清,残留不串单元)。与 _LAST_SUPPLY_PICK 同模式。
_PENDING_UNIT_GOLD_CLOSE: dict[str, Any] | None = None



def set_unit_gold_close(gold: int | None) -> None:
    """生产者(shop.py 关店对拍点):无条件暂存关店实读金。

    gold=None(read_gold 失读)也照记——unknown 占比要降到「读失败率」,
    失读必须以 trusted=False 形态可见,不可静默缺失(否则「对拍通过」与
    「失读」离线仍不可分)。
    """
    global _PENDING_UNIT_GOLD_CLOSE
    _PENDING_UNIT_GOLD_CLOSE = {'gold': gold, 'trusted': gold is not None}



def _consume_unit_gold_close() -> tuple[int | None, bool]:
    """消费者(模块级 record_spend_unit 落账时):取走暂存并清槽。"""
    global _PENDING_UNIT_GOLD_CLOSE
    slot = _PENDING_UNIT_GOLD_CLOSE
    _PENDING_UNIT_GOLD_CLOSE = None
    if slot is None:
        return None, False
    return slot.get('gold'), bool(slot.get('trusted'))



# —— 执行侧「计划≠尝试」可见化暂存槽(`w577_refresh_fee_and_andon/`,ADR-0456)——
# 与 _PENDING_UNIT_GOLD_CLOSE 同模式同理由:shop.py 执行循环握有「计划了但
# 未尝试/刷新点击后牌面变没变」的执行事实,spend_ledger 行由 director 边界
# 落账,经本槽由既有落账入口消费(消费即清,残留不串单元)。
_PENDING_UNIT_EXEC: dict[str, Any] | None = None



def set_unit_exec_facts(*, plan_truncated: bool = False,
                        refresh_skipped: str | None = None,
                        refresh_attempted: bool = False,
                        refresh_board_changed: bool | None = None) -> None:
    """生产者(shop.py 执行循环):暂存本单元「计划≠尝试」执行事实。

    plan_truncated=True = plan 含未尝试动作(硬墙跳过/至首个 RefreshShop
    截断丢弃);refresh_attempted/board_changed 供分类器三分「点击落空 vs
    免费生效」。只在有事实可报时调用(全缺省不必调)。
    """
    global _PENDING_UNIT_EXEC
    _PENDING_UNIT_EXEC = {
        'plan_truncated': bool(plan_truncated),
        'refresh_skipped': refresh_skipped,
        'refresh_attempted': bool(refresh_attempted),
        'refresh_board_changed': refresh_board_changed,
    }



def _consume_unit_exec_facts() -> dict[str, Any]:
    """消费者(模块级 record_spend_unit 落账时):取走暂存并清槽;无暂存=缺省。"""
    global _PENDING_UNIT_EXEC
    slot = _PENDING_UNIT_EXEC
    _PENDING_UNIT_EXEC = None
    return slot or {}



def set_ctx_match(match) -> None:
    """注册当前 ctx.cw_match(板深快照源;run 边界换新)。"""
    _CTX_MATCH_REF[0] = match



# ===== 落盘根装配槽(T-120 批 1,F4)=====
# 为什么是槽:get_recorder() 单例构造不传 replay_dir(缺省 DEFAULT_REPLAY_DIR,
# kernel/cw_observe 根常量块),假局档案要改指档案根原本只能私 poke
# ``_RECORDER``——与 install_obs_ports「模块级槽 + 缺省关 + 装配点显式接通」
# 同构的正规入口(方案 §4-2 落盘根装配槽申报)。缺省 None = 生产路径逐位
# 不变;测试 harness 显式接指假局档案根。换根即重建单例:recorder 的内存
# 累积(gold 轨迹/难度表)按根隔离,半途换根复用旧实例会把上一根的累积
# 写进新根。
_REPLAY_DIR_OVERRIDE: Path | None = None


def set_recorder_replay_dir(path: Path | None) -> None:
    """接通/复位 recorder 落盘根装配槽。

    ``path=None`` = 复位生产缺省(DEFAULT_REPLAY_DIR);已构造的 recorder
    单例随之丢弃,下次 :func:`get_recorder` 按新根惰性重建。测试 teardown
    必调复位——模块槽是进程全局,残留会把后续测试的遥测写进假局根。
    """
    global _REPLAY_DIR_OVERRIDE, _RECORDER
    _REPLAY_DIR_OVERRIDE = Path(path) if path is not None else None
    _RECORDER = None


def get_recorder() -> TelemetryRecorder:
    """模块级 recorder 单例(默认 enabled,写 .debug/currency_war/telemetry/live/)。

    落盘根 = :func:`set_recorder_replay_dir` 接通的装配槽值;槽缺省 None
    时走生产缺省根(kernel/cw_observe.DEFAULT_REPLAY_DIR)——两者互斥,
    槽只改根不改 enabled 等其余构造面。
    """
    global _RECORDER
    if _RECORDER is None:
        from sr_od.application.currency_war.telemetry import recorder as _rec_mod
        if _REPLAY_DIR_OVERRIDE is not None:
            _RECORDER = _rec_mod.TelemetryRecorder(enabled=True,
                                                   replay_dir=_REPLAY_DIR_OVERRIDE)
        else:
            _RECORDER = _rec_mod.TelemetryRecorder(enabled=True)
    return _RECORDER



def start_run(difficulty: str = "") -> str:
    """开始一次 run:生成 run_id(时间戳)+ start_run。返回 run_id。

    ADR-0588:生产铸造统一经 :func:`ensure_run_started`(入口链在写开局
    遥测行前调用;直调本函数仅存在于测试)。函数体零改动保留——w603 简报
    缓冲补写与测试桩面都锚在这里。

    ADR-0273:开局先补上一局(们)缺的 summary 行 —— FAIL/崩溃/重启杀局路径
    不走 3c/stop 收口,此处在下一局起点从 outcomes/decisions 重算兜底(幂等)。
    """
    global _CURRENT_RUN_ID, _CURRENT_DIFFICULTY, _RUN_CLOSED
    try:
        from sr_od.application.currency_war.sim import ledger_hooks as _lh
        _lh.recover_dangling_run_summaries()
    except Exception as e:   # noqa: BLE001  兜底 best-effort,不阻塞开局
        log.warning('[cw][telemetry] summary 兜底回填失败(不阻塞开局): %s', e)
    _CURRENT_RUN_ID = datetime.now().strftime('run_%Y%m%d_%H%M%S')
    _CURRENT_DIFFICULTY = difficulty
    _RUN_CLOSED = False
    get_recorder().start_run(_CURRENT_RUN_ID, difficulty)
    # `w603_telemetry_wiring/`:局前缓冲的简报行归属本局,新 run_id 就位后补写
    with contextlib.suppress(Exception):
        _flush_pending_briefing_rows()
    # 构建指纹随局落日志(`w596_equip_guards/`/`w593_equip_wear/` 方案①):局后判读把本局行为对到
    # 「哪个构建的进程」,消灭「整局构建性归零」这类跨局方差(局22 实证)。
    try:
        from sr_od.backend.build_info import get_build_fingerprint
        log.info('[cw][build] run=%s 构建指纹=%s', _CURRENT_RUN_ID,
                 get_build_fingerprint())
    except Exception as e:   # noqa: BLE001  观测件,失败不阻塞开局
        log.warning('[cw][build] 构建指纹读取失败(不阻塞): %s', e)
    return _CURRENT_RUN_ID



def ensure_run_started(match: object, difficulty: str) -> str:
    """幂等开局:写任何本局遥测行前确保有归属本局的 open run(ADR-0588)。

    门控三分支任一成立 → 经 start_run 铸新 run(本体零改动),并在其返回后
    自赋 _RUN_MATCH token(token 赋值在 ensure 内不进 start_run——保
    start_run 签名/函数体原样,w603 直调锁零波及);否则认领现有 open run
    原样返回(同一物理对局一段一 id)。三分支语义:

    - ``_CURRENT_RUN_ID`` 空:进程首局/重启后首铸造(治冷启动首局零行);
    - ``_RUN_CLOSED``:上局已收口,正常开新局(跨 loop 执行必然已收口,
      after_operation_done 全路径必达写 summary);
    - ``_RUN_MATCH is not match``:悬空 open run 防护——入口铸造后入口链
      FAIL 的 run 不收口;新局确凿信号处容器被弃置重建(cw_entry_start
      ``_discard_stale_once`` + establish),新容器 ≠ 铸造时容器 → 强制
      重铸,防新局开局行盖进上次失败会话的悬空 run。

    「继续进度」恢复路径:入口不走铸造分支 → loop 侧 ensure 见 _RUN_CLOSED
    铸新段 = 续段语义,与 ADR-0460 时代的担忧由本门控显式覆盖。

    生产铸造唯一调用点 = 本函数(cw_entry_start 简报/投资环境/投资策略三分
    支 + cw_loop __init__ 认领)。返回 open run_id。
    """
    global _RUN_MATCH
    if (not _CURRENT_RUN_ID) or _RUN_CLOSED or (_RUN_MATCH is not match):
        run_id = start_run(difficulty)
        _RUN_MATCH = match
        return run_id
    return _CURRENT_RUN_ID



def current_run_id() -> str:
    return _CURRENT_RUN_ID



def reset_run_state() -> None:
    """run 态簇的测试复位正规入口:清 _CURRENT_RUN_ID/_RUN_MATCH/_RUN_CLOSED
    /_CURRENT_DIFFICULTY/_PENDING_BRIEFING_ROWS 五件。

    为什么收口成单点(ADR-0588 ensure 门消费簇 × 测试复位链缺口):三件套
    分散在三处生产写点(start_run 铸造 / ensure_run_started 赋 token /
    record_run_summary 置收口位),测试侧逐件 monkeypatch 清单漏一件即留
    跨测试残留——实证:假局 harness 局终经生产 record_run_summary 裸写
    _RUN_CLOSED=True,teardown 复位链不覆盖,后续未全簇桩化就直调
    ensure_run_started 的测试把「上局已收口」误判为真走重铸假分支(出处:
    .debug/temp/currency_war/attacks/three_review_20260908/三审报告-第二波.md
    F1,**易失产物**待 ADR 回填;门控三分支语义见 ADR-0588)。

    难度列与简报缓冲两件同簇(出处:.debug/temp/currency_war/attacks/
    three_review_20260908/三审报告-第三波.md F3,**易失产物**待 ADR 回填;
    单一入口判据承本函数既有先例):_CURRENT_DIFFICULTY 由 start_run 与
    _CURRENT_RUN_ID 同语句铸造,消费 = recorder.record_decision 决策行
    难度列;_PENDING_BRIEFING_ROWS 是简报行 run 归属缓冲(下一局
    start_run 把缓冲行补写进新局)。两者残留病理 = 遥测内容污染(后续
    仅桩 run_id 的测试写出带前局难度/错局归属的行),无分支翻转;入簇
    而非散点补桩 = 簇成员随写点扩员自动进复位链,防逐件补桩清单再漏。

    生产路径零调用申报:生产 run 态由 ensure_run_started → start_run →
    record_run_summary 自洽推进(收口位由下一局 start_run 复位),复位
    语义只属于测试 teardown,本函数禁入任何生产调用链。

    边界:只复位 run 态簇五件;_RECORDER 与落盘根两槽有各自正规入口
    (:func:`set_recorder_replay_dir` / ``op_journal.set_journal_dir``),
    teardown 按槽分立调用,职责不混。
    """
    global _CURRENT_RUN_ID, _RUN_MATCH, _RUN_CLOSED
    global _CURRENT_DIFFICULTY, _PENDING_BRIEFING_ROWS
    _CURRENT_RUN_ID = ''
    _RUN_MATCH = None
    _RUN_CLOSED = False
    _CURRENT_DIFFICULTY = ''
    _PENDING_BRIEFING_ROWS = []



# ===== `w603_telemetry_wiring/` 简报行 run_id 归属(局间缓冲)=====
# 生命周期:简报读取(局前)→ start_run 补写;进程终止未遇 start_run = 缓冲丢弃
# (best-effort,与原「行被丢/带错 id」相比只改善不劣化)。上限 16 行 = 简报
# retry 重跑上限(节点 max_retry_times=10)的宽裕倍数,防异常路径无限积压。
_PENDING_BRIEFING_ROWS: list[dict[str, Any]] = []

_PENDING_BRIEFING_MAX: int = 16

#: run 关闭位:局终 summary 落盘后,直到下一局 start_run 前,_CURRENT_RUN_ID
#: 指向已收口的局 —— 此窗口内的 briefing 行归属下一局(经缓冲)。
_RUN_CLOSED: bool = False



def _buffer_briefing_row(round_num: int, detail: str,
                         state: GameState | None) -> None:
    """暂存局前简报行(ts 即刻取,state 快照即刻算;best-effort 不抛)。"""
    global _PENDING_BRIEFING_ROWS
    try:
        snap: dict[str, Any] = {}
        if state is not None:
            snap = {'hp': getattr(state, 'hp', None),
                    'gold': getattr(state, 'gold', None),
                    'level': getattr(state, 'level', None),
                    'plane': getattr(state, 'plane', None),
                    'round_num': getattr(state, 'round_num', None),
                    'bench_count': bench_occupied(
                        getattr(state, 'bench', []) or [])}
        _PENDING_BRIEFING_ROWS.append({
            'ts': datetime.now().isoformat(timespec="seconds"),
            'round_num': round_num, 'detail': detail, 'state_snapshot': snap,
        })
        if len(_PENDING_BRIEFING_ROWS) > _PENDING_BRIEFING_MAX:
            _PENDING_BRIEFING_ROWS = _PENDING_BRIEFING_ROWS[-_PENDING_BRIEFING_MAX:]
    except Exception:  # noqa: BLE001  缓冲 best-effort
        pass



def _flush_pending_briefing_rows() -> None:
    """start_run 建新 run_id 后补写缓冲简报行(归属=新局;按暂存序)。"""
    if not _PENDING_BRIEFING_ROWS:
        return
    pend = list(_PENDING_BRIEFING_ROWS)
    _PENDING_BRIEFING_ROWS.clear()
    for r in pend:
        with contextlib.suppress(Exception):   # 补写 best-effort
            get_recorder()._append("exogenous.jsonl", _to_jsonable(
                ExogenousEvent(ts=r['ts'], run_id=_CURRENT_RUN_ID,
                               round_num=r['round_num'], kind='briefing',
                               detail=r['detail'],
                               state_snapshot=r['state_snapshot'],
                               choice=None)))



def record_run_summary(result: str, plane_reached: int, rounds_survived: int,
                       final_hp: int, notes: str = "") -> None:
    """便捷:用 current_run_id 记局终 summary。loop 局终调。

    `w603_telemetry_wiring/`:落盘后置 run 关闭位 —— 此后到下一局 start_run 前的 briefing 行
    归属下一局(缓冲补写),不再挂在已收口的旧 run_id 上。
    """
    global _RUN_CLOSED
    if not _CURRENT_RUN_ID:
        return
    get_recorder().record_run_summary(_CURRENT_RUN_ID, result, plane_reached,
                                      rounds_survived, final_hp, notes=notes)
    _RUN_CLOSED = True



# —— 复现计数(分级判据③;进程内状态,按 run 切换清空)——
# key=(surface, kind, expected 特征前 80 字符);第 2 次起算复现(§4 判3:
# 同特征连续 2 次/2 帧,所有 L0 都过防抖,单帧永不直接停机)。
_defect_seen: dict[tuple[str, str, str], int] = {}

_defect_seen_run: str = ''



def _mark_defect_reproduced(surface: str, kind: str, feature: str,
                            run_id: str) -> bool:
    """登记一次缺陷特征并返回「是否复现」(进程内防抖计数,best-effort)。"""
    global _defect_seen, _defect_seen_run
    if run_id != _defect_seen_run:
        _defect_seen = {}
        _defect_seen_run = run_id
    key = (surface, kind, feature[:80])
    n = _defect_seen.get(key, 0)
    _defect_seen[key] = n + 1
    return n >= 1


#: 安灯执行器槽(注入式;签名 ``fn(payload: dict) -> bool``,True=已停)。
#: None(缺省)= **不停线**,只记台账+日志——副作用缺省关、显式接通:
#: 生产武装点 = ``CurrencyWarApp.__init__`` 调 ``set_l0_andon_handler``。
#: 禁止改回「缺省惰性调 cw_observe.stop_for_l0_andon」:惰性路径会用 gc
#: 扫描全进程定位 ctx,测试进程里命中 session 级 test_context → 写停机位
#: +真实 flag,污染整个测试会话(全集假红实证;测试漏桩即漏副作用)。
_L0_ANDON_HANDLER: Callable[[dict], bool] | None = None


#: 局级闩锁(首见 L0 即停一次,后续 L0 只补台账不再停)。键=run_id:
#: run_id 由模块级 start_run 每局重新生成(进程内「局」粒度的天然键),
#: 与复现计数的 _defect_seen_run 同款切换语义——跨局自动重置,无需手动清。
_L0_ANDON_FIRED_RUNS: set[str] = set()



def set_l0_andon_handler(fn: Callable[[dict], bool] | None) -> None:
    """注入/清除安灯执行器。生产武装点=CurrencyWarApp.__init__(幂等);
    None=关闭停线通道(缺省;台账与判级不受影响)。"""
    global _L0_ANDON_HANDLER
    _L0_ANDON_HANDLER = fn


