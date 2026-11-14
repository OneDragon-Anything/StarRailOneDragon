# v1-initial 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过（不对整个 src/ 跑）；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/ -m "not slow"` 相关子集；改公共包时含其测试）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），提交后 `git show --stat` 复核入库面 = 申报面；在飞并行批文件（game-coach 重组、dungeon-data-entry、mcp-runnable.md、writing-agent-instructions 等）一律不卷入；
- 改了任何 Python 代码后，实机验证前必须重启 MCP server（框架缓存已加载模块）；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」、MCP 节。

## 3.1 框架月度周期件

**范围**：`AppRunRecordPeriod` 加 MONTHLY + 重置判据年月段比较 + 单测；写 SR→ZZZ 同步件。不含任何 app 侧改动。
**设计依据**：details/framework-monthly-period.md 全文
**文件面**：`src/one_dragon/base/operation/application_run_record.py`；`sr-od-test/`（run record 镜像测试）；`.debug/temp/zzz/<日期>-monthly-run-record-period.md`
**依赖**：无
**优先级建议**：9
**完成判据**：
- 枚举含 MONTHLY=3；MONTHLY 分支月内不重置、跨月重置、刷新偏移跨月场景正确（对照详设 §2.2 三条）
- 完成前常规检查（本节首）
**验收凭据形式**：新增/扩展测试名 + 通过输出

## 3.2 tab 选中态模板重裁（实现前置阻断项）

**范围**：重裁 `tab-星芒兑换-选中` / `tab-余烬兑换-选中` 两模板为含高亮下划线区域（裁源=flow.md §4.1-1 两张实拍图）；离线验证两图互不命中；实机验证 `ShopSwitchTabOp` 切换验证真生效。不含其他 store 建档改动。
**设计依据**：flow.md §4.1-1（缺陷与裁源、阈值 0.7）
**文件面**：`assets/template/store/store_tab_embers_active/`、`assets/template/store/store_tab_starlight_active/`、必要时 `assets/game_data/screen_info/store.yml`（经 MCP upsert_screen_area 改，禁手改 yml）
**依赖**：无（3.5 实机串联依赖本阶段）
**优先级建议**：9
**完成判据**：
- 离线：analyze_screen(screenshot=星芒选中实拍) 只有星芒选中区命中、余烬选中区不命中；余烬选中实拍反之（对照 flow.md §4.1-1 修法）
- 实机：商店页跑 `ShopSwitchTabOp(embers)` 成功后 active 判定与真实选中一致；切回星芒同理
- 完成前常规检查（本节首）
**验收凭据形式**：两次 analyze_screen 输出对照 + run_operation 输出

## 3.3 OpenExchangeShop op

**范围**：按设计书实现无参导航 op；run_operation 实机验证（起点=大世界、起点=商店页幂等、起点=其他画面三条路径至少各验一遍关键路径）。
**设计依据**：operation-flow-1.md 全文
**文件面**：`src/sr_od/operations/shop/`（新建子包）；`sr-od-test/`（op 流程测试，如样板适用）
**依赖**：无（实机验证建议在 3.2 后跑，锚更可信；不阻塞开发）
**优先级建议**：8
**完成判据**：
- 三条起点路径走通且终点=商店兑换列表页（对照设计书 §3 流转，全部点击带 until）
- 完成前常规检查（本节首）
**验收凭据形式**：run_operation 输出（结果状态/耗时）+ 流程测试（如适用）

## 3.4 ExchangeShopBuyGoods 语义状态扩展

**范围**：失败出口补语义化状态 SOLD_OUT / CARD_UNAVAILABLE / NOT_FOUND / INSUFFICIENT_MATERIALS（对照 application-flow.md §3.1 表逐出口落位）；不改流程行为与消息文本；既有测试同步。
**设计依据**：application-flow.md §3.1（契约 C2）；shop_buy_goods.py 现有失败出口清单（代码内）
**文件面**：`src/sr_od/application/cultivation/account/operations/shop_buy_goods.py`；`sr-od-test/test/.../test_shop_buy_goods*`
**依赖**：无
**优先级建议**：8
**完成判据**：
- 四个语义状态各有出口落位且只加 status 不改行为；直接受影响流程测试一次通过
- 完成前常规检查（本节首）
**验收凭据形式**：测试名 + 通过输出

## 3.5 app 五件套与串联验证（真实兑换用例）

**范围**：const / config（ApplicationConfig 子类）/ run_record（MONTHLY + 业务字段）/ factory（create_application + create_config + create_run_record）/ app 类 + SrContext 接线；注册确认；`run_standalone_app` 实机串联第一跑——**含通票 2 张真实兑换（用户裁定 7 授权，唯一一次授权的真实消耗）**，验证成功兑换路径全链。
**设计依据**：application-flow.md 全文；requirement.md §3；样板 = trick_snack / relic_salvage 两 factory
**文件面**：`src/sr_od/application/monthly_embers_exchange/`（新建包）；`src/sr_od/context/sr_context.py`（config+run_record 接线两处）；`sr-od-test/`（app 侧可测逻辑如排序/分支纯函数）
**依赖**：3.1、3.2、3.3、3.4
**优先级建议**：10
**完成判据**：
- `list_applications` 可见 monthly_embers_exchange 且 DEFAULT_GROUP=True（对照 application-flow §1/§4 注册件）
- 串联第一跑：导航→专票(售罄跳过)→通票(真实购买 2 张, PURCHASED)→足迹(售罄跳过)→返回大世界；运行记录 bought_pass=2、skip_note 含两项、状态成功标完成
- 全程点击带 until、失败语义按 §3 分支实现（代码对照 §3.1 表逐行核）
- 完成前常规检查（本节首）
**验收凭据形式**：run_standalone_app 输出 + 运行记录 yml 内容 + 游戏内通票数量前后对照

## 3.6 端到端验收

**范围**：`run_standalone_app` 第二跑（三件套全售罄形态）验证「预期内无事可做→标完成」路径；MCP 配置工具验收（describe_config 结构清晰 / get→set→get 实测 / 运行态字段不给写口）；结束通知按 NEED_NOTIFY 发出核验。
**设计依据**：application-flow.md §3.2 终态表、§4 config 表；skill od-dev-write-application §7/§9
**文件面**：无代码改动（发现问题走 3.5 返工）；配置改动经 MCP 工具
**依赖**：3.5
**优先级建议**：10
**完成判据**：
- 第二跑零购买、skip_note 三项、状态成功标完成（对照 §3.2 表行 1）
- describe_config 对 6 个配置字段语义清晰；get/set 读回一致；改动下一次运行即时生效
- 通知发出（或 NEED_NOTIFY=False 时的口径核对）
- 完成前常规检查（本节首；无代码改动则仅核提交面为空）
**验收凭据形式**：run_standalone_app 输出 + describe/get/set 回显 + 通知记录

## 3.7 画面识别器与扫描单一源抽取（可裁项）

**范围**：抽 `shop_goods_scan.py`（网格几何/定位/角标解析纯函数平移）+ `StoreExchangeRecognizer` 落地 + analyze_screen extras 验收。**可裁**：若抽取对已验证 op 的改动风险超预期，本阶段记档延后自成迭代，app 主线不受阻。
**设计依据**：details/store-exchange-recognizer.md 全文
**文件面**：`src/sr_od/application/cultivation/account/operations/shop_goods_scan.py`（新建）、`shop_buy_goods.py`（导入平移）、`shop_switch_tab.py`（注释指针）、识别器新文件（落位随扫描模块目录约定）、`sr-od-test/` 对应测试
**依赖**：3.4
**优先级建议**：6
**完成判据**：
- 既有购买 op 测试一次通过（平移零行为变化）；analyze_screen 商店屏 extras 返回 C4 契约字段且语义与 extras_doc 一致（含 active_tab 在模板修复后的真实判别）
- 完成前常规检查（本节首）
**验收凭据形式**：测试输出 + analyze_screen extras 实拍对照

## 3.8 GUI 配置页

**范围**：默认形态一条龙应用设置列表配置页（6 字段开关+优先级），照现有 app 的配置页模式；独立 GUI 入口不做（无人需要）。
**设计依据**：application-flow.md §4；references/config-and-gui.md；现有 app 配置页样板（实现时取最近似一家）
**文件面**：`src/sr_od/gui/`（或现有 app 配置页所在目录同构位置）
**依赖**：3.5、3.6
**优先级建议**：5
**完成判据**：
- 配置页出现在一条龙应用设置列表；6 字段可改可存；改后运行生效（抽一项实测或对照 §9 已验通道说明）
- 完成前常规检查（本节首）
**验收凭据形式**：界面截图或控件清单对照 + 配置 yml 前后值

## 末阶段 3.9 正本更新与收尾

**范围**：按「正本更新清单」逐条更新；探索目录标注停更指针。
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档；`.debug/temp/app-explore/2026-11-13-monthly-exchange/`（加停更指针一行）
**依赖**：全部落地阶段
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致；探索目录有停更指针
**验收凭据形式**：文档对照 review

## 正本更新清单

- docs/game/screens/store.md：三件套双渠道/角标体系/期限窗口/选中态锚修复 ← 3.2、3.5（flow.md §4.2 玩法知识回填）
- docs/develop/sr_od/application/monthly_embers_exchange/ 正本区：新建 README 与结构说明（app 是什么、入口、配置），从本迭代设计正本化 ← 3.5
- skills 仓 od-dev-write-application design/overview.md：§7-§9「待首个真实 app 实装补验」状态注记更新 ← 3.6
- （若 3.7 裁延后）details/store-exchange-recognizer.md 的 v2 归档注记 ← 3.7
