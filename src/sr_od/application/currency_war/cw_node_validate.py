"""货币战争 位面节点序列校验器(只判不改;W27,语料三缺陷定因配套)。

背景(2026-08-24 语料质量批):P1 节点模板基准 = ``docs/game/currency_war/
research/economy.md`` §10.2(25 开局帧众数;用户口径「节点基本固定,策略才改」)。
实机以**实时识别为权威**(invest-env 等特殊投资环境可改节点,如「人身意外险」
首领前+补给 / 「战争边疆」战斗→遭遇);开局帧存的 plane_node_table 只作离线
统计源。因此校验语义:

- **对照表优先**:调用方传了该 run 的 ``plane_node_table``(开局帧实读槽序)→
  以它为该 run 的期望模板(实读真值,非众数模板);
- 未传 → 用 §10.2 众数模板;**变异位(slot3/5/6 → r4/r6/r7)的偏离单独降级
  为 ``variant_slot`` 原因**(已知变异位,非识别事故的首要嫌疑),固定槽
  (slot0/1/2/4/7 → r1/r2/r3/r5/r8)偏离标 ``template_mismatch``;
- **特殊环境证据豁免**:行带真值证据字段(``special_env_evidence`` 或
  ``node_source=='live_read'``,见 ``EVIDENCE_KEYS``)→ 不标脏(invest-env
  改节点是游戏行为,不是语料错误);
- **只判不改**:返回脏行清单(dict,含 run_id/round_num/实际值/期望值/原因),
  不修改任何输入行——数据治理的修复决策归调用方。

已知语料事实(本批定因,消费时心里有数):
- P1 r5(补给)34/34 run 全缺 —— 补给节点无战斗结算屏,outcome 写端只挂
  battle_end 锚点 → 缺行是**系统性缺失**不是偏离(本校验器只判**在场行**,
  缺行归 ``cw_sim_checks`` 的覆盖类检查);
- 重启接管段会写 **round_num=1 + 兜底节点标签** 的伪行(实锤:run_20260823_
  151050 r1 普通战斗 / run_20260823_151913 r1 遭遇,真值分别是物理局的
  r6 战斗 / r7 遭遇)——这两类伪行恰好落固定槽 r1 偏离,是本校验器的
  主要捕获目标(脏行基线 = 2,见 W27_报告)。

P2 模板(§10.2 仅 1 开局帧,待多局复核)不启用校验:
``validate_p2_node_sequence`` 留接口(NotImplementedError)。
"""

from typing import Any

#: P1 众数节点模板(economy.md §10.2;r9 首领按位置判,词表 = outcomes.jsonl
#: 的中文标准词,经 battle_loop._normalize_node_type 出口)。
P1_NODE_TEMPLATE: list[str] = [
    '奖励', '奖励', '普通战斗', '普通战斗', '补给',
    '普通战斗', '遭遇', '奖励', 'boss',
]

#: 已知变异位(0-based slot 索引;§10.2「slot3/5/6 变异位」→ r4/r6/r7)。
#: 这些槽的游戏内实际类型可合法偏离众数(invest-env 改节点 / 帧间变异),
#: 偏离原因单列,便于与固定槽偏离(识别事故嫌疑)分流。
P1_VARIANT_SLOT_IDX: frozenset[int] = frozenset({3, 5, 6})

#: 特殊投资环境改节点的证据字段名(行 dict 的 key;任一命中且真值 → 豁免)。
#: - ``special_env_evidence``:显式证据(如该局 invest-env 记录);
#: - ``node_source``:节点类型来源标记,``live_read`` = 备战画面实时识别真值。
EVIDENCE_KEYS: dict[str, Any] = {'node_source': 'live_read'}

#: P2 模板(§10.2 开局帧 1 样本,证据不足,不启用;多局复核后填)。
P2_NODE_TEMPLATE: list[str] | None = None


def _has_special_env_evidence(row: dict[str, Any]) -> bool:
    """行是否带特殊环境/实读真值证据(豁免判据)。"""
    if row.get('special_env_evidence'):
        return True
    return any(row.get(key) == expect for key, expect in EVIDENCE_KEYS.items())


def validate_p1_node_sequence(
        rows: list[dict[str, Any]],
        plane_node_table: list[str] | None = None,
) -> list[dict[str, Any]]:
    """校验一个 run 的 P1 节点序列在场行(只判不改)。

    Args:
        rows: 该 run 的 P1 行(outcomes.jsonl 反序列化 dict,至少含
            ``round_num``/``node_type``,建议带 ``run_id``)。缺 ``round_num``
            或 ``node_type`` 的行标 ``missing_field``。
        plane_node_table: 该 run 开局帧实读槽序(可选;给了则以它为期望
            模板,变异位语义随之失效——表本身就是该局真值)。

    Returns:
        脏行清单(每项 dict:run_id/round_num/node_type/expected/reason)。
        reason 取值:``template_mismatch``(固定槽偏离)/ ``variant_slot``
        (变异槽偏离,降级)/ ``round_out_of_range``(r<1 或 r>9)/
        ``missing_field``(行字段缺失)/ ``table_conflict``(对照表内
        round 越界时的槽缺失)。
    """
    template = list(plane_node_table) if plane_node_table else P1_NODE_TEMPLATE
    use_variant_slots = plane_node_table is None   # 有实读表时无变异位概念
    dirty: list[dict[str, Any]] = []
    for row in rows:
        rid = row.get('run_id', '')
        rn = row.get('round_num')
        nt = row.get('node_type')
        if rn is None or nt is None:
            dirty.append({'run_id': rid, 'round_num': rn, 'node_type': nt,
                          'expected': None, 'reason': 'missing_field'})
            continue
        try:
            idx = int(rn) - 1
        except (TypeError, ValueError):
            dirty.append({'run_id': rid, 'round_num': rn, 'node_type': nt,
                          'expected': None, 'reason': 'missing_field'})
            continue
        if not 0 <= idx < len(template):
            dirty.append({'run_id': rid, 'round_num': rn, 'node_type': nt,
                          'expected': None, 'reason': 'round_out_of_range'})
            continue
        expected = template[idx]
        if str(nt).strip() == str(expected).strip():
            continue
        if _has_special_env_evidence(row):
            continue   # 特殊环境改节点(游戏行为),不是语料错误
        reason = ('variant_slot' if use_variant_slots and idx in P1_VARIANT_SLOT_IDX
                  else 'template_mismatch')
        dirty.append({'run_id': rid, 'round_num': rn, 'node_type': nt,
                      'expected': expected, 'reason': reason})
    return dirty


def validate_p2_node_sequence(
        rows: list[dict[str, Any]],
        plane_node_table: list[str] | None = None,
) -> list[dict[str, Any]]:
    """P2 节点序列校验(接口预留;模板证据不足,暂不启用)。

    P2 模板仅 1 开局帧样本(economy.md §10.2「待多局复核」),启用即冒险
    ——多局复核补 ``P2_NODE_TEMPLATE`` 后再实现,当前显式报错防误用。
    """
    raise NotImplementedError(
        'P2 节点模板证据不足(economy.md §10.2 待多局复核),校验未启用')
