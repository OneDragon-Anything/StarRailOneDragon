"""货币战争**备战画面**额外识别器(per-screen recognizer)。

``analyze_screen`` 精准命中「货币战争-备战」后,框架按 ``screen_name`` 查表调用本识别器,把备战画面的
结构化领域事实(金币 / 阶段 / 血量 / 连胜 / 部署数 / 阵营在场人数)塞进返回的 ``extras``,供智能体 /
HTTP 消费方直接读用,不必自己 OCR / 看图。

**并发安全(关键)**:本 ``recognize`` 必须是**纯读** —— 不写 ``self.``、不写任何模块全局、不读写
``cw_match.session``。原因:``analyze_screen`` 是观察类 tool,可在某 CW operation **运行期间**被并发调用
(观察类不查 run_slot);若本识别器写了 operation 也在用的可变状态,会互相污染。故:
- gold / hp / streak / deploy / board 复用 ``cw_observation`` 的**纯 reader**(它们不写全局 / session);
- **phase 不复用 ``read_phase_round``**(它成功时写模块全局 ``_last_phase_round`` 的 last-known-good 兜底,
  会与 operation 竞争污染兜底值)→ 本模块自写 ``_read_phase_round_pure``(只 OCR + 正则,不缓存,读不到返 None);
- **不复用 ``read_game_state``**(它读写 ``cw_match.session.last_level_obs`` / ``tracked_deployed``,是 session 状态)。

**角色身份 + 星级 + 装备(前后台 / 备战席)**:用 ``cw_identity_obs.read_deployed_rows`` / ``read_bench_view``
(纯 CV SIFT,**纯读** —— 只裁槽位 + SIFT + 直产容器形状,不写 session / 全局,可安全并发)产
``front_line`` / ``back_line``(前排/后排 Unit 行)与 ``bench``(:class:`BenchView` 备战席容器
视图,占槽物品 kind 识别期细分)。立绘库经
``ensure_portrait_templates`` **幂等加载缓存**(只读资源,并发安全,同 ``ensure_equip_tm_templates``);
库缺失→三字段 None。装备经 ``read_row_equipped`` 读 below-avatar icon,按 slot 注入 Unit.equips
(frozen replace 新构造;备战席无 below icon→bench unit equips 恒 [])。

⚠️ **可靠性标注**:立绘库 ``currency_war/portrait_plaza``(官方 plaza 烘焙)实测可用 —— D-22(2026-08-09,
手采库时代)有角色槽 6/6 命中空槽不误;切 plaza 库时 A/B 对拍持平(14 vs 15,一致 13);2026-08-16
M34 live(CwOpEquipAll 身份)通过。消费方据该字段时仍知其 SIFT 来源(非 OCR),供智能体交叉验证而非盲信
(证据链见 ``currency_war_char_id`` docstring)。
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, replace
from typing import TYPE_CHECKING

from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from sr_od.application.currency_war.data.cw_equipment_data import get_equip
from sr_od.application.currency_war.kernel.cw_game_state import BenchView, Unit
from sr_od.application.currency_war.kernel.cw_obs_core import (
    A_PHASE,
    SCREEN_NAME,
    _area_rect,
    _ocr,
)
from sr_od.application.currency_war.obs.cw_equipment import (
    ensure_equip_sift_templates,
    ensure_equip_tm_templates,
    read_equips,
)
from sr_od.application.currency_war.obs.cw_identity_obs import (
    ensure_portrait_templates,
    read_bench_view,
    read_deployed_rows,
    read_ore_sights,
    read_row_equipped,
    read_supply_boxes,
)
from sr_od.application.currency_war.obs.cw_observation import (
    read_board,
    read_deploy_cap,
    read_deployed_count,
    read_gold,
    read_hp_opt,  # r317:模块级(monkeypatch 打桩按模块属性)
    read_level,
    read_streak,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext


def _read_phase_round_pure(ctx: SrContext, screen: MatLike) -> tuple[int, int] | None:
    """位面 + 轮次(**纯读**):顶栏「X-Y」(如 "1-3" = 位面1 第3轮);读不到 → None。

    与 ``cw_observation.read_phase_round`` 同解析,但**去掉**模块全局 ``_last_phase_round`` 的写 / 读
    (并发安全:recognizer 不得与运行中 operation 竞争该全局)。读不到时返 None(不伪造 (1,1) 兜底)。

    Args:
        ctx: 运行上下文(经 ``cw_obs_core._area_rect`` / ``_ocr`` 读 ``区域-阶段`` area)。
        screen: 备战画面截图。

    Returns:
        ``(plane, round_num)``;OCR 读不到返 None。
    """
    blob = ''.join(r.data for r in _ocr(ctx, screen, _area_rect(ctx, A_PHASE)))
    m = re.search(r'(\d)\s*-\s*(\d)', blob)         # "1-3"
    if m:
        return int(m.group(1)), int(m.group(2))
    plane_m = re.search(r'第\s*(\d)\s*位面', blob)
    if plane_m:
        return int(plane_m.group(1)), int(plane_m.group(1))
    digits = re.findall(r'\d', blob)
    if digits:
        return int(digits[0]), int(digits[0])
    return None


@dataclass
class _BattlePrepState:
    """备战画面领域事实(组装后 ``asdict()`` 转 dict 回传;类型化单一真相源)。

    字段类型对齐各 reader 的返回类型(gold/hp 有安全默认故非 Optional;phase/deploy/streak 读不到为 None)。
    角色槽位复用容器形状(P6 直产:front_line/back_line = Unit 行,bench = BenchView),不另建模型;
    阵营不入形状(消费点经注册表按 char_id 派生)。
    """

    gold: int                       # 当前金币(read_gold,读不到→0,安全保守)
    phase: tuple[int, int] | None   # (位面, 轮次);读不到→None(不伪造)
    hp: int | None                   # 小队剩余血量(read_hp_opt,读不到→None;r317 同源 director)
    streak: int | None              # 连胜/连败 magnitude(read_streak,读不到→None)
    deploy_count: int | None        # 已部署角色数(read_deployed_count,读不到→None)
    deploy_cap: int | None          # deploy cap 真值(read_deploy_cap,读不到→None)
    level: int                      # 团队规模等级(read_level,Lv.N;cap>level=钻石/宝钻加成)
    board: dict[str, int]           # {阵营名: 在场人数}(read_board)
    front_line: list[Unit] | None  # 前排 Unit 行(SIFT 身份 + read_star 星级 + read_row_equipped 装备按 slot 注入 equips;templates 未加载→None)
    back_line: list[Unit] | None   # 后排 Unit 行(同上)
    bench: BenchView | None        # 备战席容器视图(read_bench_view SIFT 直产;slots=9 槽 BenchSlot,占位物品 kind 细分;备战席无 below icon→unit equips 恒 [];空读→None)
    owned_equips: list[dict] | None      # 右侧 owned 装备栏(read_equips SIFT;元素 {name,category,cx,cy,inliers};category 工具/特殊=消耗品,其余简易/进阶/...=装备;空→None;templates 未加载→None)
    supply_boxes: list[dict] | None      # 备战栏补给箱槽位(read_supply_boxes TM;元素 {slot,cx,cy};晶矿开箱掉箱占席,点「开启」腾槽;空→None;2026-08-14 首见机制)
    reward_ores: list[dict] | None    # 奖励面板晶矿(read_ore_sights HoughCircles;元素 {color,cx,cy,r};color gold/blue/gray;采晶矿开启入账,角色/箱占席;空→None;2026-08-14 首见机制)


class BattlePrepRecognizer(ScreenRecognizer):
    """货币战争备战画面额外识别器(首个 per-screen recognizer 消费者)。"""

    screen_name: str = SCREEN_NAME   # '货币战争-备战'

    # extras 字段说明(随 analyze 响应平级返回 extras_doc;键集与 _BattlePrepState 一致)
    extras_doc: dict[str, str] = {
        'gold': '当前金币(int;读不到→0,安全保守默认)',
        'phase': '(位面, 轮次) 二元组,如 [1,3] = 位面1 第3轮;读不到→None(不伪造)',
        'hp': '小队剩余血量(int|None;读不到→None 与 director 同源;r317)',
        'streak': '连胜/连败 magnitude(int;读不到→None)',
        'deploy_count': '已部署角色数(int;读不到→None)',
        'deploy_cap': '部署上限真值(int;>level 表示钻石/财富宝钻加成 +1 团队槽;读不到→None)',
        'level': '团队规模等级 Lv.N(int;cap>level=钻石/宝钻加成)',
        'board': '{阵营名: 在场人数} dict(OCR 左面板)',
        'front_line': '前排 Unit 行 list(元素 Unit dict: char_id/star/equips/slot;'
                      'char_id=规范名,slot=排内 1 基画面槽号,equips=装备名 list)。SIFT 立绘识别,'
                      '供智能体交叉验证而非盲信(证据链见 currency_war_char_id);'
                      'templates 未加载→None',
        'back_line': '后排 Unit 行 list(同 front_line 结构;templates 未加载→None)',
        'bench': '备战席容器视图 dict(BenchView:slots=9 元素 BenchSlot dict'
                 '{kind: unit/supply_box/tome/bookcard/empty, unit: Unit dict 或 null}'
                 '+ capacity=9;unit 槽元素 = char_id/star/equips/slot,备战席无 below icon→equips 恒 [];'
                 '占位物品槽 kind 识别期细分;空读→None)',
        'owned_equips': '右侧 owned 装备栏 list(read_equips SIFT;元素 {name,category,cx,cy,inliers};'
                        'category 工具/特殊=消耗品,其余简易/进阶/特权/星徽/白昼/命运/骇客=装备;'
                        'cx/cy=1080p 原图绝对坐标(点该坐标开对应物品详情);空→None;templates 未加载→None)',
        'supply_boxes': '备战栏补给箱 list(read_supply_boxes TM;元素 {slot,cx,cy},cx/cy=开启按钮中心'
                        '(点它开箱腾席);奖励球(晶矿)开启可能掉箱占 1 备战席槽;空→None',
        'reward_ores': '奖励面板晶矿 list(read_ore_sights HoughCircles;元素 {color,cx,cy,r},'
                          'color=gold/blue/gray,cx/cy=采晶矿坐标;通关奖励节点后出现;席满点不动(先开箱腾席);空→None',
    }

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,   # noqa: ARG002  命中画面 ScreenInfo;本识别器经 cw_obs_core 读 area,暂未直接用
    ) -> dict | None:
        """读备战画面的经济 / 阵营领域事实 → dict(纯读,见模块 docstring 并发安全说明)。

        Args:
            ctx: 运行上下文。
            image: 备战画面截图(analyze 已截,复用)。
            screen_info: 命中画面的 ScreenInfo(经 ``cw_obs_core._area_rect`` 读 area pc_rect)。

        Returns:
            ``_BattlePrepState`` 的 dict 视图;字段含义见 ``_BattlePrepState``。
        """
        # 装备(slot_idx → 装备名;先读,再注入 Unit.equips)。备战栏 below 不读(未上阵无 icon,机制恒空,
        # 读只产假 MISS 噪声 — 某模板 val 0.55-0.56,shot miss_slot5 实证无 icon)。
        phase0 = _read_phase_round_pure(ctx, image)
        level0 = read_level(ctx, image, phase0[0], phase0[1]) if phase0 else read_level(ctx, image, 0, 0)
        # 后排装备槽按 cap 差公式选档(W209/口述「后台格数=6+(cap−level)」;
        # 旧 level 驱动已废)。已建档 6/7/8/9 直读,>9 域外保守 8 格超集(select_back_layout 内辖留证)。
        from sr_od.application.currency_war.obs.cw_back_layout import (
            select_back_layout as _sel_bl,
        )
        _back_n, _back_pfx = _sel_bl(ctx, image, level=level0)
        templates = ensure_portrait_templates(ctx)  # 幂等加载缓存(并发安全,同 ensure_equip_tm_templates);保证 analyze 产角色
        equip_grays = ensure_equip_tm_templates(ctx)
        front_equips = read_row_equipped(ctx, image, equip_grays, '前排', 4) if equip_grays is not None else {}
        # 布局未知态(15 号稿 §3.2④,select_back_layout 返 (None,''))→ 后排
        # equips 空 dict(纯读面,跳过即正确;JSONL 留证在 resolve 侧)。
        back_equips = (read_row_equipped(ctx, image, equip_grays, _back_pfx, _back_n)
                       if (equip_grays is not None and _back_n) else {})
        # 角色直产容器形状(read_deployed_rows 已按排分域);只补 equips
        #(按 slot 对齐注入;Unit frozen → replace 新构造)。
        front_line: list[Unit] | None = None
        back_line: list[Unit] | None = None
        bench: BenchView | None = None
        if templates is not None:
            front_row, back_row = read_deployed_rows(ctx, image, templates, level=level0)
            front_line = ([replace(u, equips=front_equips.get(u.slot, []))
                           for u in front_row] or None)
            back_line = ([replace(u, equips=back_equips.get(u.slot, []))
                          for u in back_row] or None)
            _bv = read_bench_view(ctx, image, templates)
            # 备战席无 below icon → unit equips 保持 [];空读(零占用)→ None
            bench = (_bv if (_bv is not None
                             and any(s.kind != 'empty' for s in _bv.slots)) else None)
        # owned 装备栏(右侧 区域-道具装备,read_equips SIFT;装备+消耗品混排,返名+位置,category 区分装备 vs 消耗品)
        # 前置契约:本 recognizer 仅在「货币战争-备战」画面识别命中后生成 extras,
        # 输入帧已是干净备战(非干净不识别的判定在外层建档识别),read_equips 无画面守卫。
        sift_templates = ensure_equip_sift_templates(ctx)
        owned_equips: list[dict] | None = None
        if sift_templates is not None:
            _owned: list[dict] = []
            for eq_name, eq_pos, eq_inliers in read_equips(image, sift_templates):
                eq_info = get_equip(eq_name)
                _owned.append({
                    'name': eq_name,
                    'category': eq_info.category if eq_info is not None else '',
                    'cx': eq_pos[0],
                    'cy': eq_pos[1],
                    'inliers': eq_inliers,
                })
            owned_equips = _owned or None
        phase = phase0
        level = level0
        # W209/:cap>level(宝钻/钻石叠加)不再只是经济信息——它直接编码
        # 后排扩展量(口述公式 6+(cap−level)),布局选档已在函数头消费。
        # r317(批次2):read_hp 裸调用迁 read_hp_opt
        # (miss→None;与 director 同源——消掉「MCP 报 100 而
        # director gated=26」双真相)。extras 序列化 None→
        # 合法 null(backend json.dumps 预校验);extras_doc
        # 文案同步「读不到→None」。(模块级 import。)
        state = _BattlePrepState(
            gold=read_gold(ctx, image),
            phase=phase,
            hp=read_hp_opt(ctx, image),
            streak=read_streak(ctx, image),
            deploy_count=read_deployed_count(ctx, image),
            deploy_cap=read_deploy_cap(ctx, image),
            level=level,
            board=read_board(ctx, image),
            front_line=front_line,
            back_line=back_line,
            bench=bench,
            owned_equips=owned_equips,
            supply_boxes=([
                {'slot': idx, 'cx': p.x, 'cy': p.y} for idx, p in read_supply_boxes(ctx, image)
            ] or None),
            reward_ores=([
                {'color': c, 'cx': p.x, 'cy': p.y, 'r': r} for c, p, r in read_ore_sights(ctx, image)
            ] or None),
        )
        return asdict(state)
