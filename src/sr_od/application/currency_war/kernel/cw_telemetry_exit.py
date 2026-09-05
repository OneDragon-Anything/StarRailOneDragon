"""货币战争 telemetry 上行出口钩子位(kernel;DESIGN §3.3-④)。

kernel/obs/decision 三桶对 telemetry 的全部上行出口收敛为本模块的钩子位,
三桶零直依 telemetry(分包目标矩阵 §3.2;单一测量源=scan_v3):

- 落账出口:``record_defect`` / ``record_exogenous`` / ``bypass_obs_conflict_to_defect``
  / ``record_exec_event``(decision 影子事件);
- 安灯出口:``l0_andon_flag_path`` / ``write_l0_andon_flag``
  (游戏侧执行器 ``kernel.cw_observe.stop_for_l0_andon`` 消费);
- run_id 归属键:``current_run_id`` provider(冲突行/结算行/影子文件名的局归属)。

注入纪律(与框架「副作用缺省关 + 启动点显式接通」一致):

- 生产武装点 = ``CurrencyWarApp.__init__`` 调 ``telemetry.install_exit_hooks()``
  (与 ``set_l0_andon_handler`` 同点;幂等)——telemetry 侧把真实现写进本模块槽位;
- 缺省(未注入)= run_id 返空串、落账 no-op、安灯不落 flag(停线三要素仍执行);
  测试需要真实落账时显式调 ``install_exit_hooks``(或 monkeypatch 本模块槽位)。

缺陷台账分级常量(SEVERITY_*)的单一源也在本模块:判级函数(telemetry.judge_severity)
与 obs 显式判级调用点同取此源。
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

# ===== 缺陷台账分级常量(单一源;值语义见 telemetry.judge_severity 判据链) =====

SEVERITY_L0_ANDON: str = 'L0_andon'
SEVERITY_L1_ALERT: str = 'L1_alert'
SEVERITY_L2_RECORD: str = 'L2_record'

# ===== 仲裁分键常量(布局档;15 号稿批 C。obs 布局面经本出口上行,
# 缺陷台账/出口双侧同引此处=字符串单一源;T-6 互不混流锁钉值)=====

#: 布局双通道分歧(公式 vs CV 占用态门,三信号梯裁决)。
DEFECT_KIND_BACK_LAYOUT_DIVERGENCE: str = 'back_layout_divergence'
#: 布局未知态(公式/CV 双弃权,读写分级+冻结止损事件面)。
DEFECT_KIND_BACK_LAYOUT_UNKNOWN: str = 'back_layout_unknown'
#: 掉血报警 node_type 空值回落(flow.on_round_end;supply 失活治本批:
#: 空 node_type 轮按位面节点台账查同轮类型,查不到=照旧空串+本分键)。
DEFECT_KIND_BLOOD_ALARM_NODE_FALLBACK: str = 'blood_alarm_node_type_fallback'

# ===== 钩子槽(注入式; None=缺省关) =====

_run_id_provider: Callable[[], str] | None = None
_record_defect: Callable[..., None] | None = None
_record_exogenous: Callable[..., None] | None = None
_bypass_obs_conflict_to_defect: Callable[[dict[str, Any]], None] | None = None
_record_exec_event: Callable[..., None] | None = None
_l0_andon_flag_path: Callable[[], Path] | None = None
_write_l0_andon_flag: Callable[..., str] | None = None


def install_exit_hooks(*, run_id_provider: Callable[[], str],
                       record_defect: Callable[..., None],
                       record_exogenous: Callable[..., None],
                       bypass_obs_conflict_to_defect: Callable[[dict[str, Any]], None],
                       record_exec_event: Callable[..., None],
                       l0_andon_flag_path: Callable[[], Path],
                       write_l0_andon_flag: Callable[..., str]) -> None:
    """注入全部出口实现(显式逐槽,幂等;生产调用方=telemetry.install_exit_hooks)。"""
    global _run_id_provider, _record_defect, _record_exogenous
    global _bypass_obs_conflict_to_defect, _record_exec_event
    global _l0_andon_flag_path, _write_l0_andon_flag
    _run_id_provider = run_id_provider
    _record_defect = record_defect
    _record_exogenous = record_exogenous
    _bypass_obs_conflict_to_defect = bypass_obs_conflict_to_defect
    _record_exec_event = record_exec_event
    _l0_andon_flag_path = l0_andon_flag_path
    _write_l0_andon_flag = write_l0_andon_flag


# ===== 出口访问器(签名与 telemetry 真实现逐参一致;缺省 no-op / 空串) =====

def current_run_id() -> str:
    """run_id 归属键(空串=局外/未注入;消费端按真值判断,不写假键)。"""
    provider = _run_id_provider
    return provider() if provider is not None else ''


def record_defect(surface: str, kind: str, expected: str, observed: str, *,
                  gap: float | None = None, plane: int = 0, round_num: int = 0,
                  unit_seq: int | None = None, verdict: str = '',
                  shot: str | None = None,
                  refs: list[dict[str, str]] | None = None,
                  reader_source: str = '', note: str = '',
                  gap_large: bool = False, auto_resolved: bool = False,
                  severity: str = '', confidence: float | None = None) -> None:
    """缺陷台账落账出口(判级/复现计数/run_id 门控语义在 telemetry 真实现)。"""
    fn = _record_defect
    if fn is None:
        return
    # 逐参关键字转发:保持调用形状与直依形态一致(测试桩按 kwargs 断言字段)
    fn(surface=surface, kind=kind, expected=expected, observed=observed,
       gap=gap, plane=plane, round_num=round_num, unit_seq=unit_seq,
       verdict=verdict, shot=shot, refs=refs, reader_source=reader_source,
       note=note, gap_large=gap_large, auto_resolved=auto_resolved,
       severity=severity, confidence=confidence)


def record_exogenous(round_num: int, kind: str, detail: str = '',
                     state: Any = None,
                     choice: dict[str, Any] | None = None) -> None:
    """外生事件落账出口(简报行局间缓冲语义在 telemetry 真实现)。"""
    fn = _record_exogenous
    if fn is None:
        return
    fn(round_num, kind, detail, state, choice=choice)


def bypass_obs_conflict_to_defect(rec: dict[str, Any]) -> None:
    """obs_conflicts 行 → 缺陷台账旁路出口(口径映射在 telemetry 真实现)。"""
    fn = _bypass_obs_conflict_to_defect
    if fn is None:
        return
    fn(rec)


def record_exec_event(run_id: str, round_num: int, action_family: str,
                      screen: str, event: str, reason: str = '',
                      retry_count: int = 0) -> None:
    """执行事件落账出口(decision 影子事件;失败类旁路在 telemetry 真实现)。"""
    fn = _record_exec_event
    if fn is None:
        return
    fn(run_id, round_num, action_family, screen, event,
       reason=reason, retry_count=retry_count)


def andon_exit_installed() -> bool:
    """安灯出口是否已注入(未注入=停线三要素不落 flag 仅停线;缺省关纪律)。"""
    return _write_l0_andon_flag is not None


def l0_andon_flag_path() -> Path:
    """安灯哨兵 flag 路径出口(未注入时由调用方跳过 flag 落盘)。"""
    fn = _l0_andon_flag_path
    if fn is None:
        raise RuntimeError('l0_andon_flag_path 未注入(出口缺省关;'
                           '生产武装点=CurrencyWarApp.__init__)')
    return fn()


def write_l0_andon_flag(flag_path: Path, *, run_id: str, surface: str,
                        kind: str, expected: str, observed: str,
                        plane: int = 0, round_num: int = 0,
                        refs: list[dict[str, str]] | None = None,
                        defect_shot: str | None = None,
                        stop_shot: str = '') -> str:
    """安灯哨兵 flag 写入出口(HOOK-STOP 内容规范在 telemetry 真实现)。"""
    fn = _write_l0_andon_flag
    if fn is None:
        return ''
    return fn(flag_path, run_id=run_id, surface=surface, kind=kind,
              expected=expected, observed=observed, plane=plane,
              round_num=round_num, refs=refs, defect_shot=defect_shot,
              stop_shot=stop_shot)


# ===== 布局档分键记录函数(15 号稿批 C;落地审 C3 择一=记录单一源迁入
# 出口模块:obs 布局面只依 kernel 出口,telemetry.defects 不留副本)=====

def record_back_layout_divergence(formula_n: int, cv_n: int,
                                  source: str = 'resolve_back_slots') -> None:
    """布局双通道分歧分键行(best-effort;run_id 缺省 no-op,恒 L2
    auto_resolved——裁决已按三信号梯完成,行面只承担不一致率统计)。"""
    if not current_run_id():
        return
    record_defect(
        'back_layout', DEFECT_KIND_BACK_LAYOUT_DIVERGENCE,
        expected=f'formula={int(formula_n)}', observed=f'cv={int(cv_n)}',
        gap=float(int(cv_n) - int(formula_n)),
        gap_large=abs(int(cv_n) - int(formula_n)) > 1,
        auto_resolved=True,
        verdict=('留证-布局双通道分歧,已按三信号梯裁决;'
                 '本键计数=不一致率,复现帧对拍 cv_back_slots'),
        refs=[{'stream': 'arbitration', 'key': f'source={source}'}],
        reader_source=str(source),
        note='布局档双通道仲裁分键(证据层见 obs_conflicts '
             'back_layout_channel_conflict 行)')


def record_back_layout_unknown(source: str = 'resolve_back_slots') -> None:
    """布局未知态分键行(best-effort;run_id 缺省 no-op,恒 L2
    auto_resolved——未知态按读写分级+冻结止损处置,频度=验收锚点)。"""
    if not current_run_id():
        return
    record_defect(
        'back_layout', DEFECT_KIND_BACK_LAYOUT_UNKNOWN,
        expected='公式/CV 至少一源可判',
        observed='双弃权(布局未知态)',
        gap=None, gap_large=False,
        auto_resolved=True,
        verdict=('留证-布局未知态(读类退 6 档基线,写类冻结止损;'
                 '频度锚点=15号稿 §7 批 B/C 验收)'),
        refs=[{'stream': 'arbitration', 'key': f'source={source}'}],
        reader_source=str(source),
        note='布局未知态分键(证据层见 obs_conflicts back_layout 行)')
