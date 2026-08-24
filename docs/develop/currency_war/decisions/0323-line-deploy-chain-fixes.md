# ADR-0323: 万敌锁而不投的部署链三修(演进去重 + flows 目标集 + 围栏序/跳过语义)

- 状态:accepted
- 日期:2026-08-25
- 背靠:W64 万敌锁而不投根因报告(意向→执行漏斗断链定位;模式 B 事务
  自重复拒 / Ring1 目标集残 / Ring5 围栏跳过与优先序两病)+ 口述
  [20](过渡是配方)/[21](final 件买而不上,变阵点窗)/[22](有用就先囤,
  囤度内 3合1 素材)+ ADR-0316(bench 槽位语义)。
- 落点:`cw_evolution.py`(`execute_replacement`)/`cw_intention.py`
  (`_line_hoard`)/`cw_deploy_logic.py`(`select_deployments`)/
  `cw_sim.py`(skip_fence 置位)/`cw_sim_checks.py`(配对锁语义)+ 对应测试。

## 背景与动机

W64 重放钉死「万敌锁而不投」= 买入通(9/11 局买到)但部署断(0/11 局上板),
断链四环:

1. **Ring4 模式 B(主断点)**:`execute_replacement` 部署名单构造
   (cw_evolution.py:374-383)把 bench 同名多副本**全量**进 deploy 名单
   (2+ 张万敌 → `deploy=['万敌','万敌',…]`)→ 终态 deployed 同名 →
   `duplicate_on_board` 整事务拒(cw_state.py:744-766,ADR-0317 不变量)。
   seed 81 实证 49 次可执行全拒,每轮每段刷屏;同 bug 非万敌专属
   (艾丝妲×2 同被拒)。
2. **Ring1 目标集残**:`_line_hoard`(cw_intention.py:431-435)阵营过滤只查
   `c.factions`,而**档位键常含流派系羁绊**(万敌单C form_tiers 燃血=
   flows;DOT 持续伤害/黄泉减益/击破/量子同频 同型)——燃血 8 成员中
   刃/镜流/布洛妮娅 的 factions 不含燃血(在 flows)被目标集排除,
   锁定线采购面 3/8 缺失。
3. **Ring5 围栏跳过语义**:`_explicit_deploy_seen` 对任何显式动作
   **无条件**置真(cw_sim.py:1187),被拒事务也 skip_fence
   (cw_sim.py:1300-1303)→ tier0 局围栏跳过 90 次/11 局——万敌
   唯一部署通道被事务风暴封死,板面欠载。
4. **Ring5 围栏优先序**:点火优先序(ignition 首键+桶序)把 ig0 的线核心
   排底部(万敌 ig0/tier_completes=0),cap 被同键过渡填充件
   (丹恒·腾荒×2)按 bench 序先占(seed 13 r5)。

## 决策

**修法一(演进事务按名去重)**:`execute_replacement` 的 `bench_new` 构造
**按 char_id 去重,同名取最高星一件上场**;其余副本**留 bench 作 3合1
合成素材,不卖**([22] 囤度内;合成进度需要副本在手)。去重键=char_id,
未识别(char_id 空)无法判同名,保留原样不折叠。根治
`duplicate_on_board` 整事务拒 + 每轮刷屏(W64 模式 B)。

**修法二(flows 并入目标集)**:`_line_hoard` 的成员判定改为
`(set(c.factions) | set(c.flows))` 与 `comp.form_tiers ∪ sub_tiers`
档位键作交集——「流派系羁绊成员进目标集」的**通用修正,非万敌特判**
(candidates/evolution 的 `_char_factions` 已是同式全集口径,对齐单一源)。
刃/镜流/布洛妮娅 等 flows 成员进锁定线囤货目标集。

**修法三(围栏部署序 + 跳过语义两修)**:
- 3a **被拒不跳围栏**:`_explicit_deploy_seen` 只在显式动作**真执行
  (applied)**时置位——被拒事务不消耗围栏,同轮围栏照跑(sim 侧;
  生产侧 grep 无 skip_fence 写入点,无需同修)。配对锁
  `check_skip_fence_pairing` 同步只数 applied 显式动作。
- 3b **线核心优先于过渡填充件**:`select_deployments` 的围栏序在
  tgt 内加「线核心优先位」——`target_cores` 成员(锁定 comp 的
  core_chars,sim/candidates 从 `session.target_comp` 注入)提到最前,
  序 = `core_tgt + ignite_rest + other_tgt + plain_rest`。
  平衡口径:过渡配方照常占位([20]),但**同 cap 内先核心后填充**
  ([21] 变阵点窗语义:锁定线核心在窗口优先上板),**不扩 cap**;
  非锁定局 target_cores 空 → 桶恒空,序不变;r404-A1「点火 > 冗余
  target」语义保留(core_tgt 之外的 tgt 仍在 ignite_rest 之后)。

## Considered Options

- **模式 B:拒收点打补丁(放行 duplicate_on_board)**——被否:W43
  A/B 实测 54% 轮同名重复是 board/factions 虚高污染源,场上同角色
  仅 1 是冻结不变量(ADR-0317);放行=数据污染,根在事务构造不该
  提议同名。
- **模式 B:演进提案端同名预过滤(不在 execute 去重)**——被否:提案
  门槛(在手≥2 档成型)本就需要副本计数,过滤提案会误伤 3合1 囤货;
  去重落在**部署名单构造**(执行侧)是唯一语义正确点——囤(副本)与
  上(单件)分层,对齐围栏 r404-A2 同名单语义。
- **Ring1:万敌特判名单(hardcode 刃/镜流/布洛妮娅)**——被否:
  燃血/持续伤害/减益/击破/量子同频 全部 flows 主档同型,特判名单
  随注册表漂移;全集判定(factions ∪ flows)是表示层根修,零维护。
- **围栏 3a:保持「发出即占通道」只在 sim 修围栏计时**——被否:
  skip_fence 的语义是「显式动作占用显式通道 → 围栏让位」,被拒事务
  未发生任何部署,**让位的前提不存在**;账本配对锁必须同语义,否则
  检查网与行为矛盾(每批误报)。
- **围栏 3b:扩 cap/强制上核心(不排队)**——被否:违反「不扩 cap」,
  且核心该不该上由围栏候选序裁决,不是强制;排队优先(先核心后填充)
  是 cap 竞争下的最小行为变化。
- **围栏 3b:只在 tgt 内部加线核心位(不动 ignite_rest 桶序)**——
  被否:seed 13 形态的点火/过渡填充件在 ignite_rest,tgt 内排序
  治不了「线核心 vs 点火填充件」的 cap 竞争;线核心桶提到
  ignite_rest 之前才兑现「锁定线核心优先于过渡填充件」。

## 影响

- `cw_evolution.execute_replacement`:同名多副本只部署最高星一件,其余
  留 bench(不卖);事务从「整拒」变「可应用」;`memory.last_deployed`
  随去重名单(回滚锚不变式不受影响)。
- `cw_intention._line_hoard`:锁定线/兜底线目标集含 flows 成员
  (锁定万敌线 → 刃/镜流/布洛妮娅 进集);买侧候选生成面扩大。
- `cw_deploy_logic.select_deployments`:锁定线核心(target_cores)优先
  上;非锁定局零变化;op 侧 `_deployment_order`(deploy_bench.py)未
  同步该维度——已锁线实机的围栏序与 sim 存在差异,归后续对齐批
  (ADR-0261 对齐纪律续)。
- `cw_sim` skip_fence 置位语义 + `cw_sim_checks.check_skip_fence_pairing`
  配对判据(applied-only):被拒轮不再 skip_fence,围栏照跑,账本
  `fence_skipped` 同语义。
- 测试:演进去重锁(2 张同名万敌 → deploy 无重复 + simulate applied +
  副本留 bench)、flows 目标集锁(刃/镜流/布洛妮娅 进集)、围栏线核心
  优先锁(cap 竞争 1 空位 → 万敌先于点火三月七)、配对锁变异改写
  (被拒事务不要求配对/被拒轮记 skip_fence=误记)。
- 行为面:W64 快验证 n=50 对照(tier0 率 33.3%→14.3%,万敌上板率
  33.3%→64.3%,同池指纹;方向性验证,数字带 n 与边界声明见 W65 报告)。
