# 0007. deploy 确定性部署(CV 占用 → 拖空槽 → CV 验源槽空)

> ⚠️ **部分被后续迭代**:「前排优先」被 [ADR-0099](0099-deploy-position-pref.md) 替(按角色 position_pref 选排,2026-08-12);「CV 验源槽空」验证被 [ADR-0120](0120-deploy-center-drag-unified.md) 替(`_src_changed` 验源槽变 + DragCwChar 统一拖拽,2026-08-13)。核心(CV 占用信号确定性部署、只拖空槽)仍有效。

- **Status**: accepted
- **Date**: 2026-08-09
- **原编号**: D-7

## Context
deploy 旧实现是 trial-and-error:试全槽 + SIFT 验 bench count。D-4 弃 SIFT 预填(SIFT 占用误判前排 → 跳前排 → 空板 → 出战阻塞 → loop 死循环),D-5 给了可靠的 CV 占用信号(`slot_occupied` 灰度 std)。有了可靠占用信号,部署可从 trial-and-error 升级为确定性。

## Decision Drivers
- D-4 卡死链:SIFT 占用误判 → 跳前排 → 空板 → 出战阻塞 → loop 死循环
- CV `slot_occupied`(D-5)给可靠空/占区分,不依赖角色身份/颜色
- retry-stick(拖后看 bench count 降)是事后验证,既费拖又依赖 SIFT count

## Considered Options
1. 保留 trial-and-error(D-4/D-5 后多余,废拖空槽)
2. SIFT 验 deployed(SIFT 半身占用不可靠,D-4 已证)
3. CV 占用 + 拖空槽 + CV 验源槽空(选中)

## Decision
`deploy_bench._deploy_deterministic`:CV `slot_occupied` 知 bench 哪些槽有角色 + stage 哪些槽空 → 每个有角色的 bench 槽拖到一个空 stage 槽(前排优先)→ CV 验「源 bench 槽空了」= 成功。同时覆盖 place + swap,替旧 trial-and-error。

## Consequences
- 正向:确定性部署(只拖空槽),准且快;不再废拖、不再依赖 SIFT count。
- 负向/代价:依赖 `slot_occupied` 阈值(灰度 std>25)准确;极端亮度场景可能漂(目前实测稳)。
- 边界:只知"槽位空/满",不知"角色身份" —— 身份排序由 D-8(SIFT)补,swap 由 D-10 扩展。

## Links
- `· docs/develop/currency_war/strategy/05_data_wiring.md`(每回合 op 序列)
- 关联 D-NN:D-4(弃 SIFT 预填)、D-5(slot_occupied)、D-8(身份排序扩展)、D-10(swap 扩展)
