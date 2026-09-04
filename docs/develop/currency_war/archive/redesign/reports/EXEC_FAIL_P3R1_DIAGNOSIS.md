# 局1 exec_fail_mismatch 离线诊断(p3r1 安灯误停)

- 局:`run_20260901_180236`,2026-09-01 18:01–19:11,停止于位面3轮1(p3r1)第二购买单元
- 停止方式:exec_fail 安灯钩子(`hook:exec_fail_mismatch`),19:11:23
- 诊断性质:离线法证,只读(日志/档案/代码),未改任何文件、未碰实机
- 结论先行:**这是一次安灯误停(false positive)。购买与升级实际都成功了(金 51→44、经验 6/72→10/72、星期日已上备战席),但钩子的「关店金」数据源 join 到了同轮上一单元的陈旧冲突行(new=51),算出金差 0,误判 not_effective 停机。**

## 1. 日志定位(活跃日志 = `.log/mcp_server.log`;`.debug/sr_od_mcp/main_server.log` 末次写入 17:18,属旧进程,与本案无关)

安灯触发行与其前购买执行序列(`.log/mcp_server.log`):

| 行号 | 时间 | 事件 |
|---|---|---|
| 46870 | 19:11:06 | `[cw][gate] path=new(shop 开店)` |
| 46872 | 19:11:09 | 稳定帧「货币战争-备战-开商店」 |
| 46889 | 19:11:12 | `shop=[...] plan=['Buy(盛会之星/星期日/3)', 'LvUp(4)']`(gold=51 lv=8 p3r1) |
| 46890 | 19:11:12.496 | `[cw-shop] Buy click @(1260,165) 盛会之星/星期日/3` |
| 46891 | 19:11:13.002 | `[cw-shop] LevelUp click @(296,859)` |
| 46892–46895 | 19:11:13.6 | bench 像素差:`char→slot(pixel-diff):{'星期日': 3}` —— **购买已生效,星期日落到备战席 slot3** |
| 46896 | 19:11:15.6 | 商店收起帧 OCR:`'获得经验4' ... '0', '44', '10/72'` —— **金已 51→44(花7),经验 6/72→10/72(升级生效)** |
| 46902/46915 | 19:11:18–21 | 关店后金币区 OCR 两次实读 `['44']` |
| 46916–46917 | 19:11:21.8 | 单元收口:「plan 买1张 升1次 刷0次 卖0张」执行成功 |
| 46919 | 19:11:23.370 | 安灯截图落盘 `exec_fail_run_20260901_180236_p3r1u1_*.png` |
| 46920 | 19:11:23.428 | **安灯触发行**:`安灯:购买单元执行失败(计划花费>0 金差≈0) p3r1 u1 → 停机 flag=cw_exec_fail_hook.flag` |
| 46922–46929 | 19:11:23.5 | 备战决策环/对局循环/货币战争 三级 op 全部 `已停止[guard:hook:exec_fail_mismatch]` |

哨兵 flag 内容(`.debug/temp/cw_exec_fail_hook.flag`)自证数据源错了:

```
plan 摘要:BuyCard:星期日:3;LevelUp:level_up:4
gold:开=51 关=51        ← 关=51 与同一秒 OCR 实读 44 直接矛盾
```

任务书提到的现场截图 `.debug/temp/currency_war/screenshot_20260901_191836` **不存在**(glob 无命中);安灯自有截图存在于 `.debug/images/exec_fail_run_20260901_180236_p3r1u1_1788261083370.png`(本会话模型无视觉,未判读;日志与档案证据已足)。

## 2. 对局档案对照(三流对拍)

### spend_ledger.jsonl(本局 p3r1 有两个单元)

| ts | unit | plan 摘要 | gold_before→gold_close(trusted) |
|---|---|---|---|
| 19:09:57 | p3r1#1 | 买2 升4 刷1 卖1 | 68→51 |
| 19:11:21 | p3r1#2 | 买1 升1 | 51→**44**(gold_close_trusted=true) |

### decisions.jsonl

- `_shop_plan_rows`(query.py:893)按 `(plane, round)` **同轮取最后** → 钩子取到的是 19:11:12 的第二单元 plan(Buy 星期日 3 金 + LvUp 4 金,gold_open=51)。这一步是对的。

### obs_conflicts.jsonl(金读数冲突行)

本局 p3r1 的 `gold_delta` 行**只有一条**,属于第一单元:

```json
{"ts": "2026-09-01T19:09:57", "field": "gold_delta", "old": 48, "new": 51,
 "verdict": "留证-动作账vs读数不等", "source": "shop_spend_audit",
 "plane": 3, "round_num": 1, "spend": 22, "run_id": "run_20260901_180236"}
```

第二单元是健康单元(账实相符),**审计不落冲突行** → 钩子按 `(plane, round)` + ts 邻近窗匹配时,唯一可匹配的就是这条 86 秒前第一单元的陈旧行(new=51)。

## 3. 代码层机理(为什么陈旧行会被吃进来)

- 钩子取数:`prep_director.py:1706-1744` —— `gold_close = (conf or {}).get('new')`,conf 来自 `query._match_conflict(query._read_conflict_gold_delta(...), plane, round, now)`。
- join 键:`query.py:843-866 _match_conflict` 只按 `(plane, round_num)` + ts 邻近,**不含 run_id、不含 unit_seq**(行内也无 run_id,query.py:689-691 注释自己写明「行内无 run_id,同 (plane, round) 跨局复现——按 ts 邻近消歧」)。
- join 窗:`query.py:691 _SPEND_CONFLICT_TS_WINDOW_S = 600`(秒)。陈旧行距钩子触发 86 秒 ≪ 600 → 命中。
- 分类:`query.py:751-817 classify_spend_unit` —— gold_open=51, gold_close=51(陈旧)→ actual=0,plan spend=7 → `abs(actual)≤2` 且非 free_refresh → **not_effective**;`run_state.py:32-49 exec_fail_should_stop` 只对 not_effective 停 → 停机。
- 若用真实 close=44:actual=-7,gap = -7-(-7) = 0 → **effective,不停**。

因果链:p3r1 同轮两单元 + 第一单元落了一条 gold_delta 冲突行 + 第二单元健康不落行 + 钩子 join 键无单元身份、600s 窗足够宽 → 第二单元的「关店金」被偷换成第一单元的关店金 → 金差 0 → 误判误停。

## 4. 候选根因逐个排查与证据定性

| # | 候选 | 定性 | 证据 |
|---|---|---|---|
| ① | 点击落空(商店已变/槽位坐标错) | **排除(强)** | 日志 46895:bench 像素差确认 `{'星期日': 3}` 已上席;46896 OCR 金 44、`获得经验4`、经验 10/72 —— 买与升都生效 |
| ② | 金币读数 OCR 错(读多了→以为买了) | **方向对但层级错(强)**:错不在 OCR(OCR 两次实读 44,正确),错在**钩子根本没用 OCR/单元账,用了陈旧 join 行**。flag 里「关=51」≠ 画面 44 | 46902/46915 OCR=44 vs flag gold_close=51;obs_conflicts 唯一行 ts=19:09:57 |
| ③ | 计划与执行之间画面切换(节点推进) | **排除(强)** | 19:11:12 plan → 19:11:12.5 Buy click → 19:11:13 LevelUp click → 19:11:15 收起,同单元内连贯,无节点推进插入 |
| ④ | 商店锁/恢复态禁买 | **排除(强)** | 无任何守卫拦截记录(`守卫拦0`);购买成功落席 |
| ⑤ | 其他(真根因) | **成立(强,即本报告结论)**:安灯金差对账的 join 键缺单元身份 + 数据源条件性落行(仅 mismatch 才写)→ 健康单元消费陈旧 mismatch 行 | §2/§3 全链 |

证据强度说明:①③④为日志直接观测(强);⑤为日志+档案+代码三方互证、且能定量复算出误判路径(强)。

## 5. 根因结论 + 修法方向(不改代码,清单)

**根因层**:表示/约定层 —— 遥测 join 约定缺陷,不是执行层故障。本次购买执行链完全健康。属**安灯(停机钩子)自身数据面误报家族**的又一变体:与已修的「局22 误停」(W577/ADR-0456 豁免 plan_truncated)同族但不同支——那次是「计划≠尝试」口径,这次是「陈旧 join 行」口径。

**修法方向(按根治优先序)**:

1. **根治(推荐)**:钩子的 gold_close 改用 `spend_ledger.jsonl` 单元行自身的 `gold_close`(该行每单元必写、带 run_id/plane/round/unit_seq、且本案里就是对的 44)——钩子本来就已经在读这个行拿 `executed` 字段(`_spend_unit_row`,query.py:870),扩用其金字段即可,join 键天然带单元身份,一举消掉「条件性落行 + 无单元身份」两个病根。
2. 次选:让 `shop_spend_audit` 的 gold_delta 行**无条件每单元落行**并补 run_id + unit_seq 字段,`_match_conflict` join 键升级为 (run_id, plane, round, unit_seq)。缺点:obs_conflicts 是「冲突才记」的 journal,改成全量落行违背其语义,污染面大。
3. 保守补丁(仅止血,需显式声明战术权衡):`_SPEND_CONFLICT_TS_WINDOW_S` 从 600 收紧到单元典型时长(≤60s)。**不推荐单独使用**:同轮两单元间隔可低至 ~20s(本案第二单元整个才 19.7s),收紧也挡不住,且跨局消歧更脆。

**风险与关联面**:
- `classify_spend_unit` / `query_spend_ledger` 离线视图共用同一 join 面(query.py:916-920 起),修 join 键需同步核对离线支出报表是否也被陈旧行污染(本案第一单元那条 `old=48 new=51 spend=22` 的「动作账vs读数不等」本身也可疑:48→51 净+3,plan 净-20 左右,gap 巨大但 verdict 只「留证」——建议顺带复核该行是否也是 join/口径产物)。
- 附带发现(隐患,非本案根因):本局多个「同轮第二单元」的 `unit_seq` 仍为 1(spend_ledger p1r1/p2r1 各有两行 unit_seq=1)——unit_seq 未按轮内单元递增,`_spend_unit_row` 靠「取最后一行」侥幸取对;任何按 (round, unit_seq) 去重/对拍的消费方都会撞键。修法 1 落地时应一并核此处。
- 运维面:按 od-dev-stop-hooks,根因修复并验证后需删 `cw_exec_fail_hook.flag` + 删安灯整段钩子;修复上线前重开新局,旧局素材价值已由本报告固化。

**主要证据文件索引**:
- 日志:`.log/mcp_server.log` L46870–46929(旧进程日志 `.debug/sr_od_mcp/main_server.log` 与本案无关)
- 代码:`src/sr_od/application/currency_war/prep_director.py` L1700–1765;`run_state.py` L32–49;`telemetry/query.py` L691、L751–817、L821–912
- 档案:`.debug/temp/currency_war/replay/{spend_ledger,decisions,obs_conflicts}.jsonl`(run_20260901_180236)
- 哨兵:`.debug/temp/cw_exec_fail_hook.flag`;截图 `.debug/images/exec_fail_run_20260901_180236_p3r1u1_1788261083370.png`
