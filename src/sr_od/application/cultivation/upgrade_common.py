"""三升级 op(角色晋阶/光锥晋阶/行迹升级)共用 helper——域根平铺,单一源。

出处:域 README §2.3 评估口径「第三份同构复制出现时评估归并」——行迹线券
刷链落地即第三份同构,机械复制面(次数设置对/事务式记账/券确认骨架/toast
门控/记名防线/等级读区/副本分流/开拓力守卫)按 upgrade-align-3 设计收进本
模块。策略差异(按钮分流/计场时机/判停返回词表/收尾载体)留各线 op,不进
helper;helper 不持状态(状态归 op 账本属性)、不做线间策略分叉。

缝保留规则(测试锁前提,三条):
1. 各线 op 私有方法保留为委托缝——签名不变、方法体改一行委托到本模块,
   测试的 monkeypatch 目标与「包装真实现再替换」写法照常生效;
2. helper 经首参 op 的实例属性访问一切识别/回合/账本依赖(不引用模块级
   函数),类级桩在属性查找上生效,helper 代码在测试里自动走桩;
3. helper 之间禁止直调:凡缝语义(读/设次数、记账、读名、守卫、副本态
   判定等)一律经 op.<缝方法>(...) 委托,直调会绕开类级桩。

消费方式:各线 op 模块以模块常量实例化一份 UpgradeLineSpec(线私有值单一
源留在 op 模块),helper 只收引用;本模块不含 Operation 子类,不影响 op
注册扫描;__init__.py 不暴露本模块,消费方直接 import 模块路径。
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from one_dragon.base.operation import operation as _framework_operation
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext

# 滑条动画等待经框架基座模块的 time 引用而非裸 import:helper 不在 op 类族
# MRO 内,测试 harness 的 fast_sleep 只替换基座模块与 op 类族模块的 time
# 属性,裸 import 的 sleep 在流程测试里不会被短路(基座引用恒被替换)。
_framework_sleep = _framework_operation.time.sleep

# ---------------- 共享画面名常量(三线同值,单一源上移) ---------------- #
# 快速刷取两弹窗/资源窗口/挑战副本/开拓力补充弹窗五画面三线共用同一建档,
# 字面量上移消掉三份重复(笔误漂移面);area 名按 helper 需要内联于签名处。

FAST_FARM_DIALOG_SCREEN: str = '快速刷取弹窗'
FAST_FARM_RESULT_SCREEN: str = '快速刷取结果弹窗'
RESOURCE_WINDOW_SCREEN: str = '培养资源窗口'
CHALLENGE_SCREEN: str = '挑战副本'
POWER_DIALOG_SCREEN: str = '开拓力补充弹窗'


@dataclass(frozen=True)
class UpgradeLineSpec:
    """单线接入参数(线私有值:画面名/日志前缀/判停词/锚表/消耗常量)。

    每线 op 模块以模块常量实例化一份;消耗数值的常量定义不迁移,spec 只作
    入参搬运(域 README §6:三线消耗常量各自独立、勿互相复用)。必填字段不
    设默认值——新线接入漏填构造期即报错,不运行期 None 传播。"""

    log_prefix: str
    """日志前缀(晋阶 / 光锥晋阶 / 行迹升级)。"""

    stop_status: str
    """材料判停返回词(char MATERIAL_CAPPED / LC LIGHT_CONE_CAPPED)。"""

    ascend_screen: str
    """养成界面画面名(角色-等级提升 / 光锥-等级提升 / 角色-行迹)。"""

    dungeon_title_areas: tuple[str, ...]
    """挑战副本画面副本类型标题锚表(编队双锚反证用;锚表内容=建档覆盖面,
    各线保留现状,扩充归补建档批次)。"""

    name_read_screens: tuple[str, ...]
    """读名区双屏迭代序(手动路线记名用;area 未建档的画面跳过不报错)。"""

    reentry_hint: str
    """读名失败指引文案(就地起跑形态;入口形态由调用点传 hint 覆盖)。"""

    trailblaze_per: int
    """每次刷取消耗开拓力(记账日志用,常量定义留各 op 模块)。"""

    ticket_per: int
    """每次刷取消耗快速刷取券(记账日志用)。"""

    farm_open_max_attempts: int = 4
    """开窗/面板钮漏检封顶(点击尝试次数;尝试发出即增,计数 ≥ 此值判停)。"""


class UpgradeFarmHost(Protocol):
    """helper 所需的 op 宿主面(结构化类型,三 op 隐式满足,不继承)。

    声明 helper 访问的全部成员:识别/回合接口、构造参数、账本状态与各
    委托缝私有方法。运行时不做结构校验(结构化类型仅约束注解);trace 按
    迁移步骤补齐同名账本字段后接入对应 helper(_farm_draws /
    _farm_window_wait_rounds 等),部分成员(手动路线相关)仅 char/LC 具备。"""

    ctx: SrContext
    last_screenshot: object
    farm_times_per_round: int
    farm_dungeon: bool
    use_fast_ticket: bool
    _farm_rounds: int
    _farm_draws: int
    _farm_times_set: int
    _farm_window_wait_rounds: int
    _farm_dialog_wait_rounds: int
    _capped: bool
    _stop_status: str
    _char_name: str | None

    def screenshot(self) -> object:
        """截取当前画面。"""
        ...

    def save_screenshot(self, prefix: str | None = None) -> str:
        """现场留证截图(判停路径取证用)。"""
        ...

    def round_by_find_area(self, screen: object, screen_name: str,
                           area_name: str) -> OperationRoundResult:
        """识别查询(命中/未命中/未配置 → 对应轮次结果)。"""
        ...

    def round_by_find_and_click_area(self, screen: object, screen_name: str,
                                     area_name: str, pre_delay: float = 0.3,
                                     success_wait: float | None = None,
                                     retry_wait: float | None = None,
                                     until_find_all: list[tuple[str, str]] | None = None,
                                     until_not_find_all: list[tuple[str, str]] | None = None,
                                     ) -> OperationRoundResult:
        """识别点击(带 until 时点击一次,锚验证在重入轮开头)。"""
        ...

    def round_success(self, status: str | None = None,
                      wait: float | None = None) -> OperationRoundResult:
        """成功轮次结果。"""
        ...

    def round_wait(self, status: str | None = None,
                   wait: float | None = None) -> OperationRoundResult:
        """等待轮次结果(原样重跑节点,不计重试)。"""
        ...

    def round_retry(self, status: str | None = None,
                    wait: float | None = None) -> OperationRoundResult:
        """重试轮次结果(计入重试预算)。"""
        ...

    def round_fail(self, status: str | None = None) -> OperationRoundResult:
        """失败轮次结果。"""
        ...

    # -------- 委托缝私有方法(helper 经这些缝互调,禁直调兄弟 helper) -------- #

    def _set_farm_times(self, target: int) -> OperationRoundResult:
        """确认框次数设置缝(H2)。"""
        ...

    def _read_farm_times(self) -> int | None:
        """确认框次数读数缝(H2)。"""
        ...

    def _settle_farm_accounting(self) -> None:
        """事务式记账缝(H3)。"""
        ...

    def _read_character_name(self) -> str | None:
        """读名缝(H6)。"""
        ...

    def _guard_unnamed_manual_farm(self, *, hint: str | None = None
                                   ) -> OperationRoundResult | None:
        """记名防线缝(H6)。"""
        ...

    def _in_dungeon_state(self, screen: object) -> bool:
        """副本态判定缝(H8)。"""
        ...


# ---------------- H1 构造校验 ---------------- #

def validate_farm_params(farm_times_per_round: int, farm_rounds_max: int) -> None:
    """三线 __init__ 共用的 farm 参数校验(文案与拆并前逐字一致)。

    trace 的 target 非空校验是线私有(行迹线专有参数),留 trace 自持。"""
    if farm_times_per_round == 0 or farm_times_per_round < -1:
        raise ValueError(
            f'farm_times_per_round 须为正数或 -1(拉满), 得到 {farm_times_per_round}')
    if farm_rounds_max < 1:
        raise ValueError(f'farm_rounds_max 必须 >= 1, 得到 {farm_rounds_max}')


# ---------------- H2 确认框次数设置对 ---------------- #

def read_farm_times(op: UpgradeFarmHost) -> int | None:
    """确认框「刷取次数 N」OCR 取 N(选次数弹窗共用建档,三线同区名)。"""
    screen = op.screenshot()
    area = op.ctx.screen_loader.get_area(FAST_FARM_DIALOG_SCREEN, '读区-刷取次数')
    results = op.ctx.ocr_service.get_ocr_result_list(
        image=screen, rect=area.pc_rect, crop_first=True)
    for r in results:
        m = re.search(r'\d+', str(r.data or ''))
        if m:
            return int(m.group())
    return None


def set_farm_times(op: UpgradeFarmHost, spec: UpgradeLineSpec,
                   target: int) -> OperationRoundResult:
    """确认框内把次数设到 target(三线同一算法,差异仅日志前缀):
    target=-1 = 点「^」拉满(滑条上限,随副本类型);正数 = OCR 现读 →
    点「+」补差 → 达标即成。实际设到的值写 op._farm_times_set(消耗统计
    口径:配置 -1 是拉满指令,真实消耗以读数为准);入口清判据位——设置
    失败不得残留旧值,否则重入轮拿旧判据跳过设次数直接确认(三线统一
    收敛:原 trace 无清位,收敛无行为变化——其调用点前置判据非零才进本
    函数且失败路径全部显式失败,不存在失败重入;统一防未来接入点踩残留)。"""
    op._farm_times_set = 0
    if target == -1:
        max_area = op.ctx.screen_loader.get_area(
            FAST_FARM_DIALOG_SCREEN, '按钮-刷取次数拉满')
        op.ctx.controller.click(max_area.rect.center)
        _framework_sleep(1)  # 滑条动画
        current = op._read_farm_times()
        if current is None:
            _framework_sleep(1)
            current = op._read_farm_times()
        if current is None:
            return op.round_fail('拉满后无法读取刷取次数')
        op._farm_times_set = current
        log.info('%s: 刷取次数已拉满至 %d', spec.log_prefix, current)
        return op.round_success()
    plus_area = op.ctx.screen_loader.get_area(
        FAST_FARM_DIALOG_SCREEN, '按钮-刷取次数加')
    for _ in range(target + 3):  # 点数上界 = 目标+3(防 OCR 偏差死循环)
        current = op._read_farm_times()
        if current is None:
            return op.round_fail('无法读取确认框刷取次数')
        if current >= target:
            op._farm_times_set = current
            return op.round_success()
        op.ctx.controller.click(plus_area.rect.center)
        # 滑条动画:点击后立即复读会读到旧值再点,越过目标多耗开拓力
        _framework_sleep(0.4)
    return op.round_fail(f'刷取次数未能设到 {target}')


# ---------------- H3 事务式记账 commit ---------------- #

def settle_farm_accounting(op: UpgradeFarmHost, spec: UpgradeLineSpec) -> None:
    """本轮券刷取记账(幂等):以 op._farm_times_set 非零为未记账判据,
    记账后归零——WAIT 重入轮不会重复计。_farm_draws 语义 = 券刷累计次数
    (确认框实际设到的值),与开拓力/券消耗记账共用口径。"""
    if op._farm_times_set == 0:
        return
    op._farm_rounds += 1
    op._farm_draws += op._farm_times_set
    log.info('%s: 第 %d 轮券刷取 %d 次(消耗开拓力 %d + 快速刷取券 %d,'
             '券免战斗开拓力照扣)',
             spec.log_prefix, op._farm_rounds, op._farm_times_set,
             op._farm_times_set * spec.trailblaze_per,
             op._farm_times_set * spec.ticket_per)
    op._farm_times_set = 0


# ---------------- H6 无名记名防线 ---------------- #

def read_character_name(op: UpgradeFarmHost,
                        spec: UpgradeLineSpec) -> str | None:
    """读名区 OCR「命途/名字」取「/」后段(屏序入 spec.name_read_screens,
    双屏迭代;两界面左上布局同位、area 同名分别建档)。

    area 未建档/读不出返回 None:某画面读名区未建档时 get_area 返回 None,
    该画面跳过不报错(保持各线现行为);两屏皆读不出由防线判停,不影响升级
    主流程。"""
    for screen_name in spec.name_read_screens:
        area = op.ctx.screen_loader.get_area(screen_name, '读名区-左上')
        if area is None:
            continue
        results = op.ctx.ocr_service.get_ocr_result_list(
            image=op.screenshot(), rect=area.pc_rect, crop_first=True)
        for r in results:
            text = str(r.data or '').strip()
            if '/' in text:
                name = text.rsplit('/', maxsplit=1)[-1].strip()
                if name:
                    return name
    return None


def guard_unnamed_manual_farm(op: UpgradeFarmHost, spec: UpgradeLineSpec, *,
                              hint: str | None = None
                              ) -> OperationRoundResult | None:
    """入口记名防线(ALREADY_ASCEND 直入/None 帧探针/入口常规路径共用):
    读名写入 op._char_name;读名失败且「farm_dungeon 且非券路线」授权时
    round_fail 拦截——手动刷取返回链落大世界后凭记名重选(角色详情不记忆
    上次角色),漏读会在战后重选防线处白烧一场开拓力,故消耗前拦截。
    券路线/未授权刷取无需记名,读名失败不拦截返回 None。

    拦截文案:就地起跑形态 = spec.reentry_hint;入口常规形态由调用点传
    hint 覆盖(两形态指引落点不同:重发起入口 vs 实机确认画面)。"""
    op._char_name = op._read_character_name()
    if op._char_name is None and op.farm_dungeon and not op.use_fast_ticket:
        return op.round_fail(hint if hint else spec.reentry_hint)
    return None


# ---------------- H7 等级读区(NN/MM 比例形态) ---------------- #

def read_level_ratio(op: UpgradeFarmHost, screen_name: str,
                     area_name: str) -> int | None:
    """画面 + area 内 OCR「NN/MM」取当前值(char 晋阶等级/LC 光锥等级
    同 regex 同构;trace「等级N」无比例形态不同构,留 trace 自持)。"""
    screen = op.screenshot()
    area = op.ctx.screen_loader.get_area(screen_name, area_name)
    results = op.ctx.ocr_service.get_ocr_result_list(
        image=screen, rect=area.pc_rect, crop_first=True)
    for r in results:
        m = re.search(r'(\d+)\s*/\s*\d+', str(r.data or ''))
        if m:
            return int(m.group(1))
    return None


# ---------------- H4 券确认节点骨架 ---------------- #

def confirm_ticket_farm_step(op: UpgradeFarmHost,
                             spec: UpgradeLineSpec) -> OperationRoundResult:
    """券确认刷取节点体(char/LC 逐字同构,查询顺序与拆并前逐条一致):
    WAIT 重入幂等分类——①补充弹窗 probe 在 = 确认被拦,判据位清零 + 判停
    置位 + POWER_BLOCKED(「确认」是星琼购开拓力,永不触碰);②结果框 probe
    在 = 领奖完成,经 op._settle_farm_accounting() 记账 + RESULT_OPEN;
    ③确认框不在 = 刷取进行中慢询;④确认框在 = 未设次数先经
    op._set_farm_times(...) 设次数,再点确认,helper success 后经
    op._settle_farm_accounting() 记账——缝间调用方向遵守缝保留规则 3。

    记账口径:确认点击生效的两个等效证据(重入轮看到结果框 / helper 返回
    success)共用同一幂等判据(_farm_times_set 非零为未记账),只挂其一则
    生产时序下记账分支不可达。"""
    screen = op.last_screenshot
    if op.round_by_find_area(screen, POWER_DIALOG_SCREEN,
                             '标题-开拓力补充弹窗').is_success:
        op._farm_times_set = 0  # 未成交未记账,本轮作废,不动历史账
        op._capped = True
        op._stop_status = 'POWER_CAPPED'
        log.info('%s: 确认已发出但被开拓力不足拦截,本轮未成交——'
                 '原路清场(可待开拓力恢复后续跑)', spec.log_prefix)
        return op.round_success(status='POWER_BLOCKED', wait=2)
    if op.round_by_find_area(screen, FAST_FARM_RESULT_SCREEN,
                             '按钮-关闭刷取结果').is_success:
        op._settle_farm_accounting()
        return op.round_success(status='RESULT_OPEN', wait=1.5)
    if not op.round_by_find_area(screen, FAST_FARM_DIALOG_SCREEN,
                                 '标题-快速刷取弹窗').is_success:
        return op.round_wait('刷取执行中,等结果框', wait=2)
    # 确认框在:次数未设则先设;已设(重入:确认点击未生效)跳过设次数
    # 只重发确认
    if op._farm_times_set == 0:
        set_result = op._set_farm_times(op.farm_times_per_round)
        if not set_result.is_success:
            return set_result
    result = op.round_by_find_and_click_area(
        screen, FAST_FARM_DIALOG_SCREEN, '按钮-确认快速刷取',
        until_find_all=[(FAST_FARM_RESULT_SCREEN, '按钮-关闭刷取结果')],
        pre_delay=0.5, success_wait=2, retry_wait=2,
    )
    if result.is_success:
        op._settle_farm_accounting()
    return result


# ---------------- H5 toast 门控开窗 ---------------- #

def no_farm_gap_toast_hit(op: UpgradeFarmHost, toast_screen: str,
                          attempts: int) -> bool:
    """「提示-无可刷缺口」toast 探测谓词(H5a 探测门内联实现自身查询,
    不经本函数;本函数供 trace 链入口段复用——trace 反应不同:转 CLOSE_PANEL
    落账,载体差异留 trace)。attempts ≤1 放行探测:慢开窗时冗余二次点击
    被拒再弹的 toast 不得误读为无可刷缺口,计数 ≥2 抑制。"""
    return attempts <= 1 and op.round_by_find_area(
        op.last_screenshot, toast_screen, '提示-无可刷缺口').is_success


def open_farm_window_step(op: UpgradeFarmHost,
                          spec: UpgradeLineSpec) -> OperationRoundResult:
    """打开资源窗口节点体(char/LC 逐字同构,查询顺序与拆并前逐条一致):
    探测门(尝试计数 ≤1 时查 toast,命中 → 判停收口留证)→ 点击-until
    资源窗口 → 成功复位计数;失败或封顶(漏检兜底)→ FARM_WINDOW_FAIL
    判停收口。封顶语义 = 尝试发出即增:点击尝试后计数自增,计数 ≥
    spec.farm_open_max_attempts 判停——第 4 次尝试发出后判停,探测发生在
    第 1、2 次尝试轮。"""
    screen = op.last_screenshot
    if op._farm_window_wait_rounds <= 1 and op.round_by_find_area(
            screen, spec.ascend_screen, '提示-无可刷缺口').is_success:
        op._farm_window_wait_rounds = 0
        op._capped = True
        op._stop_status = spec.stop_status
        op.save_screenshot(prefix='快速刷取无可刷缺口')
        log.info('%s: 无可刷缺口(游戏 toast 命中),判停收尾——'
                 '可改用 fill_generic 通用材料补全路线', spec.log_prefix)
        return op.round_success(status='FARM_WINDOW_FAIL', wait=1.5)
    result = op.round_by_find_and_click_area(
        screen, spec.ascend_screen, '按钮-快速刷取',
        until_find_all=[(RESOURCE_WINDOW_SCREEN, '标题-培养资源窗口')],
        pre_delay=0.5, success_wait=0.3, retry_wait=2,
    )
    if result.is_success:
        op._farm_window_wait_rounds = 0
        return result
    op._farm_window_wait_rounds += 1  # 尝试发出即增
    if result.is_fail or op._farm_window_wait_rounds >= spec.farm_open_max_attempts:
        op._farm_window_wait_rounds = 0
        op._capped = True
        op._stop_status = spec.stop_status
        if result.is_fail:
            log.info('%s: 资源窗口打开失败(%s),判停收尾——'
                     '可改用 fill_generic 通用材料补全路线',
                     spec.log_prefix, result.status)
        else:
            op.save_screenshot(prefix='打开资源窗口')
            log.info('%s: 资源窗口连续未打开(toast 漏检,兜底封顶),'
                     '现场已截图,判停收尾——可改用 '
                     'fill_generic 通用材料补全路线', spec.log_prefix)
        return op.round_success(status='FARM_WINDOW_FAIL', wait=1.5)
    return result


# ---------------- H8 副本态判定与副本刷取分流 ---------------- #

def is_dungeon_state(op: UpgradeFarmHost, spec: UpgradeLineSpec,
                     screen: object) -> bool:
    """副本画面判定:spec.dungeon_title_areas 任一副本类型标题在场。
    锚表逐项短路查询(与前实现 `A or B` 逐条一致);锚表内容 = 各线建档
    覆盖面(char 双锚 / LC 单锚),扩充归补建档批次。"""
    return any(op.round_by_find_area(screen, CHALLENGE_SCREEN, area).is_success
               for area in spec.dungeon_title_areas)


def farm_in_dungeon_step(op: UpgradeFarmHost,
                         spec: UpgradeLineSpec) -> OperationRoundResult:
    """副本刷取分流节点体(char/LC 逐字同构,查询顺序与拆并前逐条一致):
    券路 = 点「快速刷取副本」→ 确认框连开有界自旋(_farm_dialog_wait_rounds
    连等 ≥4 留证显式失败);手动路 = 编队双锚判定(op._in_dungeon_state 经缝
    调用——「队伍标题在 + 副本标题不在」三态分流)+ 点挑战按钮。⚠️ 编队态
    判定必须双锚:「挑战按钮」area 的 rect/text 与编队画面「开始编队挑战」
    坐标重叠、文本相似,无副本态前置判定会在编队画面误点开新战斗(实测
    事故,资源被连环消耗)——安全判定收敛为单一实现,单源优先。"""
    screen = op.last_screenshot
    if op.use_fast_ticket:
        result = op.round_by_find_and_click_area(
            screen, CHALLENGE_SCREEN, '按钮-快速刷取副本',
            until_find_all=[(FAST_FARM_DIALOG_SCREEN, '标题-快速刷取弹窗')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )
        if result.is_success:
            op._farm_dialog_wait_rounds = 0
            return op.round_success(status='USE_TICKET')
        # 确认框偶发不开:helper 的 WAIT 返回无重试上限,原样返回会无限
        # 自旋——连等超限 = 异常现场,留证后显式失败
        op._farm_dialog_wait_rounds += 1
        if op._farm_dialog_wait_rounds >= 4:
            op.save_screenshot(prefix='副本刷取分流')
            return op.round_fail('快速刷取确认框连续未打开,现场已截图')
        return result
    if not op._in_dungeon_state(screen):
        # 编队态:交手动战斗节点点开始挑战
        if op.round_by_find_area(screen, CHALLENGE_SCREEN, '队伍标题').is_success:
            return op.round_success(status='MANUAL_FIGHT')
        # 挑战按钮在但副本类型标题都读不到 = 未识别副本类型(未建档类型/
        # 标题 OCR 持续失败):交手动路线会零消耗空转(不计场的 BATTLE_DONE
        # 反复回环开窗进本)——计重试(瞬时 OCR 失败可自愈),耗尽显式失败
        # 强制补档
        if op.round_by_find_area(screen, CHALLENGE_SCREEN, '挑战按钮').is_success:
            return op.round_retry('副本类型标题未识别(未建档类型/OCR 未读出),等重判', wait=2)
        # 战斗/结算态:交手动战斗节点分类(char 计场在离开编队态时发生,
        # LC 在点击时计——计场时机是策略差异,留各线 manual_fight 节点)
        return op.round_success(status='MANUAL_FIGHT')
    result = op.round_by_find_and_click_area(
        screen, CHALLENGE_SCREEN, '挑战按钮',
        until_find_all=[(CHALLENGE_SCREEN, '按钮-开始编队挑战')],
        pre_delay=0.5, success_wait=1.5, retry_wait=2,
    )
    if result.is_success:
        return op.round_success(status='MANUAL_FIGHT')
    return result


# ---------------- H9 开拓力守卫(单发拦截形状) ---------------- #

def guard_power_blocked(op: UpgradeFarmHost, spec: UpgradeLineSpec,
                        screen: object, *,
                        on_intercept: Callable[[], None] | None = None
                        ) -> OperationRoundResult | None:
    """手动路线开拓力守卫:「开拓力补充弹窗」在场 → on_intercept()(可注入
    回调,char 传作废 _squad_clicked 旗标;LC 点击时计场无需回调)→ 判停
    置位 + POWER_BLOCKED 交返回分类原路清场;弹窗不在返回 None。
    「确认」是星琼购开拓力,永不触碰(星琼红线在本实现内声明)。
    confirm 内拦截语义不同(需作废账本判据位)不复用本函数,归 H4;
    返回分类的补充弹窗取消层归浮层清场(H10);trace 守卫为链内自持清场
    形状(置位后留守节点逐轮清场,终态载体 _final_status),不接入本函数。"""
    if not op.round_by_find_area(screen, POWER_DIALOG_SCREEN,
                                 '标题-开拓力补充弹窗').is_success:
        return None
    if on_intercept is not None:
        on_intercept()
    op._capped = True
    op._stop_status = 'POWER_CAPPED'
    log.info('%s: 手动路线开拓力不足判停,原路清场(可待开拓力恢复后续跑)',
             spec.log_prefix)
    return op.round_success(status='POWER_BLOCKED', wait=2)
