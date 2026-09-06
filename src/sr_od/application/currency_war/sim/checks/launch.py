"""达标臂发射短路·反假阴性哨兵(sim 决策下沉两小批②;裁决 = ADR-0557;
批 1 哨兵改造裁决 = ADR-0566)。

背景(docs/develop/currency_war/decisions/0557-sim-sink-launch-criteria-
kernel.md):生产达标臂发射帧**短路备战动作链**;两小批② 之前 sim 只记
观测键、决策照常跑金照花 ⇒ 金出口族改动在严格同池 A/B 的 ledger 上
pre/post 逐位一致 = **结构性假阴性**。本哨兵把该缺口变成检查器可抓的
回归面:发射帧上行为消费缺位即红,守卫移除(engine_p1 短路接线被拆)⇒
发射帧恢复旧「决策照常」形态 ⇒ 本检查恒红。

**批 1 断言语义重推(非机械跟绿;出处 = 金出口族 DESIGN v1.1 §3.2/§5,
ADR-0566)**:发射帧仲裁段(出口 B)落地后,发射帧允许**受限消费**——
「金照花」旧红形态升级为「**决策段(自由链)零执行 ∧ 仲裁段外零消费**」:

- ``short_circuited is True`` 仍必查:发射帧短路分键缺位 = 旧观测面形态
  (ADR-0557 接线被拆),红——语义未变,短路的是自由决策链,仲裁段不是
  自由链;
- ``launch['arbitrage']`` 披露必查(批 1 新增):缺披露 = 仲裁段接线被拆
  (回到批 0 金不花形态)= 假阴性回归面复活,红;
- 带内帧(zone='inband_failclosed'):fail-closed 锚 = 动作空 ∧ spend 全零
  (L1' 证不出不花),违者红;
- 溢出帧(zone='overflow'):允许仲裁消费(动作/花费可非空),但 P70 预算
  不变量必查:``gold_after ≥ g_star``(花穿息线部分出辖 = p70 边界 1;
  合并多买等投影外成本破线 = 红路径响亮暴露,禁静默);
- zone 值域闭集 {'overflow','inband_failclosed'},域外值 = 引擎披露漂移,红。
"""
from __future__ import annotations

#: 发射帧仲裁披露 zone 值域闭集(引擎写入面单一值域,哨兵与判读共用)。
_ARBITRAGE_ZONES = ('overflow', 'inband_failclosed')


def check_sim_launch_short_circuit(ledgers: list[list[dict]]) -> dict:
    """发射短路行为哨兵(批级;吃全批账本)。

    帧级判据(launch 非 None 的行,全部须满足):
    - ``launch['short_circuited'] is True``——行为消费分键在位;
    - ``launch['arbitrage']`` 披露在位且 zone 在值域闭集内(批 1 新形态;
      缺失 = 仲裁接线被拆,红);
    - 带内帧:``row['actions'] == []`` ∧ ``row['sim']['spend']`` 全零
      (fail-closed;卖出通道只来自决策动作,亦零);
    - 溢出帧:动作/花费允许(仲裁消费本体),``gold_after ≥ g_star`` 预算
      不变量必查(破线红)。

    批级判据:存在发射帧但全批零短路帧 = 行为消费整批缺位,红。

    返回 dict(violations = 违规局数;games = 违规局索引前 5,seed 重放
    定位 = simulate_p1(seed_base+idx) 同 _BATCH_CHECKS 惯例)。
    """
    bad_games: list[int] = []
    launch_frames = 0
    short_frames = 0
    for idx, rows in enumerate(ledgers):
        game_bad = False
        for row in rows:
            launch = row.get('launch')
            if launch is None:
                continue
            launch_frames += 1
            if launch.get('short_circuited') is True:
                short_frames += 1
            else:
                game_bad = True   # 分键缺位 = 行为消费缺位(旧观测面形态)
            arb = launch.get('arbitrage')
            if not isinstance(arb, dict) \
                    or arb.get('zone') not in _ARBITRAGE_ZONES:
                game_bad = True   # 仲裁披露缺位/漂移 = 接线被拆(批 1 新形态)
                continue
            spend = (row.get('sim') or {}).get('spend') or {}
            if arb.get('zone') == 'inband_failclosed':
                if row.get('actions'):
                    game_bad = True   # 带内帧动作非空 = fail-closed 破
                if any(_spend_gold(v) > 0 for v in spend.values()):
                    game_bad = True   # 带内帧金仍在花 = fail-closed 破
            else:
                g_after = arb.get('gold_after')
                g_star = arb.get('g_star')
                if isinstance(g_after, int) and isinstance(g_star, int) \
                        and g_after < g_star:
                    game_bad = True   # 溢出帧花后跌破 g* = P70 辖域破(响亮暴露)
        if game_bad:
            bad_games.append(idx)
    batch_bad = launch_frames > 0 and short_frames == 0
    if batch_bad:
        bad_games = list(range(len(ledgers))) or bad_games
    return {'violations': len(bad_games), 'games': bad_games[:5],
            'launch_frames': launch_frames,
            'short_circuited_frames': short_frames,
            'note': ('全批发射帧零短路帧(行为消费整批缺位)' if batch_bad
                     else '发射短路行为消费在位'
                     if launch_frames else '零发射帧(数据边界,不判)')}


def _spend_gold(v) -> int:
    """spend 位真金量展平:buys 位 = {通道: 金} 嵌套 dict(引擎记账原形
    ``_spend['buys'][reason] += gold``),其余位 = 标量。混合形状统一
    求和——嵌套位走标量 int() 会 TypeError 崩掉整批报告(落地审阻断
    项:恰好发射帧 buys 非空才触发 = 红路径崩成非结构化),展平后嵌套
    buys 非空同样落红。"""
    if isinstance(v, dict):
        return sum(int(x or 0) for x in v.values())
    return int(v or 0)
