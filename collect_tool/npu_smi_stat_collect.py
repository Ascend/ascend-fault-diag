# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. ALL rights reserved.
import os
import csv
import stat
import time
import argparse
import subprocess
import logging


HEADER = ["time", "dev_id", "hbm_rate", "aicore_rate", "rated_freq", "freq", "temp", "power"]
MODE = stat.S_IWUSR | stat.S_IRUSR


# echo used to print error information
_echo_handler = logging.StreamHandler()
_echo_handler.setFormatter(logging.Formatter('%(message)s'))
echo = logging.getLogger("echo")
echo.addHandler(_echo_handler)
echo.setLevel(logging.INFO)


def command_line():
    command = argparse.ArgumentParser(add_help=True, description="NPU state collector")
    command.add_argument("-o", "--output", type=str, required=True, help="save dir path")
    command.add_argument("-it", "--interval_time", type=int, default=15, help="collect interval time")
    return command.parse_args()


def collect_job(output_path, interval_time):
    """
    Collect npu state information
    :param output_path: save dir path
    :param interval_time: collect interval time
    :return:
    """
    output_path = os.path.realpath(output_path)
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    file_name = "npu_smi_{}_details.csv"
    for i in range(8):  # 8张卡
        with os.fdopen(os.open(os.path.join(output_path, file_name.format(i)),
                               os.O_WRONLY | os.O_CREAT, MODE), "w") as file:
            writer = csv.writer(file)
            writer.writerow(HEADER)  # 写入csv表头
    end_time = int(time.time() + (3600 * 72)) # 可以不限制，限制时间可保证后台执行忘记关闭后不会一直执行
    start_time = -1
    while True:
        now_time = int(time.time())
        if now_time >= end_time:
            break
        if start_time > 0 and now_time - start_time < interval_time:
            continue
        start_time = now_time
        try:
            collect_state_info(now_time, output_path)
        except Exception as e:
            echo.info("collect npu data exception: {}", e)


def collect_state_info(now_time, output_path):
    """
    Collect state info
    :param now_time: now time
    :param output_path: save dir path
    """
    file_name = "npu_smi_{}_details.csv"
    cmd_list = ["npu-smi", "info",    "-t", "common", "-i"]
    grep_cmd = ["grep", "-E", "HBM|Aicore Usage Rate|Freq|curFreq|Temperature|Power"]
    for i in range(8):
        npu_info = subprocess.Popen([*cmd_list, str(i)], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        grep_info = subprocess.Popen(grep_cmd, shell=False, stdin=npu_info.stdout,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        row_data = [now_time, i]
        for line in grep_info.stdout.readlines():
            line_list = line.decode().strip().split(":")
            row_data.append(line_list[1])
        with os.fdopen(os.open(os.path.join(output_path, file_name.format(i)), os.O_WRONLY, MODE), "a") as file:
            writer = csv.writer(file)
            writer.writerow(row_data[:len(HEADER)])


if __name__ == "__main__":
    cli = command_line()
    collect_job(cli.output, cli.interval_time)