# ADR-0530: 板满换阵补部署(M1″)——kernel swap 计划谓词单一源 + 发射位 seam 门 + 卖出通道统一义务集排除

## 裁决期限(2026-09-06 补,策略审查第 36 跳)

seam 门(`cw4_m1p_seam_verified`)缺省关属合法开关形态,但按开关生命周期
第三档须挂核销期限:第二十/二十一局连续两局「bench 成型不上板、deployed
恒满」=本 ADR 所治形态的实机代价已两现,开闸核对小批(两侧输入逐字段
对齐证据)随即立项;对齐证据齐 + 置位验收判据(实机 m1p_* 读数)达成
即核销本期限。超期未决 = 违规,处置 = 置位或退役关。
【核销回记 2026-09-06】前置已兑付(fresh 生产写点接线 5edcf324+对齐证据
m1p_seam_alignment/对齐证据.md 随档),seam 门已置位 True;**实机验收判据
第二十三局(run_045436)三过**:m1p_fired=2(≥1)、m1p_input_seam_pending=0、
sell-offtarget 执行侧闭环 4 次(g_20260906_045436 复盘 §2)。期限核销完成,
回滚路径保留(M1P_SEAM_VERIFIED 写回 False 单点恢复)。

## 背景

板满(cap 达)帧 M1/M1′ 的 vacancy 门压住部署发射,bench 里的更好 target 件当轮坐板凳
(核实报告病灶 C 边界 A);换阵卖出臂(`_sell_offtarget_deployed`)只在 CwOpDeploy 执行
时运转,且其 victim 判定长期缺买面义务集排除——P60 已证伪的「卖义务件↔买回」换手循环
在 swap 通道无防线。

方案经两轮无前提对抗收口(REVISION R1/R2,过程要点已并入本文对应节;过程文档为会话产物不入库):
R2 四阻断钉死①输入快照契约(装配源 = 执行侧 last_state+SIFT 链,同批迁移)②fenced 臂
判据迁 kernel(禁第三源)③上序 = 对卖出后假想态复用 `select_deployments` 的组合语义
(零新启发式)④sim 只建模发射意图面(双向断言)。实施批前置 sim 离线频率探针
(n=300 局/2700 帧,计划非空占比 0/2700):sim 的部署代理在轮末自动上阵,把「板满∧bench
线内件滞留」形态结构性消解——**该形态 sim 不可测,效果判定只在实机可达**。据此裁决:
基础设施保留,M1″ 发射位 fail-closed 关闭,效果判定挂实机。

## 决策

1. **kernel swap 计划谓词单一源**(`cw_deploy_logic.select_swap_plan`,与
   `select_deployments` 同族纯函数):
   - 板满门 = 占用数口径(`len(deployed)`,含 SIFT 未识别占位件;禁 `len(deployed_cids)`
     衍生集,与执行侧「禁用衍生计数」同向);
   - victim 资格 = `offtarget_sell_allowed`(W209 语义只消费不修改)+ **义务集∪新鲜度
     排除单一判定** `swap_sell_exclusion_reason`(buy_membership / fresh_buy);
   - 上序 = 对卖出后假想态复用 `select_deployments_reasoned`,底线留置件不作上序候选
     (拒因 `post_sell_held`),「白卖一件板面变弱」在谓词内不可达;
   - 双弃权键 fail-closed:`cap_unreadable` / `membership_unreadable` ⇒ 计划空
     (dd-037「留 bench 合法稳态」不对称口径)。
2. **共享输入装配函数**(`assemble_swap_plan_inputs`):发射侧(mandate M1″)与执行侧
   (CwOpDeploy 卖出臂)**同函数、同一装配契约,输入源两侧分轨**(发射 = 决策帧黑板,
   执行 = last_state + SIFT——装配源契约钉死为执行侧卖出决策实际消费的快照链)。
   fenced 臂判据(`fenced_swap_arm_of`/`swap_arm_deployed_count`)随迁 kernel,
   operations 桶副本归零(re-export 兼容)。
3. **执行侧排除接线**(§6.1 辖域表 swap 行「执行侧同步接线」兑付点):卖出臂逐候选经
   `swap_sell_exclusion_reason` 判定——买面义务集成员/轮内新鲜买入件禁卖,P60 换手
   循环在执行路径同受保护;义务集缺读 ⇒ 全候选禁卖(fail-closed)。分键
   `deploy_swap_sell_excluded_<拒因>` 逐件显影。
4. **M1″ 发射位 + seam 门**:挂 mandate 骨架 pass M1′ 后,发射 `RunDeploy`
   (`m1_swap_redeploy`,条件续类不触发截断);同帧 LevelUp 抑制(`m1p_defer_levelup`:
   升级开新 vacancy,下帧 M1′ 零卖出成本接管)。发射门 `session.cw4_m1p_seam_verified`
   **缺省关** = 发射关闭、`m1p_input_seam_pending` 显影;唯一写点 = 两侧输入逐字段
   **对齐证据**核对完成后的开闸小批(只置位不算核对)。分键族:`m1p_fired` /
   `m1p_plan_empty` / `m1p_cap_unreadable` / `m1p_membership_unreadable` /
   `m1p_input_missing` / `m1p_defer_levelup` / `m1p_input_seam_pending`。
   【键表追加,T-167(F-8):`m1p_no_direction` / `m1p_no_bench_target`——换阵可
   兑现谓词(`swap_realizable`)的 plan 级弃权键,层位 = plan 级弃权(与本节既有
   分键同族),不并入逐件拒因闭集;显影语义见 ADR-0534 修订节。】
5. **新鲜度排除载体取舍**:发射位写入(`cw4_swap_fresh_buys`,phase 键式,逐名入集),
   过度排除(被截断器丢弃的买入意图也入集)方向安全;fresh 降格为防抖+显影辅助,
   单调性由义务集排除独立承载(不宣称构造性切环)。
6. **sim 意图面**:`engine_p1.m1p_intent_record` 行内观测键(零 rng/零状态写入),
   双向断言(计划空⇒无意图 ∧ 非空⇒有意图);sim 不建模执行卖出语义,如实申报不可信。
7. **验证阶梯**:单帧锁 15+ 条(`sr-od-test/test_cw_swap_plan.py`,锁基础设施语义非发射
   行为)+ 快速集全绿;效果验收 = 实机(`m1p_input_seam_pending` 非零率 = 开闸小批
   立项门槛),sim 正向 A/B 不适用(探针实证)。

## Considered Options

- **发射门方向**:a) cap 缺读帧 fail-open(R1 边界 B,撤回——依据引用违反持久索引纪律);
  b) fail-closed 弃权+分键(选定,与 M1/M1′ vacancy=0 门同向,双门一致);
  c) 观测面 admission 升级为闸(违反「准入是观测面非第二道闸」契约,admission 零改动)。
- **fenced 臂判据落点**:a) 驻 operations,kernel 谓词自写 fp∧板满组合(第三源,
  r271 批同型双源复发);b) 迁 kernel + re-export(选定)。
- **sim 验证**:a) 正向 A/B(两臂恒等,零证伪力,撤回);b) 只记意图+双向断言
  (选定)+ 前置频率探针(0/2700 触发数据裁决)。
- **发射时机**:a) 立即开闸(执行侧排除当时未接线 → P60 环敞口 + 输入未对齐);
  b) seam 门缺省关,对齐证据+开闸小批前置(选定)。

## 后果

- 正面:swap 通道卖出资格与部署发射共享同一谓词与排除判定(第三源清零);P60 换手
  循环在发射、执行两路径同被关闭;板满帧 bench 线内件滞留形态获得可归因显影面
  (拒因逐件 + 分键族),开闸决策有数据门槛。
- 代价/边界:发射位在开闸前恒不发(`m1p_input_seam_pending` 计数即板满形态出现率)——
  留 bench 是合法稳态(dd-037),零行为风险换输入对齐义务;fresh 排除过度抑制合法
  swap(方向安全,拒因可追溯);EV 凑息卖通道的义务集排除核对仍挂账(REVISION_R1
  §6.1);sim 探针数据与门归因要点已并入「探针」节(数值只在代码)。

## 锁面

`sr-od-test/test/sr_od/app/currency_war/test_cw_swap_plan.py`(基础设施语义锁,
docstring 逐条引本文与 dd-037);`test_cw_deploy_ops.py` 的 fenced 臂真值表锁经
re-export 同一性锁(`test_fenced_arm_single_source_identity`)继续覆盖。
