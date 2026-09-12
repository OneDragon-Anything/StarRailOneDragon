"""货币战争 决策装配边界·观察端口半部(app 桶;统一迁移批 ② 后形态)。

实机观察 → Snapshot 的 observe 端口 ``snapshot_from_obs``(生产消费方 =
strategies 注册壳 MandateV1Live 的装配缝;与 sim 合成器共享字段映射语义)。
离线装配链 ``DecideAdapter``→prep_brain.decide 已随 v2 退役链删除(底稿
MAP ⓪ A10;唯一外部消费 test_cw_expected_state 同批退役);纯映射半部
单一源 = strategies/impl/mandate_v1/adapter.py。

为何在 app:本模块 import prep_actions/cw_screen_prep/obs 执行面词汇,且被
cw_screen_prep(备战环)消费——两侧都在 app 桶,装配边界归 app 是分包矩阵
(DESIGN 分包 §3.2,app 依一切)的自然落位。
"""
from __future__ import annotations

from pathlib import Path

from sr_od.application.currency_war.kernel.cw_prep_actions import (
    PrepObservation,
)
from sr_od.application.currency_war.kernel.cw_state import snapshot_copy
from sr_od.application.currency_war.kernel.cw_strategy_session import StrategySession
from sr_od.application.currency_war.strategies.impl.mandate_v1.adapter import (
    PREP_SUBSTATE_NAME,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.contracts import (
    SNAPSHOT_SCHEMA_VERSION,
    RewardSphere,
    Snapshot,
    SubstateClassification,
    SupplyBox,
    Tome,
)

# ------------------------------------------------------- obs 读口注入(期5 ⑦)

def install_obs_ports() -> None:
    """装配点接通 decision 桶的 obs 读口(生产武装点 = CurrencyWarApp.__init__)。

    分包依赖矩阵禁 decision→obs 直依:决策核只持注入槽
    (``cw_strategy._RESET_PHASE_ROUND_CACHE``),本函数从 obs 桶取实现注入。
    未接通(缺省关)= 新局弃置残留容器时跳过 obs 模块级缓存清理——
    session 全量重建承担状态隔离,仅 last-known-good 观测缓存延用旧值。

    同点接通 kernel 侧合成特效帧态门(``cw_reconcile`` 注入槽,分包矩阵禁
    kernel→obs 直依;缺省关 = 门放行走既有连续 2 次确认防抖主干)。

    (原「期望态留证 sink」expected_reconcile.jsonl 装配已随 ADR-0651
    两态制废除——覆盖点 diff 对账随条目表拆除,无 diff 行可落盘。)
    """
    from sr_od.application.currency_war.kernel.cw_reconcile import set_merge_effect_gate
    from sr_od.application.currency_war.obs.cw_identity_obs import (
        is_merge_effect_frame,
    )
    from sr_od.application.currency_war.obs.cw_observation import (
        reset_phase_round_cache,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        set_obs_reset_hook,
    )
    set_obs_reset_hook(reset_phase_round_cache)
    set_merge_effect_gate(is_merge_effect_frame)

    # 缺陷台账生产武装点(迁移批次二,任务书件 7):BoardState 观察覆盖
    # logic 值失配行(kernel/cw_board_state._emit_defect,批次一为缺省关)
    # 经 sink 落 bs_defect.jsonl(与 expected_reconcile.jsonl 同目录同追加
    # 形态);缺省关 = 只缓冲不落盘,测试零真实 IO。
    from sr_od.application.currency_war.kernel.cw_board_state import (
        set_defect_sink,
    )
    set_defect_sink(_bs_defect_sink_for_test(_reconcile_dir()))


def _reconcile_dir() -> Path:
    """bs_defect.jsonl 目录(项目根锚定绝对路径;P4R4 缺陷②:
    旧相对路径依赖 server cwd,cwd 漂移进程把追加写去别处 = 主文件
    「零新增」假截断)。"""
    from one_dragon.utils.file_utils import get_project_root
    return (get_project_root() / '.debug' / 'temp' / 'currency_war')


def _bs_defect_sink_for_test(base_dir: Path):
    """BoardState 缺陷台账 sink 工厂(形态同 expected_reconcile sink;
    单一文件 = bs_defect.jsonl,逐行 JSON,失败静默)。"""
    import json

    def _sink(row: dict) -> None:
        try:
            p = Path(base_dir) / 'bs_defect.jsonl'
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('a', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')
        except Exception:  # noqa: BLE001  留证 best-effort
            pass

    return _sink


# ------------------------------------------------- obs → Snapshot(观察端口)

def snapshot_from_obs(obs: PrepObservation, session: StrategySession,
                      substate_name: str = PREP_SUBSTATE_NAME) -> Snapshot:
    """实机观察视图 → Snapshot(observe 端口;None 语义 = 契约「读不到≠真值」)。

    与 sim 合成器(runner.synthesize_snapshot)共享字段映射语义但**不合并
    实现**:sim 侧恒真位(confident/gold_trusted/shop_open/board…)在本函数
    全部按实机观测原样携带(None 合法)。bench 取紧缩型(仅已识别件,元素
    BenchChar.slot 1-based 保持)。
    """
    from types import MappingProxyType
    st = obs.state
    # Snapshot 消费切换(W6 波 4 决策缝改造:回退锚从投影视图改容器
    # 直读——原 cw_bs_view.strategy_input_state 取帧点随改道消亡,同帧同
    # 视图 = 容器单例一次取用)。obs.state(本帧观察)优先级不变,本锚
    # 只在帧值缺席时兜底(与旧 last_state 兜底同位);读口缺省镜像 = 波 1
    # 公共读口(常态帧与旧直读逐位一致)。
    from sr_od.application.currency_war.kernel.cw_board_state import (
        board_state_of,
        level_of,
        node_kind_of,
        plane_of,
        round_num_of,
    )
    last = board_state_of(session)
    return Snapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        classification=SubstateClassification(
            name=substate_name, evidence=('cw_screen_prep:observe',),
            confident=True),
        plane=(st.plane if st is not None else None)
            or plane_of(last),
        round_num=(st.round_num if st is not None else None)
            or round_num_of(last),
        node_type=(st.node_type if st is not None else None)
            or getattr(session, 'node_type_current', None)
            or node_kind_of(last),
        selected_difficulty=(st.selected_difficulty if st is not None else ''),
        gold=(st.gold if (st is not None and st.gold_readable) else None),
        gold_trusted=bool(obs.state_gold_trusted),
        streak=(st.streak if st is not None else None),
        level=(st.level if st is not None else None) or level_of(last),
        xp_progress=(st.xp_progress if st is not None else None),
        level_up_cost=(st.level_up_cost if st is not None else None),
        bench=tuple(None if b is None else snapshot_copy(b)
                    for b in obs.bench_chars),
        deployed=tuple(None if d is None else snapshot_copy(d)
                       for d in obs.deployed_chars),
        board=(MappingProxyType(dict(st.board))
               if (st is not None and st.board_readable) else None),
        deploy_cap=(st.deploy_cap if st is not None else None),
        deploy_vacancy=obs.deploy_vacancy,
        free_bench_slots=obs.free_bench_slots,
        front_occupied=frozenset(obs.front_occupied),
        back_occupied=frozenset(obs.back_occupied),
        front_size=obs.front_size,
        back_size=obs.back_size,
        shop_open=obs.shop_open,
        shop_cards=None,   # P1 恒 None(PrepObservation 同款)
        spheres=tuple(RewardSphere(color=c, x=p.x, y=p.y, radius=r)
                      for c, p, r in obs.spheres),
        boxes=tuple(SupplyBox(x=p.x, y=p.y) for _s, p in obs.boxes),
        tomes=tuple(Tome(x=p.x, y=p.y) for _s, p in obs.tomes),
        box_overlay_open=obs.box_overlay_open,
        event_overlay=obs.event_overlay,
        hp=(st.hp if (st is not None and st.hp_readable) else None),
        hp_readable=bool(st.hp_readable) if st is not None else False,
    )
