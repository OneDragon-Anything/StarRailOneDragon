# op 拆解总表:每月合成

## op 索引表

| 标识符 | 职责 | 状态 | 设计书 |
|---|---|---|---|
| `Synthesize`(扩展) | 合成指定物品:导航+选分类+选物品+数量+确认;新增 `plus_monthly` 数量策略(+逐次点满/置灰判顶/额度0跳过)与 `quantity_mode` 分流 | 复用但需修(大半覆盖 → 扩展) | operation-flow-1.md |
| `BackToNormalWorldPlus` | 回大世界(app 导航段入口与返回段收尾) | 复用(零改动) | — |
| `OpenPhoneMenu` / `ClickPhoneMenuItem` | 手机菜单导航到合成 | 复用(Synthesize op 内部,零改动) | — |
| `MonthlySynthesizeApp`(新) | 月周期编排:开关分流→合成→回大世界/失败收尾 | 新写 | application-flow.md |
| 样板:`MonthlyEmbersExchangeApp` | 月周期 app 结构(MONTHLY run_record / factory 注入 / 失败收尾节点) | 样板(结构同型参照) | — |
| 样板:`TrickSnackApp` | 合成开关分流(开关关→round_success 跳过) | 样板 | — |

## 读数类需求去向

| 读数 | 去向 |
|---|---|
| 当前分类名 | `合成/标题-合成分类` OCR(choose_category 既有判定,不造读数 op) |
| 本月还可合成 N | `合成/读区-本月还可合成` OCR + `str_utils.get_positive_digits` 解析(数量节点内联读取,单个读数不值得造识别器) |
| + 按钮亮/灰态 | `合成/按钮-数量增加`(亮)/`按钮-数量增加-置灰`(灰)模板匹配 |

## 开放点清单

| 问题 | 倾向方案 | 裁定状态 |
|---|---|---|
| 月额度用完的画面形态 | + 置灰 + 额度 0;额度读不出 → 判失败不冒险 | 待实机核对(flow.md §4) |
| 入口即 + 置灰且额度 ≥1 | 视为「已被材料约束到顶」→ 直接合成当前数量 | 按拉满语义自洽,实机复核 |
| app_id 命名 | `monthly_synthesize`(与 monthly_embers_exchange 同族命名) | 已定 |
