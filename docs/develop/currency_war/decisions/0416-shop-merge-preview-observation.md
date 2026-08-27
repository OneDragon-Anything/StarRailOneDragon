# ADR-0416: 升星预览✦观测读取(ShopCard.merge_preview,评分层接线挂账)

## 背景

商店牌 art 顶部有「已持同名同星副本数」✦显影(迭代档案 W104 发现:✦ 数 = merge_progress 份数,买第 3 张即 3合1 升星)——游戏内视觉印证 bot tracking 的 merge_progress。策略池 L19「预测升星✦视觉信号接线」原条件(观测层冗余加固排期,fixture 已在测试仓)盘点裁定前置实质满足(W282)。此前观测层完全不读该信号:merge_progress 只有 bot tracking 一个源,无视觉对账通道。

## 决策

观测层落读取器,评分层**不接线**(消费方未备,声明):

- `cw_identity_obs.read_merge_preview(crop)`:商店牌-N crop 顶部带(HSV 严窗口 H22-40/S≥60/**V≥248 自发光截断** → 二值 mask → 单✦ TM 模板匹配 → NMS 分离相邻✦ → peak 局部 area 门)。不复用金星 `_STAR_GOLD`(10-45/V>150)——fixture 实测该窗口把亮色立绘背景/金发全部吃进(card5 顶带连成 146px 大域)。模板 `assets/template/currency_war/star/shop_preview_sparkle_tmpl.png`(29x25 二值 mask,单样本提取);阈值 0.60(fixture 标定:真✦ 0.96/0.99,负样本 max 0.475)。
- `ShopCard.merge_preview: int = 0`(坐标系/取值时机/双义语义全注在字段注释);`read_shop_cards` 与 SIFT 同 crop 填充(零额外裁切);遥测 `shop_snapshots` 序列化加 `merge_preview` 键、supply 视图 `✦名xN` 显影;`cw_replay` 回放保真透传。
- **0 = 双义**(真无副本 ∨ fail-silent 读不到,模板缺失即恒 0)——与 `read_star` 的 fallback 1 性质相反:本信号是冗余印证,缺读 ≠ 真值,消费方须按「未观测」对待,不得做否定性决策。
- sim 不建模(视觉信号离线无源,sim ShopCard 恒 0;与「新读点查写入端」纪律一致:评分层若接线,读的是进店帧快照,非执行期现读)。

**评分层未接线的声明**:decision_v2 的 merge_progress/filler_star(ADR-0402)全走 bot tracking,无任何消费点读 `ShopCard.merge_preview`;视觉源与 tracking 的对账(cw_reconcile 面)及「视觉≠tracking 时信谁」的裁决,等首个真实消费场景立项再做,不预建悬空通道。

## Considered Options

1. **采纳:观测值 + 遥测 + 消费方声明挂账**(本批)。
2. 拒:立刻接评分层——无消费场景的接线是悬空通道(防坑清单「新读点查写入端/新字段查三消费面」);merge_progress 已有 tracking 源在评分链工作,视觉源当前零增量信息,先攒对账样本。
3. 拒:复用金星 HSV 窗口加位置过滤——fixture 实测亮色背景淹没,严窗口 + 独立模板才是可标定的最小实现。
4. 拒:读不到 fallback 语义——0 双义已是缺陷,再 fallback 成非零会把「未观测」伪装成「确认有副本」,方向性毒害。

## Consequences

- 进店帧起 shop 快照带✦数,`cw_telemetry --view supply` 可见 merge 预览显影,为后续「视觉 vs tracking」对账攒历史样本。
- 模板单样本标定(仅 1 张含✦ fixture):换版本/光照漂移时由单帧锁(test_cw_w282_merge_preview)红出再补样本;area 门未设形状 circ 门(无第二形状证据),阈值余量 ~0.12/0.13。
- 旧数据(字段缺)supply 视图不显影✦;cw_replay 对旧快照填 0(双义语义不变)。

## 验证

- 单帧锁 4(sr-od-test/test/sr_od/app/currency_war/test_cw_w282_merge_preview.py,入 cw_quick):模板资产在库 / 直裁读取 [0,0,0,0,2] / 生产路径 read_shop_cards 全链 card5=2 + 默认值 / 模板缺失 fail-silent 0。
- 负样本窗:同帧 card1-4 + shop_open/shop_closed fixture 全 5 牌读取 ≤0.475(标定记录,未入锁)。
- ruff 通过;CW 域 L1 全量回归。
