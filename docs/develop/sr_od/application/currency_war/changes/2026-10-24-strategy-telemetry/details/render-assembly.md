# 复盘报告装配（详设）

## 问题与约束
- 总纲划给本篇的接口契约：DecisionRecord 行格式、存储路径 `<recorder 根>/strategy/<strategy_id>_<run_id>.jsonl`、**两级 join 语义**（动作级 dtag / 章级 entry→章键表）（design.md §2）。
- 渲染器现状：`tools/cw/replay_to_md.py`，报告按画面章组织（`#### 0 观察` + 动作节×N + `#### 策略评价`，动作节 = 回执行；match-review 协议阶段 2）；运行需 `PYTHONPATH=src`；实机局 `--match` 与 sim/裸局 `--journal` 同一渲染通道；生产 live 根 journal 含多 run 段。
- 回执覆盖面（join 的边界事实，capture-store §2）：全仓仅 4 处产回执（prep 统一口/close_shop/open_shop/shop 落地门）；12 个选择族入口不产回执——**章级挂载是这 12 类画面的唯一装配通道**，不是边角形态。
- 用户裁定面：报告无收尾章、复盘者义务产物落文末「复盘者附加」（2026-10-16）——「策略依据」是**渲染器产出**（与 0 观察同地位），不属于复盘者义务产物，不进「复盘者附加」。

## 方案

### 1. 发现与加载
- 新参 `--strategy-telemetry <路径>`：文件或目录皆可，显式优先。
- 缺省发现 = journal 同根 `strategy/` 目录下全部 `*.jsonl`（journal 路径 = `<根>/state/journal.jsonl` → 探测 `<根>/strategy/`）；目录不存在或为空 → **功能关闭，报告与现状零差异**（向后兼容硬要求；局头亦不加行）。
- 加载：逐行 `json.loads`；`envelope.run_id` ∈ 本局 run_id 集（局头运行段）过滤（live 根多 run 段场景）；按 `dtag` 建动作级索引、按 `(entry, node)` 建章级索引；非法行跳过不致命。

### 2. 章级挂载表（entry → 画面章键；14 行闭集）
章键 = 渲染器章名（SCREEN_REGISTRY/ACTOR_REGISTRY 现名，`replay_to_md.py:211-310`）：

| entry | 章键 | 依据 |
|---|---|---|
| decide_prep_screen | 画面-备战 | SCREEN_REGISTRY 货币战争-备战 |
| decide_shop_action | 画面-商店 | SCREEN_REGISTRY 货币战争-备战-开商店 |
| decide_invest_env | 画面-投资环境 | SCREEN_REGISTRY 货币战争-投资环境 |
| decide_invest_strategy | 画面-投资策略 | SCREEN_REGISTRY 货币战争-投资策略 |
| decide_supply | 画面-补给 | SCREEN_REGISTRY 货币战争-补给 / ACTOR_REGISTRY CwScreenSupplyNode |
| decide_encounter | 画面-遭遇 | 同源 CwScreenEncounter |
| decide_megastar | 画面-巨星 | 同源 CwScreenMegastar |
| decide_partner | 画面-伙伴 | ACTOR_REGISTRY CwScreenPartner |
| decide_planner | 画面-银狼策划 | ACTOR_REGISTRY CwScreenYinLang |
| decide_fortune | 画面-命运卜者 | ACTOR_REGISTRY CwScreenFortune |
| decide_wish_trial | 画面-祈愿试炼 | ACTOR_REGISTRY CwScreenWishTrial |
| decide_box_card | 画面-箱子 | ACTOR_REGISTRY CwScreenBoxPick / SCREEN_REGISTRY 货币战争-备战-武装箱选择 |
| decide_expert_invite | 画面-专家邀请 | SCREEN_REGISTRY 货币战争-备战-专家邀请函 / CwScreenExpertInvite |
| decide_star_tome | 画面-书卡 | **CwScreenBookcard 实写 star_tome_opts**（`cw_screen_report/bookcard.py:49-71`）——「书卡」画面即星徽秘典选择；`replay_to_md.py:291` 该行键集错置为 box_card_names 属存量错行，3.4 修复（见下） |

渲染器侧随本表的两处配套修订（3.4 阶段，属本迭代目标改动、记入零差异承诺的例外清单）：
- `SCREEN_REGISTRY` 补 sim 广播行 `'货币战争-星徽秘典弹窗'`（广播名来源 `kernel/cw_game_state.py:323`）→ `画面-书卡` / 键集 `('star_tome_opts',)`；
- `ACTOR_REGISTRY` `CwScreenBookcard` 行键集 `box_card_names` → `star_tome_opts`（存量错行修复：书卡键集错置使书卡章 0 观察显影错键；同 title 同规格纪律下两行必须一致）。`画面-箱子` 行与 `box_card_names` 键不动（武装箱写端 = `box_pick.py:68`，两屏本就不共键）。

映射表实现 = 渲染器侧常量 `ENTRY_SCREEN_MAP`（本表直译）；章键在注册表缺失/更名时以注册表为准修正本表（修订走本迭代设计变更，不静默）。

### 3. join 与报告块
- **适用集钉死（两级互斥）**：动作级 join 仅适用映射表行 1-2（decide_prep_screen / decide_shop_action——对应 4 个回执产出口）；章级小节仅适用行 3-14（12 个选择族入口，不产回执，capture-store §2 适用域申报）。prep/shop 的记录无回执匹配时（空动作/受阻后未重发/被截断）一律章尾「策略决策未落地」注记，**不**落入章级小节。
- **动作级（行 1-2）**：回执行 `dtag` → `envelope.dtag`；匹配 record 的依据块嵌入该动作节（标题行下、状态变化表前）。受阻回执（reason 非空）同样带 dtag；**重试链一节多回执**（渲染器既有「失败重发合并一节」形态）= 节内多回执各带 dtag → 依据块按回执顺序逐条列出（每条标各自 dtag），无 dtag 回执跳过。
- **指纹一致性校验（动作级兜底）**：回执 `op` 存在两种命名域——prep 统一口与商店落地门写动作类型名（`type(action).__name__`），open_shop/close_shop 写执行体 op 名 `'CwOpOpenShop'` / `'CwActionCloseShopOp'`——校验前先经归一映射 `{'CwOpOpenShop': 'CwActionOpenShopParam', 'CwActionCloseShopOp': 'CwActionCloseShopParam'}`，其余回执 op 即动作类型名字面相等；核 `归一后 op == envelope.emitted.op`，不符（陈旧 dtag 搭错等异常形态）→ 该回执按无依据处理 + 章尾注记 `- 策略 dtag 失配: <dtag>(<op>)`——join 键的权威校验，capture-store §2 陈旧槽残余面的最后防线。
- **章级（行 3-14）**：索引键 = `(entry, node)`；**同键多章实例按 FIFO 归属**——同 node 内备战→商店→备战会产生两个同 title 备战章（章相邻合并键 = title，`replay_to_md.py:208-210`），候选章按章首现序排列、records 按 dseq 序依次分配（决策序 = 画面访问序，单线程不变量；sim 冻结时间下 ts 不可分辨，故用序不用 ts）。匹配 records 在章内 `#### 0 观察` 之后渲染为独立小节 `#### 策略依据`（每条 record 一组：dtag + emitted 行 + payload 键值渲染），按 dseq 序全列。
- **node = null 帧**：不入章级挂载（无归属锚），计数并入局头策略遥测行「未归属 M 条」（§4），不逐条展开（完整性申报面）。
- **payload 渲染**：通用键值（dict 一层键值行、嵌套缩进 JSON），渲染器不解释语义——schema 语义归各策略文档（mandate_v1 = `strategy-docs/strategy-telemetry.md`）。
- payload 空记录：单行 `(本帧无策略载荷)`。
- **未落地决策**（动作级无回执匹配的行 1-2 记录，见适用集钉死）：章尾注记 `- 策略决策未落地: <dtag>(<op>)` 汇总。
- 用户需求「观察、策略依据、动作」的形态映射：备战/商店章 = 依据随动作节（动作前）；选择族章 = 依据为观察后的独立小节；两者与需求语义一致且不破坏「0 观察 → 动作×N → 策略评价」协议结构。

### 4. 局头
- 增一行 `- 策略遥测: <strategy_id> (N 条)`；存在 node = null 记录时行尾追加 `(未归属 M 条)`；无策略文件时整行省略（与「数据完整性」行同风格，此时报告与现状逐字节一致）。

## 关键取舍
- **章级单块 vs 动作节级块（有回执形态）**：商店访问一章多决策（单动作循环，`cw_screen_shop.py:602`），章级无法承载逐动作依据，弃。
- **per-strategy 渲染注册**（ACTOR_REGISTRY 同模式）：v1 通用渲染够用；注册制留后续迭代（payload 语义已按策略文档归位，扩展不返工）。
- **依据块独立成节 vs 动作节内小节（有回执形态）**：独立节会把既定章结构改成「观察 → 依据×N → 动作×N」交错形态，动作与依据对应关系变松；动作节内小节保持协议结构、对应最紧，取后者。
- **pick 族补回执 vs 章级挂载**：为 12 入口补 `note_action_receipt` 调用 = 12 个画面 op 各加生产接线步（违 R191 精神、流程层大面改动），弃——章级挂载零流程改动即满足「观察、依据、动作」需求。
