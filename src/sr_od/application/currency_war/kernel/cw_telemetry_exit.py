"""货币战争 telemetry 上行出口钩子位(kernel;DESIGN §3.3-④)。

kernel/obs/decision 三桶对 telemetry 的全部上行出口收敛为本模块的钩子位,
三桶零直依 telemetry(分包目标矩阵 §3.2;单一测量源=scan_v3):

- 落账出口:``record_defect`` / ``bypass_obs_conflict_to_defect``
  (缺陷台账 = 保留专用流;exogenous/exec_events 旧流写入口已随退役删除——
  ``record_exogenous`` 留 no-op 桩只护在飞挂起面调用方,见其注);
- 安灯出口:``l0_andon_flag_path`` / ``write_l0_andon_flag``
  (游戏侧执行器 ``kernel.cw_observe.stop_for_l0_andon`` 消费);
- run_id 归属键:``current_run_id`` provider(冲突行/结算行/影子文件名的局归属);
- obs_event 收编制 provider:``obs_event_board``(观察冲突证据归宿 = 统一
  state 账本行型 2;GameState 单例供给由装配段注入,kernel 禁自寻会话)。

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
# 缺陷台账/出口双侧同引此处=字符串单一源;互不混流锁钉值)=====

#: 布局双通道分歧(公式 vs CV 占用态门,三信号梯裁决)。
DEFECT_KIND_BACK_LAYOUT_DIVERGENCE: str = 'back_layout_divergence'
#: 布局未知态(公式/CV 双弃权,读写分级+冻结止损事件面)。
DEFECT_KIND_BACK_LAYOUT_UNKNOWN: str = 'back_layout_unknown'

# ===== 钩子槽(注入式; None=缺省关) =====

_run_id_provider: Callable[[], str] | None = None
_record_defect: Callable[..., None] | None = None
_bypass_obs_conflict_to_defect: Callable[[dict[str, Any]], None] | None = None
_obs_event_board_provider: Callable[[], Any] | None = None
_l0_andon_flag_path: Callable[[], Path] | None = None
_write_l0_andon_flag: Callable[..., str] | None = None


def install_exit_hooks(*, run_id_provider: Callable[[], str],
                       record_defect: Callable[..., None],
                       bypass_obs_conflict_to_defect: Callable[[dict[str, Any]], None],
                       l0_andon_flag_path: Callable[[], Path],
                       write_l0_andon_flag: Callable[..., str]) -> None:
    """注入全部出口实现(显式逐槽,幂等;生产调用方=telemetry.install_exit_hooks)。

    exogenous/exec_events 实现槽已随旧流写入端退役删除(删除波 1)——
    两流的出口访问器或为 no-op 桩、或已移除,不再接受注入。"""
    global _run_id_provider, _record_defect
    global _bypass_obs_conflict_to_defect
    global _l0_andon_flag_path, _write_l0_andon_flag
    _run_id_provider = run_id_provider
    _record_defect = record_defect
    _bypass_obs_conflict_to_defect = bypass_obs_conflict_to_defect
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
    """旧 exogenous 流出口(已退役 no-op 桩;删除波 1)。

    保留原因:锚登记机制(kernel/cw_anchor.py,已入库惰性未接线,本文件
    此前是其唯一 kernel 侧上行出口)的调用方仍 import 本符号,其归宿候裁
    (retirement.md §2 exogenous 行 §5-7 挂起)——候裁落地前本桩恒
    no-op,既不断在飞调用方,也零旧流产出。候裁裁「路由退役」时随其
    调用点整段删除,本桩同步消失。
    """
    return


def bypass_obs_conflict_to_defect(rec: dict[str, Any]) -> None:
    """观察冲突行 → 缺陷台账旁路出口(口径映射在 telemetry 真实现;
    缺陷台账 = 保留专用流,本旁路照常供给,证据 refs 指 journal (run_id,v)
    锚行(journal_refs 单一源构造,无账本媒体诚实省略)。"""
    fn = _bypass_obs_conflict_to_defect
    if fn is None:
        return
    fn(rec)


def set_obs_event_board_provider(fn: Callable[[], Any] | None) -> None:
    """注入/清除 obs_event 收编制 GameState 供给槽(装配段显式接通;
    None = 缺省关,观察冲突证据不进账本)。"""
    global _obs_event_board_provider
    _obs_event_board_provider = fn


def obs_event_board() -> Any:
    """现役 GameState 单例供给(未注入/无会话 = None,调用方据此跳过)。"""
    fn = _obs_event_board_provider
    if fn is None:
        return None
    try:
        return fn()
    except Exception:  # noqa: BLE001  供给 best-effort,不毒化观察链
        return None


def journal_refs(*extra: dict[str, str] | None) -> list[dict[str, str]]:
    """缺陷台账 refs 的 journal ``(run_id,v)`` 锚构造(保留流 refs 迁移单一源)。

    依据 = retirement.md §2 defect_ledger 行「裁保留时 refs 改指 journal
    ``(run_id,v)`` 键」(候裁 4 定谳保留专用流后的消费面迁移,R5 W7):旧流
    (decisions/outcomes/obs_conflicts)写面已随删除波 1 退役,refs 指旧流行
    = 下钻扑空;journal 行行自足(每行内嵌当时完整 state 快照),
    ``(run_id, v)`` 唯一定位一行。锚取缺陷记录时刻现版 ``current_version()``
    (读口不占版本)= 最近一行,其内嵌 state 供下钻对账;bypass 场景该值
    恰为刚写入的 obs_event 证据行版本。

    锚缺媒体(无 GameState 供给/局外/零版本)时省略,refs 允许空(诚实
    缺失);extra = 调用方语义键(arbitration 族 provenance 标签等),None 项
    过滤。本函数在 kernel 出口模块 = 四域(obs/kernel/operations/telemetry)
    调用点共一形态,禁散写第二套键格式。
    """
    gs = obs_event_board()
    version = int(gs.current_version()) if gs is not None else 0
    rid = current_run_id()
    out: list[dict[str, str]] = []
    if rid and version > 0:
        out.append({'stream': 'journal',
                    'key': f'run_id={rid}|v={version}'})
    out.extend(e for e in extra if e)
    return out


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
        refs=journal_refs({'stream': 'arbitration',
                           'key': f'source={source}'}),
        reader_source=str(source),
        note='布局档双通道仲裁分键(证据层 = journal obs_event arbitrate 行,'
             'field=back_layout_channel_conflict 对账)')


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
        refs=journal_refs({'stream': 'arbitration',
                           'key': f'source={source}'}),
        reader_source=str(source),
        note='布局未知态分键(证据层 = journal obs_event arbitrate 行,'
             'field=back_layout_unknown 对账)')
