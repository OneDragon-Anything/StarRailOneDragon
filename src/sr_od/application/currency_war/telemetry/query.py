"""判读查询:jsonl 读取/join/query_* 视图/支出账分类(自 cw_telemetry 拆出,分包期6)。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sr_od.application.currency_war.kernel.cw_state import (
    XP_CLICK_COST_FALLBACK,
)
from sr_od.application.currency_war.telemetry import state as _telstate

# ===== 迁移审计 w103(git 历史) 件1/件2(ADR-0342):策略失活检测 =====
# 病灶实录(迁移审计 w98(git 历史) 两局 run_20260825_003757/011957):崩溃恢复局 decisions
# 全行 strategy_id='' 且零策略动作族(BuyCard/SellBench/CompTransaction/
# LevelUp 除 op 层兜底外),观测层活着(EnsureShopClosed 行照写)、店里
# 明明读到目标件——决策层整局未点火,兜底打满 40min 产出 0 买垃圾局。

_STRATEGY_LIVE_CACHE: dict[tuple[str, float], set[tuple[int, int]]] = {}



def _strategy_live_rounds(run_id: str) -> set[tuple[int, int]]:
    """该 run 中「存在带非空 strategy_id 决策行」的 (plane, round) 集。

    decisions.jsonl 按 mtime 缓存(每个写入窗口只全文扫一次;跨 run 追加
    文件随局数线性增长,逐 round 查询不该每次全扫)。
    """
    path = _telstate.get_recorder().replay_dir / 'decisions.jsonl'
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return set()
    ck = (run_id, mtime)
    if ck in _STRATEGY_LIVE_CACHE:
        return _STRATEGY_LIVE_CACHE[ck]
    live: set[tuple[int, int]] = set()
    for d in read_jsonl(path):
        if d.get('run_id') == run_id and d.get('strategy_id'):
            live.add((int(d.get('plane') or 1), int(d.get('round_num') or 0)))
    # 缓存只留最新 mtime 条目(防长期运行膨胀)
    _STRATEGY_LIVE_CACHE.clear()
    _STRATEGY_LIVE_CACHE[ck] = live
    return live



def strategy_round_live(run_id: str, key: tuple[int, int]) -> bool:
    """(plane, round) 是否有带 strategy_id 的决策行(迁移审计 w103(git 历史) 件1 查询端)。"""
    return key in _strategy_live_rounds(run_id)



def dead_streak_transition(prev_key: tuple[int, int] | None,
                           key: tuple[int, int],
                           streak: int, live: bool) -> int:
    """策略失活连击状态机(迁移审计 w103(git 历史) 件1;纯函数,battle_loop 消费)。

    语义:进入新 round key 时对**上一轮** prev_key 的 live 结果结算——
    本轮的决策行还没写(检查点在备战入口,决策发生在本相位内),查本轮
    恒 False;查上一轮才是完整轮。同 key 重入(过渡帧/重试)不重复计数。
    live=True 复位;False 递增。
    """
    if prev_key is None or prev_key == key:
        return streak
    return 0 if live else streak + 1



def check_strategy_live_streak(all_rows: list[dict],
                               streak_threshold: int = 3) -> list[str]:
    """生产检查项(迁移审计 w103(git 历史) 件2;run_checks_on_replay 消费):策略失活局/失活段。

    判据:该 run 的 (plane, round) 全集中,「无任何带 strategy_id 决策行」
    的连续轮数 ≥ streak_threshold → 违规。迁移审计 w98(git 历史) 两局实录=整局恒空(全程
    57/61 轮),streak=轮数 → 必报;阈值取 3(整局空与 迁移审计 w98(git 历史) 形态远超;
    <3 的孤立空轮多为暂态/接管帧,不报警——非 sim 检查,生产局判栈用,
    与 sim 检查网(cw_sim_checks)分栈:sim 批 strategy 恒在,跑了也是
    恒绿,不进 _BATCH_CHECKS)。
    """
    rounds: dict[tuple[int, int], bool] = {}   # key → live
    for d in all_rows:
        k = (int(d.get('plane') or 1), int(d.get('round_num') or 0))
        rounds[k] = rounds.get(k, False) or bool(d.get('strategy_id'))
    streak = worst = 0
    for k in sorted(rounds):
        if k[0] != 1:
            continue   # P1 先辖(P2/P3 轮次恢复语义不同,语料不足不判)
        if not rounds[k]:
            streak += 1
            worst = max(worst, streak)
        else:
            streak = 0
    if worst >= streak_threshold:
        dead_n = sum(1 for k in rounds if k[0] == 1 and not rounds[k])
        return [f'P1 策略失活连续 {worst} 轮(共 {dead_n} 轮无 '
                f'strategy_id 决策行——W98 恢复兜底局形态,ADR-0342)']
    return []



# ===== 复盘读取(给人肉眼复盘 / 未来 ML)=====

def read_jsonl(path: Path | str) -> list[dict[str, Any]]:
    """读一个 JSONL 文件 → list[dict]。文件不存在 → []。"""
    p = Path(path)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out



def join_decisions_outcomes(replay_dir: Path | str) -> list[dict[str, Any]]:
    """按 (run_id, plane, round_num) join decisions ↔ outcomes → 每回合一条合并记录(复盘/ML 用)。

    decisions 主表,outcomes 左 join(无 outcome 的决策 outcome 字段为 None)。
    ⚖️ r68 review:join 键加 plane —— round_num 是位面内序(1-9),P1r3 与 P2r3 旧键撞行
    (跨位面 outcome 错配);两侧均含 plane 字段,旧记录缺 plane 时 get 返 None 仍一致配对。
    """
    decisions = read_jsonl(Path(replay_dir) / "decisions.jsonl")
    outcomes = read_jsonl(Path(replay_dir) / "outcomes.jsonl")
    out_by_key = {(o["run_id"], o.get("plane"), o["round_num"]): o for o in outcomes}
    joined: list[dict[str, Any]] = []
    for d in decisions:
        key = (d.get("run_id"), d.get("plane"), d.get("round_num"))
        merged = dict(d)
        merged["outcome"] = out_by_key.get(key)
        joined.append(merged)
    return joined



# ===== 复盘查询(query CLI;telemetry 的读出端,r97)=====
# 设计:数据与判读同源 —— 查询视图(逐轮演进/供给对照/异常标记)读的就是本模块落盘的
# JSONL,schema 变更查询同步;新复盘问题 = 新视图/参数,不是新脚本(一次性脚本时代终结)。
# 用法:
#   uv run python -m sr_od.application.currency_war.telemetry.cw_telemetry query [--run ID] [--recent N] [--view rounds|supply|anomalies|tiers|planexec|hp|economy|exogenous|execevents|invest|conflicts|all]

def _load_decisions_rounds(replay_dir: Path, run_id: str) -> dict:
    """该 run 的 decisions 按 (plane,round) 取 actions 最多的一条(plan 真值)。

    r363(审计 P1-8):并列(同 action 数)时取 **ts 最晚**(末帧)——
    旧严格大于让最早的行胜出,轮末 state(买后 board/gold)被首帧
    (空板)代表,收入/执行判读失真。
    """
    best: dict = {}
    for d in read_jsonl(replay_dir / "decisions.jsonl"):
        if run_id and d.get("run_id") != run_id:
            continue
        k = (d.get("plane"), d.get("round_num"))
        n = len(d.get("actions") or [])
        if k not in best or n > len(best[k].get("actions") or []) or (
                n == len(best[k].get("actions") or [])
                and (d.get("ts") or '') > (best[k].get("ts") or '')):
            best[k] = d
    return best



def _list_runs(replay_dir: Path) -> list[str]:
    ids: list[str] = []
    for d in read_jsonl(replay_dir / "outcomes.jsonl"):
        rid = d.get("run_id")
        if rid and (not ids or ids[-1] != rid):
            ids.append(rid)
    return ids



def _release_frame_counts(replay_dir: Path, run_id: str) -> dict:
    """逐 (plane,round) 统计 release 姿态帧数(姿态触发判读的逐帧分布源)。

    契约:dp_posture 恒为 str(判定口径 dp=='release' 的 str 相等),且必须滤
    strategy_id=='decision_v2'——载体帧(strategy_id='')该字段是 str(dict) 形态,
    字符串比较天然不命中,但仍显式滤掉防未来契约漂移。_load_decisions_rounds
    每键只留 actions 最多的一条,统计不了逐帧分布,故独立全帧扫描。
    """
    counts: dict = {}
    for d in read_jsonl(replay_dir / "decisions.jsonl"):
        if run_id and d.get("run_id") != run_id:
            continue
        if (d.get("strategy_id") or "") != "decision_v2":
            continue
        _dp = d.get("dp_posture")
        if isinstance(_dp, str) and _dp == "release":
            k = (d.get("plane"), d.get("round_num"))
            counts[k] = counts.get(k, 0) + 1
    return counts



def query_rounds(replay_dir: Path, run_id: str) -> list[str]:
    """视图:逐轮演进(hp/gold/买/升/D/board;v2 模式/锁线/桥)。

    迁移审计 w306(git 历史) 后补给等无决策节点经由 outcomes 的 synthetic 行并入本视图
    (source 标记可见),判读不再缺「选了什么补给」前后的状态语境。
    """
    best = _load_decisions_rounds(replay_dir, run_id)
    # release 姿态逐帧分布(姿态触发判读;键坐标系与 best 相同)
    _rel = _release_frame_counts(replay_dir, run_id)
    # 仅收「无决策行」的键(如 supply 合成行);有决策的轮以 decisions 为准
    _out_only: dict = {}
    # 迁移审计 w306(git 历史) 显示闭环:全部 outcomes 建 map —— 决策行的 source 也要能打
    # (source 在 outcomes 行,decisions 行没有;合成补给行等无决策轮才有非空 source)
    _out_by_k: dict = {}
    for o in read_jsonl(replay_dir / "outcomes.jsonl"):
        if run_id and o.get("run_id") != run_id:
            continue
        k = (o.get("plane"), o.get("round_num"))
        _out_by_k[k] = o
        if k not in best and k not in _out_only:
            _out_only[k] = o
    lines = []
    for k in sorted(set(best.keys()) | set(_out_only.keys())):
        d = best.get(k)
        if d is None:
            # 无决策节点(如 supply 合成行):展示来源与结算态,判定语义见 source
            o = _out_only[k]
            nt = o.get("node_type") or "?"
            src = o.get("source") or ""
            bb = " ".join(f"{k2}×{v}" for k2, v in (o.get("board_before") or {}).items()) or "(空)"
            gold_s = f" g={o['gold']}" if o.get("gold") is not None else ""
            lines.append(f"  p{k[0]}r{k[1]} [{nt}|{src}]{gold_s} hp={o.get('hp_after')} | {bb}")
            continue
        st = d.get("state") or {}
        acts = d.get("actions") or []
        buys = sum(1 for a in acts if isinstance(a, dict) and a.get("__type__") == "BuyCard")
        lvs = sum(1 for a in acts if isinstance(a, dict) and a.get("__type__") == "LevelUp")
        rfs = sum(1 for a in acts if isinstance(a, dict) and a.get("__type__") == "RefreshShop")
        board = " ".join(f"{k2}×{v}" for k2, v in (st.get("board") or {}).items()) or "(空)"
        # sim 批次:board 恒空 → 显示账本代理维度(深/核;判读不断档)
        _simd = d.get('sim')
        if _simd is not None:
            board = f"(sim 深={_simd.get('depth')} 核={_simd.get('core_count')})"
        act_s = f"买{buys}" + (f"/升{lvs}" if lvs else "") + (f"/D{rfs}" if rfs else "")
        # r226 v2 字段读出(策略 v2 对拍视图;空则省略——default 局全空)
        v2 = d.get("v2_mode") or ""
        lock = d.get("v2_locked_line") or ""
        bridge = d.get("v2_bridge") or ""
        v2_s = f" v2=[{v2}|{lock or '-'}|{bridge or '-'}]" if (v2 or lock or bridge) else ""
        # 迁移审计 w146(git 历史) v3 意向状态直读(锁定时点/锁定目标;None/default 局省略)
        _ist = d.get('v3_intention')
        ist_s = ''
        if isinstance(_ist, dict):
            ist_s = (f" ist=[{_ist.get('phase', '')}"
                     f"|{_ist.get('locked_comp', '') or '-'}]"
                     + ('/降格' if _ist.get('demoted_endgame') else ''))
        # 迁移审计 w114(git 历史)/ADR-0346 相位影子观测(空则省略——旧局/影子代码前全空)
        _ph = d.get("phase") or ""
        _fok = d.get("form_ok")
        _fsc = d.get("form_score")
        ph_s = (f" ph={_ph}" + ("/ok" if _fok else "")
                + (f"/{_fsc:.2f}" if isinstance(_fsc, (int, float)) else "")
                ) if _ph else ""
        # 迁移审计 w119(git 历史)/ADR-0347 授权依据 trace:DP 姿态 tag(空则省略)
        # dp 显示规整:只有 decision_v2 决策帧显示 tag 本身(判定口径
        # dp=='release' 消费的就是这个 str);载体帧(strategy_id='')是
        # str(dict) 形态、08-26 前历史帧是 dict 形态——一律 dp=? 紧凑占位,
        # 不倾倒原始串污染判读视图(实证:载体帧曾打出整段 spend_mode 长串)。
        _dpp = d.get("dp_posture") or ""
        _sid = d.get("strategy_id") or ""
        if _sid == "decision_v2" and isinstance(_dpp, str) and _dpp:
            dpp_s = f" dp={_dpp}"
        elif _dpp:
            dpp_s = " dp=?"
        else:
            dpp_s = ""
        # ADR-0348 ↺:扑满节点识别标记
        if d.get("piggy_reward"):
            dpp_s += " P=扑满"
        # r358c(用户定调「复盘要全面」):xp 进度/站位(前排数)入 rounds 主视图
        # ——升级节奏与站位分流的直读维度(旧视图不可见,须直查 jsonl)。
        # ⚠️ 判读语义(迁移审计 w229(git 历史) 分型,勿再误判为「前排未满编」缺陷):
        # - 前后分拆按 position_pref(角色命途定位)计数,deploy 按它路由落排
        #   (ADR-0392 deployed_place);「前排固定 4」是槽位可用性不是放置目标;
        # - 「满编」判据 = deployed 总数 = cap(=level),**不是前排占满 4**;
        #   队伍含 N 个 back 定位角色时,位=(cap-N)前/N后 且前排留空槽 = 合法布局
        #   (实证:run 25/28「位=3前/2后」与 deploy_bench CV 实读逐轮吻合,总数恒=cap)。
        _xp = st.get("xp_progress")
        xp_s = f" xp={_xp[0]}/{_xp[1]}" if _xp else ""
        _dep = st.get("deployed") or []
        _front = sum(1 for c in _dep if c.get("position_pref") == "front")
        pos_s = f" 位={_front}前/{len(_dep) - _front}后" if _dep else ""
        # 迁移审计 w306(git 历史):节点类型 + 行来源直读(单看数字不知道是什么节点/这行哪来的
        # ——node_type 取 state(战斗后观测),source 取 outcomes 同键行
        # (''=结算真值行,'synthetic_supply'/'recovered' 特例),合成显示 [src|nt])
        _nt = st.get("node_type") or ""
        _src = (_out_by_k.get(k) or {}).get("source") or ""
        _tag = "|".join(x for x in (_src, _nt) if x)
        nt_s = f" [{_tag}]" if _tag else ""
        # hp 可信位显影:hp_readable 在帧顶层,state.hp_trusted 在 state
        # 子字典(GameState.hp_trusted,cw_observation 写入快照;顶层没有该键,
        # 直读顶层恒 None)。任一不可信 → hp 后缀 `?`(迁移审计 w318(git 历史) economy 视图惯例),
        # 防「100 兜底值被判读为满血」(实证:run_20260828_103147 p2r4 帧
        # hp=4→100×5→4 且 hp_readable 恒 False)。sim 账本行 hp 是模拟真值
        # 且不带可信位字段,豁免不标。
        if d.get("sim") is None:
            _hpr = d.get("hp_readable")
            _hpt = st.get("hp_trusted")
            if _hpr is False or _hpt is not True:
                _hp_show = f"{d.get('hp')}?"
            else:
                _hp_show = f"{d.get('hp')}"
        else:
            _hp_show = f"{d.get('hp')}"
        # release 帧数列:逐帧 dp 标签分布(单帧/末帧判读已两次产生
        # 伪影);0 帧省略,统计口径见 _release_frame_counts
        _rln = _rel.get(k) or 0
        rl_s = f" rl={_rln}" if _rln else ""
        # level 保真位显影(对齐 hp 可信位 `?` 惯例):level_readable=False =
        # 纯 _expected_level 启发式兜底帧(OCR 与 XP 双失读),非真读;旧档案
        # 无该键(None)不加缀 = 按现有判读处理。
        _lv_show = f"{st.get('level')}?" if d.get("level_readable") is False \
            else f"{st.get('level')}"
        lines.append(f"  p{k[0]}r{k[1]}{nt_s} hp={_hp_show} g={d.get('gold')} lv={_lv_show}"
                      f"{xp_s} {act_s:<10} | {board}{pos_s}{v2_s}{ist_s}{ph_s}{dpp_s}{rl_s}")
    return lines



def query_supply(replay_dir: Path, run_id: str) -> list[str]:
    """视图:供给对照(shop_snapshots 全波牌面 vs 买了什么;配方件出现即标 ★)。"""
    snaps: dict = {}
    for s in read_jsonl(replay_dir / "shop_snapshots.jsonl"):
        if run_id and s.get("run_id") != run_id:
            continue
        snaps.setdefault((s.get("plane"), s.get("round_num")), []).append(s)
    best = _load_decisions_rounds(replay_dir, run_id)
    # 迁移审计 w306(git 历史) 显示闭环:同键 outcome 的 node_type/source 打进每轮头行
    # (synthetic 补给行无 decisions,靠 outcomes 兜出节点语境)
    _out_by_k: dict = {}
    for o in read_jsonl(replay_dir / "outcomes.jsonl"):
        if run_id and o.get("run_id") != run_id:
            continue
        _out_by_k[(o.get("plane"), o.get("round_num"))] = o
    # 配方框架(knowledge/cw_line_facts;import 失败退空 = 全牌不标)
    try:
        from sr_od.application.currency_war.knowledge.cw_line_facts import (
            TRANSITION_PACK,
        )
        recipe_names = set(TRANSITION_PACK.keys())
    except Exception:   # noqa: BLE001
        recipe_names = set()
    lines = []
    for k in sorted(set(list(snaps.keys()) + list(best.keys()))):
        d = best.get(k)
        acts = (d.get("actions") or []) if d else []
        buys = [a.get("card", {}).get("name") for a in acts
                if isinstance(a, dict) and a.get("__type__") == "BuyCard"]
        _o = _out_by_k.get(k) or {}
        _st_d = (d.get("state") or {}) if d else {}
        _tag = "|".join(x for x in (_o.get("source") or "",
                                    _st_d.get("node_type")
                                    or _o.get("node_type") or "") if x)
        tag_s = f" [{_tag}]" if _tag else ""
        lines.append(f"  p{k[0]}r{k[1]}{tag_s} tgt={(d or {}).get('target_comp', '?')}")
        for s in snaps.get(k, []):
            cards = [(c.get('name'), c.get('faction'), c.get('cost')) for c in (s.get('shop') or [])]
            star = [f"★{n}({f})" for n, f, _c in cards
                    if n in recipe_names or (f in ('仙舟', '列车同行') and n)]
            # 升星预览✦(ADR-0416):>0 才显影,0/缺字段(旧数据)不显
            previews = [f"✦{c.get('name')}x{c.get('merge_preview')}"
                        for c in (s.get('shop') or []) if c.get('merge_preview')]
            mark = ('  ' + ' '.join(star + previews)) if (star or previews) else ''
            lines.append(f"    [{s.get('event')}] g={s.get('gold')} {cards}{mark}")
        if not snaps.get(k):
            lines.append("    (无 shop 快照——旧数据只记进店帧,refresh 波丢失)")
        lines.append(f"    买了: {buys}")
    return lines



ABN_GOLD: int = 40     # 金 ≥ 此且该轮 0 买 0 升 = 钱变不成板

ABN_DROP: int = 25     # 单轮掉血 ≥ 此 = 战力断层

# outcomes.hp_confidence 的可信门(档案真值链 match_archive._hp_entry 同一判据,
# 放本模块因 match_archive 已 import query,反向 import 会成环)。
# 语义:结算屏 OCR 解析失败行 hp_confidence=0.0,hp_after 落 0 兜底;补给合成行
# hp 是快照非屏面真值——两类都是 miss 兜底伪值,g_20260830_150029 实证它们
# 触发假「战力断层」(rounds 链真值仅 -8/-24)。掉血真值单一源 = rounds 链,
# OCR 值仅辅助,故低于此门的行不入异常判定链。缺字段 = 旧数据(schema 默认
# 1.0)或 sim 账本行(模拟真值,无 conf 字段),按可信处理。
HP_CONF_TRUSTED: float = 0.9


def _outcome_hp_trusted(outcome: dict[str, Any]) -> bool:
    """outcome 行的 hp 是否可信(见 HP_CONF_TRUSTED 的判据与边界声明)。"""
    conf = outcome.get("hp_confidence")
    return conf is None or (isinstance(conf, (int, float))
                            and conf >= HP_CONF_TRUSTED)



def query_anomalies(replay_dir: Path, run_id: str) -> list[str]:
    """视图:异常标记(钱变不成板/战力断层/plan_error)。

    迁移审计 w317(git 历史)(G4 读端欠账):各条目补所在轮 node_type;断层条目另补
    enemy_affixes(迁移审计 w244(git 历史) 词缀分层)——断层归因第二分法(敌方强度
    异常)不用再开新窗口直查 jsonl。
    """
    best = _load_decisions_rounds(replay_dir, run_id)
    abn: list[str] = []
    for k in sorted(best):
        d = best[k]
        acts = d.get("actions") or []
        buys = sum(1 for a in acts if isinstance(a, dict) and a.get("__type__") == "BuyCard")
        lvs = sum(1 for a in acts if isinstance(a, dict) and a.get("__type__") == "LevelUp")
        # 迁移审计 w317(git 历史):节点类型进标签(与 rounds 视图 [tag] 风格一致)
        _nt = (d.get("state") or {}).get("node_type") or ""
        _tag = f"[{_nt}] " if _nt else ""
        if (d.get("gold") or 0) >= ABN_GOLD and buys == 0 and lvs == 0:
            abn.append(f"p{k[0]}r{k[1]} {_tag}金{d.get('gold')} 0买0升(钱变不成板)")
        if (d.get("eval_breakdown") or {}).get("plan_error"):
            abn.append(f"p{k[0]}r{k[1]} {_tag}plan_error(决策崩溃,见 log)")
    prev_hp = None
    for o in read_jsonl(replay_dir / "outcomes.jsonl"):
        if run_id and o.get("run_id") != run_id:
            continue
        hp = o.get("hp_after")
        # OCR miss 伪值过滤:不可信行不产生断层条目,也不推进 prev_hp
        # (推进了会把后续真值轮的掉血算错,实证同上)
        if not _outcome_hp_trusted(o):
            continue
        if prev_hp is not None and hp is not None and prev_hp - hp >= ABN_DROP:
            # 迁移审计 w317(git 历史):断层行带节点类型与词缀(非空才显示;词缀=开局简报
            # 位面级快照,语义见 OutcomeRecord.enemy_affixes)
            _nt = o.get("node_type") or ""
            _tag = f"[{_nt}] " if _nt else ""
            _ax = " ".join(o.get("enemy_affixes") or [])
            _ax_s = f" 词缀={_ax}" if _ax else ""
            abn.append(f"p{o.get('plane')}r{o.get('round_num')} {_tag}"
                       f"单轮掉血 {prev_hp}→{hp}(战力断层){_ax_s}")
        if hp is not None:
            prev_hp = hp
    return abn



def query_hp(replay_dir: Path, run_id: str) -> list[str]:
    """视图(r339):掉血分解——逐轮 (node, delta, 板深, 方向态)。

    与 sim hp_events 同构(对拍 sim 校准模型的直接读出端);
    board_before/bench_count 为 r339 起记录(旧数据缺省显示 -)。
    迁移审计 w317(git 历史)(G4 读端欠账):行尾补 killed(1=击杀/0=未杀/?=旧数据或
    未采到)与 boss_names(迁移审计 w244(git 历史) boss 分层,非空才显示)——「这轮输
    给谁」的断层归因不再需要另开窗口直查 jsonl。

    hp 可信位显示层过滤(与 query_anomalies 同门 HP_CONF_TRUSTED 判据,
    `_outcome_hp_trusted` 单一源):不可信行(OCR miss 兜底 hp=0 / 合成快照行)
    **保留显示但行尾标 `伪值`**,且不推进 prev_hp 链——显示层语义「标注优于
    删除」(行留证据可见,判读侧自辨),链侧语义与 anomalies 一致(伪值入链
    会让后续真值轮 Δ 算错,g_20260830_150029 实证 Δ=+67 荒谬行)。缺
    hp_confidence 字段(旧数据/sim 账本行)按可信,不误标。
    """
    lines = []
    prev_hp: int | None = None
    for o in read_jsonl(replay_dir / "outcomes.jsonl"):
        if run_id and o.get("run_id") != run_id:
            continue
        hp = o.get("hp_after")
        delta = (prev_hp - hp) if (prev_hp is not None and hp is not None) else None
        # 伪值行的 Δ 无意义(链不经过它),Δ 置 -;真值/可信行的 Δ 才是账
        if not _outcome_hp_trusted(o):
            delta = None
        _b = o.get("board_before") or {}
        depth = sum(_b.values())
        # sim 批次:board 恒空(设计如此)→ 回退账本深度(sim.depth
        # = _deployable_depth 口径,与生产 board 语义同源 r343)
        _sim = o.get("sim") or {}
        # sim 行板深带 *(审查#4:sim depth=可部署潜力/生产=已部署
        # 事实,跨 run 并排判读需可辨)
        depth_s = str(depth) if _b else (
            f"{_sim.get('depth', '-')}*" if _sim else '-')
        bench = o.get("bench_count")
        delta_s = f'{-delta:+d}' if delta is not None else '-'
        # 迁移审计 w317(git 历史):胜负(killed,None=未知)与 boss 身份(非空才显示;
        # None 元素=该位面徽章态采不到,保位过滤语义见 OutcomeRecord)
        _killed = o.get("killed")
        k_s = '1' if _killed else ('0' if _killed is False else '?')
        _bosses = [b for b in (o.get("boss_names") or []) if b]
        boss_s = f" boss=[{'|'.join(_bosses)}]" if _bosses else ""
        # 伪值标注(显示层过滤):不可信行保留行留证据,行尾标「伪值」
        fake_s = "" if _outcome_hp_trusted(o) else " 伪值"
        lines.append(
            f"  p{o.get('plane')}r{o.get('round_num')} {o.get('node_type') or '?':8s}"
            f" hp={hp} Δ={delta_s}"
            f" 板深={depth_s} bench={bench if bench is not None else '-'}"
            f" killed={k_s}{boss_s}{fake_s}")
        # 链推进同 anomalies 门:伪值不推进 prev_hp(推进即污染后续真值 Δ)
        if hp is not None and _outcome_hp_trusted(o):
            prev_hp = hp
    return lines



def query_economy(replay_dir: Path, run_id: str) -> list[str]:
    """视图(r339):金轨迹/滞留——逐轮 (gold, 升级费, 花出, 收入, 卖回)。

    「金花不出去」异常的量化端:滞留轮(金≥20 且花=0)标 ⚠。
    升级花费逐轮读 decisions.state.level_up_cost(cw_observation.
    read_level_up_cost 的 OCR 真值);该轮未读到(None,旧数据或缺省)
    时按 XP_CLICK_COST_FALLBACK 兜底常量计入并在 `luc=` 后标 `?`
    (成本项可能有偏,判读可辨)。升级成本与 gold 并列显示——
    「这轮升得起吗」直接对照,不再需要另开窗口查 decisions.state。
    列名 `luc=`(level-up cost):曾作 `lv=`——与 rounds 视图
    `lv=等级` 同名不同义,是「复盘把升级花费恒 4 的兜底显示误读成
    等级恒 4」的视图侧根因候选之一,改名根治歧义。
    卖回格(迁移审计 w323(git 历史),遥测审计 G2):优先聚合 exogenous kind='sell_income'
    行的实收 gold_delta(shop.py 执行点落盘);该轮有行但 delta=None
    (OCR miss)计 0 并标 `?`;无行(旧数据/sim 局)回退 decisions
    actions 的 SellBench.income 口径(与 sim 账本一致,不回归)。
    """
    best = _load_decisions_rounds(replay_dir, run_id)
    # 迁移审计 w323(git 历史):执行点实收卖回聚合(键 = (plane, round),与 decisions 主键同坐标系)
    sell_obs: dict[tuple, int] = {}
    sell_obs_unknown: set[tuple] = set()
    for r in read_jsonl(replay_dir / "exogenous.jsonl"):
        if (r.get("kind") or "") != "sell_income":
            continue
        if run_id and r.get("run_id") != run_id:
            continue
        k = ((r.get("state_snapshot") or {}).get("plane"),
             r.get("round_num"))
        d = (r.get("choice") or {}).get("gold_delta")
        if d is None:
            sell_obs_unknown.add(k)
        else:
            sell_obs[k] = sell_obs.get(k, 0) + int(d)
    lines = []
    prev_gold: int | None = None
    for k in sorted(best):
        d = best[k]
        acts = d.get("actions") or []
        spend = sum((a.get("card", {}).get("cost") or 0)
                    for a in acts if isinstance(a, dict)
                    and a.get("__type__") == "BuyCard")
        luc = (d.get("state") or {}).get("level_up_cost")
        luc_s = f"{luc}" if luc else f"{XP_CLICK_COST_FALLBACK}?"
        spend += (luc or XP_CLICK_COST_FALLBACK) * sum(
            1 for a in acts
            if isinstance(a, dict) and a.get("__type__") == "LevelUp")
        spend += sum((a.get("cost") or 0) for a in acts
                     if isinstance(a, dict) and a.get("__type__") == "RefreshShop")
        # 卖牌回金(迁移审计 w323(git 历史) 前口径⑤:漏计——含卖轮的 income 系统性偏负)。
        # 优先级:执行点实收(exogenous)> actions 计划值(sim 行;生产行
        # serialize_action 的 SellBench 不带 income,恒 0 不干扰)。
        sell_act = sum((a.get("income") or 0) for a in acts
                       if isinstance(a, dict) and a.get("__type__") == "SellBench")
        unknown = k in sell_obs_unknown
        sell_in = sell_obs.get(k, sell_act if k not in sell_obs_unknown else 0)
        g = d.get("gold") or 0
        income = ((g - prev_gold + spend - sell_in)
                  if prev_gold is not None else None)
        flag = ' ⚠滞留' if (g >= 20 and spend == 0) else ''
        sell_s = (f' 卖+{sell_in}' + ('?' if unknown else '')) \
            if (sell_in or unknown) else ''
        lines.append(
            f"  p{k[0]}r{k[1]} g={g} luc={luc_s}"
            f" 花={spend}{sell_s} 收={'-' if income is None else income}{flag}")
        prev_gold = g
    return lines



def query_tiers(replay_dir: Path, run_id: str) -> list[str]:
    """视图:羁绊激活档逐轮 + 角色构成(星级) + 装备分配(r358 三维同屏;
    配方成型判读的硬指标;恒 0 = 配方没真正上场)。"""
    from sr_od.application.currency_war.data.cw_factions import FACTIONS
    best = _load_decisions_rounds(replay_dir, run_id)
    lines: list[str] = []
    prev_tgt = None
    for k in sorted(best):
        d = best[k]
        # 换线标记(审查#6:核= 随 tgt 切换定义,跨线时间序列
        # 判读需可辨「数字跳水=换线非丢核心」)
        _tgt = d.get('target_comp') or ''
        mark = ' ↹' if (prev_tgt is not None and _tgt != prev_tgt) else ''
        prev_tgt = _tgt
        # sim 批次:board 恒空(档位恒 0 误导)→ 三维同屏换账本代理
        # 维度(深度/核心在场/方向态;core_count 按 target 路由,
        # **跨线不可比**——核心定义随 tgt 切换,↹ 标换线轮)
        _simd = d.get('sim')
        if _simd is not None:
            _cc = _simd.get('core_count')
            _cc_s = '-' if _cc is None else str(_cc)
            lines.append(
                f"  p{k[0]}r{k[1]} 深={_simd.get('depth')}"
                f" 核={_cc_s}"
                f"{' ✓方向' if _simd.get('dir_established') else ''}"
                f" tgt={_tgt or '-'}{mark}")
            _dep = _simd.get('deployed') or []
            if _dep:
                lines.append(f"    deployed={' '.join(_dep)}")
            continue
        board = (d.get('state') or {}).get('board') or {}
        activated = {}
        for fac, cnt in board.items():
            tiers = getattr(FACTIONS.get(fac), 'tiers', ()) or ()
            tier = next((t for t in tiers if cnt >= t), 0)
            if tier > 0:
                activated[fac] = tier
        total = sum(activated.values())
        mark = '' if total else '  ← 档0'
        lines.append(f"  p{k[0]}r{k[1]} 激活档={total} {activated if activated else ''}{mark}")
        # r358(用户点题「看羁绊忽略角色/装备乱用不可见」):阵容质量三维
        # 同屏——角色构成(名字+星级)+ 装备分配(谁穿了什么)。不再截断
        # [:7](后期 9-10 人,截断藏人);未知名(身份 miss)保留槽位计数。
        _deployed = (d.get('state') or {}).get('deployed') or []
        dep_str = ' '.join(
            f"{c.get('char_id') or '?'}{'★' * (c.get('star') or 1)}"
            for c in _deployed) or '(空板)'
        lines.append(f"    deployed={dep_str}")
        _eq_pairs = [(c.get('char_id') or '?', c.get('equips') or [])
                     for c in _deployed if (c.get('equips'))]
        if _eq_pairs:
            lines.append('    装备=' + ' '.join(
                f"{n}[{','.join(eq)}]" for n, eq in _eq_pairs))
        _owned = (d.get('state') or {}).get('equips') or []
        if _owned:
            lines.append(f"    owned装备={len(_owned)}件(滞留未穿判读): "
                         f"{','.join(_owned[:8])}{'…' if len(_owned) > 8 else ''}")
    return lines



def query_plan_vs_exec(replay_dir: Path, run_id: str) -> list[str]:
    """视图:plan 动作 vs 实际执行对拍(步进 decisions 里的 plan 序列 vs 次轮
    board/bench 变化;r126 发现「plan 买白厄在首位但实跑只买 1 张」类执行
    缺口的判读入口)。

    方法:每轮末条决策的 plan buys/refresh/level vs 下一轮首条决策的
    gold 差(金没花=买没执行/金花了板没变=点了没生效)。"""
    rows = [d for d in read_jsonl(replay_dir / 'decisions.jsonl')
            if d.get('run_id') == run_id]
    rows.sort(key=lambda d: (d.get('plane') or 0, d.get('round_num') or 0,
                             d.get('ts') or ''))
    lines: list[str] = []
    # 按轮聚合
    by_round: dict = {}
    for d in rows:
        by_round.setdefault((d.get('plane'), d.get('round_num')), []).append(d)
    keys = sorted(by_round)
    for i, k in enumerate(keys[:-1]):
        cur = by_round[k]
        nxt = by_round[keys[i + 1]]
        # 轮内累计 plan 动作
        buys = lvl = rf = 0
        for d in cur:
            for a in (d.get('actions') or []):
                t = a.get('__type__')
                if t == 'BuyCard':
                    buys += 1
                elif t == 'LevelUp':
                    lvl += 1
                elif t == 'RefreshShop':
                    rf += 1
        g_end = cur[-1].get('state', {}).get('gold')
        g_next = nxt[0].get('state', {}).get('gold')
        if g_end is None or g_next is None:
            continue
        # 期望:下轮金 ≈ 本轮末 - 花费 + 收入(5±) ;偏差大 = 执行缺口
        delta = g_next - g_end
        # 收入 ~5-8(利息+基础);delta 显著大于收入 = plan 没花出去
        suspicious = (buys + rf + lvl) > 0 and delta > 12
        mark = '  ← 疑似未执行(金几乎没花)' if suspicious else ''
        lines.append(f"  p{k[0]}r{k[1]} plan:买{buys} 升{lvl} 刷{rf} | 金 {g_end}→{g_next}"
                     f"(Δ{delta:+d}){mark}")
    return lines



# —— `w494_spend_ledger/` 执行层 spend_ledger:购买单元「计划金流 vs 实际金流」记账 ——
# 背景(根缺出处:.debug/temp/currency_war/w489_sim_real_gap/REPORT.md §1.3):
# 高金购买单元无法区分「策略裁掉不买」vs「动作发出但没生效」——缺单元级
# 完整账。本段三件:纯函数 plan_gold_flow(逐项期望金差)/ classify_spend_unit
# (三态判定)/ query_spend_ledger(读端视图)。写端 = prep_director 的
# RunBuyPhase 执行边界(record_spend_unit),只记单元框架;plan 与金真值
# join 自 decisions.jsonl(shop plan 行)与 obs_conflicts.jsonl(gold_delta
# 冲突行)——复用既有链,不建第二套金读数。

#: 单元关店实读金的冲突行 join 窗(秒):obs_conflicts 是跨局 journal、
#: 行内无 run_id,同 (plane, round) 跨局复现——按 ts 邻近消歧。
_SPEND_CONFLICT_TS_WINDOW_S: int = 600


#: 大额失配清单门槛(金):`w489_sim_real_gap/` 感知面大额漂移 16-40 金量级,>10 报清单。
_SPEND_LARGE_GAP: int = 10



def plan_gold_flow(plan_actions: list[dict[str, Any]],
                   refresh_cost: int = 2) -> dict[str, Any]:
    """plan 序列化动作清单 → 逐项期望金流(纯函数,可单测)。

    输入 = decisions.jsonl 行的 ``actions``(serialize_action 产物,``__type__``
    判型)。计费口径与 shop.py spend_audit 对齐:BuyCard 取原始 ``card.cost``
    (不做 card_cost 3 兜底——审计可比性优先);RefreshShop cost=0 退
    ``refresh_cost`` 参数(= 审计的 ``state.shop_refresh_cost or 2``);
    SellBench/SellDeployed 收入取 ``income``(None 记 0 并标 income_unknown)。

    **口径边界**:plan 是全量清单,执行侧会在首个 RefreshShop 截断 prefix 且
    跳过 Sell/Deploy 类——期望按全量算,与执行实况的偏差本身是账要暴露的
    对象(has_refresh 标志辅助判读截断型失配)。
    """
    items: list[dict[str, Any]] = []
    spend = 0
    income = 0
    has_refresh = False
    income_unknown = False
    for a in plan_actions or []:
        if not isinstance(a, dict):
            continue
        t = a.get('__type__') or ''
        if t == 'BuyCard':
            card = a.get('card') or {}
            cost = int(card.get('cost') or 0)
            spend += cost
            items.append({'type': t, 'target': str(card.get('name') or f"x{card.get('x')}"),
                          'cost': cost, 'direction': 'spend'})
        elif t == 'LevelUp':
            cost = int(a.get('cost') or 0)
            spend += cost
            items.append({'type': t, 'target': 'level_up', 'cost': cost, 'direction': 'spend'})
        elif t == 'RefreshShop':
            cost = int(a.get('cost') or 0) or int(refresh_cost)
            spend += cost
            has_refresh = True
            items.append({'type': t, 'target': 'refresh', 'cost': cost, 'direction': 'spend'})
        elif t in ('SellBench', 'SellDeployed'):
            inc = a.get('income')
            if inc is None:
                income_unknown = True
                inc = 0
            income += int(inc)
            items.append({'type': t, 'target': str(a.get('bench_idx', a.get('deployed_idx', '?'))),
                          'cost': int(inc), 'direction': 'income'})
    return {'planned_spend': spend, 'planned_income': income,
            'net': income - spend, 'has_refresh': has_refresh,
            'income_unknown': income_unknown, 'items': items}



def classify_spend_unit(plan_actions: list[dict[str, Any]],
                        gold_open: int | None, gold_close: int | None,
                        *, refresh_cost: int = 2, tolerance: int = 2,
                        boundary: str = 'closed',
                        executed: dict[str, Any] | None = None) -> dict[str, Any]:
    """购买单元三态判定(纯函数,可单测;`w494_spend_ledger/` 设计 §3;`w577_refresh_fee_and_andon/` 扩「计划≠尝试」分流)。

    verdict 域:effective(生效)/ not_effective(执行未生效)/
    partial_mismatch(金动了但对不上账)/ unplanned_spend(计划外花销)/
    no_spend_quiet(未计划且金未动)/ plan_truncated(plan 有动作未尝试——
    执行侧硬墙跳过/至首个 RefreshShop 截断,口径差非执行失败,`w577_refresh_fee_and_andon/`)/
    free_refresh_proc(刷新已尝试+牌面已变+金差≈0 = 免费刷新生效,`w577_refresh_fee_and_andon/`)/
    unknown(读数缺失或非完整单元——**记 unknown 不猜**:无 gold_delta
    冲突行 ≠ 对拍通过,read_gold 失败同样不写行,离线不可分,宁缺勿错)。
    tolerance 与 shop.py spend_audit ±2 同源;boundary != 'closed'(半单元/
    中断单元)不判——执行链不完整,任何判定都是猜。

    executed(`w577_refresh_fee_and_andon/`,可选)= 执行侧可见化事实(SpendUnitRecord 同名字段;
    None=旧数据/未挂钩,判定退回 `w494_spend_ledger/` 原语义)。判定序(ADR-0456):
    ①plan_truncated → plan_truncated(**不停**——口径差,留台账);
    ②金差≈0 ∧ 计划花费>0 ∧ 已尝试 → not_effective(**停**——真点击落空);
    ③金差≈0 ∧ 刷新已尝试 ∧ 牌面已变 → free_refresh_proc(**不停**+采证)。
    """
    flow = plan_gold_flow(plan_actions, refresh_cost)
    out: dict[str, Any] = {
        'verdict': 'unknown', 'reason': '',
        'planned_spend': flow['planned_spend'],
        'planned_income': flow['planned_income'],
        'expected_net': flow['net'], 'actual_delta': None, 'gap': None,
        'boundary': boundary, 'has_refresh': flow['has_refresh'],
        'income_unknown': flow['income_unknown'], 'items': flow['items'],
        'plan_truncated': bool((executed or {}).get('plan_truncated')),
        'refresh_attempted': bool((executed or {}).get('refresh_attempted')),
        'refresh_board_changed': (executed or {}).get('refresh_board_changed'),
    }
    if boundary != 'closed':
        out['reason'] = f'boundary={boundary}(非完整单元不判)'
        return out
    if gold_open is None or gold_close is None:
        out['reason'] = 'gold_reading_missing(开/关店金读数缺失)'
        return out
    actual = int(gold_close) - int(gold_open)
    gap = actual - flow['net']
    out['actual_delta'] = actual
    out['gap'] = gap
    if out['plan_truncated']:
        out['verdict'] = 'plan_truncated'
        out['reason'] = '计划动作未全尝试(执行侧硬墙/截断跳过)——口径差非执行失败,不停'
        return out
    if flow['planned_spend'] > 0:
        if abs(gap) <= tolerance:
            out['verdict'] = 'effective'
        elif abs(actual) <= tolerance:
            if out['refresh_attempted'] \
                    and out['refresh_board_changed'] is True:
                out['verdict'] = 'free_refresh_proc'
                out['reason'] = '刷新已尝试+牌面已变+金差≈0 = 免费刷新生效(采证),不停'
            else:
                out['verdict'] = 'not_effective'
        else:
            out['verdict'] = 'partial_mismatch'
    else:
        if actual <= -tolerance:
            out['verdict'] = 'unplanned_spend'
        else:
            out['verdict'] = 'no_spend_quiet'
    return out



def _read_conflict_gold_delta(replay_dir: Path) -> list[dict[str, Any]]:
    """obs_conflicts.jsonl 的 gold_delta/shop_spend_audit 行(容错读;坏行跳过)。"""
    rows: list[dict[str, Any]] = []
    p = replay_dir / 'obs_conflicts.jsonl'
    if not p.exists():
        return rows
    with p.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (r.get('field') == 'gold_delta'
                    and r.get('source') == 'shop_spend_audit'):
                rows.append(r)
    return rows



def _match_conflict(conflicts: list[dict[str, Any]], plane: int, round_num: int,
                    ts: str) -> dict[str, Any] | None:
    """按 (plane, round) + ts 邻近窗匹配关店实读金冲突行(就近取;纯函数)。"""
    try:
        from datetime import datetime as _dt
        t0 = _dt.fromisoformat(ts) if ts else None
    except ValueError:
        t0 = None
    best = None
    best_dt = None
    for r in conflicts:
        if (r.get('plane'), r.get('round_num')) != (plane, round_num):
            continue
        if t0 is None:
            best = r
            break
        try:
            from datetime import datetime as _dt2
            d = abs((_dt2.fromisoformat(r.get('ts') or '') - t0).total_seconds())
        except (ValueError, TypeError):
            continue
        if d <= _SPEND_CONFLICT_TS_WINDOW_S and (best_dt is None or d < best_dt):
            best, best_dt = r, d
    return best



def _spend_unit_row(replay_dir: Path, run_id: str, plane: int,
                    round_num: int, unit_seq: int) -> dict[str, Any] | None:
    """spend_ledger 本单元最新行(按 run/plane/round/unit_seq 定位;纯读)。

    消费方 = prep_director 安灯钩子(_exec_fail_hook_check):读执行侧
    「计划≠尝试」事实字段(plan_truncated/refresh_*)作分类器 executed 输入。
    行缺失(历史局/未挂钩)→ None,分类器退回 `w494_spend_ledger/` 原语义不停。
    """
    found: dict[str, Any] | None = None
    p = replay_dir / 'spend_ledger.jsonl'
    if not p.exists():
        return None
    for r in read_jsonl(p):
        if (r.get('run_id') != run_id
                or (int(r.get('plane') or 0), int(r.get('round_num') or 0))
                != (plane, round_num)
                or int(r.get('unit_seq') or 0) != unit_seq):
            continue
        found = r
    return found



def _shop_plan_rows(replay_dir: Path, run_id: str) -> dict[tuple[int, int], dict[str, Any]]:
    """decisions.jsonl 的 shop plan 行(同轮取最后;纯读)。

    判别式:shop.py plan 行的 eval_breakdown 无 'prep_step' 键,prep_director
    步进行带 'prep_step'(现成判别式,零 schema 改动)。
    """
    plans: dict[tuple[int, int], dict[str, Any]] = {}
    p = replay_dir / 'decisions.jsonl'
    if not p.exists():
        return plans
    for d in read_jsonl(p):
        if run_id and d.get('run_id') != run_id:
            continue
        eb = d.get('eval_breakdown') or {}
        if isinstance(eb, dict) and 'prep_step' in eb:
            continue
        if not d.get('actions'):
            continue
        plans[(int(d.get('plane') or 0), int(d.get('round_num') or 0))] = d
    return plans



def query_spend_ledger(replay_dir: Path, run_id: str) -> list[str]:
    """视图(`w494_spend_ledger/`):购买单元金账——三态计数 + 大额失配清单。

    join 三流:spend_ledger.jsonl(单元框架,run_id 过滤)× decisions.jsonl
    shop plan 行(plan/开店金)× obs_conflicts.jsonl gold_delta(关店实读金,
    ts 邻近窗消歧)。ledger 缺行(历史局/未挂钩期)按 plan 行逐轮重建伪单元
    (boundary 标 unknown)——`w489_sim_real_gap/` 式审计可直接消费存量 replay。读数缺失
    行记 unknown 不猜(设计 §3)。
    """
    ledger = [r for r in read_jsonl(replay_dir / 'spend_ledger.jsonl')
              if not run_id or r.get('run_id') == run_id]
    plans = _shop_plan_rows(replay_dir, run_id)
    conflicts = _read_conflict_gold_delta(replay_dir)
    units: list[dict[str, Any]] = []
    for r in sorted(ledger, key=lambda x: x.get('ts') or ''):
        pr, rnd = int(r.get('plane') or 0), int(r.get('round_num') or 0)
        plan_row = plans.get((pr, rnd))
        conf = _match_conflict(conflicts, pr, rnd, r.get('ts') or '')
        # 关店实读金取值序:行内 gold_close(shop 关店对拍点无条件落)优先;
        # 旧行(钩子挂上前)恒 None → 回退冲突行。两者同源同读,回退不是
        # 第二口径;都缺 → unknown 不猜(读失败也以行内 None+trusted=False
        # 形态留痕,与「对拍通过」可分)。
        gold_close = r.get('gold_close')
        if gold_close is None:
            gold_close = (conf or {}).get('new')
        cls = classify_spend_unit(
            (plan_row or {}).get('actions') or [],
            (plan_row or {}).get('gold'), gold_close,
            boundary=str(r.get('boundary') or 'closed'),
            executed={'plan_truncated': r.get('plan_truncated'),
                      'refresh_attempted': r.get('refresh_attempted'),
                      'refresh_board_changed': r.get('refresh_board_changed')})
        cls['unit'] = r
        cls['plan_gold'] = (plan_row or {}).get('gold')
        cls['plan_gold_readable'] = (plan_row or {}).get('gold_readable')
        cls['conflict_expected'] = (conf or {}).get('old')
        units.append(cls)
    if not ledger:
        # 历史局回退:无 ledger 行,按 shop plan 行逐轮重建伪单元
        #(boundary=unknown——无执行边界事实,判定恒 unknown,只呈现金流面)。
        for (pr, rnd), plan_row in sorted(plans.items()):
            conf = _match_conflict(conflicts, pr, rnd, plan_row.get('ts') or '')
            cls = classify_spend_unit(
                plan_row.get('actions') or [], plan_row.get('gold'),
                (conf or {}).get('new'), boundary='unknown')
            cls['unit'] = {'ts': plan_row.get('ts'), 'plane': pr, 'round_num': rnd,
                           'unit_seq': 0, 'boundary': 'unknown', 'detail': '(伪单元:无ledger行)'}
            cls['plan_gold'] = plan_row.get('gold')
            cls['plan_gold_readable'] = plan_row.get('gold_readable')
            cls['conflict_expected'] = (conf or {}).get('old')
            units.append(cls)
    if not units:
        return ['  (无购买单元记录——本局无 shop plan 行且无 spend_ledger 行)']
    verdict_count: dict[str, int] = {}
    lines: list[str] = []
    large: list[str] = []
    for c in units:
        v = c['verdict']
        verdict_count[v] = verdict_count.get(v, 0) + 1
        u = c['unit']
        gold_s = f"开金={c['plan_gold'] if c['plan_gold'] is not None else '?'}"
        if c['actual_delta'] is not None:
            flow_s = f" Δ={c['actual_delta']}(期望{c['expected_net']},差{c['gap']})"
        elif c['conflict_expected'] is not None:
            flow_s = f" 冲突行:期望{c['conflict_expected']} 实读见conflicts"
        else:
            flow_s = ' 关店金无读数'
        unit_tag = f"u{u.get('unit_seq') or '?'}"
        gold_s = f"开金={c['plan_gold'] if c['plan_gold'] is not None else '?'}"
        lines.append(
            f"  {unit_tag} p{u.get('plane')}r{u.get('round_num')} [{v}] "
            f"花费={c['planned_spend']} 收入={c['planned_income']} {gold_s}{flow_s}"
            f"{'(伪单元)' if u.get('boundary') == 'unknown' and u.get('detail') else ''}"
            f"{'(刷新截断面)' if c['has_refresh'] else ''}")
        if c['gap'] is not None and abs(c['gap']) > _SPEND_LARGE_GAP:
            large.append(f"  p{u.get('plane')}r{u.get('round_num')} {unit_tag} [{v}] "
                         f"差={c['gap']}(花费{c['planned_spend']})")
        elif c['conflict_expected'] is not None and c['plan_gold'] is not None:
            # 判定 unknown(读数缺一)但冲突行在:冲突行自身 gap = 实读 − 审计期望,
            # 是独立的失配证据,直接呈现(不与 plan 口径混算)。
            try:
                conf_gap = None
                conf = _match_conflict(conflicts, int(u.get('plane') or 0),
                                       int(u.get('round_num') or 0), u.get('ts') or '')
                if conf is not None and isinstance(conf.get('new'), (int, float)) \
                        and isinstance(conf.get('old'), (int, float)):
                    conf_gap = int(conf['new']) - int(conf['old'])
            except (ValueError, TypeError):
                conf_gap = None
            if conf_gap is not None and abs(conf_gap) > _SPEND_LARGE_GAP:
                large.append(f"  p{u.get('plane')}r{u.get('round_num')} {unit_tag} [{v}] "
                             f"冲突行差={conf_gap}(审计期望{c['conflict_expected']})")
    total = len(units)
    head = [f"  [三态计数] 共{total} " +
            " ".join(f"{k}×{v}" for k, v in sorted(verdict_count.items()))]
    if large:
        head.append(f"  —— 大额失配(|差|>{_SPEND_LARGE_GAP}){len(large)} 条 ——")
        head.extend(large)
    return head + lines



# —— 迁移审计 w315(git 历史)(遥测审计 G3):四条旁路 jsonl 流的零查询视图补齐 ——
# exogenous / exec_events / invest_cards / obs_conflicts 此前只能裸翻文件
# (审计都得手写 PowerShell Group-Object);「需求已固化的复盘 = 新视图」。
# 约定与既有视图一致:按 run_id 过滤(obs_conflicts 例外——观察冲突 journal
# 是跨局采集,行内本就无 run_id 键,见 cw_observe._CONFLICT_JOURNAL)、
# 最新优先(旁路流是事件流水,倒序看最近发生)、头部带聚合计数。


def _filter_latest(rows: list[dict[str, Any]], run_id: str,
                   key: str = "run_id") -> list[dict[str, Any]]:
    """按 run_id 过滤 + ts 倒序(最新优先);run_id 空 = 不过滤(全量)。"""
    out = [r for r in rows if not run_id or r.get(key) == run_id]
    out.sort(key=lambda r: r.get("ts") or "", reverse=True)
    return out



def query_exogenous(replay_dir: Path, run_id: str) -> list[str]:
    """视图(迁移审计 w315(git 历史)/G3):外生事件流(exogenous.jsonl)——kind/round/内容摘要。

    头部 = kind 计数(预案 trigger 频率统计的直接读出端);迁移审计 w312(git 历史) 的
    event_choice 行展开选项面(提供了什么/选了哪个/为什么——G1 闭环)。
    """
    rows = _filter_latest(read_jsonl(replay_dir / "exogenous.jsonl"), run_id)
    kind_count: dict[str, int] = {}
    lines: list[str] = []
    for r in rows:
        kind = r.get("kind") or "?"
        kind_count[kind] = kind_count.get(kind, 0) + 1
        snap = r.get("state_snapshot") or {}
        ctx_s = (f" hp={snap['hp']} g={snap['gold']} lv={snap.get('level')}"
                 if snap.get("hp") is not None else "")
        # 迁移审计 w312(git 历史) 选项快照展开:每个候选取 difficulty/name 兜底摘要(识别失败
        # 行 options=[] 时显示 (无识别)——留证据可见,不静默)
        c_s = ""
        c = r.get("choice")
        if isinstance(c, dict):
            opts = c.get("options") or []
            brief = "/".join(
                str(o.get("difficulty") or o.get("name") or o)[:14] if isinstance(o, dict)
                else str(o)[:14] for o in opts[:5]) or "(无识别)"
            c_s = (f" 选[{c.get('event')}] n={c.get('n_options')}"
                   f" pick={c.get('pick_idx')}({brief}) 因={c.get('reason') or '-'}")
        lines.append(f"  [{kind}] r{r.get('round_num', '?')}{ctx_s}"
                     f" {r.get('detail') or ''}{c_s}")
    if not lines:
        return ["  (无记录)"]
    lines.insert(0, "  [kind 计数] "
                + " ".join(f"{k}×{v}" for k, v in sorted(kind_count.items())))
    return lines



def query_exec_events(replay_dir: Path, run_id: str) -> list[str]:
    """视图(迁移审计 w315(git 历史)/G3):执行事件流(exec_events.jsonl)——能力画像读出端。

    头部 = action_family×event 计数 + fail 率(27 号设计目标的「一句 CLI」:
    实现缺陷 vs 固有难度分型先看哪个族在哪个画面集中失败);逐行 = 逐事件。
    """
    rows = _filter_latest(read_jsonl(replay_dir / "exec_events.jsonl"), run_id)
    fam_event: dict[tuple[str, str], int] = {}
    lines: list[str] = []
    for r in rows:
        fam = r.get("action_family") or "?"
        ev = r.get("event") or "?"
        fam_event[(fam, ev)] = fam_event.get((fam, ev), 0) + 1
        retry = r.get("retry_count") or 0
        retry_s = f" retry={retry}" if retry else ""
        lines.append(f"  [{ev}] r{r.get('round_num', '?')} {fam}"
                     f"@{r.get('screen') or '?'} {r.get('reason') or '-'}{retry_s}")
    if not lines:
        return ["  (无记录)"]
    total = len(rows)
    fails = sum(v for (fam, ev), v in fam_event.items() if ev == "fail")
    summary = " ".join(f"{f}:{e}×{v}"
                       for (f, e), v in sorted(fam_event.items()))
    lines.insert(0, f"  [画像] 共{total} fail率={fails / total:.0%} {summary}")
    return lines



def query_invest_cards(replay_dir: Path, run_id: str) -> list[str]:
    """视图(迁移审计 w315(git 历史)/G3):投资卡候选与选择(invest_cards.jsonl;ADR-0132 采集)。

    同一次出卡按 (kind, ts) 聚成一组(逐卡一行落盘,组=一次选卡画面);
    ★=chosen(选了哪张一眼可见);头部 = 出卡次数按 kind 计数。
    """
    rows = _filter_latest(read_jsonl(replay_dir / "invest_cards.jsonl"), run_id)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    order: list[tuple[str, str]] = []
    for r in rows:
        k = (r.get("kind") or "?", r.get("ts") or "")
        if k not in groups:
            order.append(k)
        groups.setdefault(k, []).append(r)
    kind_count: dict[str, int] = {}
    lines: list[str] = []
    for k in order:
        cards = groups[k]
        kind_count[k[0]] = kind_count.get(k[0], 0) + 1
        lines.append(f"  [{k[0]}] {k[1]} 共{len(cards)}张")
        for c in sorted(cards, key=lambda x: x.get("idx") or 0):
            mark = " ★选" if c.get("chosen") else ""
            text = (c.get("effect_text") or "").replace("\n", " ")[:40]
            lines.append(f"    #{c.get('idx')} {c.get('name') or '?'}{mark} {text}")
    if not lines:
        return ["  (无记录)"]
    lines.insert(0, "  [出卡次数] "
                + " ".join(f"{k}×{v}" for k, v in sorted(kind_count.items())))
    return lines



def query_obs_conflicts(replay_dir: Path, run_id: str) -> list[str]:
    """视图(迁移审计 w315(git 历史)/G3):观察冲突流(obs_conflicts.jsonl;cw_observe journal)。

    `w603_telemetry_wiring/` 起新行带 run_id(唯一汇点 obs_conflict() 补齐):``--run`` 给定时
    按 run_id 过滤(历史行无此键→不命中,用空 run_id 全量看);空=全量展示。
    头部 = 按 field 分组计数 + verdict 首词分布(哪个字段在哪个画面毒化频次
    最高的离线统计入口;M38 教训的读出端);逐行 = 最新冲突摘要(截断防长
    verdict 刷屏)。
    """
    # 容错读(不走 read_jsonl):obs_conflicts 是 best-effort 追加的 journal,
    # 历史上存在中断产生的截断行——坏行跳过不炸整个视图(其余流结构化写,无此问题)
    raw_rows: list[dict[str, Any]] = []
    p = replay_dir / "obs_conflicts.jsonl"
    if p.exists():
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw_rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    rows = sorted(raw_rows, key=lambda r: r.get("ts") or "", reverse=True)
    # `w603_telemetry_wiring/` 起新行带 run_id 键——给了 run_id 才过滤(历史行无键不命中);
    # 空 = 全量展示
    if run_id:
        rows = [r for r in rows if r.get("run_id") == run_id]
    field_count: dict[str, int] = {}
    verdict_count: dict[tuple[str, str], int] = {}
    lines: list[str] = []
    for r in rows:
        field = r.get("field") or "?"
        field_count[field] = field_count.get(field, 0) + 1
        # verdict 摘要 = 首个分隔符(括号/分号/顿号)前的短语(完整裁决
        # 语境常带长论据,统计口径取裁决类别词)
        v_full = r.get("verdict") or "-"
        v_short = v_full.split("(")[0].split("；")[0].split(";")[0].strip()[:16]
        verdict_count[(field, v_short)] = verdict_count.get((field, v_short), 0) + 1
        if len(lines) < 30:   # 明细只展最近 30 条(6 万行级文件,全打=刷屏)
            old = str(r.get("old"))[:24]
            new = str(r.get("new"))[:24]
            lines.append(f"  [{field}] {r.get('ts')} {old}→{new} | {v_short}")
    if not lines and not field_count:
        return ["  (无记录)"]
    head = ["  [field 计数] "
            + " ".join(f"{k}×{v}" for k, v in sorted(field_count.items(),
                                                     key=lambda x: -x[1]))]
    for (f, v), n in sorted(verdict_count.items(), key=lambda x: -x[1])[:12]:
        head.append(f"  {f}/{v}: {n}")
    return head + ["  —— 最近明细(≤30)——"] + lines

