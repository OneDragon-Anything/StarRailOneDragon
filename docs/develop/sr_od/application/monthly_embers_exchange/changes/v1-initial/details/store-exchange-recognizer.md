# 商店画面识别器 StoreExchangeRecognizer（详设）

## 1. 问题与约束

- 读数类需求的既定方向（用户裁定 2026-11-13）：**读数走画面识别器的结构化输出通道**（`analyze_screen` 的 extras），不为读数造一次性 op。
- 机制现状（依据 = `src/sr_od/backend/screen_recognizer_scan.py`：扫描根 `sr_od.operations`+`sr_od.application`、rglob 全 .py、`__module__` 守卫、**无参实例化**；`src/one_dragon/base/screen/screen_recognizer.py`：`recognize(ctx, image, screen_info)` 签名与 extras_doc 键集契约）：`ScreenRecognizer` 子类声明 `screen_name` 类属性即被自动扫描注册；`analyze_screen` 精准命中画面后自动调用，结构化 dict 进 extras、字段语义进 extras_doc。现成样板：CW `SettlementRecognizer`（纯读 + 纯函数解析器复用 + extras_doc 键集=返回键集 + 不稳定字段不硬塞）。现有识别器无 `screen_name='商店'` 撞名。
- 商店画面建档 `screen_name='商店'`（assets/game_data/screen_info/store.yml）。
- app 主链**不依赖**本识别器（购买 op 自带月限与余额判定并经 data 返回）；识别器服务 MCP agent 的「本月还能换啥 / 余额多少」类询问。
- 识别器内**不滚动列表**（识别器应快速、无副作用；售罄灰卡会沉到列表末尾，当前视口不可见即如实报 visible=False——不硬塞原则）。

## 2. 方案

### 2.1 extras 字段

| 字段 | 类型 | 来源 |
|---|---|---|
| `currency` | `int \| None` | `读区-货币数量` 经两层取数（§2.2 的 read_count_two_pass）；读不出 = None |
| `active_tab` | `str \| None` | 三个选中态模板（`tab-余烬兑换-选中` / `tab-星芒兑换-选中` / `tab-光锥呈现-选中`）哪个命中：embers / starlight / light_cone_manifest；都不命中 = None。**依赖选中态模板重裁修复**（互串未修时该字段必然失真，识别器须在修复后验收） |
| `goods` | `dict[str, dict]` | 三件套（special_pass / pass / tracks_of_destiny）各 `{remaining, total, sold_out, visible}`；卡不在当前视口 → `visible=False` 其余字段不硬塞 |

`goods` 单项语义：`remaining`/`total` 来自卡面角标「可兑换 X/Y」解析（parse_exchange_pair）；`sold_out=True` = 角标含「已售罄」；角标读不出时 remaining/total 为 None（sold_out 仍按关键词尽力判）。

### 2.2 单一源抽取（与购买 op 共用）

新建模块 `src/sr_od/application/cultivation/account/operations/shop_goods_scan.py`，从 `shop_buy_goods.py` / `shop_switch_tab.py` **平移并收拢**以下内容（两 op 改为从这里导入；消费方行为除注明处外零变化，既有测试护住）：

| 符号 | 来源 | 说明 |
|---|---|---|
| 商品网格几何常量（`_GRID_COL_WINDOWS` / `_CARD_WIDTH` / `_CARD_HEIGHT` / `_NAME_OFFSET_FROM_TOP` / `_LIST_Y_MIN` / `_BADGE_OFFSET`） | shop_buy_goods | 原值平移 |
| `_locate_window` 列窗口归列 | shop_buy_goods | `locate_cards` 的必需依赖 |
| `locate_cards(ocr_result_list, names: set[str]) -> dict[str, Rect]` | 抽自 `_scan_goods` | 一次 OCR 结果按名字定位多张商品卡；op 的 `_scan_goods` 改为「调 locate_cards 后取目标键」，包含匹配语义不变（防星轨通票/专票一字之差误命中） |
| `MONTHLY_TRIO: dict[str, str]`（special_pass/pass/tracks_of_destiny → OCR 关键词） | 抽自 `_GOODS_META` 前三条 | 三件套映射单源化：shop_buy_goods 的 `_GOODS_META` 对应三条改为引用本常量（对照表不出现第二源）；识别器按它定位卡 |
| `parse_exchange_pair(text) -> tuple[int, int] \| None`（斜杠对取双值） | 合并 shop_buy_goods `parse_monthly_left` 与 shop_switch_tab.finish 的同款正则 | **斜杠对解析的单一源签名**（返回 remaining+total 对；商店域现有两处同款正则收拢为一——CW 域另有同型两处，不属本域范围）；`parse_monthly_left` 保留为薄包装（取首值），shop_switch_tab.finish 改调它（data 键不变，行为零变化） |
| `BADGE_UNAVAILABLE_KEYWORDS` 角标不可购关键词 | shop_buy_goods | 原值平移 |
| `badge_rect(card_rect)` | shop_buy_goods `_badge_rect` | 原逻辑平移 |
| `ocr_rect_text(ocr_service, screen, rect)` | 抽自 shop_buy_goods `_ocr_rect_text` | 角标读取管线（读关键词必备件） |
| `read_count_two_pass(ocr_service, ocr, screen, area)` | 取 **shop_buy_goods 版**口径 | 两层取数（全图过滤 → 放大兜底）现网两份实现已漂移（shop_switch_tab 的弱化版首层非数字即返回；shop_buy_goods 的强化版非数字一律放大重试）——同族第二件升单一源，统一到强化版；`ShopSwitchTabOp.finish` 与购买 op 的余额读取都改调它（switch_tab 读数健壮性提升为唯一行为变化） |

`shop_buy_goods.py` / `shop_switch_tab.py` 保留同名薄包装或直接改导入（对外符号与行为不变），注释指向新模块。

### 2.3 识别器本体

- 落位 `src/sr_od/operations/store/store_exchange_recognizer.py`（与 OpenExchangeShop 同属 operations/store/ 商店域；扫描根覆盖 sr_od.operations 全子树）。
- 构造**无参**（扫描注册机制无参实例化）；screen_name='商店'。
- recognize(ctx, image, screen_info)：当前视口 OCR 一次 → locate_cards 定位三件套 → 逐卡角标读区（badge_rect + ocr_rect_text）判 sold_out / parse_exchange_pair → 组装 §2.1 extras。currency 用 read_count_two_pass。
- 字段纪律（对照 CW 样板）：extras_doc 键集 = 返回键集；读不出的字段如实 None/不硬塞。

### 2.4 已知 OCR 形态处理

- 角标「可兑换 X/Y」解析：`r'(\d+)\s*/\s*(\d+)'` 斜杠对取值（get_positive_digits 会把 5/5 取成 55，依据 shop_buy_goods.parse_monthly_left 注释）。已知「/ 误识别为 1」的形态：v1 解析不做误读修复——角标是软读数（购买链权威读数在弹窗：月限胶囊 + 价格互推 + 余额差值终验；count=None 拉满上限由游戏滑条自身钳制，误读不会导致错误购买），解析失败如实返回 None，不做有歧义的猜测修复（'515' 无法可靠区分 5/15 与 5\1\5）。

## 3. 关键取舍

- **备选：识别器自带独立扫描实现**——放弃：网格几何与角标解析双写必漂移（同族问题第二件即升单一源），抽模块是治本位；抽取同时收拢两 op 已漂移的两层取数与两处同款正则（§2.2）。
- **备选：识别器支持滚动全扫**——放弃：识别器无副作用约束下滚动属交互行为，且滚动态的角标读取价值低（调用方要全量清单可走后续 v2 只读 op），v1 收敛在当前视口。
- **备选：app 兑换段用识别器做前置 probe 省去无谓弹窗**——放弃：购买 op 自带回顶扫描与角标拦截，前置 probe 与 op 内扫描重复；app 主链保持最短。
