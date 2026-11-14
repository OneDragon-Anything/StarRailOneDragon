# operation-flow-1 · OpenExchangeShop（op 设计书）

## 1. 目标一句话

从任意画面导航到商店页的兑换商店（常驻商店），画面停在商店商品列表页；子 tab 不指定（留给调用方切换，业务决策不进导航 op）。

## 2. 起点 / 结束画面

- 起点：任意画面（大世界 / 菜单 / 商店任意页 / 其他玩法画面）。
- 结束：`商店` 画面，兑换商店子页（左列子商店 tab 栏可见，含 星芒兑换/余烬兑换/光锥呈现/戏言成真）。

## 3. 流转（逐跳）

```
[任意画面]
  --[画面级判定: 已在 商店 → 跳到第 3 跳]
  --[OpenPhoneMenu(内部: 在菜单=成功; 大世界=按菜单键(ESC); 其他=BackToNormalWorldPlus 兜底重试)]
  --> 菜单
  --[点 入口-商店, until 商店画面出现(tab-常驻商店 可见); 菜单→商店过场 ≤9s(建档 8-10s, flow.md §4.2-4)]
  --> 商店(默认推荐页)
  --[点 tab-常驻商店, until 兑换子 tab 出现(tab-余烬兑换 可见)]
  --> 商店·兑换商店列表页  [结束]
```

- 判定与锚（画面名+区域名，全部已建档）：`商店` / `tab-常驻商店`（store.yml 第 77 行区域）、`菜单` / `入口-商店`（phone_menu.yml 第 206 行区域）、`tab-余烬兑换`（store.yml 第 259 行区域，未选中白字文本常显，作「兑换子页已打开」的证据）。
- 转移验证全部走 until（点了 ≠ 成了）：入口-商店的 until 用目标页 tab 区锚；tab-常驻商店的 until 用兑换子 tab 锚。禁止不传 until 的点击。
- 幂等：起点已在商店页时直接跳到最后一跳（切常驻商店），不重复开菜单。
- 键盘使用说明：开菜单走 `OpenPhoneMenu`（内部按菜单键 ESC）——框架标准路径，左上手机图标手点无效（实测，flow.md §4.1-3）；本 op 不直接发键。

## 4. 红线

无真实消耗、无不可逆操作（纯导航）。

## 5. 结果状态

- `SUCCESS`：已到兑换商店列表页。
- 失败：画面识别失败 / 点击后锚超时未出现（节点预算耗尽），status 缺省 FAIL，message 带当前画面名。

## 6. 放置位置

`src/sr_od/operations/shop/open_exchange_shop.py`（operations 顶层包新建 shop 子包）。判定依据：商店是跨玩法通用画面，此导航链不依赖任何 app 的业务配置，属跨 app 复用件；对照现有先例——跃迁页进商店的 `enter_shop_from_warp` 放在特定业务包（cultivation/account），因其入口绑定跃迁业务；本 op 入口是通用手机菜单，归顶层 operations。构造参数只有 ctx（无参业务参数），MCP registry 可直接构造（对照：`ClickPhoneMenuItem` 的 `PhoneMenuItem` 参数无法经 MCP 构造，实测 2026-11-13，decomposition.md §2）。
