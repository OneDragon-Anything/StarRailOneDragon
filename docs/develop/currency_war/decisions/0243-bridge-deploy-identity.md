# ADR-0243 桥期 deploy 身份:四桥映射补全 hunt3/dot_belog(r373)

## Status

accepted(2026-08-22;r373;五局同指纹架构反思 25e3838d 驱动;局53 铁证)

## Context

49-53 五局 r3/r4 双败指纹 100% 复现,购买侧三轮修复(r368/r369/r371b)后指纹不变。反思审查定位统一根因:**桥期(尤其 hunt3)是决策系统的「无 target 真空」**——`_BRIDGE_FW_MAP` 只映射 xianzhou/train 四桥,hunt3/dot_belog 不在 → `transition_framework=''` + `target_comp=None` → deploy_bench 的 target 集与框架豁免名单全空 → 桥件+配方核心(仙舟对)只能走散牌通道与 8 阵营散板同序竞争,L432-437 板满即 return(无换人)→ 永久滞留 bench。局53 实证:bench 躺着爻光+藿藿,r3 出战板=狼狩2+系统散件。**买对的人没上场**——买侧/部署侧/成型速度是同一根因的三个投影。

## Considered Options

1. **桥 framework 映射补全**(选):FRAMEWORK_FACTIONS 加 '狼狩'/(狼狩,持续伤害) 与 '贝洛伯格'/(持续伤害,贝洛伯格)(桥池 engine_bonds 的目标羁绊,单一源派生);_BRIDGE_FW_MAP 加 hunt3/dot_belog。最小改动,deploy/卖侧 keep/豁免名单一次全通。不入 FRAMEWORKS 元组——pick_framework 早期框架选择仍只认三主流(仙舟 32%/列车 29%/量子),狼狩桥是 v2 桥期专属通道。
2. 桥 pseudo comp 通用化(桥→LineV1 伪 comp):重构面大,r251 曾修同型病只调排序——身份问题这次从根上给。
3. 板满 swap(bench 核心换场上散件):反思排序的最大杠杆之一,但拖拽换人的画面语义(拖到占用槽=替换?)未验证——单独走建档验证后落地(挂待办)。

## Decision

选 1。另配刷新门 `_dir_cnt<2 → <3`(r258 早期窗):买到 2 张方向件就停=局48 三人组只是首发店恰好 3 张的运气;第 3 件把「桥对子」升级成「桥+配方核心」。锁测试 4 条(全桥有身份/hunt3 框架目标/FRAMEWORKS 不变防 pick_framework 波及)。

## Consequences

- hunt3 桥选定后:狼狩/DOT 件获得 deploy target 身份+卖侧保护;cap 增长(升级)时空槽由桥件/配方核心优先填充,不再被散件抢;
- 局54+(重启后):r3 出战板预期从「8 阵营散板」变为「狼狩2-3+DOT+仙舟核心」——六局指纹的破局验证点;
- 板满 swap 仍缺(挂待办,需画面语义验证)。
