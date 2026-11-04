# 采晶矿(CollectOre)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。**本动作 = 逻辑随机态的首个落地**(随机采样契约权威版本 = rcw_merge_simulate.py::_merge_benchr docstring)。符号名引用路径根 = rsrc/sr_od/application/currency_war/r。数值只写常量名,单一源在代码。

## 1. 动作是什么

点击备战画面奖励面板的晶矿,点开后掉落奖励即时入账。op 载体 = roperations/cw_op/cw_collect_ore_action.py::CwActionCollectOreOpr;动作类型(rkernel/cw_vocab.pyr 清单中的类)= rCwActionCollectOreParamr(rpointsr = 按点击序的晶矿心坐标列,批式多点)。发出条件 = 备战策略产出 CollectOre(点击列由决策侧现算)。

## 2. 逻辑随机态域集(全部随机态)

**掉落规则 = 临时建模口径 v0**(用户 2026-09-20 临时敲定,非核实游戏事实,待采集校准;常量面 = rkernel/cw_ore_reward.pyr,披露键 rORE_ASSUMPTION_KEYSr):点开晶矿 = 金币/装备/角色 三选一(等概率假设)。金币 1–5;装备 = 简易装备池(category='简易')均匀;角色 = 按 rREFRESH_PROB[level]r 抽费用档、档内均匀抽名,星级恒 1。已登记冲突调和(fields §4.2「箱」/wandi「稀有物」)与容错论证此前已在设计稿中裁决(原设计稿已删,结论以本节为准)。

**上报函数内真掷随机、按采样结果走完整确定性链,全部状态容器(GameState)(GameState,游戏状态对象,下同)写标随机态**(rwrite_logic_randr,source=logic_rand):

| 域 | 写 | 值 |
|---|---|---|
| spheres | 写 | 被点晶矿逐点坐标摘除(整表;终值依随机链而变——后续晶矿开否取决于采样奖励耗席,属采样状态副本(GameState)) |
| gold | 写 | 抽中金:现值 +N(N ∈ 1..5);未抽中:值不变标记 |
| equips | 写 | 抽中装备:现值 +[采样件];未抽中:值不变标记 |
| bench | 写 | 抽中角色:落备战席首空槽(采样值)+ 3合1 连锁逐级整表;未抽中:值不变标记 |
| front_row / back_row | 写 | 合成触及行域:每级受影响域各落一行(整表);未触及:值不变标记 |
| board | 派生 | 行写挂钩 r_resync_board_deltar 自动重算,**继承随机态**;增量为零不写(升星不改羁绊标签) |

None 域边界:值 None(未观察)的域跳写(留空不写、等观察覆盖)不标记;抽中类型域值 None → 跳采样写等观察(诚实缺失)。

## 2.1 动作分支总览(非随机态域两条分支,整批写毕后收尾)

- **计数分支**:批内开成点数 ropenedr   rgs.effects.record_ore_openr 唯一入口入账(计数载体 = rkernel/cw_effect_inventory.pyr 的 rore_open_totalr,不进快照 = 接管局从 0 起,接受面 = 刷新两计数同款)。「点开才计数」:席满/缺项∧level 缺读跳点不入账,ropened == 0r 早退路径零计数零触发。消费方 = 战技点契约触发器。
- **环境条件发放分支**(登记表 rcw_investments.ENV_ORE_OPEN_GRANTSr 已登记环境:战技点契约 id 128):计数入账后尾部触发 rkernel/cw_env_grants.check_env_ore_open_grantsr——阈值序列(首阈值 20 + 步长 10,无限重复)逐阈值发放:火花 + 随机战技点羁绊角色各 1 个 1★(两条分支 rgain_characterr 随机态写入——触发前提 = 晶矿开启计数为未验证推演,发放按随机态定级走台账纠偏 + bench 首观察覆盖,用户裁定 2026-10-17;随机分支采样 注入槽具名键 renv_ore_open_grantr,sim = 状态副本里的值 / live 回退自掷),done 键 rore_open#<阈值>r 逐阈值封账(rwrite_logicr 簿记;fields.md §3.5.5 词表行)。
- **窗序确定**:晶矿自身奖励写(含合并升星触发分支)→ 计数入账 → 战技点契约触发分支(计数先入账后检查,检查时计数现值含本批);触发发放与晶矿奖励同动作窗同组。

## 3. 转移规则(逐点顺序推演)

载荷逐点遍历,每点:①守卫——该点时备战席无空位(含前点角色奖励耗席累计判)→ 晶矿留在 spheres、不采样;②spheres 摘除;③rroll_ore_reward(rng, level)r 采样;④按抽中类型应用(上表);⑤evidence 带点序 r#ore<k>r,合成级 rproj_ore_merge#<级>#ore<k>r,同动作同组 group_id。**逐点推演的席满分支由采样奖励决定 → spheres 终值属采样状态副本**(随机态依据)。

机械执行半不变:载荷即点击列,纯机械逐个点、零读屏;固定等待 2s 等飞行动画。

## 4. 观察收尾(最终以观察为准)

下一帧观察覆盖:真值与随机态值一致的域等值采新零行;不一致的域出 rlogic_rand_outcomer 记录行(预期内,不触发失配告警)。实机 = 猜测被校准(逐局积累 rlogic_rand_outcomer 行 = 采样口径 v0 的校准数据源);sim = 采样即状态副本里的值(无观察,零行)。

## 5. 拒绝语义

- 整批拒(零写):spheres 未观察(现行为 rapplied=Truer 诚实缺读)/载荷无交集(现行为)/rbench_unobservedr(席满守卫与角色落点均不可判,rapplied=Falser)/rlevel_unreadr(角色采样需当前等级,rapplied=Falser);
- 逐点跳过:该点席满 → 晶矿留在 spheres(出参见下);
- 动作级出参:全部开成 = rapplied=Truer;混合批 = rapplied=True, 'ore_partial_open_skipped'r;全部席满跳过 = rapplied=False, 'bench_full_no_open'r。

## 6. kernel 符号名引用

rkernel/cw_action_report/collect_ore.py::report_action_collect_ore_paramr(采样+逐步随机写单点);rkernel/cw_ore_reward.py::roll_ore_rewardr + rORE_ASSUMPTION_KEYSr(采样器常量面);rkernel/cw_merge_simulate.py::_merge_bench(on_step=…)r(合成链步回调);rkernel/cw_prep_actions.py::select_ore_clicksr / rore_click_targets_ofr;roperations/cw_op/cw_collect_ore_action.py::CwActionCollectOreOpr。

## 7. 语义验证

写序/来源/标记测试 = rtest_cw_collect_ore_rand.pyr(多点逐点/席满即止/三分支/双域合并行/None 边界/sim 接入调用);采样器支撑集与种子复现同文件;状态容器摘除分支存量测试 = rtest_collect_ore_container_precise_dropr(已更新随机态契约);合成链步回调 = rtest_cw_merge_step_callback.pyr。

## 8. 先例注记(动作发出阶段)

备战期(奖励面板只在备战画面;动作发出点 = 备战策略 rstrategies/impl/mandate_v1/entry.pyr prep_spheres,席满搁浅走策略侧 defer 计数)。商店期无本动作。**策略消费门(后续迭代)**:备战环见 rlogic_rand_fields()r 非空 → 发 rCwActionObsr 环内重观察。

## 9. 依据

rkernel/cw_action_report/collect_ore.pyr docstring(逐点推演+随机态全表);rkernel/cw_ore_reward.pyr(临时口径 v0 常量面+假设档披露);rkernel/cw_merge_simulate.py::_merge_benchr docstring(步回调契约);[flow/action_ops.md](../../flow/action_ops.md) §4.2 CollectOre 行;[fields.md](../fields.md) §3.2.8(晶矿)/§4.2 CollectOre。
