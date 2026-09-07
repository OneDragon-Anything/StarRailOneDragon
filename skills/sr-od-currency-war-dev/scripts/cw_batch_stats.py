"""批统计面(九族过程量:资源转化/成型/战斗/供给/达标臂发射/终态/采购面三观察…;2026-09-07 反馈条目落地,发射面/采购观察/必花域观测为后补族)。

定位:第 1 步统计+按指标点名最差局(供第 3 步挑局复盘);怎么判定「表现不好」不在此规定。
两种数据源:
    --sim-batch <名|latest>   sim 批次目录三流账本(ADR-0242 同构)
    --recent N / --match ID   生产对局档案(matches/;词缀条件化分组仅此模式——sim 未建模词条)

用法(项目根;⚠️ 缺省根是 cwd 相对 Path,须从项目根运行,另机/异目录
语料用 --sim-root/--matches-root 显式指路):
    uv run python skills/sr-od-currency-war-dev/scripts/cw_batch_stats.py --sim-batch latest
    uv run python skills/sr-od-currency-war-dev/scripts/cw_batch_stats.py --recent 10

口径注记(判读时心里有数):
- 胜/败从 hp 链推导(战斗类节点 hp 下降=败),无显式字段;生产档案用 hp_delta;
- 「核心二星」用「任意 deployed 2★」近似;供给利用的「相关卡」=阵营与板面交集(游戏语义);
- 「危局空转」= 连败≥2 或 hp≤40 窗口内的零动作轮(复盘试金石:140843 局 R4-6 金44-57 连败不花);
- sim 侧无词缀/补给选项(未建模)——词缀分组仅档案模式;补给选择相关率挂档案二期字段缺口;
- 末尾「表现不好的指标→最差局」是纯排序,不拍阈值;哪边算差见各指标括号(高为差/低为差)。
- 位面/锁线辖域披露(L 节):planes/plane_list/locked_frames 三字段数据源 = 逐局
  decisions 行现有键(planes = plane 键集合;锁线布尔 = v3_intention.locked_comp 非空,
  单一源与引擎一致);档案轮无 v3_intention 键 → locked_frames 为「无数据」不误报 0;
  单面批(planes=1)自动声明「L2 辖域不可达」注记——L2 触发链前置锁线,位面入口
  才建立锁线态,单面批 L2=0 是辖域结果,禁当行为信号;
- 对拍口径:统一触发面键 = cw4_counters.must_spend_l2_trigger(触发帧数),
  发射面 = must_spend_layer_hit.L2(层命中),两者分开披露不互换(实机报告键口径
  = 触发帧数,与批报告发射数不对称,对拍时先对齐口径)。
- G4 r288 复发门·部署通道(ADR-0564 §6 预注册派生指标):锁定列车冲突语境
  轮的「轮间 roster diff 仙舟全羁绊件离场事件数」,账本零新增字段;两个判定件
  (仙舟全羁绊件集/locked_comp 冲突语境)直调 src 注册表单一源,src 不可达时
  报「无数据」不误报 0。
- C 族羁绊达成率分诊(2026-09-08「校准后首跑」找问题批 F3①):行级
  board_factions 键缺/None = 无数据,不入达成率分母(行文附「分母=有观测
  N 局」);0% 只属于「有观测全灭」——无数据与全灭是两种事实,混同会把
  档案伪影当行为信号(该批 FakeP1Run 假局 0/222 行带此键,误报达成率 0%)。
- C 族等级末值双口径(同批 F3②):「等级末值」= 决策帧快照(末帧 LevelUp
  升级不计入,与等级曲线/爬升同源);「等级末值·帧内升级后」= 快照 + 末轮
  LevelUp 动作逐击结算(口径出处 = 该批重算脚本 true_end_level.py;仅计
  升级动作 XP,BuyCard 同源 XP 未计入 = 低估下界),详见 true_end_level。
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path

# 落盘根(2026-09-07 布局裁定,.debug/currency_war/telemetry/{live,matches,sim};
# 单一源 = src kernel/cw_observe 根常量块,本脚本零 src 导入故按同值独立声明)
SIM_ROOT = Path('.debug/currency_war/telemetry/sim')
MATCHES = Path('.debug/currency_war/telemetry/matches')
BATTLE_SKIP = {'奖励', '补给'}
STAGNANT_EPS = 0.02
HP_ALERT = 40          # 危局血线(占位,[18] 报警语义)


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in open(path, encoding='utf-8') if line.strip()]


def pct(vals: list[float], p: float) -> float:
    s = sorted(vals)
    return s[min(int(len(s) * p), len(s) - 1)] if s else float('nan')


def agg_key(vals: list) -> tuple | None:
    """裸数值列表 → (中位, p90);空 = None(冷启动金轨迹逐轮聚合用)。"""
    nums = [v for v in vals if isinstance(v, (int, float))]
    return (round(statistics.median(nums), 2), pct(nums, 0.9)) if nums else None


# ---------- 数据装配:统一成 row{plane,round,node_type,gold,hp,hp_delta,form,form_ok,level,deployed,factions,acts} ----------

def _sim_rows(batch: Path) -> dict[str, list[dict]]:
    dec = _load(batch / 'decisions.jsonl')
    outs = _load(batch / 'outcomes.jsonl')
    games: dict[str, dict] = {}

    def g(rid: str) -> dict:
        return games.setdefault(rid, {'rounds': {}, 'outs': {}})

    for r in dec:
        st = r.get('state') or {}
        key = (r.get('plane') or 1, r.get('round_num') or 0)
        g(r.get('run_id') or '?')['rounds'][key] = {
            'plane': key[0], 'round': key[1], 'node_type': None,
            'gold': r.get('gold'), 'hp': r.get('hp'), 'hp_delta': None,
            'form': r.get('b_t', r.get('form_score')), 'form_ok': r.get('form_ok'),  # b_t 优先(新数据),form_score 回退读历史(退役只读)
            # 锁线布尔(单一源 = v3_intention.locked_comp 非空;L 位面/锁线辖域披露用)
            'locked': bool((r.get('v3_intention') or {}).get('locked_comp')),
            # G4 语境行级数据(ADR-0564 §6):locked_comp 原串供注册表
            # 解析冲突语境(非空即语境候选);bench = roster-diff 全集另一半
            'locked_comp': (r.get('v3_intention') or {}).get('locked_comp') or '',
            'level': st.get('level'), 'xp': st.get('xp_progress'),
            'deployed': st.get('deployed') or [],
            'bench': st.get('bench') or [],
            # board_factions 键缺/None = 无数据(2026-09-08「校准后首跑」找
            # 问题批 F3①:FakeP1Run 假局档案结构性不带该行级键);直传 None
            # 不折空 dict——「无数据」与「有观测全灭」是两种事实,C 族达成率
            # 分母剔除前者(混同会把档案伪影当达成率 0%)。键在值空 dict =
            # 有观测空板,照常有数据。
            'factions': (dict(st['board_factions'])
                         if st.get('board_factions') is not None else None),
            'acts': r.get('actions') or [],
            # 达标臂发射事件(行内 launch 键,engine_p1 建模;None=未触发)
            'launch': r.get('launch'),
            # 采购面三观察计数(行内 obs 键,engine_p1 建模;缺键=旧批)
            'obs': r.get('obs') or {},
        }
    for o in outs:
        g(o.get('run_id') or '?')['outs'][(o.get('plane') or 1, o.get('round_num') or 0)] = o
    for s in _load(batch / 'shop_snapshots.jsonl'):
        if s.get('event') == 'offer':
            g(s.get('run_id') or '?').setdefault(
                'shops', {}).setdefault((s.get('plane') or 1, s.get('round_num') or 0),
                                        []).append(s.get('shop') or [])
    out: dict[str, list[dict]] = {}
    for rid, gd in games.items():
        rows = [gd['rounds'][k] for k in sorted(gd['rounds'])]
        prev_hp = None
        for r in rows:
            r['shop_waves'] = gd.get('shops', {}).get((r['plane'], r['round']), [])
            o = gd['outs'].get((r['plane'], r['round']))
            if o:
                r['node_type'] = o.get('node_type')
                hp_after = o.get('hp_after')
                r['hp_delta'] = (None if prev_hp is None or hp_after is None
                                 else hp_after - prev_hp)
                prev_hp = hp_after
            elif r['hp'] is not None:
                prev_hp = r['hp']
        out[rid] = rows
    return out


def _archive_rows(mid: str) -> dict[str, list[dict]]:
    p = MATCHES / f'match_{mid}.json'
    if not p.exists():
        idx = _load(MATCHES / 'index.jsonl')
        hit = [e['game_id'] for e in idx if e.get('game_id', '').endswith(mid)]
        if not hit:
            raise SystemExit(f'档案不存在:{mid}')
        p = MATCHES / f'match_{hit[-1]}.json'
    m = json.loads(p.read_text(encoding='utf-8'))
    def _waves(raw) -> list[list]:
        if not isinstance(raw, list):
            return []
        ws = []
        for w in raw:
            if isinstance(w, dict):
                w = w.get('shop') or []
            ws.append(w if isinstance(w, list) else [])
        return ws

    rows = [{
        'plane': r.get('plane'), 'round': r.get('round'), 'node_type': r.get('node_type'),
        'gold': r.get('gold'), 'hp': r.get('hp'), 'hp_delta': r.get('hp_delta'),
        'form': r.get('b_t', r.get('form_score')), 'form_ok': r.get('form_ok'),  # b_t 优先(新数据),form_score 回退读历史(退役只读)
        # 档案轮无 v3_intention 键 → None(锁线辖域披露为「无数据」,不误报 0)
        'locked': None,
        # G4 语境:档案行无 locked_comp → None(G4 报无数据;将来档案带
        # v3_intention 时自动升级为可算)
        'locked_comp': None,
        'level': r.get('level'), 'xp': r.get('xp_progress'),
        'deployed': r.get('deployed') or [],
        'bench': r.get('bench') or [],
        # 档案行 board=None = 无决策帧/字段缺(match_archive 装配语义),
        # 与 sim 行同分诊口径:C 族无数据剔除,不折空 dict 误报 0%
        'factions': (dict(r['board']) if r.get('board') is not None else None),
        'acts': r.get('actions') or [],
        # 档案侧发射面:行动作里的 StartBattle(生产发射核执行痕迹;
        # 档案只记「发生了」,ok 恒 True——发射失败形态仅 sim/生产
        # 计数器有真值,成功率面判读以 sim 批为准)
        'launch': ({'__type__': 'StartBattle', 'ok': True}
                   if any(a.get('__type__') in ('StartBattle', 'LaunchBattle')
                          for a in r.get('actions') or []) else None),
        'shop_waves': _waves(r.get('shop_snapshots')),
        # 档案行无 sim 行内 obs 键(生产决策帧无同构计数)——采购面观察
        # 为 sim 专属,档案模式恒空 dict(统计族退化为 0/None,不误报)
        'obs': {},
    } for r in m.get('rounds', [])]
    affixes: list[str] = []
    for b in (m.get('opening', {}).get('briefing_rows') or []):
        mt = re.search(r'affixes=\[([^\]]*)\]', str(b.get('detail') or ''))
        if mt:
            affixes = [a.strip().strip("'\"") for a in mt.group(1).split(',')]
            break
    eg = m.get('endgame', {}) or {}
    return {'game_id': m.get('game_id', mid), 'rows': rows, 'affixes': affixes,
            'result': eg.get('result'), 'final_hp': eg.get('final_hp'),
            'plane_reached': eg.get('plane_reached')}


# ---------- 指标 ----------

# 购买经验单击 XP 与升级门槛表(同值独立声明;单一源 = src
# sr_od/application/currency_war/kernel/cw_state.py 的 XP_PER_BUY /
# XP_TO_NEXT_LEVEL,本脚本零 src 导入先例同 SIM_ROOT 注记)。
XP_PER_BUY: int = 4
XP_TO_NEXT_LEVEL: dict[int, int] = {3: 4, 4: 6, 5: 20, 6: 40, 7: 52, 8: 72, 9: 84}


def true_end_level(row: dict) -> int | None:
    """末轮真实终级:行快照 lv/xp + 行内 LevelUp 动作逐击结算(帧内升级计入)。

    口径出处 = 2026-09-08「校准后首跑」找问题批重算脚本 true_end_level.py
    (F3②:决策帧 = 轮初快照,末帧快照不含帧内 LevelUp 升级,快照口径
    「等级末值」在该批 24 局系统性低估——快照中位 4 vs 真实终级中位 5)。

    边界(判读前先读):
    - 只结算 LevelUpShop/LevelUp 动作 XP(+XP_PER_BUY/击);BuyCard 同源
      XP(ADR-0286 买牌给经验建模)未计入 → 数值为低估下界,与该批重算
      单一源可逐局对照;
    - 快照 xp 缺(合成行/旧数据)按 [0, 当前级门槛] 近似,xp 结转丢失;
    - sim 行 = 每轮末帧快照 + 末帧动作(早帧动作已反映在快照,不丢不重);
      档案行 = 计划最全决策帧快照 + 全轮动作(match_archive 装配语义),
      同轮后置帧动作更多的局存在超计边界(罕见形态)。
    """
    lv = row.get('level')
    if lv is None:
        return None
    xp = list(row.get('xp') or [0, XP_TO_NEXT_LEVEL.get(lv, 4)])
    for a in row.get('acts') or []:
        if a.get('__type__') in ('LevelUpShop', 'LevelUp'):
            xp[0] += XP_PER_BUY
            while xp[0] >= xp[1] and lv < 10:
                xp[0] -= xp[1]
                lv += 1
                xp[1] = XP_TO_NEXT_LEVEL.get(lv, 999)
    return lv


def act_cost(acts: list[dict]) -> int:
    spend = 0
    for a in acts:
        t = a.get('__type__')
        if t == 'BuyCard':
            spend += (a.get('card') or {}).get('cost') or 0
        elif t == 'LevelUp':
            spend += a.get('cost') or 0
        elif t == 'RefreshShop':
            spend += 2
        elif t == 'SellBench':
            spend -= (a.get('cost') or (a.get('card') or {}).get('cost') or 0)
    return spend


def n_act(acts: list[dict], *ts: str) -> int:
    return sum(1 for a in acts if a.get('__type__') in ts)


def zero_action(acts: list[dict]) -> bool:
    return n_act(acts, 'BuyCard', 'LevelUp', 'RefreshShop') == 0


def _g1_no_victim(launch: dict) -> bool:
    """发射帧是否命中生产计数键 deploy_swap_no_victim 的三元联合形态。

    = 板满 ∧ bench core 待上 ∧ 缺合格 victim(launch.victim = G1 准入
    三元,cw_launch_admission.launch_admission_report 输出,与生产
    cw_loop 显影同键同字段)。victim 缺席(准入异常吞 None/档案行无
    观测)≠ 命中。
    """
    a = launch.get('victim') or {}
    return bool(a.get('board_full') and a.get('bench_core_waiting')
                and a.get('victim_missing'))


# ---------- G4 r288 复发门·部署通道(ADR-0564 §6 预注册派生指标)----------

_G4_REG: dict | None = None


def _find_src_dir() -> Path | None:
    """定位含 ``sr_od`` 包的 src 目录(脚本可能从任意 cwd 调用:
    候选 = cwd/src 与 __file__ 各级祖先直下/其 src 子目录)。"""
    cands: list[Path] = [Path.cwd() / 'src']
    cands.extend(Path(__file__).resolve().parents)
    for cand in cands:
        if (cand / 'sr_od').is_dir():
            return cand
        if (cand / 'src' / 'sr_od').is_dir():
            return cand / 'src'
    return None


def _make_conflict_fn(cw_intention):
    """冲突语境判定包装(fail-closed:解析异常 = 非冲突语境)。"""
    from types import SimpleNamespace

    def conflict(locked_comp: str) -> bool:
        try:
            return bool(cw_intention.locked_line_recipe_floor_conflict(
                SimpleNamespace(locked_comp=locked_comp)))
        except Exception:
            return False
    return conflict


def _g4_registry() -> dict | None:
    """G4 判定件的 src 注册表句柄(懒加载;不可达 = None → 无数据)。

    两个判定件都是注册表单一源,禁在脚本内复制第二份口径:
    - 仙舟全羁绊件集 = ``cw_chars.chars_by_faction('仙舟',
      include_flows=True)``(CHARACTERS 查表 factions+flows 含仙舟,
      ADR-0564 §6 G4 口径原文);
    - 冲突语境 = ``cw_intention.locked_line_recipe_floor_conflict``
      (locked_comp 可解析 ∧ form_tiers['列车同行'] > 门封顶档;
      鸭子型直喂只含 locked_comp 单键——helper 只读该键)。
    运行环境无 src(PYTHONPATH 缺失)时记失败缓存不再重试,消费面
    读 None 按无数据披露,不误报 0。
    """
    global _G4_REG
    if _G4_REG is not None:
        return _G4_REG or None
    import sys
    src = _find_src_dir()
    try:
        if src is not None:
            sys.path.insert(0, str(src))
        from sr_od.application.currency_war.data.cw_chars import (
            chars_by_faction,
        )
        from sr_od.application.currency_war.kernel import cw_intention
        _G4_REG = {
            'xz_all': frozenset(
                c.name for c in chars_by_faction('仙舟', include_flows=True)),
            'conflict': _make_conflict_fn(cw_intention),
        }
    except Exception:
        _G4_REG = {}
    return _G4_REG or None


def roster_cids(row: dict) -> set[str]:
    """行 roster 全集 = state.deployed/bench 逐件 char_id 并集
    (G4 差分输入;ADR-0564 §6「逐件 char_id 集合」口径)。"""
    return ({d.get('char_id') or '' for d in row.get('deployed') or []}
            | {d.get('char_id') or '' for d in row.get('bench') or []})


def analyze_game(rows: list[dict]) -> dict:
    m: dict = {}
    spends = [act_cost(r['acts']) for r in rows]
    golds = [r['gold'] for r in rows if r['gold'] is not None]
    income = (golds[-1] - golds[0] + sum(spends)) if golds else 0
    m['花费率'] = round(sum(spends) / income, 2) if income > 0 else float('nan')
    m['空转轮占比'] = round(sum(1 for r in rows if (r['gold'] or 0) >= 3 and zero_action(r['acts']))
                        / max(len(rows), 1), 2)
    # 危局空转:连败≥2(窗口内 hp_delta<0 的战斗轮)或 hp≤40 时的零动作轮
    losses = [bool(r['node_type'] not in BATTLE_SKIP and (r['hp_delta'] or 0) < 0) for r in rows]
    m['危局空转轮数'] = sum(
        1 for i, r in enumerate(rows)
        if zero_action(r['acts']) and ((r['hp'] is not None and r['hp'] <= HP_ALERT)
                                       or (i >= 2 and all(losses[i - 2:i]))))
    m['行动配比'] = {t: sum(n_act(r['acts'], t) for r in rows)
                  for t in ('BuyCard', 'LevelUp', 'RefreshShop', 'SellBench')}
    forms = [r['form'] for r in rows if r['form'] is not None]
    m['末轮成型度'] = forms[-1] if forms else float('nan')
    stag = best_s = 0
    for i in range(1, len(forms)):
        stag = stag + 1 if abs(forms[i] - forms[i - 1]) < STAGNANT_EPS else 0
        best_s = max(best_s, stag)
    m['停滞最长轮数'] = best_s
    # 羁绊达标轮:factions=None 行(无观测)跳过不参与判定;达成率分母
    # 剔除在 report 侧(逐局 _factions_seen 标记)
    _fac_rows = [r for r in rows if r['factions'] is not None]
    m['_factions_seen'] = bool(_fac_rows)
    for fac, need in (('仙舟', 3), ('持续伤害', 2), ('列车同行', 2)):
        m[f'{fac}{need}达成轮'] = next(
            (r['round'] for r in _fac_rows
             if r['factions'].get(fac, 0) >= need), None)
    m['首个2★轮'] = next(
        (r['round'] for r in rows if any(d.get('star', 0) >= 2 for d in r['deployed'])), None)
    m['上场人数曲线'] = [len(r['deployed']) for r in rows]
    levels = [r['level'] for r in rows if r['level'] is not None]
    m['等级曲线'] = levels
    m['等级爬升'] = (max(levels) - min(levels)) if levels else None
    m['等级末值'] = levels[-1] if levels else None
    # 双口径并列(2026-09-08「校准后首跑」找问题批 F3②):快照口径保留
    # (与等级曲线/爬升同源),帧内升级后终级单列,口径与边界见
    # true_end_level docstring
    m['等级末值·帧内升级后'] = true_end_level(rows[-1]) if rows else None
    # 装备覆盖:穿戴件数/(3×上场人数) 逐轮,末值+均值
    cov = [round(sum(len(d.get('equips') or []) for d in r['deployed'])
                 / max(3 * len(r['deployed']), 1), 2) for r in rows]
    m['装备覆盖末值'] = cov[-1] if cov else None
    m['装备覆盖均值'] = round(statistics.mean(cov), 2) if cov else None
    first_ok = next((i for i, r in enumerate(rows) if r['form_ok']), None)
    m['成型后退档轮数'] = sum(1 for r in rows[first_ok:] if not r['form_ok']) if first_ok is not None else 0
    # F 达标臂发射面(sim = 行内 launch 键;档案 = StartBattle 行动):
    # 成功率 sim 恒 1(发射核必然执行,建模声明见 engine_p1);
    # victim 缺失占比 = 生产计数键 deploy_swap_no_victim 同口径三元联合
    # (板满 ∧ bench core 待上 ∧ 缺合格 victim,cw_loop 发射路径 G1 准入
    # 显影同键)。裸 victim_missing 会误显影:板不满时三元③恒真但生产
    # 不计数。victim 观测缺席(档案行/准入异常吞 None)→ None 不误报 0。
    launches = [r['launch'] for r in rows if r.get('launch')]
    m['发射次数'] = len(launches)
    m['发射成功率'] = (round(sum(1 for L in launches if L.get('ok')) / len(launches), 2)
                    if launches else None)
    _vic_seen = any(L.get('victim') for L in launches)
    m['发射victim缺失占比'] = (round(sum(1 for L in launches if _g1_no_victim(L))
                                 / len(launches), 2)
                           if launches and _vic_seen else None)
    m['首发轮'] = next((r['round'] for r in rows if r.get('launch')), None)
    # H 采购面三观察(sim 行内 obs 键,engine_p1「采购面三观察计数」块建模;
    # 档案行 obs 恒空 → 0/None,不误报)。观察面只计数不定谳——
    # 「超容→买冻结 / 刷新零用 / 冷启动零买」三形态病灶判定归第 3 步复盘。
    _obs = [r.get('obs') or {} for r in rows]
    m['超容帧数'] = sum(int(o.get('overcap_frames') or 0) for o in _obs)
    _run = _best_run = 0
    for o in _obs:
        _run = _run + 1 if (o.get('overcap_frames') or 0) else 0
        _best_run = max(_best_run, _run)
    m['超容最长连续轮'] = _best_run
    m['超容峰值|B|'] = max((int(o.get('locked_b') or 0) for o in _obs),
                           default=0)
    _avail = sum(int(o.get('refresh_avail_frames') or 0) for o in _obs)
    _refs = sum(int(o.get('refreshes') or 0) for o in _obs)
    m['刷新可得帧'] = _avail
    m['刷新触发率'] = (round(_refs / _avail, 2) if _avail else None)
    _cold = [r for r in rows if r['plane'] == 1 and r['round'] <= 4]
    m['冷启动买次数'] = sum(n_act(r['acts'], 'BuyCard') for r in _cold)
    m['冷启动金花费'] = sum(act_cost(r['acts']) for r in _cold)
    # J 冷启动金轨迹(观测面):P1 r1-r4 逐轮**轮末金**
    # (decisions 行 gold = 该轮结算后值;形态口径 = sim 找问题报告
    # 的空板滞留轨迹——开局轮金逐轮爬升且零买入)。
    # 分布聚合在 report 侧(逐轮中位|p90),这里只取每局轨迹原值。
    m['冷启动金轨迹'] = [
        next((r['gold'] for r in rows
              if r['plane'] == 1 and r['round'] == rr), None)
        for rr in (1, 2, 3, 4)]
    # I 必花域观测三键(20 号稿 §6;sim 行内 obs 键,engine_p1 建模;
    # 档案行 obs 恒空 → 0/空,不误报)。观察面只计数不定谳——零消费帧
    # 判读看归因(物理残量白名单 §3.2 带分键)。
    m['必花域帧数'] = sum(int(o.get('must_spend_zone_frames') or 0)
                          for o in _obs)
    m['必花域零消费帧'] = sum(int(o.get('must_spend_zero_consume') or 0)
                              for o in _obs)
    _ms_layer: dict[str, int] = {}
    for o in _obs:
        for k, v in (o.get('must_spend_layer_hit') or {}).items():
            _ms_layer[k] = _ms_layer.get(k, 0) + int(v or 0)
    m['必花域层命中'] = _ms_layer
    # K 刷新触发源分键 + cw4 计数器族(观测面;
    # sim 行内 obs 键,engine_p1 建模;档案行 obs 恒空 → 空,不误报)。
    # 观察面只计数不定谳——fenced 子键占比按发射位预注册裁决协议
    # 裁决(协议单一源 = mandate_v1/shop 出口③ fenced 拆键处注释),
    # theta 成因分桶只述现象不归因。
    m['_obs'] = _obs
    _src: dict[str, int] = {}
    _cts: dict[str, int] = {}
    for o in _obs:
        for k, v in (o.get('refresh_trigger') or {}).items():
            _src[k] = _src.get(k, 0) + int(v or 0)
        for k, v in (o.get('cw4_counters') or {}).items():
            _cts[k] = _cts.get(k, 0) + int(v or 0)
    m['刷新触发源'] = _src
    m['cw4计数器增量'] = _cts
    # L 位面/锁线辖域披露(L2 不对称归因定谳配套,零语义只披露):
    # planes/plane_list 批级聚合在 report 侧,这里只备逐局量;锁线布尔
    # 单一源 = v3_intention.locked_comp 非空,档案行 None → 无数据不误报。
    m['锁线帧'] = (sum(1 for r in rows if r.get('locked'))
                   if any(r.get('locked') is not None for r in rows) else None)
    # M 锁线断头观测面(锁线断头 P2 定向通道设计稿 §6;纯观测件只披露
    # 不定谳)。逐局按位面轮数/锁线帧——批级锁定率(locked_frames/总轮数,
    # 按位面分列)在 report 侧聚合;42 跳对照警示:有锁对照批 hp 中位反而
    # 0.0,锁定率与结局无单调关系,只承归因(跨批摆动可见性),禁读作
    # 越高越好、禁作优化目标。档案行 locked=None → 无数据,不误报 0。
    _pl: dict[int, dict[str, int]] = {}
    for r in rows:
        b = _pl.setdefault(r['plane'], {'frames': 0, 'locked': 0})
        b['frames'] += 1
        if r.get('locked'):
            b['locked'] += 1
    m['位面锁定'] = ({p: (b['locked'], b['frames'])
                     for p, b in sorted(_pl.items())}
                    if any(r.get('locked') is not None for r in rows) else None)
    # G4 r288 复发门·部署通道(ADR-0564 §6 预注册 roster-diff 口径;
    # 挂账批落工具侧):相邻两轮 roster(state.deployed/bench 逐件
    # char_id 集合)做差,差集中消失名 ∈ 仙舟全羁绊件 = 离场事件。
    # 语境筛选 = 先行行 locked_comp 可解析 ∧ form_tiers['列车同行'] >
    # 门封顶档(单一源直调,禁脚本内复制档值口径)。语境行取差分对
    # 先行行:decisions 行 state 为决策时点快照,离场动作发生在该行
    # 决策帧、显影在次行。通道合并计(离场即计的门语义),SellBench
    # 行有顶层 name 可作通道分键;率 = 事件/语境轮(归一化读数)。
    # 档案行无 locked_comp → None 不误报 0。
    m['g4语境轮数'] = m['g4仙舟离场事件'] = None
    m['g4离场事件率'] = m['g4离场通道'] = None
    _g4reg = _g4_registry()
    if _g4reg is not None and any(
            r.get('locked_comp') is not None for r in rows):
        _ctx = _ev = 0
        _chan: dict[str, int] = {}
        for _a, _b in zip(rows, rows[1:], strict=False):
            _lc = _a.get('locked_comp')
            if not _lc or not _g4reg['conflict'](_lc):
                continue
            _ctx += 1
            # 通道分键读顶层 name = 真实账本转录单一形态(engine_p1
            # SellBench 转录行 = {'__type__','bench_idx','name',
            # 'income','sell_reason'},无 card 键)。边界声明:
            # SellDeployed 转录行({'__type__','reason','result',…})
            # 无件名字段 → 该分键结构性恒空,经 SellDeployed 的离场
            # 一律落 unattributed(判读注记,非缺陷;转录行加名字段
            # 则本分键自动激活)。
            _acts = _a.get('acts') or []
            _sb = {a.get('name') for a in _acts
                   if a.get('__type__') == 'SellBench' and a.get('name')}
            _sd = {a.get('name') for a in _acts
                   if a.get('__type__') == 'SellDeployed' and a.get('name')}
            for _name in roster_cids(_a) - roster_cids(_b):
                if not _name or _name not in _g4reg['xz_all']:
                    continue
                _ev += 1
                _ck = ('sell_bench' if _name in _sb else
                       'sell_deployed' if _name in _sd else 'unattributed')
                _chan[_ck] = _chan.get(_ck, 0) + 1
        m['g4语境轮数'] = _ctx
        m['g4仙舟离场事件'] = _ev
        m['g4离场事件率'] = round(_ev / _ctx, 2) if _ctx else None
        m['g4离场通道'] = _chan
    m['l2统一触发帧'] = _cts.get('must_spend_l2_trigger', 0)
    m['l2_rest_capacity拒'] = _cts.get('fuel_filler_stall_fenced_l2_rest_capacity', 0)
    # D 战斗过程
    lo, wo = [], []
    for r in rows:
        if r['node_type'] not in BATTLE_SKIP and r['form'] is not None:
            (lo if (r['hp_delta'] or 0) < 0 else wo).append(r['form'])
    m['最大连败'] = 0
    streak = 0
    for loss in losses:
        streak = streak + 1 if loss else 0
        m['最大连败'] = max(m['最大连败'], streak)
    m['败场形态中位'] = round(statistics.median(lo), 2) if lo else None
    m['胜场形态中位'] = round(statistics.median(wo), 2) if wo else None
    m['败场数'] = sum(losses)
    # F 供给利用(商店侧;补给选项相关率挂档案二期字段缺口)
    shops = []
    for r in rows:
        cards = [c for w in (r.get('shop_waves') or []) for c in (w or [])]
        shops.append((r['factions'], cards, r['acts']))
    m['_shops'] = shops
    m['终态'] = {'plane': rows[-1]['plane'], 'hp': rows[-1]['hp']} if rows else None
    return m


def supply_util(shops: list) -> float | None:
    """相关供给吃掉率:店内与板面阵营相关的牌中,被买入的占比(按轮聚合)。"""
    rel = bought = 0
    for facs, cards, acts in shops:
        if facs is None:
            continue  # 无观测轮不入分母(与 C 族羁绊分诊同口径)
        bf = set(facs)
        rel_names = {c.get('name') for c in cards if c.get('faction') in bf}
        if rel_names:
            rel += 1
            buys = {a['card']['name'] for a in acts
                    if a.get('__type__') == 'BuyCard' and a.get('card')}
            if rel_names & buys:
                bought += 1
    return round(bought / rel, 2) if rel else None


WORST_METRICS = [  # (指标键, 方向):max=值大更差 / min=值小更差
    ('危局空转轮数', 'max'), ('空转轮占比', 'max'), ('停滞最长轮数', 'max'),
    ('花费率', 'min'), ('装备覆盖均值', 'min'), ('等级爬升', 'min'),
    ('超容最长连续轮', 'max'),
]


def report(rows_by_game: dict[str, dict], title: str) -> None:
    print(f'\n== 批统计面 | {title} | 局数 {len(rows_by_game)} ==')
    ms = {rid: analyze_game(g) for rid, g in rows_by_game.items()}

    def agg(key: str):
        vals = [m[key] for m in ms.values() if isinstance(m.get(key), (int, float))]
        return (round(statistics.median(vals), 2), pct(vals, 0.9)) if vals else None

    print('\n-- A/B 资源转化与行动配比(中位 | p90) --')
    for k in ('花费率', '空转轮占比', '危局空转轮数'):
        a = agg(k)
        print(f'  {k}: {a[0]} | {a[1]}' if a else f'  {k}: 无数据')
    print('  行动配比(中位):', {k: int(statistics.median([m['行动配比'][k] for m in ms.values()]))
                             for k in ('BuyCard', 'LevelUp', 'RefreshShop', 'SellBench')} if ms else {})
    print('\n-- C 阵容成型(含等级/装备) --')
    for k in ('末轮成型度', '停滞最长轮数', '首个2★轮', '等级末值',
              '等级末值·帧内升级后', '等级爬升',
              '装备覆盖均值', '装备覆盖末值', '成型后退档轮数'):
        a = agg(k)
        print(f'  {k}: {a[0]} | {a[1]}' if a else f'  {k}: 无数据')
    print('  注: 等级末值双口径——「等级末值」=决策帧快照(末帧 LevelUp 升级'
          '不计入);「·帧内升级后」=快照+末轮 LevelUp 动作逐击结算(只计'
          '升级动作 XP,BuyCard 同源 XP 未计入=低估下界)')
    # 羁绊达成率分诊(2026-09-08「校准后首跑」找问题批 F3①):分母=有
    # board_factions 观测的局,无观测局剔除并单独披露——0% 只属于
    # 「有观测全灭」,无数据局不进分母(混同会把档案伪影当行为信号)
    for fac in ('仙舟3', '持续伤害2', '列车同行2'):
        key = f'{fac}达成轮'
        seen_ms = [mm for mm in ms.values() if mm.get('_factions_seen')]
        if not seen_ms:
            print(f'  {key}: 无数据(全批无羁绊面板观测,达成率不适用)')
            continue
        vals = [mm[key] for mm in seen_ms if mm.get(key) is not None]
        _miss = len(ms) - len(seen_ms)
        _den = (f'分母=有观测 {len(seen_ms)}/{len(ms)} 局' if _miss
                else f'分母={len(seen_ms)} 局')
        print(f'  {key}: 达成率 {len(vals) / len(seen_ms):.0%}({_den})'
              f' | 中位轮 {int(statistics.median(vals)) if vals else None}')
    print('\n-- D 战斗过程 --')
    for k in ('败场数', '最大连败', '败场形态中位', '胜场形态中位'):
        a = agg(k)
        print(f'  {k}: {a[0]} | {a[1]}' if a else f'  {k}: 无数据')
    su = [supply_util(m.pop('_shops')) for m in ms.values()]
    su = [v for v in su if v is not None]
    print('\n-- E 供给利用 --')
    print(f'  相关供给吃掉率(中位 | p10 低尾): '
          f'{statistics.median(su):.2f} | {pct(su, 0.1):.2f}' if su else '  无数据')
    print('\n-- F 达标臂发射面(sim launch 键 / 档案 StartBattle;成功率 sim 恒真值面;'
          ' victim 缺失占比 = 生产 deploy_swap_no_victim 同口径三元联合) --')
    for k in ('发射次数', '发射成功率', '发射victim缺失占比'):
        a = agg(k)
        print(f'  {k}: {a[0]} | {a[1]}' if a else f'  {k}: 无数据')
    fr = [m['首发轮'] for m in ms.values() if m.get('首发轮') is not None]
    print(f'  首发轮: 达成率 {len(fr) / max(len(ms), 1):.0%}'
          f' | 中位轮 {int(statistics.median(fr)) if fr else None}')
    print('\n-- G 终态 --')
    hps = [m['终态']['hp'] for m in ms.values() if m.get('终态') and m['终态']['hp'] is not None]
    print(f'  终局 hp 中位: {statistics.median(hps) if hps else None}')
    print('\n-- H 采购面三观察(sim obs 键;观察面只计数不定谳) --')
    for k in ('超容帧数', '超容最长连续轮', '刷新可得帧', '冷启动买次数', '冷启动金花费'):
        a = agg(k)
        print(f'  {k}: {a[0]} | {a[1]}' if a else f'  {k}: 无数据')
    rt = [m['刷新触发率'] for m in ms.values() if m.get('刷新触发率') is not None]
    if rt:
        print(f'  刷新触发率(实刷/可得帧,中位): {statistics.median(rt):.2f}')
    else:
        print('  刷新触发率: 无可得帧(全批零可得或非 sim 数据源)')
    over_games = [rid for rid, m in ms.items() if m.get('超容帧数')]
    print(f'  超容局占比: {len(over_games) / max(len(ms), 1):.0%}')
    cold0 = [rid for rid, m in ms.items()
             if m.get('冷启动买次数') == 0 and m.get('冷启动金花费') is not None]
    print(f'  冷启动零买局占比: {len(cold0) / max(len(ms), 1):.0%}')
    print('\n-- I 必花域观测三键(20 号稿 §6;零消费帧判读看归因) --')
    for k in ('必花域帧数', '必花域零消费帧'):
        a = agg(k)
        print(f'  {k}: {a[0]} | {a[1]}' if a else f'  {k}: 无数据')
    _ms_tot: dict[str, int] = {}
    for m in ms.values():
        for k, v in (m.get('必花域层命中') or {}).items():
            _ms_tot[k] = _ms_tot.get(k, 0) + v
    print(f'  层命中(L1/L2/L3): {_ms_tot or "无数据"}')
    _zg = [rid for rid, m in ms.items() if m.get('必花域帧数')]
    print(f'  必花域帧出现局占比: {len(_zg) / max(len(ms), 1):.0%}')
    print('\n-- J 冷启动金轨迹(P1 r1-r4 轮末金;分布 = 逐轮跨局中位 | p90;'
          ' 口径 = decisions 行 gold) --')
    _trajs = [m.get('冷启动金轨迹') or [None] * 4 for m in ms.values()]
    for i, rr in enumerate((1, 2, 3, 4)):
        vals = [t[i] for t in _trajs if isinstance(t[i], (int, float))]
        print(f'  r{rr}: {a[0]} | {a[1]}' if (a := agg_key(vals)) else f'  r{rr}: 无数据')
    print('\n-- K 刷新触发源分键 + cw4 计数器族(sim obs 键;只述现象不归因;'
          ' fenced 子键按 exit3_fence_semantics DESIGN §5-3 预注册协议裁决) --')
    _src_tot: dict[str, int] = {}
    _ct_tot: dict[str, int] = {}
    for m in ms.values():
        for k, v in (m.get('刷新触发源') or {}).items():
            _src_tot[k] = _src_tot.get(k, 0) + v
        for k, v in (m.get('cw4计数器增量') or {}).items():
            _ct_tot[k] = _ct_tot.get(k, 0) + v
    print(f'  刷新触发源实刷合计(源→次): {_src_tot or "无数据"}')
    _ct_show = {k: v for k, v in sorted(_ct_tot.items())
                if k.startswith(('theta_unavailable',
                                 'fuel_filler_stall_fenced'))}
    print(f'  theta/fenced 计数器增量(键→次): {_ct_show or "无数据"}')
    _ct_rest = len(_ct_tot) - len(_ct_show)
    if _ct_rest:
        print(f'  (其余 cw4 计数器键 {_ct_rest} 个不入打印,obs 载全量增量)')
    print('\n-- L 位面/锁线辖域披露(L2 不对称归因定谳配套;零语义只披露) --')
    planes_all = sorted({r['plane'] for rows in rows_by_game.values() for r in rows})
    print(f'  planes: {len(planes_all)} | plane_list: {planes_all}')
    lock_vals = [m['锁线帧'] for m in ms.values() if isinstance(m.get('锁线帧'), int)]
    print(f'  locked_frames 合计: {sum(lock_vals) if lock_vals else "无数据(非 sim 源无锁线布尔)"}')
    # M 锁定率按位面分列(设计稿 §6;只披露不作目标值——42 跳对照警示
    # 见脚本头注记与 analyze_game 同段)。分母=该位面总轮数,分子=locked
    # 帧数,跨局求和后相除(cw_batch_stats 同域口径)。
    _pr: dict[int, list[int]] = {}
    for m_ in ms.values():
        for p, (lk, fr) in (m_.get('位面锁定') or {}).items():
            b = _pr.setdefault(p, [0, 0])
            b[0] += lk
            b[1] += fr
    if _pr:
        print('  锁定率(locked/总轮,按位面): '
              + ' | '.join(f'P{p} {lk}/{fr}={round(lk / fr, 2)}' if fr else f'P{p} 无帧'
                           for p, (lk, fr) in sorted(_pr.items())))
    else:
        print('  锁定率: 无数据(非 sim 源无锁线布尔)')
    # M 锁线断点分键批级汇总(G5/G6/G7/G8 四分键+锁定率帧计数;来自
    # cw4_counters 轮差分,engine_p1 建模)。禁合并为单一「锁线失败」键
    # ——四键与锁定率交叉 = 摆动局「断在哪一门」逐批分解(设计稿 §6)。
    _LP_PREFIXES = ('weakplane_exempt_eval', 'p2_supply_gate_cull',
                    'neardeath_direction_obs', 'p2_handoff_',
                    'promote_candidate_', 'intention_frame_',
                    'intention_locked_frame_')
    _lp_show = {k: v for k, v in sorted(_ct_tot.items())
                if k.startswith(_LP_PREFIXES)}
    print(f'  锁线断点分键(G5-G8+锁定率帧,键→次): {_lp_show or "无数据(本批改动前落的局无键)"}')
    # G4 r288 复发门·部署通道(ADR-0564 §6 判据:事件数「≤ 基线 + 噪声」
    # 为门语义,率 = 事件/语境轮为归一化读数;None = 注册表不可达或
    # 非 sim 源无 locked_comp,不误报 0)
    _g4ev = [m.get('g4仙舟离场事件') for m in ms.values()]
    if all(v is None for v in _g4ev):
        print('  G4 仙舟离场事件: 无数据(注册表不可达或非 sim 源无 locked_comp)')
    else:
        _ev_tot = sum(v or 0 for v in _g4ev)
        _ctx_tot = sum(m.get('g4语境轮数') or 0 for m in ms.values())
        _chan_tot: dict[str, int] = {}
        for m in ms.values():
            for k, v in (m.get('g4离场通道') or {}).items():
                _chan_tot[k] = _chan_tot.get(k, 0) + v
        print(f'  G4 仙舟离场事件(门语义,合计): {_ev_tot}'
              f' | 语境轮合计: {_ctx_tot}'
              f' | 率(事件/语境轮): '
              f'{round(_ev_tot / _ctx_tot, 2) if _ctx_tot else None}'
              f' | 有事件局: {sum(1 for v in _g4ev if v)}')
        print(f'  G4 通道分键: {_chan_tot or "无"}')
    if len(planes_all) == 1:
        print('  注: 单面批(planes=1)——L2 辖域不可达(触发链前置锁线,锁线态'
              '在位面入口才建立,本批锁线帧=0),L2=0 是辖域结果,禁当行为信号')
    _trig_tot = sum(m.get('l2统一触发帧') or 0 for m in ms.values())
    _rest_tot = sum(m.get('l2_rest_capacity拒') or 0 for m in ms.values())
    _l2_emit = sum(int((m.get('必花域层命中') or {}).get('L2') or 0)
                   for m in ms.values())
    # 对拍口径注记:触发面(统一触发面键)与发射面(层命中)分开披露,禁互换
    print(f'  L2 统一触发帧(cw4_counters.must_spend_l2_trigger): {_trig_tot or "无数据"}'
          f' | L2 发射(must_spend_layer_hit.L2): {_l2_emit or "无数据"}')
    print(f'  l2_rest_capacity 拒(fenced 拆键,单列只披露): {_rest_tot or "无数据"}')
    if _rest_tot:
        print('  注(判读面候选登记,非缺口定谳): 「板未满 1-2 格 ∧ 垫件在售 ∧ '
              'L3 不可用」= 结构性残量白名单扩行候选;翻转条件 = 垫件定性改为'
              '「纯经济消费须买」(出口③判读配套,候裁)')
    print('\n-- 表现不好的指标 → 体现最重的局(每指标 2 局;第 3 步挑局复盘的抽样单) --')
    for key, d in WORST_METRICS:
        vals = [(m.get(key), rid) for rid, m in ms.items()
                if isinstance(m.get(key), (int, float))]
        if not vals:
            continue
        vals.sort(key=lambda t: t[0], reverse=(d == 'max'))
        word = '高' if d == 'max' else '低'
        print(f'  {key}({word}为差): '
              + '; '.join(f'{rid.split("_s")[-1]}={v}' for v, rid in vals[:2]))


def main() -> None:
    global SIM_ROOT, MATCHES
    ap = argparse.ArgumentParser()
    ap.add_argument('--sim-batch', default='', help='sim 批次名或 latest')
    ap.add_argument('--recent', type=int, default=0, help='生产档案最近 N 局')
    ap.add_argument('--match', default='', help='生产档案单局 game_id')
    # 档案根参数(覆盖缺省 telemetry 根;离线/另机语料对账用)
    ap.add_argument('--sim-root', default=str(SIM_ROOT),
                    help='sim 批根目录(缺省 .debug/currency_war/telemetry/sim)')
    ap.add_argument('--matches-root', default=str(MATCHES),
                    help='按局档案根(缺省 .debug/currency_war/telemetry/matches)')
    args = ap.parse_args()
    SIM_ROOT = Path(args.sim_root)
    MATCHES = Path(args.matches_root)
    if args.sim_batch:
        name = args.sim_batch
        batch = (sorted(d for d in SIM_ROOT.iterdir() if d.is_dir())[-1]
                 if name == 'latest' else SIM_ROOT / name)
        if not batch.is_dir():
            raise SystemExit(f'批次不存在:{batch}')
        report(_sim_rows(batch), batch.name)
    elif args.match:
        g = _archive_rows(args.match)
        report({g['game_id']: g['rows']}, g['game_id'])
    elif args.recent:
        idx = _load(MATCHES / 'index.jsonl')[-args.recent:]
        groups: dict[str, dict] = {}
        affix_stat: dict[tuple, list] = {}
        for e in idx:
            p = MATCHES / f"match_{e['game_id']}.json"
            if not p.exists():
                continue
            g = _archive_rows(e['game_id'])
            groups[g['game_id']] = g['rows']
            affix_stat.setdefault(tuple(g['affixes']), {'hps': []})['hps'].append(
                g['final_hp'] if g['final_hp'] is not None else 0)
        report(groups, f'生产档案最近 {len(groups)} 局')
        print('\n-- 词缀条件化分组(sim 未建模词条,仅档案;样本小只列不判) --')
        for af, st in sorted(affix_stat.items(), key=lambda kv: -len(kv[1]['hps'])):
            hps = st['hps']
            print(f'  {len(hps)} 局 | 终局hp中位 {statistics.median(hps):.0f} | {"/".join(af) or "(无词缀记录)"}')
    else:
        ap.error('需 --sim-batch / --recent / --match 之一')


if __name__ == '__main__':
    main()
