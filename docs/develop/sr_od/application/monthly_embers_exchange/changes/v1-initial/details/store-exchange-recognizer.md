# 商店画面识别器 StoreExchangeRecognizer（详设）

## 1. 问题与约束

- 读数类需求的既定方向（用户裁定 2026-11-13）：**读数走画面识别器的结构化输出通道**（`analyze_screen` 的 extras），不为读数造一次性 op。
- 机制现状（依据 decomposition.md §2.1 实勘）：`ScreenRecognizer` 子类声明 `screen_name` 类属性，被框架从 `sr_od.operations` / `sr_od.application` 自动扫描注册；`analyze_screen` 精准命中画面后自动调用，结构化 dict 进 extras、字段语义进 extras_doc。现成样板：CW `SettlementRecognizer`（纯读 + 纯函数解析器复用 + 不稳定字段不硬塞）。
- 商店画面建档 `screen_name='商店'`（assets/game_data/screen_info/store.yml）。
- app 主链**不依赖**本识别器（购买 op 自带月限与余额判定并经 data 返回）；识别器服务 MCP agent 的「本月还能换啥 / 余额多少」类询问。
- 识别器内**不滚动列表**（识别器应快速、无副作用；售罄灰卡会沉到列表末尾，当前视口不可见即如实报 visible=False——不硬塞原则）。

## 2. 方案

### 2.1 extras 字段

| 字段 | 类型 | 来源 |
|---|---|---|
| `currency` | `int \| None` | `读区-货币数量` OCR 经 parse_count；读不出 = None |
| `active_tab` | `str \| None` | 三个选中态模板（`tab-余烬兑换-选中` / `tab-星芒兑换-选中` / `tab-光锥呈现-选中`）哪个命中：embers / starlight / light_cone_manifest；都不命中 = None。**依赖选中态模板重裁修复**（互串未修时该字段必然失真，识别器须在修复后验收） |
| `goods` | `dict[str, dict]` | 三件套（special_pass / pass / tracks_of_destiny）各 `{remaining, total, sold_out, visible}`；卡不在当前视口 → `visible=False` 其余字段不硬塞 |

`goods` 单项语义：`remaining`/`total` 来自卡面角标「可兑换 X/Y」解析；`sold_out=True` = 角标含「已售罄」；角标读不出时 remaining/total 为 None（sold_out 仍按关键词尽力判）。

### 2.2 单一源抽取（与购买 op 共用）

新建模块 `src/sr_od/application/cultivation/account/operations/shop_goods_scan.py`，从 `shop_buy_goods.py` **平移**以下内容（op 改为从这里导入，行为零变化，既有测试护住）：

- 商品网格几何常量（`_GRID_COL_WINDOWS` / `_CARD_WIDTH` / `_CARD_HEIGHT` / `_NAME_OFFSET_FROM_TOP` / `_LIST_Y_MIN` / `_BADGE_OFFSET`）；
- 纯函数 `locate_cards(ocr_result_list, names: set[str]) -> dict[str, Rect]`：一次 OCR 结果按名字定位多张商品卡（现 op 的 `_scan_goods` 单目标版本改为「调 locate_cards 后取目标键」，包含匹配语义不变——防星轨通票/专票一字之差误命中）；
- 纯函数 `parse_monthly_left`（从 shop_buy_goods 平移）与角标不可购关键词元组 `BADGE_UNAVAILABLE_KEYWORDS`；
- 纯函数 `badge_rect(card_rect) -> Rect`（现 `_badge_rect` 平移）。

`shop_buy_goods.py` 保留同名薄包装/导入（对外符号不变），`ShopSwitchTabOp` 的斜杠对正则解析注释指向新模块。

### 2.3 已知 OCR 形态处理

- 数量读数用 parse_count（两层取数口径同 `ShopSwitchTabOp.finish`）。
- 角标「可兑换 X/Y」解析：`r'(\d+)\s*/\s*(\d+)'` 斜杠对取值（get_positive_digits 会把 5/5 取成 55，依据 shop_buy_goods.parse_monthly_left 注释）。已知「/ 误识别为 1」的形态：v1 解析不做误读修复——角标是软读数（购买 op 的弹窗读数才是权威源），解析失败如实返回 None，不做有歧义的猜测修复（'515' 无法可靠区分 5/15 与 5\1\5）。

## 3. 关键取舍

- **备选：识别器自带独立扫描实现**——放弃：网格几何与角标解析双写必漂移（同族问题第二件即升单一源），抽模块是治本位。
- **备选：识别器支持滚动全扫**——放弃：识别器无副作用约束下滚动属交互行为，且滚动态的角标读取价值低（调用方要全量清单可走 run_operation 传只读语义的后续 v2 op），v1 收敛在当前视口。
- **备选：app 兑换段用识别器做前置 probe 省去无谓弹窗**——放弃：购买 op 自带回顶扫描与角标拦截，前置 probe 与 op 内扫描重复；app 主链保持最短。
