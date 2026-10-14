"""cw4 证明层残留件——停手线谓词(``stop_buy``)。

批 3.7 退役申报(迭代 2026-10-12-prep-shop-workflow-redesign;
line_and_upgrade §1.6 退役面清单):本模块原承载的换线机器
(``should_switch``/θ 滞回/D_min 驻留/回锁窗 ``update_line_state``/
``register_eviction``/``resolve_switch_params``)、证据门影子评估族
(``evaluate_evidence_gate``/``evidence_gate``/``LockSandwichFrame``/
``assemble_lock_frame``/``line_missing_decomposition``)、直通信号臂
(``signal_arm``)已随候选-锁定制退役删除——防摇摆职责由锁定制结构
承接(硬规则锁定 + 锁后不换线,无摇摆形态产生;候选分数为显式版,
无影子面)。消费面去向:

- 换线判据/塌缩出口:候选-锁定制无换目标,无对象;
- 证据门:候选分数(line_select)为显式判据,夹界门与其 P76 标定槽
  (V_C_MINUS_V_F/E2_CONCENTRATION_BAND)随本批撤槽;
- 停手线:在册保留(shop.py 序 6 核验面 + mandate M2 前置)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import (
    predicates,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_vocab import Comp


def stop_buy(k: Comp | None, held_names: list[str],
             deployed_names: list[str]) -> bool:
    """停手线(R4-F8 函数位;R10-5 谓词语义钉死)。

    成型判定 = K 目标线单位齐备 ∧ 无待补缺口:线内全部成员名已出现在
    板(deployed)∪bench(held)——「当前线 K 成型」的分类谓词输出,
    评估对象恒为当前生效线 K、逐备战期随 M2 分类重评(证明 pass 后、
    M2 分类前由 entry 调用)。外因破成型(合成/装备消耗)⇒ 重评自然
    归 0,无锁存。
    """
    members = predicates.line_members(k)
    if not members:
        return False
    owned = set(held_names) | set(deployed_names)
    return all(m in owned for m in members)
