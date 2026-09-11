"""【退役墓碑 2026-09-04】V̄ 合成价值链(v_bar_net /
window_vbar / per_battle_value / streak_floor_gold)整链退役。

退役原因(用户裁定,2026-09-04):
- **禁胜率建模**——V̄_net = Δp[plane]×单战价值×r 的全部因子端
  (win_rate_dp_by_plane 分位面胜率边际、vbar_hp_value_transitional
  伤害金折算)都是统计拟合量,不属游戏定义量;
- **刷新决策改路径总账比较(形式二)**——R1 启动门比较项改
  ``c_eff·E(D|L*) + Σ卡费 + L(g, spend, R, Ī) ≤ g − g*``(全游戏
  定义量:REFRESH_PROB 池参数 / XP 表 / 息律),判据本体 =
  criteria/refresh.r1_commitment_account,装配 = shop.py R1 段;
  P57 搜索窗门(读法①/②)随 V̄ 退役消解,窗口判据重锚塌缩带
  (statefn/odds.tier/card_search_window,ω 锚,ADR-0475 同源)。

消费端处置:R1 门消费位(shop.py)与 P57 搜索窗消费位
(shop.py/_frame_search_windows、statefn/odds)已在本批改接新判据,
本模块无生产消费端;``streak_floor_gold`` 无其他消费端(grep 定夺,
仅本模块与既有测试引用),随链一并退役——连胜金流真源 =
cw_economy.STREAK_GOLD_TABLE(表值不动,其他消费不受影响)。

史料:增量 B 重推导与修订单 R1 见 math_proofs P53 行(已加退役标注);
因子处置史(rung_value/h3_win_rate/expected_battle_loss 清退)——三因子同属统计拟合量,已随早期因子清退批退役(理由见上)。
"""
