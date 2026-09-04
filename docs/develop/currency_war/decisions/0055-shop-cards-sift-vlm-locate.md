# 0055. 商店牌识别 OCR → SIFT(开拓者自定义名)+ 肖像区 VLM 定位

- **Status**: accepted
- **Date**: 2026-08-10
- **原编号**: D-55

## Context
开拓者真实名是开拓者,游戏里显示玩家自定义名"Momojie" → OCR 牌名读不到/匹配错。旧 SIFT 测试因**猜裁切**(screen_info 牌中心 ≠ 肖像中心,差 60-124px)误判"商店 SIFT 弱"。

## Decision Drivers
- 开拓者自定义名破 OCR 路径
- 立绘库 currency_war/portrait_plaza 已采(71 角色),SIFT 可用
- 肖像中心 ≠ screen_info 牌中心(文字带/点击点)→ 猜裁切错

## Considered Options
1. 保留 OCR(开拓者自定义名读不到)
2. 猜坐标裁切 SIFT(裁错位置 → 内点低 → 误判弱)
3. VLM 定位肖像真实中心 → 客观 SIFT 复核 → 改 SIFT(选中)

## Decision
1. screen_info 商店牌-N pc_rect → 肖像区(VLM bbox_2d 0-1000 定位 `[cx-109,70,cx+109,260]`);cx=501/754/1007/1260/1513。
2. `read_shop_cards` OCR → SIFT:裁肖像 → `identify_character`(SIFT 立绘库)→ `resolve_char_name`;faction/cost 从 roster 派生。
3. `ensure_portrait_templates(ctx)` 按需加载缓存。接口不变(`list[ShopCard]`)。

## Consequences
- 正向:5/5 GT 命中(内点 33-68);不依赖玩家名;board OCR 仍是阵营计数权威。
- 负向:开拓者 roster gap(Momojie 模板需定命途);肖像中心 vs 旧文字中心差 124px,需实机 click 核买牌落点。
- 方法论:VLM 定位(grounding,原生格式问对)可信,别猜坐标 + 别拿未验证参照系(screen_info 点击点)否定 VLM;沉淀 ui-region-detect skill「VLM 定位信任层级」。

## Links
- `· docs/develop/currency_war/strategy/05_data_wiring.md`(shop 识别)
- 关联 D-NN:D-54(共脸变体 SIFT 可区分)、ui-region-detect skill(VLM 定位信任层级)
