# T-32 刷新概率表 修法设计(refresh_odds_popup)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决(对抗轨迹:r1 未收敛 4 条低→修订→r2 收敛·0 条实质;残留 2 条低[R2-1 AGENTS §8 虚构直引/R2-2 登记行缺落地载体]一句话级,随定稿清偿;见 reviews/T-32-attack-r2.md)
- 审查输入:`.debug/progress/2026-09-22-cw-screen-review/reports/T-32-r1.md`(发现 F-1 一条;总判定 = 有问题,高 0 中 0 低 1)
- 真值基线:本稿全部「现状」陈述以审查时点工作树代码为准,落地时若代码已再变,以落地时点代码重新对账后再动笔。符号锚 = `文件::符号名`,行号仅作本稿定位辅助。文档路径根 = `docs/develop/sr_od/application/currency_war/`,代码路径根 = `src/sr_od/application/currency_war/`(下文反引号短路径均相对此两根;建档路径 = `assets/game_data/screen_info/`)。
- 修法性质:F-1 = `kernel/cw_overlay_registry.py` 本屏条目注释块改写,**零行为变化**(无任何逻辑/签名/字段值改动;`close_action`/`close_point`/`dispatch_priority`/`recovery_exit` 四行值逐位不动;op 文件、建档 yml、`sr-od-test/` 零触碰)。
- 准则参照:注释清理一致性参照 T-3 稿([battle_wait.md](battle_wait.md))§2.6 五条准则(禁形一·会话局部标识符 / 禁形二·变更史叙述 / 改写方向 = 结论→出处→边界 / 保留豁免 / 跨修法交叠一次成文)。本件命中面**不属两禁形**——「无关闭按钮 area」「供 cw_loop 0e2 / 恢复链复用」非会话标识符亦非变更史叙事,而是对现役状态的假陈述与无消费面的复用申报,适用条款 = 仓库根 AGENTS.md §8「注释对当前行为的陈述须与实现一致」义务(T-28 稿同判先例,[consumable_overlay.md](consumable_overlay.md) 卷首)。本稿实际消费的准则面 = 准则 3(改写只写现役行为与声明状态,结论→出处→边界);审查 §3 一致项禁借清理扩面的在册落点 = T-3 稿 §1「在册核对一致项」边界注(§2.6 准则 4 实文 = 保留豁免,非此义)。注释内退役号成分的清出另依 T-27 逐号裁决尺([plane_detail.md](plane_detail.md) §2.2),0e2 的尺上走查与出路 = §2.1 依据第 4 条。

## 1. 问题与动机

### 1.1 F-1 登记行注释与建档现状不符(低)

- **现状症状**(审查报告 F-1):`kernel/cw_overlay_registry.py` 商店刷新概率表条目行内注释(`:239-243`)两处失真——
  ①「× 位置 VLM 定位(实测坐标);**无关闭按钮 area**」与建档现状相反:建档 `currency_war_shop_refresh_odds.yml` 已建 `按钮-关闭概率表` area(pc_rect `[1471,233,1531,293]`,rect 中心 = ((1471+1531)/2, (233+293)/2) = (1501,263),恰 = close_point 值;审查 §2.2 ④ 已实测核对),且本 op 运行时点击的唯一坐标来源就是该 area(`operations/cw_screen/cw_screen_refresh_odds_popup.py::CwScreenRefreshOddsPopup.progress_once` 经 `kernel/cw_obs_core.py::area_center` 读建档 center → `mouse_move`+`click`;op 模块 docstring 亦申报「× 坐标已 area 化」)——读者对照注释与建档/op 两处得到矛盾的「当前值」画像;
  ②「close_point 载荷**供 cw_loop 0e2 / 恢复链复用**」的复用申报现役无消费面:全 `src/` 与 `sr-od-test/` grep `close_point`,除登记文件自身字段定义与两处条目载荷外零消费点(cw_loop 对本屏的分支 `:1151-1159` 只派发画面 op,on_result 仅日志)。
- **根因归层**(根源两问):①根在哪层 = **表示层(注释残留)**——× 坐标 area 化批把消费面(op 点击链)与 op docstring 申报同步迁移时,registry 登记行的注释漏扫未随;close_point 复用句则把「未接线的设计意图」写成了现在时的「现役复用面」。非语义层(机制本身合规:close_point 零行为路径,审查已判「不构成坐标单一真相源的行为违例」;registry「声明 + 锁」架构 = 模块头在册设计)、非流程层(单点位陈述,无结构性缺口)。②修的是根还是症状 = 注释块整块改写为与建档一致的现役陈述 = 治本屏症状的全部(单文件单点位;0e2 家族清点 = §1 明确不解决 #1,单点定性论证 = §2.1 依据第 4 条);『迁移/建档批收尾缺引用面清查门』的流程级根已由 battle_wait 稿 §2.1 跨批登记面立案(归宿 = harness landing 模板固定判据方向),本稿不重复立项(跨件半问:同根,共用同一登记,禁第三件症状补丁)。
- **解决到哪**:本条目注释块改写(逐字目标 = §2.1):「无关闭按钮 area」假陈述清出,改现役关屏路径 + 建档 area 锚;「0e2」退役号清出,改现役分发面符号锚;close_point 零消费面给取舍 = **留作恢复链预留声明并改措辞申报**(依据在册,论证 = §2.1 取舍)。
- **明确不解决**:
  1. op 注释「0e2」三处(`cw_screen_refresh_odds_popup.py` 模块 docstring `:3`/`:11` + `__init__` 行注释 `:41`)与文档 `screens/refresh_odds_popup.md` §5「0n」——归宿随族级清偿(T-37 在册),不在本点位辖域。号籍分记(依据须为真):**0n 为在役号**(`flow/outer_loop.md` §2.3 现行号表「0n 商店访问」在册,`:121` 日志口径「0n='商店访问'」同证)——屏文档 §5 系对在役机制的正确指认,真实缺陷 = 该篇 §1「号制已退役,不引 0x」自我声明与 §5 用号的自杀不一致(审查 §2.2 附带记录的原始框架);**0e2 已退役且现无对号映射**(outer_loop §2.3 尾句仅宣告「已无对应分支」,未给对号条目;T-27 补录的是 0a4,不涉 0e2/0n——「补录后已可解析」对 0e2 不成立),清偿时按 T-27 登记的退役号表完备性登记行对账。0e2 代码注释域清点(本稿核对)= **4 文件 6 处**:registry `:240`(本点位)/ registry `:314` / op `:3`/`:11`/`:41` / `cw_screen_shop_card_detail.py:4`(`sr-od-test/` 零命中);各处系独立指认、互不为对号条目(`:314` 与 shop_card_detail `:4` 共用「0e2 概率表/1d 星徽详情之后」同式短语,系家族公式雏形,非 0a4「同 0a4 口径」式跨文件互指);docs 侧另见 outer_loop §2.3 尾句(退役记录本体,非残留)与其「等处」所指正本枚举(如 `game_state/node-derivation.md` E16 行 0 系枚举,正本侧 0x 残留,同归族级清偿);最终清点以 T-37 全树 grep 对账为准;
  2. op 文件「bug#1 缓解」标签 3 处——跨稿在册分歧已登记候 T-37 裁决(T-11 保留派 / T-7、T-12 清出派,wish_trial.md §2.4 汇录;审查 §2.2 同证);
  3. op 模块 docstring「ADR-0584,A2」悬空引用——ADR-0584 家族在册欠账,归宿候 T-37 出路裁决(审查 §2.2 同证);
  4. registry 文件其余条目注释(含 `:314`「0e2 概率表」同族残留、`:330`/`:338` 0e3、消耗品/盛会之星既有挂账注)与模块头「一致性断言」申报的新鲜度——非本屏辖域(退役号族级清偿 / registry 级维护面);
  5. close_point 载荷形态升级(`close_area` 化)——D 面(退出链)统一切换批的家族面裁决(§2.1 备选 B),本稿只论证不落;
  6. 实机面(× 点击实机关闭成功率、入口锚实机命中率、恢复链接线时序)——审查 §4 静态不可判,本迭代边界外。
- **在册核对一致项边界**:审查报告 §3 全部一致面(推进型分型三方一致 / 决策控制铁律与读屏纪律 / 观察上报形态 / 文档 as-built 九节 / 「矩形中心 = 原 Point(1501,263)」出处职能保留判例 / AGENTS §3 转移验证形态 / 建档抽查)为落地禁触碰边界——本稿唯一修法域 = registry 本条目注释块,落地批禁借清理之名改动上述在码语义。

## 2. 方案

### 2.1 F-1 修法:登记行注释改写现役建档口径,close_point 留作恢复链预留声明

单点位(逐字;位置 = `kernel/cw_overlay_registry.py` 商店刷新概率表条目注释块,行号仅定位辅助):

| # | 位置 | 现状(逐字) | 目标(逐字) |
|---|---|---|---|
| 1 | 条目注释块(`:239-243`;`close_action=`/`close_point=` 两行值与其余字段行不动) | `# 不进清场派生集(非 closable,零行为前提);`<br>`# close_point 载荷供 cw_loop 0e2 / 恢复链复用`<br>`close_action=CLOSE_ACTION_POINT,`<br>`# × 位置 VLM 定位(实测坐标);无关闭按钮 area`<br>`close_point=(1501, 263),` | `# 不进清场派生集(非 closable,零行为前提);现役关屏 = 分发画面 op`<br>`# CwScreenRefreshOddsPopup 点建档 area「货币战争-商店刷新概率表/`<br>`# 按钮-关闭概率表」(× 按钮,VLM 实测定位;坐标单一真相源 =`<br>`# screen_info,cw_loop 分发臂零本条载荷消费)`<br>`close_action=CLOSE_ACTION_POINT,`<br>`# 退出恢复链预留载荷(恢复链消费面未切注册表 = 模块头「声明 + 锁」;`<br>`# RECOVERY_CLOSE = 复用 close_action 载荷离屏):现零运行时消费,`<br>`# 值 = 上述建档 area 中心,非独立第二源`<br>`close_point=(1501, 263),` |

依据(就地):

- 行为真值 = `cw_screen_refresh_odds_popup.py::CwScreenRefreshOddsPopup.progress_once`(读「按钮-关闭概率表」center → `mouse_move`+`click`;`CLOSE_AREA` 常量与 area 名同铭)+ 同文件模块 docstring「× 坐标已 area 化」申报 + `kernel/cw_obs_core.py::area_center`(screen_info → rect 中心,点击用);分发臂零载荷消费 = `operations/cw_loop.py` 分发臂 `:1151-1159`(仅 `_dispatch_screen_op` + on_result 日志闭包)+ 全树 grep `close_point` 零消费点(审查 F-1 同判)。
- 建档真值 = `currency_war_shop_refresh_odds.yml`(`按钮-关闭概率表` pc_rect `[1471,233,1531,293]`;中心 = (1501,263) 与 close_point 同值——审查 §2.2 ④ 实测核对)。「VLM 实测定位」保留依据 = rect 出处职能(同族判例:item_detail 修复稿对「原 VLM 定位已 area 化」判「承担 area rect 出处职能、不判变更史违例,保留」;审查 §2.2 ④ 对本 op docstring 同形句同判)——出处从 close_point 行移到建档 area 语义侧,与「area 化」现状同构。
- 「退出恢复链预留」依据在册 = `kernel/cw_overlay_registry.py` 模块头(五消费面之「退出恢复链」;「其余消费面(cw_loop 分支 / 退出链)尚未切换……本表对未切换面是『声明 + 锁』」)+ `RECOVERY_CLOSE` 常量语义(`:51`「复用 close_action 载荷(close_area 或 point)离屏」——本条 `recovery_exit=RECOVERY_CLOSE` 的载荷即 close_point)+ `OverlaySpec.close_point` 字段契约(`:78`「close_action='point' 时必填」)。审查 §4.3 对「恢复链复用是否未接线设计意图」存而不裁;本稿依上述在册条文裁之 = **未接线的设计意图**(预留声明成立)。
- 「0e2」清出依据(T-27 逐号裁决尺,[plane_detail.md](plane_detail.md) §2.2;号籍→语义→形态):
  - **号籍 = 确证退役**:outer_loop §2.3 尾句在册宣告(「0e2 在现行代码中已无对应分支」)+ git 考古定谳——分支原文随档(`git show 434cbac36~1`:分发表行 `('0e2 概率表', '货币战争-商店刷新概率表', '标识-刷新概率表')` 与 0e2 分支块在档),分支随 434cbac36(顺序链退役,改为两阶段身份分发)退役;
  - **语义 = 机制替换,所指 = 载荷复用消费语义**:`:240` 原句所指 =「分支消费本载荷」,该语义零现役载体(grep `close_point` 全树命中均在登记文件自身)且零历史载体(`git log --all -S 'close_point' -- src/` 唯一命中 = 注册表落码批 2da197517,其提交说明自申报「消费面未接零行为变化」——载荷自诞生即纯声明);考古:旧 0e2 分支 = 判定锚「标识-刷新概率表」+ `_dispatch_screen_op(CwScreenRefreshOddsPopup…)` 派发,关闭动作自持于 op(「× 坐标已 area 化(按钮-关闭概率表,中心 = 原 (1501,263))……保留在 op 内」随档),全生命周期未消费 close_point——「复用」自始即未接线意图,非「曾接线后断开」。替换 → 清/换锚。0a4 分界(防同构证据反读):0a4 所指 = 分发判定同源同参,该语义现役原样在(旧判定锚与现行身份行同屏同锚)故 T-27 判连续补录;0e2 在本点位所指 = 载荷复用消费(零载体)故判替换清号——本屏分发判定机制本身确实连续(旧判定锚 = 现行身份行同锚,op 注释「同源同参」自证;现役载体 = `cw_loop.py::CW_DISPATCH_SCREENS` 阶段一身份行「货币战争-商店刷新概率表」),但该连续面非 `:240` 原句所指,不动摇清号。出路对定性不敏感:替换 → 清/换锚;连续 + 单点指认 → 换锚清号(同出路);连续 + 家族互指 → 补录,但补录救不了零载体语义(无对号对象)——本点位无论何判,出路均为换锚清号,定性分歧不动摇修法。防 T-37 逐号台账宽松读法(裁决尺原文「禁无尺逐号拍板」):本分界声明随 T-37 登记行收录,逐号定性须逐号给依据——本点位 = 考古定谳档;在册宣告单证判替换(0i 先例)以宣告自足说明所指机制无载体为限,禁免依据通则化;
  - **形态 = 单点指认**:0e2 代码注释域 4 文件 6 处(清点 = §1 明确不解决 #1)各系独立指认、互不为对号条目——`:314` 与 shop_card_detail `:4` 的同式短语系家族公式雏形,与 0a4「同 0a4 位面详情口径」式跨文件互指(互为对号条目)不同型,不开补录支 → 换锚清号(新文本以现役 op 符号锚承担指认)。
- 注释纪律 = 仓库根 AGENTS.md §8(注释对当前行为的陈述须与实现一致;结论→出处→边界;变更史不进注释)+ AGENTS.md §5(screen_info = 画面识别与交互唯一事实源;坐标单一真相源)。

**取舍(close_point 零消费面:留作恢复链预留 + 措辞改申报,不删)**:

- 备选 A:删除 `close_point`(连带处理 `close_action`)——放弃,三条在册依据:①模块头架构 = 退出恢复链是五消费面之一、未切换面 = 「声明 + 锁」,close 载荷是该面的声明载体,删除 = 收缩恢复链声明面(与 registry「单一声明 + 派生消费」设计反向);②`recovery_exit=RECOVERY_CLOSE` 语义 = 复用 close_action 载荷,删载荷后恢复出口声明指向空载荷(悬空声明);③`OverlaySpec.close_point` 字段契约 = close_action='point' 时必填,保留 `close_action=CLOSE_ACTION_POINT` 而删 close_point = 契约违例,连带改 close_action 则从注释面修法升级为声明面重构、越 F-1 辖域。且审查已判零行为路径、非坐标单一真相源行为违例——删除收益(少一枚同值重复)小于声明面损失;同值重复的漂移风险由目标注释显式申报「值 = 上述建档 area 中心」锁死同步语义。
- 备选 B:载荷升级 `close_action=CLOSE_ACTION_AREA` + `close_area='按钮-关闭概率表'`——放弃(本稿):零行为差异(该条目 `closable=False` 不进清场派生集,恢复链未切换,分发臂不读 close 字段——两形态同为「声明 + 锁」)下属元数据声明变更,越 F-1 注释面辖域;point→area 的升级规则(哪些条目升、何时升)属 D 面(退出链)统一切换批的家族面裁决——同文件在册先例 = 消耗品条目挂账「建档批按该实作改声明并清 esc 值」、盛会之星挂账「待 D 面统一切换时一并重推」。本稿**不新增 T-37 登记行**:修后声明为真、无失真之债,升级面 = D 面批自然辖域,非需挂账的假陈述(T-28 清点纪律同款)。
- 备选 C:目标文本保留「供 cw_loop 复用」措辞、仅清 0e2 号——放弃:cw_loop 分发臂零载荷消费是静态事实(审查 F-1 同判),现在时复用申报原样保留 = 时态失真未除(T-22 指针现役化先例,[plane_transition.md](plane_transition.md) §2.2:以过期/无消费面的指称冒充现役机制的注释必须改写现役锚;外加更正注的「双层并存」读者仍先读到失真陈述,病灶加固而非治愈)。

**验证门(本修法完成判据,机械可判)**:

1. 禁形扫描:`grep -n "无关闭按钮\|cw_loop 0e2" src/sr_od/application/currency_war/kernel/cw_overlay_registry.py` 零命中(两短语现为本条目独有,`:330`/`:338`/`:346` 的 0e3/0f 属族级清偿辖域,不入本门);
2. 正向核对:修后注释块五成分在场——「按钮-关闭概率表」「CwScreenRefreshOddsPopup」「VLM 实测定位」「退出恢复链预留」「零运行时消费」;
3. `git diff` 确认该文件仅本条目注释行改动;`close_action=`/`close_point=`/`dispatch_priority=`/`recovery_exit=` 四行值逐位不动(零逻辑、零声明值 diff);`uv run ruff check src/sr_od/application/currency_war/kernel/cw_overlay_registry.py` 通过;
4. 四方口径互查一致:修后注释 ≡ 建档 `currency_war_shop_refresh_odds.yml`(area 名 / rect 中心)≡ `cw_screen_refresh_odds_popup.py::progress_once`(CLOSE_AREA 经 `area_center`)≡ registry 模块头「声明 + 锁」申报——本屏 × 关闭路径与 close_point 性质口径唯一,无第二源分叉。

### 2.2 落地文件面总表与统一验收

| 文件 | 修法点位 | 性质 |
|---|---|---|
| `kernel/cw_overlay_registry.py` | 商店刷新概率表条目注释块改写(§2.1 #1) | 注释(零逻辑、零声明值) |

统一验收:§2.1 验证门 1-4 全过;零行为变化(src 树无逻辑 diff);op 文件、建档 yml、`sr-od-test/` 零触碰;与审查报告 §3 全部一致面零交叠。

协调注(同文件在飞面):`kernel/cw_overlay_registry.py` 其余条目注释(道具详情/消耗品条目的 0e3、0f 残留与既有挂账、`:314` 0e2 残留)归退役号族级清偿与全仓注释卫生批(T-3 稿 §2.6 建议批),与本条目不同段、无交叠;同批落地时各按本稿与卫生批准则一次成文,禁互借名义扩面。
