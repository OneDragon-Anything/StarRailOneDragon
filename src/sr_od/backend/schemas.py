from dataclasses import asdict, dataclass, field

from pydantic import BaseModel, Field

from one_dragon.base.screen.screen_match import ScreenMatch


@dataclass
class OcrText:
    """OCR 识别的单条文本。

    Attributes:
        text: 识别出的文本内容。
        pc_rect: 文本框 ``[x1, y1, x2, y2]``(1080p 游戏空间,与建档 pc_rect 同形)。
    """

    text: str
    pc_rect: list[int]


@dataclass
class AnalyzeScreenResult:
    """画面识别结果(纯识别数据;失败经异常通道上报,不占返回结构)。

    Attributes:
        ocr_texts: 全图原始 OCR 文本列表(include_ocr=False 时为空;读屏幕零散文字时显式开启)。
        screens: 画面匹配结果(精准命中=[1 个 is_precise=True];否则 top_n 个
            is_precise=False 候选)。决策优先看 screens。
        screenshot_path: 本次 analyze 新存的截图绝对路径;实时+save_image=True 时有值,
            其余 None。**有值 ⟺ 这次实时模式新存了张图**(离线模式不存)。
        extras: 精准命中画面且该画面注册了额外识别器(recognizer)时,填充识别器返回的
            结构化领域事实(画面特定结构,如备战画面的前后台 / 备战席角色 + 金币 / 阶段);
            否则 None。识别器异常不中断 analyze(extras=None,详见日志)。离线模式
            (screenshot 传入)同样跑。详见 ``docs/develop/sr_od/backend/screen-recognizers.md``。
        extras_doc: 与 ``extras`` 平级的字段说明(数据归数据、说明归说明,不塞进 extras):
            精准命中且识别器声明了 ``extras_doc`` 时,原样回填该声明(字段名 → 一行语义,
            含取值格式 / 读不到时的值 / 可靠性注意);否则 None。调用方拿到 extras 的同时
            就拿到字段语义,零跳查;识别器异常时仍返回(extras=None 时可对照排障)。
    """

    ocr_texts: list[OcrText]
    screens: list[ScreenMatch] = field(default_factory=list)
    screenshot_path: str | None = None
    extras: dict | None = None
    extras_doc: dict[str, str] | None = None


# —— analyze_screen 的 MCP 输出模型(字段描述经 outputSchema 随工具列表对模型可见;
#    字段名与框架 dataclass 同构,转换用 from_backend 一步完成)——


class OcrTextOut(BaseModel):
    """散落 OCR 文字(未确认的裸文字,不带建档语义)。"""

    text: str = Field(description='识别出的文字内容')
    pc_rect: list[int] = Field(description='文字框 [x1,y1,x2,y2]，1080p 游戏空间')


class AreaMatchOut(BaseModel):
    """单个区域的命中详情(实测结果)。"""

    area_name: str = Field(description='区域名，确认过的游戏语义，见名知义')
    pc_rect: list[int] = Field(
        description='本次实测命中框 [x1,y1,x2,y2]，1080p 游戏空间'
                    '（唯一例外：离线传入非 1080p 图片时是该图像素空间）')
    matched_text: str | None = Field(
        default=None, description='实际识别到的文字；模板区（图标匹配）为 null')
    match_target: str = Field(
        default='', description='该区登记的原始匹配目标（期望文本或模板 id）')


class ScreenMatchOut(BaseModel):
    """单个画面的匹配结果。"""

    screen_name: str = Field(
        description='画面名，可作为 goto_screen / get_screen_detail / upsert_screen_area 的定位入参')
    is_precise: bool = Field(
        description='画面身份是否已确认；False 表示仅候选，画面未确认，应读图确认所在画面')
    areas: list[AreaMatchOut] = Field(
        default_factory=list, description='本次命中的区域详情')


class AnalyzeScreenOut(BaseModel):
    """analyze_screen 的返回结构(纯识别数据;失败经错误通道上报,不占本结构)。"""

    screens: list[ScreenMatchOut] = Field(
        default_factory=list,
        description='画面匹配结果；精准命中时为 1 个 is_precise=True，否则为若干候选')
    ocr_texts: list[OcrTextOut] = Field(
        default_factory=list, description='未确认的裸文字（include_ocr=True 才返回，默认空）')
    screenshot_path: str | None = Field(
        default=None, description='本次识别落盘的截图路径（save_image=True 时有值），供读图复用')
    extras: dict | None = Field(
        default=None, description='精准命中画面登记的结构化数据（未登记为 null）')
    extras_doc: dict[str, str] | None = Field(
        default=None, description='extras 各字段的语义说明，与 extras 平级对照读（未登记为 null）')

    @classmethod
    def from_backend(cls, result: AnalyzeScreenResult) -> 'AnalyzeScreenOut':
        """框架识别结果 dataclass → MCP 输出模型。

        dataclass 字段与 Out 模型同构同名,asdict 展开后由 pydantic 递归校验
        完成嵌套转换;dataclass 字段增删时本转换自动跟随,无需手改。
        """
        return cls(**asdict(result))


class WindowStatusOut(BaseModel):
    """游戏窗口状态。"""

    win_title: str | None = Field(
        default=None,
        description='controller 缓存的预期窗口标题(来自配置)，游戏未启动时也可能非 None；'
                    '勿据本字段判断窗口是否存在')
    is_win_valid: bool = Field(
        description='窗口句柄是否有效；判断游戏是否在跑/窗口是否存在看本字段')
    is_win_active: bool = Field(description='窗口当前是否处于激活状态')
    is_win_scale: bool = Field(
        description='窗口是否处于非标准尺寸(客户区 ≠ 1920×1080)；截图仍会归一到标准分辨率')
    x: int | None = Field(default=None, description='窗口左上角横坐标；不可用时为 null')
    y: int | None = Field(default=None, description='窗口左上角纵坐标；不可用时为 null')
    width: int | None = Field(default=None, description='窗口客户区宽度；不可用时为 null')
    height: int | None = Field(default=None, description='窗口客户区高度；不可用时为 null')

    @classmethod
    def from_backend(cls, result: 'WindowStatus') -> 'WindowStatusOut':
        """框架窗口状态 dataclass → MCP 输出模型(同构 asdict 转换)。"""
        return cls(**asdict(result))


class RunStatusOut(BaseModel):
    """运行状态查询结果(MCP/HTTP 共享,传输无关)。"""

    state: str = Field(
        description='idle(无运行)/running(运行中,含 stop 后退出中的间隙)/'
                    'success/failed/stopped(终态,固化)')
    source: str | None = Field(
        default=None, description='触发方 "mcp"/"http"；终态后保留,反映最近一次来源')
    app: str | None = Field(
        default=None, description='operation 类名；终态后保留(上次跑的什么)')
    started_at: str | None = Field(
        default=None, description='ISO 时间戳,可作 tail 日志锚点；不可用时为 null')
    duration_seconds: float | None = Field(
        default=None, description='截至查询时的耗时(秒)；不可用时为 null')
    current_node: str | None = Field(
        default=None, description='运行中当前节点名；终态为 null')
    retry_count: int | None = Field(
        default=None, description='运行中当前节点重试次数；终态为 null')
    last_status: str | None = Field(
        default=None, description='仅终态有值:成功描述 / 失败原因 / '
                    '已停止[来源](来源如 mcp:stop_run / hook:* / gui:*)；运行中为 null')
    failed_node: str | None = Field(
        default=None, description='仅 failed:失败停在哪一步(排障锚点)；否则为 null')

    @classmethod
    def from_backend(cls, result: 'RunStatusResult') -> 'RunStatusOut':
        """框架运行状态 dataclass → MCP 输出模型(同构 asdict 转换)。"""
        return cls(**asdict(result))


class ApplicationInfoOut(BaseModel):
    """单个可运行应用的信息。"""

    app_id: str = Field(description='应用 ID,运行/配置类工具的定位入参')
    app_name: str = Field(description='应用显示名')
    enabled_in_one_dragon: bool = Field(description='是否已在一条龙组启用')
    in_standalone_list: bool = Field(description='是否出现在独立应用列表')
    is_active_standalone: bool = Field(
        description='是否为 GUI「独立应用运行」当前选中项')


class ScreenCreateOut(BaseModel):
    """新建画面结果(create_screen 返回)。"""

    screen_id: str = Field(description='画面 ID(英文 snake_case,作 yml 文件名)')
    screen_name: str = Field(description='画面名(中文,作 analyze_screen / goto_screen 的匹配键)')

    @classmethod
    def from_backend(cls, result: 'ScreenCreateResult') -> 'ScreenCreateOut':
        """框架新建画面结果 dataclass → MCP 输出模型(同构 asdict 转换)。"""
        return cls(**asdict(result))


class AreaMutationOut(BaseModel):
    """画面区域变更结果(upsert/delete_screen_area 返回)。"""

    screen_name: str = Field(description='目标画面名')
    area_name: str = Field(description='本次变更的 area 名(同画面内唯一,作匹配键)')
    action: str = Field(
        description="实际发生的动作:'inserted'(新增)/'updated'(整体更新,已存在时全字段覆盖)/'deleted'(删除)")
    area_count: int = Field(description='变更后该画面的 area 总数')

    @classmethod
    def from_backend(cls, result: 'AreaMutationResult') -> 'AreaMutationOut':
        """框架 area 变更结果 dataclass → MCP 输出模型(同构 asdict 转换)。"""
        return cls(**asdict(result))


class GotoScreenOut(BaseModel):
    """画面导航结果(goto_screen 返回;arrived=False 是带现场的正常结果,非错误)。"""

    arrived: bool = Field(
        description='是否已到达目标画面;False 为正常中断结果(非错误),据 reason 判断如何继续')
    current_screen: str | None = Field(
        description='最终确认所在的画面名(可直接作 goto_screen 目标或 analyze_screen 核对);'
                    '画面无法识别(过渡帧/未建档)时为 null')
    steps: list[str] = Field(
        description='实际执行的跳转步骤,每步「画面 --区域--> 画面」;中断时含已完成部分')
    reason: str | None = Field(
        description="arrived=False 时的中断原因(无路径/area 未命中/点击失败/停机中断等,"
                    "文案带下一步提示);arrived=True 时为 null")

    @classmethod
    def from_backend(cls, result: 'GotoScreenResult') -> 'GotoScreenOut':
        """框架导航结果 dataclass → MCP 输出模型(同构 asdict 转换)。"""
        return cls(**asdict(result))


class ApplicationListResultOut(BaseModel):
    """应用运行配置概览(list_applications 返回)。"""

    current_instance_idx: int = Field(
        description='当前激活实例的下标(账号下标)：idx N → config/0N 目录'
                    '(idx 1 → config/01 账号01)，不是 config/0<idx+1>；'
                    '改某实例配置前先据此定位目录')
    active_standalone_app_id: str | None = Field(
        default=None, description='GUI「独立应用运行」当前选中的 app_id；无则 null')
    applications: list[ApplicationInfoOut] = Field(
        default_factory=list, description='可运行应用列表及各运行模式状态')

    @classmethod
    def from_backend(cls, result: 'ApplicationListResult') -> 'ApplicationListResultOut':
        """框架应用列表 dataclass → MCP 输出模型(同构 asdict 转换)。"""
        return cls(**asdict(result))


class ScreenNamesOut(BaseModel):
    """画面名清单(list_screen_names 返回)。"""

    screen_names: list[str] = Field(
        description='全部画面名(排序后)。screen_name 是画面建档的匹配键(中文，须完全一致)，'
                    '作 goto_screen / get_screen_detail / upsert_screen_area 的定位入参')


class InputTextOut(BaseModel):
    """文本输入结果(input_text 返回)。"""

    method: str = Field(
        description="实际输入方式:'clipboard'(剪贴板粘贴,支持中文/特殊字符)/"
                    "'keyboard'(逐键);use_clipboard=None 时跟随 game_config.type_input_way")
    masked_text: str = Field(
        description='实际输入文本的脱敏回显(密码类已打码)')

    @classmethod
    def from_backend(cls, result: 'InputTextResult') -> 'InputTextOut':
        """框架输入结果 dataclass → MCP 输出模型(同构 asdict 转换)。"""
        return cls(**asdict(result))


@dataclass
class WindowStatus:
    """游戏窗口状态。

    Attributes:
        win_title: controller 缓存的游戏窗口标题(预期标题,从配置来);游戏未启动时
            仍可能为该预期常量、非 None。判窗口是否存在/游戏是否在跑请看 is_win_valid,
            勿据 win_title 是否非空判断。
        is_win_valid: 窗口句柄是否有效。
        is_win_active: 窗口当前是否处于激活状态。
        is_win_scale: 窗口是否处于非标准尺寸(客户区 ≠ 1920×1080;True=已缩放,
            截图仍会被归一到标准分辨率)。
        x: 窗口左上角横坐标；不可用时为 None。
        y: 窗口左上角纵坐标；不可用时为 None。
        width: 窗口客户区宽度；不可用时为 None。
        height: 窗口客户区高度；不可用时为 None。
    """

    win_title: str | None
    is_win_valid: bool
    is_win_active: bool
    is_win_scale: bool
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None


@dataclass
class RunStatusResult:
    """运行状态查询结果(MCP/HTTP 共享,传输无关)。

    Attributes:
        state: idle/running/success/failed/stopped。
        source: 触发方 "mcp"/"http";终态后保留,反映最近一次来源。
        app: operation 类名(如 "OpenAndEnterGame");终态后保留。
        started_at: ISO 时间戳,可作 tail 日志锚点;不可用时 None。
        duration_seconds: 截至查询时的耗时;不可用时 None。
        current_node: 运行中当前节点名;终态 None。
        retry_count: 运行中当前节点重试次数;终态 None。
        last_status: OperationResult.status(失败原因 / "已停止[来源]"(stop_source,如 mcp:stop_run / hook:* / gui:*) / 成功描述);运行中 None。
        failed_node: 仅 failed:失败停在哪一步;否则 None。
    """
    state: str
    source: str | None = None
    app: str | None = None
    started_at: str | None = None
    duration_seconds: float | None = None
    current_node: str | None = None
    retry_count: int | None = None
    last_status: str | None = None
    failed_node: str | None = None


@dataclass
class ApplicationInfo:
    """可通过 backend 触发运行的应用信息。

    字段同时描述「一条龙组里是否启用」和「独立应用列表里是否出现」，
    这样 MCP/HTTP 客户端能区分完整一条龙运行与单个应用运行。
    """

    app_id: str
    app_name: str
    enabled_in_one_dragon: bool = False
    in_standalone_list: bool = False
    is_active_standalone: bool = False


@dataclass
class ApplicationListResult:
    """应用运行配置概览。

    用于 ``list_applications`` / ``GET /game/applications`` 返回当前实例下
    可运行应用、GUI 当前选中的独立应用，以及各应用在不同运行模式中的状态。

    Attributes:
        current_instance_idx: 当前激活实例的 idx(账号下标)。**idx N → config/0N 目录**
            (idx 1 → config/01 账号01,idx 2 → config/02 账号02),**不是** config/0<idx+1>。
            激活实例看 ``config/one_dragon.yml`` 的 ``instance_list`` 里 ``active: true`` 项;
            改某实例配置前先据此定位目录,别把 idx 当目录号做偏移。
        active_standalone_app_id: GUI「独立应用运行」当前选中的 app_id;无则 None。
        applications: 可运行应用列表及各运行模式状态。
    """

    current_instance_idx: int
    active_standalone_app_id: str | None
    applications: list[ApplicationInfo]


@dataclass
class AreaMutationResult:
    """画面 area 变更结果(传输无关)。

    Attributes:
        screen_name: 目标画面名(中文,建档匹配键)。
        area_name: 本次变更的 area 名(同画面内唯一)。
        action: 实际发生的动作 inserted(新增)/updated(整体更新)/deleted(删除)。
        area_count: 变更后该画面的 area 总数。
    """

    screen_name: str
    area_name: str
    action: str
    area_count: int


@dataclass
class ScreenCreateResult:
    """新建画面结果(传输无关)。

    Attributes:
        screen_id: 画面 ID(英文 snake_case,yml 文件名)。
        screen_name: 画面名(中文,建档匹配键)。
    """

    screen_id: str
    screen_name: str


@dataclass
class RunStartResult:
    """运行受理结果(block=False 立即返回,传输无关)。

    Attributes:
        app: 本次运行的 operation 类名。
        started_at: 受理时间 ISO 时间戳(可作 tail 日志锚点)。
    """

    app: str | None = None
    started_at: str | None = None


class RunStartOut(BaseModel):
    """运行受理结果(run_* 工具 block=False 立即返回;进度用 get_run_status 轮询)。"""

    app: str | None = Field(
        default=None, description='本次运行的 operation 类名')
    started_at: str | None = Field(
        default=None, description='受理时间 ISO 时间戳;可作 tail 日志锚点')

    @classmethod
    def from_backend(cls, result: 'RunStartResult') -> 'RunStartOut':
        """框架受理结果 dataclass → MCP 输出模型(同构 asdict 转换)。"""
        return cls(**asdict(result))


@dataclass
class RunFinishResult:
    """运行终态摘要(block=True 阻塞到结束返回,传输无关)。

    Attributes:
        success: 运行是否成功。
        status: 终态描述(成功描述 / 失败原因 / 已停止[来源])。
        data: op 的数据通道(读数类 op 携带结果);无数据为 None。
    """

    success: bool
    status: str
    data: dict | None = None


class RunFinishOut(BaseModel):
    """运行终态摘要(run_* 工具 block=True 阻塞返回)。"""

    success: bool = Field(description='运行是否成功')
    status: str = Field(
        description='终态描述:成功描述 / 失败原因 / 已停止[来源]')
    data: dict | None = Field(
        default=None, description='op 的数据通道(读数类 op 携带结果,如抽卡记录读取);无数据为 null')

    @classmethod
    def from_backend(cls, result: 'RunFinishResult') -> 'RunFinishOut':
        """框架终态摘要 dataclass → MCP 输出模型(同构 asdict 转换)。"""
        return cls(**asdict(result))


@dataclass
class RunStopResult:
    """停止信号结果(传输无关)。

    Attributes:
        stopped: 是否发出了停止信号;False=当前无运行(幂等正常结果,目标态已成立)。
        source: 被停运行的触发方;无运行时 None。
    """

    stopped: bool
    source: str | None = None


class RunStopOut(BaseModel):
    """停止信号结果(stop_run 返回)。"""

    stopped: bool = Field(
        description='是否发出了停止信号;False=当前无运行(幂等结果,目标态已成立)')
    source: str | None = Field(
        default=None, description='被停运行的触发方(mcp/http/hook:*/gui:*);无运行时 null')

    @classmethod
    def from_backend(cls, result: 'RunStopResult') -> 'RunStopOut':
        """框架停止结果 dataclass → MCP 输出模型(同构 asdict 转换)。"""
        return cls(**asdict(result))


@dataclass
class GotoScreenResult:
    """画面导航结果(传输无关;arrived=False 是带现场的正常结果,非错误)。

    Attributes:
        arrived: 是否已到达目标画面;False 为正常中断结果。
        current_screen: 最终确认所在画面名;画面无法识别时 None。
        steps: 实际执行的跳转步骤(「画面 --区域--> 画面」);中断时含已完成部分。
        reason: 中断原因;arrived=True 时 None。
    """

    arrived: bool
    current_screen: str | None
    steps: list[str]
    reason: str | None = None


@dataclass
class InputTextResult:
    """文本输入结果(传输无关)。

    Attributes:
        method: 实际输入方式 'clipboard'(剪贴板粘贴)/'keyboard'(逐键);
            use_clipboard=None 时由 game_config.type_input_way 决定。
        masked_text: 实际输入文本的脱敏回显;密码类已打码。
    """

    method: str
    masked_text: str


@dataclass
class OperationParam:
    """自定义 operation 的单个参数(纯反射得到,不实例化类)。

    Attributes:
        name: 参数名(已剔除 self/ctx)。
        annotation: 类型注解的可读字符串(如 ``str``、``ChargePlanItem``、``int``)。
        required: 是否必填(无默认值)。
        default: 默认值的字符串表示;必填参数为 None。
        json_serializable: 该参数类型是否可经 JSON 标量/列表/字典传入
            (str/int/float/bool/list/dict/Optional → True;自定义数据类 → False)。
        coercible: 该参数虽非 JSON 原生类型,但可从 dict 反序列化构造
            (``@dataclass`` + 有 ``from_dict``)。``run_operation`` 对这类参数接受 dict 值,
            实例化前用 ``from_dict`` 转成实例。
    """

    name: str
    annotation: str
    required: bool
    default: str | None = None
    json_serializable: bool = True
    coercible: bool = False


@dataclass
class OperationInfo:
    """单个 operation 的反射信息。

    Attributes:
        op_id: 定位标识,``<dotted module path>.<ClassName>``。
        class_name: 类名。
        module: 定义模块的 dotted path。
        params: ``__init__`` 参数 schema(已剔除 self/ctx)。
    """

    op_id: str
    class_name: str
    module: str
    params: list[OperationParam] = field(default_factory=list)


@dataclass
class OperationListResult:
    """operation 扫描结果。

    Attributes:
        operations: 通过三重过滤的可运行 operation 信息列表。
        failures: 单模块 import 失败记录(``{module}: {error}`` 格式),扫描不中断。
    """

    operations: list[OperationInfo] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
