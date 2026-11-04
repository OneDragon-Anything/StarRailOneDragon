"""撤销/熔断操作证据留存(纯观测索引层,零行为变更;复用 defect_ledger
record 模式,禁第二套机制)。

在库分键:
- ``sell_breaker_preserved``:卖出熔断撤销面(谁/为何/
  保留了什么;写入点 = cw_op_deploy off-target 卖出通道的围栏保留分支);
- ``drought_buy_no_reset``:干旱计数器买入不重置证据面(pair_drought
  重置单一源 = 商店可见性 _update_pair_drought,买入不重置——干旱解锁
  流程审计面;写入点 = CwActionBuyCardParam 执行成功点)。

既有覆盖(复用不另建):m2_retry_exhausted / bench_full_buy_abandon /
shop_churn_pair_buy 等 cw4_counters 族 + 干旱当值内联本证据行
expected/observed(decisions 行 drought 字段载体已停用);
策略桶受包依赖矩阵限制(strategies→telemetry
非合法边),店侧熔断 veto 经 cw4_counters 分键承载,证据写入点收敛在
operations 执行侧。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_telemetry_exit import (
    journal_refs,
)
from sr_od.application.currency_war.telemetry import defects


def record_drought_buy_no_reset(*, member: str, system: str,
                                drought: int) -> None:
    """干旱计数器买入不重置证据(L2 保留证据;解锁流程审计面)。

    pair_drought 重置单一源 = 商店可见性(cw_intention._update_pair_drought);
    买入体系成员不重置计数——本分键把「买了但没重置」的形态落台账,
    供干旱解锁流程对账(键值含成员/体系/当值摘要,可回放)。
    """
    if drought <= 0:
        return   # 计数为 0 无审计诉求(零噪声)
    defects.record_defect(
        'economy', 'drought_buy_no_reset',
        expected=f'{system} 买入重置干旱计数',
        observed=(f'买 {member} 后 pair_drought[{system}]={drought} '
                  '未重置(重置单一源=商店可见性)'),
        # 干旱计数现役载体 = 策略 state 状态容器(GameState)(值已在本行 expected/
        # observed 内联),refs 指 journal (run_id,v) 登记条目。
        refs=journal_refs(),
        note='撤销操作证据留存:买入不重置,干旱解锁流程审计面',
        gap_large=False, severity=defects.SEVERITY_L2_RECORD)
