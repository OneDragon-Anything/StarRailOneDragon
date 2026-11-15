# operation-flow-1:Synthesize op 扩展(月限物品数量策略)

## 目标一句话

把「材料合成分类下的月限物品」合成到数量顶格并确认——做完后合成页上该物品数量已合成,弹窗已关闭,停在合成页。

## 起点 / 结束画面

- 起点:任意可控画面(op 自带回大世界 → 菜单 → 合成的导航);
- 结束:合成页(数量节点返回 `QUOTA_EXHAUSTED` 时停在合成页、不点合成)。

## 现状与改动面

`Synthesize`(src/sr_od/operations/synthesize/synthesize.py)既有节点链:
画面识别 → 开始前返回 → 打开菜单 → 选择合成 → 选择合成类别 → 选择合成物品 → 选择数量 → 点击合成 → 点击确认 → 点击空白处关闭。

本次改动(零食路径字节级不动):

1. `SynthesizeItem` 增加字段 `quantity_mode: str = 'max_btn'`;`SynthesizeItemEnum` 新增 `SELF_MODELING_RESIN = SynthesizeItem('材料合成', '自塑尘脂', 'self_modeling_resin', quantity_mode='plus_monthly')`。
2. 「选择数量」节点按 `quantity_mode` 分流:
   - `max_btn`(默认,零食):原逻辑不动;
   - `plus_monthly`(新):月限拉满策略,见下。
3. 新增终止节点「额度已用完」,接 `选择数量` 的 `QUOTA_EXHAUSTED` 精确状态边(该状态必须显式接走——不带 status 的兜底边会在无精确边命中时接管,把「跳过合成」误送去点合成)。
4. 「点击合成」增加 `QTY_MAXED` 精确状态边(默认无状态边继续兜底零食路径)。

## plus_monthly 策略流转(单节点内轮询,`node_max_retry_times=30`)

每轮(基于最近截图):

1. `[读 合成所需材料不足,不流转]` → 命中 = `round_fail`(用户裁定 2:材料不足是失败,不标完成,一条龙后续补跑);
2. `[读 按钮-数量增加(亮态模板),不流转]` → 命中 = 点其中心(等价点 +),`round_retry` 进入下一轮;
3. 亮态未命中 → `[读 按钮-数量增加-置灰(灰态模板),不流转]` → 命中:
   - 本轮已点过至少一次 + → `round_success('QTY_MAXED')`(拉满完成,去点合成);
   - 一轮都没点过(入口即置灰,歧义态)→ 读额度消歧:
     - `[读 读区-本月还可合成,不流转]` → N=0 → `round_success('QUOTA_EXHAUSTED')`(无事可做,预期内完成);
     - N≥1 → 视为「已被材料/规则约束到顶」→ `round_success('QTY_MAXED')`(合成当前已设数量,拉满语义自洽);
     - 读不出 → `round_fail('额度文本不可读')`(不冒险)。
4. 两态都不命中 → `round_fail('数量按钮不可识别')`。

重试预算:`node_max_retry_times=30`(月限额度个位数,30 次覆盖充分;耗尽转 fail 走失败收尾)。

## 红线

- 本 op 消耗真实材料(遗器残骸 800/个)与月限额度——`QUOTA_EXHAUSTED` 分支**绝不点合成**;
- `按钮-最大值` 零尺寸点区域对滑条 UI 是误点源,plus 路径禁止触达。

## 建档依赖(已落 screen_info)

- `分类-材料合成` [880,40,950,85] 纯定位;
- `按钮-数量增加` / `按钮-数量增加-置灰` [1490,845,1640,895] 模板(quantity_plus / quantity_plus_max,阈值 0.7;**区域限制是硬前提**:全图裸匹配亮态模板会以 0.877 误命中形近的「−」按钮);
- `读区-本月还可合成` [1050,525,1340,560] OCR;
- 模板资产 `assets/template/synthesize/{self_modeling_resin,quantity_plus,quantity_plus_max}/raw.png`(来源截图交叉验证 1.000 / ≤0.2)。

## 放置位置建议

op 本体在项目顶层 `operations/synthesize/`(跨 app 复用:零食 CustomCombineOp 指令与本 app 共用),改动原地扩展,不新建 op。
