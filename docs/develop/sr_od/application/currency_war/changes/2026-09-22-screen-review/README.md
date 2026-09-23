# 2026-09-22-screen-review(货币战争全画面规范符合性审查·只设计不落码)

> 任务账本 = `.debug/progress/2026-09-22-cw-screen-review/dag.jsonl`(36 个画面审查任务 T-1..T-36 + 汇总 T-37)。
> 审查产出 = 账本目录 `reports/`(每屏一份规范符合性审查报告);有问题屏的修法设计稿 = 本目录逐屏一文件;设计稿经无前提对抗循环(攻击收敛或触 4 轮上限)后**停在「待用户裁决」**——用户逐屏认同后才立落地批,未认同不派任何落码。

## 迭代终态(2026-09-22 收口)
- 36 屏规范审查全部完成:已实施 3(T-5/T-6/T-7,均过验收)/合规免修 2(T-29/T-36)/对抗触顶待裁决 8/对抗收敛待裁决 23;未认同稿面前无任何进一步落码。
- 新规范重审(op-layer.md §1.1 :34 观察标准化门 / :36 禁局外单跑,commit 2f35d4011):需增补 10 屏(T-9..T-16、T-20、T-25),增补节定点对抗全部收敛闭合;推进型 11 屏(T-26..T-36)零增补。
- 落地进展:T-5 = 40674f698、T-6 = b0ebf16a4/4dca49483/c11fb00b6(测试仓 73afa15e)、T-7 = f41c40250(观察标准化门首个落地先例);其余 31 屏修法停在设计稿,待用户逐屏裁决后立落地批。
- 汇总产物:晨报 = 账本 `reports/T-37-晨报.md`(36 屏总表、18 项跨稿裁决清单、登记行主题汇总、6 项缺口核查);登记行全集底册 = `reports/T-37-inputs.md`。

## 文档
- 设计稿:`<snake>.md`(仅审查有问题的屏才产生;`§0 状态` 字段标注 草案/对抗收敛待裁决/对抗触顶待裁决/已实施/合规免修)

## 进度
- 审查:36/36 完成(明细 = `dag.py --file .debug/progress/2026-09-22-cw-screen-review/dag.jsonl list`)
- 设计对抗:全部闭合(收敛 23 + 触顶 8 + 合规免修 2 + 已实施 3;触顶稿残留均为低级文字项,处置建议见晨报 §5.1)
- 新规范重审:10 屏增补全部闭合(T-9..T-12 一组/T-13..T-16 一组/T-20+T-25 一组的定点对抗修订-复攻;最后一组 3 条一行级由编排侧机械验证收口)
- 落地:3 屏已实施并通过验收(T-5/T-6/T-7);其余待用户逐屏裁决后立落地批

## 边界(本次审查立什么、不立什么)
- 审查范围 = 每屏六面:**画面 op / 动作 op / 观察上报 / 动作上报 / game state 计算 / 文档**,对照正本:`screens/op-layer.md`、`screens/README.md`、`flow/action_ops.md`、`flow/action_exec.md`、`flow/README.md` §1(决策控制分层铁律)、`game_state/fields.md`、`game_state/logic-updates/`。
- 在册欠账(策划/装备两相上报、SwapDeploy 未接线、商店锁未建模等)不重复立项,只核对现状与在册描述一致;不一致才算新发现。
- 对抗循环上限 4 轮:不收敛即标注「对抗未收敛-待用户裁决」,不无限烧。
- 只设计不落码:所有修法(含文档修正)都停在设计稿;设计稿被用户认同前不改任何代码与正本文档。

## 逐屏状态
| 任务 | 屏 | 审查 | 设计稿 |
|---|---|---|---|
| T-1 | CwScreenPrep 备战 | 有问题(高0中9低8+死文件疑点2)·报告=reports/T-1-r1.md(合并) | **已实施**(prep.md 触顶定稿形态(残留3条随批清偿:R4-1跨稿承接声明+R4-2/R4-3);落地批 主仓46f04ed53(44文件+226/−973,两死文件删除+零穿戴哨兵退役+稳帧改固定等待)+测试仓5a9a6583,验收reports/T-1-acceptance.md **通过**(D1一行返工已清偿095223b3f;R11h分工确认成立;开放4低归T-37)) |
| T-2 | CwScreenBuyCards 商店开画面 | 有问题(高2中3低2)·报告=账本reports/T-2-r1.md | **已实施**(buy_cards.md 触顶定稿形态(残留1低纯登记随批清偿):F-1..F-7 全兑现(五槽锚定门/第三级兜底删/失败分形/计数现役化四站/BuyCard移出恒success);落地批 主仓cd17233ae+测试仓ddf0c16d,验收reports/T-2-acceptance.md **通过**(偏差3+开放2零阻塞:分流面现值8处归T-37/锚定门宿主漂移符号锚更新/mandate史注维持)) |
| T-3 | CwScreenBattleWait 战斗等待·结算 | 有问题(高0中3低3)·报告=账本reports/T-3-r1.md | **已实施**(battle_wait.md 触顶定稿形态(残留3低随批清偿);零行为注释卫生批 commit 9bfd51b6e(9文件:flow/README契约化+正本六节+设计稿随批入库),验收reports/T-3-acceptance.md **通过**(偏差2轻+开放5类零新增漏账;⚠️疑似真缺陷核实成立:predicates.py P1谓词读退役探针恒False→前窗武装静默失效+遥测失真,待裁缺陷候选)) |
| T-4 | CwScreenEncounter 遭遇 | 有问题(高1中3低1)·报告=账本reports/T-4-r1.md | **已实施**(encounter.md 触顶定稿形态(残留3低随批清偿);落地批 主仓fca7d9e9c+测试仓3ed96eba(守卫①②+直发+零容器写+F-2整篇改写+F-4自清),验收reports/T-4-acceptance.md **通过零返工**(偏差1低:_overlay_confirm分型注补给半边残余归T-37;开放3:§1.3遭遇条目收口确认/logic-updates README:61旧路径正本唯一残留/空靶正确)) |
| T-5 | CwScreenSupplyNode 补给 | 有问题(高0中3低4)·报告=账本reports/T-5-r1.md | **用户裁决通过,已实施**(supply_node.md;r1 7条→r2 4条→r3收敛;commit 40674f698,验收 reports/T-5-acceptance.md 偏差 0 条) |
| T-6 | CwScreenInvestStrategy 投资策略 | 有问题(高0中4低1)·报告=账本reports/T-6-r1.md | **已裁决已实施**(invest_strategy.md;r1 4条→r2收敛;主仓 b0ebf16a4/c11fb00b6/4dca49483+测试仓 73afa15e,验收 reports/T-6-acceptance.md 通过;稿面 §0 状态行未翻转,见晨报 §7-G2) |
| T-7 | CwScreenInvestEnv 投资环境 | 有问题(高0中3低3)·报告=账本reports/T-7-r1.md | **已实施**(invest_env.md;r1 6条→r2 3条→r3 1低→r4收敛;commit f41c40250 行为级:F-4 观察标准化门+局外单跑退役+正本四文档,验收 reports/T-7-acceptance.md 通过) |
| T-8 | CwScreenMegastar 盛会之星 | 有问题(高1中2低2)·报告=账本reports/T-8-r1.md | **已实施**(megastar.md 触顶稿定稿形态;5 commit:e7b803009 阶段1观察门+局外交回/9a064073a 阶段2守卫三臂/b480d85e8 阶段3文档面/34b6b799c+dbffcb326 坐标收敛;验收 reports/T-8-acceptance.md 通过附开放项 O1/O2 文档滞后、O4 环境卡观察缺口另批、D1 已申报偏差) |
| T-9 | CwScreenEquipPick 选择装备 | ~~有问题(高1中1低3)~~ **历史误判撤销**·报告=账本reports/T-9-r1.md(留档) | **画面不存在,全套已删除**(commit d37d78fab:op/yml/正本/迭代设计稿 equip_pick.md 一并删除;审查与增补工作留档不再实施;R1 六屏族→五屏、R2 :34 登记族同步除员) |
| T-10 | CwScreenYinLang 骇入策划/银狼升星 | 有问题(高0中2低3)·报告=账本reports/T-10-r1.md | **已实施**(planner.md;主体 r1 7条→r4收敛,一轮增补 §3 复攻收口,坐标规范增补 §4 r5→r8 触顶后终审修订(F-1 辖域澄清改形 + F-1b 确认钮查找全族统一 round_by_find_and_click_area 唯一行为项 + T-9 撤销余波收回);落地批 commit 54af975df+6df84b6db,验收 reports/T-10-acceptance.md **通过**(开放项4全低:CONFIRM死常量×2归卫生批/过程件随归档/节号不精确/簿记)) |
| T-11 | CwScreenPartner 选择伙伴 | 有问题(高1中2低3)·报告=账本reports/T-11-r1.md | **已实施**(partner.md 四重收敛:主体 r4+§3 增补 15 落点折入本体+§4 坐标登记(xy 全链=在册欠账恒None显式申报);落地批 主仓 54942fd9f+测试仓 c330f2bf(守卫两臂+返回契约+越界断言+兜底全删+直发),验收 reports/T-11-acceptance.md **通过零返工**(偏差0;开放4低:xy收敛批未立稿归T-37/env.idx陈旧注挂族级/r104前缀残留/状态行汇总批统一)) |
| T-12 | CwScreenFortune 命运卜者 | 有问题(高1中1低2)·报告=账本reports/T-12-r1.md | **已实施**(fortune.md;r1 5条→r2收敛+§3 新规范增补闭合+坐标规范增补(增补二对抗 r1 十三条→r3 收敛);落地批 commit 6a650aaac 行为面+6deedde66 坐标数据面+4a8a5a294 as-built 收敛+测试仓 7985ab04,验收 reports/T-12-acceptance.md **通过**(开放项1低:稿面正文旧申报未回改,零行为,汇总批回改)) |
| T-13 | CwScreenWishTrial 祈愿试炼 | 有问题(高1低2)·报告=账本reports/T-13-r1.md | **已实施**(wish_trial.md 三重收敛:主体 r3+§3 复攻收敛+§4 坐标闭合;落地批 主仓 705d5721a+测试仓 6a26bf31(F-1 三重守卫+兜底全删+直发/:36 两臂/:35 观察解点+双写+容器取点 env 停喂),验收 reports/T-13-acceptance.md **通过**(开放项2:守卫清单祈愿条目归正本更新阶段/跨批正向清单;偏差2判合理;4点设计漂移裁决全成立)) |
| T-14 | CwScreenBookcard 星徽秘典书册卡 | 有问题(高1中2低3)·报告=账本reports/T-14-r1.md | **已实施**(bookcard.md 触顶定稿形态(残留1低随批清偿):主体+§3 增补(:36 两臂/:34 登记与转换同批施工)+§4 坐标收敛;落地批 主仓 16e6e8a09+测试仓 9c42131f(守卫两臂/FACTIONS 两段门/坐标解算迁观察+双域零写/容器取点/F-4 七站点/守卫清单条目),验收 reports/T-14-acceptance.md **通过零阻断**(开放5:偏差2轻+开放登记3归T-37)) |
| T-15 | CwScreenExpertInvite 专家邀请函 | 有问题(高1低1)·报告=账本reports/T-15-r1.md | **已实施**(expert_invite.md 三重收敛:主体+§3 增补(锁E)+§4 坐标收敛(payload 双源取点);落地批 主仓 4371b188e+测试仓 e6c08d45(守卫两件+删宽except/:36 局外臂/坐标迁出+四字段双写等长守卫/双源取点五态断言/F-2 四站点/§1.3 条目),验收 reports/T-15-acceptance.md **通过行为面零偏差**(开放4低:O1 稿内5处stance回改归收口/O2 遭遇先例引据过时三屏注释归T-37/O3/O4 极低)) |
| T-16 | CwScreenBoxPick 武装箱选卡 | 有问题(高0中1低5)·报告=账本reports/T-16-r1.md | **已实施**(box_pick.md 三重收敛:主体 r4+§3 复攻收敛+§4 坐标闭合;落地批 主仓 b7ce3c9d9+测试仓 e3eed87b(:36 局外门/:34 标准化两段/:35 同门双写+容器取点 env idx-only;F-3 schema 键 box_card_opts→box_card_names),验收 reports/T-16-acceptance.md **通过**(开放项2低归T-37::36跨稿形态分歧——本屏round_success门vs遭遇屏已删门,待统一;LCS段无歧义拒判落差,实机关注)) |
| T-17 | CwOpOpenShop 商店框·开店 | 有问题(高0中1低2)·报告=账本reports/T-17-r1.md | **已实施**(op_open_shop.md 三重收敛:主体+§3 登记级+§4 坐标登记级;落地批 commit 8a6bd9e2d(修法 A act 现取→last_screenshot+F-2 九站点现役化+op-layer 例外③三类化宿主清单落现值),验收 reports/T-17-acceptance.md **通过**(开放项4均在册非本批缺陷:设计稿untracked待docs收尾/站点1-5坐标欠账待收敛批/同族面归T-37/ADR-0646标签已清偿观察;偏差1已预授权判合理)) |
| T-18 | CwOpCloseShop 商店框·关店 | 有问题(高0中3低3)·报告=账本reports/T-18-r1.md | **对抗触顶待裁决**(op_close_shop.md;r4终轮=收敛0条实质,3条低残留随定稿/归T-37) |
| T-19 | CwScreenArmoryBox 简易武装箱 | 有问题(高0中1低2)·报告=账本reports/T-19-r1.md | **对抗收敛待裁决**(armory_box.md;r1收敛附2条文字级备注) → **已实施**(落地批 主仓faa6f1a15+测试仓dc506e9f,验收reports/T-19-21-22-23-24-acceptance.md 通过零返工) |
| T-20 | CwScreenBriefing 简报 | 有问题(高0中1低5)·报告=账本reports/T-20-r1.md | **已实施**(briefing.md 触顶定稿形态(残留1低随批清偿:§2.5括注纯语义修订+session.md:55重写);主体F-1..F-6+§3 boss域行为级(两段转换+失败分流round_fail零写)+词缀登记级;落地批 主仓a2f094123+测试仓71bf5efc,验收reports/T-20-acceptance.md **通过**(偏差4+开放2全部非阻塞:D1行为级随批落地销号/O1 flow.py过期行归T-37/O2 ADR台账过期按9949eaaf8销号)) |
| T-21 | CwScreenBossBriefing BOSS简报 | 有问题(高0中2低2)·报告=账本reports/T-21-r1.md | **对抗收敛待裁决**(boss_briefing.md;r1 3条低→r2收敛) → **已实施**(落地批同上(五屏合并批),验收同报告通过) |
| T-22 | CwScreenPlaneTransition 位面过渡 | 有问题(高0中1低2)·报告=账本reports/T-22-r1.md | **对抗收敛待裁决**(plane_transition.md;r1 3条低→r2收敛) → **已实施**(落地批同上(五屏合并批),验收同报告通过) |
| T-23 | CwScreenWaitOneOne 等待1-1 | 有问题(高0中0低1)·报告=账本reports/T-23-r1.md | **对抗收敛待裁决**(wait_one_one.md;r1收敛) → **已实施**(落地批同上(五屏合并批),验收同报告通过) |
| T-24 | CwScreenDeployNotFull 未达上限弹窗 | 有问题(高0中0低4)·报告=账本reports/T-24-r1.md | **对抗收敛待裁决**(deploy_not_full.md;r1收敛附4条文字级备注) → **已实施**(落地批同上(五屏合并批,含F-4观察侧三腿锁),验收同报告通过) |
| T-25 | CwScreenPlaneIntel 位面情报 | 有问题(高0中0低5)·报告=账本reports/T-25-r1.md | **已实施**(plane_intel.md 三重收敛:主体 r3 定点+§3 登记级+R17 判据申报(开放集合采集豁免,稿面已有表述照抄);落地批 commit 7fa38e3a(F-1..F-5 零行为:变更史删/指针删/§7.6 双定位/日期清/裸名全形),验收 reports/T-25-acceptance.md **通过偏差0**(开放3簿记级:账本收口已由编排侧补/锚漂移1行归汇总校正/op-layer条款锚:36→:37他批所致)) |
| T-26 | CwScreenNextButton 下一步按钮 | 有问题(高0中0低2)·报告=账本reports/T-26-r1.md | **对抗收敛待裁决**(next_button.md;r1 7条→r2收敛附2低) → **已实施**(落地批 commit bb2974a44(九屏文档批:注释/正本文档/死码删除,零行为),验收 reports/T-26-35-acceptance.md 通过零返工) |
| T-27 | CwScreenPlaneDetail 位面详情 | 有问题(高0中0低3)·报告=账本reports/T-27-r1.md | **对抗收敛待裁决**(plane_detail.md;r1 2条中→r2收敛) → **已实施**(落地批 commit bb2974a44(九屏文档批:注释/正本文档/死码删除,零行为),验收 reports/T-26-35-acceptance.md 通过零返工) |
| T-28 | CwScreenConsumableOverlay 消耗品浮层 | 有问题(高0中0低1)·报告=账本reports/T-28-r1.md | **对抗收敛待裁决**(consumable_overlay.md;r1收敛附3低) → **已实施**(落地批 commit bb2974a44(九屏文档批:注释/正本文档/死码删除,零行为),验收 reports/T-26-35-acceptance.md 通过零返工) |
| T-29 | CwScreenEmblemDetailPopup 徽章详情弹窗 | **合规**(0发现)·报告=账本reports/T-29-r1.md | 无需修法,直接收口 |
| T-30 | CwScreenItemDetailPopup 物品详情弹窗 | 有问题(高0中0低2)·报告=账本reports/T-30-r1.md | **对抗收敛待裁决**(item_detail.md;r1收敛附1低) → **已实施**(落地批 commit bb2974a44(九屏文档批:注释/正本文档/死码删除,零行为),验收 reports/T-26-35-acceptance.md 通过零返工) |
| T-31 | CwScreenInterruptDialog 中断对话 | 有问题(高0中0低1)·报告=账本reports/T-31-r1.md | **对抗收敛待裁决**(interrupt_dialog.md;r1 5条→r2 1词→r3定点收敛) → **已实施**(落地批 commit bb2974a44(九屏文档批:注释/正本文档/死码删除,零行为),验收 reports/T-26-35-acceptance.md 通过零返工) |
| T-32 | CwScreenRefreshOddsPopup 刷新概率表 | 有问题(高0中0低1)·报告=账本reports/T-32-r1.md | **对抗收敛待裁决**(refresh_odds_popup.md;r1 4低→r2收敛附2低) → **已实施**(落地批 commit bb2974a44(九屏文档批:注释/正本文档/死码删除,零行为),验收 reports/T-26-35-acceptance.md 通过零返工) |
| T-33 | CwScreenRoleDetailOverlay 角色详情浮层 | 有问题(高0中1低1)·报告=账本reports/T-33-r1.md | **对抗收敛待裁决**(role_detail_overlay.md;r1收敛附4低) → **已实施**(落地批 commit bb2974a44(九屏文档批:注释/正本文档/死码删除,零行为),验收 reports/T-26-35-acceptance.md 通过零返工) |
| T-34 | CwScreenShopCardDetail 商店牌详情 | 有问题(高0中1低2)·报告=账本reports/T-34-r1.md | **对抗收敛待裁决**(shop_card_detail.md;r1收敛附4低) → **已实施**(落地批 commit bb2974a44(九屏文档批:注释/正本文档/死码删除,零行为),验收 reports/T-26-35-acceptance.md 通过零返工) |
| T-35 | CwScreenPrepLockedReturn 锁定返回 | 有问题(高0中0低1)·报告=账本reports/T-35-r1.md | **对抗收敛待裁决**(prep_locked_return.md;r1 2低→r2 2低→r3定点收敛) → **已实施**(落地批 commit bb2974a44(九屏文档批:注释/正本文档/死码删除,零行为),验收 reports/T-26-35-acceptance.md 通过零返工) |
| T-36 | CwScreenAhaEquipPick 顿悟装备选卡 | **合规**(0发现)·报告=账本reports/T-36-r1.md | 无需修法,直接收口 |
| T-37 | 汇总(晨报+本 README 收口) | **已完成** | 已完成,见账本reports/T-37-晨报.md(36 屏总表/18 项跨稿裁决清单/登记行主题汇总/6 项缺口核查) |
