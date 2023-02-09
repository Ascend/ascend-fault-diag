# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
import argparse
from pathlib import Path

from ascend_fd.log import echo
from ascend_fd.controller import router
from ascend_fd.tool import safe_open, VERSION_FILE_READ_LIMIT


def command_line():
    """
    The command line interface. Commands contain:
    1. version
    2. parse
      -i, --input_path, the input path of origin data file
      -o, --output_path, the output path of parsed data file
    3. diag
      -i, --input_path, the input path of parsed data file
      -o, --output_path, the output path of diag result file
      -m, --mode, indicate whether a force-kill scenario is used
      -p, --print, indicate whether to print the result
    """
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
                          help="the output path of diag result file")
    diag_cmd.add_argument("-m", "--mode", type=int, default=0, choices=[0, 1],
                          help="indicate whether a force-kill scenario is used. "
                               "0: force-kill, 1: not force-kill. default 0.")
    diag_cmd.add_argument("-p", "--print", action="store_true",
                          help="indicate whether to print the result. "
                               "If no parameter is specified, the result is not printed.")

    return args.parse_args()


def show_version():
    src_path = Path(__file__).absolute().parent.parent
    version_file = src_path.joinpath("Version.info")
    with safe_open(version_file, 'r') as f:
        echo.info(f"ascend-fd v{f.read(VERSION_FILE_READ_LIMIT)}")


def main():
    args = command_line()
    if args.cmd == "version":
        show_version()
        return
    router(args)
