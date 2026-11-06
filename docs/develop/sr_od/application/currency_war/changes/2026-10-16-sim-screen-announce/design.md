# sim-screen-announce 迭代设计（总纲）

## 0. 元信息
- 迭代目标：sim 局复盘报告的画面章补全——sim 引擎把内部画面状态机广播进遥测（用户裁定 2026-10-16 会话，方案 a「sim 侧补遥测」）。
- 状态：定稿（首轮两攻击面 17 项收敛 + 终审通过，残留 5 条随定稿同笔修订；2026-10-16）
- 文档清单：无详设（单文档方案，本文件 §2 即完整设计）
- 对抗报告：[attack.md](attack.md)（17 项发现全部处置）
- **用户裁定偏差申报**：裁定假设「渲染器零改动（已支持）」；实际需两处渲染器改动——①切章证据收窄（**缺陷级**：不收窄则广播引入陈值幽灵章与备战章碎片化，真引擎探针局实证，attack.md A1）；②SCREEN_REGISTRY 扩容（**提质级**：把未注册兜底章升级为正式规格章）。偏差原因 = 裁定时未评估「广播行与 actor 行并存的双证据形态」及「行内快照 cs 累计子集」两个事实。渲染器无其他改动。

## 1. 问题与动机
- 现状症状：sim 局渲染报告的画面章标题 = `(未观察)` 占位（每节点备战/商店章全部命中）；实机局同一渲染器产出正式画面章。
- 根因归层（两层）：
  - **机制层（遥测覆盖面）**：sim 引擎内部有画面状态机 `self._screen`（**12 处赋值点**：937 BRIEFING / 1047 PREP / 1403 `_present_modal` 动态 / 1423 `_dismiss_modal` 动态 / 1543 PLANE_TRANSITION / 1682 INVEST_STRATEGY / 1707 SUPPLY / 1713 ENCOUNTER / 1717 BOSS_BRIEFING / 1744 PREP / 1942 SETTLE / 1988 LOBBY；词表 = 实机建档名，`cw_sim_backend.py:189-211`），但从不写入 GameState 容器 → journal 无画面证据行。实测 sim journal（sim_match_20261016_082523，600 行）：`current_screen` 写入行 0 条；快照三形态 actor 无画面观察行（仅以回执/结算形态出现：CwScreenShop 13、CwScreenBattleWait 13，备战形态 0）；回执 `screen` 字段有值（按行到达口径备战 314/开商店 326）但实机数据实证其恒为底层画面值（源迭代 attack.md #2 结论：弹层动作也标底层画面），已裁定不参与切章。
  - **约定层（更深一层）**：sim 正本 `sim/sim-wiring.md:57` **已申报** prev_screen/current_screen「同实机」覆盖，其给的机制 `update_screen_after_operation`（operation.py:1488-1497）只写框架 screen_loader 路由簿记（sim 经 cw_sim_ports.py:243 在走），与容器 Field `gs.current_screen` 是两个东西——正本申报与实现不符。本迭代 = **兑现既有申报**，并修正该正本行（landing 正本更新清单）。
- 解决到哪：sim 引擎在画面流转点广播 `current_screen`/`prev_screen` 同形对进 journal；渲染器切章证据收窄（§2.2）+ 快照章注册表扩容（§2.2）。**明确不解决**：sim 的「真观察」面（无截图/OCR——广播是引擎声明不是读数，渠道如实性三级标记见 §2.1）；实机链路零改动。

## 2. 方案（单文档完整设计）

### 2.1 sim 广播（`sim/cw_sim_backend.py`）

1. **新私有 helper** `_announce_screen(value: str) -> None`：
   - **值级豁免**：`value ∈ {SCREEN_SETTLE, SCREEN_LOBBY}` → 直接 return（豁免按值不按赋值点——:1423 动态返回位可为结算屏，点位豁免会泄漏「货币战争-结算」未注册空壳章，探针实测形态）。豁免理由：结算事实已由战斗章「章内变化」承载（settlement 写入行兼开战斗章，journal-review-renderer details/pipeline.md §4「settlement 写入行 = 战斗章开章证据」）+ 局头终局行；大厅收口事实在局头。广播只会各造一个空壳章（terminal variant 探针实测每节点 2 个）。
   - 写 `prev_screen` = 上次广播值（初值 = 容器现值空串）→ 写 `current_screen` = value，两行一对；渠道 = `self.gs.observe(self.gs.current_screen, value, evidence=sim_evidence(f'screen:{value}'), sig=obs_sig(group_id='sim:screen'))`（同形先例 = 同文件 gold/streak 写入 `cw_sim_backend.py:1912-1921`）。
   - **渠道如实性三级标记**：①family='obs'（obs_sig 内建）；②**mode='synthesized'**（obs_sig 内建 `cw_sim_base.py:30-34`；journal.md §2 渠道封闭集明文含 sim 合成形态——渠道级主标记）；③evidence 前缀 `screen:`（辅助）。渲染器观察尾注跳过表已含双键（零噪声）。
   - 同值广播不抑制（kernel 写端天然落 `same_value=true` 行；渲染路由只认键在场且同值行续开 base 不重开章，零副作用）。
2. **广播点** = 12 处赋值点中除 :1942/:1988 外 **10 处**：直通点 937（BRIEFING）/1047（PREP）/1543（PLANE_TRANSITION）/1682（INVEST_STRATEGY）/1707（SUPPLY）/1713（ENCOUNTER）/1717（BOSS_BRIEFING）/1744（PREP）+ 动态点 1403/1423（`_present_modal`/`_dismiss_modal`，承载 SHOP/INVEST_ENV/BOX/EXPERT/MEGASTAR/PLANNER 六值与返回位）。值 = `SCREEN_*` 常量直通（词表 = 实机建档名，对照 `cw_game_state.py:289-307` `_PAYLOAD_DOMAINS` 属屏映射与 `cw_loop.py:560-565` 实机路由表，同源）；值级豁免见上。
3. `self._screen` 状态机本体不动（引擎内部消费面照旧），广播是附加写。
4. **不复用 kernel `observe_screen_context`（自称「观察汇聚唯一写点」）**：该口对 备战/开商店 值会触发顶栏观察/商店类型派生等实机分支（`cw_game_state.py:3290/:3298`），sim 常量值与其同值会误触实机逻辑——手搓两行对是刻意取舍，非漏接单一源（防后人按「唯一写点」纪律误裁）。

### 2.2 渲染器（`tools/cw/replay_to_md.py`）

1. **切章证据收窄（核心修订）**：`_locate_screen` 的 cs 分支判据从「行内快照含 `current_screen` 键」收窄为「**本行 `field=='current_screen'`**」（即漏斗/广播写入行本体）。**非广播行携带的 cs 一律只作归属（挂当前章），永不作为切章锚**。
   - 为什么：行内快照是累计子集，两次广播之间的行全带陈值 cs——只看键在场，结算段陈值 cs 会开幽灵备战章（探针局实证章数近倍膨胀）、overlay 广播会偷 base 致备战章碎片化。
   - 实机回归性：实机切章锚本来就是漏斗 `current_screen` 写入行，收窄不改变实机章结构（攻击者以补丁对 4 个实机档案实测 0 diff；机理 = 漏斗节拍下「陈值 cs==base 续章」与「挂 cur」等价）。
   - settlement 开章证据规则（源迭代 pipeline §4）保留——它是无 cs 写入形态（sim 旧数据/战斗段）的战斗章锚。
2. **SCREEN_REGISTRY 扩 11 键**（键 = sim 广播的 overlay 画面值，规格 = 各自 actor 孪生同款，render-spec §3 既有定义）：货币战争-简报/BOSS简报 → 画面-BOSS简报（非决策面）；货币战争-投资环境/投资策略/补给/遭遇节点 → 各自画面章（决策面）；货币战争-位面过渡 → 画面-位面转场（非决策面）；货币战争-备战-武装箱选择/备战-专家邀请函/盛会之星/银狼升星 → 画面-箱子/专家邀请/巨星/银狼策划（决策面）。
3. **相邻合并键 = title**：sim overlay 实际顺序 = cs 广播行先（report 前赋值）、actor 行后，两者 title 相同 → 相邻合并归一为单章；非相邻不合并（备战→商店→备战是独立访问）。**注册纪律（新增）：同 title 必须同规格（decision/键集）**——合并沿用先开章规格，同 title 异规格会静默错规格（render-spec §3 补纪律行；现注册表全量查重已满足）。
4. **_opening_note 补空值跳过**（prev_screen 首行空串不入账是当前采集时序的实测形态，但注记口防御性跳过，防将来时序变化出噪声行）。
5. 未注册 id 兜底（原样开章+缺口）保留——真未知画面仍响亮。

### 2.3 渲染行为预期（验收基准）

- sim 新跑报告：`(未观察)` 占位清零（备战/商店广播行开正式章；overlay 相 = 广播行 + actor 行合并单章）；**无幽灵章**（章序 = 引擎画面状态机直映，攻击者探针局已按修订后规则复验）。
- 实机报告回归：4 档案抽样零 diff（攻击者补丁实测）+ landing 3.1 的 live 存量重渲判据。
- 旧 sim 存量（无广播行）：渲染零 diff（无切章锚新增；快照 cs 键不再切章，但存量数据本就无 cs 键）。

## 3. 关键取舍

- **不广播 SETTLE/LOBBY（按值豁免）**：结算/大厅的复盘事实已有承载位，广播各造一个空壳章（探针实测形态）；若未来结算屏有独立判读面再扩。
- **不造「战斗等待」广播值**：sim 无该相位（常量注释 :202-207 明言战斗等待动画窗属实机时间维），造值 = 词表外发明；战斗章由 settlement 证据规则承载。
- **合并键用 title**：actor 章与广播章的 screen_id 不同源（actor 名 vs 画面名），title 是唯一共同语义面；配「同 title 必须同规格」注册纪律封住静默错规格风险。
- **广播渠道用 obs 族**：实机 current_screen 即 obs 族，渲染路径单一；引擎声明非真读数的事实由 mode='synthesized'（渠道级主标记）+ evidence 前缀（辅助）如实承载。
- **不复用 observe_screen_context**：见 §2.1.4。
