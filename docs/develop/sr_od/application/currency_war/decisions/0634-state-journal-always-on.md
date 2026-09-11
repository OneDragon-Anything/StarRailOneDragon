# 0634 journal 无条件常开——影子双写推翻(直迁口径)

> 编号注:本 ADR 初拟 0633,与并行批 T-126 种子豁免(ADR-0633)撞号让位改
> 0634(先例=ADR-0627 撞号让位)。

- 日期:2026-09-10(裁定)/ 2026-09-11(W1 实施批入档)
- 状态:accepted
- 关联:ADR-0630(本 ADR 推翻其决策 6「影子双写」,其余决策不受影响;其后果节
  「M5 旧流停写前必须完成 obs_event 登记面收编」由本 ADR 升级为 W1 交付项)、
  `docs/develop/sr_od/application/currency_war/game_state/r5-migration-plan.md`(R5 迁移规划 v2.1,
  本裁定的排期正本:单源直迁八波,重构 retirement.md 影子框架)、
  `docs/develop/sr_od/application/currency_war/game_state/retirement.md`(影子期/M1-M5 排期框架
  随本裁定作废,其文档重构挂 W7 文档批,改版前旧文以 R5 规划为裁决口径)、
  `docs/develop/sr_od/application/currency_war/game_state/journal.md`(记录机制 as-built)

## 背景

ADR-0630 落地时采用影子双写形态:config `state_journal` 开关缺省关——关 =
BoardState 派生域/上下文域零写入、零落盘、零版本消费(行为与旧 12 流时代逐位
一致);开 = journal 与旧流并行写;配套「影子期过渡语义」(写入口签名缺位时
合成 legacy 签名、派生/上下文写面受武装闸辖、开关两态逐位锁),retirement.md
据此排影子期/M1-M5 观察窗。

用户裁定(2026-09-10,经编排者转达;v2.1 修正令 2026-09-11 明确「影子开关
销案」):**不用影子开关/影子期——直接迁移并删除旧代码**。journal 无条件
常开,旧 12 流 = 删除代码(不是停写观察);验证职责 = 测试锁族 + 落地审 +
实机窗口直接暴露,直接暴露优于双源并行(风险立场用户已接受)。

## 决策

1. **journal 无条件常开**:无 `state_journal` 开关、无装配条件分支、无影子期。
   生产装配单点 = currency_war_app 装配段无条件 `install_state_telemetry`;
   「武装」概念退役——sink 在场/run_id 在场只辖**行落盘**(缺实例 = 行不落
   而写路径照常:Field 写入与版本分配不受影响,记录被动零行为分支),
   不再辖写路径本身。yml 残留键无害,config 不再读不再写。
2. **写入口签名必填,legacy 合成签名路径删除**:影子期「sig 缺位按 API 语义
   合成 (family, mode, produced_by, None)」的过渡路径退役;8 个写 API
   (observe/carry/write_prior/leave_screen/confirm/write_logic/relay/
   note_obs_event)的 sig 升为必填参数,缺位 = 结构性 TypeError。生产调用链
   显式签名铺满(kernel helper 内建 sig/画面 op 就地构造),actor 登记面扩员
   至 26 名(新增 10 个画面 op 类名 + obs_conflict 仲裁汇点),全行 actor
   在册非空(legacy 行 = 0 锁)。
3. **影子闸分支折叠**:派生域/上下文域/回执域写入无条件(R1 的「未武装 =
   零写入零版本消费」语义作废);行落盘另以 sink/run_id 在场为准(与
   ADR-0630 W2 修订节 match_final 监听语义同构)。`state_telemetry_armed`
   函数删除(无生产调用点,不留死代码)。
4. **验证三元组替代影子对拍**:每波 = 测试锁族(开关两态锁重构为常开锁,
   锁语义重推申报)+ 落地审(独立干净上下文 reviewer,逐 hunk+亲跑)+
   实机窗口(直接暴露,删除波 ≥2 局)。journal 首局容量风险由 W1 实测门
   承接(三口径:单行写 p50/p99、备战链增量、单局体积;超预期调 flush
   阈值常量 `DEFAULT_FLUSH_EVERY`,缺省 64)。
5. **obs_event 收编与 battle_done 收编提前**(原 M2/M5/M3 义务折入 W1):
   obs_conflict 汇点转 `note_obs_event`(行结构/截图节流/告警门原样,键封闭
   清单以 defects.py `OBS_FIELD_TO_SURFACE` 枚举为底补全调用点);旧 exogenous
   `node_enter`/`battle_done:<节点类型>` 外生行的「出节点」判读语义由结算
   覆盖 settlement 行注记 `battle_done:<节点类型>` 承接(同时点同载荷,
   行行自足快照语义强于旧行)。

## Considered Options

- **维持影子双写至 M5 停写(retirement.md v1 框架)**——否决:双源并行期
  需要维护「开关两态行为等价」的锁面与对拍验收,成本高;且旧 12 流的读者
  切换(W3)与写面删除(W7)仍要另排窗口,过渡态本身是双源漂移温床
  (ADR-0630 决策 8 的「逐流评估禁一句话收编」不受本裁定影响)。
- **保留开关但缺省开(半直迁)**——否决:开关留存 = 影子语义残留(测试
  两态锁/装配分支/闸分支全部要维持),与「删开关不留死代码」纪律相抵;
  且关态路径成为永不被生产执行的死代码。
- **直迁 + journal 常开(本裁定)**——采纳:删除是代码操作可 revert(每波
  删除面 revert 即恢复);验证职责由三元组承接,无影子缓冲的风险由实机
  窗口直接暴露兜底;过渡态(双容器/双流)存在时长最小化。

## 后果

- W1 起任意局无条件产 journal(常开锁);首局即三口径实测,无影子缓冲,
  写放大直接上进实机路径——异常 = 停局排查(实机卡住=现场修复纪律)。
- 测试锁面重构:开关两态锁(影子关零写入/开 = 轨迹一致)→ 常开形态锁
  (无实例 = 行不落而写路径照常/账本接线被动零行为分支/签名必填);
  legacy 合成签名锁 → 结构删净锁 + 签名必填锁(test_cw_state_telemetry_w1.py)。
- ADR-0630 决策 6 及其「影子期过渡」相关表述以本 ADR 为准;retirement.md
  的影子期/M1-M5 排期/前置六条按 R5 规划重构(挂 W7 文档批),改版前以
  R5 迁移规划为裁决口径。
- 旧 12 流写面删除(W7)与 GameState 本体删除(W8)的波序门不变:
  obs_event 收编(W1 已交付)先于 obs_conflicts 写面删除;
  落地判定 applied-gate 迁移(W6)先于本体删除。
