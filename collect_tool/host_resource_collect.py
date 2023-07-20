# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. All rights reserved.
import argparse
import json
import re
import os
import subprocess
import time


def command_line():
    arg_cmd = argparse.ArgumentParser(add_help=True, description="Ascend Fault Diag Host Metrics Sample")
    arg_cmd.add_argument("-o", "--output_path", type=str, default="./", help="OUTPUT_PATH")
    return arg_cmd.parse_args()


class HostResourceCollect:
    def __init__(self, output_path):

        self.output_path = output_path
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

        self.core_num = self.get_core_num()
        self.top_res = {}

    @staticmethod
    def get_core_num():
        """
        Get cpu core number.
        """
        cpu_res = subprocess.Popen(["cat", "/proc/cpuinfo"], shell=False, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        grep_res = subprocess.Popen(["grep", "processor"], shell=False, stdin=cpu_res.stdout, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
        core_res = subprocess.Popen(["wc", "-l"], shell=False, stdin=grep_res.stdout, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
        res = core_res.stdout.read().decode("utf-8").strip()
        return res

    @staticmethod
    def get_top_data():
        """
        Get the top result by popen
        """
        top_cmd = "top -o +RES -i -n 1"
        top_popen = subprocess.Popen(top_cmd.split(), shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        res = top_popen.stdout.read().decode("utf-8").strip()
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
                     r'(0[mlnp-z]?)|' \
                     r'(/Z)|' \
                     r'(\d+)|' \
                     r'(\[\?\d;\d0c)|' \
                     r'(\d;\dR))'
        ansi_escape = re.compile(ansi_regex, flags=re.IGNORECASE)
        res = ansi_escape.sub('', res)
        return res

    def host_resource_collect(self):
        """
        Top info collect
        :return: host_metrics_{core_num}.json
        """
        start_time = None
        while True:
            if not start_time:
                start_time = time.time()
            end_time = time.time()
            # 间隔60s采集一次
            if int(end_time - start_time) != 60:
                continue
            start_time = time.time()
            top_data = self.get_top_data()
            self.parse_single_top_data(top_data, int(start_time))
            with open(os.path.join(self.output_path, f"host_metrics_{self.core_num}.json"), 'w') as f:
                f.write(json.dumps(self.top_res))

    def parse_single_top_data(self, top_data, top_tme):
        """
        Parse the top data of 60s.(one piece)
        :return: result save to top res
        """
        top_count = 0
        for line in top_data.splitlines():
            if top_count > 9:  # 采集rss前十大
                break
            top_count += 1
            match_mem = re.match(r'.*?KiB.*?Mem.*?free,.*?(\d+\+?).*?used,.*?buff/cache', line)
            match_process = re.match(
                r'.*?(\d+)\s*\w+\s+\d+\s+\d+\s+[\d\.]+g?\s+([\d\.]+g?)\s+\d+\s+\w\s+([\d\.]+)\s+[\d\.]+\s+[\d:\.]+ .+$',
                line)

            # 处理mem数据
            if match_mem:
                self.top_res.setdefault("node_mem_used", list()).append(
                    [top_tme, int(match_mem[1].replace('+', '0')) * 1024])
                continue

            # 处理process数据(process_info[0]: pid, process_info[1]: RES, process_info[2]: cpu)
            if match_process:
                process_info = list(match_process.groups())
                if process_info[1][-1] == "g":
                    process_info[1] = int(float(process_info[1][:-1]) * 1024 * 1024 * 1024)
                else:
                    process_info[1] = int(float(process_info[1]) * 1024)
                self.top_res.setdefault(f"node_rss_{process_info[0]}", list()).append([top_tme, process_info[1]])
                self.top_res.setdefault(f"node_cpu_{process_info[0]}", list()).append([top_tme, process_info[2]])


if __name__ == "__main__":
    args = command_line()
    HostResourceCollect(args.output_path).host_resource_collect()
