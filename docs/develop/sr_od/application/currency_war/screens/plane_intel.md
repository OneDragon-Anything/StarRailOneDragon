# 位面情报采集(plane_intel · 货币战争-位面详情)

> 代码 = 采集 `operations/cw_screen/cw_screen_plane_intel.py::CwScreenPlaneIntel`(位面详情屏纯识别,6 node 管线)+ 编排 `operations/cw_entry/cw_entry_plane_intel.py::CwEntryPlaneIntel`(四 node,独立可调起入口),均直继承 `SrOperation`。职责:接管场景(对局进行中但容器无位面序真值——MCP 重启丢内存 / bot 未走过简报链 / 人工要补)下补采三位面情报——三位面 boss(大图标 SIFT)/ 敌人词缀横条 / 位面节点带与敌人难度参考值。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

非外循环分支直管画面 op;两条调用路共用同一份编排(编排单一源 = `CwEntryPlaneIntel`):

- **备战委派** = `cw_screen_prep.py::CwScreenPrep._delegate_plane_intel_if_needed`(挂点 = 观察 node;触发谓词 = 容器无位面真值 `not gs.plane_bosses.value`;「节点条可读」守卫——半开帧不委派、等下轮免费重判、不烧失败链;委派结果透传,失败走外循环既有失败链);
- **手动调起** = MCP `run_operation` 独立入口(`CwEntryPlaneIntel`;容器已有真值时门节点零点击直通,不白开白关详情屏)。

## 2. 画面形态声明

**多屏管线形态**(6 node,用户裁定 2026-09-20 豁免 [op-layer.md](op-layer.md) §1.1 两 node):识别/点开子步各自独立 node 与重试预算,逐子步验收;开/关转场(进屏/出屏)归编排 op,采集 op 不开屏不关屏。

`CwScreenPlaneIntel` 节点图(`@node_from` 显式边):

```
识别位面1(start)→ 点开位面2 → 识别位面2 → 点开位面3 → 识别位面3 → 上报
```

重试预算:识别 node 3、点开 node 2,耗尽 = op fail(瞬时噪声由框架重试覆盖)。

`CwEntryPlaneIntel` 节点图(四 node,`@node_from` 显式边):

```
门(start)→ 打开位面详情 → 委派识别 → 关闭位面详情
```

## 3. 观察面

**恒全采位面1→2→3**(用户裁定 2026-09-20「先按能采处理」):

- **三位面 boss**(每个识别 node 同体执行 `_recognize_current_plane`):点该位面卡(「按钮-位面卡1..3」;转移证据 = 详情条节点编号 OCR 位面段联动到目标位面)→ 点最右 boss 节点(位置先验「首领 = 位面最后节点」;`read_plane_detail_nodes` 动态定位节点圆,节点数随位面/投资策略变,不硬编码)→ 详情条类型名标签验「首领」(`read_detail_node_type_label`;非首领 = 位置先验失效,重试)→ 大图标 SIFT 对拍 boss_avatar 模板库(`_read_boss_big_icon`,「区域-boss大图标」~107px;`obs/cw_node_reader.py::match_boss_sift`;锁态小图 SIFT 特征塌缩认不出,大图标增熵破局)。
  **boss 节点两种渲染态**:①头像态——节点 = 红框头像,大图标 SIFT 命中;②**纹章风头像渲染变体**——节点 = 金色纹章风头像图案,图案即 boss 的纹章风头像(boss 身份在屏;游戏侧画面档 = [../../../../game/screens/货币战争-位面详情.md](../../../../game/screens/货币战争-位面详情.md))。模板库缺该风格致 SIFT 未命中,属识别能力缺口;证据帧 = `sr-od-test/screens/货币战争-位面详情/位面详情-纹章风头像-run30.png`。两种态统一同一失败语义:**识别失败 = node 重试,耗尽 = op fail 响亮暴露,无 None/占位/降级分支**(把识别失败降级为 None 违反对账真值纪律;纹章风头像模板采集批外立项前,含该类 boss 的对局接管会响亮失败,属预期失败显影)。
- **敌人词缀**:「区域-词缀横条」(`read_detail_affixes`,位面1 同帧读一次;词缀不随位面卡切换变;空 = 无词缀,上报走幂等门)。
- **位面节点带**:该位面全节点预览序列随采随存(`_detail_seqs`,键 = 位面号 1 基;node6 经台账口统一落账)。
- **敌人难度参考值**:`read_plane_detail_difficulty`(每个识别 node 同帧顺带读当位面值;node6 逐位面落账;生产难度主源 = 备战旗牌两级管线,本值仅参考)。

## 4. 动作面

| 动作 | 归属 | 锚 | 等待/转移证据 |
|---|---|---|---|
| 点位面卡切选中位面 | 采集 op(点开 node;识别位面1 首步恒点卡1 保证从位面1起采) | 「按钮-位面卡1/2/3」 | 切卡等待后验详情条节点编号位面段 = 目标位面,未联动重重点 |
| 点 boss 节点圆 | 采集 op(识别 node) | 动态 center(`_boss_node_center`,可复用同帧已读槽列表免双读) | 固定短等后读详情条 |
| 点备战节点图标开详情 | 编排(打开 node) | 备战节点条动态 center(current 槽优先,无则首个检出圆;点任意节点图标都开) | 开屏等待后验「标识-位面详情标题」出现 |
| 点 X 关闭位面详情 | 编排(关闭 node) | 「按钮-关闭位面详情」 | 点后验「标识-位面详情标题」消失 = 真转移 |

## 5. 终结与交回

- 采集 op 入口门:非位面详情屏 = round_fail + 存证截图(调用时机错误——开屏归编排 op,不进重试空转);出口留在位面详情屏(关闭归编排 op)。
- 失败语义(响亮暴露):节点条读不出 / 详情条类型名未读出 / 非首领 / 大图标 SIFT 未命中 = 该识别 node round_retry,耗尽 = op fail;上报时无对局 session = round_fail(真值无处落,不静默丢)。
- 编排门三重(零点击):对局中(session 在,缺席 = fail 存证)→ 画面合法(备战/位面详情;其它屏 = 调用时机错误快速 fail 存证,不空转 retry 烧预算)→ 真值跳过(容器已有位面真值 → 零点击直通成功;放在屏幕门之后,错屏先报错屏,别让跳过门吞掉真实状态信号)。
- 编排委派 = `round_by_op_result` 结果透传(失败 = 编排 fail 交调用方失败链,不自旋);委派失败详情屏留场、无专用清理——下一轮再进时「已在详情屏直通」分支跳过打开直接委派(自愈);连续失败 = 连续响亮。
- 编排关闭 = 点 X 验标题消失 → success 交回外循环。

## 6. 状态上报面

- **容器写门(唯一一份)** = `kernel/cw_screen_report/plane_intel.py::report_screen_plane_intel_obs`(挂采集 op「上报」node,gs 通道):`plane_bosses` 3 槽保位全量写 + **已有真值不覆写**(简报源先落 = 真值已在,实采内容再新也只是重复或残留,不覆写);`enemy_affixes` **幂等门**(仅容器空时写;空读数 = 无词缀,不落写——空表覆写会把已有真值抹成「无数据」)。写门签名定死:`ChannelSig(family='logic_action', actor='CwScreenPlaneIntel', screen='货币战争-位面详情', mode='compute')`,evidence = `plane_intel_row` / `plane_intel_affixes`(采集真值落账属 logic_action 族,同简报写点族;screen = 实际采集画面)。
- **附属机制**(与写门同居「上报」node 簇,session 通道;异常口径 best-effort,不阻塞上报主链):
  - 节点类型台账:`kernel/cw_exec_state.py::ledger_update_plane` plane_detail 源(详情条整面覆盖,None 位保旧)+ boss 位按「首领 = 位面最后节点」位置先验回填(`fill_boss_by_position`,回填依据 = 本 op 标签验证语义)。台账值载体宿主 = `GameState.plane_node_sequences`(`PlaneNodeLedger`,容器非 Field 簿记)。
  - 敌人难度参考值:`get_node_ledger().difficulty_ref` 逐位面落账。
  - 词缀效果账本登记:`kernel/cw_affix_effects.py::register_affixes_from_names`(上报后登记;接管局这是词缀登记唯一活源——简报侧登记挂点在接管局不运行;命中结构化注册才入账本,登记体按在册条目幂等,补采重跑不双登记;登记面纪律 = [../game_state/effect-domain.md](../game_state/effect-domain.md) 词缀源节)。

## 7. 子态与 overlay

入口前提 = 已在位面详情屏(采集 op)/ 备战或位面详情(编排门);编排打开 node 备战节点条未读出 = 半开帧重试(开屏动画落定不足由 node 重试账兜)。已通过位面节点变暗 = 详情条识别退化正常态(渲染事实;恒全采语义 = 不按变暗裁剪跳位面)。boss 节点两种渲染态(头像态/纹章风头像渲染变体)见 §3,游戏侧描述 = 画面档。

## 8. 守卫与防线

点卡转移证据(详情条节点编号联动,防在错误位面上继续跑);位置先验失效 retry 兜底(点到的非首领节点);识别失败响亮失败(无 None/占位/降级,瞬时噪声由框架 node 重试覆盖);编排真值跳过门 + 详情屏留场自愈;委派失败透传(prep 侧不自旋、无自带计数/放弃分支)。守卫细则指针 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 = 「货币战争-位面情报采集」(采集子 op,随宿主编排访问的 `[cw-op]` 行承载)与「货币战争-接管补采位面情报」(编排);日志前缀 `[cw-plane-intel]` / `[cw-takeover]`。
- 测试锁 = `sr-od-test/test/sr_od/application/currency_war/test_cw_takeover_intel_pipeline.py`(6 node 流程 / 识别失败响亮失败 / entry 编排真值跳过 / prep 委派透传行为锁)。
- game 侧知识:画面档 = [../../../../game/screens/货币战争-位面详情.md](../../../../game/screens/货币战争-位面详情.md);位面结构/节点链 = [../../../../game/currency_war/research/README.md](../../../../../game/currency_war/research/README.md)(台账容器侧对接 = [../game_state/chain-observation.md](../game_state/chain-observation.md));画面建档 = `assets/game_data/screen_info/currency_war_plane_detail.yml`(+ 备战档节点条 area)。
