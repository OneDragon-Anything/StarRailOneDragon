"""tracking 对账公共层(观察冲突审计 P0 #12)。

两处对账实现(deploy_bench._reconcile_tracking / cw_screen_prep._reconcile_tracking)同语义
但强弱不一 —— director 版有空读守卫(M14 实锤)+截图留证,deploy_bench 版直接覆盖(过渡帧
双空读会污染 tracking)→ bug 温床。本模块抽公共 helper:统一守卫 + obs_conflict 证据链。
"""
from __future__ import annotations

from cv2.typing import MatLike

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_of,
)

# (终态契约 §A:下行守卫标定常量 HP_REAL_JUMP_CONFLICT/HP_LOSS_CAP_P100_BY_NODE/
#  HP_SUSPECT_*/HP_ZERO_LOSS_NODE_TYPES 随守卫删除——cw_registry 标定面
#  失去消费方,标定段归属复核归 docstring 桶。)
from sr_od.application.currency_war.kernel.cw_opening_hp import opening_hp_prior

# 合成特效帧态门注入槽(分包依赖矩阵禁 kernel→obs 直依):kernel 只持槽位,
# 实现由 app 装配点(decision_assembly.install_obs_ports)从 obs 桶注入。
# 缺省关(None)= 门放行,回退直接走「连续 2 次确认采新」——与门函数自身
# 「screen=None → False 不拦」的 best-effort 语义同向,不引入新故障面。
_IS_MERGE_EFFECT_FRAME = None


def set_merge_effect_gate(fn) -> None:
    """注入合成特效帧态门实现(obs 桶 ``is_merge_effect_frame``;生产武装点接通)。"""
    global _IS_MERGE_EFFECT_FRAME
    _IS_MERGE_EFFECT_FRAME = fn


def is_merge_effect_window(screen: MatLike | None) -> bool:
    """合成特效窗判定读口(P3-10 批次二复审):观察消费前的窗内统一判别口。

    复用 ``_IS_MERGE_EFFECT_FRAME`` 注入槽(生产武装点 =
    decision_assembly.install_obs_ports 注入 obs 桶 ``is_merge_effect_frame``——
    与 star 回退帧态门是同一特效窗物理事实的两个消费口)。``screen=None`` 或
    槽缺省关(未装配)恒 False = 核对放行,与既有门 best-effort 语义同向,
    不引入新故障面;注入后 True = 窗内星读数物理不可信,消费方顺延核对
    (本帧不写观察、保 logic 逻辑态值,下帧干净帧实读覆盖)。
    """
    if screen is None or _IS_MERGE_EFFECT_FRAME is None:
        return False
    return bool(_IS_MERGE_EFFECT_FRAME(screen))


#: star 降级采新确认门(连续降级读帧数)。推导:确认门 N 必须 > 实测最长
#: 「同名多星星读抖动」episode 长度——2026-09-15 局深检实锤 bench 同名
#: 1/2/3★ 三副本并存时星读在帧间
#: 翻转,本局 3 次 episode 全部「连续 2 次」(05:48:54/05:56:12/06:04:44),
#: 旧 N=2 恰在 episode 末帧采新 → 锚被洗 → 全程抖动(3★ 合成线报废实证);
#: 动画窗族(排查结论存档 cw_dev/live_round11_diagnosis.md,274 张存证重放)
# (终态契约 §A:STAR_DOWNGRADE_CONFIRM_FRAMES 防抖常量与 _hold_star_read
#  保旧写入端已随 star 回退防抖退役删除——回退即采新,失败可见。)


def _merge_equips(old_list, new_list) -> list:
    """对账合并语义(ADR-0387,对账覆盖装备):char_id 续接保留 equips。

    断点实锤:对账写回若**整批替换** tracked 主账 deployed 面(新读对象
    equips=[] 默认,宿主现 = GameState.tracked_books),则 ``deploy_bench._
    snapshot_equips_into_tracking`` 写入的装备在下次对账即被冲(希儿装备
    闪烁实证——当年经决策行快照显影:round6 三条快照仅一条有装备)。

    修法:按 char_id 把**旧 tracking 的 equips 续接到新读对象**(同名多副本
    逐个配对消耗,次序无关);新读自带的非空 equips(画面真值,如 deploy_bench
    快照后传参)优先保留不覆盖;旧有新无(角色离场)自然丢弃。
    """
    old_eq: dict[str, list[list[str]]] = {}
    for bc in (old_list or []):
        if bc is not None and bc.char_id:
            old_eq.setdefault(bc.char_id, []).append(
                list(getattr(bc, 'equips', None) or []))
    out = []
    for bc in (new_list or []):
        if bc is not None and getattr(bc, 'char_id', ''):
            if not getattr(bc, 'equips', None):
                pools = old_eq.get(bc.char_id)
                if pools:
                    bc.equips = pools.pop(0)   # 同名逐个配对消耗
        out.append(bc)
    return out


def reconcile_tracking(session, bench, deployed, screen=None, *,
                       source: str = 'reconcile', ctx=None) -> bool:
    """tracking 对账统一入口:新 SIFT 读 vs 旧 session tracking,守卫后写回。

    守卫(审计 #11/#12):
    - **双空读守卫**(M14 实锤):新读 bench/deployed 双空 + 前值非空 = 疑 SIFT 过渡帧
      → 保旧不写(空读是读失败,不是「板真没了」);
    - **漂移留证**:新旧不一致 → obs_conflict(裁决=采新-对账纠漂)+ [cw!] 日志;
      一致 → 静默(常态无噪声)。

    (star 回退停机钩子已随「星回退处置归观察对账」批退役,2026-09-16:
    merge 预估星被实读证伪 → observe-vs-logic 对账承接,不再单设钩子。)

    Args:
        session: StrategySession(tracked_bench_chars/tracked_deployed 被写回)
        bench/deployed: 新读 list[BenchChar](None = 读失败,不写该侧)
        screen: 冲突帧(传则 obs_conflict 存去重截图)
        source: 证据行来源标记(deploy_bench/director)
        ctx: SrContext(传则 star 回退停机走 run_context.stop_running;None = 离线/测试只留证)
        合成特效帧态门(采新确认前判别):实现经模块级 ``set_merge_effect_gate`` 注入
        (分包矩阵禁 kernel→obs 直依);缺省关 = 门放行,走既有
        STAR_DOWNGRADE_CONFIRM_FRAMES 连续确认主干。

    Returns:
        是否发生了写回(False = 守卫拦截保旧)。边界:槽号健康门拒绝
        (bench 侧保旧)**不**计入 False——该门只辖 bench 写回分支,
        deployed 侧照常写回,函数整体仍返回 True;False 仅双空读守卫
        与 session 为 None 两处早退产生。
    """
    if session is None:
        return False
    # 形状契约(ADR-0316):tracked_bench_chars 在买牌后被
    # mutate_bench_deployed→pad_bench 就地 pad 成定长 9 槽**含 None**
    # (槽位表语义写入端)——本消费端若假设紧凑无 None 即双写冲突
    # (曾致验证局数百次 AttributeError 崩溃-重派循环)。
    # 守卫:跳过 None 槽(空槽在对账语义里=无信息,不是冲突)。
    # 旧账基准 = game state 簿记(宿主 = GameState.
    # tracked_books,本函数 = game state 层内部实现,就地处置)。
    _books = game_state_of(session).tracked_books
    old_b = [(bc.char_id, bc.star) for bc in _books.bench
             if bc is not None]
    old_d = [(bc.char_id, bc.star) for bc in _books.deployed
             if bc is not None]
    if not bench and not deployed and (old_b or old_d):
        log.warning(f'[cw!][{source}] 对账跳过:SIFT 双空读(疑过渡帧)+前值非空 → 保旧 tracking')
        _conflict('tracking', f'{old_b}|{old_d}', '[]|[]', screen,
                  verdict='保旧-双空读守卫(疑SIFT过渡帧)', source=source)
        return False
    new_b = [(bc.char_id, bc.star) for bc in (bench or [])]
    new_d = [(bc.char_id, bc.star) for bc in (deployed or [])]
    # star 回退留证(终态契约 §A:防抖/帧态门(ADR-0420)/银狼升费豁免退役
    # ——用户裁定「失败可见」,回退即采新;实机失准走识别优化批)。名级锚
    # 比较口径保留(名下最高读星对最高旧星仲裁一次)。停机钩子/采样登记
    # (star_regression)已随「观察对账覆盖」批退役(2026-09-16 用户裁定:
    # 星回退的处置归 observe-vs-logic 对账,不再单设停机钩子)。
    # 防抖可能原地改 bench/deployed 副本 star → 纠漂判定与日志必须
    # 取**防抖后**快照(改前快照会误导排障)。bench/deployed 入参
    # 是 SIFT 紧凑列表(无 None),但入参若被上游 pad 过则守卫之(同形状契约)。
    new_b = [(bc.char_id, bc.star) for bc in (bench or []) if bc is not None]
    new_d = [(bc.char_id, bc.star) for bc in (deployed or []) if bc is not None]
    drifted = (old_b != new_b) or (old_d != new_d)
    # 布局代次写回事实位:bench 侧是否实际写回(健康门通过)。
    # drifted 分支据此决定是否递增 bench_layout_epoch——deployed 驱动的
    # 纠漂不递增(bench 布局未变);误递增无害(重播种幂等)、漏递增有害
    #(布局变化无人知晓),故取「bench 写回 ∧ drifted」。
    _bench_written = False
    if bench is not None:
        # ADR-0646 S2 主修:写回经 bench_from_compact 重建槽位表——
        # 与下方 deployed 侧 deployed_from_compact 同构(ADR-0392 单一源
        # 适配先例,bench 侧为同构修法补齐,非发明新机制)。SIFT 读的
        # slot = 画面物理槽号(read_bench_chars→identify_slots 逐槽赋值,
        # 与读序同帧同源;亲读结论见 ADR-0646),重建后列表布局=画面布局、
        # slot=下标+1 天然一致,紧凑态从写入端消失,两域播种自动同源——
        # 消灭 tracked 下标布局 vs BenchChar.slot 脱节的持续制造点
        #(本函数旧写回直拷 SIFT 紧凑列表,违反 ADR-0316 形状契约)。
        # 前置槽号健康门:
        # 占用槽号唯一 ∧ 全在 1..BENCH_CAPACITY——把 bench_from_compact 对
        # 无效槽号的静默 fallback(冲突走 bench_place 首空槽)在写回点升级
        # 为显式拒绝,防脏读数固化为形状自洽的槽位表(布局错而守卫恒过,
        # 比现状更难发现)。违者拒绝写回保旧+留证:经 _conflict 通道
        #(obs_conflict 行经旁路进缺陷台账;kernel 层落账走出口约束)。
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            BENCH_CAPACITY,
            bench_from_compact,
            bench_occupied_slot_nos,
            bench_slots_healthy,
        )
        _slots = bench_occupied_slot_nos(bench)
        _healthy = bench_slots_healthy(_slots)
        if _healthy:
            # 锚定写回 = 观察态退出点:屏幕真值写回成功即「已观察」
            # ——容器观察态字段置 True(策略商店门放行;bench 读失败/双空
            # 读守卫/槽号健康门拒绝不走此处 = 保持未观察)。best-effort:
            # 容器缺席/写失败不阻断对账主链(簿记已照常写回)。
            game_state_of(session).tracked_books.bench = bench_from_compact(
                _merge_equips(_books.bench, bench))
            _bench_written = True
            try:
                game_state_of(session).write_logic(
                    game_state_of(session).tracked_account_observed, True,
                    produced_by=f'reconcile_tracking:{source}',
                    evidence='observation_anchor',
                    sig=ChannelSig(family='logic_action',
                                   actor='CwReconcile', mode='compute'))
            except Exception as _e:  # noqa: BLE001  观察态置位不阻断对账
                log.warning(f'[cw!][{source}] 观察态置位失败(不阻断): {_e}')
        else:
            # 留证排序 str 化:健康门防御的对象正是非 int 槽号,拒绝分支若
            # 对混型列表(如 [None, 2])直接 sorted 会先 TypeError——防御
            # 分支自伤,拒绝留证与保旧都未完成;此处取 str 化保排序
            # 可读且混型安全)。
            _slots_disp = sorted(map(str, _slots))
            log.warning(f'[cw!][{source}] 对账写回拒绝:bench 槽号不健康'
                        f'(唯一∧1..{BENCH_CAPACITY})slots={_slots_disp}'
                        f' → 保旧 tracking(脏读数不固化为槽位表)')
            _conflict('bench', '占用槽号唯一∧全在1..9',
                      f'slots={_slots_disp}', screen,
                      verdict=('保旧-写回槽号健康门拒绝(SIFT 读 slot 重复/'
                               '越界,拒写防脏布局固化为槽位表;'
                               'ADR-0646;处理:频发→查 SIFT 槽位识别)'),
                      source=source)
    if deployed is not None:
        # ADR-0392:tracked_deployed 是槽位表——_merge_equips 出紧缩占用序,
        # 写回前经 deployed_from_compact 转槽位表(单一源适配)。
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            deployed_from_compact,
        )
        game_state_of(session).tracked_books.deployed = deployed_from_compact(
            _merge_equips(game_state_of(session).tracked_books.deployed,
                          deployed))
    if drifted:
        log.warning(f'[cw!][{source}] 对账纠漂(read≠tracking):bench {old_b}→{new_b} |'
                    f' deployed {old_d}→{new_d}')
        _conflict('tracking', f'{old_b}|{old_d}', f'{new_b}|{new_d}', screen,
                  verdict='采新-对账纠漂(SIFT 实读)', source=source)
        # ADR-0646 S3:布局代次递增(churn 事件通道最小面)。对账纠漂
        # = 布局可能重排,visit 内未来消费者(单动作循环每动作消费前检差)
        # 据此截断在飞计划并按 tracked 重播种。当前架构 reconcile 均在
        # visit 外跑,恒无消费者(S2+S1 后 epoch 只递增不消费,纯未来防御:
        # 防 visit 中段未来引入读屏/对账点时布局变化无人知晓)。
        if _bench_written:
            game_state_of(session).exec_books.bench_layout_epoch += 1
    return True


# (终态契约 §A:hp 同域上行留证阈值/下行守卫三助手(_battle_facts_between/
#  _outcome_is_no_loss/_reject_down)已随 session 防御锚退役删除——
#  行为变化登记 design §1.3,实机失准走识别优化批。)


def reconcile_hp(session, new_hp: int | None, screen=None, *,
                 source: str = 'read_game_state',
                 node_t: int | None = None) -> tuple[int | None, bool]:
    """hp 对账统一入口(终态契约 §A 简化形态)。

    旧三层(保旧不写沿用/下行守卫/复现确认/帧龄门)随 session 防御锚
    (last_hp_real/last_hp_real_node/hp_suspect)退役删除——「上一真值」
    职责由 gs.hp 结算覆盖写端 + carried 语义承载(该三层 = ADR-0282 hp
    三层设计「读不到保旧沿用 last_hp_real」;ADR 档案目录已删,原文 =
    git 历史 docs/develop/currency_war/decisions/0282-hp-three-layers.md。
    定谳:结算观测 hp_after 与沿用锚的先后语义随退役消解——结算覆盖是
    hp 唯一真值入口,本读侧无锚可遮蔽之;行为变化登记 design §1.3:
    失读窗不再有锚补,实机识别失准走识别优化批)。

    保留两支:
    - 开局初值表先验(ADR-0559):读不到 → 实证档先验(readable=False,
      真值帧到达即被覆盖);先验输入 briefing_*/enemy_difficulty 待 T-3
      重复账退役换源 gs 正本;
    - 真值帧直传(真值帧是物理读数,判读侧消费证据)。

    Args:
        session: StrategySession(开局先验输入面;None=离线/测试,只透传)
        new_hp: read_hp_opt 现读(None=读不到,shop 开态血量区空)
        screen/source/node_t: 留证兼容形参(守卫删除后 node_t 不再消费)

    Returns:
        (决策用 hp, 是否真读):真值帧=(新读, True);读不到=(先验或
        None, False)——诚实未知(ADR-0491,不再 100 兜底)。
    """
    if new_hp is None:
        # 开局全无真值 → 遥测实证的初值表先验(ADR-0559;实证档 A8/108:
        # 基础 82、「开局不利」62;无实证档 → None 诚实未知,ADR-0491)。
        # 先验非真读,readable=False;真值帧到达即被观察覆盖。
        # (终态契约 §B:三先验输入全读容器——briefing 写端直入
        #  gs.enemy_affixes/selected_difficulty/enemy_difficulty。)
        prior = (opening_hp_prior(
            game_state_of(session).enemy_affixes.value,
            (game_state_of(session).selected_difficulty.value or '')
            if session is not None else '',
            game_state_of(session).enemy_difficulty.value)
            if session is not None else None)
        if prior is not None:
            log.info(f'[cw][{source}] hp 开局无真值 → 初值表先验 {prior}'
                     f'(词缀={sorted(set(game_state_of(session).enemy_affixes.value or []))};'
                     f'ADR-0559,readable=False,真值帧到达即被覆盖)')
            return prior, False
        return None, False   # 无实证档(其他难度/未读到难度)→ None 诚实未知(ADR-0491)
    return new_hp, True


def _conflict(field: str, old, new, screen, *, verdict: str, source: str,
              **ctx) -> None:
    """obs_conflict 封装(best-effort,导入失败/异常不阻塞)。**ctx 透传(如 char=)。"""
    try:
        from sr_od.application.currency_war.kernel.cw_observe import obs_conflict
        obs_conflict(field, old, new, screen, verdict=verdict, source=source, **ctx)
    except Exception:  # noqa: BLE001  留证 best-effort
        pass
