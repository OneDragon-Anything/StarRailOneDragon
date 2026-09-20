# 晶矿掉落规则(临时建模口径 v0)

> 定位:备战画面晶矿(奖励球)点开后的掉落规则在册口径。**证据分级 = 用户临时拍定(2026-09-20),非核实游戏事实**——整套规则是自动化建模的临时工作口径,后续按实机采集数据校准(校准数据源 = 自动化随机态收口台账 `logic_rand_outcome` 行,逐局积累「采样值 vs 实读真值」对照)。
> 建模落点 = `src/sr_od/application/currency_war/kernel/cw_ore_reward.py`(常量面,采集优化只改常量与披露键);设计正本 = `docs/develop/sr_od/application/currency_war/changes/2026-09-20-logic-rand-sampling/design.md`。

## 口径 v0

- 点开一颗晶矿 = **金币 / 装备 / 角色** 三选一(等概率,假设键 `ore_type_uniform`);
- 金币:1–5 随机(均匀,假设键 `ore_gold_uniform_1_5`);
- 装备:**简易装备池**均匀一件(装备注册表 category='简易' 全集,8 件);
- 角色:按当前等级查商店概率表(`REFRESH_PROB`,Lv1-10 实机 OCR 权威表)抽费用档、档内均匀抽一名,星级恒 1★(假设键 `ore_char_star1`);
- 不受轮岗翻倍档影响(假设键 `ore_no_rotation_tier`)。

## 在册记载对照(未调和差异,采集校准的核对清单)

- `screen_flow_timing.md` #16(实机观察):晶矿去向「奖励角色→备战 / 金币→商店 / 装备→右侧装备栏」——**与三形态口径一致**;
- `fields.md` §4.2 CollectOre(旧记录层陈述):「角色/**箱**落席占 1 槽」——箱形态 v0 不建模,采样错形态时观察收口兜底;
- `final_comps/final_wandi_burn.md`:「晶矿(金币/角色/装备/**稀有物**)」——月光精华层效果语境的晶矿,稀有物形态 v0 不建模。

## 席满交互

席满时点击晶矿无效、无法开启(用户拍定);批式点击中前点奖励耗尽席空位后,后续晶矿同样点不开——未开的晶矿留在画面,由后续观察回补、下轮再派(`screen_flow_timing.md` #16 在册裁定同源)。
