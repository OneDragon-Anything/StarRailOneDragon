"""BoardState → GameState 消费适配器(迁移批次二;设计正本 =
``docs/develop/currency_war/design/BoardState-数据结构设计.md`` §8.7 批次二)。

**本模块是什么**:策略器决策输入的切换载体——旧读取对象
(``session.last_state`` 原始观察帧)转 BoardState 适配层:对已建模域,
值取自 BoardState 单例(经 :func:`cw_observation._feed_board_state` /
sim 合成口逐帧喂入,来源四分类带 evidence);对**未建模/执行域**,显式
透传入参帧(声明残差,退役归迁移批次四)。返回值 = 标准
:class:`GameState`(形状兼容,消费方零改动)。

**等价性语义(行为等价门)**:
- 已建模域:BoardState 值由同一帧的观察流镜像而来,常态帧与旧直读
  逐位一致;失读帧按 §2.2 记录模型语义返回沿用值(carried)而非原始帧
  的兜底值(raw 0/启发式值)——这是记录模型的核心语义,属于「同函数
  同输入序下更诚实的输入」的申报面,回放语料(无 OCR 失读)逐位零差;
- 透传域:值与旧形态逐位一致(同一入参帧原样搬运)。

**未建模/透传域清单**(批次二实况,批四退役时清零):hp(门权威随帧:
last_state.hp = gated_hp 门后消费值,BoardState.hp = 门前真值,消费施门
归策略侧 kernel 不可反向依赖——记录/消费分离,模块内 hp 注释)/
bench/deployed(席位身份识别在 PrepObservation/执行侧 SIFT,未入
BoardState 观察流)/deploy_cap(宝钻 cap=现场实时读值,§3.2.7 豁免显式
申报)/plane_bosses/enemy_affixes/active_env/equips(开局域与持久账本组
的画面写端挂建模批;当前经入参帧透传)/shop/refresh_probs(商店域决策
帧 = 波顶融合态 shop_state_frame,不是本适配器的辖域)/
board_next_tier(派生键:帧缺省时由 :func:`board_next_tier_of` 自
BoardState.board 现算补齐)。
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
    # hp = **帧透传**(显式申报,非疏漏):旧链 last_state.hp 是过
    # gated_hp 新鲜度门后的消费值(director 写门控值,cw_screen_prep
    # 单写者语义;r68 教训「消费方必须同门」= ADR-0583 §2.4),而
    # BoardState.hp 是记录模型真值(§2.2 门前观察,§3.5.1 结算覆盖),
    # 门 = session 政策(kernel 不可反向依赖策略实现)。记录归记录、
    # 消费归消费:决策视图的 hp 取帧值(门已施),BoardState 保留真值
    # 供归档/对账。
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

    # —— 透传域(未建模/执行域,批四退役时清零;清单见模块 docstring)——
    st.deployed = list(fr.deployed)
    st.bench = list(fr.bench)
    st.deploy_cap = fr.deploy_cap
    st.shop = list(fr.shop)
    st.refresh_probs = dict(fr.refresh_probs) if fr.refresh_probs else None
    st.active_env = fr.active_env
    st.plane_bosses = list(fr.plane_bosses)
    st.enemy_affixes = list(fr.enemy_affixes)
    st.equips = list(fr.equips)
    st.front_max = fr.front_max
    st.back_max = fr.back_max
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
