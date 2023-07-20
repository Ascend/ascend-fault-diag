# coding: UTF-8
# Copyright (c) 2023. Huawei Technologies Co., Ltd. ALL rights reserved.
import argparse
import csv
import logging
import os.path
import subprocess
import time

HCCL_TOOL = '/usr/bin/hccn_tool'
FILE_NAME = "npu_{}_detail.csv"
FLAG = os.O_WRONLY | os.O_CREAT

# echo used to print error information
_echo_handler = logging.StreamHandler()
_echo_handler.setFormatter(logging.Formatter('%(message)s'))
echo = logging.getLogger("echo")
echo.addHandler(_echo_handler)
echo.setLevel(logging.INFO)


def command_lines():
    """
    This function is used to get arguments
    """
    arg_cmd = argparse.ArgumentParser(add_help=True, description="Ascend Fault Diag Metric Sample")
    arg_cmd.add_argument("-n", "--npu_num", type=int, default=8, help="NPU number")
    arg_cmd.add_argument("-it", "--interval_time", type=int, default=15, help="Interval time")
    arg_cmd.add_argument("-o", "--output_path", type=str, required=True, help="Output path")
    return arg_cmd.parse_args()


def collect_single_stat(device_id):
    """
    collect net stat for a single npu card
    :param device_id: device id
    """
    name_list = list()
    value_list = list()
    stat_cmd_list = [HCCL_TOOL, '-i', str(device_id), '-stat', '-g']
    cmd_res = subprocess.Popen(stat_cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    out_list = cmd_res.stdout.read().decode().split()
    for name_value in out_list:
        if name_value in ['packet', 'statistics']:
            continue
        name, value = name_value.split(':')
        value_list.append(value)
        name_list.append(name)
    return value_list, name_list


def create_file(npu_num, output_path):
    """
    create npu stat csv file for each npu
    :param npu_num: number of npu
    :param output_path: path to save csv files
    """
    header_row_data = ['timestamp', 'npu_index']
    _, name_list = collect_single_stat(0)
    header_row_data.extend(name_list)
    for device_id in range(npu_num):
        with os.fdopen(os.open(os.path.join(output_path, FILE_NAME.format(device_id)), FLAG, 0o640), 'w+') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(header_row_data)


def collect_stat(npu_num, output_path):
    """
    collect npu stat for each npu
    :param npu_num: number of npu
    :param output_path: path to write stat information
    """
    now = int(time.time())
    for device_id in range(npu_num):
        row_data = [now, device_id]
        value_list, _ = collect_single_stat(device_id)
        row_data.extend(value_list)
        with os.fdopen(os.open(os.path.join(output_path, FILE_NAME.format(device_id)), FLAG, 0o640), 'a') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(row_data)


def run_collect_task(npu_num, output_path, wait_time):
    """
    run collect npu stat task
    :param npu_num: number of npu
    :param output_path: path to write stat information
    :param wait_time: waiting time for each collection
    """
    create_file(npu_num, output_path)
    while True:
        try:
            collect_stat(npu_num, output_path)
        except Exception as e:
            echo.info(f"Collect npu data exception e: {e}\n")
        time.sleep(wait_time)


if __name__ == '__main__':
    try:
        arg = command_lines()
        run_collect_task(arg.npu_num, arg.output_path, arg.interval_time)
    except KeyboardInterrupt:
        echo.info(f"Collection stops\n")
