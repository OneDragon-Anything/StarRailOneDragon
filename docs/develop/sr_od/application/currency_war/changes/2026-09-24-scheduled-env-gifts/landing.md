# 环境定时道具发放与特权武装箱开箱 落地

> 阶段小节 = 账本唯一源;立任务照各节 `dag.py add`,criteria 指向本文件对应节。
> §12 通用工程门 = sr-od-test/README.md「提交」节 + 项目 AGENTS.md §7/§10
> (类型注解/ruff/受影响测试全绿/逐文件 add)。

## 3.1 kernel:定时登记通道 + 队列 + 到点发放原语

**范围**:`GiftGrant.items_scheduled` 字段;`ENV_GIFTS['特权阶级']` 登记;
`_validate_env_gifts` 三校验扩展(节点键格式/道具名禁 ∈ CHARACTER_ROSTER/
空发放集并入);`BENCH_ITEM_NAMES` 派生面并入 scheduled 道具;容器新字段
`pending_item_grants`(Field[list[dict]],开局种子 [],`DEFAULT_GS_SCHEMA
['match_facts']` 5→6 带注记,`seed_opening_state` 同步);`on_env_gained`
scheduled 入队支 + 效果串 `item_scheduled:<名>@<节点键>`;新原语
`discharge_due_item_grants`(design.md §2.3 契约逐条);cw_projection_audit
`pending_item_grants` 行(PROJECTION_AUDIT 登记,design.md §2.2 对账申报)+
人读镜像同步
`.debug/progress/2026-09-16-strategy-terminal-contract/projection-audit.md`。
**不含**:sim 挂点(3.2)、画面/overlay(3.3)、正本文档(末阶段)。
**设计依据**:design.md §2.1/§2.2/§2.3
**文件面**:src/sr_od/application/currency_war/kernel/cw_investments.py、
kernel/cw_gain_chain.py、kernel/cw_game_state.py、kernel/cw_projection_audit.py;
sr-od-test/test/sr_od/application/currency_war/test_cw_gain_chain.py、
test_cw_game_state_opening_seed.py;
.debug/progress/2026-09-16-strategy-terminal-contract/projection-audit.md
**依赖**:无
**优先级建议**:5
**完成判据**:
- 登记:gain_invest_env('特权阶级') → pending_item_grants =
  [{'env':'特权阶级','plane':2,'round_num':1,'item':'特权武装箱'}],
  效果串含 'item_scheduled:特权武装箱@2-1',active_env 正常写,零落席
  (对照 design.md §2.3)
- 发放:discharge_due_item_grants(2,1) → bench supply_box×1 + 队列回写 []
  + 效果串 'item_gift:特权武装箱';非到点 (1,1) → 零写零效果、队列原样
- 落位语义复用:discharge 席满 → 溢出落位两字段;溢出位被占 → 零写留证
  (DEFECT_OVERFLOW_TAKEN)
- 词表:'特权武装箱' ∈ BENCH_ITEM_NAMES(scheduled 派生)
- 校验:坏节点键 / 道具名 ∈ CHARACTER_ROSTER / 四通道全空 → ValueError
  (注入 + 直调 _validate_env_gifts,沿孤儿键测试惯用法)
- 种子:opening-seed 测试 _A_SEEDED 含 pending_item_grants 且冷建值 []
- 对账:PROJECTION_AUDIT 含 pending_item_grants 行(process_only)且人读镜像
  同步(行集与代码表一致)
- §12 通用工程门
**验收凭据形式**:test_cw_gain_chain.py 新用例组 + test_cw_game_state_opening_seed.py
全绿;ruff 干净

## 3.2 sim:进节点收口 discharge

**范围**:`SimBackend._begin_node_window` 在 `_apply_env_plane_gold` 之后调
`discharge_due_item_grants(rand=False, sig=logic_sig('sim:env'))`。**不含**:
实机侧接线(design.md §2.5 明确不解决)。
**设计依据**:design.md §2.4
**文件面**:src/sr_od/application/currency_war/sim/cw_sim_backend.py;
sr-od-test/test/sr_od/application/currency_war/test_cw_sim_backend.py
**依赖**:3.1
**优先级建议**:5
**完成判据**:
- sim 用例:选 特权阶级(invest_env_opts 注入,沿
  test_contract_env_pick_sends_cards_to_bench 惯用法)→ `_drive_step` 推进
  (沿 test_boss_briefing_click_resolves_battle 的 seed 61 通道)→ 位面过渡屏
  呈现时队列未消费 → 点空白收口后 PREP 帧:bench 含 supply_box×1、
  pending_item_grants == []、非到点节点(1-x 各轮)队列不消费
- 回归:test_cw_sim_backend.py 既有用例全绿
- §12 通用工程门
**验收凭据形式**:新 sim 用例 + 既有 sim 用例全绿

## 3.3 武装箱开箱链路泛化(弹窗锚泛化 + 选卡读数闸放宽)

**范围**:①design.md §2.6 四处同锚改动:画面档 area 改名/改 text(经 MCP
`upsert_screen_area` 新建 `标识-武装箱`(rect [830,150,1000,200],text 武装箱,
id_mark)+ `delete_screen_area` 删旧,**禁手编 yml**);overlay 注册表
anchor_area;CwScreenArmoryBox 两处锚引用与 docstring;
_IN_MATCH_KEYWORDS 关键词。②design.md §2.7 读数闸放宽:
cw_screen_box_pick.py `_read_card_names` 上限改注册表最长名长度派生
(`_CARD_NAME_LEN_MAX`),9 字特权名经闸存活;归一化两段与决策面不动。
**不含**:特权/进阶箱备战槽模板(T-421 待实机)。
**设计依据**:design.md §2.6/§2.7
**文件面**:assets/game_data/screen_info/currency_war_armory_box_dialog.yml
(MCP 写);src/sr_od/application/currency_war/kernel/cw_overlay_registry.py、
operations/cw_screen/cw_screen_armory_box.py、
operations/cw_screen/cw_screen_box_pick.py、currency_war_app.py;
sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_closing_screens.py、
test_cw_screen_progression_inline.py
**依赖**:无(与 3.1/3.2 并行可)
**优先级建议**:5
**完成判据**:
- 既有弹窗 op 用例全绿(锚名同步后的用例面)
- 新用例:9 字名(如「战场进化手册·特权」)经读数闸存活且归一精确命中;
  `_CARD_NAME_LEN_MAX` 与注册表最长名一致(防手抄常数)
- 全仓 grep `标识-简易武装箱` 零残留(src + assets);
  `_IN_MATCH_KEYWORDS` 无 `简易武装箱`
- 合并缓存生效:upsert/delete 后 analyze_screen 或加载路径无旧 area 引用报错
- §12 通用工程门
**验收凭据形式**:test_cw_obs_arch_closing_screens.py +
test_cw_screen_progression_inline.py 全绿 + grep 清零凭据;
特权标题/9 字名实机对照 = 首遇项,不入判据

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本 + invest-effects-calc 进度树收口
(checklist T-3 行终态凭据;T-421 为 dag 账本任务(wait,非 checklist 行),
其范围收窄经该任务后续流转 why 携带,账本不新增行;迭代 README 进度)。
**设计依据**:本文件「正本更新清单」节
**文件面**:清单所列正本文档;.debug/progress/2026-09-23-invest-effects-calc/
**依赖**:3.1、3.2、3.3
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致
**验收凭据形式**:文档对照 review

## 正本更新清单

- docs/develop/sr_od/application/currency_war/game_state/fields.md:
  §3.2 新增 pending_item_grants 节(语义/写端声明/entry 形;取舍 1 进动机段)
  ← 阶段 3.1
- docs/develop/sr_od/application/currency_war/game_state/gain-chain.md:
  §3 道具通道补 scheduled 支与效果串;新增 discharge 原语小节(挂点/幂等边界);
  §4 身份两分 bullet 的词表来源句改「items_immediate ∪ items_scheduled」
  ← 阶段 3.1/3.2
- src/sr_od/application/currency_war/kernel/cw_investments.py:
  ENV_GIFTS scheduled 首条注释与 BENCH_ITEM_NAMES 词表注释核对
  (注释随代码批已写,本阶段只核对不重写)← 阶段 3.1
- docs/game/currency_war/research/invest_effects.md:通道计数/形态描述受影响处
  ← 阶段 3.1
- docs/develop/sr_od/application/currency_war/screens/armory_box.md:
  弹窗识别锚名引用同步(旧锚 `标识-简易武装箱` 2 处,T-3 交付时发现)
  ← 阶段 3.3
- .debug/progress/2026-09-23-invest-effects-calc/checklist.md:
  T-3 行收口(终态凭据 + commit 指针)← 末阶段
  (T-421 = dag.jsonl 账本任务,checklist 无该行;其范围收窄——特权弹窗部分
  由本迭代消化、余备战槽模板待实机——经该任务后续流转 why 携带)
- .debug/progress/2026-09-23-invest-effects-calc/README.md:依赖/关联迭代注记
  ← 末阶段
