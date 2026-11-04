"""货币战争 决策装配边界·生产装配接入点(app 层)。

生产装配接入点 = ``install_obs_ports``(CurrencyWarApp.__init__ 接通):
decision 层 obs 读口注入、kernel 侧合成特效帧态门注入、GameState
缺陷台账 sink 的落盘实现(实现住本模块,
kernel 零像素触达;缺省关 = 不落盘),以及策略遥测 sink 接通
(DecisionRecord 落 recorder 根 strategy/ 目录;缺省未装配 = 零写)。

为何在 app:本模块 import prep_actions/obs 执行面词汇,且被
cw_screen_prep(备战环)消费——两侧都在 app 层,装配边界归 app 是分包矩阵
(DESIGN 分包 §3.2,app 依一切)的自然落位。
"""
from __future__ import annotations

from pathlib import Path

# ------------------------------------------------------- obs 读口注入

def install_obs_ports() -> None:
    """装配点接通 decision 层的 obs 读口(生产装配接入点 = CurrencyWarApp.__init__)。

    分包依赖矩阵禁 decision→obs 直依:决策核只持注入槽
    (``cw_strategy._RESET_PHASE_ROUND_CACHE``),本函数从 obs 层取实现注入。
    未接通(缺省关)= 新局弃置残留状态容器时跳过 obs 模块级缓存清理——
    session 全量重建承担状态隔离,仅 last-known-good 观测缓存延用旧值。

    同点接通 kernel 侧合成特效帧态门(``cw_reconcile`` 注入槽,分包矩阵禁
    kernel→obs 直依;缺省关 = 门放行走既有连续 2 次确认防抖主干)。

    (「期望态保留证据 sink」expected_reconcile.jsonl 不再装配——两态制
    已废除,覆盖点 diff 对账随条目表拆除,无 diff 行可落盘。)
    """
    from sr_od.application.currency_war.kernel.cw_reconcile import (
        set_merge_effect_gate,
    )
    from sr_od.application.currency_war.obs.cw_identity_obs import (
        is_merge_effect_frame,
    )
    from sr_od.application.currency_war.obs.cw_observation import (
        reset_phase_round_cache,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        set_decision_sink,
        set_obs_reset_hook,
    )
    set_obs_reset_hook(reset_phase_round_cache)
    set_merge_effect_gate(is_merge_effect_frame)

    # 策略遥测生产装配接入点(obs 读口同位接通,capture-store §4):决策信封
    # 经 wrapper 装配槽落 recorder 根 strategy/ 目录(run_id 补齐与局外
    # 零写判断都在 sink);缺省未装配 = 零写,本点缺接即纯单测零副作用。
    from sr_od.application.currency_war.telemetry.strategy_telemetry import (
        strategy_telemetry_sink,
    )
    set_decision_sink(strategy_telemetry_sink)

    # 缺陷台账生产装配接入点:GameState 观察覆盖
    # logic 值失配行(kernel/cw_game_state._emit_defect,槽缺省关)
    # 经 sink 落 gs_defect.jsonl(与 expected_reconcile.jsonl 同目录同追加
    # 形态);缺省关 = 只缓冲不落盘,测试零真实 IO。
    from sr_od.application.currency_war.kernel.cw_game_state import (
        set_defect_sink,
    )
    set_defect_sink(_gs_defect_sink_for_test(_reconcile_dir()))


def _reconcile_dir() -> Path:
    """gs_defect.jsonl 目录(项目根锚定绝对路径;P4R4 缺陷②:
    旧相对路径依赖 server cwd,cwd 漂移进程把追加写去别处 = 主文件
    「零新增」假截断)。"""
    from one_dragon.utils.file_utils import get_project_root
    return (get_project_root() / '.debug' / 'temp' / 'currency_war')


def _gs_defect_sink_for_test(base_dir: Path):
    """GameState 缺陷台账 sink 工厂(形态同 expected_reconcile sink;
    单一文件 = gs_defect.jsonl,逐行 JSON,失败静默)。"""
    import json

    def _sink(row: dict) -> None:
        try:
            p = Path(base_dir) / 'gs_defect.jsonl'
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('a', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')
        except Exception:  # noqa: BLE001  保留证据 best-effort
            pass

    return _sink

