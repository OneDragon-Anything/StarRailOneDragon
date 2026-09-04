# ADR-0316: bench 槽位语义模型(定长 9 槽,空槽留 None 不紧缩)

- 状态:accepted
- 日期:2026-08-25
- 背靠:W57 索引坐标系审查(F2 跨源拼装无全局防护 / F3 fill bench 源
  pop 漂移)+ 用户裁定(2026-08-25):「idx 跟画面语义一致,空槽留 None
  不紧缩」;W51 扩面批任务书。
- 落点:`cw_state.py`(`GameState.bench`/helpers/`simulate`/
  `mutate_bench_deployed`/CompTransaction)+ 全部 bench 消费端
  (decision_v2 全家/cw_plan/cw_evolution/cw_sim/line_strategy 等)。

## 背景与动机

bench 原先用**紧缩 list**(删除即左移):卖出 `pop(idx)`、上阵 `pop`、
3合1 删件——任何删除都改变后续元素的下标。由此产生一整个「索引漂移」
病族(W57 §1 矩阵):

- **F1(阻塞)**:同轮多笔 SellBench 顺序 pop 左移,卖错件(根因实例,
  W51 原批已辖);
- **F2(阻塞,新发现)**:decide_prep 五源拼装(演进/rollback/carry_gate/
  liquidity/arbiter 采纳集)的所有 bench_idx 都基于同一原始 state.bench
  生成,执行层按序消费——跨源组合下先动容器的源会让后源的 idx 漂移;
- **F3(条件性阻塞)**:CompTransaction fill 的 bench 源应用期
  `post_bench.pop(f.idx)`,多个 bench 源 fill 顺序 pop 填错人。

三个发射点的局部缓解(降序发射/arbiter index_drift 守卫)都是**约定层
补丁**——它们各自修一个发射点,管不住「生成期索引 vs 执行期索引」的
系统性错位。用户裁定把表示层改成**定长槽位表**:空槽留 None,任何
操作不紧缩不移位——索引 = 槽位号,天然跨动作组稳定,整个病族在表示
层消失。

三层证据(为什么槽位是根因修法):①生产 prep 层本就按物理槽位工作
(prep_actions 声明「非 bench 列表下标」);②画面留空不移动(用户口述
权威——卖出后备战栏槽位不左移);③W52 补偿趟需要「生成期索引 = 执行
期索引」——槽位表示下这是恒等式。

## 决策

**核心不变量**:`GameState.bench: list[BenchChar | None]` 定长
`BENCH_CAPACITY`(9)槽表;列表下标 0-8 = 物理槽位 1-9 减一
(`BenchChar.slot` 保留 1-based 屏幕槽号作信息位,权威槽位=下标)。

- 卖出(SellBench)/上阵(DeployMove)/3合1 消费份 → **置 None 不 pop**,
  任何操作不紧缩不移位;
- 买入 → `bench_place`(首个空槽;无空槽 = bench_full 拒);
- 容量判据 = 占用数 `bench_occupied`(**禁止 `len(bench)`**——定长下
  len 恒 9,是容量判断的经典错位源);
- 迭代一律 `iter_occupied`((idx, char) 对,None 跳过)——全仓扫掉
  裸 `for c in bench`/`bench[i]` 紧缩假设;
- `GameState.__post_init__` / `simulate` / `mutate_bench_deployed` 入口
  防御性 pad(None 补到定长 9;调用方直接赋值短 bench 时不崩)。
- **CompTransaction fill 的 bench 源 idx = 槽位下标(0-8)**:生成期索引
  = 执行期索引,无 pop 无左移修正(F3 根治);fill 的候选池 = 迁移后的
  bench 槽位表(deploy/sell 清槽、undeploy 放回首个空槽),校验/应用
  按同一视图解析。
- **降序发射移除声明**:liquidity 的 `-bench_idx` 降序重排(旧紧缩表
  pop 左移的症状补丁)在槽位语义下无意义,已删——任意发射序零漂移
  (乱序发射也零漂移 = 更强断言,测试改写为槽位语义锁)。

## Considered Options

- **降序发射(症状补丁,维持)**——被否:只修 liquidity 一个发射点,
  F2 跨源组合/carry_gate 多笔/未来新发射点照漂;且发射序被强制降序
  是「为错误表示买单」的约定层债,每次新动作类型都要记得补。
- **紧缩 + 发射端重索引(症状且侵入更大)**——被否:保留紧缩表示,
  在每个发射点逐步 simulate 重导 idx(cw_plan 式)或发射前名快照
  (arbiter 守卫式)——侵入每个发射点,且重导/快照本身是新的漂移源
  (生成期 vs 执行期的语义永远要靠「记得写」维持)。
- **槽位表示(根,选中)**:表示层与画面语义一致(留空不移动),索引
  恒等式成立——发射点零改动免疫漂移;消费端一次性适配(iter_occupied/
  bench_occupied/None 守卫),之后新增动作类型无索引债。

## 影响

- `cw_state.py`:`GameState.bench` 语义 + `iter_occupied`/
  `bench_occupied`/`bench_place`/`bench_clear`/`pad_bench`/
  `bench_from_compact` helpers + simulate/mutate_bench_deployed 槽位化
  + CompTransaction fill 槽位下标 + `_merge_bench` 置 None。
- 消费端全仓适配:decision_v2(candidates/discipline/arbiter/scoring/
  strategy)/cw_plan/cw_evolution/cw_sim/cw_sim_checks 读侧(账本序列化
  保持占用序紧缩,下游零迁移)/line_strategy/cw_evaluate/cw_comps/
  cw_bundle/cw_intention/cw_line_defs/cw_transition/cw_system_cards/
  cw_events 的裸迭代/len 容量判断 → iter_occupied/bench_occupied/None
  守卫。
- 测试:全量旧锁的紧缩语义假设(构造短 bench 无 None/断言 pop 左移/
  len(bench) 容量断言)逐个改写为槽位语义(构造 None 混排 bench 才是
  有效覆盖);F2 跨源共存锁新增(同轮多源混合动作组,断言每个 bench_idx
  执行后命中的恰是生成期指向的槽)。
- sim 账本:bench 序列化保持占用序紧缩(下游 checks/视图零迁移,
  占用数=len 语义不变)。
- 行为面:仅「降序发射移除」与「索引稳定性」两项(执行语义等价改造);
  容量/迭代语义经 bench_occupied/iter_occupied 还原为与旧紧缩语义
  等价,无新策略语义。
