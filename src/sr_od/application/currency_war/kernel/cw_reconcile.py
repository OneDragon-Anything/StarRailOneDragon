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


# star 回退截图留证注入槽(共用中段禁摸像素——kernel 不
# import cv2,截图落盘实现住 app 装配模块,经 decision_assembly.install_obs_
# ports 注入;先例 = 上方 ``set_merge_effect_gate`` 同款装配缝)。缺省关
# (None)= 不落截图,flag 文本留证照写(best-effort 语义同向,不引入新故障面)。
_STAR_EVIDENCE_SAVER = None


def set_star_evidence_saver(fn) -> None:
    """注入 star 回退截图留证实现(签名 ``(screen, char)``;生产武装点 =
    decision_assembly.install_obs_ports)。"""
    global _STAR_EVIDENCE_SAVER
    _STAR_EVIDENCE_SAVER = fn


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
#: 窗内假确认 ≤2 帧,且特效帧已由帧态门前置冻结计数、不占 N。N=3 = 观测
#: 覆盖(2)×1.5 边际;代价不对称:假保旧(真降级晚 N−1 帧,秒级自愈)≪
#: 假采新(锚洗,整局抖动)。真降级形态 = 同名同槽连续 ≥N 帧低读(持续性
#: 遮挡),N 再大线性加重该形态自愈时延,3 为观测覆盖与时延的平衡点。
STAR_DOWNGRADE_CONFIRM_FRAMES: int = 3


def _hold_star_read(tracked_bench, bench, deployed, name: str,
                    anchor_star: int) -> None:
    """保旧写入端:本帧读链中该名的锚定星不被低读洗掉(原地修读链)。

    判读 = 名级锚比较(主循环只对「名下最高读星 < 锚定星」仲裁一次;
    逐副本对名 max 比较会把真实 2★/1★ 副本误判成回退并连环误抬——
    run_20260915_054718 §5 bench 1/2/3★ 三副本并存形态)。保旧三级:
    ①槽位锚定:tracked 槽位表上锚定星副本所在物理槽(bench 侧 = 表下标
      +1,ADR-0316)在本帧读链同槽读低 → 原地抬回锚定星(旧「首个低读
      副本」命中会误抬真实低星副本,假 3★ 与丢真 1★ 双向污染合成/卖牌);
    ②锚槽缺失(SIFT 漏检锚副本):注入锚副本重建(slot=锚槽,star=锚定星)
      ——不注入 = 写回即锚被静默洗掉;注入使锚定星跨帧存续,equips 经
      _merge_equips 同名配对自旧 tracking 续接;
    ③槽位对不上(deployed 侧 = 排内槽号坐标系,不入锚集)回退首中抬升
      ——deployed 侧同名唯一性守卫(mutate_bench_deployed W43 裁决)
      保证至多一副本,首中即唯一。"""
    anchor_slots = {i + 1 for i, bc in enumerate(tracked_bench or [])
                    if bc is not None and bc.char_id == name
                    and bc.star == anchor_star}
    if anchor_slots:
        for bc in (bench or []):
            if (bc is not None and bc.char_id == name
                    and bc.slot in anchor_slots and bc.star < anchor_star):
                bc.star = anchor_star
                return
        for bc in (bench or []):
            if bc is not None and bc.char_id == name \
                    and bc.slot in anchor_slots:
                return   # 锚槽该名在读但读星≥锚:不修,交常态采信
        # 锚槽该名整缺(SIFT 漏检)→ 注入锚副本(见 docstring ②)
        from sr_od.application.currency_war.kernel.cw_exec_state import BenchChar
        bench.append(BenchChar(slot=min(anchor_slots), char_id=name,
                               star=anchor_star))
        return
    for lst in (bench, deployed):
        for bc in (lst or []):
            if bc is not None and bc.char_id == name and bc.star < anchor_star:
                bc.star = anchor_star
                return


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

    ⚖️ star 回退停机钩子(用户 2026-08-17 指示):买牌 merge 预估升星(tracking)后,实机
    read_star 回读更低 = 星级识别可疑(read_star 漏金星/星区被遮挡)——**star≥2 的回退连续
    2 个节点仍现 → 停机保画面排查**(第 1 次可能是升星特效遮挡过渡帧,一节点内消;防抖
    同 M35 shop_unknown 模式)。sentinel 自描述(删钩子位置/排查项),防「孤儿残留」误判
    (教训:反复出现的 sentinel 必有活生产者,grep 写入者)。

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
    _pending_evidence: list[tuple] = []   # 留证队列(对账位统一消费)
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
    # star 回退留证(观察冲突审计 #13):同名 star 下降(如 2★读回 1★)= read_star
    # 漏金星 或 卖后重买边缘场景;不保旧(审计:保旧不安全)只留证统计毒化率。
    _old_stars = {(n, s) for n, s in old_b + old_d if n}
    _new_stars = {(n, s) for n, s in new_b + new_d if n}
    _reg = dict(game_state_of(session).exec_books.star_regression or {})
    # ⚖️ star 回退防抖 + 锚定(274 张存证全量重放实证:回退角色 40/40 在场
    # 且 36/40 **同图重读为 2★**(live 读 1★)→ 真根因 = 3合1 合成动画窗
    # 识别(read_star 在特效期读 1,存证帧在动画后半段星已显),非 SIFT
    # 身份错配)。回退即采新写回 → 动画窗 1★ 毒化 tracking,下一帧又纠回
    # (往返抖)。修法(两级):
    # ①锚定保旧:首次回退不写回(该角色 star 保旧=_old_s 即锚定星),读低
    #   副本按槽位锚定抬回(_hold_star_read);下一帧读回正常即自愈。
    # ②超额证据采新:名级最高读星低于锚定星连续 STAR_DOWNGRADE_CONFIRM_
    #   FRAMES 帧一致(帧态门帧不计数)才确认真回退采新——N 推导见常量注。
    _pend = dict(getattr(session, 'star_pending_regression', {}) or {})
    _tracked_bench_now = game_state_of(session).tracked_books.bench
    # 名级锚比较:每名只取**最高读星**对**最高旧星(锚定星)**仲裁一次。
    # 旧实现按 (名,星) 对逐副本比较——同名 1/2/3★ 三副本并存时,2★/1★
    # 真实副本各被判一次「回退」并连环触发误抬(run_20260915_054718 §5
    # 实锤形态);锚定语义 = 名下最高确认星不因低读帧洗掉。
    for _n in sorted({n for n, _ in _new_stars}):
        _s = max(s for n, s in _new_stars if n == _n)
        _old_s = max((_os for _on, _os in _old_stars if _on == _n), default=None)
        if _old_s is not None and _s < _old_s:
            # 银狼升费机制豁免:银狼LV.999 3★拖上场→变4费1★(升费签名
            # =2★→1★×2-3 与 3★→2★ 成对同刻,文档记载的正常机制,非识别失败);
            # merge 修复实证不消银狼回退(48条/224局全为机制性),豁免防每2局误停一次
            if _n.startswith('银狼') and _old_s - _s == 1:
                log.info(f'[cw][{source}] star 回退豁免:{_n} {_old_s}★→{_s}★(升费机制,非识别失败)')
                continue
            # 帧态门(ADR-0420)前置到每一降级读帧:星爆动画/拖拽过渡窗可
            # 持续 ≥2 帧,特效帧 = 物理不可信窗——保旧并**计数冻结不推进**
            #(非清零——动画结束后的干净回退帧仍走计数分支确认;门漏检时
            # 退化为纯防抖行为)。旧实现只在第 2 帧起判门,窗内第 1 帧会
            # 占计数,与「特效帧读数不进证据」语义不符。
            if screen is not None and _IS_MERGE_EFFECT_FRAME is not None \
                    and _IS_MERGE_EFFECT_FRAME(screen):
                log.info(f'[cw][{source}] star 回退帧态门:{_n} {_old_s}★→{_s}★'
                         f'(合成特效帧,读数不可信)→ 保旧 {_old_s}★,防抖冻结')
                _conflict('star', _old_s, _s, screen,
                          verdict='保旧-合成特效帧态门(采新确认被拦,防抖冻结;'
                                  'W292/ADR-0420)',
                          source=source, char=_n)
                _hold_star_read(_tracked_bench_now, bench, deployed,
                                _n, _old_s)
                continue
            _seen = _pend.get(_n, 0) + 1
            _pend[_n] = _seen
            if _seen < STAR_DOWNGRADE_CONFIRM_FRAMES:
                # 防抖窗:疑星读抖动/动画窗尾——不写回,star 保旧防毒化;
                # 连续计数达标前读回正常即自愈(离场/恢复分支清计数)。
                log.info(f'[cw][{source}] star 回退防抖:{_n} {_old_s}★→{_s}★'
                         f'(疑同名多星星读抖动/动画窗)→ 本帧保旧 {_old_s}★,'
                         f'连续 {_seen}/{STAR_DOWNGRADE_CONFIRM_FRAMES}')
                _conflict('star', _old_s, _s, screen,
                          verdict=(f'保旧-回退防抖(疑星读抖动,'
                                   f'{_seen}/{STAR_DOWNGRADE_CONFIRM_FRAMES},'
                                   f'下帧确认)'),
                          source=source, char=_n)
                _hold_star_read(_tracked_bench_now, bench, deployed,
                                _n, _old_s)
            else:
                # 连续 N 帧一致:确认真回退(卖后重买/持续性遮挡/真识别
                # 问题)→ 采新写回(超额证据门,推导见常量注)。确认即
                # 消费本段连续计数(episode 收口;读回恢复分支仍会兜底清)。
                _pend.pop(_n, None)
                log.warning(f'[cw!][{source}] star 回退确认:{_n} {_old_s}★→{_s}★'
                            f'(连续{_seen}帧一致,超额证据)')
                _conflict('star', _old_s, _s, screen,
                          verdict=(f'采新-回退确认(连续{_seen}帧一致)'),
                          source=source, char=_n)
                # ⚖️ star 回退留证(排查结论存档 cw_dev/live_round11_diagnosis.md
                # :根因在 SIFT 身份域,非读星;降级为高频留证——每 5 次回退存
                # 一张证,不 stop,排查证据流保留。SIFT 身份修复后本段连同
                # _star_stop_hook 删)。
                # 钩子归位:留证调用经**队列记录**——真正落盘由 director 对账位
                # 统一触发(消费统一观察;帧态门在 _star_stop_hook
                # 内,双层保护)。reconcile 只登记,不做 IO。
                if _old_s >= 2:
                    _reg[_n] = _reg.get(_n, 0) + 1
                    _pending_evidence.append((_n, _old_s, _s, source))
        elif _n in _pend or _n in _reg:
            _pend.pop(_n, None)   # 读回恢复(或超预估)→ 清防抖(自愈;pop 而非 del——
            # 名字可能只在 _reg 不在 _pend,del 抛 KeyError 会打断备战环,实锤 丹恒·饮月)
            _reg.pop(_n, None)   # 连续回退计数同步清零(恢复语义)
    # 离场清除 pending(角色卖出/上场后 _pend 残留 → 该角色下次登场时
    # 单次动画误读被误判「连续第二次确认」)。只在两侧都真读(非 None)时清 —— None 侧
    # 读失败不代表离场。双空读已在上方守卫早退,这里 old 非空 + 双真读 = 真离场。
    if _pend and bench is not None and deployed is not None:
        _gone = [n for n in _pend if n not in {x for x, _ in _new_stars}]
        for n in _gone:
            del _pend[n]
    session.star_pending_regression = _pend
    game_state_of(session).exec_books.star_regression = _reg
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
    # 钩子归位——「对账&hook」位统一消费留证
    # 队列(原 reconcile 深处散调;计数节流每 5 次留一张不变,
    # _star_stop_hook 内帧态门保留=双层保护)。
    for _n, _o_s, _s, _src in _pending_evidence:
        if _reg.get(_n, 0) >= 2 and ctx is not None and _reg[_n] % 5 == 0:
            _star_stop_hook(ctx, session, _n, _o_s, _s, screen, _src,
                            stop_run=False)
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
    职责由 gs.hp 结算覆盖写端 + carried 语义承载(行为变化登记
    design §1.3:失读窗不再有锚补,实机识别失准走识别优化批)。

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
        prior = (opening_hp_prior(
            getattr(session, 'briefing_affixes', None),
            getattr(session, 'selected_difficulty', ''),
            getattr(session, 'enemy_difficulty', None))
            if session is not None else None)
        if prior is not None:
            log.info(f'[cw][{source}] hp 开局无真值 → 初值表先验 {prior}'
                     f'(词缀={sorted(set(getattr(session, "briefing_affixes", None) or []))};'
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


def _star_stop_hook(ctx, session, char: str, old_star: int, new_star: int,
                    screen, source: str, stop_run: bool = True) -> None:
    """star 回退留证钩子(用户指示;star≥2 回退触发)。

    留证模式:排查已尽策略侧所能(结论存 cw_dev/live_round11_diagnosis.md:
    根因在 SIFT 身份域,非读星)——stop_run=False 时只留证截图不停机(证流保留,
    实跑可推进);SIFT 身份修复后本段整删。
    停机保备战画面供排查星级识别(read_star 漏金星?星区被特效/光标遮挡?SIFT 身份错配?)。
    sentinel 自描述(教训:内容含「这是自己的钩子停的+删除位置」,防误判孤儿/外部拦截)。
    帧态门:留证/停机只在备战类精准帧(is_prep_like_frame)
    ——动画帧上的星读回退本就常发(升星特效窗),不留证。
    """
    from datetime import datetime
    from pathlib import Path

    from one_dragon.utils import log_utils
    try:
        # 帧态门:非备战类精准帧直接跳过(动画帧星读回退
        # 常发,留证只是噪声)。screen=None(测试/无帧上下文)
        # 不拦——留证本身是离线安全操作。
        if screen is not None:
            from sr_od.application.currency_war.kernel.cw_obs_core import (
                is_prep_like_frame,
            )
        if screen is not None and ctx is not None \
                and not is_prep_like_frame(ctx, screen):
            return
        _p = Path('.debug/temp/currency_war/star_regression_hook.flag')
        _p.parent.mkdir(parents=True, exist_ok=True)
        _p.write_text(
            f'[{datetime.now().isoformat(timespec="seconds")}] star 回退{"停机" if stop_run else "留证(r17 降级,不阻断)"}——'
            f'{char} 预估 {old_star}★(买牌 3合1 merge)多次读回 '
            f'{new_star}★,星级/身份识别可疑。\n'
            f'处理流程(r100k 补):\n'
            f'1. 对截图 shots/star_regress_{char}_*.png 肉眼核星级(金框/角标);\n'
            f'2. ①星读对预估错(merge 逻辑)→ 修 cw_reconcile 预估;②星读错(read_star)\n'
            f'   → 核星区遮挡/光标;③SIFT 身份错配 → 核 portrait 模板;\n'
            f'3. 修好后删钩子:cw_reconcile.py 搜「_star_stop_hook」整段 + 删本 flag。\n'
            f'画面态:备战(角色在板上,星区可见);来源:{source}',
            encoding='utf-8')
        try:
            # 截图留证经注入槽(cv2 落盘实现迁 app 装配
            # 模块,kernel 保持纯逻辑;缺省关 = 不落截图只写 flag)。
            _saver = _STAR_EVIDENCE_SAVER
            if _saver is not None and screen is not None and screen.size:
                _saver(screen, char)
        except Exception:  # noqa: BLE001  截图 best-effort
            pass
        log_utils.log.warning(
            f'[cw-hook] star 回退{"停机" if stop_run else "留证(r17 降级,不阻断)"}:'
            f'{char} 预估{old_star}★×多节点读回{new_star}★ → '
            f'保画面排查星级识别(sentinel: star_regression_hook.flag;修好删 _star_stop_hook)')
        if stop_run:
            ctx.run_context.stop_running(reason='hook:star_regression')
    except Exception:  # noqa: BLE001  停机失败不阻塞对账写回
        pass
