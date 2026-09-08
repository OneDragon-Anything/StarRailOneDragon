# 模拟测试怎么用

> CW skill 的模拟测试说明。读者 = 智能体。sim 的价值 = 在实机之前发现问题;任何改动上实机前问「模拟里能不能先暴露它」——能模拟到的就模拟,别拿实机试错。批怎么排、谁常驻跑 → autonomous-loop「sim 批组织细则」;**改动怎么验证(A/B)→ strategy-work「验证」**。
>
> **用法总纲**:统计指标是公共底座——没改动时,走「一、找问题」三步;有改动时按 strategy-work「验证」做 A/B(改前改后各跑一次统计对比),仍然差的指标回到三步下钻。

## 先知道边界(sim 能信什么)

- **可信(真代码层)**:策略决策、发牌概率表、有限牌池、角色注册表、XP 表、板深 Δ 池(三态 `resolve_pool`;改快照后 `reset_resolved_cache()`)。
- **校准层(参数注入,带误差)**:开局 bench/收入模型/战斗结算/节点序列。
- **代理近似(消费前核语义)**:`st.deployed` 代理名单;板深=`_deployable_depth` 可部署口径(≠已部署,视图带 `*`)。
- **未建模**:装备效果、星级、词条/boss 克制、P2/P3 专属;P2 备战与 P1 共享(spend 正常非零),但结算键仅 3 维——涉 P2 战力判读须声明。
- Δ 池按深度分桶:±2 深度测不出;「散面 vs 集中」与实机可能反向——这类维度以实机为准并记录偏差。
- **重放 = seed + 池指纹(缺一不可)**:`cw_sim replay --seed N --pool snapshot`;跨日对照必核 `pool_fingerprint` 一致;校准数据缺源大声报错(静默回退=假信心);sim 批绝不写生产 replay 目录。

## 一、找问题(三步主线)

**主线**:统计指标 → 找出表现不好的指标 → 挑一局复盘归因。

### 1. 统计指标
`uv run python skills/sr-od-currency-war-dev/scripts/cw_batch_stats.py --sim-batch latest`(生产档案 `--recent N`,含按开局词缀分组——sim 未建模词条)。六族指标,每局每指标都有值;口径边界见脚本头注记。

### 2. 找出表现不好的指标
从第 1 步的指标里筛出表现不好的(怎么筛不规定:与设计预期对照、与历史批/同批分布比,哪种都行)。

### 3. 挑一局复盘——归因到决策
对表现不好的指标,拿体现它最重的那一局做复盘(脚本按指标点名最差局):sim 局=批次目录里该局的记录,实机局=对局档案;按 match-review.md 复盘协议读,带上面边界——sim 边界造成的现象不立为策略病灶。直查:`cw_telemetry query --sim-batch <名|latest> --view rounds|economy|supply|...`。复盘骨架与可疑项预填生成器:`uv run python tools/cw/review_skeleton.py --decisions <decisions.jsonl> [--run-id <rid>]`(跑 sim/checks/suspects.py 检测器集 D1-D11,条目嵌对应节点小节判定三槽前;ADR-0593)。
