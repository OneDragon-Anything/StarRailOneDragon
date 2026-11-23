"""货币战争 telemetry 上行出口钩子位(kernel;DESIGN §3.3-④)。

kernel/obs/decision 三桶对 telemetry 的全部上行出口收敛为本模块的钩子位,
三桶零直依 telemetry(分包目标矩阵 §3.2;单一测量源=scan_v3):

- run_id 归属键:``current_run_id`` provider(冲突行/结算行/影子文件名的局归属);
- obs_event 并入制 provider:``obs_event_board``(观察冲突证据归宿 = 统一
  state 账本行型 2;GameState 单例供给由装配段注入,kernel 禁自寻会话)。

缺陷台账落账出口(record_defect/bypass_obs_conflict_to_defect)已随缺陷
台账废弃拆除(用户裁定 2026-11-24);观察冲突证据行的现役归宿 =
journal obs_event 行(经 obs_event_board 供给的账本写点,见 kernel/
cw_observe 汇点),不再另落索引流。

注入纪律(与框架「副作用缺省关 + 启动点显式接通」一致):

- 生产装配接入点 = ``CurrencyWarApp.__init__`` 调 ``install_exit_hooks()``
  (幂等)——注入 run_id provider;
- 缺省(未注入)= run_id 返空串;
  测试需要真实归属键时显式调 ``install_exit_hooks``(或 monkeypatch 本模块槽位)。
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

# ===== 钩子槽(注入式; None=缺省关) =====

_run_id_provider: Callable[[], str] | None = None
_obs_event_board_provider: Callable[[], Any] | None = None


def install_exit_hooks(*, run_id_provider: Callable[[], str]) -> None:
    """注入出口实现(显式逐槽,幂等;生产调用方=currency_war_app 装配段)。

    缺陷台账落账出口实现槽已随缺陷台账废弃拆除,不再接受注入。"""
    global _run_id_provider
    _run_id_provider = run_id_provider


# ===== 出口访问器(缺省 no-op / 空串) =====

def current_run_id() -> str:
    """run_id 归属键(空串=局外/未注入;消费端按真值判断,不写假键)。"""
    provider = _run_id_provider
    return provider() if provider is not None else ''


def set_obs_event_board_provider(fn: Callable[[], Any] | None) -> None:
    """注入/清除 obs_event 并入制 GameState 供给槽(装配段显式接通;
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


def record_exogenous(round_num: int, kind: str, detail: str = '',
                     state: Any = None,
                     choice: dict[str, Any] | None = None) -> None:
    """旧 exogenous 流出口(已停用 no-op 桩)。

    保留原因:观测登记机制(kernel/cw_anchor.py,已入库惰性未接入调用,本文件
    此前是其唯一 kernel 侧上行出口)的调用方仍 import 本符号——本桩恒
    no-op,既不断在飞调用方,也零旧流产出。若裁「路由停用」时随其
    调用点整段删除,本桩同步消失。
    """
    return
