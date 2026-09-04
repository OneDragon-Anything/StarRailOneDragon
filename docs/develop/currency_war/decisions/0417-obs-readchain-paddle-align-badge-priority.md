# ADR-0417: 观测读链修复——部署对齐以 paddle X 为准 + board 裁决徽标优先(W287)

## 背景

W285 分层抽样(`.debug/temp/currency_war/w285_obs_conflict_sampling.md`,4258 张 obs_conflict 实证)判明读链两大病灶族(合计外推 ~2938 张,69%):

1. **部署数目标错位**:read_game_state 的部署对齐目标 = `min(sum(state.board.values()), level)`。board 是**羁绊计数**(多阵营角色重复计:藿藿=仙舟+治疗算 2)+ 徽标 OCR 误读放大,不是部署角色数——prep_director r3(2026-08-17)同判早已把 board 移出三源对拍("board 根本给不出角色数"),read_game_state 这处漏改,继续驱动补齐/截断 → 幻影部署(W285 deployed_align 3/6 误判;5aa9ce34 board_ocr=17 vs 实部署 7)。tracking 空板帧幻影(2/6)同根:board 徽标误读经重建上限灌进 deployed。
2. **board 裁决方向错**:tracked 身份 computed 与左栏徽标 OCR 计数不等时,旧裁决采 computed;W285 board 层抽样 3/6 采错——游戏左栏徽标才是画面事实(b6fc9934 徽标盛会之星=2、computed=1)。但 overlay 遮挡帧(2/6)徽标与 computed 各错一次(10f40509 徽标对/32f9abdd computed 对)——无条件翻转会在 overlay 帧引入新错。

## 决策

- **部署对齐/重建目标 = 舞台 paddle「X/Y」的 X**(`read_deployed_count`):舞台指示几何上只数已上阵角色,不含底部商店行/备战栏。paddle 读不到(overlay 遮挡/OCR 失读)= 本帧无对齐基准 → **跳过对齐**(宁缺勿造:补齐/截断都是用猜的数改写 tracking);重建分支(tracked 空)上限 = `min(level, paddle X)`,空板(paddle=0)不再幻影。
- **paddle 图标前缀守卫**:「X/Y」左侧人形图标常被 OCR 并进 X 成前缀 '1'(空板 0/3 实读 "10/3",字段先验 X≤Y 恒成立)——去前缀 '1' 后入域才采;仍域外维持旧行为(X 不可信返 None,Y 仍可信)。
- **board 裁决翻转(带 overlay 守卫)**:computed 仍是全集底座(滚出屏阵营只有它知道);可视行徽标计数与 computed 不等时,**备战帧且徽标解析 honest → 采徽标覆入**(`is_prep_like_frame` 判定,仅真有分歧时才做帧态判定,常态零开销);**非备战帧(overlay/动画)双不可信 → 不裁不覆**,保 computed 底座 + 留证,等下一帧备战帧再裁——overlay 帧两侧各 1/2 错的实证不支持任何单向裁决,不裁是唯一不引入新错的选择。

## Considered Options

1. **采纳:paddle X 为对齐基准 + 徽标优先翻转 + overlay 双不可信守卫**(本批)。
2. 拒:对齐目标改「独立羁绊外的最大单阵营计数」——同阵营多角色照样错,且 prep_director r3 已论证 board 结构性给不出角色数。
3. 拒:对齐目标用 CV 占用(front_occupied+back_occupied)——read_game_state 无 obs 上下文,重算一遍 slot_occupied 是第二实现;候选否决后 paddle 是唯一同帧可读的部署数画面事实。
4. 拒:board 裁决无条件翻转(不看帧态)——W285 overlay 帧 1/2 会翻错,用「不裁」换「不引入新错」,备战帧自愈。
5. 拒:徽标不可读时回退采 computed——overlay 帧 computed 同样 1/2 错,回退即恢复旧病灶。

## Consequences

- deployed_align 冲突族(board 徽标和误计 + 空板幻影)源头消除;paddle 失读帧无对齐(原补齐/截断本就是猜,无信息损失)。
- source 字段 `tracked_vs_board` → `tracked_vs_paddle`;board 冲突 verdict 语义变(采新-badge / 留证-双不可信),判读侧按新口径读 obs_conflicts.jsonl。
- 旧锁更新:test_cw_observation a8_start 帧(真值 0/3,OCR "10/3")由「X>Y guard 返 None」改锁「图标前缀守卫返 0」——0 是画面事实,防幻影重建的正确值。
- 已知边界:paddle 读不到且 tracked 为空的帧,deployed 重建仍退 level 估(旧行为);该残留在 paddle 长期失读场景(遮挡整轮)不消除,由 board 冲突留证暴露。
