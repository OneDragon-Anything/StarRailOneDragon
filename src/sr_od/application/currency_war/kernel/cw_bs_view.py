"""BoardState → GameState 消费适配器(迁移批次二;字段级详设(迭代期) =
``docs/develop/sr_od/application/currency_war/changes/2026-09-11-unified-state/
details/BoardState-数据结构设计.md`` §8.7 批次二(正本入口=game_state/README.md);
透传域收编设计正本 = ``docs/develop/sr_od/application/currency_war/
changes/2026-09-06-redesign/w5-透传域建模方案.md``)。

**本模块是什么**:策略器决策输入的切换载体——旧读取对象
(``session.last_state`` 原始观察帧)转 BoardState 适配层:对已建模域,
值取自 BoardState 单例(经 :func:`cw_observation._feed_board_state` /
备战装配环席位写端 / sim 合成口逐帧喂入,来源两态带 evidence);对
尚未建模域,显式透传入参帧(各域有"不入 BoardState 记录模型"的显式
理由,见下方清单)。返回值 = 标准 :class:`GameState`(形状兼容,消费方
零改动)。

**等价性语义(行为等价门)**:
- 已建模域:BoardState 值由同一观察漏斗镜像而来,常态帧与旧直读
  逐位一致;失读帧按 §2.2 记录模型语义返回沿用值(carried)而非原始帧
  的兜底值(raw 0/启发式值)——「同函数同输入序下更诚实的输入」申报面,
  回放语料(无 OCR 失读)逐位零差;
- payload 域(shop/refresh_probs)例外:**无值 = 结构离屏,返回空牌面,
  禁透传入参帧旧牌面**(残留会把离屏帧误读成「商店仍开着」,决策买牌
  空转);开店态 OCR 失读帧容器保持上一开店帧旧牌面(喂入口失读不写),
  视图如实返回该沿用牌面——与「帧实读空表→决策保守跳过」的旧形态是
  申报过的行为差(失读窗内发射买牌由执行侧核对兜底)。

**域清单**(建模收编状态,各域理由/边界申报):
- hp(W5 专项):视图供**门前真值**(记录/消费分离)——``st.hp`` =
  BoardState.hp 值(含 carried 沿用;无值透传帧引导窗);
  ``hp_readable`` = ``bs.hp.source == 'observation'``(**最近观察**语义:
  真读或结算覆盖,ADR-0282 两来源 True 时可信度等同真读的如实化——
  结算覆盖帧 readable=True 属非常态帧行为差申报);``hp_trusted`` =
  来源映射(observation/carried→True,prior/logic→False;与现役
  real_read/same_node_carried 词表一一同构,ADR-0431 帧龄门语义)。
  消费侧施门 = 策略实现层(gated_hp)在**读点**显式施(mandate adapter
  decision_state / encounter λ 键读点;kernel 不可反向依赖策略实现),
  session 政策窗口径(gap==1 / 不可信放宽 gap≤3)不变。
- bench/deployed(席位):容器值收编(BenchView→槽位表 /
  front_row+back_row→deployed 槽表,换算单一源在 kernel/cw_board_state
  映射层);观察写端 = 备战装配环(防 SIFT 双跑,漏斗声明修订见
  cw_observation._feed_board_state)。
- deploy_cap:容器识别真值(ADR-0420 采信门输出;与 back_layout 双存
  属 §8.8 在册例外,字段注释见 BoardState.deploy_cap)。
- shop/refresh_probs:payload 收编(离屏语义见上);牌转换 = 双 ShopCard
  归一映射单一源(kernel/cw_board_state.shop_cards_to_legacy,x 置 0 不
  消费——执行侧 buy 发射从 screen_info 现取)。
- active_env/plane_bosses/enemy_affixes/equips:容器值收编,无值透传帧
  引导窗(equips 观察写端 = 装备分配链装备区现读 + 载体中继兜底,
  接线滞后窗值冻结申报见喂入口 equips 段)。
- front_max:常量供数(DEPLOYED_FRONT_CAPACITY,恒 4 非观察事实);
- back_max:容器动态真值供数(W5 §2.3 定谳 + back_max 语义裁决四闸门:
  读 ``bs.back_layout``——三信号裁决值,值域 6-9(平常 6,宝钻/召唤物
  扩展,上限 9,机制正本 = board_structure.md 量化公式节);9 档坐标
  未交互建档,建档前域外按 8 格超集运行 + evidence ``superset`` 标记。
  无值透传帧兜底引导窗——容器空壳期零行为变化,写端接线后自动携带
  真值(天然灰度)。写端 = obs 选档链 ``resolve_back_slots`` 容器接线
  + sim 合成口扩员;消费面 max_units 封顶 / back_overflow 阈值 /
  back_left 空位同读一个字段,供数切换后自动同源);
- dual_track_phase:透传保留(策略侧派生旗标,committed_from 权威经
  mandate adapter 装配回填;非游戏可观察事实不入容器,W6 消费切换时
  消费面改读派生函数);
- focus_factions:视图恒 None(与 dual_track_phase 同族——策略侧回填
  字段,真家 StrategyState;本视图不透传不建模,W6 处置执行侧回填点);
- board_next_tier(派生键:帧缺省时由 :func:`board_next_tier_of` 自
  BoardState.board 现算补齐)。

调用点数以批首 grep 清点为准(现树 src 直调 ``strategy_input_state``
15 处 + ``game_state_view`` 直调 1 处)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # 仅类型注解引用(项目规范);运行时经鸭子类型读字段,避免 kernel
    # 内部观录模块与 cw_state 建立运行时依赖环。
    from sr_od.application.currency_war.kernel.cw_board_state import BoardState
    from sr_od.application.currency_war.kernel.cw_state import GameState


def game_state_view(bs: BoardState, frame: GameState | None) -> GameState:
    """BoardState(主)+ 观察帧(透传兜底)→ GameState 消费视图。

    :param bs: BoardState 单例(= :func:`board_state_of(session)`;None
        时按裸帧透传构造——调用方无 session 形态的保守降级);
    :param frame: 入参观察帧(旧读取对象;通常 = ``session.last_state``
        或当帧 read_game_state 产物)。None → 透传域取 GameState 缺省。

    逐域规则见模块 docstring;每个已建模域的取值序 = BoardState 有值
    用之(含 carried 沿用值),否则透传入参帧(开局首帧前 BoardState
    未观察的引导窗)。
    """
    from sr_od.application.currency_war.kernel.cw_board_state import (
        board_next_tier_of,
    )
    from sr_od.application.currency_war.kernel.cw_state import (
        REFRESH_COST_BASE,
        GameState,
    )

    st = GameState()
    fr = frame if frame is not None else GameState()

    # —— 经济与成长(已建模)——
    if bs is not None and bs.gold.value is not None:
        st.gold = int(bs.gold.value)
        # prior(开局先验)= 非真读,readable False(§3.1.6 形态);其余
        # 来源(observation/logic/carried)= 已知真值,readable True
        #(失读帧沿用值的 readable 语义 = 记录模型申报面,模块 docstring)。
        st.gold_readable = bs.gold.source != 'prior'
    else:
        st.gold = fr.gold
        st.gold_readable = getattr(fr, 'gold_readable', True)
    if bs is not None and bs.level.value is not None:
        st.level = int(bs.level.value)
        # 启发式兜底帧的 level 不入 BoardState(喂入口 carry 门),故
        # BoardState 有值即真读值;透传帧分支才可能带兜底值。
        st.level_readable = True
    else:
        st.level = fr.level
        st.level_readable = getattr(fr, 'level_readable', True)
    if bs is not None and bs.xp.value is not None:
        st.xp_progress = tuple(bs.xp.value)
    else:
        st.xp_progress = fr.xp_progress
    if bs is not None and bs.streak.value is not None:
        st.streak = int(bs.streak.value)
    else:
        st.streak = fr.streak
    # hp(W5 专项):视图供**门前真值**(记录/消费分离,施门迁消费侧)。
    # 旧链在写侧预施门(last_state.hp = gated_hp 门后值,单写者纪律
    # ADR-0583 §2.4「消费方必须同门」),消费侧再施门 = 值二手化——本
    # 改动后门输入 = 容器真值,门在消费读点显式施(mandate adapter
    # decision_state / encounter λ 键读点;写侧门保留至旧链删除),
    # session 政策语义(gap 窗)原样。等价三支:①门参数同源(门本体与
    # session.last_hp/last_hp_t 不动);②真值同源(容器 observe/carry 与
    # 旧链 last_hp_real 同一观察漏斗,差异 = 沿用值带来源帧标注 +
    # 结算覆盖刷新方向,失读窗取更新值为申报的行为差);③门幂等(门后
    # 值再过门不变)。失败帧(无真值)透传帧引导窗。
    if bs is not None and bs.hp.value is not None:
        st.hp = int(bs.hp.value)
        # readable = **最近观察**语义(source=='observation' = 真读或结算
        # 覆盖,ADR-0282「两来源 True 时可信度等同真读」的如实化——结算
        # 邻接帧 readable=True 属非常态帧行为差申报);carried/prior 非
        # 本帧真读 → False。
        st.hp_readable = bs.hp.source == 'observation'
        # trusted = 来源映射(observation=真读含结算覆盖 / carried=同记录
        # 沿用链 → True;prior=先验 / logic=推算值(现无 hp 写端)→ False)。
        # 与现役帧位差异窗 = 跨节点沿用帧(旧帧位 False,本映射 True,
        # 值 = 最新已知真值)——失读帧行为差申报面。
        st.hp_trusted = bs.hp.source in ('observation', 'carried')
    else:
        st.hp = fr.hp
        st.hp_readable = getattr(fr, 'hp_readable', False)
        st.hp_trusted = getattr(fr, 'hp_trusted', False)
    if bs is not None and bs.level_up_cost.value is not None:
        st.level_up_cost = int(bs.level_up_cost.value)
    else:
        st.level_up_cost = fr.level_up_cost
    # 刷新费消费策略(§3.3.4 申报:None=未读到,消费端按建模基价显式
    # 默认——原 ``or 2`` 兜底形态的搬迁归宿,数值逐位一致;现场识别值
    # (ADR-0622)经 BoardState 进消费,免费帧不写保证不会出 0)。
    if bs is not None and bs.shop_refresh_cost.value is not None:
        st.shop_refresh_cost = int(bs.shop_refresh_cost.value)
    else:
        st.shop_refresh_cost = REFRESH_COST_BASE

    # —— 节点(已建模;kind 未读帧继承语义在喂入口已处理)——
    _node = bs.node.value if bs is not None else None
    if _node is not None:
        st.plane = int(_node.plane)
        st.round_num = int(_node.round_num)
        st.node_type = str(_node.kind)
    else:
        st.plane = fr.plane
        st.round_num = fr.round_num
        st.node_type = fr.node_type

    # —— 局级事实(已建模域)——
    if bs is not None and bs.board.value is not None:
        st.board = dict(bs.board.value)
        st.board_readable = True
    else:
        st.board = dict(fr.board)
        st.board_readable = getattr(fr, 'board_readable', True)
    if bs is not None and bs.enemy_difficulty.value is not None:
        st.enemy_difficulty = int(bs.enemy_difficulty.value)
        # live 位=本帧现场真读(喂入口仅 live 帧才 observe);沿用帧
        # (carried)在旧链 live=False,同语义。
        st.enemy_difficulty_live = bs.enemy_difficulty.source == 'observation'
    else:
        st.enemy_difficulty = fr.enemy_difficulty
        st.enemy_difficulty_live = getattr(fr, 'enemy_difficulty_live', False)
    if bs is not None and bs.active_strategies.value is not None:
        st.active_strategies = list(bs.active_strategies.value)
    else:
        st.active_strategies = list(fr.active_strategies)
    if bs is not None and bs.selected_difficulty.value is not None:
        st.selected_difficulty = str(bs.selected_difficulty.value)
    else:
        st.selected_difficulty = fr.selected_difficulty

    # —— 派生键补齐(帧缺省时由 BoardState.board 现算,ADR-0488 同源)——
    st.board_next_tier = dict(getattr(fr, 'board_next_tier', None) or {})
    if not st.board_next_tier and st.board:
        st.board_next_tier = board_next_tier_of(st.board)

    # —— W5 收编域(容器值优先,无值透传帧引导窗;payload 域离屏例外)——
    from sr_od.application.currency_war.kernel.cw_board_state import (
        bench_slots_to_legacy,
        shop_cards_to_legacy,
        unit_rows_to_deployed,
    )
    from sr_od.application.currency_war.kernel.cw_state import (
        DEPLOYED_FRONT_CAPACITY,
    )
    # 席位(bench/deployed):观察写端 = 备战装配环(见模块 docstring);
    # 换算单一源 = kernel 映射层,消费形状零变化(定长槽表 + None 填充)。
    if bs is not None and bs.bench.value is not None:
        st.bench = bench_slots_to_legacy(bs.bench.value)
    else:
        st.bench = list(fr.bench)
    if bs is not None and (bs.front_row.value is not None
                           or bs.back_row.value is not None):
        st.deployed = unit_rows_to_deployed(
            list(bs.front_row.value or []),
            list(bs.back_row.value or []))
    else:
        st.deployed = list(fr.deployed)
    # deploy_cap:容器识别真值(ADR-0420 采信门输出);无值透传帧引导窗。
    if bs is not None and bs.deploy_cap.value is not None:
        st.deploy_cap = int(bs.deploy_cap.value)
    else:
        st.deploy_cap = fr.deploy_cap
    # shop/refresh_probs(payload 域,**离屏禁帧兜底**):容器无值 = 结构
    # 离屏 → 空牌面/None,透传旧牌面会把离屏帧误读成「商店仍开着」;
    # 开店态失读帧 = 容器沿用上一开店牌面(喂入口失读不写),行为差申报
    # 见模块 docstring。牌转换 = 双 ShopCard 归一映射单一源;x/merge_
    # preview 两执行/读取器域字段按同帧下标对齐透传(失配窗置 0,申报见
    # 映射函数)。
    _bs_payload = bs.shop.value if bs is not None else None
    if _bs_payload is not None:
        st.shop = shop_cards_to_legacy(list(_bs_payload.cards),
                                       frame_cards=list(fr.shop))
        st.refresh_probs = (dict(_bs_payload.refresh_probs)
                            if _bs_payload.refresh_probs else None)
    else:
        st.shop = []
        st.refresh_probs = None
    # 开局域/词缀/装备(容器值收编,无值透传帧引导窗)。
    if bs is not None and bs.active_env.value is not None:
        st.active_env = str(bs.active_env.value)
    else:
        st.active_env = fr.active_env
    if bs is not None and bs.plane_bosses.value is not None:
        st.plane_bosses = list(bs.plane_bosses.value)
    else:
        st.plane_bosses = list(fr.plane_bosses)
    if bs is not None and bs.enemy_affixes.value is not None:
        st.enemy_affixes = list(bs.enemy_affixes.value)
    else:
        st.enemy_affixes = list(fr.enemy_affixes)
    if bs is not None and bs.equips.value is not None:
        st.equips = list(bs.equips.value)
    else:
        st.equips = list(fr.equips)
    # front_max = 常量供数(恒 4,非观察事实,不立字段派生直接取常量);
    # back_max = 容器动态真值(W5 §2.3 定谳 + back_max 语义裁决·闸门一):
    # 供数读 bs.back_layout(三信号裁决值,值域 6-9;9 档未建档前域外由
    # 8 格超集 + superset 标记承载),无值透传帧兜底引导窗——容器空壳期
    # 零行为变化(天然灰度),写端接线后自动携带真值。禁退回「恒透传帧」:
    # 容器有值时帧值是旧观察残留,退回即「链按 6 格自洽地错」复发。
    st.front_max = DEPLOYED_FRONT_CAPACITY
    if bs is not None and bs.back_layout.value is not None:
        st.back_max = int(bs.back_layout.value)
    else:
        st.back_max = fr.back_max
    # dual_track_phase:透传保留(策略侧派生旗标,adapter 装配回填为权威
    # 读法;W6 消费切换时消费面改读 committed_from 派生函数)。
    st.dual_track_phase = getattr(fr, 'dual_track_phase', False)
    return st


def strategy_input_state(session) -> GameState:
    """策略决策输入状态(消费切换调用面的**单一源**,迁移批次二)。

    = ``game_state_view(board_state_of(session), session.last_state)``:
    旧形态 ``session.last_state or GameState()`` 的逐点替换形态——事件屏
    pick 族/flow 结算半等策略输入点统一经本口取值,迁移计数按本函数的
    调用点清点。session 为 None(局外/裸调用)→ 空态视图(与旧
    ``or GameState()`` 分支同语义)。
    """
    if session is None:
        return game_state_view(None, None)
    from sr_od.application.currency_war.kernel.cw_board_state import (
        board_state_of,
    )
    return game_state_view(board_state_of(session),
                           getattr(session, 'last_state', None))
