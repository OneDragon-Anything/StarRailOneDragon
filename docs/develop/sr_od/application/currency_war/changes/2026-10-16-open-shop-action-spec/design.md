# open-shop-action-spec 迭代设计（总纲）

## 0. 元信息
- 迭代目标：开店动作 op 按 `flow/action_ops.md` 规范重组（机械执行 + 发出即记账恒 True，禁验证/重试/判断），复盘报告中开店回执不再出现 `applied=否` 误显。渲染器零改动（回执 actor 字符串 `'CwOpOpenShop'` 维持，词表解耦存活）。
- 状态：定稿（首轮两攻击面发现全部处置 + 终审通过，7 条一行级残留随定稿同笔修；2026-10-16）
- 文档清单：无详设（单文档方案，本文件 §2 即完整设计）
- 对抗报告：[attack.md](attack.md)（两攻击面 17 项发现全部处置，含真引擎复现证据）
- 规范依据 = 用户裁定原文（`flow/action_ops.md`）：
  - 「动作 op 是机械执行——只负责把一个动作发出去（点击/拖拽）+ 如实上报动作事实。**禁止做验证，禁止做重试。任何需要验证或需要重试的地方，一律是 bug。**」
  - 「选择动作执行就一定按成功处理——动作 op 点完就立即上报，按成功把结果写进 game state。」
  - 「基类契约恒 True；机械不能发出（定位缺失/无空槽）才以 `emitted=False` 申报未发出事实。」

## 1. 问题与动机

- **归层**：约定层（在册豁免形态与 2026-09-21 后裁定冲突——2026-09-18 动作 op 重组批映射表明列豁免「不调(不可达)」、拆验证批 73aff315f 明示保留幂等观察、T-45/T-17 两轮审查选「登记」非「重组」）+ 流程层（规范清点作用域盲区：`action_ops.md` §3 偏离清单核查面只扫 §4 注册表动作 op，§4.7 组合壳/直调体从不在任何一轮清点范围——本迭代在正本清单中把核查面扩展列为收尾义务）。
- **违规面**（`operations/cw_op/cw_op_open_shop.py`，代码锚已两攻击方独立核验）：
  1. observe + act 两节点形态（规范 = 单节点动作 op）；
  2. act 节点「落地复查」（重入帧商店锚再判）= 验证——明文禁止；
  3. `round_retry('开商店点击已发,重入观察裁决', wait=1)` 循环 = 重试——明文禁止；
  4. 幂等出口发 `applied=false`（「商店已开(幂等入口观察,无动作可发)」）= 动作 op 内做判断（幂等归流程层，§2.3）。
- **症状与真实机理**（依据 = `cw_sim_backend.py:1006-1016` + `cw_sim_ports.py:219-241` 屏门段，攻击方真引擎复现）：sim 机械 IO 关闭是全局策略，但 sim 的 `round_by_find_and_click_area` **已被端口覆写为零图像锚形态**——点击经端口 `click_answer` 感知 = 开店的世界推进通道（sim-design §3.2 转移源 2：`_handle_click_source('货币战争-备战','按钮-商店')` → `_open_shop()` 呈现 + 离屏牌面补写 + 刷价写回，「不开店不写」）。点击受理转移后，mirror 按**点击前档名**问询屏门 → round_retry → `is_success=False`——现行代码把它误读为「未发出」→ 回执 `applied=false · reason=找不到商店/收起按钮` → 渲染 ⚠。业务事实 = 店已开（发牌入账），回执与事实相反。

## 2. 方案（单文档完整设计）

### 2.1 直调体 `open_shop` 规范重组（生产路径，`_open_shop_phase` 调用）

```python
def open_shop(op: SrOperation) -> OperationRoundResult:
    # 动作 op 规范(action_ops.md 裁定原文):机械执行 + 发出即记账,禁验证/重试。
    clicked = op.round_by_find_and_click_area(
        op.screenshot(), '货币战争-备战', '按钮-商店').is_success
    if cw_sim_ports.mechanical_io_allowed():
        # 实机:is_success = 发出事实。False = 定位缺失(唯一合法 applied=false
        # 出口,emitted=False 申报未发出)。
        if not clicked:
            _note_receipt(op, False, '定位缺失(按钮-商店)')
            return op.round_fail('定位缺失(按钮-商店)')
        op.park_cursor()
        time.sleep(SHOP_OPEN_ANIM_S)
    else:
        # sim:点击经端口 click_answer 感知 = 世界推进通道(sim-design §3.2
        # 转移源 2:_handle_click_source → _open_shop 呈现 + 离屏牌面补写 +
        # 刷价写回);屏门按点击前档名问询的 retry 是转移后可见性语义,不作
        # 发出判读——点击已受理即已发出,applied=true 名副其实。
        pass
    _note_receipt(op, True, '')
    return op.round_success('开商店已发')
```

- **删除面**：幂等入口观察（「按钮-收起」锚判断）、act 落地复查、`round_retry` 环——幂等判定归流程层（`visit_open_shop` 入口观察 + 外循环 0n 三锚已承载，`cw_screen_prep.py:1073-1081` 明文「已开连点都不发」不依赖 open_shop 幂等性）。
- **点击分支保留的架构理由**：sim 下这条调用是开店的唯一世界推进通道（呈现 + 离屏牌面补写 + 刷价写回全部由它触发）；同时它就是 sim 的「机械对偶」——发出 = click_answer 受理，`applied=true` 与 note_action_receipt 契约（「是否发出的机械事实透传」）**零冲突，字段语义零改动**。
- **上报面申报**：①唯一上报口 = `note_action_receipt`（回执域机制）；②`report_action_open_shop_param` 不调（zero_writes.py:103 零写族登记成员，开店无状态写效果）；③开店非 §4.8 十八转移集成员（转移由 §3.2 点击源承载）→ 无 WorldDecl 喂入行。
- 回执 op 名/actor 维持 `'CwOpOpenShop'`（`_note_receipt` 硬编码，journal 词表稳定）。

### 2.2 类壳 `CwOpOpenShop` 解散

- 消费面核察结论（两攻击方独立确认）：类零外部消费（注册表走 `CwActionOpenShopOp` 终端承载行 `cw_action_registry.py:191`；流程走直调；渲染器消费的回执 actor 字符串与类删除解耦）。
- 处置 = **解散而非迁改**（迁改 = 留双源）：删 `CwOpOpenShop` 类 + `CwOpOpenShopObs`（`kernel/cw_screen_report/open_shop.py`，纯数据类无 report 接口，删之无容器/上报面空洞，随类壳同删）。
- 测试迁改面（仅两处）：`test_screen_report_ports.py:58+71` 两张名单删 `'open_shop'` 与 `'CwOpOpenShopObs'` 条目；`test_action_registry.py`/`test_launch.py`/`test_sim_smoke_batch.py` 零迁移。
- `cw_op_settle_confirm.py:6` docstring「惯例 CwOpOpenShop」引语改指规范形态。

### 2.3 流程层承接核察

- `_open_shop_phase`（`cw_screen_prep.py:1002`）逐位不变：`open_shop(self)`（结果弃置，用户裁定 2026-09-10「调用方不问成败」）→ `visit_open_shop()`（入口观察 = 已开判定承载位）。
- **现役防重入三件**（引用修正，原 bridge.py:76-82 引证失效）：外循环 0n 三锚路由（`cw_loop.py:453`）+ `shop_handled` 会话标记（session_scope）+ 段旗 `cw4_launch_spend_visited`；前置动作发出点不经 S1 标志与节流（S1 已删，`mandate_state.py:20`，shop_handled 承接防活锁）。
- **行为差申报**：实机下「店已开后再显式开店」从「幂等成功」变「定位缺失 false」，回执 reason 从「商店已开(幂等入口观察)」变「定位缺失(按钮-商店)」——对复盘者可读性略退化（换得动作 op 合规）；措辞在实机 fixture 验收时定稿。失败面语义修正：visit 入口观察对空牌面是容忍降级（`cw_screen_shop.py:503-505`「离屏语义关断」），真实失败面 = 决策核 ValueError 异常（0n 路径经 `_FnResult` 计入 outcome，显式路径仅日志）。

### 2.4 同族清单（裁定落地后的清点机制缺口——同根，分账处置）

| 成员 | 违规形状 | 处置归属 |
|---|---|---|
| `cw_close_shop_action.py:89-94` | 「按钮-收起」miss → applied=false + reason 做业务推断（「商店已关(幂等入口观察)」）——与开店旧幂等同锚同构 | **本批对账**：reason 改定位缺失语义（其 miss 实为「点击目标获取失败 = 定位缺失」合法出口），去业务推断；同函数 :93 round_success status 文案与 :77-78 docstring 同为业务推断，同批一并改 |
| `cw_pick_partner_action.py:76-82/101` | 确认点未找到 → round_retry + 重入裁决 | 在册待修（§4.5/§2.3 已登记），引用不混本批 |
| `operations/cw_screen/_overlay_confirm.py` | §2.3 在册待修问题本体 | 在册待修 |
| `cw_start_battle_action.py:108-184` | 执行后单帧弹窗识别 | §1 现役违例清单在册 |

流程级修正（本迭代收尾义务）：`action_ops.md` §3 偏离清单核查面从「§4 注册表动作 op 全量」扩展至「§4.7 组合壳/直调体」——本次四家同根的教训（§1 归层）。

### 2.5 原「谜团」定性修正（实现期验收项，非阻塞拆账）

半修形态（仅改回执、删点击）实测 `decide_shop_action` 抛「容器商店 payload 离屏(shop=None)」——两攻击方独立定性：**即 §2.1 旧 sim 分支自身缺陷**（点击源断裂 → 呈现/离屏补写无触发器），非独立缺陷。嫌疑面①（回执消费——全仓无 applied 消费点）③（动画帧节拍——sim 等待参数透传丢弃）已排除。本迭代 §2.1 新形态保留点击源，该症状随之消失；验收判据含「离屏零抛」。**回退门（单支）**：若新形态落地后驱动仍不收口或离屏仍抛（修不透）→ 本迭代整体回退收场，不留半解机制。

## 3. 关键取舍

- **sim 保留点击**：它既是 sim 的机械对偶（发出 = click_answer 受理），又是开店呈现/发牌补写的唯一触发器——拆掉即确定性死局（真引擎复现）。发出判读语义按渠道拆分（实机 is_success / sim 点击受理），字段契约零改动。
- **applied 字段保留**：「动作是否发出」事实位（防意图蒸发），修的是违规 op 与 sim 归因，不是字段。
- **类壳解散而非迁改**：零消费面，迁改 = 双源漂移。
- **幂等判断出清到流程层**：动作 op 规范禁判断；流程层两道承载（显式开店路径 visit 入口观察 + 0n 转交路径）。
- **同族四家分账**：CloseShop 本批对账（同锚同构最小修）；余三家在册待修引用——逐件补丁不做，清点机制缺口走正本核查面扩展。
