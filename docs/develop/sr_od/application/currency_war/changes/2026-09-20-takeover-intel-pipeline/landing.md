# 接管域重构:编排单一源与位面详情识别管线 落地

> **通用工程门**(各阶段完成判据统一引用此定义,源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节):
> ①`uv run ruff check` 全部改动文件零告警;②L1 `$env:PYTHONPATH="src"; uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow" -q` 0 failed(总数可因并行批浮动);③git add 逐文件点名、提交前 `git diff --stat --staged` 复核入库面 = 申报面、不 push。
> 本迭代落地阶段采用**原子切换**:3.2 为单一原子阶段(接管链全部调用点同批切换),不留跨阶段破态窗口。

## 3.1 kernel 屏文件转正

**范围**:cw_screen_report/plane_intel.py 从占位转正——obs 类扩展(三位面 boss 身份 `list[str]` + 词缀)、report 写门两件(已有真值不覆写/词缀幂等)+ 全量写。边界:不含对账网(已裁定退役,见 3.2);不动任何 op 层文件;不动 CwScreenBriefing 写点。
**设计依据**:design.md §2.3
**文件面**:src/sr_od/application/currency_war/kernel/cw_screen_report/plane_intel.py
**依赖**:无
**优先级建议**:1
**完成判据**:
- 行为对照 design.md §2.3:写门单测(真值已在不覆写/词缀仅空时写/成功全量写,sig 逐位 = §2.3 定死形状)
- 通用工程门(见首节定义)
**验收凭据形式**:新增单测名 + L1 全绿

## 3.2 接管链整体切换(原子阶段)

**范围**:接管链全部调用点同批切换,阶段完成态即生产链一致——
①CwScreenPlaneIntel 重构为 6 node 管线(design §2.2 全规格:识别失败响亮失败、附属机制处置表四行、ctx 写点删除、上报走 3.1 report、fixture 不进测试面);
②CwEntryPlaneIntel 编排重构(门 = 对局中 + 画面合法 + **真值跳过零点击直通**(保留现役 entry 真值门语义,防手动调起白开白关详情屏)→ 打开 → 委派 → 关闭;写回 node 退役;start_plane 读取退役;ADR 死引用清理);
③CwScreenPrep 切换(`_takeover_collect_if_needed` 删除;触发谓词 `not gs.plane_bosses.value`;**节点条可读守卫保留**——半开帧等下轮免费重判;委派结果透传);
④字段与通道退役:gs `takeover_tries`/`takeover_collect_done` 删除 + match_facts 域版本 bump(2→3)+ 合同断言翻新;cw_projection_audit.py 两行申报删除;CwScreenPrepObs/report_screen_prep_obs 接管域瘦身保链域;ctx 通道三文件全删;
⑤对账网退役:obs `reconcile_briefing_vs_plane_intel`/`briefing_reconcile_pairs` 零消费删除、entry 挂点随写回节点消亡、config `briefing_reconcile` 字段处置(唯一消费点随亡;另有消费则保字段删死路径并回报);
⑥None 语义注释勘误全量清零(grep『徽章态/该位面无身份』逐处改写,含 cw_game_state.py 字段注释/cw_vocab.py/cw_comps.py/telemetry/schema.py/cw_briefing_obs.py);随 cw_observation.py 在文件面内顺手改写其 :756-759 docstring 段(描述已退役的跳过机制:渲染事实"过去位面变暗识别可能退化"保留,行为指引改恒全采+响亮失败;A19);
⑦sr-od-test 测试同步:位面 op 6 node 流程测试(桩 SIFT 未命中构造失败;fixture 不进测试面)+ 识别失败响亮失败锁 + entry 编排流程测试 + prep 触发委派测试 + 字段退役零残留断言翻新。
**设计依据**:design.md §2.1/§2.2/§2.3/§2.4(附属机制处置表)
**文件面**:src/sr_od/application/currency_war/operations/cw_screen/cw_screen_plane_intel.py、operations/cw_entry/cw_entry_plane_intel.py、operations/cw_screen/cw_screen_prep.py、kernel/cw_screen_report/plane_intel.py(3.1 已建,本阶段接线)、kernel/cw_screen_report/prep.py、kernel/cw_game_state.py、kernel/cw_projection_audit.py、kernel/cw_comps.py、kernel/cw_vocab.py、obs/cw_briefing_obs.py、obs/cw_observation.py、telemetry/schema.py、currency_war_config(briefing_reconcile 字段处置)、sr-od-test 对应测试文件
**依赖**:3.1
**优先级建议**:2
**完成判据**:
- 行为对照 design.md §2.1/§2.2:6 node 流程测试走通;识别失败 → 重试耗尽 → op fail → prep 透传 fail;接管链全链(prep→entry→intel→report→容器)一次贯通
- design.md §2.2 附属机制处置表逐行:①零残留、②④挂 node6 簇各一测、③难度参考**逐位面**落账(三识别 node 各读、node6 落账)
- entry 真值跳过门:容器已有真值 → 零点击直通(防手动调起白开白关详情屏)
- design.md §2.4:takeover 两字段/ctx 通道/对账网/start_plane 零残留;match_facts 域版本断言(翻新后值)绿;audit_stale_keys 完备性锁绿
- None 语义勘误清零:grep『徽章态』+『该位面无身份』src 双模式零命中(文档勘误归正本更新批)
- 通用工程门(见首节定义)
**验收凭据形式**:grep 零残留输出 + 测试名清单 + L1 全绿

## 3.3 ctx 通道与退役项零残留清扫

**范围**:全库 grep `ctx.cw_plane_bosses`/`ctx.cw_plane_affixes`/`takeover_tries`/`takeover_collect_done`/`start_plane`/`decide_plane_skip`/`徽章态`/`该位面无身份`/`briefing_reconcile` 残留,漏网点清理。边界:gs 容器字段 plane_bosses/enemy_affixes 本体与其合法写点(CwScreenBriefing、plane_intel report)不算残留;『徽章态』『该位面无身份』仅查 src(文档勘误归正本更新批)。
**设计依据**:design.md §2.4
**文件面**:以 grep 结果为准(预期无或极少)
**依赖**:3.2
**优先级建议**:5
**完成判据**:
- grep 零残留清单贴出;如有清理,行为对照 design.md §2.4
- 通用工程门(见首节定义)
**验收凭据形式**:grep 输出

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本
**设计依据**:本文件「正本更新清单」节
**文件面**:清单所列正本文档
**依赖**:全部落地阶段
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致
**验收凭据形式**:文档对照 review

## 正本更新清单

- docs/develop/sr_od/application/currency_war/screens/op-layer.md:§3 形态分型(CwScreenPlaneIntel 改记多屏管线形态 6 node、用户裁定 2026-09-20 豁免两 node、真实容器摄入面;CwScreenPrep 行接管补采改委派编排 op);**§2.1 清理已退役的 REGISTERED_ACTORS 表述**(现役 sig 校验只辖渠道族) ← 3.2
- docs/develop/sr_od/application/currency_war/screens/plane_intel.md:全篇按新结构重写(6 node 管线/上报域与写门/编排归属 CwEntryPlaneIntel/ctx 中转节删除/附属机制挂点/纹章风头像表述) ← 3.2
- docs/develop/sr_od/application/currency_war/screens/prep.md:接管补采行(委派 CwEntryPlaneIntel;触发谓词;tries/done 字段退役;失败透传语义) ← 3.2
- docs/develop/sr_od/application/currency_war/game_state/fields.md:plane_bosses/enemy_affixes 写点域改位面详情屏(sigs 按 design §2.3);takeover 两字段删除 ← 3.1/3.2
- docs/game/screens/货币战争-位面详情.md:「徽章态」节勘误为纹章风头像渲染变体(证据 = fixture 帧 sr-od-test/screens/货币战争-位面详情/位面详情-纹章风头像-run30.png;频率统计保留;"本屏无身份信息"结论撤销);**行 4 source_image 帧清单同步(三帧 → 四帧)** ← 3.2(勘误文本依据 = design.md §2.5)
