# 2026-09-18-screen-op-flat-report

## 文档
- 设计总纲:[design.md](design.md)
- 落地:[landing.md](landing.md)

## 进度
- 迭代设计:定稿(用户七轮裁定代行对抗,2026-09-18 会话)
- 设计对抗:收敛(用户逐项裁定:①基类废弃+独立类+obs+report;②多 node+对账段去除;③round_wait+on_outcome 退役;④无防御上限;⑤刷新计数出辖,动作 op 侧另会话;⑥report 与动作上报统一模块级函数族 report_screen_*_obs;⑦kernel/cw_screen_report/ 包每画面一文件 obs+report 同居,推进型也拆,cw_game_state.py 零触碰)
- 落地:阶段 0/8 done(明细见 landing.md)
- 正本更新:未开始

## 协调注记
- 动作 op 侧(`cw_op/` 动作执行体、ActionOp 契约、apply_*_action_logic 族、`kernel/cw_action_report/` 包)由另一会话并行改动中;本迭代不触碰。**该会话同时在改 `cw_screen_buy_cards.py`(商店 op)与 `sim/`**——T-5 涉及买牌前先对账在飞面,冲突即停手上报。
- 刷新计数(encounter_refresh_used/strategy_refresh_used)写端模型由用户转达动作 op 会话;本迭代 on_outcome 钩子随基类退役,过渡态缺口用户已知悉。
