# W836 · 件价值模型 Phase 1 实施批 REPORT

> 任务=W831 v2 设计落码(架构闭环后实施)+W833 三补丁落实;基线=主仓
> 4a2b3f27;主仓 commit=**48c42110**,测试仓 commit=**fb6eab5**。

## 1. 落码对照表(任务书范围逐条)

| 范围 | 落点 | 状态 |
|---|---|---|
| 模型模块 evaluate_piece → PieceValueBreakdown 纯函数 | `src/.../decision_v2/piece_value.py`(新):六字段齐备纯披露;同输入逐位相等/零副作用(test 锁 5) | ✅ |
| total 合成面 Phase 1 仅 A/B 非零 | `PieceValueWeightPhase1` 仅 w_activation/w_retention 两字段(类型层收窄,W833 补丁④推荐方案);registry 无 C/D/E/F 权重字段(契约锁兜底=test 锁 6) | ✅ |
| 买侧试点接入(κ 通道外侧应用,κ 路径零改动) | `scoring.py` score_candidate:pv 加项置于 off-lock 降级**之前**(与 tp_gap 同位)→ 随既有 κ 折扣外应用;锁定帧线外辖域(locked_buy_scope);bd['pv*'] 七披露键(分量归因通道,设计 §3.3) | ✅ |
| 五结构锁+哨兵锁+锁 6 | `sr-od-test/.../test_cw_piece_value.py`(新)9 锁,含 off 恒等零漂移(锁 4)、纯函数(锁 5)、κ 通道零改动=W802 锁#3 恒等式在 pv 开关两态下均成立(锁 7)、C 分量 missing_members 同源对拍(锁 8) | ✅ |
| PREREG 判前锁冻结 | `PREREG.md`(本目录):M1-L 传导格主门(W829 v3 分布级分层格同式+效应量下界)/G7 复算上界带(折算式写死 pp+逐局差集配对+U<0.5pp 无预算分支)/Phase 1.5 对照臂显式=Phase 1 开臂态(补丁①)/「Phase 1 绿≠全模型验证」声明(补丁③)/哨兵语义收敛(补丁④) | ✅ |
| 验证 | 锁组 9/9 绿;test_cw_realization_chain 13/13 绿(κ 基线保护);cw_quick L1 **1761 passed**(1 red=adr0293 字段面锁「新增字段须入 _EXPECTED_FIELDS 面册」,按锁语义登记 piece_value 六字段缺省值后 4/4 绿——锁红≠改动错,该锁职责就是强制面册登记);ruff:src 3 文件+test 2 文件全过 | ✅ |
| 禁触面 | realization.py/allocator.py/tier_push.py 零触碰(git show 48c42110 三文件佐证) | ✅ |

## 2. 关键落码决定(判读锚)

- **A 激活** = w_activation × engine_jump_gold(e)(V_D 收益侧同式同源,
  ADR-0352 金口径),辖域门:锁定帧 ∧ 线外 ∧ 体系钥匙件 ∧ e<2 ∧
  k→k+1 恰达(P20 直译);**B 留存** = w_retention × 费用(费用=再遇
  稀有序数代理,P1 单调;满息段+bench 有位辖域,P11),P34 挂账占位;
- **签名偏差声明**:evaluate_piece(piece, state, weight) 落码为
  (piece, state, weight, registry, session=None, target_scope=…)——
  registry=常量单一源注入、session=C/D 披露分量的缺件判据入口
  (None 时 C/D 恒 0)、target_scope=消费点解析后传入(本函数对意向
  态零依赖,纯函数面不变);
- **D 披露分量**复刻 merge_timing_unit×2/3(披露面只读;行为面单一
  实现仍在 W802,Phase 2-b 收口时消费点改读本分量后删平行);
- **E 披露分量** = −bench 占用比(H 标定挂账,零新魔数)。

## 3. 偏差与挂账

1. **同文件并行批冲突(cw_registry.py)**:W829 支出门批在飞同文件,
   按任务书预案做 hunk 级 staged(只取本批 @1270 hunk);共享 index
   被并行批压入后改用**临时 index commit**,主仓 48c42110 精确含本批
   3 文件(+309),并行批 staged 态未受扰;
2. **adr0293 字段面锁登记**(测试仓 fb6eab5)属锁面义务,入本批;
3. **ADR 未立**:默认关零行为变更,按「攒 ADR=漂移」判据挂到开臂批
   (开臂/删码时一并记 ADR,PREREG §8 前置件已含锁组全绿前提);
4. cw_quick 全量红转绿后未重跑整套 L1(红因=面册登记,修复后该文件
   4/4 绿+新锁组 9/9 绿;风险=其余 1761 绿与本修复正交,字段登记
   只影响面册测试自身)。

## 4. 合格线自检

Phase 1 范围逐条落码 ✅ / 五结构锁+哨兵锁全过(9/9)✅ / off 零漂移
(锁 4:权重非零+伞关逐位等基线、无披露键)✅ / κ 通道零改动断言绿
(锁 7+realization 13 锁原样全绿)✅。
