# 采晶矿(CollectOre)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。**本动作 = 逻辑随机态的首个落地**(随机采样契约权威版本 = `cw_merge_simulate.py::_merge_bench` docstring)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名,单一源在代码。

## 1. 动作是什么

点击备战画面奖励面板的晶矿,点开后掉落奖励即时入账。op 载体 = `operations/cw_op/cw_collect_ore_action.py::CwActionCollectOreOp`;动作类型(`kernel/cw_vocab.py` 清单中的类)= `CwActionCollectOreParam`(`points` = 按点击序的晶矿心坐标列,批式多点)。发出条件 = 备战策略产出 CollectOre(点击列由决策侧现算)。

## 2. 逻辑随机态域集(全部随机态)

**掉落规则 = 临时建模口径 v0**(用户 2026-09-20 临时敲定,非核实游戏事实,待采集校准;常量面 = `kernel/cw_ore_reward.py`,披露键 `ORE_ASSUMPTION_KEYS`):点开晶矿 = 金币/装备/角色 三选一(等概率假设)。金币 1–5;装备 = 简易装备池(category='简易')均匀;角色 = 按 `REFRESH_PROB[level]` 抽费用档、档内均匀抽名,星级恒 1。已登记冲突调和(fields §4.2「箱」/wandi「稀有物」)与容错论证此前已在设计稿中裁决(原设计稿已删,结论以本节为准)。

**上报函数内真掷随机、按采样结果走完整确定性链,全部状态容器(GameState)(GameState,游戏状态对象,下同)写标随机态**(`write_logic_rand`,source=logic_rand):

| 域 | 写 | 值 |
|---|---|---|
| spheres | 写 | 被点晶矿逐点坐标摘除(整表;终值依随机链而变——后续晶矿开否取决于采样奖励耗席,属采样状态副本(GameState)) |
| gold | 写 | 抽中金:现值 +N(N ∈ 1..5);未抽中:值不变标记 |
| equips | 写 | 抽中装备:现值 +[采样件];未抽中:值不变标记 |
| bench | 写 | 抽中角色:落备战席首空槽(采样值)+ 3合1 连锁逐级整表;未抽中:值不变标记 |
| front_row / back_row | 写 | 合成触及行域:每级受影响域各落一行(整表);未触及:值不变标记 |
| board | 派生 | 行写挂钩 `_resync_board_delta` 自动重算,**继承随机态**;增量为零不写(升星不改羁绊标签) |

None 域边界:值 None(未观察)的域跳写(留空不写、等观察覆盖)不标记;抽中类型域值 None → 跳采样写等观察(诚实缺失)。

## 2.1 动作分支总览(非随机态域两条分支,整批写毕后收尾)

- **计数分支**:批内开成点数 `opened` 经 `gs.effects.record_ore_open` 单口入账(计数载体 = `kernel/cw_effect_inventory.py` 的 `ore_open_total`,不进快照 = 接管局从 0 起,接受面 = 刷新两计数同款)。「点开才计数」:席满/缺项∧level 缺读跳点不入账,`opened == 0` 早退路径零计数零触发。消费方 = 战技点契约触发器。
- **环境条件发放分支**(登记表 `cw_investments.ENV_ORE_OPEN_GRANTS` 已登记环境:战技点契约 id 128):计数入账后尾部触发 `kernel/cw_env_grants.check_env_ore_open_grants`——阈值序列(首阈值 20 + 步长 10,无限重复)逐阈值发放:火花 + 随机战技点羁绊角色各 1 个 1★(两条分支 `gain_character` 随机态写入——触发前提 = 晶矿开启计数为未验证推演,发放按随机态定级走台账纠偏 + bench 首观察覆盖,用户裁定 2026-10-17;随机分支采样经注入槽具名键 `env_ore_open_grant`,sim = 状态副本里的值 / live 回退自掷),done 键 `ore_open#<阈值>` 逐阈值封账(`write_logic` 簿记;fields.md §3.5.5 词表行)。
- **窗序确定**:晶矿自身奖励写(含合并升星触发分支)→ 计数入账 → 战技点契约触发分支(计数先入账后检查,检查时计数现值含本批);触发发放与晶矿奖励同动作窗同组。

## 3. 转移规则(逐点顺序推演)

载荷逐点遍历,每点:①守卫——该点时备战席无空位(含前点角色奖励耗席累计判)→ 晶矿留在 spheres、不采样;②spheres 摘除;③`roll_ore_reward(rng, level)` 采样;④按抽中类型应用(上表);⑤evidence 带点序 `#ore<k>`,合成级 `proj_ore_merge#<级>#ore<k>`,同动作同组 group_id。**逐点推演的席满分支由采样奖励决定 → spheres 终值属采样状态副本**(随机态依据)。

机械执行半不变:载荷即点击列,纯机械逐个点、零读屏;固定等待 2s 等飞行动画。

## 4. 观察收尾(最终以观察为准)

下一帧观察覆盖:真值与随机态值一致的域等值采新零行;不一致的域出 `logic_rand_outcome` 记录行(预期内,不触发失配告警)。实机 = 猜测被校准(逐局积累 `logic_rand_outcome` 行 = 采样口径 v0 的校准数据源);sim = 采样即状态副本里的值(无观察,零行)。

## 5. 拒绝语义

- 整批拒(零写):spheres 未观察(现行为 `applied=True` 诚实缺读)/载荷无交集(现行为)/`bench_unobserved`(席满守卫与角色落点均不可判,`applied=False`)/`level_unread`(角色采样需当前等级,`applied=False`);
- 逐点跳过:该点席满 → 晶矿留在 spheres(出参见下);
- 动作级出参:全部开成 = `applied=True`;混合批 = `applied=True, 'ore_partial_open_skipped'`;全部席满跳过 = `applied=False, 'bench_full_no_open'`。

## 6. kernel 符号锚

`kernel/cw_action_report/collect_ore.py::report_action_collect_ore_param`(采样+逐步随机写单点);`kernel/cw_ore_reward.py::roll_ore_reward` + `ORE_ASSUMPTION_KEYS`(采样器常量面);`kernel/cw_merge_simulate.py::_merge_bench(on_step=…)`(合成链步回调);`kernel/cw_prep_actions.py::select_ore_clicks` / `ore_click_targets_of`;`operations/cw_op/cw_collect_ore_action.py::CwActionCollectOreOp`。

## 7. 语义验证

写序/来源/标记测试 = `test_cw_collect_ore_rand.py`(多点逐点/席满即止/三分支/双域合并行/None 边界/sim 接入调用);采样器支撑集与种子复现同文件;状态容器摘除分支存量测试 = `test_collect_ore_container_precise_drop`(已更新随机态契约);合成链步回调 = `test_cw_merge_step_callback.py`。

## 8. 先例注记(动作发出阶段)

备战期(奖励面板只在备战画面;动作发出点 = 备战策略 `strategies/impl/mandate_v1/entry.py` prep_spheres,席满搁浅走策略侧 defer 计数)。商店期无本动作。**策略消费门(后续迭代)**:备战环见 `logic_rand_fields()` 非空 → 发 `CwActionObs` 环内重观察。

## 9. 依据

`kernel/cw_action_report/collect_ore.py` docstring(逐点推演+随机态全表);`kernel/cw_ore_reward.py`(临时口径 v0 常量面+假设档披露);`kernel/cw_merge_simulate.py::_merge_bench` docstring(步回调契约);[flow/action_ops.md](../../flow/action_ops.md) §4.2 CollectOre 行;[fields.md](../fields.md) §3.2.8(晶矿)/§4.2 CollectOre。
