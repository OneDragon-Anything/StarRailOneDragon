# journal.md —— 记录机制(账本/渠道签名/版本 id/自足快照行/落盘与查询)

> 本文档所属 = game_state 设计目录,总纲见 [README](README.md)(含 GameState/BoardState
> 命名对应注)。本文 = 统一 state 流水的记录机制面(原流程侧遥测设计件已删,git 可溯);设计裁定与 why 的持久锚 = 本目录正本各区 + git 历史。

## 1. 账本:state/journal.jsonl

流程侧唯一落盘流 = `state/journal.jsonl` 单文件追加(JSONL),行内 `run_id` 列切段归局;
落盘根 = 现役 live 遥测根下的 `state/journal.jsonl`。每次 state 写入记一行,行 = 改了什么
+ 渠道签名 + 版本 id + **写入后完整 state 快照**。per-run 分文件候选已否决(单文件+行内
run_id,段界识别沿用现役段首帧判据)。

两行型(流内任一行自足,查询不分行型):

- **行型 1 写入行**:`v`(版本 id)/`ts`/`run_id`/`row='write'`/`field`(本次写入字段
  寻址)/`after`(新值)/`same_value`/`state`(**写入后完整 state 快照**)/`sig`(渠道
  签名)/`note`/`evidence_refs`。
- **行型 2 观察事件行(obs_event)**:零状态变更的观察证据(拒读仲裁/失读留证/popup/
  类型直定冲突/链 diff 等),同样占版本、内嵌当时 state;`event` 词 = 登记清单非全量
  (现役 obs_conflicts 写点逐点收编 + 新登记项)。全量 miss 不留证(沿现役纪律)。

## 2. 三渠道封闭集与渠道签名

**渠道族封闭集**(裁定:写入源有且只有三个):

| family | 谁 | 说明 |
|---|---|---|
| `obs` | 画面 op 观察 | mode 子模词表:`read`(真读)/`carried`(失读沿用)/`prior`(先验)/`synthesized`(sim 合成) |
| `logic_action` | 动作 op 逻辑计算 | mode 恒 `compute`(买卖扣金/升级/回执写点等) |
| `logic_hook` | state 内部派生逻辑计算 | mode 恒 `compute`(节点推进派生/效果推进/局终收口/接管中继) |

carried/prior/synthesized 是 obs 族内子模,**非第四源**。

**渠道签名 ChannelSig** 每次写入必带:

- `family`+`mode`:见上;显式签名过渠道族封闭校验;**签名必填**
  (影子期「缺位合成 legacy 签名」过渡路径已随直迁退役,缺位 =
  调用期炸错,全行 actor 非空)。
- `actor`:写入者身份标注(画面 op 类名/观察汇聚模块/动作 op 类名/派生规则登记名
  /接管协议/局终收口等;类属注防 family 反查漏行)。
- `screen`/`frame`:画面建档名与 carried 行的沿用来源帧键(carried 行必带 frame)。
- `quality`:**字段级质量元数据**——`{字段名: 标记}`,记录「这个值是怎么读到的」,是
  写入闸门语义的落账面而非字段本体。起步词表(首写字段须登记申报值域):hp=
  real_read/settlement_fresh/same_node_carried/prior;gold=real_read/carry;level=
  real_read/xp_derived;商店卡 cost=badge/roster/roster_fallback;enemy_difficulty=
  real_read/briefing_constant;node_type=nodeseq/ledger_fallback/overlay_map/none。
- `group_id`:一次逻辑计算打包组标识(动作=`act:<op类名>@<seq>`,派生=`hook:<登记名>@<序>`)。

## 3. 版本 id 与单版本事务

分配规则:

1. **单点分配**于写入口同一临界区(先变更、后落行)。
2. **run 段内自 1 连续单调**,不重不漏;跨 run 唯一性由 `(run_id, v)` 保证;段内
   流内行序=版本序(版本号≠物理行号)。
3. **全序性**:版本序=写入序;前提=单写者(单线程 op 链),多线程化须先加锁(硬前置)。
4. **计版本动作面(单版本模型)**:一次逻辑写入(obs 系观察写入含组 confirm/动作 op
   逻辑写入/派生管线一次触发)各产一行各占一个版本;obs_event 行各占一个版本;carry
   且值无正式值(early return)不换帧不产行。**派生连带更新共享同一版本 id,一笔行
   落账**,行载荷标注派生管线段(derived 清单);「派生各占版本」「组 confirm 逐字段
   多行」两形态废除——多行形态会让 state_ref 钉到从未被决策消费过的中间态。
5. **读口**:`current_version()` 只读;策略侧版本钉 state_ref=`(run_id, v)`,回溯=
   直接读该行,行缺失才 `unverified`,不猜。

段界三窗(规则见本文 §3.2.2 规则 6):局间旧 id 驻留窗
(收口后 run_id 供给槽返空+写入口上游**写缓冲**,新段铸造后按序补写,补写行带原始
ts 与 `buffered` 行注记)/历史段补写窗(专用装配通道,不经运行时写入口)/恢复局跨段
容器重基线窗(每段容器重基线,「v 自 1」的前提)。

## 4. 自足快照行

- **state 快照**:行内嵌写入后完整统一 state(JSON 安全化),含逐字段来源注记面
  `gs_prov`(source 非 observation 或带 evidence 的字段入注记——单行可判「gold 真读
  还是沿用、hp 是否结算新鲜」)、effects 规范化序列、挂起预期摘要 `pending_expected`。
- **序列化规范化**:effects 按 spec id 排序、receipts 按窗序——同态同形,离线 diff 可比。
- **派生原子生效**:派生规则在单版本事务内完成(节点判定→类型→效果推进固定次序),
  派生字段与原始变更同行可见;派生出错=整笔回滚留证。
- **效果域捕获声明**:效果账本域(effects)保持就地可变 inventory 方法域,不设专用
  写口、不设专用域行——效果变化随每行全量快照自带;效果域**内容语义**(计数器模型/
  生命周期/规格声明)= [effect-domain.md](effect-domain.md),本文只管捕获面。
- 预期簿记不单独产行:挂起面随快照可见,产生/清账由相邻行差分人读可见。

## 5. 落盘与查询

- **落盘形态**:内存追加+规范化序列化;磁盘批量 flush(阈值常量
  DEFAULT_FLUSH_EVERY,单一源 = kernel/cw_state_journal),同步关键
  路径零 open/write。**收口 flush**:run 收口单点(telemetry close_run)
  先把缓冲批量落盘再返回——批量阈值之间局终时,局终行与段尾行若留缓冲,
  紧随的档案装配读盘漏行(g_20260915_070645 档案缺 endgame.match_final
  实证),丢失窗上界收敛到收口时点(单一源 = kernel flush_pending)。
  体积=单行全量快照所致显著大于旧单流,体积实测挂验收;
  压缩候选须保行自足。
- **宽容消费契约**:批量 flush 的半行/坏行=逐行跳过+坏行计数留痕;消费方(判读
  CLI/装配器/哨兵)统一按此消费,禁把半行当合法行解析。
- **局外拒写**:run_id 空=拒写(符号锚=`StateJournal.append` 局外门与写入口双门)。
- **查询模型**:判读/装配/策略回溯=按行直接读(单行自足);跨行对照=行间差分(人读
  /离线),无机制化重放;完备性显影(节点推进数/效果递减伴生性等)回归判读侧离线
  派生,不设系统机制。
- **读向隔离**:决策输入禁读状态流水;运行时控制面读口=显式豁免类
  (封闭枚举:局终扫描/终局防重查重/Δ 池再生触发/落地判定 reconcile 对比读口)。
- **寿命(滚动清理)策略**:触发时点=装配前置(生产装配趟
  `install_state_telemetry` 调
  `enforce_journal_retention`,单一源=kernel/cw_state_journal;该时点写端未启动,
  零并发窗;每次进程装配触发一次,频率对天级窗足够)。清理单元=**run 段整体**
  (禁切半段——段内版本序完整是 state_ref 版本钉解析的前提);淘汰分三道闸,
  按序判定,命中即入淘汰集:
  1. **实机段龄窗**(常量 `JOURNAL_RETENTION_DAYS`=跨期语料窗):只辖实机形态段
     (run_id 铸造口径常量 `REAL_RUN_ID_RE`;与判读装配/三件哨兵的正选口径同源,
     一致性由测试锁钉住;kernel 禁依 telemetry 故此处持独立字面量)。跨期语料窗
     承诺辖域=实机对局语料。
  2. **非实机段龄窗**(常量 `JOURNAL_NONLIVE_RETENTION_DAYS`):sim 批段
     (fake_/sim_ 前缀)与 harness 段的全消费面(Δ池隔离/判读过滤/档案装配/哨兵)
     均不采信,保留价值=批后隔日复查判读,短窗足够。依据=常开化后真实积累实测
     (2026-09-12):现役账面全部段均为非实机段且段龄 <2 天——30 天窗对其
     永无效力,账面体积随 sim 批积累无上界,是哨兵/装配整账读成本线性上涨的
     体积根源;窗口数值随真实积累形态定(r5-migration-plan(已删,git 可溯) §4-5 授权)。
  3. **体积兜底窗**(常量 `JOURNAL_MAX_BYTES`):前两道清完后现役文件仍超上限,
     按段末时间从最老段继续淘汰(**不分型**,实机段也在淘汰序内),直到 ≤ 上限
     或只剩不可清段。容量失控(如压测日异常积累)可击穿闸 1 的承诺窗——此时
     保留窗「下限」语义让位于容量约束,被清段经 manifest 显影保考古。
  通用护栏:活跃段(段末行最新)永不清理;无 ts 段不判龄不清理(宁保留不误删);
  坏行/无 run_id 行原样保留(宽容契约,清理面不判定);淘汰逐段追加写
  `journal.retirement.jsonl`(archived_out 显影,`reason` 键辨「哪道闸清的」);
  文件重写=临时文件+原子改名。state_ref 钉解析失败=查 manifest 辨「清理 vs
  丢数据」(行缺失=unverified 不猜,schema 既有口径)。

## 6. 写入口 API 面与硬约束

API 面(宿主=GameState 写入 API,符号=kernel/cw_game_state.py):

```text
渠道①:observe / carry / write_prior / leave_screen     (均带 sig)
渠道②③:expect / confirm / write_logic / write_logic_rand / discard_expected / relay   (均带 sig)
观察事件:note_obs_event(...)                            (行型 2,占版本)
读口:current_version()
```

`write_logic` 仅限设计显式申报豁免的写端(事件屏 chosen 族〔事件屏选择结果字段族
`chosen_*`,定义见容器正本 §3.4〕/局级事实写端〔局终域域键 `match_final`,唯一写口
`write_match_final`,渠道③ actor=MatchClose:一段一行,载荷 = 终局类型封闭集 + 时点
版本 id + code_commit/registry_fingerprint 版本戳 + 终局快照 + 段级时长,abnormal 补写行
note=recovered 显影;辖域 = 段内补写与在线收口,启动扫描**历史段**补写走专用装配通道,
不经本口——迁移批修订 2026-09-11〕/刷新计数组/效果写端申报行/动作发射
写点 receipts/账本→字段桥),其余禁走此口。

硬约束四条(机器面=测试锁):①禁旁路直写(grep 子串守卫锁+效果域直摸锁);②渠道族
封闭集;③域准入白名单(逐格以实码写点全集核源,禁凭概念断格);④读向隔离(§5)。

## 7. 旧 12 流退役与消费方迁移

退役理由、12 流逐流处置表、消费方迁移清单、退役前置条件与批次排期 =
[retirement.md](retirement.md)(单一源,本文不复写);排期与裁决口径的现行
原正本 r5-migration-plan(单源直迁八波)已随过程件清理删除,考古走 git 历史。
**常开语义(影子双写裁定已推翻)**:journal 无条件常开——无开关、
无装配条件分支;生产装配 = app 装配段显式接通 + **局容器单例建立点兜底**
(`game_state_of` 建立路径注入 run 归属读取函数并触发 kernel
`ensure_journal_assembly`,幂等;GameState 构造器零装配逻辑——画面解析草稿
容器直构路径结构性不可能触发遥测;生产注入漏斗 = `establish_new_match`
容器建立点——CwEntryStart 进对局
前移点与 CwLoop handle_init 兜底两生产调用方的公共漏斗;装配归属裁定 = 遥测
数据的保存是 game state 职责,run 领取层 telemetry `ensure_run_started` 不辖
装配〔用户裁定 2026-09-15〕;
辖 op 直跑入口——run_operation 直调 CwLoop 的接管/续跑不经 app 装配段,
九流退役后该路径失旧 lazy recorder 隐式覆盖,2026-09-14 18:56 起
8 连局零行零档案实证,深检 run_20260915_054718.md §0),收口单点 reset;
写路径不因账本存在与否分支,行落盘另以 sink 在场与 run_id 在场为准
(缺实例 = 行不落,诚实缺失)。

## 8. 两文件模型与策略侧

全局落盘目标 = ①流程侧 state/journal.jsonl(本文)+ ②策略侧决策行文件(DecisionTrace
瘦身演进,行 schema 归策略侧设计正文)。策略侧对 state 的引用只经 state_ref 版本钉,
禁读状态流水;两文件按 run 段同批淘汰(寿命契约耦合,见 retirement.md §6)。

