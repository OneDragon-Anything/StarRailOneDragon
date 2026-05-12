import concurrent.futures
import os
import re
from cv2.typing import MatLike
from typing import Optional, Tuple, List

from one_dragon.base.config.yaml_operator import YamlOperator
from one_dragon.utils import yolo_config_utils, os_utils
from one_dragon.yolo.detect_utils import DetectFrameResult
from one_dragon.yolo.yolo_utils import get_github_model_download_url
from one_dragon.yolo.yolov8_onnx_det import Yolov8Detector
from sr_od.config.model_config import YOLO_RELEASE_TAG
from sr_od.config.game_const import OPPOSITE_DIRECTION

_EXECUTOR = concurrent.futures.ThreadPoolExecutor(thread_name_prefix='sr_yolo_detector', max_workers=1)


class SrDetectClass:

    def __init__(self, name: str, cate: str, label: str):
        self.name = name
        self.cate = cate
        # 标签去除中文
        self.label = re.sub(r'[\u4e00-\u9fa5]', '', label).replace('--', '-')


class YoloScreenDetector:

    def __init__(self,
                 sim_uni_model_name: Optional[str] = None,
                 world_patrol_model_name: Optional[str] = None,
                 standard_resolution_w: int = 1920,
                 standard_resolution_h: int = 1080
                 ):
        self.standard_resolution_w: int = standard_resolution_w
        self.standard_resolution_h: int = standard_resolution_h

        self.sim_uni_yolo: Optional[Yolov8Detector] = None  # 模拟宇宙用的模型
        self.sim_uni_model_name: str = sim_uni_model_name
        if sim_uni_model_name is not None:
            self.sim_uni_yolo = Yolov8Detector(
                model_download_url=get_github_model_download_url(YOLO_RELEASE_TAG),
                model_parent_dir_path=yolo_config_utils.get_model_category_dir('sim_uni'),
                model_name=sim_uni_model_name,
            )

        self.world_patrol_yolo: Optional[Yolov8Detector] = None  # 锄大地用的模型
        self.world_patrol_model_name: str = world_patrol_model_name
        if world_patrol_model_name is not None:
            self.world_patrol_yolo = Yolov8Detector(
                model_download_url=get_github_model_download_url(YOLO_RELEASE_TAG),
                model_parent_dir_path=yolo_config_utils.get_model_category_dir('world_patrol'),
                model_name=world_patrol_model_name
            )

        self.last_async_future: Optional[concurrent.futures.Future] = None  # 上一次异步回调
        self.last_detect_result: Optional[DetectFrameResult] = None  # 上一次识别结果

        self.detect_info_list: List[SrDetectClass] = []  # 所有可识别的信息
        self.label_2_class: dict[str, SrDetectClass] = {}
        self.world_patrol_label_list: List[str] = []  # 锄大地时需要识别的标签

        self.read_detect_info()

    def init_world_patrol_model(self, model_name: str, gpu: bool = False) -> None:
        """
        重新初始化模型
        """
        if model_name == self.world_patrol_model_name:
            return
        self.world_patrol_model_name = model_name
        self.world_patrol_yolo = Yolov8Detector(
            model_download_url=get_github_model_download_url(YOLO_RELEASE_TAG),
            model_parent_dir_path=yolo_config_utils.get_model_category_dir('world_patrol'),
            model_name=model_name,
            gpu=gpu
        )

    def init_sim_uni_model(self, model_name: str, gpu: bool = False) -> None:
        """
        重新初始化模型
        """
        if model_name == self.sim_uni_model_name:
            return
        self.sim_uni_model_name = model_name
        self.sim_uni_yolo = Yolov8Detector(
            model_download_url=get_github_model_download_url(YOLO_RELEASE_TAG),
            model_parent_dir_path=yolo_config_utils.get_model_category_dir('sim_uni'),
            model_name=model_name,
            gpu=gpu
        )

    def detect_should_attack_in_world(self, screen: MatLike, detect_time: float) -> DetectFrameResult:
        """
        大世界画面下使用 识别当前的可攻击状态
        - 有被怪物锁定的标志
        - 有可攻击的标志
        :param screen: 游戏画面
        :param detect_time: 识别时间
        :return:
        """
        yolo = None
        if self.world_patrol_yolo is not None:
            yolo = self.world_patrol_yolo
        elif self.sim_uni_yolo is not None:
            yolo = self.sim_uni_yolo

        if yolo is not None:
            self.last_detect_result = yolo.run(screen, conf=0.85, run_time=detect_time,
                                               category_list=['界面提示被锁定', '界面提示可攻击'])
        else:
            self.last_detect_result = DetectFrameResult(raw_image=screen, run_time=detect_time, results=[])

        return self.last_detect_result

    def should_attack_in_world(self, screen: MatLike, detect_time: float) -> bool:
        """
        同步阻塞的方法
        大世界画面下使用 判断目前是否处于应该攻击的状态
        :param screen: 游戏画面
        :param detect_time: 识别时间
        :return:
        """
        frame_result = self.detect_should_attack_in_world(screen, detect_time)
        return len(frame_result.results) > 0

    def detect_should_attack_in_world_async(self, screen: MatLike, detect_time: float) -> Tuple[bool, Optional[concurrent.futures.Future]]:
        """
        异步进行运算，如果上一次还没有结束，则放弃本次运算。
        大世界画面下使用 识别当前的可攻击状态。
        - 有被怪物锁定的标志
        - 有可攻击的标志
        :param screen: 游戏画面
        :param detect_time: 识别时间
        :return: 是否提交成功, 提交后的回调
        """
        if self.last_async_future is not None and not self.last_async_future.done():
            return False, None
        self.last_async_future = _EXECUTOR.submit(self.detect_should_attack_in_world, screen, detect_time)
        return True, self.last_async_future

    def should_attack_in_world_last_result(self, detect_time: float, timeout_seconds: float = 0.5) -> bool:
        """
        取上一次的结果
        大世界画面下使用 判断目前是否处于应该攻击的状态
        :param detect_time: 识别时间
        :param timeout_seconds: 多久秒之前的结果被认为是无效的
        :return:
        """
        if self.last_detect_result is None:
            return False

        if self.last_detect_result.run_time + timeout_seconds < detect_time:
            return False

        return len(self.last_detect_result.results) > 0

    def get_attack_direction(self, screen: MatLike,
                             last_direction: Optional[str],
                             detect_time: float) -> Tuple[bool, str]:
        """
        根据画面结果 判断下一次的攻击方向
        多个候选方向时 优先选上一次反方向的 防止产生的位置越走越远
        :param screen: 游戏画面
        :param last_direction: 上一次的攻击方向
        :param
        :param detect_time: 识别时间
        :return: 是否有警告, 攻击方向
        """
        direction_cnt: dict[str, int] = {'w': 0, 'a': 0, 's': 0, 'd': 0}

        frame_result = self.detect_should_attack_in_world(screen, detect_time)
        for result in frame_result.results:
            x, y = result.center
            if x < self.standard_resolution_w // 3:
                direction_cnt['a'] = direction_cnt['a'] + 1
            elif x > self.standard_resolution_w // 3 * 2:
                direction_cnt['d'] = direction_cnt['d'] + 1
            else:
                # 怪在后面追赶的时候 感叹号显示在最上面 跟怪在前面的情况一样，因此无法很好判断在前面还是在后面
                direction_cnt['w'] = direction_cnt['w'] + 1
                direction_cnt['s'] = direction_cnt['s'] + 1

        max_direction: Optional[str] = None
        max_cnt: int = 0
        for direction, cnt in direction_cnt.items():
            if cnt > max_cnt:
                max_cnt = cnt
                max_direction = direction
        with_alert: bool = max_cnt > 0

        if last_direction is not None:
            if max_cnt == 0 or direction_cnt[OPPOSITE_DIRECTION[last_direction]] > 0:
                # 目前没有识别到警告 或者 有警告在上一次的反方向的 优先用反方向
                return with_alert, OPPOSITE_DIRECTION[last_direction]

        # 其他情况 优先取警告最多的方向
        # 没有告警时候优先向后攻击 因为这是来的方向 向后的话不容易陷入卡死
        target_direction = 's' if max_direction is None else max_direction
        return with_alert, target_direction

    def read_detect_info(self) -> None:
        """
        加载识别目标列表
        """
        self.detect_info_list = []
        self.label_2_class: dict[str, SrDetectClass] = {}
        self.world_patrol_label_list = []

        file_path = os.path.join(
            os_utils.get_path_under_work_dir('assets', 'game_data'),
            'detect_info.yml'
        )

        yaml_data = YamlOperator(file_path)
        for data_item in yaml_data.data:
            info = SrDetectClass(**data_item)
            self.detect_info_list.append(info)
            self.label_2_class[info.label] = info

            if info.cate in ['界面提示被锁定', '界面提示可攻击']:
                self.world_patrol_label_list.append(info.label)

    def sim_uni_combat_detect(self, screen: MatLike, screenshot_time: float) -> DetectFrameResult:
        """
        模拟宇宙中战斗楼层使用的识别
        :return:
        """
        return self.sim_uni_yolo.run(screen, run_time=screenshot_time,
                                     category_list=['普通怪', '界面提示被锁定', '界面提示可攻击',
                                                    '模拟宇宙下层入口', '模拟宇宙下层入口未激活'])

def __debug():
    from sr_od.context.sr_context import SrContext
    ctx = SrContext()
    ctx.init_for_world_patrol()

    from one_dragon.utils import debug_utils
    import time
    screen = debug_utils.get_debug_image('1')
    ctx.yolo_detector.detect_should_attack_in_world(screen, time.time())


if __name__ == '__main__':
    __debug()