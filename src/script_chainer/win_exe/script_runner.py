# 添加进程退出的 pid 检测方式

import argparse
import datetime
import subprocess
import time

import psutil
from colorama import init, Fore, Style

from one_dragon.base.operation.one_dragon_context import ContextRunStateEnum
from one_dragon.utils import cmd_utils
from one_dragon.utils.log_utils import log
from script_chainer.config.script_config import ScriptConfig, ScriptChainConfig, CheckDoneMethods
import os
import errno

# from script_chainer.context.script_chainer_context import ScriptChainerContext


# # 全局变量用于Push实例
# _push_instance = None
#
# def get_push_instance():
#     """获取Push实例，延迟初始化"""
#     global _push_instance
#     if _push_instance is None:
#         try:
#             ctx = ScriptChainerContext()
#             _push_instance = Push(ctx)
#         except Exception as e:
#             log.error(f'初始化Push实例失败: {e}')
#             _push_instance = None
#     return _push_instance
#
# def get_logger():
#     logger = logging.getLogger('OneDragon')
#     logger.handlers.clear()
#     logger.setLevel(logging.INFO)
#
#     formatter = logging.Formatter('[%(asctime)s.%(msecs)03d] [%(filename)s %(lineno)d] [%(levelname)s]: %(message)s', '%H:%M:%S')
#
#     log_file_path = os.path.join(os_utils.get_path_under_work_dir('.log'), 'log.txt')
#     archive_handler = TimedRotatingFileHandler(log_file_path, when='midnight', interval=1, backupCount=3, encoding='utf-8')
#     archive_handler.setLevel(logging.INFO)
#     archive_handler.setFormatter(formatter)
#     logger.addHandler(archive_handler)
#
#     return logger
#
#
# log = get_logger()
from sr_od.context.sr_context import SrContext


def is_process_existed(process_name) -> bool:
    """
    判断进程是否存在
    """
    if process_name is None or len(process_name) == 0:
        return False

    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] == process_name:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return False


def kill_process(process_name):
    """
    关闭一个进程
    """
    if process_name is None or len(process_name) == 0:
        return

    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] == process_name:
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chain', type=str, default='01', help='脚本链名称')
    parser.add_argument('--shutdown', action='store_true', help='结束后关机')

    return parser.parse_args()


def print_message(message: str, level="INFO"):
    if level == "INFO":
        log.info(message)
    elif level == "WARN":
        log.warn(message)
    elif level == "ERROR":
        log.error(message)


def is_pid_running(pid):
    try:
        # 检查进程是否存在
        process = psutil.Process(pid)

        # 进一步验证（防止PID复用）：获取进程创建时间
        create_time = process.create_time()

        # 返回进程状态（running/sleeping等）
        return {
            "alive": True,
            "status": process.status(),
            "create_time": create_time
        }

    except psutil.NoSuchProcess:
        return {"alive": False, "reason": "process_exited"}
    except psutil.AccessDenied:
        # 权限不足但进程可能存在，标记为"不确定"
        return {"alive": None, "reason": "access_denied"}
    except psutil.ZombieProcess:
        return {"alive": False, "reason": "zombie_process"}
    except Exception as e:
        # 捕获所有其他异常（如系统调用失败）
        return {"alive": None, "reason": f"error: {str(e)}"}


def run_script(script_config: ScriptConfig, ctx: SrContext = None) -> None:
    """
    运行脚本
    """
    script_path = script_config.script_path
    args = script_config.script_arguments

    invalid_message = script_config.invalid_message
    if invalid_message is not None:
        print_message(f'脚本配置不合法 跳过运行 {invalid_message}')
        return

    command = [script_path]
    if args and args.strip():
        command.extend(args.split())

    start_time = time.time()

    subprocess_created: bool = False
    subprocess_create_time: float = start_time  # 子进程创建的时间
    process = None

    while True:
        now = time.time()
        if process is None:
            try:
                subprocess_create_time = now
                if script_config.script_working_directory is None:
                    process = subprocess.Popen(command)
                else:
                    process = subprocess.Popen(command,cwd=script_config.script_working_directory)
                print_message(f'创建脚本子进程 {script_path}')
            except Exception:
                print_message(f'创建子进程失败 {script_path}')
                log.error(f'创建子进程失败 {script_path}', exc_info=True)
        else:
            process_result = process.poll()
            if process_result is None:
                process_result_display = '运行中'
            elif process_result == 0:
                process_result_display = '运行成功'
            else:
                process_result_display = '运行失败'

            print_message(f'检测脚本子进程运行 {process_result_display}')
            # None = 子进程正在运行中 未返回结果
            # 0 = 子进程运行结束 可能脚本的启动器自身启动了其它进程
            if process_result is None or process_result == 0:
                if now - subprocess_create_time >= 5:  # 已经运行超过5秒
                    subprocess_created = True
            else:  # 子进程运行结束 返回异常 尝试重新调用
                process = None

        if subprocess_created:  # 子进程正常
            break

        if now - start_time > 20:  # 超时
            break

        time.sleep(1)

    if not subprocess_created:
        print_message(f'子进程创建失败 {script_path}')
        return
    else:
        print_message(f'脚本子进程创建成功 {script_path}', level='PASS')

    script_ever_existed: bool = False  # 脚本进程是否存在
    game_ever_existed: bool = False  # 游戏进程是否存在
    is_done: bool = False
    while True:
        if ((script_config.stop_chain_when_pause_pressed and ctx.context_running_state == ContextRunStateEnum.PAUSE)
                or ctx.context_running_state == ContextRunStateEnum.STOP):
            break

        game_current_existed: bool = is_process_existed(script_config.game_process_name)
        game_closed = game_ever_existed and not game_current_existed
        game_ever_existed = game_ever_existed or game_current_existed

        if len(script_config.game_display_name) > 0:
            if not game_ever_existed:
                print_message(f'等待打开 {script_config.game_display_name}')
            elif game_current_existed:
                print_message(f'正在运行 {script_config.game_display_name}', level='PASS')
            else:
                print_message(f'运行结束 {script_config.game_display_name}', level='PASS')
        else:
            print_message(f'等待 {script_config.check_done_display_name}')

        # 添加进程退出的 pid 检测方式
        if script_config.script_process_name == 'None':
            pid_status = is_pid_running(process.pid)
            script_current_existed: bool = pid_status.get('alive') and (pid_status.get('create_time') is not None) and pid_status.get('create_time') < subprocess_create_time + 5
        else:
            script_current_existed: bool = is_process_existed(script_config.script_process_name)
        script_closed = script_ever_existed and not script_current_existed
        script_ever_existed = script_ever_existed or script_current_existed

        if script_config.check_done == CheckDoneMethods.GAME_OR_SCRIPT_CLOSED.value.value:
            if game_closed or script_closed:
                is_done = True
                print_message(f'游戏或脚本被关闭 {script_config.game_display_name}', level='PASS')
        elif script_config.check_done == CheckDoneMethods.GAME_CLOSED.value.value:
            if game_closed:
                is_done = True
                print_message(f'游戏被关闭 {script_config.game_display_name}', level='PASS')
        elif script_config.check_done == CheckDoneMethods.SCRIPT_CLOSED.value.value:
            if script_closed:
                is_done = True
                print_message(f'脚本被关闭 {script_config.script_display_name}', level='PASS')
        else:
            print_message(f'未知的检查结束方式 {script_config.check_done}', level='ERROR')
            is_done = True

        now = time.time()

        if now - start_time > script_config.run_timeout_seconds:
            is_done = True
            print_message(f'脚本运行超时 {script_config.script_display_name}', level='ERROR')

        if is_done:
            break

        time.sleep(1)

    if script_config.kill_script_after_done:
        print_message(f'尝试关闭脚本进程 {script_config.script_process_name}')
        try:
            process.kill()
        except Exception:
            log.error('关闭脚本子进程失败', exc_info=True)

        try:
            if script_config.script_process_name is not None and len(script_config.script_process_name) > 0:
                kill_process(script_config.script_process_name)
        except Exception:
            log.error('关闭脚本进程失败', exc_info=True)

    if script_config.kill_game_after_done:
        print_message(f'尝试关闭游戏进程 {script_config.game_process_name}')
        try:
            if script_config.game_process_name is not None and len(script_config.game_process_name) > 0:
                kill_process(script_config.game_process_name)
        except Exception:
            log.error('关闭游戏进程失败', exc_info=True)


def run():
    init(autoreset=True)
    args = parse_args()
    module_name: str = args.chain
    chain_config: ScriptChainConfig = ScriptChainConfig(module_name)
    # push_instance = get_push_instance()
    try:
        if not chain_config.is_file_exists():
            print_message(f'脚本链配置不存在 {module_name}', "ERROR")
        else:
            for i in range(len(chain_config.script_list)):
                script_config = chain_config.script_list[i]
                # if script_config.notify_start:
                #     if push_instance is not None:
                #         push_instance.send(
                #             content=f'脚本链 {module_name} 开始运行: {script_config.script_display_name}'
                #         )
                run_script(script_config)
                # if script_config.notify_done:
                #     if push_instance is not None:
                #         push_instance.send(
                #             content=f'脚本链 {module_name} 运行结束: {script_config.script_display_name}'
                #         )
                if i < len(chain_config.script_list) - 1:
                    print_message('10秒后开始下一个脚本')
                    time.sleep(10)

            print_message('已完成全部脚本')

        # if args.shutdown:
        #     cmd_utils.shutdown_sys(60)
        #     print_message('准备关机')

    #     print_message('5秒后关闭本窗口')
    #     time.sleep(5)
    finally:
        # # 清理Push资源
        # global _push_instance
        # if _push_instance is not None:
        #     try:
        #         _push_instance.ctx.after_app_shutdown()
        #     except Exception as e:
        #         log.error(f'清理Push资源失败: {e}')
        pass


if __name__ == '__main__':
    run()
