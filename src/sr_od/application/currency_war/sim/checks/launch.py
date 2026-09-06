"""达标臂发射短路·反假阴性哨兵(sim 决策下沉两小批②)。

背景(sim 决策下沉选型建议书,.debug/temp/currency_war/sim_sink_adjudication/
选型建议.md 裁决 = 方案三混合):生产达标臂发射帧**短路备战动作链**
(金不花);两小批② 之前 sim 只记观测键、决策照常跑金照花 ⇒ 金出口族
改动在严格同池 A/B 的 ledger 上 pre/post 逐位一致 = **结构性假阴性**
(form_ok 镜像族无写者同族事故,已两次实证)。本哨兵把该缺口变成检查器
可抓的回归面:发射帧上行为消费缺位(short_circuited 分键缺失 / 决策
动作仍在跑 / 金仍在花)即红。守卫移除(engine_p1 短路接线被拆)⇒
发射帧恢复旧「决策照常」形态 ⇒ 本检查恒红,防回归。
"""
from __future__ import annotations


def check_sim_launch_short_circuit(ledgers: list[list[dict]]) -> dict:
    """发射短路行为哨兵(批级;吃全批账本)。

    帧级判据(launch 非 None 的行,全部须满足):
    - ``launch['short_circuited'] is True``——行为消费分键在位(旧观测
      面形态无此键 = 两小批② 接线被拆,红);
    - ``row['actions'] == []``——发射帧零决策动作(生产短路语义;若
      发射帧仍在跑商店决策,则金出口族 A/B 的 pre/post 回到逐位一致 =
      假阴性形态,红);
    - ``row['sim']['spend']`` 全零——发射帧金不花(sell_income 亦零:
      卖出通道只来自决策动作)。

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
            if row.get('actions'):
                game_bad = True   # 发射帧决策动作仍在跑 = 短路失效
            spend = (row.get('sim') or {}).get('spend') or {}
            if any(_spend_gold(v) > 0 for v in spend.values()):
                game_bad = True   # 发射帧金仍在花 = 假阴性形态
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
    buys 非空同样落「金照花」红。"""
    if isinstance(v, dict):
        return sum(int(x or 0) for x in v.values())
    return int(v or 0)
