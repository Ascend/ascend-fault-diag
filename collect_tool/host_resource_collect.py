# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. All rights reserved.
import argparse
import json
import re
import os
import stat
import subprocess
import time


def command_line():
    """
    This function is used to get arguments
    """
    arg_cmd = argparse.ArgumentParser(add_help=True, description="Ascend Fault Diag Host Metrics Sample")
    arg_cmd.add_argument("-o", "--output_path", type=str, required=True, help="Output path")
    return arg_cmd.parse_args()


class HostResourceCollect:
    def __init__(self, output_path):
        """
        Init host resource collect params
        :param output_path: the output path
        """
        self.output_path = output_path
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

        self.core_num = self.get_core_num()
        self.top_res = {}

    @staticmethod
    def get_core_num():
        """
        Get cpu core number by 'cat /proc/cpuinfo | grep processor | wc -l'
        :return: the cpu max core num
        """
        cpu_cmd = "cat /proc/cpuinfo"
        cpu_res = subprocess.Popen(cpu_cmd.split(), shell=False, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        grep_cmd = "grep processor"
        grep_res = subprocess.Popen(grep_cmd.split(), shell=False, stdin=cpu_res.stdout, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
        core_cmd = "wc -l"
        core_res = subprocess.Popen(core_cmd.split(), shell=False, stdin=grep_res.stdout, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
        core_num = core_res.stdout.read().decode("utf-8").strip()
        return core_num

    @staticmethod
    def get_top_data():
        """
        Get the top result by 'top -o +RES -i -n 1 -b'
        :return: the top data
        """
        top_cmd = "top -o +RES -n 1 -b"
        top_popen = subprocess.Popen(top_cmd.split(), shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        res = top_popen.stdout.read().decode("utf-8").strip()
        # 处理top数据中的转义字符
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        res = ansi_escape.sub('', res)
        ansi_regex = r'\x1b(' \
                     r'(\[\??\d+[hl])|' \
                     r'([=<>a-kzNM78])|' \
                     r'([\(\)][a-b0-2])|' \
                     r'(\[\d{0,2}[ma-dgkjqi])|' \
                     r'(\[\d+;\d+[hfy]?)|' \
                     r'(\[;?[hf])|' \
                     r'(#[3-68])|' \
                     r'([01356]n)|' \
                     r'(O[mlnp-z]?)|' \
                     r'(/Z)|' \
                     r'(\d+)|' \
                     r'(\[\?\d;\d0c)|' \
                     r'(\d;\dR))'
        ansi_escape = re.compile(ansi_regex, flags=re.IGNORECASE)
        top_data = ansi_escape.sub('', res)
        return top_data

    def host_resource_collect(self):
        """
        Host resource collect by top data
        :return: host_metrics_{core_num}.json
        """
        last_time = None
        while True:
            # 记录本次采集的时间
            now_time = time.time()
            # 第一次采集没有last time, 赋予初始上次采集时间
            if not last_time:
                last_time = now_time - 60
            # 当前时间和上次采集时间的间隔为60s时采集一次
            if int(now_time - last_time) < 60:
                continue
            top_data = self.get_top_data()
            self.parse_single_top_data(top_data, int(now_time))
            with os.fdopen(os.open(os.path.join(self.output_path, f"host_metrics_{self.core_num}.json"),
                                   os.O_WRONLY | os.O_CREAT, stat.S_IWUSR | stat.S_IRUSR), 'w') as f:
                f.write(json.dumps(self.top_res))
            last_time = now_time

    def parse_single_top_data(self, top_data, top_time):
        """
        Parse the top data of 60s.(one piece)
        :param top_data: the top data (one piece)
        :param top_time: the time of top data collect
        :return: result save to top res
        """
        process_data_count = 0
        for line in top_data.splitlines():
            if process_data_count > 9:  # 采集RES前十大
                break

            match_mem = re.match(r'.*?KiB.*?Mem.*?free,.*?(\d+\+?).*?used,.*?buff/cache', line)
            match_process = re.match(
                r'.*?(\d+)\s*\w+\s+\d+\s+\d+\s+[\d\.]+g?\s+([\d\.]+g?)\s+\d+\s+\w\s+([\d\.]+)\s+[\d\.]+\s+[\d:\.]+ .+$',
                line)

            # 处理mem数据
            if match_mem:
                # 获取到的used数据有两种格式, 例如111/111+, 如果有'+', 替换成'0'
                self.top_res.setdefault("node_mem_used", list()).append(
                    [top_time, int(match_mem[1].replace('+', '0')) * 1024])
                continue

            # 处理process数据(process_info[0]: pid; process_info[1]: RES; process_info[2]: cpu)
            if match_process:
                process_data_count += 1
                process_info = list(match_process.groups())
                # 把获取到的RES数据单位换算成字节, 有两种格式, 例如：0.1g/111:
                # 有'g': 0.1*1024*1024*1024;
                # 无'g': 111*1024
                if process_info[1][-1] == "g":
                    process_info[1] = int(float(process_info[1][:-1]) * 1024 * 1024 * 1024)
                else:
                    process_info[1] = int(float(process_info[1]) * 1024)
                self.top_res.setdefault(f"node_rss_{process_info[0]}", list()).append([top_time, process_info[1]])
                self.top_res.setdefault(f"node_cpu_{process_info[0]}", list()).append([top_time, process_info[2]])


if __name__ == "__main__":
    args = command_line()
    HostResourceCollect(args.output_path).host_resource_collect()
