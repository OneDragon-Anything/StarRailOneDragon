# ADR-0650: R5 W4 cw4 计数流删 + 键收编落码(键全集封闭性锁)

| | |
|---|---|
| 状态 | 已实施(工作树;入库走 committer) |
| 日期 | 2026-09-11 |
| 决策者 | 编排者(用户 2026-09-10 直迁裁定承接;r5-migration-plan.md §2 W4) |
| 关联 | ADR-0630(统一 state journal)/ ADR-0634(journal 常开)/ ADR-0641(删除波 1 九流写入端退役)/ retirement.md §2-§3 处置表 / T-311(W4 审计先行段 v3 交付 + 键收编落码段) |

## 背景与问题

cw4_counters 是策略行为观测计数的独立 JSONL 流(`cw4_counters.jsonl`):
mandate_v1 各模块把分键计数写进策略 state 容器(`MandateState.cw4_counters`),
局终收口时 cw_loop 把容器整表快照落流,match_archive 按局时间窗归并进档案顶层
字段,replay_to_md 渲染——这是实机侧唯一的局终级全键聚合可见面。R5 直迁八波中
W4 的任务是:键收编落码(效果键→效果域 inventory / 策略键→决策行字段 / 无消费
键删)+ 流删(cw_loop 写点 + match_archive COUNTERS_FILE 面 + cli cw4 视图)。

T-311 审计先行段(v3,三轮复核 accept)定谳:**效果域 0 键**(全部键为策略侧
决策/观测语义,效果域 inventory 容器与本容器零交集,候裁 8 不构成依赖);
**策略行为键 256 字面 + 16 闭域参数化族(实例上界 80)+ 9 开放域族全数归属决策
行(strategy state)**;**无消费键 0**(四查+测试锁双口径下不存在可删键,弱消费
~26 键全保留随迁);**声明面/值场面 7 名**(launch_arbitrage_budget_blocked、
funding_support_stall_convert、funding_hold_liquidated、f7_contingency_armed、
depsilon_advisor_violation、f7_exempt_emission、f7_uncovered_interest_sell)非计
数键,须豁免防锁假红。

## 决策

1. **流删全脸拆除**:cw_loop `_record_cw4_counters_snapshot` 写点及两收口调用
   点、match_archive `COUNTERS_FILE` 常量、`record_cw4_counters_snapshot`/
   `record_cw4_counters_from_match` 写端、`_match_counters` 时间窗归并、档案顶层
   `cw4_counters` 字段整体删除。cli cw4 视图经审计定谳无对象(W3 已删,无操作)。
   档案 schema **不 bump 版本**(申报:wold 档案已落盘顶层字段只读保留;bump 会
   触发 load 期重装配把存量字段整批抹掉且流源已清无法补回,先例 = W2 endgame.
   match_final 键不 bump 申报)。
2. **键收编 = 留在策略 state,聚合改挂局终行**(retirement.md §3 定谳②:策略行
   为键归宿 = 策略侧决策行的 strategy-state 要素;决策行文件是两文件模型②的
   未来载体,行 schema 归策略侧设计正文,W4 不造第二源):容器
   `MandateState.cw4_counters` 原样保留——sim 红则/轮差分/预注册披露/约 40 个
   测试文件读容器不经流,零影响;局终级全键聚合可见性改由**局终域行载荷
   `MatchFinal.cw4_counters`** 携带(cw_loop 两收口点收口时点现读快照传入,
   先于 close_run;None=无载体/补写无源,{}=真实零计数,两型可辨沿旧装配语义)。
   档案显影位 = `endgame.match_final.final.cw4_counters`(match_final_view 载荷
   透传,纯读派生零新装配写入)。
3. **键全集封闭性锁**(W4 验收门):测试仓 `test_cw4_key_closure.py` 三层登记
   ——字面键全集对齐(256+增量)、参数化族登记(16 闭族含域闭集 + 9 开放族
   前缀,产出表达式登记)、豁免清单(7 名反向锁:出现写点即红)。扫描方法 = 审
   计 §2.6 七类写模式的 AST 机器化(别名赋值→别名下标写、helper 实参常量键经
   全局常量表解析——r2 复核逃逸实证 mandate.py 常量实参形态,禁纯字面量正则断
   格)+ 漏斗变量同函数作用域绑定追源。登记住测试侧:键集唯一消费方 = 锁与判读
   面,src 无运行时读键集的代码,禁造第二源。
4. **效果域写点门空转申报**(W4 验收门 D1 锚):效果域 0 键定谳的机器面 = 锁内
   `test_effect_domain_zero_keys_d1_idle_declaration`(效果域模块零本容器访问 +
   两容器键域零交集);效果键落域实施面无对象,候裁 8 成文义务不受影响。

## Considered Options

- **聚合载体:局终域行载荷**(采纳)vs 保留流面只改写入时机(违背直迁裁定,流
  = 删除对象)vs obs_event 行扩展(词表 = 观察证据封闭集,局终聚合非观察事件)vs
  等策略侧决策行文件落地再补可见性(违背审计输入清单①「决策行收编须保局终级
  全键聚合可见性」,W4 到实机窗口时无面可查)vs BoardState 新域(336 键进每行
  快照 = 写放大,W1 实测门不可承受)。
- **聚合落档案顶层字段重派生**(保留 `cw4_counters` 顶层键由局终行再派生)——
  否:审计输入清单⑩明列档案顶层字段为删除对象;endgame.match_final 已是既有纯
  读显影位,载荷透传零新代码。
- **封闭锁登记住 src 侧**(如 LOCK_PATH 前缀常量先例)——否:LOCK_PATH 常量服
  务运行时行为,键全集登记无运行时消费方;测试侧登记即登记单一源,避免造第二
  源。先例差异在 ADR-0611 键登记注释族(写点注释)仍保留,锁为机器对账面。
- **扫描器逐行正则**(审计 §2.3 复算命令同法)——否:实测多行调用/跨行下标/
  文档串形态不封闭(本项目实现期三类全部命中);改走 ast 语法节点判定,审计七
  类模式逐一映射到语法形态,常量表 = 跨模块 Assign/AnnAssign 字符串常量。

## 后果

- 正面:实机侧判读可见性等价保住(局终行即唯一账本的唯一局终行);sim/预注册
  /测试锁消费面零迁移;新增键/新族/新豁免未登记即锁红(变异红证在案),审计
  §2.6 残留风险②(常量键逃逸)有机器拦截;实现期封闭锁即捕获一例审计后增量键
  (fuel_filler_stall_precheck_unavailable,T-313 在飞 shop 批新增,锁红后补登
  记)——锁的价值当场兑现。
- 代价/移交:旧档案重装配不再产出顶层计数键(裸数据在盘可考古;判读面宽容缺
  键);replay_to_md 的计数渲染对 W4 后新档案显示无数据(候裁 6 考古工具面去留
  另裁);约 26 弱消费键与 9 开放族随迁决策行文件落地批(W6 后另批)。
- 验收门状态:键全集封闭性锁绿 + 变异红证;效果域写点门空转申报;落地审候编排
  者派;实机窗「判读面计数可见性抽查」候实机解禁(查 endgame.match_final.final.
  cw4_counters 显影)。

## 验证

- 新锁 8 条(test_cw4_key_closure)全绿;变异红证:私加
  `st['rogue_mutation_key_xyz']=1` 写点 → test_literal_keys_within_registry 红
  (精确定位文件:行)→ 还原绿。
- 载体行为锁:test_cw_match_final +2(载荷落账/浅拷贝/journal 行端到端);
  test_cw_telemetry_archive 4 旧流锁退役墓碑 +2 新锁(流脸退役结构锁 + endgame
  显影锁);test_cw_old_stream_write_retirement 扩员辖 cw4 面。
- 点名域快速集 + ruff 本工文件:见交付报告
  `.debug/temp/currency_war/W4-键收编-交付报告.md`。
