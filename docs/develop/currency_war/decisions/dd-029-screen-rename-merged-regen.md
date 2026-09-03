# DD-029: 画面改名只改分文件漏再生 merged——运行时加载源漂移致「选择伙伴」遮罩下部署死局

- 状态: accepted
- 日期: 2026-09-04
- 关联: dd-028(编号避让:买面设计攻击批预留)、ADR-0269(「新增画面忘进名单」同族结构性缺口)、75880dd1(引入漂移的改名 commit)

## 1. 背景与问题(第三起实机卡死)

2026-09-04 01:02 起实机局(基线 95faf4e7)推进到 1-9 节点备战期,游戏弹出
「选择伙伴」事件遮罩(选择 1 名列车同行成员加入羁绊并复制首件装备效果)。
此后 ~8 分钟备战环反复重发 RunDeploy:部署拖拽「拖 3 次源槽未变,跳过」
(板面被遮罩盖住),`上阵不全: placed=0/7`,deployed 读数在对账纠漂中抖动;
每帧以「序列完成(RunDeploy),交回外循环重判」结束,下轮仍路由到部署。

失败帧存证:`.debug/images/deploy_fail_slot8_1788456717612.png`(遮罩全景);
应用日志 `.log/mcp_server.log` 01:24–01:32 段。

关键矛盾:**画面识别层没有任何问题**——`analyze_screen` 对遮罩画面精准命中
建档画面(标识-选择伙伴 + 按钮-确认选择均命中)。断点在分发/路由层。

## 2. 根因(代码级证据链)

OneDragon 的画面加载是**双层**的,运行时只读合并层:

1. `one_dragon/base/screen/screen_loader.py` `reload()` 默认分支(else 路径,
   L125–156)**只读 `_od_merged.yml`**,分文件(`currency_war_partner.yml` 等)
   仅在显式 `from_separated_files=True`(GUI 画面管理界面)时加载。
2. 75880dd1 把该画面改名:分文件 yml + 5 处代码引用 + overlay 注册表同步改为
   `货币战争-列车同行`(area「标识-选择伙伴」不变),**但 `_od_merged.yml`
   未随之再生**(commit 说明称「MCP server 重启后 yml 生效」——对 merged 不成立,
   重启只重读旧 merged)。
3. 于是运行时状态:`cw_loop.loop` 0a 分支
   `round_by_find_area(screen, '货币战争-列车同行', '标识-选择伙伴')` →
   `screen_utils.find_area` → `get_area` 在 merged 键空间查不到 → None →
   `AREA_NO_CONFIG` → `round_by_find_area` 返回 `round_fail('区域未配置')`,
   `if ...is_success` 为假,**分支静默跳过,无任何日志**(result 对象被丢弃)。
4. 分发落到备战分支:伙伴遮罩只盖板面,备战双锚(左下「购买经验」+「出战」)
   透出命中(伙伴分文件档内甚至存有 `备战标识-购买经验` area 佐证同帧可见)→
   进 CwScreenPrep → RunDeploy 拖拽全部落在遮罩上 → 源槽不变 → 死局。
5. 同帧 `analyze_screen`(消费同一 merged,含旧名「货币战争-选择伙伴」)
   精准命中——识别层「看得见」与分发层「查不到」同源于 merged 的新旧割裂,
   这正是矛盾的解释。

**一层根因**:merged 是运行时唯一加载源,却是「按需再生的缓存」——仓库里
没有任何机制保证它与分文件一致,也没有任何运行时信号区分「区域未配置」与
「画面上没找到」。

## 3. 修法(治本面)

1. **数据修复**:按分文件全集重生成 `_od_merged.yml`(101 屏;工具
   `.debug/temp/currency_war/hotfix_partner_overlay/audit_merged_drift.py
   --regen`,与 `ScreenContext.save()` 的 merged 写出口径一致)。修复前审计
   还发现 merged 整体过期:缺整屏(如「委托」)、2 个过期 area 孤儿
   (货币战争-投资环境/投资策略.按钮-刷新,分文件已删、代码无引用)。
2. **可诊断性(双通道,均已落地)**:
   - **框架层**(`one_dragon/base/screen/screen_utils.py`,编排者预批准):
     `find_area` / `find_area_binary` / `find_and_click_area` 三处
     `get_area(...) is None` 分支在 return 前加同一行
     `log.warning('区域未配置(画面名或 area 名不在运行时 screen_info 中): …')`
     (+`log_utils` import)。最小 diff=3 告警+1 import,返回枚举/调用方语义
     零变化;ZZZ 波及面=仅新增日志输出,会暴露 ZZZ 侧同类漂移(预期收益,
     SR→ZZZ 同步件已建)。
   - **SR 侧 cw_loop**:`CwLoop` 新增 `DISPATCH_AREA_ANCHORS` 全分支判定锚表
     (29 条,0 系全部浮层+备战双锚)+ `_dispatch_anchor_precheck()`(iter1
     调用):任一锚不在运行时 screen_info → 逐条 `log.error` 点名分支。不中止
     运行(缺锚分支退化为「该画面不识别」);硬门由测试侧同表断言补。
     框架告警按调用逐帧、预检每局一次汇总点名,互补不重复。
3. **回归锁**(`sr-od-test/test/sr_od/app/currency_war/
   test_cw_partner_overlay_dispatch.py`):
   - merged 新鲜度 = 分文件全集(screen_id 集/画面名/area 名集,红证已验:
     对修复前 merged 该锁 FAILED);
   - overlay 注册表 + 主循环序锁矩阵全部锚在 merged(运行时真源)可解析;
   - 事故帧 fixture(`sr-od-test/screens/货币战争-列车同行/伙伴遮罩-备战透出.webp`,
     取自失败帧)上伙伴锚 + 确认选择 + 备战购买经验锚同帧命中——路由恢复 +
     透出机制存证;
   - 主循环 `DISPATCH_AREA_ANCHORS` 预检表全部锚在 merged 可解析(生产侧
     iter1 log.error 软防线的测试侧硬门)。
4. **处理链归属澄清**:选择伙伴 overlay 的专属 handler 是 `CwScreenPartner`
   (选择 → 确认选择 → step2 请选择强化角色,生命周期 owner;注册表
   `handler_id='CwScreenPartner'` 同源,op 完整无缺口)。「专家邀请函
   CwScreenExpertInvite」是另一画面(货币战争-备战-专家邀请函)的 handler,
   与本 overlay 无关,不接线。分发优先级无需改动:0 系 overlay 分支先于备战
   双锚已由序锁矩阵(test_cw_dispatch_order_matrix)钉死,事故不是优先级问题。

## 4. Considered Options

- **A(采纳)再生 merged + 新鲜度回归锁 + AREA_NO_CONFIG 显式告警**:
  三层分别治数据、防复发、保可诊断;不改加载架构,风险最小。
- B 运行时改为加载分文件全集(merged 降级为纯缓存):更彻底,但改
  one_dragon 框架加载语义,波及 ZZZ 共仓与 GUI 画面管理界面,超出热修批
  权限面;作为后续演进挂账。
- C cw_loop 0a 分支兜底旧名:双源合法化,治标且扩散漂移,否决。
- D 把「选择伙伴」接给 CwScreenExpertInvite:归因错误(邀请函是另一画面),
  会造成新误派发,否决。

## 5. 后果

- 改画面 screen_name / 增删 area 的批次,**必须再生 merged 并与分文件一起
  提交**(新鲜度锁会红提示);改名不再声称「重启 server 即生效」。
- `AREA_NO_CONFIG` 形态的配置缺失由三条通道拦截:框架层告警(逐帧)、
  iter1 分发锚预检 log.error(每局汇总点名)、同表测试断言(提交面硬门)。
- 框架侧「分文件为源、merged 为缓存」的架构收敛(B 选项)挂账待排。
