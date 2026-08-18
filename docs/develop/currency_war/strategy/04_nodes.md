# 04 节点与事件决策

> 备战核心循环之外的每局必遇决策点:投资卡选择 / 遭遇难度 / 补给 / 巨星 / 伙伴。本篇:`cw_events` + `cw_survey19_hooks` + `cw_difficulty_account` 及 handler 接线。模式统一:**read 选项 → 调策略函数 → 点选中项**(非硬编码默认)。

## 1. cw_events:事件决策函数

- **decide_event(投资策略/环境 3 选 1)**:pick_value 评估(ADR-0143/0144)——经济效果走台账/pick_value、战力效果走选卡分、与 target_comp 的阵营/装备件亲和(`ENV_COMP_AFFINITY`/`AUGMENT_COMP_AFFINITY`,M1「资源入口」);用户 `strategy/env_priority/forbid` 偏好轴参与打分。
- **decide_encounter(遭遇难度三选)**:评分 = 词缀契合(mechanics_fit,全分支克 comp → 刷新换批)+ 难度档定价(经 `encounter_tier_score` 包装难度账本 `marginal_value` 三态 + P1 尖峰;「阵容足够强才敢难」,碾压敢难白拿奖励 / 边际保守保血 / P3 永避高难 ADR-0130)+ 奖励价值(文本启发分档,与敢难联动)。
- **decide_supply(补给选装备)**:决策链 = 带钻(红/蓝/财富宝钻)直选 → 无钻且刷新未用 → 点刷新重掷(P8)→ 刷过按 `target_comp.key_equips` 契合 + 通用装备价值选。钻识别双通道(SIFT 模板主 / OCR 装备名兜底)。

## 2. cw_difficulty_account:难度账本

难度「可算可读」的记账层(ADR-0199):恒等式(基础难度 + 词缀 + 持卡修正 + 连胜通胀,残差桶对账)+ `marginal_value`(难度差的三态钟形定价 + P1 尖峰——A8 一层遭遇常比 boss 凶 + 地板衰减 + 溢出守卫);`from_strategies` 从持卡注册表建账(伟大征服「难度+连胜」类耦合不漏)。消费口:decide_encounter(经 survey19 包装)、boss 血量参照(`1.052^难度`,competitors.md)。

## 3. cw_survey19_hooks:二轮扫描落地件

三件纯函数决策件(离线可测):遭遇接难度账本(§1)/ 狼狩穿戴纪律(M16 用户修正版,03 §6)/ 补给重刷判据(§1 P8)。`cw_events` 消费。

## 4. 巨星与伙伴

巨星 = comp 引擎 × 乘区绑定(选择序详 [02 §7](02_comp.md));伙伴选择(HandleSelectPartner)决策输入受限(候选为立绘无角色名,需 SIFT 立绘库),当前按 core/build_around 命中兜底。祈愿试炼(HandleWishTrial)naive 首张。

## 5. 决策点接线表(handler → 策略函数)

| 决策点 | 策略函数 | 执行 op |
|---|---|---|
| 买牌/升/刷/deploy/卖 | plan → decide_prep_action | PrepDirector + prep_actions |
| 投资策略/环境 | decide_invest(→decide_event) | handle_invest_strategy / handle_invest_env |
| 遭遇 | decide_encounter | handle_encounter |
| 补给 | decide_supply | run_supply_node(含刷新流) |
| 巨星 | decide_megastar | run_megastar_node |
| 伙伴 | decide_partner | handle_select_partner |
| 武装箱选卡 | 执行器默认(key_equips→材料通用性) | handle_armory_box |
| 祈愿试炼 | naive | handle_wish_trial |

## 6. 边界

- 品质→难度通胀量级无本地数据(API 无记载,ADR-0205 裁定放弃建模);难度账本 quality_inflation 因此开环。
- 扑满识别(遭遇小怪含扑满=奖励更高)待扑满图模板。
