# application-flow:每月合成 app(monthly_synthesize)

## 四段落成 op 序列

| 段 | 节点 | 内容 |
|---|---|---|
| ① 导航段 | `合成自塑尘脂`(start) | 开关关 → `round_success('SWITCH_OFF')`;开 → `Synthesize(SELF_MODELING_RESIN, num=0)`(op 内部自带回大世界→菜单→合成导航) |
| ② 玩法段 | (并入①,合成确认/关闭在 op 内闭环) | — |
| ③ 领奖段 | 无 | — |
| ④ 返回段 | `返回大世界` | `BackToNormalWorldPlus`,一条龙在大世界干净交接 |
| 失败收尾 | `失败收尾` | `BackToNormalWorldPlus` 尽力回大世界后 `round_fail`(带原始语境) |

## 分支处理(合成自塑尘脂节点的出边)

`Synthesize.execute()` 结果分支:

| 结果 | 出边去向 | app 语义 |
|---|---|---|
| success(默认状态,合成完成) | → 返回大世界(置当月锚) | 正常完成 |
| success(`QTY_MAXED` 透传,合成完成) | → 返回大世界(置当月锚) | 正常完成 |
| success(`QUOTA_EXHAUSTED` 透传,未合成) | → 返回大世界(置当月锚) | 预期内无事可做(本月额度已用完),照常标完成 |
| success(`ITEM_ABSENT_FIRST_SCREEN`,首屏未见) + 当月锚已置 | → 返回大世界 | 额度用尽(物品沉底),标完成 |
| success(`ITEM_ABSENT_FIRST_SCREEN`,首屏未见) + 当月锚未置 | → 失败收尾 | 材料不足或额度被人手用尽,**不标完成**(用户裁定 2) |
| fail(材料不足/识别失败/导航失败等) | → 失败收尾 | **不标完成**(用户裁定 2),一条龙下个周期(日批)重跑补做 |

`返回大世界` 失败 → 直接 `round_fail`(不做二次收尾,同 monthly_embers_exchange 口径)。

**当月锚**(`resin_quota_confirmed`,运行记录字段):成功合成或读到额度 0 时置位,当月不回退,自然月翻转清零——「首屏未见」的成因只能靠它区分(物品沉底后额度文本不可达)。已知边界:额度被人手提前用尽且当月 app 从未成功过 → 锚未置 → 日批失败噪音到月底,下月自愈。

## 失败处理语义

- 入口导航失败(合成 op 内部失败)= 中止档 → 失败收尾节点尽力回大世界,带原始语境 fail;
- 无「单点重试后跳过」档:当前唯一子项,跳过即空跑;
- 失败明细走通知文本(status 即语境),运行记录不设业务字段(用户裁定 1:不关注具体个数)。

## run_record 处理方式

- `MonthlySynthesizeRunRecord`:周期 **MONTHLY**(自然月刷新,与兑换商店月限口径一致;依据:画面文案「本月还可合成」+ 沉底排序律随额度刷新,跨月复位待跑过一个完整月界复核);
- 周期标记:app success(含 QTY_MAXED / QUOTA_EXHAUSTED / 首屏未见且已锚 / SWITCH_OFF)= 标「本月已完成」,月内一条龙跳过;app fail = 不标,日批重跑补做;
- 业务字段:`resin_quota_confirmed`(当月额度耗尽锚,见分支表)——数量数值不留痕(用户裁定 1:不关注具体个数);自然月翻转 reset_record 全清;
- SWITCH_OFF 同样标本月完成(与余烬兑换全关口径一致):已知代价是月内途开开关要靠手动单跑,接受。

## config 处理方式

- `MonthlySynthesizeConfig(ApplicationConfig)`:`synthesize_resin_enabled: bool` 默认 True(用户裁定 3),默认值补进内存 data(同 monthly_embers_exchange,防 MCP get_config 读 null);
- 读取点:仅 `合成自塑尘脂` 节点入口;False → 跳过合成(月度职责视为已履行);
- 未来新增月限物品:const 加标识符 + config 加 `{item}_enabled` 开关 + 编排节点按序扩展。

## 中断恢复

不做(流程短、全程 <1 分钟,从主界面重跑成本低;导航段自带回大世界,任意状态可安全重入)。
