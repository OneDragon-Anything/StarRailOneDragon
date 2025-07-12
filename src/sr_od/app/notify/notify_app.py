from typing import List
from datetime import datetime, timedelta

from one_dragon.base.notify.push import Push
from one_dragon.base.operation.application_run_record import AppRunRecord
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt

from sr_od.app.sr_application import SrApplication
from sr_od.app.sr_one_dragon_app import SrOneDragonApp
from sr_od.context.sr_context import SrContext


class NotifyApp(SrApplication):

    def __init__(self, ctx: SrContext):
        SrApplication.__init__(self, ctx, 'notify',
                              op_name=gt('通知'),
                              need_check_game_win=True,
                              run_record=ctx.notify_record)

    @operation_node(name='发送通知', is_start_node=True)
    def notify(self) -> OperationRoundResult:
        """
        发送通知
        :return:
        """
        self.exist_failure = False

        def is_within_time(time_str) -> bool:
            end_time = datetime.now()
            try:
                # 解析输入的时间字符串，格式为月-日 时:分
                parsed_time = datetime.strptime(time_str, "%m-%d %H:%M")
            except ValueError:
                # 时间格式不正确
                return False

            candidates = []
            # 生成当前年份和前一年的候选时间
            for year in [end_time.year, end_time.year - 1]:
                try:
                    candidate = parsed_time.replace(year=year)
                    candidates.append(candidate)
                except ValueError:
                    # 处理无效日期（如闰年的2月29日）
                    continue

            start_time = end_time - timedelta(hours=3)
            for candidate in candidates:
                # 检查候选时间是否在最近三小时内且不超过当前时间
                if start_time <= candidate <= end_time:
                    return True
            return False

        # 消息格式化
        def format_message(results: List[SrApplication]) -> str:
            success = []
            failure = []

            for item in results:
                if is_within_time(item.run_record.run_time):
                    if item.run_record.run_status_under_now == AppRunRecord.STATUS_SUCCESS:
                        success.append(item.op_name)
                    if item.run_record.run_status_under_now == AppRunRecord.STATUS_FAIL:
                        failure.append(item.op_name)
                        self.exist_failure = True

            parts = [f"一条龙运行完成："]
            has_failure = bool(failure)
            has_success = bool(success)

            if has_failure:
                parts.append(f"❌ 失败指令：{', '.join(failure)}")
            elif has_success:
                parts.append(f"全部成功✅")

            if has_success:
                parts.append(f"✅ 成功指令：{', '.join(success)}")
            elif not has_failure:
                parts.append(f"全部失败❌")

            return "\n".join(parts)

        message = format_message(SrOneDragonApp.get_app_list(self))
        image = None
        if self.ctx.push_config.send_image:
            image = self.save_screenshot_bytes()

        pusher = Push(self.ctx)
        pusher.send(message, image)

        if self.exist_failure:
            return self.round_fail(wait=5)
        else:
            return self.round_success(wait=5)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    app = NotifyApp(ctx)
    app.execute()


if __name__ == '__main__':
    __debug()