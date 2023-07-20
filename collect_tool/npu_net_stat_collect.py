# coding: UTF-8
# Copyright (c) 2023. Huawei Technologies Co., Ltd. ALL rights reserved.
import argparse
import csv
import os.path
import subprocess
import time

HCCL_TOOL = '/usr/bin/hccn_tool'
file_name = "npu_{}_detail.csv"


def command_lines():
    arg_cmd = argparse.ArgumentParser(add_help=True, description="Ascend Fault Diag Metric Sample")
    arg_cmd.add_argument("-n", "--npu_num", type=int, default=8, help="NPU number")
    arg_cmd.add_argument("-wt", "--wait_time", type=int, default=15, help="Wait time")
    arg_cmd.add_argument("-ct", "--collect_time", type=int, default=60, help="Collect time")
    arg_cmd.add_argument("-o", "--output_path", type=str, required=True, help="Output path")
    return arg_cmd.parse_args()


def collect_single_stat(device_id):
    name_list = list()
    value_list = list()
    stat_cmd_list = [HCCL_TOOL, '-i', str(device_id), '-stat', '-g']
    cmd_res = subprocess.Popen(stat_cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    out_list = cmd_res.stdout.read().decode().split()
    for name_value in out_list:
        if name_value in ['packet', 'statistics']:
            continue
        name, value = name_list.split(':')
        value_list.append(value)
        name_list.append(name)
    return value_list, name_list


def create_file(npu_num, output_path):
    header_row_data = ['timestamp', 'npu_index']
    _, name_list = collect_single_stat(0)
    header_row_data.extend(name_list)
    for device_id in range(npu_num):
        with open(os.path.join(output_path, file_name.format(device_id)), "w+") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(header_row_data)


def collect_stat(npu_num, output_path):
    now = int(time.time())
    for device_id in range(npu_num):
        row_data = [now, device_id]
        value_list, _ = collect_single_stat(device_id)
        row_data.extend(value_list)
        with open(os.path.join(output_path, file_name.format(device_id)), "a") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(row_data)


def run_collect_task(npu_num, output_path, collect_time, wait_time):
    create_file(npu_num, output_path)
    end_time = int(time.time()) + collect_time
    while int(time.time()) < end_time:
        try:
            collect_stat(npu_num, output_path)
        except Exception as e:
            print("Collect npu data exception e:{}\n".format(e))
        time.sleep(wait_time)


if __name__ == '__main__':
    arg = command_lines()
    run_collect_task(arg.npu_num, arg.output_path, arg.collect_time, arg.wait_time)
