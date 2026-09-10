"""备战/对局运行态旗标:执行失败停机钩子(exec_fail)族(自 cw_screen_prep 拆出,分包期6)。

停机钩子语义:write_exec_fail_flag 在观测到执行失败时落旗,下一局起点
exec_fail_should_stop 消费分类结论决定是否停线(消费 cw_telemetry.query
的支出分类单一源,不建第二套分类)。
"""

from __future__ import annotations

import time
from pathlib import Path

from one_dragon.utils.file_utils import get_project_root

# [停机钩子·临时采证,W494 spend_ledger 续;安灯式,用户裁决采纳]
# 触发:购买单元关闭时分类器判 mismatch(计划花费>0 且金差≈0 = 动作发出但金没动)。
# 生命周期(od-dev-stop-hooks §2.1 临时捕获类):失败模式根因修完并验证后删整段
# (谓词/写 flag/挂点一并删),不留开关/参数。

#: 哨兵 flag 路径(仓根锚定绝对路径:daemon spawn 的非 CWD 进程里相对路径会落错,
#: 同 shop_unk 钩子审查#4 教训;测试经 write_exec_fail_flag 参数注入 tmp_path)。
_EXEC_FAIL_FLAG_RELPATH = Path('.debug') / 'temp' / 'cw_exec_fail_hook.flag'



def exec_fail_flag_path() -> Path:
    """哨兵 flag 绝对路径(锚仓根,经 one_dragon.utils.file_utils.get_project_root 定位)。"""
    return get_project_root() / _EXEC_FAIL_FLAG_RELPATH



def exec_fail_should_stop(plan_actions: list | None, gold_open, gold_close, *,
                          boundary: str = 'closed',
                          executed: dict | None = None) -> bool:
    """安灯式停机谓词(纯函数,可单测):mismatch 才停。

    mismatch = 分类器 not_effective(计划花费>0 且金差≈0 且**已尝试**——
    真点击落空);partial_mismatch(金动了但对不上账)与 unknown(读数缺失/
    半单元)不停——前者可能是口径差非执行失败,后者证据不足。W577(ADR-0456)
    扩两豁免态:**plan_truncated**(plan 有动作未尝试——硬墙跳过/截断,口径差)
    与 **free_refresh_proc**(刷新已尝试+牌面已变+金差≈0,免费生效)——verdict
    域变宽,本谓词仍只对 not_effective 停,自动豁免两新态。判定复用
    ``cw_telemetry.classify_spend_unit``,不建第二套分类。
    """

    from sr_od.application.currency_war.telemetry.query import classify_spend_unit
    cls = classify_spend_unit(plan_actions or [], gold_open, gold_close,
                              boundary=boundary, executed=executed)
    return cls['verdict'] == 'not_effective'



def write_exec_fail_flag(flag_path: Path, *, run_id: str, plane: int,
                         round_num: int, unit_seq: int, plan_summary: str,
                         gold_open, gold_close) -> str:
    """写哨兵 flag(纯 IO,可单测;内容锁 od-dev-stop-hooks flag 三要素)。

    三要素:触发定位(HOOK-STOP 标记+钩子位置+触发态+时间)/ 可执行处理步骤 /
    移除条件(按 od-dev-stop-hooks §2.1 分类:本钩子 = 常驻兜底,非临时捕获)。
    返回写入内容(测试断言用)。
    """
    content = (
        '[HOOK-STOP] 执行失败停机钩子(常驻兜底,安灯式;cw_screen_prep 购买单元记账边界)\n'
        f'触发:购买单元关闭时分类器判 mismatch(计划花费>0 且金差≈0 = 动作发出但金没动;'
        f'partial/unknown 不停)。\n'
        f'定位:run_id={run_id} p{plane}r{round_num} unit_seq={unit_seq} '
        f'ts={time.strftime("%Y-%m-%d %H:%M:%S")}\n'
        f'plan 摘要:{plan_summary}\n'
        f'gold:开={gold_open} 关={gold_close}\n'
        f'截图:.debug/images/exec_fail_* (前缀含 run_id/轮/unit_seq)\n'
        f'处理步骤:1. 看截图核购买单元画面;2. 对拍现场数据确认是执行未生效'
        f'(点击落空/被拦)还是口径失配——现役数据源 = journal(state/journal.jsonl:'
        f'receipts 回执窗 + state.values.gold 行行快照)与本钩子 flag 的 plan/gold '
        f'三件组;旧三流对拍(spend_ledger/decisions/obs_conflicts)已随删除波 1 '
        f'停写,只辖存量语料;3. 修失败模式并验证后,删本 flag'
        f'(钩子保留)+ 重启载入代码的进程。\n'
        f'移除条件:常驻兜底钩子——该失败类根因修复并长期验证后,按 '
        f'od-dev-stop-hooks §2.1 评估移除整段;平时触发只删 flag 不删钩子,不留开关。\n'
    )
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.write_text(content, encoding='utf-8')
    return content

