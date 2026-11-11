"""切换游戏内文本语言的 operation(简体中文 ↔ English)。

用途:快速切换游戏显示语言(如切 English 读官方英文名做数据回填),完成后
游戏与 ``game_config.lang`` 保持一致。经 MCP ``run_operation`` 运行:

    op_id = 'sr_od.application.game_settings.game_settings_op.SwitchLanguageOp'
    args  = {'target_lang': 'en'}   # 或 'cn'

完成时同步两件事:
- ``game_config.lang`` 更新为目标语言(项目多语言状态源:i18 默认语言、
  OCR 阈值表、窗口标题都按它取值);同时兼作「配置与实际漂移」的校正入口
  —— 配置说已是目标语言时仍会进语言页读实际值,漂移则照常切换;
- 控制器窗口标题刷新 —— 游戏切文本语言会连窗口标题一起改
  (cn=崩坏：星穹铁道 / en=Honkai: Star Rail),控制器按标题查找窗口,
  不同步刷新 = 本次运行结束后窗口失明。

多语言判定走框架既有机制:screen_info 文本 area 的 text 写中文,
``screen_utils.find_area`` 匹配时经 ``gt(text, 'game')`` 按当前 i18 语言翻译
(en 翻译在 ``assets/text/game/en.po`` → 编译进 game.mo;cn 模式 gt 缺 cn
目录返回原文)。判定 area 的翻译词条:开拓等级/语言/图像/资源下载/简体中文。
点击目标全是固定位置控件;大世界是锁光标画面(screen 级 pc_alt=true),其上
的点击取 area 中心显式 pc_alt=True。

结构:每节点 = 自判定循环(每轮先判画面状态决定动作,达成才 success 出去)
—— 「点击」与「确认转移」必须在同一节点,拆开会让点击节点只回 retry 直到
重试上限(转移确认节点永远不会被调度)。

边界:op 的 gt 翻译方向 = 配置语言 —— 「界面英文 + 配置 cn」的漂移态下
中文锚匹配会失效,先用 MCP ``update_game_config(lang='en')`` 校正配置再跑
本 op(target='cn')。切换到 en 且英文文本资源未下载时,游戏弹资源下载确认
+ 使用确认两个弹窗(中文界面发起时弹窗为中文),本 op 自动逐个点确认。
"""

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen import screen_utils
from one_dragon.base.screen.screen_utils import FindAreaResultEnum
from one_dragon.utils.i18_utils import gt, update_default_lang
from one_dragon.utils.str_utils import find_in_list_with_fuzzy
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_WORLD_SCREEN: str = '大世界'
_MENU_SCREEN: str = '菜单'
_IMAGE_SCREEN: str = '设置-图像'
_LANG_SCREEN: str = '设置-语言'

_CN_VALUE: str = '简体中文'
_EN_VALUE: str = 'English'

#: 文本语言下拉当前值的判定词(OCR 相似匹配目标;下拉当前值是「值域解析」,
#: 不走 area.text 翻译 —— 同一值区在两种界面语言下显示不同语言名)
_LANG_VALUE_WORDS: dict[str, str] = {'cn': _CN_VALUE, 'en': _EN_VALUE}


class SwitchLanguageOp(SrOperation):
    """切换游戏内文本语言到目标语言,终点 = 语言已切换且配置已同步。

    参数:
        target_lang: 目标文本语言,取 ``GameLanguageEnum`` 的 value('cn'/'en')。

    失败:不在大世界(导航前置缺失)/ 离开语言设置页 / 弹窗处理超限。
    """

    def __init__(self, ctx: SrContext, target_lang: str = 'cn'):
        self.target_lang: str = target_lang
        self.target_value: str = _LANG_VALUE_WORDS.get(target_lang, _CN_VALUE)
        self.current_lang: str = ctx.game_config.lang
        SrOperation.__init__(self, ctx, op_name=gt('切换游戏语言'),
                             node_max_retry_times=30)

    @operation_node(name='入口核对', is_start_node=True)
    def check_entry(self) -> OperationRoundResult:
        """入口判定用语言无关锚:本 op 的合法发起场景含 English 界面(切回
        中文),画面级判定(文本锚组合)在英文界面必失效(实测判定 None),
        故以「角色图标」模板单锚判定 —— 大世界右上角头像图标,位置独有且
        语言无关。不在锚位 = 不在大世界,fail 交用户导航。"""
        if screen_utils.find_area(
                self.ctx, self.last_screenshot,
                _WORLD_SCREEN, '角色图标') != FindAreaResultEnum.TRUE:
            return self.round_fail(
                '未命中大世界角色图标(当前不在主界面,或画面被遮挡);'
                '请先回到主界面再运行本 op')
        return self.round_success()

    @node_from(from_name='入口核对')
    @operation_node(name='打开手机菜单')
    def open_menu(self) -> OperationRoundResult:
        """自判定循环:菜单展开锚(开拓等级,gt 按 i18 翻译)命中 → success;
        未命中 → 点手机菜单入口后重试。大世界是锁光标画面(screen 级
        pc_alt=true),area 级 pc_alt 默认 False,取中心显式 pc_alt=True
        点击(自由光标下 Alt+点击无害,先例 back_to_normal_world_plus)。"""
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _MENU_SCREEN, '读区-菜单判定') == FindAreaResultEnum.TRUE:
            return self.round_success()
        menu_area = self.ctx.screen_loader.get_area(_WORLD_SCREEN, '按钮-手机菜单')
        self.ctx.controller.click(menu_area.rect.center, pc_alt=True)
        # wait 必须 ≥ 菜单展开动画实测时长(2s 不够:判定跑在动画里,失败后再
        # 点击会把已展开的菜单点关,循环反复误触世界交互物)
        return self.round_retry('已点击手机菜单,等待菜单展开', wait=3)

    @node_from(from_name='打开手机菜单')
    @operation_node(name='打开设置')
    def open_settings(self) -> OperationRoundResult:
        """自判定循环:已在设置页(标题锚 语言/图像,gt 翻译)→ success 带
        status(游戏会记忆上次页签);仍在菜单 → 点设置齿轮后重试。"""
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _LANG_SCREEN, '标题-语言') == FindAreaResultEnum.TRUE:
            return self.round_success(status='ON_LANGUAGE')
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _IMAGE_SCREEN, '标题-图像') == FindAreaResultEnum.TRUE:
            return self.round_success(status='ON_IMAGE')
        settings_area = self.ctx.screen_loader.get_area(_MENU_SCREEN, '按钮-设置')
        self.ctx.controller.click(settings_area.rect.center)
        return self.round_retry('已点击设置,等待设置页打开', wait=2.5)

    @node_from(from_name='打开设置', status='ON_IMAGE')
    @operation_node(name='切到语言页签')
    def open_lang_tab(self) -> OperationRoundResult:
        """自判定循环:已在语言页 → success;仍在图像页 → 点语言页签后重试;
        两页都不在 → fail(设置页被意外关闭)。"""
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _LANG_SCREEN, '标题-语言') == FindAreaResultEnum.TRUE:
            return self.round_success()
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _IMAGE_SCREEN, '标题-图像') != FindAreaResultEnum.TRUE:
            return self.round_fail('离开设置页(标题判定未命中,意外画面)')
        tab_area = self.ctx.screen_loader.get_area(_IMAGE_SCREEN, '页签-语言')
        self.ctx.controller.click(tab_area.rect.center)
        return self.round_retry('已点击语言页签,等待切换', wait=1.5)

    @node_from(from_name='打开设置', status='ON_LANGUAGE')
    @node_from(from_name='切到语言页签')
    @operation_node(name='切换语言')
    def switch_language(self) -> OperationRoundResult:
        """语言页主循环:读当前值 → 展开下拉 → 点目标项 → 处理确认弹窗,
        以「文本语言当前值 = 目标」为出口(点了≠成了)。离开语言页 fail。"""
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _LANG_SCREEN, '标题-语言') != FindAreaResultEnum.TRUE:
            return self.round_fail('离开语言设置页(意外画面)')

        current_value = self._read_lang_value()
        if current_value == self.target_lang:
            return self.round_success(status='SWITCHED')

        # 弹窗态:资源下载确认 / 使用确认,两个弹窗的确认按钮同位,逐个确认
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _LANG_SCREEN, '弹窗-标题资源下载') == FindAreaResultEnum.TRUE:
            confirm_area = self.ctx.screen_loader.get_area(_LANG_SCREEN, '弹窗-确认按钮')
            self.ctx.controller.click(confirm_area.rect.center)
            return self.round_retry('弹窗已确认,等待下一状态(下载/应用)', wait=3)

        # 下拉展开态:目标语言项(text 锚,gt 翻译)可见则点它
        item_area_name = '项-简体中文' if self.target_lang == 'cn' else '项-English'
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _LANG_SCREEN, item_area_name) == FindAreaResultEnum.TRUE:
            item_area = self.ctx.screen_loader.get_area(_LANG_SCREEN, item_area_name)
            self.ctx.controller.click(item_area.rect.center)
            return self.round_retry(f'已点击目标语言项 {self.target_value}', wait=2)

        # 未展开:点文本语言下拉
        dropdown_area = self.ctx.screen_loader.get_area(_LANG_SCREEN, '下拉-文本语言')
        self.ctx.controller.click(dropdown_area.rect.center)
        return self.round_retry('已点开文本语言下拉', wait=1.5)

    @node_from(from_name='切换语言', status='SWITCHED')
    @operation_node(name='同步配置')
    def save_config(self) -> OperationRoundResult:
        """语言已切换:更新 game_config.lang + 刷新控制器窗口标题 + i18 默认语言。"""
        self.ctx.game_config.lang = self.target_lang
        self.ctx.controller.set_window_title(self.ctx.game_config.win_title)
        update_default_lang(self.ctx.game_config.lang)
        return self.round_success(
            f'游戏语言已切换为 {self.target_value},配置与窗口标题已同步')

    def _read_lang_value(self) -> str | None:
        """OCR 读「文本语言」下拉当前值,返回 cn/en/None(读不出)。

        值域解析不走 area.text 翻译:同一值区在两种界面语言下显示不同语言名
        (cn 界面显示「简体中文」,en 界面显示 'English'),双语词表直判。"""
        area = self.ctx.screen_loader.get_area(_LANG_SCREEN, '读区-文本语言值')
        results = self.ctx.ocr_service.get_ocr_result_list(
            self.last_screenshot, rect=area.rect)
        texts = [r.data for r in results]
        for lang_code, word in _LANG_VALUE_WORDS.items():
            if find_in_list_with_fuzzy(word, texts) is not None:
                return lang_code
        return None


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    op = SwitchLanguageOp(ctx, target_lang='en')
    op.execute()


if __name__ == '__main__':
    __debug()
