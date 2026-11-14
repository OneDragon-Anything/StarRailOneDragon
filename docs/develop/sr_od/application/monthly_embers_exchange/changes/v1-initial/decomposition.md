# 月度限量兑换 app · op 拆解总表（迭代沉淀版）

> 沉淀自探索目录 decomposition.md，按定稿编排同步更新。op 逐个设计书见 operation-flow-1.md（新 op 唯一一份）；识别器设计见 details/store-exchange-recognizer.md。

## 1. 拆解原则

- 拆出的每个 op 独立可用：MCP agent 单独 `run_operation` 就能完成一个有意义的动作。
- app 只做编排（导航 + 优先级循环 + 返回），不含业务动作。
- 已验证件不重写：`ExchangeShopBuyGoods` / `ShopSwitchTabOp` / `OpenPhoneMenu` / `BackToNormalWorldPlus` 全复用。

## 2. op 清单与复用判定

| op | 覆盖判定 | 说明 |
|---|---|---|
| `ExchangeShopBuyGoods` | **全覆盖·直接复用** | 参数全简单类型，MCP 直接可传；`count=None` 拉满；内部自动切目标 tab；PURCHASED data 带实际数量/单价/余额/月限剩余。**扩展项**：失败出口在 data 补机器可读字段 `fail_status`（SOLD_OUT / CARD_UNAVAILABLE / NOT_FOUND / INSUFFICIENT_MATERIALS，逐口落位见 application-flow.md §3.1 权威表；status 保持人读诊断句），供 app 分支；只加 data 字段不改流程行为与消息文本，既有测试护住 |
| `ShopSwitchTabOp` | 复用（被购买 op 内部调用） | 选中态模板互串修复是**实现前置件**（flow.md §4.1-1）；修复后其切换验证从空转恢复真验证 |
| `OpenPhoneMenu` / `BackToNormalWorldPlus` | 全覆盖·直接复用 | 无参构造，MCP 直接可用 |
| `OpenExchangeShop` | **无覆盖·新建** | 手机菜单→商店→兑换商店的无参导航；MCP agent 一键到位；`ClickPhoneMenuItem` 的 `PhoneMenuItem` 参数 MCP 无法构造（实测 2026-11-13），无参包装才是可用形态。落位 `src/sr_od/operations/store/`（商店域现有子包，不另立双包）。设计书 operation-flow-1.md |

样板备注：`enter_shop_from_warp`（跃迁页进商店）与本 op 同型不同入口（跃迁业务绑定 vs 手机菜单通用），不合并。

## 3. 读数去向（不造读数 op）

读数走画面识别器 extras 通道：`StoreExchangeRecognizer`（screen_name='商店'），字段 currency / active_tab / goods 三件套角标；解析逻辑与购买 op 单一源共用（模块抽取方案见 details/store-exchange-recognizer.md §2.2）。app 主链不消费识别器（购买 op data 已带全部所需读数）。MCP 价值：「本月还能换啥 / 余额多少」不进弹窗即可答。

## 4. 开放点

全部已裁定并落档：单项失败=中止（requirement §3-5，预期内结果区分见 application-flow §3）；星芒渠道不进 v1（§3-6）；优先级兜底 专票>通票>足迹（§3-8）；通票 2/5 留端到端实测（§3-7）；运行记录周期改 DAILY（2026-11-14 周期语义缺陷修订，见 requirement §4 与 design §2.4）。无未决开放点。
