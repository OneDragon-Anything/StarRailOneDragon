# 设计对抗报告（首轮）

> 攻击方：核一无前提+实现者试读+真引擎复现（补丁打进去复现死局，工件 .debug/temp/repro_*）、核二+三规范遵循+治本（全文+git 史核）。状态：全部发现已处置。

## A. 定稿门槛项

| # | 发现 | 处置 |
|---|---|---|
| A1 | **【致命】§2.1 sim 分支拆断开店喂入通道**（两攻击方独立结论）：sim as-built 里 `round_by_find_and_click_area` 不是机械腿，是开店唯一世界推进通道（sim-design §3.2 转移源 2：click_answer → `SimBackend._open_shop` 呈现+离屏牌面补写+刷价写回，「不开店不写」`cw_sim_backend.py:1035/1095-1119`）。删点击 = 商店永不呈现 → 二次进店 `shop=None` → mandate 在屏前置抛离屏——核一按 §2.1 原样打补丁真引擎复现（同 seed 死局，异常栈存档） | 已重写：**sim 保留点击**（发出 = click_answer 受理，applied=true 名副其实，note_action_receipt 契约零改动）；实机才读 `is_success` 走定位缺失出口（唯一 false） |
| A2 | **§1 症状机理错误**：「sim 图像锚必 miss」不成立——sim 无图像锚（round_by_find_* 已被端口覆写 `cw_operation_base.py:87-165`）；真实机理 = click_answer 受理转移后 mirror 按点击前档名问询屏门 → round_retry → `is_success=False` 被现行代码误读为「未发出」（`cw_sim_backend.py:1006-1016` + `cw_sim_ports.py:219-241`） | 已重写：§1 按真实机理 + §2.1 发出判定改 sim 生效语义（点击后画面切走 = 已发出；屏门 retry 且画面未切才是定位缺失） |
| A3 | **§2.4 谜团定性错误**：非独立缺陷——三嫌疑面裁定：①回执内容消费面排除（全仓无 applied 消费点）；③动画帧节拍排除（sim 等待参数透传丢弃）；②发牌-清场定性修正——真根因 = A1 点击源断裂（关店清 payload 后再进店无点击 → 无离屏补写 → 在屏前置炸） | 已改判：谜团 = §2.1 自身缺陷，本迭代内修透（A1 修法即解），无拆账支；回退门改单支（修不透整体回退） |

## B. 设计文本/引用修正

| # | 发现 | 处置 |
|---|---|---|
| B1 | `_note_receipt(op, True)` 缺必填 reason 参数 = TypeError（22:44 四连死与此吻合，journal 零回执行佐证） | 已修：新形态调用补 `''` |
| B2 | §2.3 可达性引证失效：bridge.py:76-82 原文恰相反（前置发出点**不经** S1 标志与节流；防护 = 段旗 `cw4_launch_spend_visited`）；S1 开店标志已删除（mandate_state.py:20，shop_handled 会话标记承接）；现役防重入 = 0n 三锚路由 + shop_handled + 段旗 | 已重写 §2.3：改引三件现役防线 + 异常失败面（visit 入口观察对空牌面容忍降级，真实失败面 = 决策核 ValueError） |
| B3 | 「node 1-2 起」与数据不符（四连死全死 P1r1；复现局死 P1r6） | 已修 |
| B4 | landing 判据不可机检：`terminal=death\|game_over`——drive 枚举 = abandoned\|death\|p3_enter，game_over 不存在 | 已修：`death\|p3_enter`；fixture 判据移至 A1 修法落地后 |
| B5 | 测试引用面修正：需迁改仅 `test_screen_report_ports.py:58+71` 两张名单；test_action_registry/test_launch/test_sim_smoke_batch 零迁移 | 已修 landing 文件面 |

## C. 规范遵循（核二+三 S2-S8 + 附带）

| # | 发现 | 处置 |
|---|---|---|
| S2 | §1 机理错误且无依据标注 | 并入 A2；依据标注补（cw_sim_backend.py:1006-1016 + cw_sim_ports.py:219-241） |
| S3 | 正本清单漏 `screens/op-layer.md`（:85 惯例句 / :98 画面 op 计数 35→34 / :107 分型总表画面框行 + §1.1 例外③宿主清单——重组后「判断动作是否已做过」用途消亡，例外语义须改写） | 已修：landing 3.2 补 op-layer 三处 + screens/shop.md 核对 |
| S4 | 新形态上报面未对照规范件申报：`report_action_open_shop_param`（zero_writes.py:103 零写族）不调须申报理由；非转移动作（§4.8 十八集外）无 WorldDecl 喂入义务须申报判定依据；note_action_receipt 与上报通道表关系未说明 | 已修：§2.1 增上报面申报三行 |
| S5 | 同族未普查：CloseShop 幂等出口（同锚同构业务推断）、PickPartner 重入裁决、_overlay_confirm、StartBattle 单帧弹窗识别——四家同根 =「裁定落地后的清点机制缺口」 | 已修：§2.5 同族清单（成员/处置归属/依据）：CloseShop 本批对账（reason 去业务推断改定位缺失语义）；余三家引用在册待修账（T-45/T-17 系登记），不混本批 |
| S6 | bridge.py:76-82 引证失准 | 并入 B2 |
| S7 | 「M1③」会话局部标识符 | 已删，改语义描述；代码 docstring 内 M1③ 随本迭代顺手清 |
| S8 | §1 缺根因归层行 | 已补：归层 = 约定层（在册豁免形态与 2026-09-21 后裁定冲突）+ 流程层（规范清点作用域盲区） |
| 附 | action_ops.md:40 悬空指针（cw_screen_op_base.py 已不存在，裁定原文现住 op-layer.md §1.2:49） | 已修：正本清单补指针另修 |

## D. 治本核验（逐问）

| # | 结论 | 处置 |
|---|---|---|
| Q1 | 归层修正：非「漏迁」——2026-09-18 重组批映射表明列豁免（「不调(不可达)」）+ 拆验证批（73aff315f）明示保留幂等观察 + T-45/T-17 两轮登记选「登记」非「重组」。真流程缺陷 = action_ops.md §3 偏离清单核查面只扫 §4 注册表 op，§4.7 组合壳/直调体从不在清点范围 | 已修：§1 归层改写 + 流程教训写入；正本清单补 action_ops.md §3 核查面扩展 ← 3.2 |
| Q2 | 同族四家（见 S5）；跨件半问：四家同根 = 清点机制缺口，升级为 Q1 流程级修正 | 已修（S5 + Q1） |
| Q3 | §2.4 处置错序：谜团与本病同根（A1），「拆账另立」预设不成立；通道语义先定案，重组随之，谜团本迭代内修透 | 已修（A3） |
| Q4 | applied 语义：原 §2.1（sim 零机械发出却恒 True）与 note_action_receipt 契约（机械事实透传）不兼容且未申报修订；**保留 sim 点击后两者同时满足，矛盾消解，契约零改动**——唯一自洽路径 | 已采用（A1） |
| Q5 | CwOpOpenShopObs 删除无容器/上报面空洞（纯数据无 report）；独立可跑壳零消费无需补位；渲染器词表字符串 `'CwOpOpenShop': '开店'` 与类删除解耦（回执 actor 名维持） | 已修（S3 + landing） |

## E. 已核无发现面（两攻击方交叉确认）

违规面四条代码锚逐一命中；幂等出清到流程层方向正确（visit_open_shop docstring「不调 open_shop…已开连点都不发」明文承载）；落地文档结构七件齐；回退门机制合规；类壳零外部消费（渲染器词表字符串解耦存活）；测试引用面仅两张名单需迁改；§1 症状引用逐字成立。
