# ADR-0534: 转型臂(M1″ swap 谓词触发域扩展)——锁线后线未成型板满帧的 bench→板 换血通道

## 背景(病灶)

M1″ 基座(ADR-0530)与成型臂(`fenced_swap_arm_of`,fp≥1.00 门)都不辖
「锁线后 fp<1.00 转型期」:板满帧 fenced victim 全被 W209 熔断
(`offtarget_sell_allowed` 引擎/配方体系件恒不卖)拒 ⇒ victim 空 ⇒
bench 上的锁线核心件持续坐板凳、deployed 恒旧线过渡件,换血死锁。
实机两次线事实:连续两局「锁 列车同行 → 三月七 2★+姬子·启行 bench
成型、deployed 恒 6 过渡件、3 备战轮未上板」(对局档案
g_20260906_021859 P2r2-r4 与 g_20260906_005259 同型,复盘归 ADR-0530
期限核销记录同一批实机证据)。

设计经五轮无前提对抗收口(设计载体为会话临时文档,过程要点并入本文;
判据源 = 宪法/玩法文档/注册表直调,残留两条纯文字批注随实施批兑付)。

## 决策

1. **触发域(追加资格族,基座/成型臂零修改)**:
   `locked ∧ fp<1.00 ∧ 板满(占用数) ∧ 存在逐件守卫合格的 fenced
   victim ∧ 卖出后假想态上序 ∩ target 视图 ≠ ∅ ⇒ 发射`。
   locked = `ist.locked_comp` 非空(锁线布尔单源,定谳见
   strategy-docs/17_stall_form_spend_authority.md §1.1——成型门
   fp≥1.00 不是锁线门);fp 缺读 ⇒ `fp_unreadable` 弃权(两臂同
   fail-closed);守恒门全拒帧 = 两臂全关静默(合法稳态,非臂失效)。
2. **逐件守卫(资格族拒因闭集)**:
   - `engines_guard` 档位守恒门:体系档表 `SWAP_GUARD_SYSTEMS` =
     `GUARD_SYSTEM_TIERS` ∪ 护盾(`FACTIONS['护盾'].tiers` 注册表
     消费,零硬编码档),模块级断言体系集 ⊇ DEPLOY_FENCE(熔断替代
     论证承重前提);逐体系 achieved 档数(卖出后 vs 卖出前)不减,
     希儿系 = 单卡二元判定 `seele_system_formed`(自 engines_count
     提出,engines_count 与守恒门同吃,禁第二实现);
   - `merge_material_guard` 合成素材守卫:victim 含自身全场域同名同星
     计数 = 2(合成定义值 3 的未完态,注册表派生零自由参数)⇒ 拒——
     卖 v 使 2★ 合成进度 2/3 退 1/3;计数 ≤1 帧概率残差不在辖域
     (fail 向 = 不换);
   - `star_guard` 1★ 限卖(全退金前提,星级不可读 fail 向 = 不换);
   - `target_keep` / `fp_unreadable` / `fenced_arm_closed` 沿用旧键。
3. **判定函数内聚(单一交汇点)**:守恒门/素材守卫/回滚常量的消费点
   全部落回 `cw_deploy_logic.swap_sell_exclusion_reason` 函数体或其
   唯一调用链——发射面(`select_swap_plan`)与执行面
   (`_sell_offtarget_deployed`)同吃本函数,新资格族语义只实现一次,
   发射⇔执行资格自动同值,分轨态被结构性关闭。基座/成型臂经本函数
   参数化接入 `offtarget_sell_allowed`(本体零修改);admission/W209
   本体不动(W209 熔断在未锁全域保持)。
4. **执行侧逐件放行**:swap 装配在场时,`_sell_offtarget_deployed`
   逐候选消费单一判定函数(per-piece 布尔/拒因,禁退化为标量
   fenced_on 喂入——标量形态在 fp<1.00 帧恒 False = 新资格族整体
   不可达的缺口根源);资格族拒因经 `deploy_swap_sell_rejected_*`
   分键逐件显影(零静默);`fenced_arm_closed`∧fenced 件保留 W209
   留证。swap_ctx 缺读退旧路径(排除链静默关闭)为在册遗留缺口,
   原样继承未扩大,收缩候裁另案。
5. **胜出序与 arm 标注**:现行 victim 序(1★ 优先,并列取现行序首个)
   取首个可成交者,`plan.arm` 随胜出者资格族标注('base'/'formed'/
   'transition');禁新排序键、禁 fenced 提权;转型臂附加卖后上序
   target 视图底线(拒因 `post_sell_offline`),base/formed 臂维持
   现状判 up 非空。
6. **双开关切割**:转型臂回滚 = 单点常量 `SWAP_TRANSITION_ARM_ENABLED`
   (缺省开,落码即活跃;翻 False 仅关本臂——消费点在判定函数内,
   发射/执行自动同关,无「发射关执行开」分轨态);seam 门
   (`cw4_m1p_seam_verified`)是 M1″ 基座开闸载体,不作为转型臂回滚
   路径(写回会连坐基座)。删码时同删常量,无永久悬置。
7. **分键**:发射面 `swap_arm_transition_trigger` /
   `swap_arm_formed_trigger`(plan.arm 消费)+ 拒因五键
   (engines_guard/star_guard/merge_material_guard/post_sell_offline/
   fp_unreadable)帧级显影;执行面 `deploy_swap_sell_rejected_<拒因>`。
8. **seam 对齐增量**:对齐证据表(m1p_seam_alignment/对齐证据.md)增
   15/16/17 行——`ctx.fp`(form_progress 单一源,同帧同值,None 两臂
   同弃权)/`ctx.locked`(locked_comp 非空,同函数同式)/`plan.arm`
   与资格语义(发射侧判合格 ⇒ 执行侧同函数必同判),随实施批入表。
9. **支配论证**:B_t(板面 target 视图承重计数)严格增 + 五体系达成
   档不减(守恒门承接)+ 金不减(1★ 全退)⇒ 弱支配;锁线期买面
   (locked_buy_membership 单一源)与卖出侧集合结构不相交,演进层
   素材面竞争由 merge_material_guard 封闭,垫件回流由既有观测覆盖。
   遗留缺口:单位级面板残差/B_t 无权重/素材概率性残差(计数<2 帧)。

## Considered Options

- **熔断替代形态**:a) 转型期整域解除 W209(连坐未锁帧,振荡敞口,
  否);b) 守恒门逐件放行,辖域绑定 locked=True(选定——精度更强,
  W209 在未锁全域保持);
- **守恒门触发态**:a) ∖{v} 同名同星 ≥2(合成恒律下不可达 = 死守卫,
  撤);b) 含 v 计数 = 2 未完态(选定,注册表派生零自由参数);
- **执行侧放行形态**:a) 标量布尔喂入(标量 = R3 缺口根源,否);
  b) 逐件布尔/拒因,同函数输出(选定);
- **回滚载体**:a) seam 门写回(连坐基座,否);b) 转型臂专属单点
  常量(选定)。

## 后果

- 正面:锁线转型期板满换血死锁获得治本出口;资格语义发射⇔执行单点
  同值(条件不变式对新资格族成立);拒因全显影可归因;双开关切割使
  回滚不连坐。
- 代价/边界:守恒门逐件求值新增 O(victim×体系) 纯函数开销(可忽略);
  fp 缺读帧转型臂关(fail-closed);守恒门全拒帧静默为合法稳态(判读
  按 engines_guard 分键区分于臂失效);素材计数<2 帧的概率性进度损失
  不在守卫辖域(显式模型缺口,fail 向 = 不换)。

## 锁面

`sr-od-test/test/sr_od/app/currency_war/test_cw_swap_transition_arm.py`
(病灶帧回放/守恒门/素材守卫/星级守卫/回滚常量/双臂互斥/胜出序/执行侧
同函数放行/mandate 分键/辖域不变式,docstring 逐条引本文节名);
`test_cw_swap_plan.py` 谓词锁面随资格族扩展更新(扩展向后兼容:非转型
帧行为逐位不变)。

## 修订(T-167,2026-09-08:换阵可兑现谓词单一源 + 用例预期更新)

发射⇔执行接缝在无方向态断裂(run_20260908_210431 实机软卡死:M1″ 发射
53 次幻影部署、执行 0 次真实换阵,交替活锁 15 分钟)——修复批把「换阵
可兑现」谓词单一源化到 kernel(`swap_realizable` 三合取:目标视图非空 ∧
bench 存在目标视图件 ∧ 板上存在其资格臂下可卖的 off-target 件;方案审
F-1 修订版),本文 §决策3「判定函数内聚」原则的同构延伸,对既有裁决的
影响如实申报:

1. **用例预期更新(原「计划非空」用例变「计划空」)**:无方向态
   (target 视图空,决策1 触发域此前不辖的形态)`select_swap_plan` 弃权
   `no_direction`;有向态 bench 无目标视图件帧弃权 `no_bench_target`
   (base/formed 臂「非目标件填空上序」是执行面必然空转的形态——发射→
   执行 no-op 变为弃权→空批出战,支配正确方向的行为变化,非零回归)。
   转型域触发域与资格族语义逐位不变(三合取门在 victim 扫描之前,
   扫描本身的逐件拒因显影保留)。
2. **fw_carry 口径收口(F-1③,择 kernel 含)**:bench 目标视图件判定
   单一源 = `target_view_char_is`(含 fw_carry),发射面 `_bench_is_target`
   与执行面旧 `_is_tgt_char`(不含)合并。依据:上序裁判
   select_deployments 的 is_tgt 含 fw_carry(框架件是部署一等公民,
   为其腾位可兑现)+ 卖出侧对本函数 fw_carry 板件 target_keep 保护
   (对称)。行为变化面:执行面 1:1 替换上限自此计 fw_carry bench 件
   (有向态可多卖一件 off-target 为其腾位)。
3. **执行面两门同吃**:CwOpDeploy 卖出臂前提改消费同一谓词合取支
   (合取②计数 + 合取③逐件判定);「板上无可卖 off-target 件」帧的
   卖出分支不再进入(旧形态进入后逐件拒卖 0 件——卖出行为等价,日志
   与臂态记账不再空转)。「装配不可得退型第二份目标视图派生」拆除
   (总图 §2.2 F-9 硬约束:只消费装配 ctx 字段)。
4. **分键追加**:`m1p_no_direction` / `m1p_no_bench_target`(登记 =
   ADR-0530 决策4 键表追加行)。
