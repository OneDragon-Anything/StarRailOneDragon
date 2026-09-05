# ADR-0522: W209 换阵卖出义务臂与 ADR-0386 辖域桥接裁决

- 状态:已实施(代码+测试+本 ADR 含辖域裁决)
- 日期:2026-09-05
- 关联:ADR-0386(换血走演进层裁决——本 ADR 修正其辖域边界)、ADR-0521(P0-1 买面拆分)、14 号稿 §9(swap 发射位治本设计,玩家门后排期)、第三次停机诊断(20260905_noprogress_stop_diag/report.md「第三次停机」节)

## 背景

第七局实机 r9 备战环三环零推进停机(守卫第三次触发,同面第二次):线已成型(fp=1.00,target 已换 仙舟+列车同行)、板面 7/7 真满、bench 2 个 target 单位待进场,唯一腾位通道=卖 deployed off-target 件,但 W209 卖出熔断把含旧线 off-line 件(艾丝妲)在内的全部 deployed 护住 → 每环 sold 0/2 → 合法 no-op 死锁。诊断修正细节:黑塔不在围栏键域本就可卖,熔断实证行只列艾丝妲/停云/丹恒·饮月。

## 辖域裁决(对 ADR-0386 的桥接修正)

ADR-0386 决策 2 裁定「换血走演进层,不归 deploy 腾位通道管」——该裁决的前提是演进层换血通道存在。现状:演进层换血未实现,deploy 腾位是 deployed 槽位唯一卖出通道(SIFT 身份单位不经商店域)。裁决:**义务臂为显式桥接件**——在演进层换血落地(14 号稿 §9 swap 发射位,玩家门后)之前,deploy 通道承接换阵卖出义务;§9 落地时本臂让位并由彼处单一源接管(与 §9.2 E3 前置项同一收口批核)。

## 决策

1. `offtarget_sell_allowed` 加 `fenced_offline_sellable`(默认 True:off-line 引擎/配方件让位可卖)+ `protect_names`(新线 core∪shared,禁卖护栏不因换阵解除,P41② 口径)两参。
2. 触发门 `fenced_swap_arm_of`:fp≥1.00(form_progress 现读单一源)∧ deployed 计≥前后排槽位总数。未成型/未满板帧熔断原语义零变化。
3. 接线:bench 有 target 待进场 ∧ 触发门成立 ⇒ 开臂。

## 已登记债务

- **P18 型结构命题(立项候选,零参数可证)**:「fp≥1.00 ⟹ 买入集 ∩ off-line fenced = ∅」——成立则义务臂无振荡风险;证伪则触发门改 locked_comp 单一源(fp 与 locked_comp 建立一致性未论证,存在不一致帧则振荡回归)。
- as-built 同步:flow/action_exec.md off-target 行已随本 ADR 更新。
- 旧 test_cw_w209_offtarget_sell_guard 由 test_cw_deploy_ops.py 义务臂锁组取代(断言面含默认臂守卫保持)。

## 验证

ruff 净;test_cw_deploy_ops.py 64 passed(含守卫移除验证=义务臂关闭停滞形态复现、事故帧锁、触发门真值表、接线源锁);CW 快速集 2197 passed / 1 skipped(指纹守卫)。

## 修订(2026-09-05,三件审计 P1,fbcbe235)

触发门「板满」喂入修正:`sum(board.values())`(羁绊计数总和,一人多阵营 4 人可 11 次)≠部署数——建模对象错误使熔断自线成型起事实失效(过早不可逆卖旧线件)。现口径=`swap_arm_deployed_count`(占用一致性仲裁同源的 SIFT 真读部署数)。教训持久化:测试真值表喂对量掩盖错量——锁的建模对象与公式同等需审(P42 同型第二例)。
