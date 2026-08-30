"""按局存档(cw match archive):终局旁路装配单局档案。

来源:2026-09-07 单局复盘实证的摩擦(规格件见当次任务书,设计要点)——
复盘一局需要在查询侧手工做四件事:跨 run 拼段(server 重启切段)、滤
hp=100 备帧假值、grep 跨 run 帧流、多源现算拼视图。本模块把这套机制化:

- **档案 = 终局旁路产物**:只读 replay/*.jsonl(与判读 CLI 同源同层),
  写 ``replay/matches/``;对运行时零侵入(不改任何内存态/决策路径,
  触发点 try 包裹失败不阻塞局终收口)。
- **触发双路**:①局终钩子(battle_loop 在 ``on_match_end`` 调用点之后调
  ``assemble_pending``,正常局自动装配);②CLI 离线装配(崩溃局/补装配,
  ``--game`` 点名绕过水位线)。旧数据不回填:首次装配以水位线记账
  (``.watermark.json``),只装水位线之后结束的局。
- **game_id 跨段继承**:段首帧非 (p1,r1) 起 = 续局,继承上一段所在局;
  game_id = 首段 run_id 时间戳派生(``g_YYYYMMDD_HHMMSS``)——纯数据派生,
  跨重启稳定,不依赖生成时进程状态。
- **自包含切片**:档案内嵌该局全部关联 jsonl 行切片(decisions/outcomes/
  shop_snapshots/exogenous/invest_cards/spend_ledger),``--match`` 视图
  把切片物化到临时目录后走**同一套** query_* 视图函数——与 ``--run``
  聚合输出保证一致(单一源,不建第二套视图实现)。
  obs_conflicts.jsonl 例外:跨局 journal 无 run_id 键且体积大,不入切片。
- **写盘原子性**:档案与 index 均 tmp 写入 + ``os.replace`` 原子改名,
  并发/中断读者不会读到半截 JSON。

保留策略(先记账不实现):档案体积 ≈ 单局 decisions 切片(百 KB~MB 级),
按局线性增长;方案 = index.jsonl 永久保留(每局一行,KB 级),match_*.json
超保留窗口(如 90 天或目录总量上限)时删档留 index 行(摘要仍可查,
细节回源 replay 原始 jsonl 重装配)。落地时加配置项,本批不实现。
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from sr_od.application.currency_war.telemetry.query import read_jsonl

#: 档案 schema 版本(字段变更时递增;消费端按版本分支)
SCHEMA_VERSION: int = 1

#: 档案子目录(replay/matches/)
MATCHES_DIRNAME: str = 'matches'

#: 水位线文件名(旧数据不回填的记账锚)
_WATERMARK_NAME: str = '.watermark.json'

#: 结算屏真值链可信门槛(与 telemetry-reading 可信白名单同口径:conf≥0.9)
_HP_CONF_TRUSTED: float = 0.9

#: 入切片的 jsonl 流(按 run_id 过滤;obs_conflicts 为跨局 journal 不入)
_SLICE_FILES: tuple[str, ...] = (
    'decisions.jsonl', 'outcomes.jsonl', 'shop_snapshots.jsonl',
    'exogenous.jsonl', 'invest_cards.jsonl', 'spend_ledger.jsonl',
)

#: 终局结果的完结值域;非此值(如 'stopped')= abandoned(ADR-0235 口径:
#: 中断局也装配,标 abandoned 供判读分型)
_TERMINAL_RESULTS: frozenset[str] = frozenset({'win', 'loss'})


def matches_dir(replay_dir: Path | str) -> Path:
    """档案目录:``<replay_dir>/matches``。"""
    return Path(replay_dir) / MATCHES_DIRNAME


def game_id_from_run(run_id: str) -> str:
    """run_id(``run_YYYYMMDD_HHMMSS``)→ game_id(``g_YYYYMMDD_HHMMSS``)。

    非标准 run_id 原样加 ``g_`` 前缀兜底(容错,不抛)。
    """
    ts = run_id[len('run_'):] if run_id.startswith('run_') else run_id
    return f'g_{ts}'


def _row_ts(r: dict[str, Any]) -> str:
    """行时间戳统一读取(排序键;缺失回空串保序)。"""
    return str(r.get('ts') or '')


def _first_frame_key(rows: list[dict[str, Any]], run_id: str) -> tuple[int, int] | None:
    """段首帧的 (plane, round_num)(decisions 优先,outcomes 兜底)。

    判「续局」的依据:一局正常从 (p1,r1) 起;server 重启续打的段首帧
    落在局中某轮 → 该段是上一局的延续。
    """
    best: tuple[int, int] | None = None
    best_ts = ''
    for src in (rows, ):   # 单遍:decisions/outcomes 已由调用方合并传入
        for r in src:
            if r.get('run_id') != run_id:
                continue
            try:
                k = (int(r.get('plane') or 1), int(r.get('round_num') or 0))
            except (TypeError, ValueError):
                continue
            ts = _row_ts(r)
            if best is None or k < best or (k == best and ts < best_ts):
                best, best_ts = k, ts
    return best


def assign_games(replay_dir: Path | str) -> list[dict[str, Any]]:
    """按局分组全量段(outcomes 出现序)→ 有序列表。

    返回元素:``{game_id, segments: [run_id...], start_ts, end_ts}``。
    分组规则:段首帧 = (p1,r1) → 新局(继承规则的主判据);否则续局并入
    上一局。孤立续局(上一局不在库,如首段丢失)自成一体,game_id 取
    本段首段——档案内 ``continuity_note`` 留痕(装配时补)。
    plane/round/hp 连续性只作复核素材,不作分组判据(首帧判据已覆盖
    实证形态;连续性兜底留给未来出现「续局段恰好从 (p1,r1) 误读起」时)。
    """
    outcomes = read_jsonl(Path(replay_dir) / 'outcomes.jsonl')
    decisions = read_jsonl(Path(replay_dir) / 'decisions.jsonl')
    runs = read_jsonl(Path(replay_dir) / 'runs.jsonl')
    # 段出现序:outcomes 首现序;无 outcome 的段(decisions 有帧)按 ts 补尾
    seg_order: list[str] = []
    for o in outcomes:
        rid = o.get('run_id')
        if rid and (not seg_order or seg_order[-1] != rid) and rid not in seg_order:
            seg_order.append(rid)
    known = set(seg_order)
    extra = sorted({d.get('run_id') for d in decisions
                    if d.get('run_id') and d.get('run_id') not in known},
                   key=lambda r: min((_row_ts(d) for d in decisions
                                      if d.get('run_id') == r), default=''))
    seg_order.extend(r for r in extra if r)
    games: list[dict[str, Any]] = []
    for rid in seg_order:
        fk = _first_frame_key(decisions, rid) or _first_frame_key(outcomes, rid)
        is_continuation = (fk is not None and fk != (1, 1)) and bool(games)
        if is_continuation:
            games[-1]['segments'].append(rid)
        else:
            games.append({'game_id': game_id_from_run(rid), 'segments': [rid]})
    for g in games:
        segs = set(g['segments'])
        all_ts = sorted(_row_ts(r) for src in (decisions, outcomes, runs)
                        for r in src if r.get('run_id') in segs and _row_ts(r))
        g['start_ts'] = all_ts[0] if all_ts else ''
        g['end_ts'] = all_ts[-1] if all_ts else ''
    return games


def _load_slice(replay_dir: Path, segments: set[str]) -> dict[str, list[dict[str, Any]]]:
    """按段集合过滤各 jsonl 流(只读;文件缺 = 空列表)。"""
    out: dict[str, list[dict[str, Any]]] = {}
    for name in _SLICE_FILES:
        rows = read_jsonl(replay_dir / name)
        out[name] = [r for r in rows if r.get('run_id') in segments]
    return out


def _best_decision_frame(dec_rows: list[dict[str, Any]],
                         key: tuple[int, int]) -> dict[str, Any] | None:
    """同轮取 actions 最多、并列取 ts 最晚的决策帧(口径与
    ``query._load_decisions_rounds`` 一致,档案装配自持一份避免私有函数耦合)。"""
    best: dict[str, Any] | None = None
    for d in dec_rows:
        try:
            k = (int(d.get('plane') or 0), int(d.get('round_num') or 0))
        except (TypeError, ValueError):
            continue
        if k != key:
            continue
        if (best is None
                or len(d.get('actions') or []) > len(best.get('actions') or [])
                or (len(d.get('actions') or []) == len(best.get('actions') or [])
                    and _row_ts(d) > _row_ts(best))):
            best = d
    return best


def _hp_entry(dec_frame: dict[str, Any] | None,
              outcome: dict[str, Any] | None) -> dict[str, Any]:
    """逐轮 hp 真值链:结算屏(outcomes.hp_after)优先,备帧兜底,带可信位。

    - source='settlement':结算屏真值(trusted = hp_confidence ≥ 0.9);
    - source='frame':决策备帧 hp(trusted = hp_readable 且 state.hp_trusted
      非 False——readable=False 时 hp 是 read_hp miss 沿用值/兜底值,不可信
      必须显影。r1 备战帧例外:血量固定但不恒 100,读失败帧顶层 hp=None
      (recorder 诚实未知口径)自然落 source='none',不再以兜底 100 混入)。
    两源皆缺 → hp=None, trusted=False。
    """
    if outcome is not None and outcome.get('hp_after') is not None:
        conf = outcome.get('hp_confidence')
        return {'hp': outcome['hp_after'], 'source': 'settlement',
                'trusted': isinstance(conf, (int, float))
                and conf >= _HP_CONF_TRUSTED}
    if dec_frame is not None and dec_frame.get('hp') is not None:
        st = dec_frame.get('state') or {}
        trusted = (dec_frame.get('hp_readable') is True
                   and st.get('hp_trusted') is not False)
        return {'hp': dec_frame['hp'], 'source': 'frame', 'trusted': trusted}
    return {'hp': None, 'source': 'none', 'trusted': False}


def _action_counts(actions: list[dict[str, Any]]) -> dict[str, int]:
    """序列化动作清单 → 类型计数(键 = __type__)。"""
    counts: dict[str, int] = {}
    for a in actions or []:
        if isinstance(a, dict) and a.get('__type__'):
            counts[a['__type__']] = counts.get(a['__type__'], 0) + 1
    return counts


def _evidence_links(replay_dir: Path, key: tuple[int, int]) -> list[str]:
    """buy_expect 留证 webp 按轮索引(prep_director 只在对账不一致时落盘,
    文件名 tag=p{plane}-r{round},落 replay 根;可选证据,缺 = 空列表)。"""
    tag = f'p{key[0]}-r{key[1]}_'
    base = Path(replay_dir)
    if not base.exists():
        return []
    return sorted(p.name for p in base.glob(f'buy_expect_{tag}*'))


def _build_rounds(replay_dir: Path, slice_rows: dict[str, list[dict[str, Any]]]
                  ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """装配逐轮表 + 败场节点列表。

    逐轮表键 = (plane, round_num)(位面内序,与全部视图同坐标系);
    每轮聚合:node_type(结算屏真值优先)/ hp 真值链 / 金 / 等级 / 动作
    (计数+全量序列化)/ shop 快照全波(offer/refresh)/ 配对(sess_p1_pair)/
    姿态(dp_posture,decision_v2 决策帧口径)/ form_score / 证据链接。
    败场节点 = hp 链上掉血的轮(delta = 本轮 hp − 前轮 hp < 0;死因素材)。
    """
    dec = slice_rows['decisions.jsonl']
    outs = slice_rows['outcomes.jsonl']
    snaps = slice_rows['shop_snapshots.jsonl']
    keys: set[tuple[int, int]] = set()
    for r in dec + outs:
        try:
            keys.add((int(r.get('plane') or 1), int(r.get('round_num') or 0)))
        except (TypeError, ValueError):
            continue
    out_by_key: dict[tuple[int, int], dict[str, Any]] = {}
    for o in sorted(outs, key=_row_ts):
        try:
            out_by_key[(int(o.get('plane') or 1), int(o.get('round_num') or 0))] = o
        except (TypeError, ValueError):
            continue
    snap_by_key: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for s in snaps:
        try:
            snap_by_key.setdefault(
                (int(s.get('plane') or 1), int(s.get('round_num') or 0)), []).append(s)
        except (TypeError, ValueError):
            continue
    rounds: list[dict[str, Any]] = []
    prev_hp: int | None = None
    for key in sorted(keys):
        frame = _best_decision_frame(dec, key)
        outcome = out_by_key.get(key)
        st = (frame or {}).get('state') or {}
        hp_e = _hp_entry(frame, outcome)
        delta = None
        if hp_e['hp'] is not None and prev_hp is not None:
            delta = int(hp_e['hp']) - int(prev_hp)
        if hp_e['hp'] is not None:
            prev_hp = int(hp_e['hp'])
        actions = (frame or {}).get('actions') or []
        # 姿态:该轮 decision_v2 决策帧的 dp_posture 标签集(载体帧是
        # str(dict) 形态天然不命中,与 _release_frame_counts 同口径)
        dp_tags: list[str] = []
        for d in dec:
            try:
                if ((int(d.get('plane') or 0), int(d.get('round_num') or 0)) == key
                        and (d.get('strategy_id') or '') == 'decision_v2'
                        and isinstance(d.get('dp_posture'), str)
                        and d.get('dp_posture')):
                    dp_tags.append(d['dp_posture'])
            except (TypeError, ValueError):
                continue
        # form_score:同轮末帧时点值(无决策帧 → outcome 无此字段 → None)
        nt_out = (outcome or {}).get('node_type')
        nt_state = st.get('node_type')
        rounds.append({
            'plane': key[0], 'round': key[1],
            'node_type': nt_out or nt_state,
            'node_type_source': 'settlement' if nt_out else (
                'frame' if nt_state else 'none'),
            'hp': hp_e['hp'], 'hp_source': hp_e['source'],
            'hp_trusted': hp_e['trusted'], 'hp_delta': delta,
            'gold': (frame or {}).get('gold'),
            'gold_readable': (frame or {}).get('gold_readable'),
            'level': st.get('level'),
            'xp_progress': st.get('xp_progress'),
            'actions': actions, 'action_counts': _action_counts(actions),
            'shop_snapshots': snap_by_key.get(key, []),
            'sess_p1_pair': (frame or {}).get('sess_p1_pair'),
            'dp_postures': sorted(set(dp_tags)),
            'form_score': (frame or {}).get('form_score'),
            'form_ok': (frame or {}).get('form_ok'),
            'target_comp': (frame or {}).get('target_comp'),
            'board': st.get('board'),
            'deployed': st.get('deployed'),
            'outcome': outcome,
            'evidence': _evidence_links(replay_dir, key),
        })
    loss_nodes = [
        {'plane': r['plane'], 'round': r['round'], 'node_type': r['node_type'],
         'hp': r['hp'], 'delta': r['hp_delta'], 'hp_source': r['hp_source']}
        for r in rounds if r['hp_delta'] is not None and r['hp_delta'] < 0]
    return rounds, loss_nodes


def build_archive(replay_dir: Path | str, game: dict[str, Any]) -> dict[str, Any]:
    """装配单局档案 dict(纯读 + 内存组装;不落盘)。

    ``game`` = ``assign_games`` 的元素(game_id/segments/start_ts/end_ts)。
    """
    rd = Path(replay_dir)
    segments: list[str] = list(game['segments'])
    seg_set = set(segments)
    slice_rows = _load_slice(rd, seg_set)
    rounds, loss_nodes = _build_rounds(rd, slice_rows)
    runs_rows = [r for r in read_jsonl(rd / 'runs.jsonl')
                 if r.get('run_id') in seg_set]
    runs_by_seg = {r.get('run_id'): r for r in runs_rows}
    seg_summaries = [
        {'run_id': rid,
         'first_frame': _first_frame_key(slice_rows['decisions.jsonl'], rid)
         or _first_frame_key(slice_rows['outcomes.jsonl'], rid),
         'summary': runs_by_seg.get(rid)}
        for rid in segments]
    last_summary = runs_by_seg.get(segments[-1]) if segments else {}
    result = str((last_summary or {}).get('result') or '')
    # abandoned 判定:末段无 runs 摘要(收口路径没走)或 result 非完结值域
    abandoned = (not result) or (result not in _TERMINAL_RESULTS)
    # 孤立续局(本段是续局但上一局不在库)留痕:首段首帧非 (p1,r1)
    first_fk = seg_summaries[0]['first_frame'] if seg_summaries else None
    continuity_note = ('孤立续局段(上一段不在库,game_id 取本段)'
                       if first_fk is not None and first_fk != (1, 1) else '')
    return {
        'schema_version': SCHEMA_VERSION,
        'game_id': game['game_id'],
        'segments': seg_summaries,
        'start_ts': game.get('start_ts') or '',
        'end_ts': game.get('end_ts') or '',
        'archived_at': datetime.now().isoformat(timespec='seconds'),
        'continuity_note': continuity_note,
        'rounds': rounds,
        'loss_nodes': loss_nodes,
        'opening': _build_opening(slice_rows, runs_by_seg),
        'endgame': {'result': result or 'abandoned',
                    'abandoned': abandoned,
                    'plane_reached': (last_summary or {}).get('plane_reached'),
                    'rounds_survived': (last_summary or {}).get('rounds_survived'),
                    'final_hp': (last_summary or {}).get('final_hp'),
                    'difficulty': (last_summary or {}).get('difficulty'),
                    'segment_summaries': seg_summaries},
        'slices': slice_rows,
    }


def _build_opening(slice_rows: dict[str, list[dict[str, Any]]],
                   runs_by_seg: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """开局面:词缀/难度/投资卡简报(invest_cards 全行带 chosen 位)。"""
    briefing = [r for r in slice_rows['exogenous.jsonl']
                if (r.get('kind') or '') == 'briefing']
    invest = slice_rows['invest_cards.jsonl']
    return {
        'difficulty': next((r.get('difficulty') for r in runs_by_seg.values()
                            if r.get('difficulty')), ''),
        'briefing_rows': briefing,
        'invest_cards': invest,
        'chosen_env': [r.get('name') for r in invest
                       if r.get('kind') == 'env' and r.get('chosen')],
        'chosen_strategies': [r.get('name') for r in invest
                              if r.get('kind') == 'strategy' and r.get('chosen')],
    }


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """原子写 JSON:tmp 同目录写入 + ``os.replace`` 改名(防半截读)。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent),
                               prefix=path.name + '.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def archive_path(replay_dir: Path | str, game_id: str) -> Path:
    return matches_dir(replay_dir) / f'match_{game_id}.json'


def load_archive(replay_dir: Path | str, game_id: str) -> dict[str, Any] | None:
    """读单局档案;不存在 → None。"""
    p = archive_path(replay_dir, game_id)
    if not p.exists():
        return None
    with p.open('r', encoding='utf-8') as f:
        return json.load(f)


def rebuild_index(replay_dir: Path | str) -> None:
    """从全部档案重建 index.jsonl(一行一局摘要;原子写)。

    摘要字段刻意最小(游戏面身份 + 终局 + 轮数),细节回档案。
    """
    md = matches_dir(replay_dir)
    entries: list[dict[str, Any]] = []
    for p in sorted(md.glob('match_*.json')):
        try:
            with p.open('r', encoding='utf-8') as f:
                a = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue   # 半截/损坏档案不进 index(原子写使概率极低)
        endgame = a.get('endgame') or {}
        entries.append({
            'game_id': a.get('game_id'),
            'segments': [s.get('run_id') for s in (a.get('segments') or [])],
            'start_ts': a.get('start_ts'), 'end_ts': a.get('end_ts'),
            'result': endgame.get('result'),
            'abandoned': endgame.get('abandoned'),
            'plane_reached': endgame.get('plane_reached'),
            'rounds_survived': endgame.get('rounds_survived'),
            'final_hp': endgame.get('final_hp'),
            'n_rounds': len(a.get('rounds') or []),
            'n_loss_nodes': len(a.get('loss_nodes') or []),
        })
    entries.sort(key=lambda e: e.get('start_ts') or '')
    md.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(md), prefix='index.jsonl.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False,
                                   separators=(',', ':')) + '\n')
        os.replace(tmp, md / 'index.jsonl')
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def assemble_game(replay_dir: Path | str, game_id: str) -> dict[str, Any] | None:
    """装配指定局(补装配入口:不问水位线;游戏不存在 → None)。"""
    rd = Path(replay_dir)
    game = next((g for g in assign_games(rd) if g['game_id'] == game_id), None)
    if game is None:
        return None
    archive = build_archive(rd, game)
    _atomic_write_json(archive_path(rd, game_id), archive)
    rebuild_index(rd)
    return archive


def _read_watermark(replay_dir: Path) -> str:
    p = Path(replay_dir) / MATCHES_DIRNAME / _WATERMARK_NAME
    try:
        with p.open('r', encoding='utf-8') as f:
            return str(json.load(f).get('archived_through') or '')
    except (OSError, json.JSONDecodeError, AttributeError):
        return ''


def _write_watermark(replay_dir: Path, through_ts: str) -> None:
    p = Path(replay_dir) / MATCHES_DIRNAME / _WATERMARK_NAME
    _atomic_write_json(p, {'archived_through': through_ts})


def assemble_pending(replay_dir: Path | str) -> list[str]:
    """装配「水位线之后结束、尚未入档」的局(局终钩子/CLI 缺省入口)。

    旧数据不回填:首次调用只落水位线(= 当前最晚局结束时刻),不装任何
    存量局;此后每次只装 end_ts > 水位线的局并推进水位线。崩溃局没走钩子
    也被下次任一触发点补装(end_ts 仍 > 水位线);更早的漏网局用
    ``assemble_game`` 点名补装配。返回本次装配的 game_id 列表。
    """
    rd = Path(replay_dir)
    games = assign_games(rd)
    if not games:
        return []
    wm = _read_watermark(rd)
    done: list[str] = []
    if not wm:
        # 首次启用:只记账不回填(边界:旧段 shop 刷新波已丢,回填也残缺)
        _write_watermark(rd, games[-1]['end_ts'])
        return done
    for g in games:
        if (g['end_ts'] or '') <= wm:
            continue
        if archive_path(rd, g['game_id']).exists():
            continue   # 已入档(如显式补装过)——不重复写
        _atomic_write_json(archive_path(rd, g['game_id']),
                           build_archive(rd, g))
        done.append(g['game_id'])
    if done:
        rebuild_index(rd)
        _write_watermark(rd, games[-1]['end_ts'])
    return done


def materialize_slice(archive: dict[str, Any], tmp_root: Path) -> Path:
    """档案切片 → 临时 replay 目录(供 ``--match`` 复用 query_* 视图)。

    写切片文件后原目录可直接传给 query 视图函数——与 ``--run`` 走同一套
    实现,输出保证一致(单一源)。
    """
    tmp_root.mkdir(parents=True, exist_ok=True)
    for name, rows in (archive.get('slices') or {}).items():
        with (tmp_root / name).open('w', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False,
                                   separators=(',', ':')) + '\n')
    return tmp_root
