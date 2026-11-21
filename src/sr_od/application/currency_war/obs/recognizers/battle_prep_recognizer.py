"""货币战争**备战画面**额外识别器(per-screen recognizer)。

``analyze_screen`` 精准命中「货币战争-备战」后,框架按 ``screen_name`` 查表调用本识别器,把备战画面的
结构化领域事实(金币 / 阶段 / 血量 / 连胜 / 部署数 / 阵营在场人数)塞进返回的 ``extras``,供智能体 /
HTTP 消费方直接读用,不必自己 OCR / 看图。

**并发安全(关键)**:本 ``recognize`` 必须是**纯读** —— 不写 ``self.``、不写任何模块全局、不读写
``cw_match.session``。原因:``analyze_screen`` 是观察类 tool,可在某 CW operation **运行期间**被并发调用
(观察类不查 run_slot);若本识别器写了 operation 也在用的可变状态,会互相污染。故:
- gold / hp / streak / deploy / board 复用 ``cw_observation`` 的**纯 reader**(它们不写全局 / session);
- **phase 不复用 ``read_phase_round``**(它成功时写模块全局 ``_last_phase_round`` 的 last-known-good 兜底,
  会与 operation 竞争污染兜底值)→ 本模块自写 ``_read_phase_round_pure``(只 OCR + 共享解析纯函数
  ``parse_phase_round_text``,不缓存不写全局,读不到返 None);
- **不复用 ``read_game_state``**(它读写 ``cw_match.session.last_level_obs`` / ``tracked_deployed``,是 session 状态)。

**角色身份 + 星级 + 装备(前后台 / 备战席)**:用 ``cw_identity_obs.read_deployed_rows`` / ``read_bench_view``
(纯 CV SIFT,**纯读** —— 只裁槽位 + SIFT + 直产状态容器形状,不写 session / 全局,可安全并发)产
``front_line`` / ``back_line``(前排/后排 Unit 行)与 ``bench``(class:`BenchView` 备战席状态容器
视图,占槽物品 kind 识别期细分)。立绘库经
``ensure_portrait_templates`` **幂等加载缓存**(只读资源,并发安全,同 ``ensure_equip_tm_templates``);
库缺失→三字段 None。装备经 ``read_row_equipped`` 读 below-avatar icon,按 slot 注入 Unit.equips
(frozen replace 新构造;备战席无 below icon→bench unit equips 恒 [])。

**银轨商店入口(``rail_shop``)**:备战画面左侧上下文入口的「在场性 + 在场定位 + 开店
点击点 + 余额 + 胶囊在场性」。横幅左段**列车图案**带内 TM 匹配(:func:`find_rail_shop_train`
纯 CV 核心,搜索域 = 画面档「标识-银轨商店列车图案」带状 pc_rect —— 横幅 y 随羁绊
面板布局浮动,必须带内全搜而非定点)作在场识别锚;开店点击点 = 横幅「打开商店」
文本 OCR 锚中心(:func:`parse_rail_shop_banner`,横幅 = 入口按钮区,点文本即开面板;
菱形徽记锚定羁绊面板行位置浮动,不可当点击锚)—— 用户现场指导定谳:识别对列车图案
做模板匹配、开店点「打开商店」文本,别点菱形徽记。横幅带**先裁后 OCR 且 x 下限
排除列车图案**(含图案的宽带全图/先裁路径均漏检余额小字行「×N」、窄带两行全读出,
余额读数的生面前提)。三子状态(备战 /
商店面板开启 / 消费回备战)备战态横幅在场;商店未开张(开拓银轨 <2)不在场。商店
面板开启态横幅被面板盖住 → TM/OCR 无锚 → present=False/None(正确降级;该画面
不产 extras,识别面无消费)。胶囊 buyable 只回报胶囊在场性(游戏内触发语义未收敛:
现假设 = 商品池刚刷新出余额可负担的新商品,已实测否定「恒定可负担指示」,
待采样收敛 —— 见 ``PREP_EXTRAS_DOC``),False 态不产出(「确无胶囊」与「OCR 失读」
不可区分,统一 None)。OCR 端到端依赖 ctx,单测覆盖不到 —— 由实机 / 离线
analyze 验证兜底;列车图案纯 CV 核心与横幅/胶囊解析纯函数有 fixture 回归
(测试仓 ``test_battle_prep_recognizer.py``)。开拓商店浮层的**收店**点击仍锚
菱形徽记(画面档「标识-银轨商店徽记」,浮层态徽记在场而横幅被盖,唯一稳定锚;
见 ``cw_toggle_shop_panel``)。

⚠️ **可靠性标注**:立绘库 ``currency_war/character_avatar``(官方 plaza 烘焙)实测可用 —— D-22
(手采库时代)有角色槽 6/6 命中空槽不误;切 plaza 库时 A/B 交叉核对持平(14 vs 15,一致 13);实机对局实证:
plaza 烘焙立绘库经备战执行面身份链 live 验证通过(该执行面已停用)。消费方据该字段时仍知其 SIFT 来源(非 OCR),供智能体交叉验证而非盲信
(证据链见 ``currency_war_char_id`` docstring)。
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, replace
from typing import TYPE_CHECKING

import cv2
import numpy as np

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from one_dragon.utils.file_utils import get_project_root
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
    read_armory_boxes,
    read_bench_view,
    read_deployed_rows,
    read_ore_sights,
    read_row_equipped,
)
from sr_od.application.currency_war.obs.cw_observation import (
    parse_phase_round_text,
    phase_round_in_range,
    read_board,
    read_deploy_cap,
    read_deployed_count,
    read_gold,
    read_hp_opt,  # r317:模块级(monkeypatch 打桩按模块属性)
    read_level,
    read_level_up_cost,
    read_streak,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext


def _read_phase_round_pure(ctx: SrContext, screen: MatLike) -> tuple[int, int] | None:
    """位面 + 轮次(**纯读**):顶栏「X-Y」(如 "1-3" = 位面1 第3轮);读不到 → None。

    与 ``cw_observation.read_phase_round`` 共享解析纯函数
    (func:`cw_observation.parse_phase_round_text` +
    :func:`cw_observation.phase_round_in_range`,同正则同值域单一源;
    工具态 ``round_caps`` 恒 None → cap 回退默认长度
    P1=9,「1-10」断言对本工具面不作要求,修饰局真值由场字段/台账
    承载),但**去掉**模块全局 ``_last_phase_round`` 的写 / 读
    (并发安全:recognizer 不得与运行中 operation 竞争该全局)。
    数字回退分支(digit_fallback=True)随共享实现保留、行为不变。
    读不到时返 None(不伪造 (1,1) 兜底)。

    Args:
        ctx: 运行上下文(经 ``cw_obs_core._area_rect`` / ``_ocr`` 读 ``区域-阶段`` area)。
        screen: 备战画面截图。

    Returns:
        ``(plane, round_num)``;OCR 读不到/值域外返 None。
    """
    blob = ''.join(r.data for r in _ocr(ctx, screen, _area_rect(ctx, A_PHASE)))
    cand = parse_phase_round_text(blob, digit_fallback=True)
    if cand is not None and phase_round_in_range(cand):
        return cand
    return None


@dataclass
class _BattlePrepState:
    """备战画面领域事实(组装后 ``asdict()`` 转 dict 回传;类型化单一真相源)。

    字段类型对齐各 reader 的返回类型(gold/hp 有安全默认故非 Optional;phase/deploy/streak 读不到为 None)。
    角色槽位复用状态容器形状(P6 直产:front_line/back_line = Unit 行,bench = BenchView),不另建模型;
    阵营不入形状(消费点经注册表按 char_id 派生)。
    """

    gold: int                       # 当前金币(read_gold,读不到→0,安全保守)
    phase: tuple[int, int] | None   # (位面,轮次);读不到→None(不伪造)
    hp: int | None                   # 小队剩余血量(read_hp_opt,读不到→None;r317 同源 director)
    streak: int | None              # 连胜/连败 magnitude(read_streak,读不到→None)
    deploy_count: int | None        # 已部署角色数(read_deployed_count,读不到→None)
    deploy_cap: int | None          # deploy cap 真值(read_deploy_cap,读不到→None)
    level: int                      # 团队规模等级(read_level,Lv.N;cap>level=钻石/宝钻加成)
    bench_overflow: bool            # 「备战席已满」告警横幅在场(OCR;True=有未安置单位,出战被游戏忽略——flow 层 overflow_warning 同源口径)
    board: dict[str, int]           # 羁绊面板可见行原文(read_board OCR 直读;v4.7 面板滚动+重排,只是可见子集,决策用 flow 层计算值)
    front_line: list[Unit] | None  # 前排 Unit 行(SIFT 身份 + read_star 星级 + read_row_equipped 装备按 slot 注入 equips;templates 未加载→None)
    back_line: list[Unit] | None   # 后排 Unit 行(同上)
    bench: BenchView | None        # 备战席状态容器视图(read_bench_view SIFT 直产;slots=9 槽 BenchSlot,占位物品 kind 细分;备战席无 below icon→unit equips 恒 [];空读→None)
    owned_equips: list[dict] | None      # 右侧 owned 装备栏(read_equips SIFT;元素 {name,category,cx,cy,inliers};category 工具/特殊=消耗品,其余简易/进阶/...=装备;空→None;templates 未加载→None)
    armory_boxes: list[dict] | None      # 备战栏简易武装箱槽位(read_armory_boxes TM;元素 {slot,cx,cy};晶矿开箱掉箱占席,点「开启」腾槽;空→None;首见机制)
    reward_ores: list[dict] | None    # 奖励面板晶矿(read_ore_sights 多尺度模板匹配;元素 {color,cx,cy,r};color gold/blue/gray;采晶矿开启入账,角色/箱占席;空→None;首见机制)
    rail_shop: dict | None           # 银轨商店入口域(_read_rail_shop;{present,cx,cy,open_cx,open_cy,balance,buyable};模板/画面档缺失→None 整键;两态都返回,见 PREP_EXTRAS_DOC)


def _read_xp_progress(ctx: SrContext, screen: MatLike) -> tuple[int, int] | None:
    """经验面板「N/M」进度(纯读):N=当前档已攒经验,M=升下一级所需;读不到 → None。

    v4.7 实测样本:Lv.4 档「2/6」、Lv.5 档「0/16」(数值随档位增长)。
    area = ``文本-升级所需经验``;读不到 / 解析失败返 None(不伪造)。
    """
    rect = _area_rect(ctx, '文本-升级所需经验')
    if rect is None:
        return None
    blob = ''.join(r.data for r in _ocr(ctx, screen, rect))
    m = re.search(r'(\d+)\s*/\s*(\d+)', blob)
    if m is None:
        return None
    return int(m.group(1)), int(m.group(2))


# ===== 银轨商店入口域(rail_shop)=====

# 列车图案 TM 匹配阈值(与画面档「标识-银轨商店列车图案」template_match_threshold
# 同口径)。分离度(带 (325,250,500,480) 内存档帧实测):备战态命中 0.9998-1.0;
# 商店未开张帧(开拓银轨<2)最高 0.167;开拓商店面板开启帧 0.518(面板盖住横幅、
# 仅左缘窄条露出——该画面不产 extras,识别面无消费,阈值仍留 0.18 余量)。
# 标定与回归:测试仓 test_battle_prep_recognizer.py。
_RAIL_TRAIN_TM_THR: float = 0.7

# 横幅「打开商店 ×N」OCR 搜索带(1080p x1,y1,x2,y2),**先裁后 OCR**(crop_first=
# True:全图识别路径漏检小字行,先裁路径可读——余额读数的生面前提;弃 OCR 缓存,
# 本域每帧恰一次横幅 OCR,可接受)。x 下限 495 **必须排除列车图案**(图案右缘 480):
# 含图案的宽带实测漏检余额小字行「×0」、排除后锚与余额两行全读出(检测干扰实证,
# 校准帧 RGB 管线离线复验);x 上限 660 < 前排-1 卡左缘 677。y 域覆盖横幅浮动域
# (入口指示组锚定羁绊面板布局,见玩家卡「货币战争-备战-开拓商店」入口节);
# 带内唯一文本源即横幅锚与余额行,不引入面板/卡面数字噪声。校准帧实测锚与余额行
# 均在带内:「打开商店」中心 (550,283)、「×N」数字中心 (582,309)。
_RAIL_BANNER_RECT: tuple[int, int, int, int] = (495, 270, 660, 470)

# 「有商品可购买」胶囊条 OCR 搜索带(1080p x1,y1,x2,y2)。胶囊 y 随局浮动(两局实测:
# 一局紧贴横幅下方 y≈345-375,另一局 y≈445-470)→ 带覆盖两实测域(330-478);
# x 沿用横幅带(同区配套指示,两局实测胶囊 x 均落 360-540)。x 边界同横幅带论证:
# 下限 330 > 徽记带右缘 310,上限 660 < 前排-1 卡左缘 677,不引入卡面数字噪声。
# 带内文本源 = 横幅(浮动低位布局时与胶囊同带)+ 胶囊,buyable 锚「有商品可购买」
# 与横幅文本天然区分。胶囊在场正样本 fixture = 测试仓 rail_badge_capsule_prep_r4
# (端到端 OCR 依赖 ctx 单测覆盖不到,离线 analyze 验证兜底)。
_RAIL_CAPSULE_RECT: tuple[int, int, int, int] = (330, 330, 660, 478)

_rail_train_gray: MatLike | None = None
_rail_train_loaded: bool = False


def _get_rail_train_gray() -> MatLike | None:
    """加载银轨商店横幅列车图案 TM 模板灰度图(模块级缓存,幂等,缺文件 → None)。

    模板 = 实帧裁片 128×62 列车图案(assets/template/currency_war/cw_rail_shop_train/
    raw.webp,与画面档「标识-银轨商店列车图案」template_id 同源)。加载手法同
    func:`cw_identity_obs._get_bookcard_gray`(并发安全:模块级只读模板缓存)。
    """
    global _rail_train_gray, _rail_train_loaded
    if not _rail_train_loaded:
        _rail_train_loaded = True
        p = (get_project_root() / 'assets' / 'template' / 'currency_war'
             / 'cw_rail_shop_train' / 'raw.webp')
        img = cv2.imdecode(np.fromfile(str(p), np.uint8), cv2.IMREAD_COLOR) if p.is_file() else None
        _rail_train_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img is not None else None
    return _rail_train_gray


def find_rail_shop_train(screen: MatLike, rect: Rect) -> tuple[float, int, int] | None:
    """纯 CV 核心:列车图案带内 TM 匹配 → ``(score, cx, cy)`` | None(离线可测,无 ctx 依赖)。

    横幅(入口按钮区)左段的列车图案 = 静态渲染图形,作**在场识别锚**;横幅 y 随局
    浮动 → 识别必须带内全搜而非定点(搜索域 = 画面档「标识-银轨商店列车图案」带状
    pc_rect)。命中判定 score ≥ ``_RAIL_TRAIN_TM_THR``(与画面档阈值同口径);
    cx/cy = 匹配中心(1080p 绝对坐标,**在场定位用,不是点击点**——开店点击 =
    「打开商店」文本锚,见 :func:`parse_rail_shop_banner`;菱形徽记锚定羁绊面板行、
    位置浮动,不可当开店锚)。
    灰度转换与模板加载同 func:`cw_identity_obs.find_bookcards` 手法
    (模板与画面同权重转灰度,相对匹配一致)。
    """
    tm = _get_rail_train_gray()
    if tm is None:
        return None
    gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
    crop = gray[rect.y1:rect.y2, rect.x1:rect.x2]
    if crop.shape[0] < tm.shape[0] or crop.shape[1] < tm.shape[1]:
        return None
    _, max_val, _, max_loc = cv2.minMaxLoc(
        cv2.matchTemplate(crop, tm, cv2.TM_CCOEFF_NORMED))
    if max_val < _RAIL_TRAIN_TM_THR:
        return None
    return (max_val, rect.x1 + max_loc[0] + tm.shape[1] // 2,
            rect.y1 + max_loc[1] + tm.shape[0] // 2)


def parse_rail_shop_banner(results: list) -> tuple[int | None, int | None, int | None]:
    """横幅带 OCR 结果 → ``(balance, open_cx, open_cy)``(纯函数,离线可测)。

    ``results`` 元素需有 ``data`` 与 ``center`` 属性(框架 :class:`OcrMatchResult`
    即满足;单测以同属性对象构造)。锚 = 「打开商店」文本条目:

    - ``open_cx/open_cy`` = 锚条目 bbox 中心(1080p 绝对坐标)= **开店点击点**
      (横幅 = 入口按钮区,点文本即开面板);
    - ``balance`` = 锚条目自带数字;两行渲染(「打开商店」/「×N」分行)时取锚后
      第一条数字。

    无锚(横幅不在场;商店面板开启态横幅被面板盖住)→ ``(None, None, None)``
    (正确降级,不伪造);锚在场但数字缺失 → ``(None, open_cx, open_cy)``
    (点击点与余额独立降级)。
    """
    for i, r in enumerate(results):
        if '打开商店' not in (r.data or ''):
            continue
        c = r.center
        m = re.search(r'\d+', r.data)
        if m is not None:
            return int(m.group()), c.x, c.y
        for r2 in results[i + 1:]:
            m = re.search(r'\d+', r2.data or '')
            if m is not None:
                return int(m.group()), c.x, c.y
        return None, c.x, c.y
    return None, None, None


def _parse_rail_shop_buyable(texts: list[str]) -> bool | None:
    """胶囊带 OCR 文本 → 「有商品可购买」胶囊在场性:True = 读到;None = 带内未读到。

    ⚠️ 游戏语义未收敛 —— 本字段只管如实回报胶囊在场性,现假设 = 商品池刚刷新出
    余额可负担的新商品;已实测否定「恒定可负担指示」口径(同局多帧在场/缺席与
    余额-可负担性不相关),待采样收敛,消费方勿当「现在买得起」用。
    False 不产出 —— 「确无胶囊」与「OCR 失读」在带内 OCR 层面不可区分,
    统一返 None 交消费方按「未知」处理(宁缺勿造,同 phase 读不到→None 口径)。
    """
    for t in texts:
        if '有商品可购买' in t:
            return True
    return None


def _read_rail_shop(ctx: SrContext, screen: MatLike) -> dict | None:
    """银轨商店入口域(纯读)→ dict {present, cx, cy, open_cx, open_cy, balance, buyable} | None。

    - 模板 / 画面档缺失 → None(整键,同「templates 未加载→None」惯例);
    - 列车图案未命中(present=False)→ 其余字段恒 None:横幅与胶囊是入口在场态
      的配套指示(商店未开张时一并缺席),入口不在场短路两次 OCR,
      也避免「present=False 但 balance 有值」的矛盾态;
    - balance/open_cx/open_cy:商店面板开启态横幅被面板盖住 → 带内 OCR 无锚 →
      None(正确降级);
    - OCR 端到端(balance/open 点的带内 OCR 拼装)依赖 ctx,单测覆盖不到 ——
      由实机 / 离线 analyze 验证兜底;列车图案纯 CV 核心与横幅/胶囊解析纯函数有
      fixture 回归(测试仓 ``test_battle_prep_recognizer.py``)。
    """
    if _get_rail_train_gray() is None:
        return None
    train_rect = _area_rect(ctx, '标识-银轨商店列车图案')
    if train_rect is None:
        return None
    hit = find_rail_shop_train(screen, train_rect)
    if hit is None:
        return {'present': False, 'cx': None, 'cy': None,
                'open_cx': None, 'open_cy': None,
                'balance': None, 'buyable': None}
    _, cx, cy = hit
    balance, open_cx, open_cy = parse_rail_shop_banner(
        _ocr(ctx, screen, Rect(*_RAIL_BANNER_RECT), crop_first=True))
    buyable = _parse_rail_shop_buyable(
        [r.data or '' for r in _ocr(ctx, screen, Rect(*_RAIL_CAPSULE_RECT))])
    return {'present': True, 'cx': cx, 'cy': cy,
            'open_cx': open_cx, 'open_cy': open_cy,
            'balance': balance, 'buyable': buyable}


def read_prep_extras(ctx: SrContext, image: MatLike,
                     full_read: bool = True) -> dict:
    """备战画面领域事实读取(**备战 / 备战-开商店两识别器共用**)。

    并发安全同模块 docstring:纯读(不写 self. / 全局 / session);
    装备立绘模板经 ensure_* 幂等加载。读不到的字段 None(不伪造)。

    :param full_read: 是否做完整读(含部署行/血量/晶矿)。开商店画面传
        False——商店牌行盖住部署计数与血量、面板遮挡使立绘与晶矿识别
        不可靠(实机:行读恒缺/残缺,晶矿检出全是商品图标误报),这些字段
        **整键省略**(键不出现,与「读到空」区分;用户裁定:不识别的字段
        不该出现在返回里),要完整读数用备战画面(收店后);跳过还省 SIFT 开销。

    Returns:
        dict(full_read=True 时键集 = ``PREP_EXTRAS_DOC``;开商店画面省略
        front_line/back_line/deploy_count/deploy_cap/hp/reward_ores 六键,
        开商店识别器在此基础上叠加 shop_cards / refresh_probs)。
    """
    omit_keys = frozenset() if full_read else frozenset({
        'front_line', 'back_line', 'deploy_count', 'deploy_cap',
        'hp', 'reward_ores', 'owned_equips',
    })
    # 装备(slot_idx → 装备名;先读,再注入 Unit.equips)。备战栏 below 不读(未上阵无 icon,机制恒空,
    # 读只产假 MISS 噪声 — 某模板 val 0.55-0.56,shot miss_slot5 实证无 icon)。
    phase0 = _read_phase_round_pure(ctx, image)
    level0 = read_level(ctx, image, phase0[0], phase0[1]) if phase0 else read_level(ctx, image, 0, 0)
    front_equips: dict = {}
    back_equips: dict = {}
    _back_n = None
    if full_read:
        # 后排装备槽按 cap 差公式选档(口述「后台格数=6+(cap−level)」;
        # 旧 level 驱动已废)。已建档 6/7/8/9 直读,>9 域外保守 8 格超集(覆盖式保留证据在 select_back_layout)。
        from sr_od.application.currency_war.obs.cw_back_layout import (
            select_back_layout as _sel_bl,
        )
        _back_n, _back_pfx = _sel_bl(ctx, image, level=level0)
    templates = ensure_portrait_templates(ctx)  # 幂等加载缓存(并发安全,同 ensure_equip_tm_templates);bench 读也依赖
    equip_grays = ensure_equip_tm_templates(ctx)
    if full_read and equip_grays is not None:
        front_equips = read_row_equipped(ctx, image, equip_grays, '前排', 4)
        # 布局未知态(15 号稿 §3.2④,select_back_layout 返 (None,''))→ 后排
        # equips 空 dict(纯读面,跳过即正确;JSONL 保留证据在 resolve 侧)。
        back_equips = (read_row_equipped(ctx, image, equip_grays, _back_pfx, _back_n)
                       if _back_n else {})
    # 角色直产状态容器形状(read_deployed_rows 已按排分域);只补 equips
    #(按 slot 对齐注入;Unit frozen → replace 新构造)。
    front_line: list[Unit] | None = None
    back_line: list[Unit] | None = None
    bench: BenchView | None = None
    if full_read and templates is not None:
        front_hits, back_hits = read_deployed_rows(ctx, image, templates, level=level0)
        front_line = ([replace(u, equips=front_equips.get(s, []))
                       for s, u in front_hits] or None)
        back_line = ([replace(u, equips=back_equips.get(s, []))
                      for s, u in back_hits] or None)
    if templates is not None:
        _bv = read_bench_view(ctx, image, templates)
        # 备战席无 below icon → unit equips 保持 [];空读(零占用)→ None
        bench = (_bv if (_bv is not None
                         and any(s.kind != 'empty' for s in _bv.slots)) else None)
    # owned 装备栏(右侧 区域-道具装备,read_equips SIFT;装备+消耗品混排,返名+位置,category 区分装备 vs 消耗品)
    # 前置契约:本 reader 仅在备战族画面识别命中后生成 extras,
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
    #cap>level(宝钻/钻石叠加)不再只是经济信息——它直接编码
    # 后排扩展量(口述公式 6+(cap−level)),布局选档已在函数头消费。
    # r317:read_hp 裸调用迁 read_hp_opt
    # (miss→None;与 director 同源——消掉「MCP 报 100 而
    # director gated=26」双真相)。extras 序列化 None→
    # 合法 null(backend json.dumps 预校验);extras_doc
    # 文案同步「读不到→None」。(模块级 import。)
    # board = 面板 OCR 直读(快路径;可见行原文,语义与截断警示见 read_board docstring)。
    # 羁绊计数决策面用 flow 层 board_from_deployed(以算为准)——extras 不做慢的
    # SIFT 单位表计算路径(用户裁定:读要快,算的逻辑单独改对)。
    # 告警横幅在场 = 溢出态(有未安置单位,出战被游戏忽略;flow 层 overflow_warning
    # 同源口径,识别面 = 画面档「告警-备战席已满」OCR 区)。横幅在 y 512-555,
    # 商店牌行(y≤330)盖不住 → 备战/开商店两态都可读,不进省略清单。
    _ov_rect = _area_rect(ctx, '告警-备战席已满', '货币战争-备战')
    bench_overflow = False
    if _ov_rect is not None:
        for _r in _ocr(ctx, image, _ov_rect):
            if '备战席已满' in (_r.data or ''):
                bench_overflow = True
                break
    state = _BattlePrepState(
        bench_overflow=bench_overflow,
        gold=read_gold(ctx, image),
        phase=phase,
        hp=(None if not full_read else read_hp_opt(ctx, image)),
        streak=read_streak(ctx, image),
        deploy_count=None if not full_read else read_deployed_count(ctx, image),
        deploy_cap=None if not full_read else read_deploy_cap(ctx, image),
        level=level,
        board=read_board(ctx, image),
        front_line=front_line,
        back_line=back_line,
        bench=bench,
        owned_equips=owned_equips,
        armory_boxes=([
            {'slot': idx, 'cx': p.x, 'cy': p.y} for idx, p in read_armory_boxes(ctx, image)
        ] or None),
        reward_ores=([
            {'color': c, 'cx': p.x, 'cy': p.y, 'r': r} for c, p, r in read_ore_sights(ctx, image)
        ] or None) if full_read else None,
        rail_shop=_read_rail_shop(ctx, image),
    )
    data = asdict(state)
    if omit_keys:
        # 开商店画面:不可靠字段**整键省略**(不是 null)——键缺席 = 「本画面不提供」,
        # 与「读了但没读到」的语义区分开(用户裁定:不识别的字段不该出现在返回里)。
        for k in omit_keys:
            data.pop(k, None)
    data['xp_progress'] = _read_xp_progress(ctx, image)
    data['levelup_cost'] = read_level_up_cost(ctx, image)
    return data


#: 备战族 extras 字段说明(单一源;备战识别器直接引用,开商店识别器以
#: ``{**PREP_EXTRAS_DOC, ...}`` 叠加商店域字段——键集与 read_prep_extras
#: 返回 dict 一致,加/改字段时同步)。
PREP_EXTRAS_DOC: dict[str, str] = {
    'gold': '当前金币(int;读不到→0,安全保守默认)',
    'phase': '(位面, 轮次) 二元组,如 [1,3] = 位面1 第3轮;读不到→None(不伪造)',
    'hp': '小队剩余血量(int|None;读不到→None 与 director 同源;r317)。开商店画面整键省略(计数被商店牌行盖住,收店后用备战画面取)',
    'streak': '连胜/连败 magnitude(int;读不到→None)',
    'bench_overflow': '「备战席已满」告警横幅在场(bool,OCR 直读)。True = 有未安置单位,出战会被游戏忽略(锁定)——先卖角色腾位再出战;与 flow 层 overflow_warning 同源口径;横幅在商店态也可见,两态都返回',
    'deploy_count': '已部署角色数(int;读不到→None)。开商店画面整键省略(遮挡不可靠,收店后用备战画面取)'
                    '(商店牌行盖住计数,遮挡不可靠;完整读数收店后用备战画面取)',
    'deploy_cap': '部署上限真值(int;>level 表示钻石/财富宝钻加成 +1 团队槽;读不到→None)。'
                  '开商店画面整键省略(遮挡不可靠,收店后用备战画面取)(同 deploy_count)',
    'level': '团队规模等级 Lv.N(int;cap>level=钻石/宝钻加成)',
    'board': '羁绊面板可见行原文 {羁绊名: 面板数字}(OCR 直读,快路径)。'
             '⚠️ v4.7 面板滚动+重排,本读数只是可见子集,不可当完整羁绊计数或'
             '在场人数用于决策;决策面用 flow 层 board_from_deployed 计算值'
             '(证据与推导见 research/v47_first_match_observation.md §2.5)',
    'front_line': '前排 Unit 行 list(元素 Unit dict: char_id/star/equips/slot;'
                  'char_id=规范名,slot=排内 1 基画面槽号,equips=装备名 list)。SIFT 立绘识别,'
                  '供智能体交叉验证而非盲信(证据链见 currency_war_char_id);'
                  'templates 未加载→None;开商店画面整键省略(遮挡不可靠,收店后用备战画面取)'
                  '(遮挡不可靠,完整读数收店后用备战画面取)',
    'back_line': '后排 Unit 行 list(同 front_line 结构;templates 未加载→None;'
                 '开商店画面整键省略(遮挡不可靠,收店后用备战画面取))',
    'bench': '备战席状态容器视图 dict(BenchView:slots=9 元素 BenchSlot dict'
             '{kind: unit/supply_box/tome/bookcard/empty, unit: Unit dict 或 null}'
             '+ capacity=9;unit 槽元素 = char_id/star/equips/slot,备战席无 below icon→equips 恒 [];'
             '占位物品槽 kind 识别期细分;空读→None)',
    'owned_equips': '右侧 owned 装备栏 list(read_equips SIFT;元素 {name,category,cx,cy,inliers};开商店画面整键省略(用户裁定:商店态无需装备栏,完整读数收店后取);'
                    'category 工具/特殊=消耗品,其余简易/进阶/特权/星徽/白昼/命运/骇客=装备;'
                    'cx/cy=1080p 原图绝对坐标(点该坐标开对应物品详情);空→None;templates 未加载→None)',
    'armory_boxes': '备战栏简易武装箱 list(read_armory_boxes TM;元素 {slot,cx,cy},cx/cy=槽 rect 几何中心'
                    '(slot = 备战栏物理槽位 1 基;开箱点击坐标另走建档「武装箱开启位-N」直查,'
                    '本坐标供交叉定位);奖励球(晶矿)开启可能掉箱占 1 备战席槽;空→None',
    'reward_ores': '奖励面板晶矿 list(read_ore_sights 多尺度模板匹配;元素 {color,cx,cy,r},'
                      'color=gold/blue/gray,cx/cy=采晶矿坐标;通关奖励节点后出现;席满点不动(先开箱腾席);空→None;开商店画面整键省略(晶矿在商店画面不可见,检出全是商品图标误报)',
    'rail_shop': '左侧开拓银轨商店入口域 dict {present, cx, cy, open_cx, open_cy, balance, buyable}'
                 '(横幅列车图案带内 TM 匹配 ≥0.7 + 横幅/胶囊带 OCR;两态都返回,不进开商店省略清单)。'
                 'present=列车图案在场(商店开张指示:开拓银轨≥2 开张;银轨<2 商店未开张→False);'
                 'cx/cy=列车图案匹配中心(1080p 绝对坐标,**在场定位用,不是点击点**;不在场→None);'
                 'open_cx/open_cy=横幅「打开商店」文本 OCR 锚中心(**开店点击点**:横幅 = 入口按钮区,'
                 '点文本即开面板;菱形徽记锚定羁绊面板行、位置浮动,别当开店点击目标;OCR 无锚→None,'
                 '此时无可靠开店点击点);balance=「×N」开拓力余额(横幅带先裁后 OCR 且 x 下限'
                 '排除列车图案——含图案宽带实测漏检小字行;商店面板开启态横幅被面板盖住→None 正确降级;'
                 '入口不在场→None);'
                 'buyable=「有商品可购买」黄胶囊条在场性(OCR 到→True,带内未读到→None;'
                 '⚠️ 游戏语义未收敛:现假设=商品池刚刷新出余额可负担的新商品,已实测否定「恒定可负担指示」'
                 '(同局多帧在场/缺席与余额-可负担性不相关),待采样收敛,勿当「现在买得起」用;'
                 'False 不产出:「确无胶囊」与「OCR 失读」不可区分,消费方按「未知」处理)。'
                 '模板/画面档缺失→整键 None。横幅 y 随局浮动,识别为带内全搜',
    'xp_progress': '经验面板「N/M」进度 [已攒, 升级所需](读不到→None)',
    'levelup_cost': '购买经验按钮价格(int 金币;读不到→None)',
}


class BattlePrepRecognizer(ScreenRecognizer):
    """货币战争备战画面额外识别器(首个 per-screen recognizer 消费者)。"""

    screen_name: str = SCREEN_NAME   # '货币战争-备战'

    # extras 字段说明(随analyze 响应平级返回 extras_doc;键集与 read_prep_extras 返回一致)
    extras_doc: dict[str, str] = PREP_EXTRAS_DOC

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
            领域事实 dict(读取主体 = 模块级 :func:`read_prep_extras`,
            与「货币战争-备战-开商店」识别器共用单一实现)。
        """
        return read_prep_extras(ctx, image)
