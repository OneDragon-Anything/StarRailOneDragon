# 0049. below-avatar 装备 icon 固定 ~32px(98px 模板 scale 0.33)

- **Status**: accepted
- **Date**: 2026-08-10
- **原编号**: D-49

## Context
D-46 建 mini-template(34px native)、D-48 推"icon 随装备数缩 → 3 件 28px 分辨率墙"。用户质疑"角色下方装备图标大小应该是一样的"。CV multi-scale 验证:1 件 / 3 件同图 best scale 都是 0.33(32px),3 件全中(无分辨率墙)。D-48/D-46 的"随数量缩"基于 harvest 投影法裁切假象(紧密横排 icon 投影连段失灵,裁出 34/28px 是脚本人为产物)。

## Decision Drivers
- 用户直觉 icon 大小一致
- D-48/D-46 的"随数量缩"建立在 harvest 裁切假象上
- CV 大图模板 multi-scale 给客观 scale

## Considered Options
1. mini-template 库(每装备每件数采;D-46 推;工程大 + 3 件也 borderline 误判)
2. 大图压缩 + 接受 3 件 borderline 分辨率墙(D-48;基于错误前提)
3. 大图 98px 模板 multi-scale scale 0.33(icon 固定 32px;选中)

## Decision
below-avatar 装备 icon 固定 ~32px(98px×0.33),**不随装备数变**。`read_equipped_below` 用大图 98px multi-scale(scale 0.30-0.37 含 0.35 位置变,D-51)主路径;mini 库(`cw_equip_mini`)冗余删除(34px mini ≈ 大图缩放结果)。

## Consequences
- 正向:简化(不建 mini 库);3 件全中(0.745-0.781);"谁穿了什么"给策略层地基(recognizer `front_equips`/`back_equips`/`bench_equips`,D-46 集成)。
- 负向:icon 尺寸随**位置**略变(梯形视角:前排 ~32px / 后排最右 ~34px)→ scales 需含 0.35(D-51)。
- 边界:进阶+3 件 borderline 是历史误判(实为裁切假象);通道灰度需 RGB2GRAY(D-52 bug)。

## Links
- `· docs/develop/currency_war/strategy/07_equipment.md`
- 关联 D-NN:D-46(mini-template,被纠正)、D-48(分辨率墙,推翻)、D-51(scale 随位置变)、D-52(RGB2GRAY bug)
