# 0514 - 安灯钩子关店金数据源改 spend_ledger 单元行(exec_fail 误停根治)

> **引用勘误(2026-09-04 ADR 存量 review)**:`.debug/` 归档 → 本目录(decisions/)同名 ADR。文内出现处按此对照读取。

- Status: accepted(2026-09-15 落码;依据=离线法证 `.debug/temp/currency_war/redesign/EXEC_FAIL_P3R1_DIAGNOSIS.md`,修法①采纳;重启加载由实机批局间隙执行)
- 影响层: `operations/prep_director.py`(`_exec_fail_hook_check` 数据源 + `_spend_unit_open` 序号重计)/ `telemetry/query.py`(`resolve_unit_gold_close` 新纯函数 + `query_spend_ledger` 取值序)/ `telemetry/schema.py`(unit_seq 注释)
- 关联: 诊断 = `EXEC_FAIL_P3R1_DIAGNOSIS.md`(局 `run_20260901_180236` p3r1 误停);同族前案 = ADR-0456(局22 误停,plan_truncated 豁免——「计划≠尝试」口径支);gold_close 无条件落行 = ADR 2e7364de(W505 金面收口)

## Context

局 run_20260901_180236 位面3轮1 第二购买单元实为健康单元(金 51→44、经验 6/72→10/72、星期日上席),但 exec_fail 安灯钩子停机。根因在**钩子数据源**,非执行链:

- 钩子的「关店金」取自 obs_conflicts.jsonl 的 gold_delta 冲突行——该 journal **仅 mismatch 才写**且**行内无 run_id/unit_seq**,join 键只有 (plane, round) + 600s ts 邻近窗;
- 同轮第一单元落了一条冲突行(new=51),第二单元健康不落行 → join 唯一可命中的是 86 秒前的陈旧行;
- gold_open=51 vs 陈旧 gold_close=51 → 金差 0 → `not_effective` → 误停。

与 ADR-0456(局22)同属安灯数据面误报家族,不同支:那次是「计划≠尝试」口径,这次是「陈旧 join 行」口径。

## Decision Drivers

- 每单元必写、带完整单元身份(run_id/plane/round/unit_seq)的数据已有:spend_ledger 单元行的 `gold_close`(W505 金面收口后 shop.py 关店对拍点无条件暂存、落账时消费填充)——本案里就是对的 44;
- 钩子本来就读该行取 executed 字段(ADR-0456),扩用金字段零新增 IO;
- obs_conflicts 保持「冲突才记」语义不污染(诊断推荐修法②否决理由)。

## Considered Options

1. **单元行 gold_close 优先(选定)**:join 键天然带单元身份,一并消掉「条件性落行 + 无身份键」两个病根。旧行(无该字段,W505 前)回退冲突行 join 兼容存量 replay;新行读失败以 None 进分类器记 unknown 不猜、**不回退**——回退等于把陈旧 join 面从主路径挪进读失败路径。
2. gold_delta 行改无条件每单元落行 + join 键升级 (run_id, plane, round, unit_seq):违背 obs_conflicts「冲突才记」journal 语义,污染面大。弃。
3. ts 窗 600s 收紧到 ≤60s:同轮两单元间隔可低至 ~20s(本案第二单元全程 19.7s),收紧也挡不住,跨局消歧更脆。仅止血不治本。弃。

解析逻辑抽为 `query.resolve_unit_gold_close` 纯函数,安灯钩子与离线视图(`query_spend_ledger`)共用单一源;离线视图取值序同步收紧(读失败不再回退陈旧行,历史旧行保留回退)。

## 附带修复(同根隐患)

unit_seq 在 run() 环入口清零——run() 节点被外环重派重入是常态,重入清零使同轮多单元恒 seq=1(p1r1/p2r1 双单元撞键实测),`_spend_unit_row` 靠「取最后一行」侥幸取对。改为 `_spend_unit_open` 内按 (plane, round) 键重计,run() 重入只清新局轮键不清序。

## Consequences

- 安灯停线面不收窄:真失败(单元行 gold_close=51 金确实没动)仍 not_effective 停,新锁覆盖;
- 钩子生命周期不变:仍是临时采证钩子,根因修复验证(实机批重启后观察)后按 od-dev-stop-hooks 删整段;
- 运维面:旧 flag `.debug/temp/cw_exec_fail_hook.flag` 由实机批按局间隙流程处理,本批只改码。

## 验证

- 本案数据回放(`exec_fail_p3r1_verify.py`,replay 三流直读):修后 gold_close 来源=unit_row.gold_close=44 → verdict=effective(actual=-7, gap=0)不停;修前路径(冲突行 join)复现 new=51 → not_effective 停;
- 新锁 5 条(陈旧行不误停/真失败仍停/读失败不回退/旧行回退兼容/序号轮键重计)+ `_seed_three_stream` fixture 按 lock 纪律改 legacy 形态(意图=三流 join 面,行造为 W505 前旧行),test_cw_economy 全文件 91 绿;ruff 0 error;CW L1 快速集全绿。
