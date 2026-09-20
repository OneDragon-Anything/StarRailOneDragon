# 接管域重构:编排单一源与位面详情识别管线 迭代设计(总纲)

## 0. 元信息

- 迭代目标:接管补采域重构——编排归 CwEntryPlaneIntel 单一源、位面详情识别拆 6 node 管线、写门收 kernel 屏文件、ctx 中转通道与防御性计数/降级退役(用户裁定 2026-09-20,会话逐条批准)
- 状态:对抗审中
- 文档清单:无详设(单文档方案,本文件即完整设计,深度要求同详设)

## 1. 问题与动机

### 现状症状(代码锚)

1. **巨型节点**:CwScreenPlaneIntel 中间节点在单个 node 内用 while 循环完成三位面采集/跳位面判定/节点序叉验/非净读容错(`operations/cw_screen/cw_screen_plane_intel.py` `_collect_cycle`),不可逐屏验收;
2. **ctx 裸属性中转**:采集结果经未声明动态属性 `ctx.cw_plane_bosses`/`ctx.cw_plane_affixes` 中转(写点带 `# type: ignore[attr-defined]`,cw_screen_plane_intel.py:695-696),生产 1 处、消费 2 处(cw_screen_prep.py:901-904、cw_entry_plane_intel.py:131-137)、"用完清空"纪律散布 3 文件——跨局泄漏风险分散且无类型保护;
3. **写门双份拷贝**:词缀幂等/已有真值不覆写的判定在 prep 侧(cw_screen_prep.py:869-870 触发门 + :911-913)与 entry 侧(cw_entry_plane_intel.py:144-173)各一份,kernel 屏文件(cw_screen_report/prep.py)只做"字段在场才写"的机械转录——违反 op-layer.md §2.2 判断线(2026-09-20 修订版:落容器半进 kernel 屏文件);
4. **徽章态误读**:详情屏 boss 节点的金色纹章图案被建模为"游戏侧不透露身份 → 记 None 占位容错"(cw_screen_plane_intel.py `conclude_plane_boss` skip 分支、docs/game/screens/货币战争-位面详情.md「徽章态」节)。实拍证伪:该图案即 boss 的**纹章风头像**(fixture = `sr-od-test/screens/货币战争-位面详情/位面详情-纹章风头像-run30.png`;单帧像素不可区分"该 boss 专属纹章"与"跨 boss 通用徽章","即 boss 头像"系用户游戏知识判读,2026-09-20,记录备查)。真相 = 模板库缺该风格致 SIFT 失败,属识别能力缺口而非信息缺失;把识别失败降级为 None 违反对账真值纪律;
5. **防御性计数与降级**:自建计数 `takeover_tries` + "两次失败放弃、boss 缺省中性"(`takeover_collect_done`,cw_screen_prep.py:876-885),违反循环无上限/不收敛响亮暴露裁定(op-layer.md §1.1,用户裁定)。

### 根因归层

③语义层:徽章态 = 对游戏真值的错误建模;防御性计数与降级 = 把"瞬时识别失败"错误建模为需容忍的常态(实质也是对失败模式的语义误设)。
②流程层:接管编排无单一源(prep/entry 两路各持一份写门);巨型节点 = 单 node 承载多屏流程,无逐屏验收边界。
①约定层:ctx 中转绕过容器、写门错层住画面 op(应住 kernel 屏文件)。

### 解决到哪 / 明确不解决

解决:上述 1-5 全治(三 op 责任切分 + 写门归 kernel 屏文件 + None/计数/降级退役 + ctx 通道删除 + 对账死机制退役)。

明确不解决(防范围外溢):

- **纹章风 boss 头像模板采集**(`portrait_plaza` 缺该风格模板 → 该类 boss 识别将失败):批外立项(用户裁定 2026-09-20)。在其落地前,含此类 boss 的对局接管会响亮失败——属预期行为(失败显影),非本迭代缺陷;
- 简报侧 plane_bosses 写入语义(CwScreenBriefing 直写,现役不动);
- boss_fit 消费算法(仅注释勘误)。

## 2. 方案

### 2.1 三 op 责任切分(系统级变化)

| op | 重构前 | 重构后 |
|---|---|---|
| CwScreenPrep | 观察 node 内联补采簇:触发判定 + 委派子 op + ctx 排干 + 写门 | 判定接管 → 委派 CwEntryPlaneIntel → **子 op 结果透传**(成功 = round_success 交回外循环重识别;失败 = round_fail 传播,走外循环既有失败链,不自旋)。**node 图零变更** |
| CwEntryPlaneIntel | 门 + 委派 CwScreenPlaneIntel → 写回session(排干 ctx 池进容器 + 对账网) | **编排单一源**:门(对局中/画面合法/**真值跳过——容器已有位面真值 → 零点击直通成功,防手动调起白开白关详情屏**)→ 打开位面详情 → 委派 CwScreenPlaneIntel → 关闭位面详情。写回 node 退役 |
| CwScreenPlaneIntel | 3 node(观察 / 巨型采集循环 / 关闭并回写 ctx) | 位面详情屏纯识别,6 node 管线(§2.2)。开/关转场移出;上报写容器 |

两条调用路(prep 内联委派 / MCP `run_operation` 手动调起)共用同一份编排,不再各走各的。

**prep 侧语义定稿**(三问三答):

- **触发谓词** = `not gs.plane_bosses.value`(逐字替换现役两臂 `takeover_collect_done.value or plane_bosses.value`;done 闩随字段退役,不引入显式失效标记);**「节点条可读」守卫保留**(现役语义 = 半开帧不委派、等下轮免费重判,cw_screen_prep.py:871-875;与 start_plane 无关——start_plane 推导职责退役不变):半开帧轮次跳过委派,不烧失败链;
- **委派失败**:经 `round_by_op_result` 透传子 op 结果——失败 = prep round_fail,交外循环既有失败链(重试/熔断)处置,不做 round_success 自旋;
- **失败后详情屏留场**:不加专用清理。下一轮 prep 触发接管 → entry 门「已在详情屏直通」分支跳过打开直接委派,自愈;连续失败 = 连续响亮,符合失败显影语义。

### 2.2 CwScreenPlaneIntel 管线规格

- 构造签名 `(ctx)`(start_plane 参数退役);已在位面详情屏为前提,node1 内置门:非「货币战争-位面详情」屏 = round_fail + 存证截图(调用时机错误,不进重试空转);
- node 序(用户裁定 2026-09-20;豁免 op-layer.md §1.1 两 node 形态,§3 记多屏管线形态):

  ```
  node1 识别位面1 → node2 点开位面2 → node3 识别位面2
  → node4 点开位面3 → node5 识别位面3 → node6 整理观察数据上报(写容器)
  ```

  点开节点带转移证据(目标位面卡选中/详情条联动出现);
- 单屏识别 = 现机制复用,不重造:点该位面卡 → `read_plane_detail_nodes` 动态定位 boss 节点 → 详情条标签验「首领」→ 大图标 SIFT 对拍模板库(依据:docs/develop/sr_od/application/currency_war/screens/plane_intel.md 现役机制行);
- **失败语义**:标签读不出 / 非首领 / SIFT 未命中 = 该识别 node fail → 框架 node 重试(识别 node `node_max_retry_times=3`,点开 node `=2`)→ 耗尽 = op fail,响亮暴露。**无 None/占位/降级分支**:`conclude_plane_boss` skip 分支、`decide_plane_skip`、`conclude_plane_unreadable` 容错、"半更新帧防误跳"复读全部退役(瞬时噪声由框架重试覆盖);
- **恒全采位面1→2→3**(用户裁定 2026-09-20"先按能采处理";原 2026-09-03"只采当前及之后"裁决由此取代)。显式接受战术风险:若实机证伪已过位面不可采,op 响亮失败显影后再修——不预置容错;
- 词缀采集机制不动(词缀横条随采;空 = 无词缀,上报走幂等门);
- **fixture 用途边界**:`位面详情-纹章风头像-run30.png` 仅作本设计证据与 game doc 勘误证据,**不进测试面**(识别失败场景用桩 SIFT 未命中构造)。

#### 附属机制处置(现役 op 内四个活机制的去留,逐一定死)

| 机制 | 去留 | 挂点/理由 |
|---|---|---|
| ①节点序列互证(`_cross_check_node_seq`/`node_seq_cross_mismatch`,输入 = 备战帧节点序列快照) | **退役** | 输入快照住现役备战入口分支,新前提(已在详情屏)下无输入。该机制实为**全节点类型序列的感知冲突留证**(纯记账,零决策),非 boss 位置防线;退役后非 boss 槽位的错型从"留证"变"无声"——显式接受的战术权衡;boss 槽错位仍由「标签验首领 + 失败响亮」承接 |
| ②节点类型台账两源落账(`ledger_update_plane` 'prep_row'/'plane_detail' + `fill_boss_by_position`) | **保留 plane_detail 源 + boss 位回填;prep_row 源退役** | 挂 node6 上报簇(op 侧,session 通道 `get_node_ledger`;kernel 屏文件只有 gs,先例 = 备战现行链写端)。prep_row 源随备战入口分支消亡退役,其信息由 plane_detail 源 + 回填闭环(台账定位"详情条源为主" = plane_intel.md §6) |
| ③敌人难度参考值(`read_plane_detail_difficulty` → `ledger.difficulty_ref`,现役逐位面读、值随选中位面变) | **保留** | **每个识别 node 同帧顺带读当位面值**;node6 按现役 `_collect_cycle` 的落账口径逐位面落账(session 通道,同②先例) |
| ④词缀效果账本登记(`register_affixes_from_names`) | **保留** | 挂 node6 上报簇(词缀上报后登记)。接管局这是词缀登记唯一活源(简报侧登记挂点 cw_screen_briefing.py 在接管局不运行;cw_affix_effects.py 自述双挂点),静默丢失 = 恰在本 op 服务的场景丢效果账本 |

②③④均为 session 通道操作,与上报写门(gs 通道)同居 node6 簇但分通道;异常口径沿用现役 best-effort(台账/登记异常不阻塞上报主链)。

### 2.3 上报语义(kernel/cw_screen_report/plane_intel.py 转正)

- obs 类扩展:三位面 boss 身份(3 槽 `list[str]`)+ 词缀(`list[str]`,可空);纯数据;
- report 写门(**唯一一份**,迁并现散落写门:词缀幂等门两份拷贝 cw_screen_prep.py:911-913 与 cw_entry_plane_intel.py:168-173、已有真值不覆写门 cw_entry_plane_intel.py:153-158):
  - `plane_bosses`:全量写;**已有真值不覆写**门(容器已有值 → 跳写;迁自 cw_entry_plane_intel.py:153-158);
  - `enemy_affixes`:**幂等门**(仅容器空时写;迁自 cw_screen_prep.py:911-913 与 cw_entry_plane_intel.py:168-173 双份拷贝);
- **统一写门 sig 定死**:`write_logic(plane_bosses/enemy_affixes, produced_by='CwScreenPlaneIntel', sig=ChannelSig(family='logic_action', actor='CwScreenPlaneIntel', screen='货币战争-位面详情', mode='compute'))`;evidence:`'plane_intel_row'` / `'plane_intel_affixes'`(原 'takeover_collect*' 语义段随字段退役)。定值依据:采集真值落账属 logic_action 族(同简报写点族);screen 标实际采集画面(非简报的空 screen——本写点有明确宿主屏);actor = 写者本体。原 ResumeAttach(logic_hook)与 CwEntryPlaneIntel(logic_action)两写端随本迭代消亡;
- ~~简报 vs 实采对账网迁入~~ **对账网退役**(治本裁定 2026-09-20):该对账现役唯一调用点在 `write_logic(plane_bosses)` 之后取 `.value` 比对——write_logic 即时生效,比对对象 = 刚写入的同一列表(自比较);已有真值不覆写门又保证有简报真值时提前返回不进对账。即**任何可达分支都不存在双源可比对**,属死机制,按"零实效机制退役"纪律随本迭代退役,不迁入新写门。处置:`reconcile_briefing_vs_plane_intel`/`briefing_reconcile_pairs`(obs/cw_briefing_obs.py)零消费删除;config 字段 `briefing_reconcile` 唯一消费点随亡,字段退役(grep 若发现另有消费,保留字段只删死路径并回报)。

### 2.4 退役清单

- `ctx.cw_plane_bosses`/`ctx.cw_plane_affixes`:生产(cw_screen_plane_intel.py:695-696)、消费(cw_screen_prep.py:901-904、cw_entry_plane_intel.py:131-137)、清空(三处)全删,grep 零残留;
- gs 字段 `takeover_tries`/`takeover_collect_done` 删除(cw_game_state.py,宿主 match_facts 域):**域内容变更 → `DEFAULT_GS_SCHEMA['match_facts']` 版本 bump(2→3)**,配套合同断言翻新(test_cw_game_state_contract.py 钉死 ==2 处);`kernel/cw_projection_audit.py:146-151` 两行申报随字段退役(该表自带退役完备性锁 audit_stale_keys,漏删必红);CwScreenPrepObs 接管域四字段删除,`report_screen_prep_obs` 瘦身保链域(kernel/cw_screen_report/prep.py);
- `_takeover_collect_if_needed` 整方法删除(cw_screen_prep.py:853-914);start_plane 全套退役(见 §2.2);
- **对账网退役**(见 §2.3):obs 两函数零消费删除、entry 挂点随写回节点消亡、config 字段处置;
- **None 语义注释勘误——全量清点口径**:grep『徽章态/该位面无身份』全 src 逐处改写为新语义(实采源恒全识别;None 仅可能来自简报源未读得),已知至少含:cw_game_state.py:2198(字段定义注释「该位面无身份」,字段存续)、cw_vocab.py:235、cw_observation.py:795-799、cw_comps.py:233/:1512、telemetry/schema.py:630、cw_briefing_obs.py(若对账函数已删则注释随亡);落地判据挂勘误清零(grep 双模式:『徽章态』+『该位面无身份』);
- 附属机制退役项(见 §2.2 处置表):①互证全套、②prep_row 源。

### 2.5 文档勘误(随正本更新批执行)

- docs/game/screens/货币战争-位面详情.md:「徽章态」节改写为"纹章风头像渲染变体"(boss 身份在屏——图案即 boss 纹章风头像,系模板库缺该风格致 SIFT 失败;频率统计保留;撤销"本屏无身份信息"结论;证据 = fixture 帧);**行 4 source_image 帧清单同步**(三帧 → 四帧,补纹章风头像帧);
- op-layer.md §3、§2.1、screens/prep.md、screens/plane_intel.md、game_state/fields.md:见 landing.md 正本更新清单(§2.1 清理已退役的 REGISTERED_ACTORS 表述)。

### 2.6 明确保留(防误伤)

- 免费刷新对账件与免费闸(cw_refresh_shop_action / cw_screen_buy_cards);
- prep 其余观察链(bench/装备/晶矿/溢出告警/现行链);
- CwScreenBriefing 的 plane_bosses 写点(简报源);
- CwEntryPlaneIntel 的独立调起入口能力(MCP run_operation 可达);
- 附属机制保留项:节点台账 plane_detail 源与 boss 位回填、敌人难度参考值、词缀效果账本登记(处置见 §2.2 表)。
