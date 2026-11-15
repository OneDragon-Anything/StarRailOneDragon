# 每月合成(monthly_synthesize)

> 正本区:本 app「现在就是这么设计的」;架构演进归 changes/ 迭代后正本化更新。

## 1. app 是什么

自动把**每月限量合成**的物品合成拉满——当前唯一项:自塑尘脂(材料合成分类,合成遗器时指定主词条用,单价遗器残骸×800,每月合成上限画面文案「本月还可合成: N」)。数量固定拉满不可配(用户裁定 2026-11-15);进一条龙默认组,月内首跑完成后不再跑;材料不足判失败不标完成,由一条龙日批重跑补做(用户裁定)。

## 2. 运行语义

- **四段式**:导航+玩法段 `合成自塑尘脂`(开关分流 → `Synthesize(SELF_MODELING_RESIN)`,op 内部自带回大世界→菜单→合成导航)→ 返回段 `BackToNormalWorldPlus`。无领奖段(合成确认/关闭在 op 内闭环);失败收尾节点尽力回大世界后带原始语境 FAIL。
- **数量策略**(数量按物品分流,`SynthesizeItem.quantity_mode`):
  - `max_btn`(默认,奇巧零食在用):消耗品合成页点「最大值」,原路径不动;
  - `plus_monthly`(自塑尘脂):材料合成页滑条 UI 无「最大值」按钮——「+」按钮逐次点满,**置灰判顶**(亮/灰模板限定在 + 按钮局部区域匹配,全图裸匹配会误命中形近「−」按钮);入口即置灰为歧义态,读「本月还可合成」消歧(0=无事可做跳过;≥1=已到顶,合成当前数量;读不出=失败不冒险);
  - `QUOTA_EXHAUSTED` / `ITEM_ABSENT_FIRST_SCREEN` 各挂**精确状态边**接终止节点,绝不误点合成(兜底边接管语义,缺边会对自动选中的无关物品执行合成)。
- **首屏判定**(额度用尽判据):材料合成列表按「可合成排前、不可用沉底」排序——物品首屏未见即本期不可合成,不拖拽深扫;成因按运行记录当月锚 `resin_quota_confirmed` 裁定(已锚=额度用尽,标完成;未锚=材料不足或额度被人手用尽,判失败)。已知边界:额度被人手提前用尽且当月 app 从未成功过 → 日批失败噪音到月底,下月自愈。
- **分支语义**:op 成功(合成完成/额度用完/首屏未见且已锚)与开关关 = 月度职责履行,标本月完成(开关关标本完成与余烬兑换全关口径一致,月内途开需手动单跑);op 失败(材料不足/识别失败)= FAIL 不标,一条龙日批重跑。
- **运行记录**:周期 MONTHLY(月限额度自然月刷新,跨月复位待完整月界复核);业务字段仅 `resin_quota_confirmed` 当月锚(数量数值不留痕,用户裁定)。
- **时序**:正常 1-2 分钟;额度用尽空跑约 7 秒;开关关空跑约 1 秒。

## 3. 配置

`MonthlySynthesizeConfig`(ApplicationConfig,`config/<idx>/<group>/monthly_synthesize.yml`):`self_modeling_resin_enabled` 开关,默认开(用户裁定)。未来新增月限物品:`MONTHLY_ITEMS` 追加标识符 + config 加 `{item}_enabled` 开关 + 编排节点扩展。

读写通道:MCP(`describe_config`/`get_config`/`set_config`)、运行时(factory 缓存实例,写立即生效);GUI 配置页暂未做(默认形态待 app 验收后补)。

## 4. 组成与文档

- app 包:`src/sr_od/application/monthly_synthesize/`(const/config/run_record/app/factory)
- 依赖 op:`Synthesize`(operations/synthesize/,数量策略分流)+ `BackToNormalWorldPlus`
- 画面建档:`合成` 画面新增 `分类-材料合成` / `按钮-数量增加`(亮)/ `按钮-数量增加-置灰` / `读区-本月还可合成`;模板 `assets/template/synthesize/{self_modeling_resin,quantity_plus,quantity_plus_max}/raw.png`
- 迭代过程:`changes/v1-initial/`(设计→落地全记录)
