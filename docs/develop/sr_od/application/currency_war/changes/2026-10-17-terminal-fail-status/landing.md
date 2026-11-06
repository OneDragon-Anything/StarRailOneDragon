# terminal-fail-status 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 直接受影响测试全量一次通过（sim 子集 + operations 子集 + tools，`-m "not slow"`）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段名；提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 六口删检查（七段）+ 词表缩减 + 终结口透传 + 规范文本更新

**范围**：①六出口改造（design §2.1 表）：**参数违法类三口改 op 内守卫断言**（BuyCard 槽解析/槽号越界、DeployMove 落位越界+补 to_slot≥1 下界——raise AssertionError 消息原文保留，:21 坐标裁定域）；**area 缺失类四口删检查直接使用**（PickEncounter/PrepLevelUp/StartBattle :121-126+弹窗 :135-137（QA）/WearEquip 坐标缺失——自然异常即报错）；保留面 = BuyCard 槽匹配循环/StartBattle 两屏查+:119/LevelUp :89-98 自读回落；②`prep_actions.py` `_PREP_RECEIPT_BLOCK_CODES` 删 8 行（design §2.2 清单）+ docstring 同步；③`cw_screen_shop.py:309-310` `_SHOP_VISIT_BLOCK_CODES` 整表退役 + `_visit_block_code` 死代码删除；④**终结出口失败透传**（QC (b)：`cw_screen_prep.py` `_terminal_exit` 增 op round 结果入参，失败返回 round_fail——外环防线可数）；⑤**动作 op 规范文本更新**（`action_ops.md`，一等交付）：§5 词表缩减（与 fields.md 同批落）+ **§2.3 返回值已登记例外句跟随**（:71 BuyCard 两口/StartBattle area 缺失表述随批陈旧）+ **emitted=False 残留清理两处**（:99 WearEquip 行/:60 §2.1 句——env.emitted 已随 receipt-applied-retire 退役）+ **零防御纪律句成文**（:11 裁定应用条款：「显式报错修根因」现役形态 = 取值直接使用自然异常，不为建档缺失/参数违法设检查出口——限定域申报见 design §2.1.1）+ **参数现算契约 + 校验落点契约成文**（§1 末尾「决策侧参数现算契约」段：同帧性限定单动作决策环/战斗链边界载体登记/违纪承接双层/负值形态对账链承接 + **校验落点契约**（参数校验唯一落点 = op 内守卫断言，执行器集中校验退役）——design §2.1.1）+ DeployMove 行「陈旧载荷」语义改写 + §4.1/§4.2 出口语义跟随；⑥`fields.md` 回执契约节 invariant 改写（design §2.2 句式 + QA 例外从句）；⑦传播路径验证（design §2.3：全链 except 扫描，口径 = 无未申报吞点——:817 与框架层维持现状即申报项）；⑧测试面 **6 文件点名**（design §4：test_prep_action_ops/test_action_report/test_shop_screen_op〔:285-297 映射单测删除〕/test_overlay_ops/test_prep_actions〔两回执行测试删除，:100-119 保留〕/test_deploy）+ 终结出口透传断言新增 + 现读落空族回归。边界：LogicOutcome 契约不动、现读落空族非成员口不动、:817 与框架层维持现状（QB (a)）、T-4 保留不撤（§3.2 注记改写）。
**设计依据**：design.md §2.1-§2.5（裁定终值表 §3）。
**文件面**：`src/sr_od/application/currency_war/operations/cw_op/{cw_pick_encounter_action,cw_prep_level_up_action,cw_start_battle_action,cw_wear_equip_action,cw_buy_card_action,cw_deploy_move_action}.py`；`src/sr_od/application/currency_war/prep_actions.py`（映射表删行）；`src/sr_od/application/currency_war/operations/cw_screen/cw_screen_shop.py`（词表退役）；`src/sr_od/application/currency_war/operations/cw_screen/cw_screen_prep.py`（QC 落码）；`docs/develop/sr_od/application/currency_war/flow/action_ops.md`；`docs/develop/sr_od/application/currency_war/game_state/fields.md`；测试仓 6 文件。
**依赖**：无（四裁定已终值）。
**优先级建议**：0
**完成判据**：
- sim 驱动整局收口（`terminal=death|p3_enter`，fail_streak<5）；
- 自然失败可达：fixture **直驱层**构造五口条件（DeployMove 仅正越界，负值勿构造——QD(d)）→ TypeError/IndexError 上抛；
- 终结出口透传可达：fixture 构造终结口 round_fail → visit 返回 round_fail；
- 传播路径验证记录（全链 except 扫描，无未申报吞点）；
- 非成员回归：StartBattle :119 受阻码链 + 现读落空族行为不变；
- grep 清零（白名单口径）：六 op 文件 `round_fail` 仅剩 StartBattle :119 + WearEquip :74-76；「陈旧载荷,观察重派」「禁兜底坐标交回重读」注释清除；映射表删行逐行核；
- 全量测试过 + §3 偏离清单复核随批重跑；
- 完成前常规检查（本文首节）。
**验收凭据形式**：自然异常 fixture 记录 + 终结口透传断言记录 + 全链 except 扫描报告 + grep 白名单清零记录 + 测试名清单。

## 3.2 正本更新 + T-4 注记改写

**范围**：①`flow/action_ops.md` 各动作行语义跟随（六出口直接使用语义 + §2.3 例外句已于 3.1）；②`screens/*.md`/`game_state/logic-updates/*.md` 正本核对（grep 定面：禁兜底坐标纪律句保留、出口行为描述跟随）；③`game_state/retirement.md` 登记「观察重派」旧语义退役；④receipt-applied-retire 迭代 T-4 分账**保留不撤**，注记按 design §2.5 改写（用户裁定不做防御性编程+五口删检查自然异常；残余未落地循环由失配告警停局+NODE-DWELL 900s 哨兵承接）；⑤README 进度收尾。闭合法 = 删除段特征串正本树 grep 清零 + 终态 status 串逐命中归属。
**设计依据**：design.md §2.1/§2.2/§2.5。
**文件面**：`docs/develop/sr_od/application/currency_war/flow/action_ops.md`；`docs/develop/sr_od/application/currency_war/screens/`（grep 定面）；`docs/develop/sr_od/application/currency_war/game_state/logic-updates/`（grep 定面）；`docs/develop/sr_od/application/currency_war/game_state/retirement.md`；`.debug/progress/2026-10-16-receipt-applied-retire/dag.jsonl`；本迭代 README。
**依赖**：3.1。
**优先级建议**：0
**完成判据**：删除段特征串正本树 grep 清零；T-4 注记改写完成；README 终态。
**验收凭据形式**：grep 记录 + 文档对照 review。

## 正本更新清单

- `flow/action_ops.md` 六出口直接使用语义跟随 ← 3.2
- `screens/` + `game_state/logic-updates/` grep 定面清退 ← 3.2
- `game_state/retirement.md` 「观察重派」旧语义退役登记 ← 3.2
- receipt-applied-retire T-4 注记改写（保留不撤） ← 3.2
