# W505 Phase A:观测自检框架设计(表面×真值源全枚举 + 统一缺陷台账 + 分级安灯标准)
> 类名已随 2026-09-03 命名迁移更替,对照 NAMING.md(本文为带日期记录,类名保持当时事实,未改)。

> 纯设计批:只读 src 与 replay,只写本目录;Phase B(实现)另批放行。
> 证据链:本设计的每一条「现状」论断都标注了代码出处(文件+符号);「缺口」论断标注了
> 反证检索方式(grep 什么没找到)。读者只需代码与本文件即可重建全部推导。
> 用户裁决(立件依据):识别错误与执行失败=实机缺陷,要修到零;能加 hook 的都加——
> 不插桩的「策略优化」是在噪声上拟合。金面已有系统对拍(W494 spend_ledger + W501 读取链
> 根因修复中),本设计把同样的纪律推广到其余观测面。

---

## 0. 一句话

把「每个决策相关面都有第二条真值或硬不变量在盯」变成全量清单(§1 矩阵),把散在三处的
冲突/失败记录收拢成统一缺陷台账(§3),按「决策关键性 × gap 大小 × 复现性」三级安灯
(§4),并给出 Phase B 落地顺序(§5)。天然盲区显式披露(§6)。

---

## 1. 表面 × 真值源全枚举矩阵

判读约定:
- **决策相关性**:该面读数错误是否会直接喂错策略决策(高=直接改买/升/部署决策;
  中=改辅助判断如保血阈值/成型判定;低=只影响复盘统计)。
- **真值源类型**:第二读数(同帧另一独立读法)/ 跨帧真值(结算屏/对拍点)/
  硬不变量(物理不可能违反的约束,如 plane∈1-3、deployed≤cap、HP 只降不升)/ 无。
- **缺口等级**:✅可审计(有第二真值或硬不变量,现有对拍或加钩子即可)/
  🔶可双读设计(需要新增第二读法或新增读屏)/ ⬛天然盲区(单读无第二真值,见 §6)。

| # | 表面 | 决策相关性 | 可用真值源 | 现有对拍 | 缺口等级 |
|---|---|---|---|---|---|
| 1 | **金(gold)** | 高 | 跨帧:shop 关店对拍点 `read_gold`(shop.py L776 `spend_audit`);结算屏 `gold_detail`(base/streak/interest 三分量,cw_settlement_obs);不变量:gold∈[0,400](GOLD_MIN/MAX)、plan 金流守恒(±2 容差) | **有**(obs_conflicts `gold_delta` source=shop_spend_audit + spend_ledger 单元账 + classify_spend_unit 三态 + mismatch 安灯停机钩子);W501 在修读取链根因(窄区裁 3 位数首位,replay_gold_clip.py 实证) | ✅可审计(金面是范本;残余缺口=spend_ledger.gold_close 恒 None 的 unknown 面,W494 DESIGN §5 已挂账 shop.py 钩子) |
| 2 | **备战席构成(bench)** | 高 | 第二读:SIFT 实读 vs session.tracked_bench_chars 对账(reconcile_tracking);买牌落点 pixel-diff `new_bench_slots`(cw_observation L1356)是身份无关的落位真值;不变量:bench 占用数 ≤9、每 char 成本∈注册表 | **部分**(reconcile_tracking 有双空读守卫+纠漂留证;star 回退防抖+帧态门);**无**「买后 bench 逐槽回读验证」——buy 动作声称买了 X,bench 上 X 是否真出现,只靠下一次 heavy 观察隐式覆盖 | 🔶可双读设计(买牌执行点即时回读 bench,与 plan 对拍;复用 new_bench_slots 的 pixel-diff 作落位证据) |
| 3 | **上场板面(board/deployed)** | 高 | 三源:paddle「X/Y」部署数指示(read_deployed_count/cap,真值锚)+ tracked_deployed(SIFT)+ 徽标行 OCR(computed_vs_ocr 仲裁);不变量:deployed≤deploy_cap、cap∈[level, level+2] 域(域外双帧一致才采信,ADR-0420)、cap≤13 | **有**(deployed_align 截断/补齐留证 + board computed_vs_ocr 仲裁 + cap 域防抖);**但 deployed_align 与 board 徽标冲突是「裁决已自动、频发才排查」的纯留证,无分级升级** | ✅可审计(源已齐;缺的是台账分级与「对账纠漂」从留证升告警的通道) |
| 4 | **等级/XP/升级付费** | 高 | 三源:等级 OCR 直读 + XP 分母反推(XP_TO_NEXT_LEVEL 强先验)+ `_expected_level` 启发式(_resolve_level 仲裁,毒化防线);付费不变量:LevelUp 应使 XP cur+cost 步进或 level+1、gold 按费用下降 | **部分**(level 三源解析+XP 覆盖+单调/跳变守卫);**无 LevelUp 付费审计**——点「购买经验」后 XP 条是否真步进、gold 是否真扣,零验证(shop.py L527-529 只 log click) | 🔶可双读设计(升级点击后同帧/次帧回读 XP+gold,期望-观测对:ΔXP=费用档、Δgold=level_up_cost;复用 read_xp_progress/read_level_up_cost,零新增 reader) |
| 5 | **血量(hp)** | 中(保血/出口线) | 跨帧:结算屏 `hp_after`(parse_settlement_hp,conf 门);硬不变量:HP 只降不升(结算语义)、下行须有战斗事实背书(幅度×节点型损血谱,ADR-0431) | **有**(reconcile_hp 三层:保旧/下行拒信+复现确认通道/上行留证;hp_trusted 帧龄门);**无冲突台账分级**——下行拒信、上行留证全进 obs_conflicts 同一平面,无 gap 大小分级 | ✅可审计(reconcile 是范本级;缺台账分级归 §3 收拢) |
| 6 | **商店牌面与刷新** | 高(买决策输入) | 牌面:SIFT 肖像识别(5 牌位,内点数 30-120);不变量:cost∈注册表、shop 开态锚「按钮-收起」门;**刷新有效性**:刷后牌面应≠刷前(r97 已落盘 refresh 波快照到 decisions,但**无「变化验证」**——点击落空时新波=旧波,数据上不可分) | **部分**(空槽检测灰带留证、未知卡停机钩子已删归因闭环);**刷新有效性完全裸奔** | 🔶可双读设计(Refresh 点击后重读 shop 5 牌,与刷前集合比对:全同=刷新未生效(费用扣了没刷/点击落空)→ 台账;复用 read_shop_cards,零新增 reader) |
| 7 | **节点/轮次(plane/round/node_type)** | 高(支出 gate/level_plan 地基) | 双源:备战顶栏「X-Y」OCR + 结算屏头部「X-Y」(parse_settlement_round);硬不变量:plane∈1-3 单调、round 同位面单调、boss=位面末节点(≥9 轮,P1 模板 cw_node_validate) | **有**(phase_round 值域守卫+单调守卫+fallback 拒;node_type 轮次门+标签位置锚;离线 validate_p1_node_sequence 校验语料) | ✅可审计(在线守卫齐;离线校验器已有;仅「结算屏 vs 备战顶栏同轮双读对拍」未接——两源各写各的,不等才留证的通道缺) |
| 8 | **装备(穿戴/合成)** | 中 | 第二读:deploy_bench 装备快照 `_snapshot_equips_into_tracking` + `_merge_equips` 续接;不变量:每角色 equips≤3?装备总数守恒(合成 2→1、穿戴不上减)? | **无对拍**(W209g 断点修复只是「保住已写入的」,没有「写的是不是对的」验证;round6 希儿装备闪烁实证过对账链脆) | 🔶可双读设计(穿戴/合成动作执行点前后各读一次角色详情装备区,期望-观测对;成本高,Phase B 后期) |
| 9 | **投资策略激活态(active_strategies)** | 中(效果解/押韵依赖) | 真值源:仅 session.active_strategies(handle_invest_strategy 写入的事件记录);**屏面无第二读**(持卡列表在画面上无已建档 reader);不变量:策略数≤上限、效果台账 ledger_fingerprint 随持卡变化 | **无**(ledger_fingerprint 恒 'base' 的 67-P1c 接线哨兵仍挂账;策略误选/漏选无法发现) | 🔶可双读设计(投资策略画面持卡区建档+回读;或最低配:选择事件落盘选项 vs session 终态对拍——exogenous event_choice 已有结构化载荷,W312) |
| 10 | **识别置信度(SIFT/OCR 分数分布)** | 低(但全表象的地基) | 第二真值:无(分数本身就是置信);可用不变量:分布监控——内点数阈值(真卡 30-120 vs 空槽 3)、灰带 50-60 暗卡 | **无落盘**(read_shop_cards 的 inliers、SIFT 各读法的分数只进瞬时 log,不进任何 jsonl;离线无法统计「哪个 reader 在哪个画面退化」) | 🔶可双读设计(分数进缺陷台账字段,分布漂移=留证;这是所有其它面的**预警地基**) |
| 11 | **节点行序列(备战顶部未来节点)** | 中 | 第二真值:位面详情屏节点条(read_plane_detail_nodes,同 CV 核心互证);模板众数(cw_node_validate P1_NODE_TEMPLATE) | **部分**(clean 门+Hu 距离未识别兜底+标签位置锚);跨屏互证只在采集通道用,**备战帧与位面详情帧的序列对拍未常态化** | ✅可审计(两读法都在,只差对拍钩子;低成本) |
| 12 | **streak(连胜/连败)** | 低-中 | 双源:结算屏带符号(parse_streak)+ 备战 magnitude(read_streak) | **有**(双源不等留证,settlement_vs_prep) | ✅可审计(已闭环,只差台账分级) |
| 13 | **enemy_difficulty / 敌方血量** | 中 | 难度:备战 OCR(stylized 常空)+ session 简报恒值(两源已留 live 位);**敌方血量:结算屏无通道(W23 定谳)**,只有伤害代理 | 难度有双源标记;敌血天然盲区 | ⬛/🔶(难度可审计;敌血盲区显式披露 §6) |

**矩阵结论**:金/hp/轮次/板面计数四面的对拍纪律已经成型(是资产);备战席构成、升级付费、
刷新有效性、装备、策略激活态五面裸奔或缺第二读(是本框架要补的主体);SIFT 分数分布
不落盘是全表象面的共同盲点(预警地基缺失)。

---

## 2. 逐面审计规格(可审计面 + 可双读设计面)

通用原则:期望-观测对必须在**动作后即时**(动作点同帧或 +1 帧)检测——等到轮末/局终
对拍,中间已被纠漂/覆盖,证据链断(38 教训:lv4 毒化 3 个位面才被发现)。

### 2.1 金(gold)——已有,规格作为范本记录
- 不变量对:`expected_gold_after_actions(open, actions) vs close 实读`,容差 ±2(shop.py spend_audit);单元级三态 classify_spend_unit(W494)。
- 检测时点:关店即时(每购买单元)。
- 代价:0(既有链)。
- 误报依据:卖入相抵已纳入(shop.py L67 注);残余误报源=read_gold 失读(→unknown 不猜,W494 §3)。
- Phase B 动作:补 shop.py 关店钩子填 spend_ledger.gold_close(W494 DESIGN §5 已备接口)→ unknown 占比降到 read_gold 失败率;W501 根因修完读失败率本身下降。

### 2.2 备战席构成(bench)
- 期望-观测对:每张 `BuyCard` 执行后,`new_bench_slots(before, after)`(pixel-diff,身份无关、可靠)应有 ≥1 新槽,且新槽数累计 = 本单元 BuyCard 数 − 中途卖出数;SIFT 回读槽内身份 = plan 目标件(LCS 名匹配,容一个未识别 '?'——身份留证不算失败,占位不出现才算失败)。
- 检测时点:买牌动作后即时(pixel-diff 本来就要 before/after 两帧,零新增截图);单元关闭再总账一次(与 plan 清单对)。
- 代价:0 新增读屏(复用 buy 前后帧;SIFT 回读复用 ensure_portrait_templates 缓存)。
- 误报依据:pixel-diff 阈值 10.0 已标定(cw_observation BENCH_SLOT_DIFF_THRESHOLD;真卡 icon diff 显著);误报主要形态=动画帧截屏,靠「单元关闭总账」兜底(单槽误判被总账对冲)。

### 2.3 上场板面(deployed)
- 期望-观测对:单元关闭时 paddle X vs tracked_deployed 占用数(deployed_align 已有);**升级项**:DeployMove 执行后 paddle X 应 +1、SellDeployed 后应 −1(动作级即时对,现在只有对账层事后纠漂)。
- 检测时点:部署/卖出动作后 +1.5s(MCP 异步,框架不变量)读一帧 paddle;单元关闭总账。
- 代价:每部署动作多一次「区域-部署数」区域 OCR(~小 crop,毫秒级;部署动作本身秒级,占比可忽略)。
- 误报依据:paddle 已是 W287 裁决的画面事实锚(ADR-0417);域守卫已有。误报源=转场动画帧,paddle 读不到返 None 时跳过不判(宁缺勿造,同现有语义)。

### 2.4 等级/XP 升级付费
- 期望-观测对:第 n 次 LevelUp 后,`Δgold ≈ −level_up_cost`(同单元累计)、`xp.cur` 步进或 `level+1`(XP cur 达 next 时);XP 读不到的帧(已知失读形态)→ 退「gold 确实扣了 + 单元关闭时 level 三源解析无乒乓」的弱对。
- 检测时点:LevelUp 点击后 +1.5s 读一帧 XP 条(已有 reader read_xp_progress,3x 放大管线);单元关闭对总账(升级次数 × 费用 vs gold 差分量)。
- 代价:每次升级多一次区域 OCR;升级是低频动作(每单元 0-2 次),可忽略。
- 误报依据:费用读不到时退 LEVEL_UP_COST_TABLE 兜底(容忍 ±表差,只对「gold 完全没动」这类硬失败报警,不对「扣多扣 1」报警)——**只捕 not_effective 级缺陷,不捕口径差**(与金面 tolerance 哲学一致)。

### 2.5 商店刷新有效性
- 期望-观测对:Refresh 点击后(r97 已在刷后重读 `_new_shop`),`set(刷后牌名) == set(刷前牌名)` → 刷新未生效(点击落空/动画帧误读);连续两次刷新全同才确认(防抖,同 star 防抖语义)。
- 检测时点:刷新动作后即时(r97 落盘点就地加对拍,零新增读屏)。
- 代价:0(r97 已读)。
- 误报依据:真刷出相同 5 牌的概率 = Π p(牌)×5!组合级小概率,连续两次更低;误报可容忍(留证级别)。

### 2.6 血量(hp)
- 已有 reconcile_hp 全规格(三层+战斗事实联合守卫)。Phase B 只做 §3 台账收拢:下行拒信/上行留证按 gap 与复现性分级,无新读屏。

### 2.7 节点/轮次
- 期望-观测对(新增的唯一一条):同轮结算屏头部「X-Y」(parse_settlement_round 产物)vs 备战 phase_round 缓存,不等 → 留证(W28 残留屏场景已知,判定窗限「非 relaunch 首帧」)。
- 检测时点:结算屏记录时点(同帧 OCR 已有,零新增)。
- 代价:0。
- 误报依据:值域守卫已在正则字符类内;误报主要来自 relaunch 残留(已被 source 标记区分)。

### 2.8 装备(Phase B 后期)
- 期望-观测对:穿戴动作后角色详情装备区读数含目标装备;合成动作后装备总数 −1 且产物星级/身份符合配方(cw_recipe)。
- 检测时点:动作后即时(需角色详情屏 reader——**当前不存在**,要先建档,成本最高,排最后)。
- 误报依据:暂缺(依赖建档后多 fixture 标定)。

### 2.9 投资策略激活态(最低配先行)
- 期望-观测对:投资策略画面选择事件(exogenous event_choice,W312 已落盘 pick)与单元后 session.active_strategies 增量一致(选了 X → active_strategies 出现 X);不一致 = 写链断或选择落空。
- 检测时点:投资单元关闭时(session 写入后)。
- 代价:0(两端数据都已存在,纯对拍)。
- 屏面回读(持卡区建档)排 Phase B 末期,先跑事件级对拍。

### 2.10 识别置信度分布
- 规格:SIFT 内点数、OCR 各 reader 的「读空率」进缺陷台账字段(`confidence` / `readable`);不设即时告警,离线分布监控(某 reader 读空率环比翻倍 = reader 退化的最早信号——W501 金读数窄区裁切这类系统性缺陷,分布上会先于大额漂移暴露)。

---

## 3. 统一缺陷台账 schema

### 3.1 现状:三处散口径
| 流 | 口径 | 问题 |
|---|---|---|
| obs_conflicts.jsonl(cw_observe.obs_conflict)| `field/old/new/verdict/source` + 散 ctx | 感知冲突专用;无 gap 数值化、无分级、无 run_id(靠 ctx 里偶带 plane/round_num)、无截图必带 |
| exec_events.jsonl(ExecEvent)| `action_family/screen/event/reason/retry_count` | 执行失败专用;无 expected/observed(gap 语义要靠 reason 文本猜)、无截图 |
| gold_detail.jsonl(collect_gold_detail_hook)| 结算金三分量 | 不是缺陷流,是真值采集流——但判读时常被当证据引用,无统一引用键 |

三流 join key 各异(obs_conflicts 无 run_id、exec_events 有 run_id+round 无 plane),W489 式
审计要人肉对齐三流(其 §1.2 四层分类账就是这个成本)。

### 3.2 统一 schema:defect_ledger.jsonl(新流)

```jsonc
{
  "schema_version": 1,
  "ts": "ISO 时间",
  "run_id": "run_YYYYmmdd_HHMMSS",        // join key 主键(现有流缺的补齐)
  "plane": 0, "round_num": 0,             // join key
  "unit_seq": 0,                          // 购买单元序(可空;spend 面专用)
  "surface": "gold|bench|deployed|level_xp|hp|shop_refresh|phase_round|equip|strategy|confidence|node_seq|streak",
  "kind": "perception_conflict|exec_fail|invariant_break",   // 三类=现有三流口径的归一
  "expected": "<期望值/不变量描述>",
  "observed": "<观测值>",
  "gap": 0.0,                             // 数值化差(可空;文本面=不填,gap 用 expected/observed 表达)
  "severity": "L0_andon|L1_alert|L2_record",   // §4 分级;写入端给初判,离线可重判
  "verdict": "<裁决(保旧/采新/拒信/待研)——沿用 obs_conflict verdict 语义>",
  "evidence": {
    "shot": "<shots/xxx.png 可空>",
    "refs": [{"stream": "obs_conflicts|exec_events|spend_ledger|gold_detail|decisions",
               "key": "<该流内定位:(plane,round,unit_seq/field)>"}]   // 原流行引用,不复制数据(单一源)
  },
  "reader_source": "<shop_spend_audit/computed_vs_ocr/... 沿用既有 source 词表>",
  "note": "<处理提示,一行>"
}
```

设计要点:
- **新流,不扩旧流**:旧三流是「原始证据层」保持原样(append-only 兼容,新字段末尾追加
  原则不破);defect_ledger 是「归一索引层」,每行通过 refs 指回原流行——审计先查台账,
  下钻再回原流。这避免给 obs_conflicts 补 run_id 这类破坏性 schema 改动(obs_conflicts
  写入点 10+ 处,逐处加参数是高风险机械改动)。
- **写入端单一入口**:`cw_telemetry.record_defect(...)`(与 record_spend_unit 同模式,
  模块级便捷函数自动取 current_run_id)。现有 obs_conflict / record_exec_event 不改签名,
  在**两函数内部**各加一行「同时落 defect_ledger」的旁路(映射表:field/surface、
  reason/kind),零调用方改动。
- **severity 写入端只给初判**(§4 规则表),离线可用同一规则重判(规则纯函数可单测)——
  分级标准演进时不重写历史,重放即得。
- **防刷屏**:同 (surface, kind, expected 特征) 慢性态在台账层只首行 + 每 N 行采样一行
  (复用 obs_conflict 截图节流的 (field,verdict) 300s 思路;JSONL 行本身便宜,节流的是
  截图与告警,不是行)。

### 3.3 兼容策略
- 既有消费端(判读脚本、cw_sim_checks、query_spend_ledger)零改动——它们读旧流照旧。
- defect_ledger 的 refs 键含流名+定位,原流行永不删除,索引失效不可能(append-only)。
- W489 式审计的复现成本从「人肉对齐三流」降到「查 defect_ledger 一张表 + 按需下钻」。

---

## 4. 分级安灯标准

### 4.0 分级判据(三条,按序判)
1. **决策关键面吗?**(§1 矩阵「高」= gold/bench/deployed/level_xp/shop_refresh/phase_round)
2. **gap 大吗?**(数值面:超容差且超「决策可感阈值」——gold>10 金级、deployed 计数差 ≥1
   且不可自动纠、level 乒乓;非数值面:硬失败形态,如「计划花费>0 金差≈0」「刷新两连全同」)
3. **复现了吗?**(同 surface 同特征连续 2 次/2 帧——所有 L0 都过防抖,单帧永远不直接停机,
   这是 star 防抖/hp 复现通道/M35 shop 防抖三处先例的统一)

### 4.1 三级标准
| 级 | 判据(1∧2∧3 全真) | 动作 | 先例 |
|---|---|---|---|
| **L0 安灯停机** | 决策关键面 + 大 gap + 复现,且**无法自动裁决**(裁决已自动的不算:deployed_align 截断/补齐是自动纠漂,不停) | 复用 stop-hooks 方案 D:sentinel flag(三要素:触发定位/可执行处理步骤/删除条件)+ 截图 + `run_context.stop_running()` + 保画面 | prep_director exec_fail 停机钩子(not_effective)、shop 未知卡钩子(已删)——**已存在的两个 L0 收进同一分级框架,行为不变** |
| **L1 台账+告警** | 决策关键面 + 大 gap + **单次**(未复现);或中相关面 + 大 gap + 复现 | defect_ledger 落 L1 行 + `[cw!]` 日志 + 哨兵脚本可消费的告警面(不 stop);同轮再犯升级 L0 | W489 §5 建议「漂移 >10 金局中告警」的落位 |
| **L2 纯留证** | 中/低相关面;或小 gap;或裁决已自动(deployed_align、board 徽标仲裁、hp 上行留证、streak 双源、cap 域外双帧采信) | defect_ledger 落 L2 行,离线统计毒化率,零实时动作 | 现有 obs_conflicts 的绝大多数行 |
| 升级/降级 | **降级(L0→L1/L2)必须用户点头 + 证据结论**(od-dev-stop-hooks §2.3 双条件);升级(L2→L1)离线判读提案、agent 不自改 | — | star 回退钩子 r17 降级先例 |

### 4.2 停机钩子触发点位置(观测层)
统一挂在**缺陷判定函数**里,不散在 op 动作点:
- 金:not_effective 判定处(prep_director 安灯段,已有,不动);
- 其余各面:§2 各「期望-观测对」判定处判定 → `defect_ledger 落行(带 severity 初判)`
  → severity==L0 且防抖计数达阈 → 写 sentinel + stop_running。即:**安灯是台账分级的一
  个消费动作,不是独立机制**——所有停机都先有台账行,现场处理(od-dev-stop-hooks §0
  五步)能直接从 flag 引用的台账行拿到 expected/observed/gap/refs 全部下钻入口。

---

## 5. 实施分期建议(Phase B)

排序原则:决策相关性 × 实施成本,先做「零新增 reader、纯对拍」的(性价比最高),
后做要建档的。

| 期 | 内容 | 动文件 | 动既有 schema? |
|---|---|---|---|
| **B1 台账地基**(先行,~1 批) | `defect_ledger.jsonl` 流 + `record_defect` 入口 + obs_conflict/exec_event 内部旁路映射 + severity 纯函数 + 三先例钩子(金 mismatch、star、hp)收进分级 | cw_telemetry.py(追加)、cw_observe.py(旁路 1 行)、cw_reconcile.py(旁路)、prep_director.py(安灯段接台账) | 否(纯新流) |
| **B2 金面收口** | shop.py 关店钩子填 spend_ledger.gold_close(未知占比归零);与 W501 读取链修复合流 | operations/prep/shop.py(L776 对拍段 +1 处) | spend_ledger 字段已预留,无 schema 变 |
| **B3 升级付费审计** | LevelUp 点击后 XP+gold 回读对拍(§2.4) | operations/prep/shop.py(执行循环 LevelUp 分支) | 否 |
| **B4 刷新有效性审计** | r97 落盘点加「刷前 vs 刷后集合对拍」(§2.5)+ bench 买牌落位对拍(§2.2,复用 new_bench_slots) | operations/prep/shop.py(r97 段)、deploy_bench.py 或 shop buy 分支 | 否 |
| **B5 板面/节点即时对拍** | DeployMove/SellDeployed 动作级 paddle 对拍(§2.3)+ 结算 vs 备战同轮 round 对拍(§2.7)+ 备战/位面详情节点序列互证(§2.11) | prep_director.py、cw_settlement_obs.py 或 battle_loop 记录点、采集/备战观察链 | 否 |
| **B6 策略激活 + 分数遥测** | 投资策略事件级对拍(§2.9,零读屏);SIFT 内点/读空率进 defect 台账 confidence 字段(§2.10) | cw_telemetry.py、invest/strategy handler 各 1 行 | defect schema 追加可选字段(末尾,兼容) |
| **B7 装备链**(最后,需建档) | 角色详情装备区建档 + 穿戴/合成期望-观测对(§2.8) | 新 reader + cw_bench_equips/合成 op | — |

每期验证门:schema/判定纯函数单测(sr-od-test,fixture 走 tmp_path)+ 受影响域测试全量 +
ruff 改动文件;B1 需追加 1 条 ADR(台账分级与安灯统一决策)。

---

## 6. 诚实边界:天然盲区清单

以下面**单读无第二真值**,任何框架都只能留证不能断言;它们对策略优化的残余风险显式声明:

| 盲区 | 为什么无第二真值 | 残余风险声明 |
|---|---|---|
| 商店牌 SIFT 身份(低内点/模板缺) | SIFT 是唯一身份读法;OCR 牌名对自定义名系统性失读(D-55 定谳) | 身份读错会污染 bench tracking 与 comp 匹配——防线只有分布监控(§2.10)+ 未知留证;策略侧对 '?' 身份已有保守降级语义 |
| enemy_difficulty(OCR stylized 常空) | session 恒值非真值(live 位已标记) | 难度爬升曲线分析只能用 live=True 子集;live=False 混入会把曲线拉平(判读纪律已写进 read_game_state 注释) |
| 敌方血量 | 结算屏无该通道(W23 定谳),伤害求和只是代理 | 「输给谁/差多少」的定量归因永久缺失,只能靠 damage_dealt 代理相关 |
| 备战 streak 符号 | 备战屏只显 magnitude;符号唯一真值在结算屏 | 结算漏采轮(streak 断链)符号不可恢复;streak 类策略门在该轮退化为无方向 |
| board 滚动截断区(无 tracked 时) | 混合态(tracked 含 '?')computed=None,OCR 又只读可视区 | 半成型误判风险回到混合态兜底(obs_conflict 留证统计暴露频率),无根治读法 |
| XP/等级双失读帧 | OCR 与 XP 同帧皆空时只剩 `_expected_level` 启发式 | 启发式值**不写回 last_level_obs**(毒化防线),但它仍在当帧参与决策——P1 早期系统性偏高的残余已实测(佩佩局),只能靠「authoritative=False 不锁死」把误差限在单帧 |
| 投资策略屏面持卡(未建档前) | 只有事件记录,屏面真值缺失 | 事件漏记(异常路径)时 active_strategies 与实况静默脱钩——ledger_fingerprint 接线哨兵(67-P1c)是当前唯一报警,修完前策略效果解读以持卡记录为「声明值」非「验证值」 |
| 战斗内实时过程 | 备战/结算两屏外无读数(战斗实时屏未建档,total_damage 是诊断性 fragile 读) | 战斗行为缺陷只能以「战前状态 × 结算结果」对表达,过程级归因(站位/先手)不可观测 |

**总残余风险声明**:盲区内的策略优化结论,其置信上限 = 对应面的「声明值」置信(事件
记录/启发式/代理量),判读时必须按 §1 矩阵标注的数据可信级别分层取样,禁止把盲区面
与可审计面等权混入同一统计。

---

## 7. 结论合格线自检

- 论断均有代码出处(§1 表、§3.1 表、§2 各节);缺口论断均有反证检索说明(如 §2.5
  「无变化验证」= shop.py 刷新分支只有 r97 落盘无比对;§2.4 = LevelUp 分支只 log click)。
- 推理链:缺口等级判据(§1 头)→ 审计规格(§2)→ 台账归一(§3)→ 分级(§4)→ 分期(§5),
  每步可独立被证伪。
- 本批零 src 改动,零行为变更。
