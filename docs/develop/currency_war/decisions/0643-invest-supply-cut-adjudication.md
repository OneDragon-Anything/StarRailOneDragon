# 0643 invest 效果原文断供定谳——接受断供,恢复路径 = strategy_offer 画面 payload 域(落地挂 W5 评估)

> 编号注:0N 系顺延(建档时 INDEX 现最大 0642)。r5-migration-plan.md §5 风险 10
> 规定「候裁 2 定谳为 W7 删流硬门」;删除波 1(ADR-0641)先于本定谳执行了
> invest_cards 写入端删除,本件为该硬门的补位落档(派单义务源 = 删除波 1
> 落地审 §五-③「定谳凭据未见独立 ADR,随文档批补」+ §八 P-4)。

- 日期:2026-09-11
- 状态:accepted
- 关联:ADR-0641(删除波 1——invest_cards 写入端删除 = 本件断供事实的执行批;
  其后果 3「invest 效果原文回流断供(接受后果;归宿 = strategy_offer 画面
  payload 域)」指认本件定谳)、`docs/develop/currency_war/game_state/r5-migration-plan.md`
  (§2 W7 行「候裁 2 定谳=删除前定谳硬门」/§5 风险 10/候裁清单第 2 条 = 定谳
  对象)、`docs/develop/currency_war/game_state/retirement.md`(§2 invest_cards
  行 = 处置单一源,本件兑现其「停写前须定谳」)、ADR-0132(投资卡效果原文采集
  设计——其采集通道随删除波 1 退役,本件即其封档指针;本体按 ADR 不可追溯
  纪律不改)、`.debug/progress/2026-09-06-currency-war-redesign/reviews/删除波1-落地审.md`
  (§五-③,本地不入 git)

## 背景(断供事实)

invest_cards 流 = 逐局候选卡效果原文语料(ADR-0132 设计:strategy/env 两屏
采集分桶,每卡一行 {ts, run_id, kind, idx, name, x, effect_text, chosen}),
用途 = 离线对拍注册表漂移(错效果/未注册名清单 → 补注册表)+ 选卡面语料。
删除波 1(主仓 `3d4461438`)删除其全部生产写入端:`record_invest_cards`、
strategy/env 两屏采集分桶、候选评分供数块写端(ADR-0641 §决策表;落地审
§一「invest_cards:record_invest_cards 全仓 ZERO」亲证)。逐项后果(在树可核):

1. **逐局语料断流**:`invest_cards.jsonl` 停写,存量冻结(归档只读,裸读
   考古,r5 §2 W7「归档只读声明」);新局不再产出「候选卡全集 + 逐卡效果
   原文 + chosen 位」语料。
2. **对局档案面**:`telemetry/match_archive.py` 装配的 opening 域 `invest_cards`
   切片对新局恒空(读侧容忍缺键,`slice_rows.get('invest_cards.jsonl') or []`);
   历史档案不受影响。
3. **判读面**:单局复盘按 invest_cards 切片定位投资选卡的指引失新局载体
   (skill 判读文档 telemetry-reading.md / match-review.md 已随本批改指
   journal 行型 1 写入行:`active_strategies`(选卡名,局级累计追加,单次
   选择 = 相邻行差分)+`strategy_refresh_used`(刷新明细,行内
   evidence='refresh_click@slotN'),写入点均在 cw_screen_invest_strategy.py
   (确认成功块/刷新发射块);reason 归因串仅应用日志 [cw-strat]/[cw-env]
   行承载不入档案,策略侧决策行文件属两文件模型规划载体(落地前无写入端);
   历史切片保留只读标注)。

**未断供面(边界,防过度定性)**:注册表 ground truth 回流通道不受影响——
`cw_invest_data` 注册表(plaza API 生成器直灌,ADR-0150)照常在产;人读版
doc 已随 2026-08-18 注册表大收敛删除(单一源在代码注册表,见
`docs/game/currency_war/data/README.md`);投资策略名未注册告警保留
(数据源 = 当前确认轮候选名,cw_screen_invest_strategy 在树注释)。

## Considered Options(r5 候裁 2 原文两案)

1. **strategy_offer 域建模(r5 倾向,随 W5 payload 建模同批)**——候选卡面+
   效果原文收编为统一 state 的画面 payload 域(离屏即 None),语料随 journal
   快照行自带,不设独立流。
2. **接受断供**——逐局原文语料永久断流,注册表回流继续承载 ground truth,
   等真实消费方出现再议恢复。

## 决策

**定谳 = 接受断供(方案 2);恢复路径 = strategy_offer 画面 payload 域建模
(方案 1)为既定归宿(ADR-0641 后果 3 指认),落地时点挂 W5 payload 建模批
评估,不设强制接线义务。**语义分三层:

1. **断供即终态,不回滚不补写**:删除既成事实与定谳一致;禁为语料回流恢复
   旧流写端(ADR-0634 直迁口径:旧流 = 删除代码,停写观察属已销案的影子
   框架语义)。
2. **断的是什么、留的是什么**:断 = 逐局候选卡效果原文语料——「注册表文本
   vs 逐局实拍文本」的分歧检测通道(ADR-0132 离线对拍闭环)与新效果长尾的
   实机先见窗口;留 = 注册表 ground truth(plaza API 全量,生成器重跑即得)
   + 词缀侧同构采集通道(HandleBriefing → affix_effects_data)照常在产。
   实质损失评估 = 投资卡效果文本漂移只能经注册表侧生成器对拍发现,逐局
   实拍先见能力让位;当前无活跃消费方挂账(选卡语料统计/漂移检测均无
   在办任务引用 live invest_cards),断供无在飞受损面。
3. **恢复路径与触发条件**:出现真实消费方(选卡语料统计/效果文本漂移检测
   立项)或 W5 域建模批到场时,恢复载体 = strategy_offer 画面 payload 域
   (语料随 journal 快照行自带,不复活独立流);无消费方则维持断供终态——
   禁无消费方的采集通道(retirement §1「写点不全」退役理由的直接推论)。

**硬门时序申报(如实)**:r5 风险 10 规定候裁 2 须在 W7 删流前定谳(「删除前
定谳硬门——效果原文回流断供不可逆」);实际时序 = 删除波 1(含 invest 写入端)
先于本件入库(同 ADR-0641 已申报的「W7 进入门未满足即先行」波序事实,落地审
§五-③ 亲证)。后果评估:断供决策事实上已由删除执行作出,本定谳不改变执行面,
只把既成事实、边界与恢复路径落档;「硬门义务先于执行排期」的教训属 r5 排期
纪律面,编排者知悉,本件不另立卡。

## 后果

- retirement.md §2 invest_cards 行「停写前须定谳」兑现为本件(行文与版本
  历史表随批更新)。
- **obs 缺陷 refs 指冻结档案的处置(ADR-0641 后果 2)同批逐处落档**(纯文档
  零行为):guards.md §6(exec_fail 数据源改内存直读口径——旧三流含
  obs_conflicts join 全停写)、telemetry-reading.md(events 视图替 anomalies/
  obs_conflicts 白名单冻结标注)、match-review.md(投资选卡定位改 journal
  行型 1 写入行)、
  strategy-docs/15(留证术语落点)、统一观察架构设计稿(对拍行括注)。
  逐处明细 = 交付报告 `.debug/temp/currency_war/T-275-交付报告.md`(本地
  不入 git)。
- **缺陷台账 refs 面(现状申报,不随本批改代码)**:defect_ledger 保留专用
  (候裁 4 未裁),冲突旁路行 refs 仍指 `stream='obs_conflicts'` + (field,ts)
  键——历史行可下钻冻结档案,新冲突证据行在 journal obs_event(行型 2,
  field+ts 可对账),按现 refs 下钻新行扑空。恢复 = retirement.md §2
  defect_ledger 行已预申报的「裁保留时 refs 改指 journal `(run_id,v)` 键 +
  寿命联动」(挂候裁 4,随 W3 消费迁移批),本批纯文档不预支代码面。
- **相邻断供面(申报不处置,归 W3 消费切换批的文档同步)**:shop_visit.md
  旧流写点描述段(spend_ledger 单元行/record_shop_snapshot/decisions Error
  占位行/set_unit_exec_facts 等八处)、telemetry-reading.md 核心原则第 2 条
  (decisions.jsonl 直查指引)、match-review.md 同行 outcomes/exogenous 定位、
  统一观察架构 §12.4 指标 1(动作锚闭合公式引用三流)——非本批两件辖域
  (obs 缺陷 refs/invest 原文),逐处列于交付报告。

## 附带勘误(T-274 落地审低项②③随批闭环,不另立卡)

- **低项②「§5-7」模糊指针**:ADR-0641 §决策「cw_telemetry_exit 桩挂
  R5 §5-7」的「§5-7」在现行 r5-migration-plan.md 无对应条目(新旧 retirement
  §5 亦无第 7 条,T-256 入库时已然);语义真锚 = r5 §7 候裁 3(cw_anchor 四
  carrier_kind 归宿)。本件即该指针的持久勘误锚;代码注释同款
  (cw_telemetry_exit.py/测试仓)归注释批改写,本批不改代码。
- **低项③ 临时件指针未标注**:ADR-0641「逐流明细单一源 = 删除波 1 交付报告
  §二」指向 `.debug/temp/` 临时件,未标注「本地不入 git」——临时件清理后仅
  指针失路;删除面实质已由 ADR-0641 §决策概要表承载,失路不影响判死依据
  可追溯,不回改 ADR 本体(immutable)。
