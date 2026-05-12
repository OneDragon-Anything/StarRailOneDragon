from datetime import datetime, timedelta

from one_dragon.base.operation.application_run_record import AppRunRecord
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.application.notify import notify_const

from sr_od.application.sr_application import SrApplication
from sr_od.context.sr_context import SrContext


class NotifyApp(SrApplication):

    def __init__(self, ctx: SrContext):
        SrApplication.__init__(self, ctx, notify_const.APP_ID,
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

        message = self.format_message()

        self.ctx.push_service.push(
            title=self.ctx.notify_config.title,
            content=message,
            image=self.last_screenshot,
        )

        if self.exist_failure:
            return self.round_fail(wait=5)
        else:
            return self.round_success(wait=5)

    def format_message(self) -> str:
        success = []
        failure = []

        group_config = self.ctx.app_group_manager.get_one_dragon_group_config(
            instance_idx=self.ctx.current_instance_idx,
        )
        for app_config in group_config.app_list:
            run_record: AppRunRecord = self.ctx.run_context.get_run_record(
                app_id=app_config.app_id,
                instance_idx=self.ctx.current_instance_idx,
            )
            if run_record is None:
                continue
            if not self.is_within_time(run_record.run_time):
                continue
            if run_record.run_status_under_now == AppRunRecord.STATUS_SUCCESS:
                success.append(app_config.app_name)
            if run_record.run_status_under_now == AppRunRecord.STATUS_FAIL:
                failure.append(app_config.app_name)
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

    def is_within_time(self, time_str: str) -> bool:
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
        return any(start_time <= candidate <= end_time for candidate in candidates)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    app = NotifyApp(ctx)
    app.execute()


if __name__ == '__main__':
    __debug()
