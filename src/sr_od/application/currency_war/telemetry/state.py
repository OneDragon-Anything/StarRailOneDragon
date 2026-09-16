"""telemetry 模块级可变单例态簇(自 cw_telemetry 前置收敛,分包期6)。

本模块是全部模块级可变单例(run_id/recorder/安灯 handler/缺陷复现位)的
唯一拥有者:其他段(schema/recorder/defects/query/cli)一律以
``state.X`` 属性访问读取,赋值只发生在本模块内(含 global 声明的变更器
函数),防 import 绑定快照读到过期值。

删除波 1(用户 2026-09-10 直迁裁定)后本模块只剩「run 生命周期 + 落盘根
槽 + 缺陷台账辅助态」:旧流写入端面临的所有暂存槽(supply pick/单元金收口/
执行事实/简报局间缓冲)与 runs 收口写行随九流写入端退役删除;run 收口位
保留(close_run——run_id 段归属供给 journal run_id provider,收口位驱动
跨局重铸,语义见该函数注)。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from one_dragon.utils import log_utils  # 67-P1c 指纹哨兵日志

if TYPE_CHECKING:
    # 惰性构造防模块级环:recorder/hooks 段在模块级依赖本模块(state),
    # 反向只允许函数内延迟 import(原单文件同命名空间直引,语义不变)。
    from sr_od.application.currency_war.telemetry.recorder import TelemetryRecorder


log = log_utils.log

# ===== 模块级单例 + run_id 跟踪(ops 不改签名即可采集)=====
# telemetry 是横切关注点,用模块级 recorder + current_run_id。run_id 铸造
# 单点 = ensure_run_started(入口链在写任何开局遥测行前铸造,loop 侧认领,
# ADR-0588)。退役后 run_id 的现役消费方 = journal 行归属(kernel
# run_id provider 注入面)与缺陷台账行归属。
# 默认 enabled=True(用户 2026-08-03 要数据调优;写 .debug/ 不入 git,I/O <1ms 不影响备战实时)。
_RECORDER: TelemetryRecorder | None = None

_CURRENT_RUN_ID: str = ""

_CURRENT_DIFFICULTY: str = ""

# ADR-0588:铸造时点的 match 容器引用 token。ensure_run_started 用「is 比较」
# 判当前 open run 是否属于这个物理对局(不用 id()——规避对象复活后 id 复用;
# 强引用滞留一个死容器,内存代价可忽略)。None = 尚未铸造或铸造时无容器
# (重启后中途进局,ctx.cw_match=None 直达投资屏的形态)。
_RUN_MATCH: object | None = None


# ===== 落盘根装配槽 =====
# 为什么是槽:get_recorder() 单例构造不传 replay_dir(缺省 DEFAULT_REPLAY_DIR,
# kernel/cw_observe 根常量块),假局档案要改指档案根原本只能私 poke
# ``_RECORDER``——与 install_obs_ports「模块级槽 + 缺省关 + 装配点显式接通」
# 同构的正规入口(方案 §4-2 落盘根装配槽申报)。缺省 None = 生产路径逐位
# 不变;测试 harness 显式接指假局档案根。换根即重建单例:recorder 单例按根
# 隔离,半途换根复用旧实例会把上一根的累积写进新根。
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
    槽只改根不改 enabled 等其余构造面。退役后现役写入面 = 缺陷台账
    (record_defect);本单例同时是档案装配/计数快照的 replay_dir 供给口。
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
    """开始一次 run:生成 run_id(时间戳)。返回 run_id。

    ADR-0588:生产铸造统一经 :func:`ensure_run_started`(入口链在写任何
    开局遥测行前调用;直调本函数仅存在于测试)。

    删除波 1:局起点两件旧流伴生面随写入端退役——①runs 兜底回填
    (sim/ledger_hooks.recover_dangling_run_summaries,写 runs 行);
    ②简报行局间缓冲补写(写 exogenous 行)。run_id 铸造/指纹日志照常
    (journal 行归属 + 构建指纹随局落日志)。
    """
    global _CURRENT_RUN_ID, _CURRENT_DIFFICULTY, _RUN_CLOSED
    _CURRENT_RUN_ID = datetime.now().strftime('run_%Y%m%d_%H%M%S')
    _CURRENT_DIFFICULTY = difficulty
    _RUN_CLOSED = False
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

    职责边界(用户裁定 2026-09-15):本函数只辖 run 领取(铸造/认领);
    遥测数据的保存 = game state 职责,state 流水装配入口 =
    kernel/cw_game_state :func:`game_state_of` 局容器单例建立路径(触发只钉
    该建立点;生产注入漏斗 =
    ``establish_new_match`` 容器建立点),run 领取层不辖装配。
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
    /_CURRENT_DIFFICULTY 四件。

    为什么收口成单点(ADR-0588 ensure 门消费簇 × 测试复位链缺口):三件套
    分散在三处生产写点(start_run 铸造 / ensure_run_started 赋 token /
    close_run 置收口位),测试侧逐件 monkeypatch 清单漏一件即留
    跨测试残留——实证:假局 harness 局终经生产收口位裸写
    _RUN_CLOSED=True,teardown 复位链不覆盖,后续未全簇桩化就直调
    ensure_run_started 的测试把「上局已收口」误判为真走重铸假分支(出处:
    .debug/temp/currency_war/attacks/three_review_20260908/三审报告-第二波.md
    F1,**易失产物**待 ADR 回填;门控三分支语义见 ADR-0588)。

    难度列入簇(出处:.debug/temp/currency_war/attacks/
    three_review_20260908/三审报告-第三波.md F3,**易失产物**待 ADR 回填;
    单一入口判据承本函数既有先例):_CURRENT_DIFFICULTY 由 start_run 与
    _CURRENT_RUN_ID 同语句铸造。残留病理 = 遥测内容污染,无分支翻转;
    入簇而非散点补桩 = 簇成员随写点扩员自动进复位链,防逐件补桩清单再漏。

    生产路径零调用申报:生产 run 态由 ensure_run_started → start_run →
    close_run 自洽推进(收口位由下一局 start_run 复位),复位
    语义只属于测试 teardown,本函数禁入任何生产调用链。

    边界:只复位 run 态簇四件;_RECORDER 与落盘根两槽有各自正规入口
    (:func:`set_recorder_replay_dir` /
    ``decision_frame_hooks.set_decision_frame_dir``,两槽出处 = 三审
    二波 F2 同报告 F1 节的复位链纪律;op_journal 第三槽随其流退役拆除),
    teardown 按槽分立调用,职责不混。
    """
    global _CURRENT_RUN_ID, _RUN_MATCH, _RUN_CLOSED
    global _CURRENT_DIFFICULTY
    _CURRENT_RUN_ID = ''
    _RUN_MATCH = None
    _RUN_CLOSED = False
    _CURRENT_DIFFICULTY = ''


#: run 关闭位:局终收口后,直到下一局 start_run 前,_CURRENT_RUN_ID
#: 指向已收口的局 —— ensure_run_started 据此在下一局铸造新段
#(journal 行 run 归属的生命周期承接口)。
_RUN_CLOSED: bool = False


def close_run(result: str = "", plane_reached: int = 0,
              rounds_survived: int = 0, final_hp: int = 0,
              notes: str = "") -> None:
    """run 收口位(局终调;删除波 1 后**零落盘**)。

    `w603_telemetry_wiring/`:收口置 run 关闭位 —— 此后到下一局
    start_run 前 ensure_run_started 铸新段(journal 行归属新 run_id)。
    旧局终 summary 写行已随旧流写入端退役(删除波 1);形参保留
    (调用点传值面不变),值只进日志不进任何流。局终元数据的 journal
    归宿 = 局终域 match_final 行(W3 在线接线,写点 = kernel
    write_match_final,收口点 = cw_loop 3c 回大厅 / W75 停机兜底)。
    收口时点先落盘流水缓冲(:func:`kernel.cw_state_journal.flush_pending`):
    批量 flush 阈值之间收口时局终行与段尾行还在内存,紧随的档案装配
    读盘会漏行(g_20260915_070645 档案缺 endgame.match_final 实证)——
    与 StateJournal.close「局终收口 flush」设计意图对齐,丢失窗上界
    收敛到本时点。
    """
    global _RUN_CLOSED
    if not _CURRENT_RUN_ID:
        return
    try:
        from sr_od.application.currency_war.kernel.cw_state_journal import (
            flush_pending,
        )
        flush_pending()
    except Exception as e:  # noqa: BLE001  观测件,失败不阻塞收口
        log.warning('[cw][telemetry] 收口流水落盘失败(不阻塞): %s', e)
    _RUN_CLOSED = True
    log.info('[cw][telemetry] run 收口:%s p%s-r%s hp=%s (%s)',
             result or '-', plane_reached, rounds_survived, final_hp,
             notes or '-')


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
