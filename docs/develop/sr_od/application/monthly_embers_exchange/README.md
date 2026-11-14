# 每月余烬兑换(monthly_embers_exchange)

> 正本区:本 app「现在就是这么设计的」;架构演进归 changes/ 迭代后正本化更新。

## 1. app 是什么

自动兑换常驻商店·兑换商店·余烬兑换 tab 的**月限三件套**(星轨专票 月限 5 / 星轨通票 月限动态 / 命运的足迹 月限 1),按配置开关与优先级顺序逐项拉满兑换;进一条龙默认组每日跑,「已换不重买」由购买 op 的售罄拦截承担。游戏知识(期限窗口/排序律/角标体系)见 [docs/game/screens/store.md](../../../../game/screens/store.md)「兑换商店实测补记」与「月限三件套」节。

## 2. 运行语义

- **编排**(四段式):导航段 `OpenExchangeShop` → 兑换段(按优先级逐项 `ExchangeShopBuyGoods(count=None, scroll_search=False)`)→ 返回段 `BackToNormalWorldPlus`。无领奖段(获得物品弹窗在购买 op 内)。
- **首屏判定**:月限三件套可用排前、售罄沉底——首屏没有即本期已尽,跳过不滚动。
- **分支语义**:购买失败带 `data.fail_status`(SOLD_OUT/CARD_UNAVAILABLE/NOT_FOUND/INSUFFICIENT_MATERIALS)→ 跳过或终止循环(余额不足即终止,其后项放弃);其余失败 = 非预期 → 尽力返回大世界后 FAIL。
- **运行记录**:周期 DAILY,预期内完成(含全售罄/零购买/余额终止)照常标完成;`bought_*` 当日累计、`skip_note` 单次运行诊断(运行开始清零)、`balance_left` 最近观测。取舍依据(为何不是 MONTHLY):期限口径未分辨,日周期在月历/版本周两口径下额度解锁都最迟次日补上。
- **时序**:常规兑换 1-2 分钟;全售罄空跑整跑约 2 分钟。

## 3. 配置

`MonthlyEmbersExchangeConfig`(ApplicationConfig,`config/<idx>/<group>/monthly_embers_exchange.yml`):三件套各 `enabled` + `priority`(默认全开,优先级 10/20/30 = 专票>通票>足迹)。数量固定拉满不可配(用户裁定)。

读写通道:GUI(一条龙→每月余烬兑换页)、MCP(`describe_config`/`get_config`/`set_config`,经 config_router 登记)、运行时(factory 缓存实例,三者同一份,写立即生效)。

## 4. 组成与文档

- app 包:`src/sr_od/application/monthly_embers_exchange/`(const/config/run_record/app/factory)
- 依赖 op:`ExchangeShopBuyGoods`(购买,内含切 tab)、`OpenExchangeShop`(导航,operations/store/)、`BackToNormalWorldPlus`
- 读数通道:`StoreExchangeRecognizer`(operations/store/,analyze_screen extras:余额/选中 tab/三件套角标)
- 扫描单一源:`shop_goods_scan.py`(网格几何/卡定位/角标解析,购买 op 与识别器共用)
- 迭代过程:`changes/v1-initial/`(设计→对抗→落地全记录)
