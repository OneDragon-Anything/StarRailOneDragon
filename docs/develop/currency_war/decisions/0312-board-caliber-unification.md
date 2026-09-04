# ADR-0312: 羁绊口径统一(全集+星徽装备贡献)与 Δ池桶键对齐

- 状态:accepted
- 日期:2026-08-25
- 背靠:W49 口径全量审计(leader 裁决 1/2/3,阻塞项)+ W47 条2 裁决①。
  涉及文件面与 W48(同名守卫)合并为联调修复批 W50。

## 背景与动机

W49 审计实锤三处系统性口径分裂(细节见 `W49_报告.md` §1 Q4):

1. **board 双口径并存**:实机 `board_from_tracked` = 全集
   (factions+flows+independent,开拓者按排归一);sim `state.board`
   (`_recount_board`/`_board_counts_of`/DeployMove `board[faction]+=1`)
   = 主阵营单标签——双阵营角色/流派角色/独立羁绊全被压成主阵营一个,
   同一局面 sim 每羁绊计数 ≤ 实机。
2. **星徽羁绊贡献三处全缺**:22 张星徽「装备者加入【X】羁绊」+
   欢愉卡带「已是成员计数+1」+星核猎手卡带「羁绊计数+1」装备后
   左面板该羁绊行 +1,是面板真值的一部分;`tracked_deployed[].equips`
   数据在手(deploy_bench 读回)但零消费 → computed_vs_ocr 常态化
   误报 + 星徽局档位系统性低估。
3. **Δ池桶键混口径**:池语料板深 = Σ(decisions.state.board)(实机
   全集口径,双标签角色每人贡献 ≥2);sim 采样键
   `_deployable_depth = min(level, len(deployed))`——同一局面两侧
   落不同桶,采样系统性偏浅;battle rung 输入 board_before 同病
   (sim 侧 `_board_factions_of` 缺 independent)。

## 决策

1. **口径单一源**:新建 `cw_bond_equips.unit_bond_tags(bc)`——
   per-unit 羁绊标签多集(L1 全集 + L2 星徽装备贡献),三处统计
   同函数:实机 `board_from_tracked`、sim/状态派生 `_recount_board`
   (= `cw_sim._board_counts_of` alias)、checks 镜像
   `_board_agg_of_deployed_row`。未识别身份回退 `faction` 字段
   单标签(实机侧整体 bail 语义不变)。
   - 卡带净效果语义:欢愉卡带「加入羁绊,若已是成员则计数+1」=
     **无条件 +1**(成员佩戴者对该羁绊贡献 2 = 自身 1 + 卡 1,
     「一人一标签」上限的唯一突破机制);实现为逐装备追加标签,
     不做成员条件分支。
2. **DeployMove 保持增量语义**:board 可来自 OCR 真值而 deployed
   尚空(生产 read_game_state 填充序),全量重算会抹掉 OCR 计数
   (W50 实测踩坑:`test_plan_buys_synergy_push` 红)——DeployMove
   分支用 unit_bond_tags 做**增量** `+=`;SellDeployed/SwapDeploy/
   CompTransaction 维持全量重算(动作 v2 域 board 恒为 deployed 派生)。
3. **sim equips 回写**:equip_allocation 结果写回 `BenchChar.equips`
   (防重守卫),装备随人进账本行 deployed——星徽贡献在 sim 局内
   可涌现(生产 tracked_deployed[].equips 同语义)。
4. **桶键统一**:`_deployable_depth` 改 Σboard(全集口径,与池语料
   同口径,无 level 上限——池侧同样无);`_settle_rung` 输入改
   `_recount_board`。`_SAMPLER_VERSION` 6→7;快照 META 指纹重算
   (6c0c8397f3f38a58,池内容不变仅版本变);`ANCHOR_REGISTRY_N300`
   锚重记(n=300 seed 0-299 snapshot)。
5. **W47 条2(选项①)**:W16 过半统计入注册表
   `cw_plugins.W16_MAJORITY_LINES`(12 张:8 骨架件 + 4 边界卡;
   家族键去重——绯英/银狼两线同归欢愉族);单卡插件
   `majority_lines` 从该表程序同步(单一写入口,旧部分标注被覆盖);
   `CROSS_LINE_SKELETON` 改派生(`cross_line_skeleton()`:≥3 线过半
   +恰 2 家族过半且非线级 carry),快照测试锁 == 原 10 名。
6. **检查网随动**:`formation_hp_coupling_sentinel` 小批护栏 <5→<20
   (v7 后 n=25 两度噪声假红[formed_n=2 / 13:12 侧 −4.11],
   同批 n=300 真判 +5.39 绿——护栏对齐判据原意「真批次 n≥300 判定」,
   判定力不减)。

## Considered Options

- **A(采纳):三侧同函数单一源 + DeployMove 增量**——口径漂移窗口
  关死(任一侧改标签函数自动传导);增量语义保住 OCR 真值路径。
- B:DeployMove 也全量重算——实测抹掉 OCR 提供的 board 计数
  (legacy plan 路径红),否决。
- C:sim 侧维持独立 `_board_counts_of` 主阵营口径、只改采样键——
  state.board 消费方(recipe 门/意向②信号)仍读窄口径,与实机
  判读分叉,W49 Q4 的主病没治,否决。
- D:卡带按「已是成员」条件分支加两份——对卡面文本过度解读
  (净效果恒 +1),且引入成员判定时序依赖,否决。

## 后果

- 正面:board 语义三处一致且对齐游戏左面板真值;星徽局
  computed_vs_ocr 误报源消除;Δ池采样与池语料同口径(消系统性
  偏浅);跨线骨架名单脱锚风险消除(W45 判定)。
- hp 类锚下移属预期(avg_final_hp 32.08→27.97:同局面落更深的
  encounter/boss 桶 → 更真实战损);策略侧近零漂移
  (engines2_by_r6 0.39→0.38 / recipe5_by_r6 0.71→0.72);
  avg_refreshes 3.87→2.31(板面集中买门读全集 board,行为面
  变化——预期内,判读注意与旧锚不可裸串比)。
- **遗留(报 leader 对拍)**:n=300 涌现边缘违规
  `engine_seed_not_resold`(1/300,g188)/`carry_on_shelf_responded`
  (2/300,g243/296)——行为面随口径变化的涌现信号,裁决归联调批。
- L3(装备 props 强度/投资环境效果进战力评估层)不在本 ADR,
  归 win_model 迭代(W49 裁决 4)。

## 回归验证

- 新增 `test_cw_w50_board_caliber.py`(14 锁:装备贡献解析/22 星徽
  全覆盖/unit_bond_tags 全集+未知+开拓者/三侧同函数/DeployMove
  增量/Σboard 桶键/W16 表值锁/派生==原 10 名/插件同步)。
- 过期锁更新(逐条判「主阵营语义[更新断言] vs 巧合依赖[修复]」,
  明细见 W50 报告 §口径前后对照):r410 board 两锁(语义)、
  system_cards `_state_with_deployed` 补丁循环删除(语义——全集
  后双计)、r343/r390 depth 源锁(语义)、adr0292/r409 版本锁
  (7)、action_v2 两处(语义:r390 补丁/agg 同源化)、r413 哨兵
  双向锁(护栏语义)。
- ruff 全过;currency_war 全目录 1621 passed;全量 2156 passed
  (sim_uni 1 例顺序敏感偶发红,单跑绿,非本批面)。
- 锚重记:n=300 seeds 0-299 snapshot,指纹 6c0c8397f3f38a58。
