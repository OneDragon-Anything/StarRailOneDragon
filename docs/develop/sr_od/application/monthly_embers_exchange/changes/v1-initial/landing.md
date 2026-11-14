# v1-initial 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过（不对整个 src/ 跑）；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/ -m "not slow"` 相关子集；改公共包时含其测试）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），提交后 `git show --stat` 复核入库面 = 申报面；在飞并行批文件（game-coach 重组、dungeon-data-entry、mcp-runnable.md、writing-agent-instructions 等）一律不卷入；
- 改了任何 Python 代码后，实机验证前必须重启 MCP server（框架缓存已加载模块）；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」、MCP 节。

## 3.1 tab 选中态模板重裁（实现前置阻断项）

**范围**：先把两张实拍裁源从 `.debug` 归档进 sr-od-test fixtures（`.debug` 易失，判据不能依赖它）；重裁 `tab-星芒兑换-选中` / `tab-余烬兑换-选中` 两模板为含高亮下划线区域（裁源坐标以像素级核对为准，选中判别特征=白字+底部白色下划线，未选中=灰字无下划线）；离线验证两图互不命中；实机验证 `ShopSwitchTabOp` 切换验证真生效。不含其他 store 建档改动。
**设计依据**：flow.md §4.1-1（缺陷与修法、阈值 0.7）；归档判据源 = design.md §2.1-4
**文件面**：`assets/template/store/store_tab_embers_active/`、`assets/template/store/store_tab_starlight_active/`、必要时 `assets/game_data/screen_info/store.yml`（经 MCP upsert_screen_area 改，禁手改 yml）；`sr-od-test/` fixtures 归档 + 可选的离线模板互斥测试
**依赖**：无（3.4 实机串联依赖本阶段）
**优先级建议**：9
**完成判据**：
- 两张实拍已归档进 fixtures（路径在测试/判据中引用）
- 离线：analyze_screen(screenshot=归档星芒选中实拍) 只有星芒选中区命中、余烬选中区不命中；余烬选中实拍反之（对照 flow.md §4.1-1 修法）
- 实机：商店页跑 `ShopSwitchTabOp(embers)` 成功后选中判定与真实选中一致；切回星芒同理
- 完成前常规检查（本节首）
**验收凭据形式**：两次 analyze_screen 输出对照 + run_operation 输出

## 3.2 OpenExchangeShop op

**范围**：按设计书在 `src/sr_od/operations/store/` 实现无参导航 op；run_operation 实机验证（起点=大世界、起点=商店页幂等、起点=其他画面三条路径至少各验一遍关键路径）。
**设计依据**：operation-flow-1.md 全文
**文件面**：`src/sr_od/operations/store/open_exchange_shop.py`（新文件）；`sr-od-test/`（op 流程测试，如样板适用）
**依赖**：无（实机验证建议在 3.1 后跑，锚更可信；不阻塞开发）
**优先级建议**：8
**完成判据**：
- 三条起点路径走通且终点=商店兑换列表页（对照设计书 §3 流转，全部点击带 until）
- 完成前常规检查（本节首）
**验收凭据形式**：run_operation 输出（结果状态/耗时）+ 流程测试（如适用）

## 3.3 ExchangeShopBuyGoods 语义状态扩展

**范围**：失败出口在 data 补 `fail_status` 字段，语义集与逐口落位严格按 application-flow.md §3.1 表（SOLD_OUT / CARD_UNAVAILABLE / NOT_FOUND / INSUFFICIENT_MATERIALS 各自的出口清单，无遗漏无多余）；`status` 保持人读诊断句、消息文本与流程行为零变化；既有测试同步（含「无 fail_status 的失败=非预期」断言）。
**设计依据**：application-flow.md §3.1（契约 C2 权威表）；shop_buy_goods.py 现有失败出口清单（代码内）
**文件面**：`src/sr_od/application/cultivation/account/operations/shop_buy_goods.py`；`sr-od-test/test/sr_od/application/cultivation/account/operations/test_shop_buy_goods*`
**依赖**：无
**优先级建议**：8
**完成判据**：
- §3.1 表的每个出口在代码中可指认且 fail_status 落位正确；status 全部保持原诊断句；直接受影响流程测试一次通过
- 完成前常规检查（本节首）
**验收凭据形式**：测试名 + 通过输出

## 3.4 app 五件套与串联验证（真实兑换用例）

**范围**：const（无 PRIORITY）/ config（ApplicationConfig 子类 + `*_adapter` 属性）/ run_record（DAILY + 业务字段 + reset_record 覆写）/ factory（create_application 注入 config+run_record、create_config、create_run_record）/ app 类（节点图按 application-flow §1，含 n4 失败收尾）+ config_router.py 登记 RouterEntry；注册确认；`run_standalone_app` 实机串联第一跑——**含通票 2 张真实兑换（用户裁定 7 授权，唯一一次授权的真实消耗）**，验证成功兑换路径全链。
**设计依据**：application-flow.md 全文；requirement.md §3；样板 = large_map_recorder（factory/config 注入）+ trick_snack（run_record 形态）+ config_router trailblaze_power 条目（RouterEntry 写法）
**文件面**：`src/sr_od/application/monthly_embers_exchange/`（新建包）；`src/sr_od/backend/config_router.py`（新增 RouterEntry）；`sr-od-test/`（排序/分支映射等可测逻辑）；**不含 SrContext 改动**（config/run_record 均走 factory 与 run_context 通道）
**依赖**：3.1、3.2、3.3
**优先级建议**：10
**完成判据**：
- `list_applications` 可见 monthly_embers_exchange 且 DEFAULT_GROUP=True（对照 application-flow §1 注册件）
- 串联第一跑：导航→专票(售罄跳过)→通票(真实购买 2 张, PURCHASED)→足迹(售罄跳过)→返回大世界；运行记录 bought_pass=2、skip_note 含两项、状态成功标完成（对照 §3.2 表）
- 全程点击带 until；分支只认 data.fail_status（对照 §3.1 表逐行核）；非预期失败路径走 n4 尽力返回（对照 §1 节点图 n4 语义）
- MCP 配置工具可达：describe_config 返回 6 字段结构（可达性验收在此，读写实测在 3.5）
- 完成前常规检查（本节首）
**验收凭据形式**：run_standalone_app 输出 + 运行记录 yml 内容 + 游戏内通票数量前后对照 + describe_config 回显

## 3.5 端到端验收

**范围**：`run_standalone_app` 第二跑（三件套全售罄形态）验证「预期内无事可做→标完成」路径；MCP 配置工具读写实测（describe 结构清晰 / get→set→get 一轮 / 写后下一跑生效）；结束通知按 NEED_NOTIFY 发出核验。
**设计依据**：application-flow.md §3.2 终态表、§4 config 表；skill od-dev-write-application §7
**文件面**：无代码改动（发现问题走 3.4 返工）；配置改动经 MCP 工具
**依赖**：3.4
**优先级建议**：10
**完成判据**：
- 第二跑零购买、skip_note 含三项、状态成功标完成（对照 §3.2 表行 1）；当日重复发起一条龙同 app 被跳过（is_done 生效）
- describe_config 对 6 个字段语义清晰；get→set→get 读回一致；set 后读配置实例值已变（同缓存写穿）
- 通知发出（或 NEED_NOTIFY=False 时的口径核对）
- 完成前常规检查（本节首；无代码改动则仅核提交面为空）
**验收凭据形式**：run_standalone_app 输出 + describe/get/set 回显 + 通知记录

## 3.6 画面识别器与扫描单一源抽取（可裁项）

**范围**：抽 `shop_goods_scan.py`（平移收拢清单严格按 details/store-exchange-recognizer.md §2.2 表——含首版曾漏的 `_locate_window`/`MONTHLY_TRIO`/`ocr_rect_text`/强化版 `read_count_two_pass` 与斜杠对单源签名 `parse_exchange_pair`）+ `StoreExchangeRecognizer` 落地 + analyze_screen extras 验收。**可裁**：若抽取对已验证 op 的改动风险超预期，本阶段记档延后自成迭代，app 主线不受阻。
**设计依据**：details/store-exchange-recognizer.md 全文
**文件面**：`src/sr_od/application/cultivation/account/operations/shop_goods_scan.py`（新建）、`shop_buy_goods.py`（导入平移）、`shop_switch_tab.py`（改调 parse_exchange_pair / read_count_two_pass）、`src/sr_od/operations/store/store_exchange_recognizer.py`（新建）、`sr-od-test/` 对应测试
**依赖**：3.1（active_tab 真实判别依赖模板修复）、3.3（抽取在语义状态扩展之上做，避免同文件并行改动）
**优先级建议**：6
**完成判据**：
- 既有购买 op 测试一次通过（平移零行为变化；switch_tab 两层取数统一强化版为唯一注明行为变化）；analyze_screen 商店屏 extras 返回 C4 契约字段且语义与 extras_doc 一致（含 active_tab 在模板修复后的真实判别）
- 完成前常规检查（本节首）
**验收凭据形式**：测试输出 + analyze_screen extras 实拍对照

## 3.7 GUI 配置页

**范围**：默认形态一条龙应用设置列表配置页（6 字段开关+优先级），照现有 app 的配置页模式；独立 GUI 入口不做（无人需要）。
**设计依据**：application-flow.md §4（config 通道：GUI 经 `ctx.run_context.get_config` 取缓存实例 + `*_adapter` 绑定）；references/config-and-gui.md；现有 app 配置页样板（实现时取最近似一家）
**文件面**：`src/sr_od/gui/interface/one_dragon/`（配置页新文件）+ `src/sr_od/gui/interface/one_dragon/sr_one_dragon_interface.py`（add_sub_interface 手动注册——框架不自动发现 GUI）
**依赖**：3.4、3.5
**优先级建议**：5
**完成判据**：
- 配置页出现在一条龙应用设置列表；6 字段可改可存（adapter 双向同步）；改后运行生效
- 完成前常规检查（本节首）
**验收凭据形式**：界面截图或控件清单对照 + 配置 yml 前后值

## 末阶段：正本更新（3.8）

**范围**：按「正本更新清单」逐条更新；探索目录标注停更指针；skill 分歧走反馈件（不直改公共 skills 仓——AGENTS.local.md §1 红线）。
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档与反馈件；`.debug/temp/app-explore/2026-11-13-monthly-exchange/`（加停更指针一行）
**依赖**：全部落地阶段
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致；探索目录有停更指针
**验收凭据形式**：文档对照 review

## 正本更新清单

- docs/game/screens/store.md：三件套双渠道/角标体系/期限窗口/选中态锚修复（含信用点双形态复核结论）← 3.1、3.4（flow.md §4.2 玩法知识回填）
- docs/develop/sr_od/application/monthly_embers_exchange/ 正本区：新建 README 与结构说明（app 是什么、入口、配置、运行语义），从本迭代设计正本化 ← 3.4
- `.debug/temp/skill_feedback.md`：write-application skill 两处分歧反馈——①§9「通用配置工具自动读写」承诺 vs SR 实码 config_router 手工路由（app 必须登记 RouterEntry 才可达）；②§7-§9 首个真实 app 实装补验结论 ← 3.5
- （若 3.6 裁延后）details/store-exchange-recognizer.md 的 v2 归档注记 ← 3.6
