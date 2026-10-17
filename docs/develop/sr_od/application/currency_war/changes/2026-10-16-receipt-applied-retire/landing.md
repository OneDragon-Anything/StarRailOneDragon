# receipt-applied-retire 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 直接受影响测试全量一次通过（sim 子集 + operations 子集 + kernel 子集 + tools，`-m "not slow"`）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段名；提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 回执契约退役 + 调用点迁移 + 渲染器跟随

**范围**：①`kernel/cw_game_state.py::note_action_receipt` 删 applied（design §2.1，docstring 重写 + LogicOutcome 边界申报 + reason 码词表**暂住 docstring**——正本家 = fields.md 契约节随 3.2，action_ops.md 回执契约小节指针随 3.2）；②调用点迁移 4 处（design §2.2 表：prep 统一口回执保留 reason 码化（round_fail status 闭集映射 not_emitted:*/no_effect:*，invariant 保持）/open_shop 定位缺失回执保留 reason 码化 + round_fail 维持/close_shop 定位缺失回执保留 reason 码化 + round_success 维持/cw_screen_shop visit 环删 applied + 机械早退码化（落地门取码 = round result status 前缀闭集映射，design §2.1 供给申报））；③渲染器 `tools/cw/replay_to_md.py`（design §2.3：Action.applied 删、受阻样式挂 reason、重试链判据换锚、**extra 排除表保留 'applied' 键**）；④测试面（attack 核一发现 9 点名：`test_replay_render.py:64-67/:340-353` 回执 fixture 与链合并、`test_open_shop.py:126-171` 回执窗投影与 sim 恒 true、`test_shop_screen_op.py:195/:378` kernel 口签名桩、`test_sim_smoke_batch.py:209-212` 统计谓词**换锚** `not item.get('reason')`（新旧数据两洽，与渲染器受阻判据同款；原 applied 谓词退役）+ 新增受阻码 fixture（码集 = design §2.1 定稿词表））。豁免面申报：LogicOutcome 域断言（test_gain_chain/test_ore/test_supply/test_node_advance/test_sim_backend/test_world_decl 等）不在迁移面。边界：LogicOutcome.applied 契约不动、outcome 冒泡后续批。
**设计依据**：design.md §2.1-§2.4/§3。
**文件面**：`src/sr_od/application/currency_war/kernel/cw_game_state.py`；`src/sr_od/application/currency_war/prep_actions.py`；`src/sr_od/application/currency_war/operations/cw_op/cw_op_open_shop.py`；`src/sr_od/application/currency_war/operations/cw_op/cw_close_shop_action.py`；`src/sr_od/application/currency_war/operations/cw_screen/cw_screen_shop.py`；`tools/cw/replay_to_md.py`；测试仓四文件 + 新增 fixture。
**依赖**：无。
**优先级建议**：0
**完成判据**：
- sim 驱动整局收口（`terminal=death|p3_enter`，fail_streak<5）+ 渲染报告：全回执无 `applied` 字样、受阻回执显 reason 码；
- 旧 journal（sim_match_20261016_202444 等含 applied 键历史批）重渲染零异常且布尔字样零显影（排除表保留判据）；
- fixture 码齐全（design §2.1 定稿词表五族）：`定位缺失(按钮-商店)`（open_shop 实机）/`定位缺失(按钮-收起)`（close_shop）/`not_emitted:*`（prep 点击前失败）/`no_effect:*`（prep 点后未生效，StartBattle 例外类）/`slot_unresolved`|`slot_out_of_range`（visit 环机械早退）；
- 全仓（src+tools）回执域 `applied` grep 清零（豁免面逐命中归属：LogicOutcome 域 + **渲染器排除表保留的 'applied' 字面量**（:1009/:1531））；
- 完成前常规检查（本文首节）。
**验收凭据形式**：单测名清单 + 双局渲染对照 + grep 清零记录（含豁免面归属表）。

## 3.2 正本更新

**范围**：①`game_state/fields.md` 行为模型段**扩为回执契约单一节**（shape + reason 码词表（design §2.1 定稿词表，not_emitted:*/no_effect:* 子码枚举在此定稿）+ invariant——正本归位，治「契约散落四处无机器守护」根因，journal.md 无回执形态小节不硬造）；②`flow/action_ops.md` **新增「回执契约」小节**（现无此节；收 reason 码词表 + 引 fields.md 单一节）+ §4.1 CloseShop 行语义闭清（「miss = 店已关,幂等出口」语义保留，确认无 applied 词残留）+ §4.7 open_shop 行核对 + **§2.3:70「prep 域旁路字段 env.detail/env.emitted」句随 env.emitted 退役成死锚——入语义闭清清单**（grep 抓不到，须点名）；③`game_state/logic-updates/close-shop.md:16/:30` 回执两出口描述跟随（幂等已关出口回执 reason 码化,布尔退役）**+ 幂等已关语义与「定位缺失(按钮-收起)」码的对齐改写**（跨迭代张力申报：open-shop-action-spec 去业务推断裁定 vs 本正本「幂等已关」框架——零观察 op 辨不出已关/未开，码报机械事实，业务态语义归正本散文）；④`game_state/retirement.md` 11 号项**仅语义修正**（前置子句「零成败 receipts 落地前旧数据源不得抽空」的事实前提随本迭代成立，改写该子句；落地事实记进度账本不进本文——本文 as-built 无状态）+ §2 exec_events 行与 `telemetry/defects.py:325` 同款核对；⑤渲染器 ⚠/重试链判据规范的正本归宿申报（现住渲染迭代 changes/ details/，清理即死锚——归宿 = 渲染器模块 docstring 或 fields.md 契约节，随 3.1 定稿定点）；⑥README 进度收尾。闭合法 = 回执域 applied 正本树全域 grep 逐命中归属（LogicOutcome 域豁免面列出）+ **语义闭清**（不含 applied 字样的旧语义表述逐处核对：CloseShop「店已关(幂等出口)」、`screens/shop.md:48`「执行未落地＝applied=false 回执行」点名、action_ops.md §2.3:70 env.emitted 死锚）。
**设计依据**：design.md §0/§1/§2.1/§2.3；attack.md A8（排除表保留）/发现 9（prep invariant）/发现 10（retirement 措辞）/核二+三 S3（正本锚）/S6（闭合法）/S10（retirement 纪律）。
**文件面**：`docs/develop/sr_od/application/currency_war/game_state/fields.md`；`docs/develop/sr_od/application/currency_war/flow/action_ops.md`；`docs/develop/sr_od/application/currency_war/game_state/logic-updates/close-shop.md`；`docs/develop/sr_od/application/currency_war/game_state/retirement.md`；`telemetry/defects.py` 核对；本迭代 README。
**依赖**：3.1。
**优先级建议**：0
**完成判据**：回执域 applied 正本树 grep 逐命中归属清零（LogicOutcome 域豁免面列出）+ 语义闭清记录；fields.md 回执契约单一节与代码现状一致；README 终态。
**验收凭据形式**：grep 记录 + 文档对照 review。

## 正本更新清单

- `game_state/fields.md` 行为模型段扩为回执契约单一节 ← 3.2
- `flow/action_ops.md` 新增回执契约小节（reason 码词表）+ §4.1 语义闭清 ← 3.2
- `game_state/logic-updates/close-shop.md` 回执两出口描述 ← 3.2
- `game_state/retirement.md` 11 号项语义修正（+§2/defects.py 核对） ← 3.2
