"""货币战争 op_journal.jsonl 薄流(T-113/ADR-0579:深度复盘遥测缺口②③)。

两个行型(独立于 decisions.jsonl 的薄流;体积红线 = 永不并入 decisions 行,
3.5KB 行基数上叠逐动作/逐 op 快照是体积爆炸路径):

- kind='action':单动作执行回执(商店域唯一写点 = apply_action_outcome
  回执位;备战域写点 = PrepActionExecutor._note_action_journal,T-16
  执行缝账务包络扩围——备战帧金动作自此逐行在账,op 分键
  「货币战争-备战动作」,行携执行点 ``gold_delta``)。期望态 delta 列
  (expected_delta/gold/bench_used)已随 T-163 前瞻推算消费退役不入行:
  逻辑态真值在容器 receipts 直写流水(state/journal.jsonl 行行自足),
  判读输入 = 动作行本体 + 该流水 join,行内不再复制第二份逻辑态;
- kind='op':非决策 op(战斗等待/入口链/位面切换)enter/exit 成对行。轮询
  内循环逐 tick 不落行(用户需求粒度 = 每次 op 调用;tick 级留日志)。孤儿
  enter 行(进程中断/停局导致 exit 丢失)= 进程中断证据,装配端标注
  ``outcome='orphan'`` 容缺非缺陷。

体积纪律:action 行 ≤400B(op 行 ≤250B),超限截断 + ``_trunc`` 标记。
行数**不设上限**(原「每局 500 行软上限超限停写」已由用户裁定 2026-09-07
整条删除):病态决策循环的停线防护已由哨兵层 STALL/LOOP 检测承接,
journal 侧静默触顶停写会让长局尾段 op 行无感丢失——复盘盲区的代价
远大于流体积风险(T-121 深局实测单 run 690 行即已越旧顶)。禁入决策
输入(守卫 = 键族命中锁,ADR-0571 §2.3 范式;决策输入一律走 TurnState
幂等装配)。
"""
from __future__ import annotations

import datetime
import json as _json
import time as _time
from pathlib import Path
from typing import Any

from sr_od.application.currency_war.kernel.cw_observe import LIVE_DIR
from sr_od.application.currency_war.telemetry.schema import (
    serialize_action,
)
from sr_od.application.currency_war.telemetry.state import current_run_id

#: journal 落盘位置(telemetry/live 实时流根,单一源 = kernel/cw_observe
#: 的根常量块;独立流,永不并入 decisions 行)
_JOURNAL = LIVE_DIR / 'op_journal.jsonl'

# ===== journal 根装配槽(T-120 批 1;T-129/T-130「sim 与 live 共写同一
# ===== journal 文件」混流设计注记的落地点)=====
# 机制裁决 = **写端根隔离**而非读端 run_id 过滤:假局(经根槽接指假局
# 档案根)的 action/op 行从写入时点就不进 live 流,读端无需维护
# 「run_id ∈ sim 集」过滤态(过滤态漏维护 = 静默混流,比写端漏接通更
# 难发现——写端漏接通表现为 live 流出现行,obs_conflict 式审计可见)。
# 行内 run_id 键保持不变,读端过滤能力不受影响(双保险,非双实现)。
# 缺省 None = LIVE_DIR(生产路径逐位不变)。假局遥测写根共三根
# (recorder 流/journal 行/决策帧,三审二波 F2 勘明——决策帧原为无槽
# 第三根,靠 harness monkeypatch 私函数兜住,「两根恒一致」旧声明对
# 三根现实不成立),三根槽(telemetry/state.set_recorder_replay_dir /
# 本模块 set_journal_dir / operations/decision_frame_hooks.
# set_decision_frame_dir)由驱动方同点接指同一档案根:恒一致由三槽
# 并列接线承载,不再靠调用侧自觉。
_JOURNAL_DIR: Path | None = None


def set_journal_dir(path: Path | None) -> None:
    """接通/复位 journal 落盘根(缺省 None = LIVE_DIR 生产路径)。

    与 :func:`telemetry.state.set_recorder_replay_dir` 同装配纪律:缺省关、
    测试显式接通、teardown 复位——进程全局槽,残留会把后续写的 journal
    行带去假局根。
    """
    global _JOURNAL_DIR
    _JOURNAL_DIR = Path(path) if path is not None else None


def _journal_path() -> Path:
    """journal 文件现算路径(根槽优先;槽是函数内读取,测试可 monkeypatch
    槽变量后立即生效,不经模块 import 绑定快照)。

    槽缺省回落模块常量 ``_JOURNAL``(非直接回落 LIVE_DIR):既有测试以
    monkeypatch ``_JOURNAL`` 作落盘重定向缝(test_cw_op_journal/
    test_cw_dispatch_wrapper 同款),常量保持活读=该缝不失效;根槽是
    追加缝,不改写既有缝语义。"""
    if _JOURNAL_DIR is not None:
        return _JOURNAL_DIR / 'op_journal.jsonl'
    return _JOURNAL

#: 行字节硬上限(超限截断 + ``_trunc`` 标记;方案 §共通-体积纪律 (a))
_ROW_CAP: int = 400

#: 决策帧关联键帧序(C6):每 run 当前段序号(shop 段计数同源,由
#: advance_frame_seq 在段边界推进;action 行读取当前值做精确 join)
_frame_seq_by_run: dict[str, int] = {}


def advance_frame_seq() -> int:
    """段边界推进帧序(shop 段循环起点调用;返回推进后的段序)。"""
    rid = current_run_id()
    if not rid:
        return 0
    _frame_seq_by_run[rid] = _frame_seq_by_run.get(rid, 0) + 1
    return _frame_seq_by_run[rid]


def current_frame_seq() -> int:
    """当前段序(动作行 frame_seq 关联键读取端;局外 = 0)。"""
    return _frame_seq_by_run.get(current_run_id(), 0)


def _emit(rec: dict[str, Any], row_cap: int) -> None:
    """best-effort 追加一行(局外无 run_id 不写假键;
    序列化超行帽截断 + ``_trunc``,obs_conflict 同款 try/except 兜底;
    行数不设上限——软上限删除裁决见模块 docstring 体积纪律节)。"""
    rid = rec.get('run_id', '')
    if not rid:
        return
    try:
        blob = _json.dumps(rec, ensure_ascii=False)
        if len(blob.encode('utf-8')) > row_cap:
            # 超帽降级 = 摘大载荷键后重试(expected_delta 已退役,降级
            # 现为纯截断标记;键名保留 = 旧判读面「_trunc 行 = 行不完整」
            # 分型语义不变,未来大载荷键扩条只改本剥离清单)。
            slim = {k: v for k, v in rec.items()
                    if k not in ('expected_delta',)}
            slim['_trunc'] = True
            blob = _json.dumps(slim, ensure_ascii=False)
        out = _journal_path()
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('a', encoding='utf-8') as f:
            f.write(blob + '\n')
    except Exception:   # noqa: BLE001  journal best-effort,失败不阻塞业务流
        pass


def _base_row(plane: int, round_num: int) -> dict[str, Any]:
    return {'schema_version': 1,
            'ts': datetime.datetime.now().isoformat(timespec='seconds'),
            'run_id': current_run_id(),
            'plane': plane, 'round_num': round_num}


def record_action_journal(match: Any, action: Any, seq: int, exec_ok: bool,
                          pre_receipt: Any, post_receipt: Any = None, *,
                          op_name: str = '货币战争-买牌',
                          extra: dict[str, Any] | None = None) -> None:
    """缺口②写点:单动作执行回执行(商店域唯一写点 =
    apply_action_outcome 回执位;备战域写点 = PrepActionExecutor
    ._note_action_journal,T-16 执行缝账务包络扩围)。

    :param match: 对局对象(session 载体;run_id 读取经 telemetry.state)
    :param action: 已执行的动作对象(商店 BuyCard/RefreshShop/LevelUpShop/
      CloseShop;备战 pa.* 动作全集)
    :param seq: 段内动作序(1 起;visit_actions 追加后长度)。备战域恒 0
      = 无段序账(行序即时序,商店 seq 语义不适用)
    :param exec_ok: 执行落地与否(False 行照落,exec_ok=False 判读面)
    :param pre_receipt: 执行前时点位置回执(容器期:本函数只读
      ``plane``/``round_num`` 两属性作行位置键;商店域 = 段顶
      ``GameStateReadReceipt``,备战域 = 容器读口现读的命名空间桩。
      位置键真值由调用方在动作时点捕获,本函数不回读容器防时点漂移)
    :param post_receipt: 退役位,恒 None(形参保留只为调用点位兼容——
      期望态 delta/gold/bench_used 列已随 T-163 前瞻推算消费退役不入行,
      两域同口径;逻辑态真值单一源 = 容器 receipts 直写流水,判读 join
      该流水,本行不复制第二份。传非 None = 调用方契约违约)
    :param op_name: 行 op 键(复盘「分发了谁/金动归属」直读域分键):缺省
      = 商店「货币战争-买牌」;备战域 = 「货币战争-备战动作」
    :param extra: 行级结构化扩展(备战域携 ``gold_delta`` = 执行点金差,
      T-16;商店域不用)
    """
    try:
        rid = current_run_id()
        if not rid:
            return
        rec = _base_row(int(getattr(pre_receipt, 'plane', 0) or 0),
                        int(getattr(pre_receipt, 'round_num', 0) or 0))
        rec.update({'kind': 'action', 'op': op_name,
                    'seq': seq, 'frame_seq': current_frame_seq(),
                    'action': serialize_action(action), 'exec_ok': exec_ok})
        if extra:
            rec.update(dict(extra))
        _emit(rec, _ROW_CAP)
    except Exception:   # noqa: BLE001  journal best-effort
        pass


def _op_journal_pos_of(ctx: Any) -> tuple[int, int]:
    """op 行位置键(ADR-0579):最后已知 (plane, round),缺省 (0, 0)。

    位置键语义属 journal 行型本体,故住本模块(原住 cw_loop;清场件收编
    备战 op 后跨 op 复用,迁此消「画面 op → 外循环模块」的依赖倒挂)。
    模块级形态供仲裁段第三载体行复用——仲裁宿主在测试缝里可为非 CwLoop
    桩,位置键只依赖 ctx 的 getattr 链,不依赖宿主方法。
    (换源 T-146:plane/round = 容器 node;未观察 = 旧缺帧形态 (0, 0)。)
    """
    _sess = getattr(getattr(ctx, 'cw_match', None), 'session', None)
    from sr_od.application.currency_war.kernel.cw_game_state import (
        board_state_of,
    )
    _nd = (getattr(board_state_of(_sess).node, 'value', None)
           if _sess is not None else None)
    return (int(_nd.plane) if _nd is not None else 0,
            int(_nd.round_num) if _nd is not None else 0)


def resolve_dispatch_ok(res: Any) -> bool:
    """op 执行返回值的 ok 判定(单一源;r2 必修①消双源)。

    判定体 = cw_loop._dispatch_screen_op 原分支逐位:OperationRoundResult
    走轮次枚举(FAIL/RETRY 之外 = ok,链形透传语义);其余(SrOperation
    .execute 的 OperationResult)走 success 属性。禁在调用方手写第二份
    ——round-result 型返回只有 ``is_success`` 属性,手写 ``getattr(res,
    'success')`` 形态会让成功恒记 fail(r1 验收缺陷 1 实证)。
    """
    from one_dragon.base.operation.operation_round_result import (
        OperationRoundResult,
        OperationRoundResultEnum,
    )
    if isinstance(res, OperationRoundResult):
        return res.result not in (OperationRoundResultEnum.FAIL,
                                  OperationRoundResultEnum.RETRY)
    return res is not None and getattr(res, 'success', False)


def journal_wrapped_execute(op: Any, journal_name: str,
                            pos: tuple[int, int]) -> tuple[bool, Any]:
    """op.execute() 的 journal 包装单一源(enter/execute/exit 成对模板;
    r2 必修①:清场件等「分发语境外的 op 行」复用,替代手写包装)。

    异常补 error 出口行后原样上抛(ADR-0584 §5.2 同款);ok 判定 =
    :func:`resolve_dispatch_ok`(与 _dispatch_screen_op 同源,防双源漂移)。
    返回 ``(ok, res)``;调用方按语境决定 res 消费(清场语境丢弃)。
    """
    _token = record_op_enter(journal_name, *pos)
    try:
        _res = op.execute()
    except Exception as e:   # noqa: BLE001  出口行补发后原样上抛
        record_op_exit(_token, outcome='error', detail=str(e)[:120])
        raise
    _ok = resolve_dispatch_ok(_res)
    record_op_exit(_token, outcome='ok' if _ok else 'fail')
    return _ok, _res


def record_op_enter(op_name: str, plane: int, round_num: int,
                    obs: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """缺口③写点(enter):非决策 op 执行前调用,返回 exit 用的 token。

    局外(current_run_id 空)返回 None = 零行(不写假键,obs_conflict 同规)。
    """
    rid = current_run_id()
    if not rid:
        return None
    token = {'op': op_name, 't0': _time.monotonic(), 'plane': plane,
             'round_num': round_num, 'obs_enter': dict(obs or {})}
    rec = _base_row(plane, round_num)
    rec.update({'kind': 'op', 'op': op_name, 'event': 'enter',
                'obs': dict(obs or {})})
    _emit(rec, 250)
    return token


def record_op_exit(token: dict[str, Any] | None, outcome: str = 'ok',
                   detail: str = '', obs: dict[str, Any] | None = None) -> None:
    """缺口③写点(exit):op 执行后调用(token = enter 返回值;None = 局外静默)。"""
    if token is None:
        return
    rec = _base_row(int(token.get('plane', 0) or 0),
                    int(token.get('round_num', 0) or 0))
    rec.update({'kind': 'op', 'op': token.get('op', ''), 'event': 'exit',
                'duration_s': round(_time.monotonic() - token.get('t0', 0.0), 2),
                'outcome': outcome})
    if detail:
        rec['detail'] = detail
    if obs:
        rec['obs'] = dict(obs)
    _emit(rec, 250)
