"""晶矿奖励附着通道:spheres 观察写端单一挂接入口 + 声明入队/过期电平检查。

迭代 2026-10-10-ore-reward-attach(kernel 面,详设 =
docs/develop/sr_od/application/currency_war/changes/2026-10-10-ore-reward-attach/
details/ore-reward-channel.md §4-§5)。

为什么单一入口(详设问题与约束末条):spheres 的写端有两处(live = 备战
观察写端,sim = 节点面板呈现),附着奖励的身份键与 spheres 坐标耦合——
容差配对轨迹继承只在写端逐帧交叉核对「写前旧坐标 × 写后新坐标」时可判,散落
两处即键漂移(声明金被「消失清洗 + 新现重掷」链路静默蒸发)。两端
(live 3.4 / sim 3.3 接线)spheres 写一律经 :func:`report_spheres_observed`,
禁第二写径。
(范围注记:「一律经此」辖**观察写径**——动作/获得侧直写 spheres 为
策略晶矿授予矿新立形(采晶矿上报触发腿 + 策略卡获得链立刻腿),授予矿
身份若与后续观察真值不配对由步序 5 消失清洗自清,零观察写径污染。)

通道分工(硬约束,依据 = ``cw_game_state.write_logic_rand`` docstring:
附着奖励在实机是猜测 → 只能走随机态;通道混域会让消费门
``logic_rand_fields`` 对附着值失灵):

- ``spheres`` 本体 = 画面真值(位置/颜色),观察通道(``observe``);
- ``ore_rewards`` 附着值 = 可能世界快照,随机态通道
  (``write_logic_rand``;声明归属不可观察,用户裁定 2026-10-10);
- ``ore_declared_pending`` / ``ore_declared_done`` = 登记事实,
  逻辑态(``write_logic``;kernel 确定效果直写先例)。

声明入队/过期 = **电平触发单一规则**(无边沿检测、无帧间记忆、无 op 成员;
边沿形态已否定,取舍见详设「关键取舍」节):入队条件在每判定点现查
pending+done 双守卫(守卫状态住 GameState,op 每备战环重建无可失忆);
恢复局两形态(离线回放 done 随快照存续 / live 中断恢复对局 active_env 恒空)
各自闭合。**次序硬约束 = 入队检查完成先于同帧 spheres 写**(接错次序则
位面首帧新现生成时声明未入队,若该帧后无新现,声明永不附着)。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    OreSight,
)
from sr_od.application.currency_war.kernel.cw_ore_reward import (
    OreReward,
    generate_ore_rewards,
)

#: ore_rewards 域三写(rekey/生成/清理)的写入者标识(journal/台账过滤键)。
_ATTACH_PRODUCER: str = 'ore_reward_attach'
#: 声明域两字段(入队/消费/过期)的写入者标识。
_DECLARE_PRODUCER: str = 'ore_declared_channel'
#: 挂接生成采样分支的 rng 具名键(解析口 = cw_action_report.action_sampling_rng;
#: live 缺省回退现掷,sim 装配方供流键 rng——先例 = collect_ore 分支)。
_ORE_GEN_RNG_KEY: str = 'ore_reward_gen'


def _ore_key(xy: tuple[int, int]) -> str:
    """矿身份键 'x,y'(与容器 ore_rewards 键制同格,JSON 安全字符串)。"""
    return f'{int(xy[0])},{int(xy[1])}'


def _pair_tolerance(old_coords: list[tuple[int, int]],
                    new_coords: list[tuple[int, int]]) -> dict[int, int]:
    """容差配对(身份连续性判定,详设 §4 步序 3):旧列 × 新列贪心最近
    一一配对 → ``{旧下标: 新下标}``。

    - 配对门 = 双轴独立 ≤ 持存容差(单一源 = ``cw_identity_obs.
      SPHERE_PERSIST_POS_TOL``,与 ``filter_persistent_ores`` 同门;
      **kernel→obs 运行时导入本函数体内 lazy**——模块级反向边破坏
      kernel←obs 单向分层;禁复制数值);
    - 排序键 = 欧氏距离(实现用整数平方距离,单调等价且平局判定精确),
      最近者优先;距离平局 = 枚举序(旧列序 × 新列序)先者优先,**禁
      随机**——附着是随机态猜测,配对误差不引入系统偏差(sim 侧合成
      坐标恒稳无歧义);
    - 误配几何可达域(同帧两矿圆心最小间距 = Hough ``minDist=35``,跨帧
      各抖 ±12px 时异矿最窄 11px ≤ tol,交叉配对几何可达):贪心最近在
      真对距离(抖差,常态 ≪ 11px)< 交叉对距离时选真对,常态救回;
      误配接受并披露(详设 §4 步序 3 边界披露)。
    """
    # 函数体内 lazy import 公开名(kernel→obs 单向分层的本迭代立例形态)
    from sr_od.application.currency_war.obs.cw_identity_obs import (
        SPHERE_PERSIST_POS_TOL,
    )
    tol = SPHERE_PERSIST_POS_TOL
    cands: list[tuple[int, int, int]] = []   # (平方距离,旧下标,新下标)
    for i, (ox, oy) in enumerate(old_coords):
        for j, (nx, ny) in enumerate(new_coords):
            if abs(ox - nx) <= tol and abs(oy - ny) <= tol:
                cands.append(((ox - nx) ** 2 + (oy - ny) ** 2, i, j))
    cands.sort()
    used_old: set[int] = set()
    used_new: set[int] = set()
    pairs: dict[int, int] = {}
    for _d2, i, j in cands:
        if i in used_old or j in used_new:
            continue
        used_old.add(i)
        used_new.add(j)
        pairs[i] = j
    return pairs


def report_spheres_observed(gs: GameState, sight: OreSight, *,
                            obs_sig: ChannelSig,
                            hook_sig: ChannelSig,
                            evidence: str) -> None:
    """spheres 观察写端单一挂接入口(live/sim 共用;详设 §4 步序)。

    步序(单一入口,两端写 spheres 一律经此):

    1. 旧坐标列 = 写前 ``gs.spheres.value.points`` 的 (x,y) 列(值 None →
       空列);
    2. ``gs.observe(gs.spheres, sight, sig=obs_sig)``(现行为原样,含空读
       照写 count=0 语义);
    3. 容差配对(:func:`_pair_tolerance`)→ 配对命中 = 同身份,ore_rewards
       键 old→new 重挂(write_logic_rand,值不变**不重掷**——声明金由此
       在坐标抖动下保全;跨面板别名残留同坐标按同身份继承旧附着,
       sim 侧经济中性,live 侧自愈于观察收口);
    4. 生成集 = 无附着的现役身份(重挂后新值坐标中仍无键者——覆盖未配对
       新现、level 缺读跳过帧、恢复/竞态残留形态):level 缺读 → 本帧不
       生成(保真防御,下帧自动再进生成集);否则出队当前 plane 声明 →
       :func:`generate_ore_rewards` → 合并写(write_logic_rand, None 起点
       从 {} 起);声明消费写 = pending 移除 + done 追加(同一 write_logic
       承载,消费与标记原子);
    5. 未配对消失身份:键从 ore_rewards 移除(evidence ``ore_gen_cleanup``;
       零配对变化 ∧ 零新现 ∧ 零消失 → 零写)。

    - ``obs_sig`` = spheres 观察写的渠道①签名;``hook_sig`` = 挂接写
      (ore_rewards/声明域)用的 sig(泛指:live = logic_hook 族
      group_id 'prep:ore-channel',sim = logic_action 族 logic_sig
      ('sim:ores'),族差异归两端接线,详设 §5 sig 形态);
    - ``evidence`` = spheres 观察写证据串(空串按无证据透传);
    - 点击未真开的回补形态(点击已摘除、下帧矿重现):无旧坐标可配对 →
      按未配对新现重掷 = 新猜测,无偏;误记金域随机态由观察收口纠偏。
    """
    prev = gs.spheres.value
    old_coords = [(int(p[1]), int(p[2]))
                  for p in (prev.points if prev is not None else ())]
    gs.observe(gs.spheres, sight, evidence=(evidence if evidence else None),
               sig=obs_sig)
    new_coords = [(int(p[1]), int(p[2])) for p in sight.points]
    node = gs.node.value
    # plane 未知(首锚定前)用 0 仅作 evidence 面注记(判读可辨「未知」档;
    # 声明侧 check_ore_declared_level 对 node None 整段跳过,不依赖本值)
    plane = int(node.plane) if node is not None else 0

    # —— 步序 3:容差配对 → 键重挂(值不变不重掷)——
    pairs = _pair_tolerance(old_coords, new_coords)
    rewards: dict[str, OreReward] = (
        dict(gs.ore_rewards.value) if gs.ore_rewards.value is not None else {})
    rekeyed_any = False
    for i in sorted(pairs):
        old_key = _ore_key(old_coords[i])
        new_key = _ore_key(new_coords[pairs[i]])
        if old_key != new_key and old_key in rewards:
            rewards[new_key] = rewards.pop(old_key)
            rekeyed_any = True
    if rekeyed_any:
        gs.write_logic_rand(gs.ore_rewards, rewards,
                            produced_by=_ATTACH_PRODUCER,
                            evidence=f'ore_gen_rekey#p{plane}', sig=hook_sig)

    # —— 步序 4:生成集 = 无附着的现役身份 ——
    gen_coords = [xy for xy in new_coords if _ore_key(xy) not in rewards]
    if gen_coords:
        level = gs.level.value
        if level is None:
            # 本帧不生成(种子恒写 level=3,生产近乎不可达,保真防御):
            # 该批身份仍无键,下帧自动再进生成集;点击侧另有兜底(3.2 覆盖)
            pass
        else:
            pending = tuple(gs.ore_declared_pending.value or ())
            done = tuple(gs.ore_declared_done.value or ())
            # 出队当前 plane 声明条目,按生成集大小截断(generate 的
            # 「构造方保证 declared ≤ coords」契约由此成立;余量留队,
            # 下帧新现再附着)
            consumed = [e for e in pending if e[1] == plane][:len(gen_coords)]
            from sr_od.application.currency_war.kernel.cw_action_report import (
                action_sampling_rng,
            )
            generated = generate_ore_rewards(
                tuple(e[2] for e in consumed), tuple(gen_coords), int(level),
                action_sampling_rng(_ORE_GEN_RNG_KEY, None))
            # 新 dict 合并(禁就地改步序 3 已落 Field 的同一定对象——
            # frozen 帧替换语义,持旧引用的读者不被污染)
            merged = dict(rewards)
            merged.update(generated)
            gs.write_logic_rand(
                gs.ore_rewards, merged, produced_by=_ATTACH_PRODUCER,
                evidence=f'ore_gen#p{plane}+{len(gen_coords)}', sig=hook_sig)
            if consumed:
                # 声明消费写 = pending 移除 + done 追加(同一 write_logic
                # 承载,消费与标记原子;done = 幂等守卫第二分支)
                gs.write_logic(
                    gs.ore_declared_pending,
                    tuple(e for e in pending if e not in consumed),
                    produced_by=_DECLARE_PRODUCER, sig=hook_sig)
                gs.write_logic(
                    gs.ore_declared_done,
                    done + tuple((e[0], e[1]) for e in consumed),
                    produced_by=_DECLARE_PRODUCER, sig=hook_sig)

    # —— 步序 5:未配对消失身份 → 清洗 ——
    cur = gs.ore_rewards.value
    if cur:
        dead_keys = {_ore_key(old_coords[i])
                     for i in range(len(old_coords)) if i not in pairs}
        cleaned = {k: v for k, v in cur.items() if k not in dead_keys}
        if len(cleaned) != len(cur):
            gs.write_logic_rand(gs.ore_rewards, cleaned,
                                produced_by=_ATTACH_PRODUCER,
                                evidence='ore_gen_cleanup', sig=hook_sig)


def report_giftbox_sight_observed(gs: GameState, readings: tuple[int, ...], *,
                                  sig: ChannelSig,
                                  evidence: str = '') -> None:
    """giftbox_sight 观察写端单一挂接入口(live = 备战观察 heavy 段;sim
    零接线——sim 无板件;设计 = .debug/progress/2026-10-19-giftbox-piece-obs/
    designs/giftbox-piece-obs.md §2.2)。

    上报语义(用户裁定 2026-10-19):

    - ``readings`` 空 → no-op **零写**(未检出/OCR 全败/检测异常 = 本帧
      无样本:域原值与 ``pending_item_opens`` 逻辑态均保持,无「空读」
      形态——与 spheres「空读照写 count=0」的存在性通道语义分化);
    - 非空 → 一次 ``gs.observe`` 整条替换写(多件全报;部分件读不出 =
      可读子集替换写,不可读件上一帧读数随写丢失——整条替换语义,设计
      披露 4/5)。

    运行时零比较零纠偏:本函数不读 ``pending_item_opens``、不做模型↔观察
    的任何比较/修正——逻辑态恒由战斗结算/节点推进等模型事件链更新,观察
    域任何值不得触发队列写端;不一致对账 = 离线校准批(join 快照 prov
    时间线与队列事件线)。``evidence`` 传非空(空串经 observe 转 None 后
    prov 无行,校准时间线失效;先例 = spheres live 调用即传空串,勿效仿)。
    """
    if not readings:
        return
    gs.observe(gs.giftbox_sight, tuple(int(n) for n in readings),
               evidence=(evidence if evidence else None), sig=sig)


def check_ore_declared_level(gs: GameState, *, hook_sig: ChannelSig) -> None:
    """声明入队/过期电平检查(详设 §5;live 判定点 = 每个 heavy 帧
    ``observe_full`` 回执后、spheres 写之前;sim = 节点窗起点,接线归
    3.3/3.4)。

    **电平触发单一规则**(无边沿检测、无帧间记忆、无 op 成员):

    - plane 取值源 = ``gs.node.value.plane``(回执后现值;None = 首锚定前,
      node 域不在开局种子表 → 本帧不检查,下一 heavy 帧兜住——禁在锚定
      前后找「旧 plane 现值」,漏斗回执后已无旧值可用);
    - 入队条件(电平):``env = active_env 现值 ∈ ENV_ORE_GRANTS`` ∧
      ``(env, plane)`` ∉ pending ∧ ∉ done → 追加
      ``(env, plane, ENV_ORE_GRANTS[env][plane-1])``(write_logic)。位面 1
      晚选环境、位面 2/3 过渡、恢复局续跑全部由此一式闭合;
    - 过期(电平清理):顺手移除 pending/done 中 plane ≠ 当前 plane 的条目
      (write_logic,evidence 留痕 ``ore_declared_expired#p{old}``,逐旧
      位面一行)。边界披露:依赖 plane 读数单调(node 域漏斗直写无倒退
      免疫),plane 误读抖动 = 位面内至多重发一条声明,观察收口自愈,
      接受并披露(详设 §5);若实机为自动开启(矿永不出现),pending
      条目留至位面过渡被清理即终态——零污染。
    """
    node = gs.node.value
    if node is None or node.plane is None:
        return
    plane = int(node.plane)
    from sr_od.application.currency_war.kernel.cw_investments import (
        ENV_ORE_GRANTS,
    )
    env = gs.active_env.value
    pending = tuple(gs.ore_declared_pending.value or ())
    done = tuple(gs.ore_declared_done.value or ())
    # 守卫键 = (env, plane) 投影(pending 元素带第三位 gold,二元组对
    # 三元组列表做成员判定恒 False,守卫会静默失效)
    pending_keys = {(e, p) for e, p, _g in pending}
    golds = ENV_ORE_GRANTS.get(env) if env is not None else None
    if golds is not None and 0 < plane <= len(golds) \
            and (env, plane) not in pending_keys \
            and (env, plane) not in done:
        gs.write_logic(
            gs.ore_declared_pending,
            pending + ((env, plane, int(golds[plane - 1])),),
            produced_by=_DECLARE_PRODUCER, sig=hook_sig)
        pending = pending + ((env, plane, int(golds[plane - 1])),)
    for old_plane in sorted(
            {p for _e, p, _g in pending if p != plane}
            | {p for _e, p in done if p != plane}):
        new_pending = tuple(e for e in pending if e[1] != old_plane)
        if new_pending != pending:
            gs.write_logic(gs.ore_declared_pending, new_pending,
                           produced_by=_DECLARE_PRODUCER,
                           evidence=f'ore_declared_expired#p{old_plane}',
                           sig=hook_sig)
            pending = new_pending
        new_done = tuple(e for e in done if e[1] != old_plane)
        if new_done != done:
            gs.write_logic(gs.ore_declared_done, new_done,
                           produced_by=_DECLARE_PRODUCER,
                           evidence=f'ore_declared_expired#p{old_plane}',
                           sig=hook_sig)
            done = new_done
