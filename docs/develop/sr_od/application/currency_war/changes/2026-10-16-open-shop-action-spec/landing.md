# open-shop-action-spec 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 直接受影响测试全量一次通过（sim 子集 + operations 子集，`-m "not slow"`）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段名；提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 开店 op 规范重组 + 类壳解散 + CloseShop 对账

**范围**：①`operations/cw_op/cw_op_open_shop.py` 直调体按 design §2.1 重写（幂等观察/落地复查/retry 环删除；sim 保留点击、恒 applied=true；实机定位缺失唯一 false 出口）；②类壳 `CwOpOpenShop` + `CwOpOpenShopObs` 解散（design §2.2）；③CloseShop 对账（design §2.4：`cw_close_shop_action.py` reason 去业务推断改定位缺失语义，同批含 :93 round_success status 文案与 :77-78 docstring 的业务推断清理）；④decide 离屏症状消失验收（§2.5）。边界：不动策略决策面、不动 visit_open_shop、不动渲染器、PickPartner/_overlay_confirm/StartBattle 在册待修不混本批。
**设计依据**：design.md §2.1-§2.5。
**文件面**：`src/sr_od/application/currency_war/operations/cw_op/cw_op_open_shop.py`；`src/sr_od/application/currency_war/kernel/cw_screen_report/open_shop.py`（随类壳退役）；`src/sr_od/application/currency_war/operations/cw_op/cw_action_registry.py`（终端行复核）；`src/sr_od/application/currency_war/operations/cw_op/cw_op_settle_confirm.py`（docstring 引语）；`src/sr_od/application/currency_war/operations/cw_op/cw_close_shop_action.py`（reason 对账，含 :93 status 文案与 :77-78 docstring）；M1③ 会话局部标识符顺手清四路径（仅注释零行为）：`operations/prep_actions.py:414`、`kernel/cw_game_state.py:1332`、`operations/cw_screen/cw_screen_shop.py:260`、`operations/cw_screen/_overlay_confirm.py:11`；`sr-od-test/test/sr_od/application/currency_war/sim/test_sim_smoke_batch.py:131`（注释悬空引用随类壳解散清理）；测试迁改（`test_screen_report_ports.py:58+71` 两张名单）+ 新增 fixture 测试。
**依赖**：无。
**优先级建议**：0
**完成判据**：
- sim 全局：驱动整局收口（`terminal=death|p3_enter`，fail_streak<5）+ 报告开店回执 `applied=是`（⚠ 消失）+ `decide_shop_action 离屏` 零抛；
- 实机形态 fixture：定位缺失 → applied=false「定位缺失(按钮-商店)」（唯一 false 出口）；sim fixture：恒 true；
- 类壳解散后全仓 `CwOpOpenShop` 类引用零残留（渲染器词表字符串与 docstring 引语除外，均已在文件面申报）；
- `test_screen_report_ports.py` 两张名单迁改后全量过；
- 完成前常规检查（本文首节）。
**验收凭据形式**：单测名清单 + 驱动整局日志行 + 报告开店节引用 + 谜团消失对照。

## 3.2 正本更新

**范围**：①`flow/action_ops.md`：开店条目 as-built（规范形态单节点、applied 恒 True、sim 点击源语义）+ §3 偏离清单核查面扩展至 §4.7 组合壳/直调体（本迭代流程教训）+ :40 悬空指针另修（cw_screen_op_base.py 已不存在，裁定原文现住 op-layer.md §1.2:49）；②`screens/op-layer.md`：:85 惯例句、:96（§3 标题）与 :98（计数）与 :112（合计式）35→34 联动、:107 分型总表**行内移除 CwOpOpenShop**（该行仍承载 CwOpSettleConfirm，非整行删）+ §1.1 例外③宿主清单改写（「判断动作是否已做过」用途随幂等出清消亡）；③`game_state/logic-updates/open-shop.md` §3.1（「幂等,已开不点」随幂等删除失真）；④`sim-design.md:88-90` 开店点击源语义随 §2.1 改形联动；⑤`screens/shop.md` 核对；⑥M1③ 会话局部标识符顺手清（3.1 文件面四路径 + note_action_receipt docstring）；⑦README 进度收尾。闭合法 = 09-22 screen-review 的「退役符号正本树全域 grep 逐命中归属」。
**设计依据**：design.md §2.1/§2.3/§2.5；attack.md S3/S4/S7/Q1/E。
**文件面**：`docs/develop/sr_od/application/currency_war/flow/action_ops.md`；`docs/develop/sr_od/application/currency_war/screens/op-layer.md`；`docs/develop/sr_od/application/currency_war/game_state/logic-updates/open-shop.md`；`docs/develop/sr_od/application/currency_war/sim/sim-design.md`；`docs/develop/sr_od/application/currency_war/screens/shop.md`；本迭代 README。
**依赖**：3.1。
**优先级建议**：0
**完成判据**：退役符号（CwOpOpenShop 类/CwOpOpenShopObs/幂等出口语义）正本树全域 grep 逐命中归属清零；文档与代码现状一致；README 终态。
**验收凭据形式**：grep 记录 + 文档对照 review。

## 正本更新清单

- `flow/action_ops.md`：开店条目 as-built + §3 核查面扩展 + :40 指针 ← 3.2
- `screens/op-layer.md`：:85/:98/:107 三处 + §1.1 例外③改写 ← 3.2
- `game_state/logic-updates/open-shop.md` §3.1 ← 3.2
- `sim-design.md:88-90` 开店点击源语义 ← 3.2
- `screens/shop.md` 核对 ← 3.2
