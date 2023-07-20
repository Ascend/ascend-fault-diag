# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. ALL rights reserved.
import os
import csv
import time
import argparse
import subprocess


HEADER = ["time", "dev_id", "power", "rated_freq", "freq", "temp", "hbm_rate"]


def command_line():
    cli = argparse.ArgumentParser(add_help=True, description="NPU state collector")
    cli.add_argument("-o", "--output", type=str, required=True, help="save dir path")
    cli.add_argument("-it", "--interval_time", type=int, default=15, help="collect interval time")
    return cli.parse_args()


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
        with open(os.path.join(output_path, file_name.format(i)), "w+") as file:
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
            print("collect npu data exception: {}\n".format(e))


def collect_state_info(now_time, output_path):
    """
    Collect state info
    :param now_time: now time
    :param output_path: save dir path
    """
    file_name = "npu_smi_{}_details.csv"
    cmd_list = ["npu-smi", "info",    "-t", "common", "-i"]
    grep_cmd = ["grep", "-E", "HBM|Freq|curFreq|Temperature|Power"]
    for i in range(8):
        npu_info = subprocess.Popen([*cmd_list, str(i)], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        grep_info = subprocess.Popen(grep_cmd, shell=False, stdin=npu_info.stdout,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        row_data = [now_time]
        for line in grep_info.stdout.readlines():
            line_list = line.decode().strip().split(":")
            row_data.append(line_list[1])
        with open(os.path.join(output_path, file_name.format(i)), "a") as file:
            writer = csv.writer(file)
            writer.writerow(row_data)


if __name__ == "__main__":
    cli = command_line()
    collect_job(cli.output, cli.interval_time)
