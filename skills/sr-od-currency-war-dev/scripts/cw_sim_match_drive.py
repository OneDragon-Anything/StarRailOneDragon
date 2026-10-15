"""sim 单局复盘素材采集:跑一局带遥测落盘的 sim 对局,产出可复盘的对局档案。

定位:sim-testing「找问题」三步主线的第 3 步(挑一局复盘)的数据采集入口——
批驱动器退役后(2026-09-15),sim 局的正规跑法只剩测试冒烟(不落盘遥测,
复盘无数据源);本脚本补上「单局 + 遥测落盘」这一档。装配缝与测试仓
``test/harness/sim_backend_runner.py::run_sim_full_match`` 同源(真策略
mandate_v1 + 真 CwLoop 驱动 SimBackend),差异只有 telemetry 三件套落盘到
独立批目录(不接内存捕获),局终自动点名补装配出对局档案——与实机局同一
判读通道(match-review 协议口径)。

sim 批绝不写生产 replay 目录(sim-testing 红线):recorder 根 / state
journal / 决策帧 / debug 图 / 窗口运行锁全部重定向到批目录,生产零触碰。

用法(项目根):

    uv run python skills/sr-od-currency-war-dev/scripts/cw_sim_match_drive.py --seed 20261012
    uv run python skills/sr-od-currency-war-dev/scripts/cw_sim_match_drive.py --seed 7 --out-dir <目录>

产出(批目录内):``matches/match_<game_id>.json``(对局档案,复盘主数据)、
``state/journal.jsonl``(kernel 状态流水,行级溯源)、``decision_frames/``
(识别仲裁帧)、终态摘要与复盘入口提示打在 stdout。跑完拿档案按
match-review 协议复盘即可。

边界:
- 局配置固定 A8 / 敌方难度 108 / 标准博弈 / 环境在场(与测试冒烟同口径;
  A8 是开局 HP 唯一实证档,其余档注册表报错索样本,不设参数不外推);
- 敌方词缀缺省由 seed 采样(RunConfig override 语义);
- 依赖测试仓 ``sr-od-test/``(harness/conftest 单一源,禁第二份装配复制);
- 健康局秒级收口;卡死局由看门狗 1200 轮兜底(可能数分钟)。
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import time
from pathlib import Path


def _find_project_root() -> Path:
    """项目根定位:从脚本位置向上找含 ``src/sr_od`` 的祖先。

    经 junction(.dsh/skills/...)调用时 ``__file__.resolve()`` 已落到本仓
    skills/ 真实路径,向上三级即项目根;再校验测试仓在位(装配缝依赖)。
    """
    here = Path(__file__).resolve()
    for cand in here.parents:
        if (cand / 'src' / 'sr_od').is_dir():
            if not (cand / 'sr-od-test' / 'test' / 'harness').is_dir():
                raise SystemExit(
                    f'测试仓缺失: {cand / "sr-od-test"} 不存在或不含 test/harness——'
                    '本脚本装配缝复用测试仓单一源(sr-od-test/README.md),请先就位。')
            return cand
    raise SystemExit(f'项目根定位失败: {here} 向上未找到含 src/sr_od 的目录')


ROOT = _find_project_root()
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'sr-od-test'))

# ---- 日志静音(照 sr-od-test/test/conftest.py 手法:进程不写共享日志文件,
#      与 GUI/MCP server 的 log.txt 零句柄交集;脚本输出一律走 print) ----
from one_dragon.utils import log_utils  # noqa: E402
from one_dragon.utils.log_utils import log as framework_log  # noqa: E402

log_utils._close_managed_handlers(framework_log)  # noqa: SLF001
_nh = logging.NullHandler()
_nh._one_dragon_logger_owner = framework_log.name  # noqa: SLF001
framework_log.addHandler(_nh)
framework_log.propagate = False
framework_log.setLevel(logging.WARNING)


def _print_match_digest(journal_path: Path, run_id: str) -> None:
    """局况摘要(hp 链 / 节点序 / 金轨迹 / 终态):stdout 直接可读,
    免二次脚本;逐行锚 = journal 写行 v 号(复盘报告引用行锚用)。"""
    hp_rows: list[tuple[int, object, dict]] = []
    gold_by_node: dict[tuple[int, int], list] = {}
    node_seq: dict[int, list[tuple[int, str]]] = {}
    final_state: dict = {}
    for line in journal_path.open(encoding='utf-8'):
        r = json.loads(line)
        if r.get('run_id') != run_id or r.get('row') != 'write':
            continue
        node = (r.get('state') or {}).get('values', {}).get('node')
        field = r.get('field')
        if field == 'hp':
            hp_rows.append((r['v'], r.get('after'), node or {}))
        elif field == 'gold' and node:
            gold_by_node.setdefault(
                (node['plane'], node['round_num']), []).append(r.get('after'))
        elif field == 'node' and r.get('after'):
            n = r['after']
            node_seq.setdefault(n['plane'], []).append((n['round_num'], n['kind']))
        final_state = (r.get('state') or {}).get('values', final_state)

    print('--- hp 链(写行 v 号即行锚) ---')
    for v, a, n in hp_rows:
        print(f'  v={v:>3} hp={a}  P{n.get("plane")}r{n.get("round_num")}({n.get("kind")})')
    print('--- 节点序 ---')
    for p, lst in sorted(node_seq.items()):
        print(f'  P{p}: {lst}')
    print('--- 金轨迹(每节点 首末) ---')
    for k in sorted(gold_by_node):
        vals = gold_by_node[k]
        print(f'  P{k[0]}r{k[1]}: {vals[0]} -> {vals[-1]}')
    print('--- 终态 ---')
    print(f'  gold={final_state.get("gold")} level={final_state.get("level")} '
          f'hp={final_state.get("hp")} bench={len((final_state.get("bench") or {}).get("slots") or [])}')


def main() -> int:
    ap = argparse.ArgumentParser(
        description='跑一局带遥测落盘的 sim 对局(复盘素材采集)')
    ap.add_argument('--seed', type=int, default=None,
                    help='世界与策略共用种子(缺省 = 当前 HHMMSS,stdout 已印,同 seed 可复现)')
    ap.add_argument('--strategy-seed', type=int, default=None,
                    help='策略器种子(缺省 = 世界种子;测试冒烟同口径)')
    ap.add_argument('--out-dir', type=str, default=None,
                    help='批目录(缺省 = .debug/currency_war/telemetry/sim/sim_match_<时刻>)')
    args = ap.parse_args()
    seed = args.seed if args.seed is not None else int(time.strftime('%H%M%S'))
    strategy_seed = args.strategy_seed if args.strategy_seed is not None else seed
    out_dir = (Path(args.out_dir).resolve() if args.out_dir else
               ROOT / '.debug' / 'currency_war' / 'telemetry' / 'sim'
               / f'sim_match_{time.strftime("%Y%m%d_%H%M%S")}')
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f'[drive] root={ROOT}')
    print(f'[drive] out_dir={out_dir} seed={seed} strategy_seed={strategy_seed}')

    import pytest

    from sr_od.application.currency_war.kernel import cw_state_journal
    from sr_od.application.currency_war.kernel.cw_state_journal import (
        install_state_telemetry,
        reset_state_telemetry,
    )
    from sr_od.application.currency_war.telemetry import state as tel_state

    # ---- telemetry 重定向(先于 CW 装配;句柄级直接装,teardown 逐槽复位) ----
    tel_state.set_recorder_replay_dir(out_dir)
    install_state_telemetry(out_dir / 'state' / 'journal.jsonl',
                            run_id_provider=tel_state.current_run_id)

    mp = pytest.MonkeyPatch()
    run_id = ''
    try:
        mp.setattr(cw_state_journal, 'default_journal_path',
                   lambda: out_dir / 'state' / 'journal.jsonl')
        import one_dragon.utils.cv2_utils as cv2_utils
        from one_dragon.utils import debug_utils

        _dbg_dir = out_dir / 'debug_images'
        _dbg_dir.mkdir(exist_ok=True)

        def _save_debug_to_out(image, file_name=None, prefix: str = '',
                               copy_screenshot: bool = False):
            fn = (file_name if file_name is not None
                  else f'{prefix}_{round(time.time() * 1000)}')
            cv2_utils.save_image(image, str(_dbg_dir / f'{fn}.png'))
            return fn

        mp.setattr(debug_utils, 'save_debug_image', _save_debug_to_out)
        from one_dragon.base.operation import window_run_mutex
        mp.setattr(window_run_mutex, 'default_lock_dir',
                   lambda: out_dir / 'run_mutex')
        # 决策帧落点(patch _out_dir 而非 get_project_root:后者是 hooks 模块
        # from-import 绑定,patch 它拼出的嵌套路径丑;_out_dir 直返批内目录)
        from sr_od.application.currency_war.operations import decision_frame_hooks
        mp.setattr(decision_frame_hooks, '_out_dir',
                   lambda run_id_: out_dir / 'decision_frames' / run_id_)

        # ---- 测试 ctx(照 conftest::test_context;不 init OCR——sim obs 纯生成器) ----
        from test.conftest import MockController

        from one_dragon.envs.ghproxy_service import GhProxyService
        from sr_od.context.sr_context import SrContext

        ctx = SrContext()
        ctx.env_config.is_debug = True
        ctx.current_instance_idx = 99
        _real_update_proxy = GhProxyService.update_proxy_url
        GhProxyService.update_proxy_url = lambda self: False
        try:
            ctx.init_by_config()
        finally:
            GhProxyService.update_proxy_url = _real_update_proxy
        ctx.load_instance_config()
        ctx.controller = MockController(
            game_config=ctx.game_config,
            standard_width=ctx.project_config.screen_standard_width,
            standard_height=ctx.project_config.screen_standard_height,
        )

        # ---- sim 全流程装配(装配缝 = run_sim_full_match 同源) ----
        from types import SimpleNamespace

        from test.harness.fixture_controller import (
            WatchdogOperationMixin,
            enter_running_state,
            fast_sleep,
            reset_running_state,
        )
        from test.harness.sim_backend_runner import (
            SimControllerStub,
            freeze_cw_module_time,
        )

        from sr_od.application.currency_war.kernel.cw_game_state import (
            bind_session_container,
        )
        from sr_od.application.currency_war.kernel.cw_reconcile import (
            set_merge_effect_gate,
        )
        from sr_od.application.currency_war.kernel.cw_strategy_session import (
            StrategySession,
        )
        from sr_od.application.currency_war.obs.cw_identity_obs import (
            is_merge_effect_frame,
        )
        from sr_od.application.currency_war.obs.cw_observation import (
            reset_phase_round_cache,
        )
        from sr_od.application.currency_war.operations.cw_loop import CwLoop
        from sr_od.application.currency_war.sim.cw_sim_backend import (
            SimBackend,
            install_backend,
            uninstall_backend,
        )
        from sr_od.application.currency_war.sim.cw_sim_run_config import RunConfig
        from sr_od.application.currency_war.strategies.impl.cw_strategy import (
            CurrencyWarMatch,
            set_obs_reset_hook,
        )
        from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
            bridge as cw_bridge,
        )

        set_obs_reset_hook(reset_phase_round_cache)
        set_merge_effect_gate(is_merge_effect_frame)

        backend = SimBackend(
            seed=seed,
            cfg=RunConfig(selected_difficulty='A8', enemy_difficulty=108,
                          env_present=True, enemy_affixes=()))
        install_backend(backend)

        session = StrategySession()
        session.rng = random.Random(strategy_seed)
        bind_session_container(session, backend.gs)
        strategy = cw_bridge.MandateV1Strategy(
            backend.gs, SimpleNamespace(strategy_seed=strategy_seed))
        session.strategy_state = strategy.state
        match = CurrencyWarMatch(strategy, session, backend.gs,
                                 performance=getattr(session, 'performance', None))

        mp.setattr(ctx, 'controller', SimControllerStub())

        class _WatchedLoop(WatchdogOperationMixin, CwLoop):
            pass

        _WatchedLoop.watchdog_max_rounds = 1200
        mp.setattr(ctx, 'cw_match', match, raising=False)
        enter_running_state(ctx)
        loop = None
        started = time.perf_counter()
        try:
            with freeze_cw_module_time():
                loop = _WatchedLoop(ctx)
                with fast_sleep(loop):
                    result = loop.execute()
        except Exception as exc:
            exc.add_note(
                f'sim 单局崩点: seed={seed}, node={backend.gs.node.value!r}, '
                f'screen={backend._screen!r}, steps={backend._steps}, '
                f'hp={backend.gs.hp.value!r}, gold={backend.gs.gold.value!r}')
            raise
        finally:
            if loop is not None:
                reset_running_state(ctx, loop)
            uninstall_backend()
        dur = time.perf_counter() - started
        if not (getattr(result, 'success', False) and backend.done):
            print(f'[drive] 局未正常收口: success={getattr(result, "success", None)} '
                  f'done={backend.done}(journal 仍在,可作卡死排查素材)')

        # ---- 统计行(冒烟同口径;死亡/进 P3 两源都算跑完) ----
        node = backend.gs.node.value
        if not backend.done:
            terminal = 'abandoned'
        elif backend.gs.hp.value is not None and int(backend.gs.hp.value) == 0:
            terminal = 'death'
        else:
            terminal = 'p3_enter'
        hp_trail = backend.hp_trail or (0,)
        print(f'[smoke] seed={seed} terminal={terminal} '
              f'end=P{node.plane}r{node.round_num}({node.kind}) '
              f'settled={loop._settle.rounds_done} steps={backend._steps} '
              f'gold={int(backend.gs.gold.value or 0)} '
              f'level={int(backend.gs.level.value or 0)} hp_min={min(hp_trail)} '
              f'fail_streak={loop._op_fail_streak_n} dur={dur:.1f}s')
        run_id = tel_state.current_run_id()
        print(f'[drive] run_id={run_id!r}')
        return _finalize(out_dir, run_id)
    finally:
        mp.undo()
        reset_state_telemetry()
        tel_state.set_recorder_replay_dir(None)
        tel_state.reset_run_state()


def _finalize(out_dir: Path, run_id: str) -> int:
    """局终收尾:点名补装配对局档案 + 摘要 + 复盘入口提示(失败不阻塞)。"""
    journal_path = out_dir / 'state' / 'journal.jsonl'
    archive_path: Path | None = None
    game_id = ''
    if run_id:
        # 水位线坑:assign_games 对 journal-only 段(旧流停写后)end_ts = 段首行
        # ts = 开局时刻,单局目录内 assemble_pending 的 end_ts<=wm 判定永久跳过
        # ——必须 assemble_game 点名补装(match_archive.assemble_pending 注:
        # 更早漏网局即用点名补装配,本脚本把该形态常态化)。
        try:
            from sr_od.application.currency_war.telemetry import match_archive
            game_id = match_archive.game_id_from_run(run_id)
            # assemble_game 返回值 = 档案 dict(非路径);落盘路径走 archive_path
            match_archive.assemble_game(out_dir, game_id)
            archive_path = match_archive.archive_path(out_dir, game_id)
        except Exception as e:  # noqa: BLE001  档案装配失败不阻塞(journal 仍可复盘)
            print(f'[drive] 档案装配失败(可用 journal 直读复盘): {e}')
    if archive_path is not None:
        print(f'[drive] 对局档案: {archive_path}')
    if journal_path.exists():
        print(f'[drive] journal 流水: {journal_path}')
        _print_match_digest(journal_path, run_id)
    print(f'[drive] 复盘入口: game_id={game_id or "(见上)"} —— 按 match-review '
          f'协议复盘,数据 = 上述档案/journal;批统计 = cw_batch_stats.py(旧流'
          f'字段,对本形态不适用)')
    print('[drive] artifacts:')
    for p in sorted(out_dir.rglob('*')):
        if p.is_file():
            print(f'  {p.relative_to(out_dir)}  ({p.stat().st_size}B)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
