"""判读查询纯函数层(自 cw_telemetry 拆出,分包期6;W3 收缩为单一源保留面)。

W3(R5 单源直迁第三波,正本 = docs/develop/sr_od/application/currency_war/game_state/
r5-migration-plan.md §2 W3):旧 12 流视图族(query_rounds/supply/anomalies/
hp/economy/gold_flow/tiers/plan_vs_exec/spend_ledger/exogenous/exec_events/
invest_cards/obs_conflicts 及其 join/helper)随流写入端退役(删除波 1)一并
删除——判读唯一读面 = journal 新账(telemetry/journal_query 视图族 + 判读
CLI);本模块只保留仍被**活消费方**引用的纯函数单一源:

- ``read_jsonl``:通用 JSONL 宽容读(match_archive 切片/装配面;存量档案
  裸读考古同用);
- ``HP_CONF_TRUSTED``/``_outcome_hp_trusted``:outcome 行 hp 可信门单一源
  (match_archive 档案真值链 + sim 池语料面);
- ``plan_gold_flow``/``classify_spend_unit``:支出账分类单一源(运行时安灯
  停机钩子 run_state.exec_fail_should_stop 消费;输入 = serialize_action
  产物,与旧 decisions plan 行同 schema)。

吃旧流的存量语料判读:裸 JSONL 可直接读(归档只读);git 历史可复活已删
视图(申报 = 候裁 6 考古工具面口径,retirement.md §7-#7)。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# 升级动作类型口径(读端统一桶):生产 serialize_action 落具体类名
# ``LevelUpShop``(W970 §4.1.3 商店屏拆分,is-a LevelUp;schema.py
# ``__type__=type(action).__name__``),sim 账本与旧数据落基类名
# ``'LevelUp'``(engine_p1 显式注释「账本 __type__ 仍落 'LevelUp'」)。
# 读端两型同桶,单一源 = 本常量(实证 g_20260903_232823 p1r2/r4:
# LevelUpShop 已发而视图 升/花 全 0)。
_LEVELUP_TYPES: tuple[str, ...] = ('LevelUp', 'LevelUpShop')


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


def plan_gold_flow(plan_actions: list[dict[str, Any]],
                   refresh_cost: int = 2) -> dict[str, Any]:
    """plan 序列化动作清单 → 逐项期望金流(纯函数,可单测)。

    输入 = serialize_action 产物(``__type__`` 判型;W3/T-255 起运行时
    安灯侧同样喂真实动作对象的 serialize_action 产物,与旧 decisions
    plan 行同 schema,分类单一源不建第二套)。计费口径与 shop.py
    spend_audit 对齐:BuyCard 取原始 ``card.cost``(不做 card_cost 3 兜底
    ——审计可比性优先);RefreshShop cost=0 退 ``refresh_cost`` 参数
    (= 审计的 ``state.shop_refresh_cost or 2``);SellBench/SellDeployed
    收入取 ``income``(None 记 0 并标 income_unknown)。

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
            # 归因名优先平铺 char_id(M2 增强批:serialize_action 顶层富化,
            # 注册表规范名)→ 跨流对账不再吃 OCR 原名;旧记录无此键回退
            # card.name,再退 x 序号。
            target = str(a.get('char_id') or card.get('name')
                         or f"x{card.get('x')}")
            items.append({'type': t, 'target': target,
                          'cost': cost, 'direction': 'spend'})
        elif t in _LEVELUP_TYPES:
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

    executed(`w577_refresh_fee_and_andon/`,可选)= 执行侧可见化事实
    (W3/T-255 起运行时源 = 安灯钩子的访问事实暂存,切片5 = ledger
    .fact_rows 发射时增量追加行,经
    ``unit_exec_facts_from_receipts`` 派生;迁移批 3.2 前历史源 =
    BuyCardsOutcome 执行事实字段;None = 旧数据/未挂钩,判定退回
    `w494_spend_ledger/` 原语义)。判定序(ADR-0456):
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
