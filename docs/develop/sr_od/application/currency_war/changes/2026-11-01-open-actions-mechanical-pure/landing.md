# 开件动作去识别化 落地

## 完成前常规检查(各阶段完成判据引用本节,不复述)

- `uv run ruff check` 对本阶段改动文件全部通过;
- 本阶段直接受影响测试全量一次通过;
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交;
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号;提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 建档:武装箱开启位 per-slot area

**范围**:经 MCP `upsert_screen_area` 新建 `武装箱开启位-1..9` 九个纯 rect area(画面 = 货币战争-备战;rect 初值 = 现档 `备战栏-{N}` rect 整体垂直平移 +41px〔尺寸与备战栏-N 同、中心即槽中心+41,与现码校准基准同源〕,实机校准回补归 3.3;同步合并缓存)。
**边界**:只加不改既有 area;无模板(直点形态,design §2.3)。
**设计依据**:design.md §2.3。
**文件面**:`assets/game_data/screen_info/` 分 yml(经 MCP 写)+ 合并缓存(MCP 自动)。
**依赖**:无。
**优先级建议**:0
**完成判据**:
- 九 area 在档且 `get_screen_detail` 可读;rect 与推导式一致(抽查三槽);
- 完成前常规检查(本文首节;yml 变更随 commit)。
**验收凭据形式**:get_screen_detail 输出。

## 3.2 三 op 直点形态重写 + 测试

**范围**:design §2.1 逐 op 重写(读门删除/槽号解析含 None 现算〔resolved slot 重建 param〕/建档坐标直查/mouse_move+click/自上报/`BOX_OPEN_DY` 删除/`mechanical_io_allowed` 分支保留);`read_tomes` 符号删除(design §2.4-3);`prep_actions.py` 回执映射表三行退役(design §2.4-6);`cw_vocab.py` slot 注释同步(design §2.4-5)含 :470 陈旧 as-built 顺改(「点槽两次」→ 单击,2026-09-25 用户确认口径);三 op 单帧测试重写 + 新增(design §2.5 测试条)。
**边界**:不碰观察层(`read_armory_boxes`/`find_bookcards` 保留);不碰外循环连败网;不含文档(3.3)。
**设计依据**:design.md §2.1/§2.2/§2.4/§2.5。
**文件面**:`src/sr_od/application/currency_war/operations/cw_op/cw_open_box_action.py`;`cw_open_tome_action.py`;`cw_open_bookcard_action.py`;`src/sr_od/application/currency_war/obs/cw_identity_obs.py`(仅 read_tomes 符号删除);`src/sr_od/application/currency_war/prep_actions.py`(回执映射行);`src/sr_od/application/currency_war/kernel/cw_vocab.py`(slot 注释);`sr-od-test/test/sr_od/application/currency_war/` 下三 op 对应测试文件(grep 定位)。
**依赖**:3.1。
**优先级建议**:0
**完成判据**:
- 单帧测试全绿:slot 显式/None 现算 → 建档坐标点击 + 自上报 + success;slot 越界 AssertionError;**None 现算双出口(gs 为 None / 容器无该 kind 首槽)各一条 AssertionError 断言**;sim 形态(旁路静默成功 + 后端世界推进);
- grep 验证:三 op 文件 `read_armory_boxes`/`read_tomes`/`find_bookcards`/`BOX_OPEN_DY`/`screenshot` 零残留;**`read_tomes` 在 src/ 与 sr-od-test/ 零引用**(文档面引用归 3.3 正本更新,不在本判据域);
- design §2.4 行为变化逐条自检;
- 完成前常规检查(本文首节;ruff + 受影响测试;L1 红集须与本批清单吻合,清单外变红 = 停手)。
**验收凭据形式**:测试名 + grep 清零记录 + ruff。

## 3.3 文档同步与实机实测

**范围**:`flow/action_ops.md` `:110-112` 动作表 as-built 更新(直点形态)、`:18` 出战挂账行补同类关系声明;实机 `run_operation` 三 op 单跑(`武装箱开启位-N` 坐标实测校准,偏差回补 3.1 建档)。
**边界**:不动其他正本篇;实机坐标偏差 = 回补建档(3.1 面)而非改代码。
**设计依据**:design.md §2.5 正本文档行/§2.6-3。
**文件面**:`docs/develop/sr_od/application/currency_war/flow/action_ops.md`;实机校验回补(3.1 面 yml)。
**依赖**:3.2。
**优先级建议**:1
**完成判据**:
- action_ops.md 与实现一致(grep 旧读门表述清零);
- 实机三 op 单跑记录(成功/失败与坐标校准结论);
- 完成前常规检查(本文首节)。
**验收凭据形式**:文档对照 + 实机 run 记录。

## 3.4 同 seed 端到端验收

**范围**:`cw_sim_match_drive.py --seed 20261101` 整局复跑,断言 P1-R8 判废链消灭(武装箱开箱走通,局正常收口或推进到 R8 之后)。
**边界**:只跑局与判读,不因本批外因素修代码(复跑暴露其他问题另行登记)。
**设计依据**:design.md §2.6-2。
**文件面**:无(验证动作;产物 = 新 sim 批目录)。
**依赖**:3.1-3.3。
**优先级建议**:1
**完成判据**:g_20261101 同 seed 局不再复现「无简易武装箱」fail_streak 判废;结果与 3.2 交付一致。
**验收凭据形式**:复跑 stdout + journal 终态行。

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新。
**设计依据**:本文件「正本更新清单」节。
**文件面**:清单所列文档。
**依赖**:3.1-3.4 全部。
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致。
**验收凭据形式**:文档对照 review。

## 正本更新清单

- `flow/action_ops.md`::110-112 动作表 as-built(直点形态)、:18 同类挂账声明、:225 回执词表三码退役(供给零)← 3.3
- `flow/projection_contract.md`::139 G5 行(read_tomes 除名;消费方理由改观察域)← 3.3
- `docs/develop/sr_od/application/currency_war/game_state/fields.md`::2763 回执词表正本家同步收缩 ← 3.3
- `docs/develop/sr_od/application/currency_war/game_state/logic-updates/open-box.md`::17-18(read_armory_boxes 识别序 + BOX_OPEN_DY 执行序)改直点形态 ← 3.3
- `docs/develop/sr_od/application/currency_war/game_state/logic-updates/open-tome.md`::15/:19(read_tomes 执行序)改直点形态 ← 3.3
- `docs/develop/sr_od/application/currency_war/game_state/logic-updates/open-bookcard.md`::11/:28(find_bookcards 识别 + 失败语义)改直点形态 ← 3.3
