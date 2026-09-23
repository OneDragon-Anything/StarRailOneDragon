# 选择伙伴(partner · 货币战争-列车同行)

> 代码 = `operations/cw_screen/cw_screen_partner.py::CwScreenPartner`(两 node 直继承 `SrOperation`;画面档 screen_name = 货币战争-列车同行)。职责:选择伙伴 overlay 一次访问——OCR 候选阵营标签 + SIFT 立绘识别真身 → `decide_partner` 选 → 「点选候选 → 确认」脉冲链 → 标识消失 = 完成门。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_partner.yml`。

## 1. 分发判定

- 阶段一身份分发(号制已退役):id_mark 锚「货币战争-列车同行.标识-选择伙伴」(位置约束 area;全屏 LCS 判据已退役——「选择伙伴」与「请选择投资策略」共享「选择」子序列会误匹配)。
- 与装备选屏的历史碰撞(共享「请选择1个」副题位)由本屏整行副题锚消解,单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口门(「标识-选择伙伴」,miss = round_fail 交回外循环重判)→ 候选一次读 → `report_screen_partner_obs` 落容器 `partner_opts` 槽 → obs + 候选坐标挂实例属性。决策动作 node = 顶部重入裁决(确认 pending:标识不在 = overlay 关 = 链完结 → success;标识在 = 重走脉冲)→ 零参决策 `match.strategy.decide_partner()`(候选自容器槽;缺省实现优先 `config.character_build_around`/`target.core_chars` 命中,否则 idx=0,规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E6);决策出口守卫:候选空 = 具名 round_fail 零盲发(「伙伴屏无候选」在册文案上移至决策前)、返回 None/词表外 = 具名 round_fail(含原值)、idx 越界 = 守卫断言 AssertionError 禁钳位(出口③/§1.3;均在派发前零点击);无 match 局外不设早退支(用户裁决 2026-09-22 全族删门)→ 「点选候选 → 确认」脉冲链经 `CwActionPickPartnerOp` 派发(机械链+自上报在动作 op 内,pick-op-unify 批;确认点读缺旁路不上报)→ `round_wait` 循环(无防御上限;`node_max_retry_times=10` 现役值仅框架异常路径消费,有界防线 = CONFIRM_REJECT_MAX,见 §8)。chosen_partner 留守选择点,不进 report。

## 3. 观察面

观察 node = 入口门(「标识-选择伙伴」)+ 候选一次读(每访问恰一次,决策轮复用实例载体);候选与选中态读取:

- 候选 `_read_candidates`:OCR 候选阵营标签(label 行 y 带 = `CwScreenPartner.LABEL_CY_LO/HI`、x 带 = `LABEL_CX_LO/HI`(数值单一源在代码;识别几何现役走代码内矩形先例 = fields.md §3.4.5,标签行 / 立绘裁剪框 area 化补档候批)——**必须滤 x**:左侧备战面板阵营 label 同 y 会混入;2-4 字 + 排除表),按 center-x 左→右排序;
- 立绘真身 `_identify_portraits`:SIFT 立绘识别(label 上方立绘区 vs `portrait_plaza` 模板库,`obs/currency_war_char_id.py::identify_character`;裁剪框 = `_identify_portraits` 类内几何,数值单一源在代码,同先例申报)→ 每候选 char_id(识别失败回落 label 流派名)——真身识别让 `decide_partner` 的 core_chars 匹配真正生效;
- 转换成功性边界(op-layer.md §1.1 :34「屏契约登记」义务):`char_id` = SIFT 真身识别产物,**识别失败回落 label 流派名/空 = 转换失败欠账形态**(:34 要求任一候选转换失败 = 观察失败 round_fail 早退、零写零上报;现役回落为既有语义,无新增未标准化直报面),收敛方向 = 观察失败 round_fail 零写零上报;多候选命中同一注册名(选项互斥屏)= 同判转换失败;
- 未选中态正判定 `_unselected_hint_present`:建档「提示-请选择强化角色」区域命中(确认钮置灰态伴随文案,区域约束 OCR 无全屏 LCS 误匹配面)。选中态呈现零实拍,**选中与否不作读数判定**(推进语义由脉冲 + 完成门承载)。

观察 payload = `CwScreenPartnerObs`(`on_screen`/`options`(PartnerOption idx+char_id)/`screen`,住 `kernel/cw_screen_report/partner.py`);report = `report_screen_partner_obs` 候选写容器 `partner_opts` 槽(空候选不写,闸在 report 内;match/gs 缺席的局外路径跳过 report——report 跳写 = 容器写闸,与决策无关;无 match 局外不设早退支,用户裁决 2026-09-22 全族删门,见 §2)。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionPickPartnerOp`(`CwActionPickPartnerParam`) | 注册表工厂 `action_op_for`(决策半组装 `OverlayPickExecEnv`:未选中实证 `unselected`;点卡点/确认点经 `env.op` 消费决策半缓存,点选脉冲与确认脉冲均在动作 op 内,确认点 op 类体内经「货币战争-列车同行.按钮-确认选择」rect 约束 OCR 现读) | 自上报 `report_action_pick_partner_param`(零写族单相:确认点击发出后即按完整结果上报回执,容器零写、真值归观察覆盖;确认点读缺 retry 旁路未发确认点击,不上报) | 否(非终结):发出后 `round_wait` 循环推进;落地由重入裁决判——「标识-选择伙伴」不在 = overlay 关 = `round_success` 交回外循环(见 §5) |

脉冲链(每轮一脉冲;确认被拒守卫/零参决策/chosen 写端留守决策动作 node,「点选候选 → 确认」脉冲 + 自上报零写整体经动作工厂 `cw_pick_partner_action.py::CwActionPickPartnerOp`,派发 param 携真实选中 idx):

```
1. 未选中提示在场 ∧ 脉冲计数 ≥ CONFIRM_REJECT_MAX(4) → 显式 round_fail
   (确认被拒形态有界重试:未选中提示持续在场 = 确认钮置灰被游戏拒,
    先于无界循环给出精确失败原因)
2. 守卫先行(候选空 / 返回词表外·None = round_fail;越界 =
   AssertionError——均先于决策与写端零点击;无 match 局外不设早退支,
   用户裁决 2026-09-22 全族删门)→ 首轮决策一次
   (缓存同一点位防跨轮决策抖动换候选):
   candidates → SIFT char_ids → decide_partner()(零参,候选读容器
   partner_opts 槽)→ _pick_point(x = 候选 label 中心,y = 「候选-卡区」
   建档带中心)→ GameState chosen_partner write_logic(选择点直写)
3. 建档缺失(候选-卡区不在)= round_fail(坐标单一真相源,禁裸坐标兜底)
4. 提示在场(含重入轮)∨ 首轮 → 点候选卡(单选语义重点已选卡无反选面;
   提示不在 = 不重点选,防未知选中呈现被扰动)→ 0.7s
5. 点确认(mouse_move 防吞点击 + click;定位 = 「按钮-确认选择」rect 约束
   OCR → 全屏 OCR 兜底)→ 未找到 = round_retry → 找到 = 点 + 1.0s
   → 脉冲 +1 → 置确认 pending → round_wait(落地归重入裁决)
```

交互陷阱(机制更正注,screen doc 同源):旧「选中态 gate」(全屏 OCR 找「已选择」)与本屏常驻文案共享子序列恒误命中 → 恒跳过点选、对置灰确认钮原样重试;现形态废除选中态读数,改「点选 → 确认」脉冲 + overlay 关闭完成门。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 重入裁决标识不在(overlay 关) | **画面终结** | round_success 交回外循环重分发 |
| 确认被拒(未选中提示持续在场达上限) | op FAIL | 显式失败交外环重判 |
| 入口锚 miss | op FAIL | 交回外循环重分发 |
| 决策出口守卫(候选空/返回词表外·None/idx 越界) | 守卫 fail(op FAIL) | round_fail(含原值,直落零预算)/ 框架异常路径(留证截图 + node_max_retry_times=10 预算耗尽,守卫③)交回外循环;连续 fail 由外环 fail 重派网兜底(cw_loop.py::CwLoop) |
| 局外无 match | 不设早退支(op-layer.md §1.1;用户裁决 2026-09-22 全族删门) | 未支持用法:单跑缺上下文沿正常链路自然失败,局内不达此态 |

「确认离开 = 画面终结」= [README.md](README.md) §6;`node_max_retry_times=10` 现役值仅框架异常路径消费,循环推进 = `round_wait`,有界防线 = CONFIRM_REJECT_MAX。

## 6. 状态上报面

- 候选观察:`report_screen_partner_obs` 候选写容器 `partner_opts` 槽(空候选不写)。
- `chosen_partner` write_logic(**选择点**直写、确认前 = 判定点二元之选择点(fields.md §3.4 导语在册);写点 → 点选→确认窗口内无流程读者,确认未落地 = 重入裁决不写成功 + CONFIRM_REJECT_MAX 显式失败出口 + 外环重派重写,无幻影成功消费面;gs 单一源,session 域无此写端;单次逻辑写入豁免;值 = 选中候选 `char_id`,值语义随 §3 观察面 char_id——识别失败回落流派名/空 = :34 转换失败欠账形态)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5 / §4「事件选择」。

## 7. 子态与 overlay

本屏无子态。左侧备战面板透出(候选 y 行的 board 阵营 label)= 本屏观察面的过滤对象(非可交互面)。

## 8. 守卫与防线

- `CONFIRM_REJECT_MAX=4` 确认被拒防线(置灰确认被游戏拒的形态显式失败,禁原样无限重试)。
- 决策输入守卫:候选空 = 具名 round_fail 零盲发(无候选在册文案保留;原「常量 idx0 盲选派发」退役)。无 match 局外不设早退支(op-layer.md §1.1;用户裁决 2026-09-22 全族删门)。
- 返回契约与值域守卫:返回 None/词表外 = 具名 round_fail;pick idx 越界 = 守卫断言 AssertionError(原「静默钳 0」退役)。
- 候选选中几何:y 由「候选-卡区」建档带中心锚定(布局漂移可经建档对账暴露;禁裸坐标兜底)。
- 决策单次缓存(`_pick_point`)防重入轮决策抖动换候选。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「选择伙伴」;op 内日志 tag = `[cw-partner]`(candidates/pick/点选点/确认被拒)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(节点循环族两 node 形态锁:观察上报容器/入口门 miss fail/容器零参决策 + round_wait;决策出口守卫两锁——伙伴臂输入守卫锁:候选空 fail / 局外无早退支自然失败两臂分开断言,返回契约+值域锁)、test_cw_partner_select_confirm_flow.py(选选流序 + 确认被拒有界重试锁;桩面 = cw_match 桩,decide_partner 恒 idx=0——守卫面锁归 two_node_family 伙伴臂,选选流序断言面不变)。
- game 侧知识:画面与交互更正 = [../../../../game/screens/currency_war_choose_partner.md](../../../../../game/screens/currency_war_choose_partner.md)。
