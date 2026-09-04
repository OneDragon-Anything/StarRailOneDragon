# ADR-0458: DirectorV2 并行循环落地 + 生命周期六件套计数清零时机表(阶段2批②)

## 背景

期望态统一化阶段2批②(W571 任务书;设计素材 = W561 审计报告 §三.1/§三.7):新框架循环
DirectorV2 以「快照驱动 decide(snapshot, session) -> Decision」契约并行落地。六件套
(步数预算/stall 门/连败→恢复→屏蔽/defer 计数/bail 同因计数与 ping-pong 停机/W209j
停机刹车)自 prep_director 现役环迁入时,**计数清零时机本身是历史事故现场**——局 47
死循环(r366b)根因即「环入口清零让计数永不到门」,清零时机错 = 行为漂移。故逐件
写明「何时清零/何时不清」,并以「表=代码」一致性进锁。

## 决策

**件 1(循环形态)**:`decision_v2/director_v2.py` 纯循环引擎 + 端口注入
(decide/observe/execute/recover/force_battle/is_stopped/stop_with_evidence/
record_defect 八端口,构造期显式注入),出口为 `LoopOutcome` 值(BATTLE/
BATTLE_FORCED/BAIL/PINGPONG_STOP/BRAKE_STOPPED/EVIDENCE_STOP/FAIL);到
SrOperation 轮次语义的映射归批③适配器(循环↔外环边界,W561 §三.9)。规则中立:
框架只消费 op_key(屏蔽/幂等键)与 domain(同域批校验),不解释 op 语义;
现役类型特判(ClickSpheres 例外/defer 门 max 抬升/DeployMove 失败记忆)不迁框架,
归批③经 session.reject_ledger 回灌(W561 攻击4 修法通用化)。本批纯新增未接线、
不开开关、prep_director 零行改动。

**件 2(六件套清零时机表,权威表)**:

| 件 | 载体 | 何时清零 | 何时不清 |
|---|---|---|---|
| 1 步数预算 | 引擎内 steps | 环入口(run 重入) | 局级不清、步间不清 |
| 2 stall | 引擎内 stall | 环入口 + 任一 op progressed 即清 | 失败/拒绝路径不清(正是要计的零进展) |
| 3 连败链 | fail_counts/blocked/recovered | 环入口重建 + 恢复发放清 fail_counts[key] + 屏蔽落定清 fail_counts[key] | recovered/blocked 环内存活不清 |
| 4 defer | session.defer_count | 环入口清 | 步间不清(门=2 需跨步累积);失败链抬升用 max |
| 5 bail 同因 | session.bail_reason_counts | **只增不清;唯一清零点 = 外环 handler 成功消化(battle_loop._clear_bail_count,仅成功才清)** | 环入口清零会让 ping-pong 检测永不可见(r366b 同型错误) |
| 6 W209j 刹车 | 非计数 | 无清零动作(start_running/stop 既有框架语义) | 双查点(环顶 + execute 前)每步现读,不缓存 |

**件 3(新语义,D1-D5)**:非 confident 分类有界重试(CONF_RETRY_LIMIT=3,对齐 gate
3-strike)→ EVIDENCE_STOP 留证停机接口位;批语义同域校验 + fail-stop + 批内轻/批尾
heavy(单 op 批 = 批尾 heavy,等价现役每步 heavy);空批 = 合法零进展计 stall;
LoopOutcome 值出口;屏蔽豁免条目(现役 StartBattle 豁免属类型知识)挂批③对账。

**件 4(对设计的检查点后补全)**:恢复无效分型「关过已知弹层 → 弹层顽固 → bail」按
recover 端口 closed_known 通道落框架(规则中立,无需类型知识);编排者批准设计时
骨架未展开此分支,补全不改变六件套时机表,行为与现役分型一致。

## Considered Options

- 形态:①纯引擎+端口注入、出口为值(采纳——零 IO 可离线锁,轮次语义后置批③)
  ②继承 SrOperation 直接落节点(绑死轮次框架,六件套与 SrOperation retry 语义纠缠,
  无法并行对拍)③复制 prep_director 整环改名(把类型特判/破墙链一并继承,规则中立失败)。
- 清零表落点:①ADR 权威表 + 时机锁「表=代码」(采纳)②只写代码注释(锁不住漂移,
  r366b 教训)③保持现役行为不写表(时机决策隐式,批③切换无对账基准)。
- 类型特判:①框架不迁、reject_ledger 回灌通道归批③(采纳)②按 op_key 前缀猜类型
  (字符串协议,静默漂移)③全迁框架(规则中立破约)。

## 影响

- 新文件面:director_v2.py + test_cw_w588_director_v2.py(行为锁 11 条 + 时机锁 2 条,
  全绿);contracts.py 只 import 零修改;现役循环/识别链零触碰,默认零行为影响
  (纯新增未接线,decide 无实现体,无热路径)。
- 批③挂账:适配器+开关+对拍;op 枚举与 prep_actions 对账;屏蔽豁免;reject_ledger
  回灌通道;start_battle 类 op 与 BATTLE 出口的映射。

## 验证

- 新锁 14(test_cw_w588_director_v2:正常步/defer/bail+ping-pong+异因不清/非 confident
  有界重试与留证停机/刹车双查点/步数预算/stall 门双向/连败链三分型/fail-stop 批/
  跨域批/空批 + 时机锁环入口表/环内清点表),全绿;CW 域全集与 ruff 结果随批交付记录。
- 时机锁断言「引擎计数由 run() 环入口清零重建,不预设」——预设计数被清零正是表语义本身。
