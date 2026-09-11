# ADR-0486: 按局存档(match archive)——终局旁路装配单局自包含档案

## 状态
accepted (2026-09-08)

## 背景
复盘一局需要在查询侧手工重复四件事:server 重启把一局切成多个 run 段
(实证:run_20260830_094754 + run_20260830_101513 为同一局两段)靠末态
人工拼段;hp=100 备帧 miss 兜底值需人工滤假;decisions.jsonl 跨 run 累积
需逐局手工抽帧;rounds/supply/anomalies/economy 各视图每次查询现算。
实时流式文件(decisions.jsonl 等)是哨兵/早停/对账网的数据源,不能动。

## 决策
档案 = **终局旁路产物**,落地 `telemetry/match_archive.py`:

1. **触发双路**:局终钩子(battle_loop 在 `on_match_end` 调用点之后调
   `assemble_pending`,try 包裹失败不阻塞收口)+ CLI 离线装配
   (`assemble [--game]`,崩溃局/补装配兜底)。
2. **game_id 跨段继承**:段首帧非 (p1,r1) 起 = 续局,继承上一段所在局;
   game_id = 首段 run_id 时间戳派生(`g_YYYYMMDD_HHMMSS`),纯数据派生
   跨重启稳定。
3. **自包含切片**:档案内嵌该局全部关联 jsonl 行切片(decisions/outcomes/
   shop_snapshots/exogenous/invest_cards/spend_ledger)+ 装配逐轮表
   (node_type/hp 真值链带可信位/金/等级/买卖明细含 shop 刷新波/动作/
   配对/姿态/form_score)+ 开局面 + 终局面(outcome/败场节点列表/
   abandoned 标记)。obs_conflicts 为跨局 journal 不入切片。
4. **消费同源**:`--match` 把切片物化到临时目录后走**同一套** query_*
   视图函数,与 `--run` 聚合输出逐字节一致;`--recent` 改读
   matches/index.jsonl(一行一局摘要)。
5. **写盘原子性**:tmp + `os.replace`;水位线记账(`.watermark.json`)
   实现「旧数据不回填」——首次装配只记账,此后只装水位线后结束的局。
   abandoned 局也装配(ADR-0235 口径标 abandoned)。

## Considered Options
- **A(采纳)旁路装配+切片自包含**:`--match` 复用 query_* 保逐字节一致,
  不建第二套视图实现;档案是切片+装配表双层,判读要新维度不用改档案。
- B(拒)档案只存装配好的摘要表:体积小,但任何新复盘维度都受档案
  schema 限制,违背「新复盘需求=新视图」纪律。
- C(拒)改实时流为按局分文件:动哨兵/对账网数据源,运行时风险不可接受。
- D(拒)on_match_end 挂策略类内部:decision 桶是策略面,装配是观测面,
  挂调用点侧(battle_loop)保持桶边界。

## 后果
- 正常局局终自动入档;崩溃局由下次任一触发点补装,更早漏网用
  `assemble --game` 点名;首次启用存量局不回填(旧段 shop 刷新波已丢)。
- 档案体积 ≈ 单局 decisions 切片(百 KB~MB 级);保留策略已记账未实现:
  index.jsonl 永久保留,match_*.json 超窗口删档留行,细节可从 replay
  原始流重装配(见 match_archive 模块 docstring)。
- 验证:sr-od-test `test_cw_match_archive.py`(分组/真值链/原子写/水位线/
  切片视图同源);游戏 G 实测装配与 W764 手工复盘逐轮对照一致,
  `--match` 四视图与 `--run` 聚合逐字节一致。

## 附录:schema v2(match archive 二期;主仓 7a0c1002)

加法式字段扩展,`SCHEMA_VERSION` 1→2,旧档案向后兼容:

1. **决策流程明细入档**:`rounds[].decision_detail` = 该轮最优决策帧的
   `v3_intention`/`candidate_scores`/`eval_breakdown`/`dp_posture`——全帧
   本就在 `slices.decisions` 切片里,v2 只把判读高频字段提到逐轮表,免
   「查明细先翻切片」;None = 该轮无决策帧。同批 `rounds[].bench`/`equips`
   (备战席逐张/装备栏 owned)从 state 快照提到逐轮表,与 board/deployed
   并读——阵容质量三维的 bench 维此前只能翻切片。
2. **策略版本戳**:`telemetry/version_stamp.py` 单一源(git 短哈希 +
   registry 指纹 sha256 前 12 位);`runs.jsonl` 加 `code_commit`/
   `registry_fingerprint` 两列(recorder 局终写时点打戳——决策明细语义随
   版本解读,戳必须是「跑这局的版本」而非装配时点版本;旧记录读端容忍缺列);
   档案顶层 `strategy_version` 取自 runs 行**段序倒查**(末段优先=终局时点
   版本),index 同步两列。**向后兼容语义:旧数据两值为空 = 版本未知,不冒认**。
