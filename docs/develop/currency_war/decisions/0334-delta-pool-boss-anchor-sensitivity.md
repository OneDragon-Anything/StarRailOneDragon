# 0334 - Δ池扩容:boss 桶真值锚 + sim 敏感化验证(W73)

- **Status**: accepted(2026-08-25;0305/0306 登记的扩容前置兑现——语料
  增量实机到位,本批不改策略代码与池 schema,改的是校准层数据地基与
  锚)
- **Context**:0306「Δ池扩容总闸已解锁但语料零增量,真扩容靠实机跑局
  攒 outcomes」——今夜实机 5 局补齐:outcomes 284 行(新增 45,
  含 5 boss 真值行:r9 hp_after 1/40/1/13/12,killed 全 False)。
  0305 登记的「池胜判定口径差(killed vs Δ)扩容批一并修」与
  W70「hp 持平=sim 战斗层不敏感(已知边界)」的边界是否随扩容松动,
  本批一并验证。**数据治理先判**:5 局×9 行完整 P1,node_type 全在
  映射表(普通战斗/遭遇/奖励/补给/boss),board_before 齐,killed
  空值=r6 battle 已知未捕获模式(19/80 同族),**零坏行零隔离**;
  无 QUARANTINED 命中。
- **Decision**(五件):
  1. **件1 先验重跑 + 核心键数据就绪判定**:precheck v2 输出——
     可信标签配对 239 行(全 core 可判 239/239,target_comp 87
     v2:jizi_train/56 feiying_joy/其余混合);按 (node, depth,
     core) 分桶,达标(各 ≥10)核心键:**battle depth9/12 ×
     core0/1/2**(14/25/12/29/12)+ **boss (12,1) n=10**(boss 桶
     首次有 core 维达标桶)+ reward 若干。**判定:数据量已支持扩
     core 维,但 Δ池 schema 无 core 维**(扩=sampler 版本 bump+
     采样键语义变+消费点更新,独立 schema 批)——本批按现有
     schema 只做数据扩容,boss 桶真值锚;core 键扩容立项登记
     (下一批,证据=本先验)。
  2. **件2 boss 桶真值锚(现有 schema 入桶)**:5 boss 行按 depth
     桶入池(Δ=-20/-34/-24/-34/-34;深度 9/12/13/13/11 → 桶9×2/
     桶12×3);快照重生成 46066bbe(sampler v7 内容扩容,语义不变):
     battle rung 0/1/2 = **53/47/14**(旧 40/31/9);boss 桶 9/12/15
     = **4/15/8**(旧 2/7/8);encounter 33 / reward 65(恒 +2 不变)。
     **sim n=100 r9 boss 掉血分布 vs 实机**:实机 mean -29.2/
     median -34(5 行);sim 扩容后 mean -22.9/median -24——**sim
     仍系统性低估 boss 伤害 ~6hp**;根因=**sim r9 深度 15-19(桶15
     为主)vs 实机 boss 深度 9-13(桶9/12)错位**——sim 进 boss 时
     板面比实机深一个桶域,采样域不匹配(校准面信号,非池数据病)。
  3. **件3 口径统一复审计(killed 权威)**:ADR-0306 已裁决 killed 为
     唯一权威口径;本批在全量 284 语料复审计(生成器配对口径):
     battle killed 已知配对 **84 行异号 0**(rung0 0/40、rung1
     0/35、rung2 0/9)——0305 登记的「同 9 行 3 行异号」=tier×
     core 与 rung 两分桶错位伪影,扩容后仍成立;生成器 note 更新
     (0/84,防再引用旧 0/61 口径)。
  4. **件4 sim 敏感化验证(扩容前后同 seed 同代码 n=100,仅池变量)**:
     - **battle 层部分敏感出现**:rung0 -11.9 vs rung1/2/3
       -4.9/-5.0/-4.2(未成型每场多掉 ~7hp;扩容前 rung0 -11.5 vs
       rung1 -5.3 已有雏形,扩容后 rung1/2/3 收敛)——「未成型更
       痛」的敏感度在 battle 节点**已现**;
     - **boss 层仍不敏感**:r9 delta × 引擎数 0/1/2/3 = -23.4/
       -22.3/-23.2/-23.4(扩容前 -24.2/-23.2/-23.7/-25.1,持平)
       ——boss 结算键是 **depth 非 rung**(schema),引擎数只经深度
       弱相关进入,扩容不改变这一点;
     - **hp 基线随池校准修正(同 seed)**:hp_ge_60 0.01→0.10、
       avg_final_hp 24.68→27.93(池更真实,校准修正非策略变化;
       W70 报告「hp 持平」的语义是 A/B 双臂持平,与池校准修正
       正交);
     - 池级检查扩容前后同违规形态(coverage 0 违规/rung 锁 0/
       reward 锁 0;min_n 4 与 depth_cliff 1 为既有披露型红,
       depth_cliff 旧池同样红=非新增)。
  5. **件5 语料缺口量化清单(boss 敏感化还差什么)**:
     - **boss rung 条件桶**:boss 对引擎数敏感的前提=boss 结算
       rung 化(schema 变更)或 boss 胜负面 rung 条件化——实机
       boss 行 rung 标签仅 5 行(r0×2/r1×2/r2×1),每 rung ≥10
       需 ~40 局;rung 条件化前 boss 敏感度不可测(sim 侧观察面
       boss_win_curve_sample_gate 已披露);
     - **sim↔实机 boss 深度错位**:sim r9 深度 15-19 vs 实机
       9-13——即使桶有数据,采样域不同步使伤害对照失真;需
       sim 板深行为对齐(部署收敛/买牌密度)或对照按深度域匹配
       (登记为校准面下一件);
     - **battle rung2 均值非单调**(rung1 -5.4 vs rung2 -6.7,
       n=14):损失严重度混入均值;敏感度判读以 **killed 胜率维
       度**为准(rung0/1/2 = 0/0.54/0.67 单调);rung3/4 桶仍缺
       (0 行),rung≥3 成型局样本需攒。
- **Considered Options**:
  1. **core 键直接入 schema(本批做)**:否决——采样键语义变
     (battle key → (rung,core))=_SAMPLER_VERSION bump+消费点
     更新+测试重写,超出「按现有 schema 入桶」范围;先验证明数据
     达标,登记为下一批(证据在本批报告)。
  2. **boss 结算键 depth→rung(本批做)**:否决——schema 变更+
     实机 boss rung 样本 5 行远不足(每桶 ≥10 需 ~40 局);本批先
     把 boss 桶数据攒厚,条件化等样本到位(件5 量化)。
  3. **锚不重记(维持 6c0c8397)**:否决——池内容变锚必须跟随
     (ADR-0306/0312 先例),否则检查网 anchor_registry_n300 永久
     披露指纹失配,跨批基线核对失去锚点。
- **验证**(新池 46066bbe90647c02,采样器 v7 内容扩容;单进程串行;
  报告 `.debug/temp/currency_war/cw_dev/w73_*`):
  - 先验:precheck_delta_core_key.py v2(239 配对,core 全可判);
  - 口径复审计:84 killed 已知行异号 0(脚本 w73_pool_diag.py);
  - 扩容预演+池级检查对照:生成器 build_pool 全量 + 旧池 JSON 备份
    回测(coverage/rung_lock/reward_lock 双态 0 违规;min_n/depth_
    cliff 既有红不变形态);
  - 敏感度:同 seed n=100 前后配对(w73_sens_before/after.json);
  - 新锚:n=300 seed 0-299(hp_ge_60 0.08 / avg_final_hp 28.69 /
    battle_losses_le_2 0.11 / engines2_by_r6 0.33 / recipe5_by_r6
    0.67 / avg_refreshes 2.36;旧 6c0c8397 锚 0.05/27.97/0.11/
    0.38/0.72/2.31 标注失效=池校准修正);checks_violations 无
    本批新增红(既有:dead_system 144 / equip_value_strategy_key_
    coverage 300 / carry_on_shelf 7 / degrade_recover 8 / engine_
    seed_not_resold 1 / min_n 4 / depth_cliff 1 / endgold 1);
  - 测试:121 定向(快照/池/锚族)全绿 + ruff 通过;CW 全子集见
    批收账(全量 pytest 欠账延续)。
- **Consequences**:
  - 正:boss 桶首次真值锚(9/12/15 = 4/15/8);口径统一全量复审计
    0/84;battle 未成型敏感已现(rung0 vs formed ~7hp/场);hp
    基线随池校准修正(hp_ge_60 0.08@n300);核心键扩容数据就绪
    证据入档;W70「hp 持平」边界定位收敛——battle 层松动、boss
    层仍封,缺口量化清单明确;
  - 负/风险:①boss 敏感化需 rung 条件桶(样本 ~40 局+ schema 批);
    ②sim↔实机 boss 深度错位(校准面登记);③锚重记在 W72 在飞树
    (合流后按 anchor drift 披露复验);④battle rung2 均值非单调
    (判读以 killed 胜率维为准)。
