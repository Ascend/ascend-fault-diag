# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
import argparse

from ascend_fd.parse.controller import ParseController
from ascend_fd.diag.controller import DiagController
from ascend_fd.tool import path_check

VERSION = "0.3"


def version(args):
    print(f"ascend-fd v{VERSION}")


def parse(args):
    args.input_path, args.output_path = path_check(args.input_path, args.output_path)
    controller = ParseController(args)
    controller.start_job()


def diag(args):
    args.input_path, args.output_path = path_check(args.input_path, args.output_path)
    controller = DiagController(args)
    controller.start_job()


def command_line():
    args = argparse.ArgumentParser(add_help=True, description="Ascend Fault Diag")
    sub_arg = args.add_subparsers(dest="cmd", required=True)

    sub_arg.add_parser("version", description="show ascend-fd version", help="show ascend-fd version")

    parse_cmd = sub_arg.add_parser("parse", help="parse origin log files")
    parse_cmd.add_argument("-i", "--input_path", type=str, required=True,
                           help="the input path of origin data file")
    parse_cmd.add_argument("-o", "--output_path", type=str, required=True,
                           help="the output path of parsed data file")

    diag_cmd = sub_arg.add_parser("diag", help="diag parsed log files")
    diag_cmd.add_argument("-i", "--input_path", type=str, required=True,
                          help="the input path of parsed data file")
    diag_cmd.add_argument("-o", "--output_path", type=str, required=True,
                          help="the output path of result file")
    diag_cmd.add_argument("-t", "--task", type=int, default=0, choices=[0, 1, 2, 3],
                          help="the diag task id, please input one of [0,1,2,3]. "
                               "0: execute all task, 1: kg diag task, 2: node diag task, 3: net diag task."
                               "default 0.")
    diag_cmd.add_argument("-m", "--mode", type=int, default=0, choices=[0, 1],
                          help="Indicates whether a force-kill scenario is used. "
                               "0: force-kill, 2: not force-kill. default 0.")
    diag_cmd.add_argument("-p", "--print", action="store_true",
                          help="Indicate whether to print the result. "
                               "If no paramter is specified, the result is not printed.")

    return args.parse_args()


def main():
    func_map = {
        "version": version,
        "parse": parse,
        "diag": diag
    }
    args = command_line()
    func_map.get(args.cmd)(args)
