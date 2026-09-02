# 01 · 简报 op / 开局序列 / 位面切换

> W971 分篇。总纲见 [../DESIGN.md](../DESIGN.md)。

## 1. BriefingOp:简报观察收敛为单 op

简报画面(货币战争-简报,含 P1 开局简报与 P2/P3 位面简报同族)唯一入口:

- 观察:词缀/敌人难度/三 boss 序(`cw_briefing_obs` 现有读法);
- 写局状态:session.briefing_affixes / enemy_difficulty / briefing_bosses(替代 ctx 信箱与 0a0b 内联写);
- 动作:点「下一步」;完成承诺 = DD-011(固定时长或判稳标志,#1 口述「锚出现后 ~1s 动画完结」);
- 兜底补采(session 空时位面详情补采)并入本 op 重试形态,不再散落第二写入点;
- 简报 vs 位面详情对账(reconcile_briefing_vs_plane_intel)保留,消费局状态;
- 遥测:exogenous briefing 事件随 op 迁移,语义不变。

## 2. 开局序列独立于主循环

**1-1 之前的整段固定流程拉出 battle_loop 主循环**,作为独立的开局编排单元——跑完(1-1 备战就绪)才交常态循环。battle_loop 瘦掉开局分支(位面简报 0a0b、位面过渡点空白、开局投资环境段),只保留本职:常态循环(备战决策 ↔ 战斗 ↔ 结算)+ 局中不定时 overlay 的按画面分发(遭遇/补给/巨星/伙伴/投资策略——节点类型决定出现时机,必须留 loop)。

```
开局编排(P1,进对局后一次性):
BriefingOp(简报观察+写局状态+点下一步;#1 锚后 ~1s)
  → PlaneTransitionOp(位面过渡,点空白;#2 提示出现即点)
  → InvestEnvOp(投资环境 3 选 1;现 handle_invest_env)
  → WaitOneOneOp(特殊:1-1 开局动画等待 ~10s)
  → 1-1 备战 → 交备战循环(PrepDirector)
```

- **顺序依据**(screen_flow_timing #1→#2→#3,#5/#29):简报点「下一步」→ 位面过渡(#2「点击空白处继续」提示出现 = 完结)→ 投资环境(#3 标题出现 1s 内三卡稳定)→ 进 1-1(**触发开局补给,动画长且无结束标志 → 用户裁定特殊等待 ~10s,值待校准**;1-1 **不自动开商店**)→ 1-1 备战。
- **WaitOneOneOp 形态**(用户两选项取独立 op):插在 InvestEnvOp 之后,固定时长等待(DD-011 形态①);不给备战循环加「现在是 1-1」的特殊状态参数。
- **投资环境仅开场一次**(#11:开场 1-1 前弹投资环境,1-3 后起局中弹投资策略,两画面不同 handler)——InvestEnvOp 只在开局编排;局中投资策略 = overlay handler 由 loop 按画面分发。出现规律不需精确建模:画面识别分发,出现即处理。

## 3. 位面 2/3 切换:同款 op 复用,编排挂结算后

- **打完 boss(1-6/2-6)后只有位面过渡,没有投资环境**;位面过渡 op 与 P1 复用。位面简报屏(P2/P3,三 boss+词缀)是 BriefingOp 同族输入。
- 编排位置:boss 结算 op 的后继序列(结算完成 → 流程层识别进入新位面 → BriefingOp(位面简报)→ PlaneTransitionOp → 2-1 自动开商店 → 交备战循环)。
- 与 1-1 的差异:2-1/3-1 **自动开商店**(无 WaitOneOneOp;开店完成判定按 DD-011 两形态,场景①口径)。
- 现有 handler op(handle_invest_env/invest_strategy/encounter/supply/megastar/partner)保留为画面 op 纳入编排;**位面过渡/开局补给补 op**。
