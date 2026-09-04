# 0303 - 决策框架 v2 合流批(危机批常量上移 registry + copy_swap 守卫×目标件豁免)

- **Status**: accepted(2026-08-25;纯搬家隔离复验逐位一致;守卫豁免
  三窗小负贡献如实报,见验证节——豁免保留但登记下批裁决)
- **Context**:批㉞(供给 vs 标签审计)两发现清偿:①ADR-0302 危机
  批因「registry 为攻坚批(ADR-0301)在飞域,零文件交集纪律」把应急集
  补充标签(_EMERGENCY_EXTRA_TAGS)与危机三参(_CRISIS_HOARD_GOLD/
  _CRISIS_BUY_BIAS/_CRISIS_BUY_TAGS)暂驻 filters.py,违背 registry
  「单一注入点,禁止散落硬编码」的模块契约(ADR-0290),合流批上移;
  ②批㉞ M2 实证:在场目标件 2504 卡次中 20%(483 次)被 r410
  copy_swap 守卫拦截——守卫镜像的 deploy 侧保留判据(target_cores/
  target_factions)与 v2 层1 的目标件保护集(_target_names,锁线期
  并入全部桥 fixed∪core,ADR-0299)口径不同:目标件在 v2 保护集内
  =deploy 侧不会当 off_target 卖,守卫前提「在场副本会被卖」对该
  集不成立;且目标件第 2 份语义不同(3合1 素材/阵容深度,非换卡)。
- **Decision**(三件):
  1. **常量上移**(纯搬家,零值变化):emergency_tags 并入
     for_gold/levelup(ADR-0302 内容修正落位);crisis_hoard_gold
     (层2 节)/crisis_buy_bias+crisis_buy_tags(层3 节)进
     registry;filters/scoring 改读 registry,暂驻常量删除
     (锁:旧名残留即红);0293 hash 锁按流程更新
     (deaa0764→3446bf3c)。
  2. **copy_swap 守卫×目标件豁免**(candidates._copy_swap_blocked):
     卡名 ∈ _target_names 保护集时不走 _copy_swap_useless 守卫
     (目标件第 2 份=3合1 素材/阵容深度);非目标件照旧受守卫辖
     (v1 _copy_swap_useless 判据不动,v1 臂零影响)。批㉞检查项
     decision_v2_supply_label_consistency 的 blocked 谓词同步镜像
     (单一源=生成器 helper,检查器不复制判据)。
  3. **smoke 待裁登记清偿**:批㉜ F4 检查项
     equip_value_strategy_key_coverage(docstring 明示「裁决归策略域,
     裁决前恒红」)未进 smoke 豁免表致 test_ci_smoke_snapshot_batch
     红——按 ADR-0289 同款语义进 _PENDING_ADJUDICATION,策略域
     补值/裁决后移除回归 0 容忍。
- **Considered Options**:
  1. **豁免落 v1 守卫本体(_copy_swap_useless 内加目标集判据)**:
     否决——v1 是 A/B 对照臂,动 v1 = 基线漂移(三窗复验失锚);
     豁免属 v2 生成器层语义(保护集口径是 v2 的 _target_names),
     落 candidates 层。
  2. **豁免=守卫整体下线(483 次全放行)**:否决——守卫本意(防
     同名换同名纯耗,r410 局72 实证)对非目标件仍成立;豁免只做
     目标件名单交叉。
  3. **豁免后再 v2 目标集内细分(仅桥 core 不含 fixed)**:未采——
     批㉞ M2 口径是 _target_names 全集;细分无证据支撑,先按审计
     口径落地,效果由三窗/sim 裁决。
- **验证**(snapshot 池 066c41856dd5d4f5,v1 臂同进程配对):
  - **纯搬家隔离复验**(豁免关闭还原守卫):v2 三窗逐位复现
    ADR-0302 基线(34.27/30.27/34.27)——常量上移零行为变化 ✓;
    v1 臂三窗(31.27/29.27/34.00)与基线逐位一致 ✓;
  - **三窗 30+30+30**(anchor 0-29/fam_a 900000 族/fam_b 900030 族):
    gap(v1−v2)+1.67(SE 4.79)/−0.10/0.00——**anchor 出负值域**
    (基线 −3.00/−1.00/−0.27);豁免的确定性贡献(v2 同 seed 对比)
    anchor −4.67/fam_a −0.90/fam_b −0.27,**三窗一致小负**;单窗
    量级与窗口 SE 同量级(批间纪律:带内不叙述为效应),但方向
    一致——如实报:豁免未兑现批㉞「下批杠杆」预期;
  - 定向锁:0303 新锁 5 条(危机三参在 registry/应急集内容/暂驻
    常量已删/目标件豁免+非目标照旧拦)+0302 锁改读 registry+
    0293 hash 锁更新+0300 守卫锁原绿;currency_war 测试目录
    1342 通过 2 skip 1 xfail;ruff 通过;
  - **全量 pytest 未跑**(CPU 配额纪律):采样 66%/18%/63%
    (idle 均值 ~51% <70% 空窗线),按纪律跳过——全量欠账仍挂,
    下个空窗批补;本批以 currency_war 目录 1342 绿作最大子集。
- **Consequences**:
  - 正:registry 模块契约恢复(单一注入点无散落);批㉞ M2 交叉
    误拦清偿(生成器语义对齐保护集);批㉜ 待裁披露登记清账;
    sim 检查项谓词与生成器单一源化。
  - 负/风险:①守卫豁免 sim 三窗一致小负(anchor −4.67 主导),
    与批㉞预期相反——**登记下批裁决**:候选=豁免收窄(仅桥
    core)/评分侧补偿/回退(一行:守卫直通还原);裁决依据=
    豁免买的目标件副本事后去向交叉表(是否真成 3合1/上阵);
    ②gap anchor 窗回正(+1.67,基线 −3.00)但在 SE 带内,不构成
    「v2 落后」结论,下批 A/B 需含 anchor 窗复核;③全量 pytest
    欠账延续(CPU 空窗即补)。
