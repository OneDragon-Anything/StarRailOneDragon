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
  (match_archive 档案真值链 + sim 池语料面)。

(原 ``plan_gold_flow``/``classify_spend_unit`` 支出账分类族已随执行失败
安灯退役删除——2026-09-16 裁定「未建档实证的故障形态不作兜底理由」,
安灯挂点/谓词/分类单一源一并删,git 历史可复活。)

吃旧流的存量语料判读:裸 JSONL 可直接读(归档只读);git 历史可复活已删
视图(申报 = 候裁 6 考古工具面口径,retirement.md §7-#7)。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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


