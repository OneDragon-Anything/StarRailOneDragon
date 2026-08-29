---
gameplay_name: 仙舟过期邮包
app_id: buy_xianzhou_parcel
last_updated: 2026-08-29
source: `application/buy_xianzhou_parcel/` + `config/custom_combine_op/buy_xianzhou_parcel.yml` + `operations/store/buy_store_item.py`
involves_screens: [大世界, 对话, 商店]
---

# 仙舟过期邮包(buy_xianzhou_parcel)

每周在仙舟「罗浮」流云渡找 NPC **茂贞** 购买「逾期未取的贵重邮包」——随机奖励包(信用点消耗,低买高值的赌性质周常)。bot 流程是**自定义组合指令**(`config/custom_combine_op/buy_xianzhou_parcel.yml`),非专用 op 链。

## 玩法机制

- 茂贞(流云渡·积玉坊)每周出售 1 个「逾期未取的贵重邮包」,信用点定价,开出随机奖励(有概率出高价值遗器/材料)。
- 每周刷新(周一);本周已购 → 售罄。
- 纯信用点消耗,无开拓力。

## bot 流程(CustomCombineOp `buy_xianzhou_parcel`)

`back_to_world_plus` → `transport`(仙舟「罗浮」/流云渡/1/积玉坊)→ `wait in_world` → `move`(393,789)→ `interact world_single_line 茂贞` → `interact talk 我想买个过期邮包试试手气` → `buy_store_item xianzhou_parcel 0`(0=最大数量;`allow_fail=true`,售罄/材料不足时走取消退出)→ `back_to_world_plus`。

## 涉及画面(均已建档)

- 大世界:传送落地 + 走位 + NPC 交互提示(`移动交互-单行`,F 对话)。
- 对话:talk 选项「我想买个过期邮包试试手气」。
- 商店:NPC 杂货摊与菜单商店共用 `商店` 画面档的购买弹窗 area(商品列表/购买最大值/确认/取消/已售罄;见 [screens/商店](../screens/store.md))。

## 备注 / 待查

- **售罄是常态分支**:`BuyStoreItem` 检测 `购买-已售罄` / `购买-兑换材料不足` → 主动点取消退出;`allow_fail=true` 让整个组合指令不因本周已购而失败。
- **跑周常时序**:每周一刷新后跑收益最大;一周内重复跑会走售罄分支(仍算成功)。
- 该 app 是 CustomCombineOp 配置驱动模式的样板(传送+走位+对话+购买拼装),同类「跑腿购买」玩法可照抄此模式。
