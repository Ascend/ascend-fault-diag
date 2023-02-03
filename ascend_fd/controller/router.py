# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
from ascend_fd.tool import path_check
from ascend_fd.log import echo
from ascend_fd.status import FileNotExistError
from ascend_fd.controller.controller import ParseController, DiagController


def router(args):
    """
    Perform parsing or diagnostic tasks based on command-line arguments
    :param args: the command-line arguments
    :return: None
    """
    try:
        args.input_path, args.output_path = path_check(args.input_path, args.output_path)
    except FileNotExistError as err:
        echo.error(err)
        return

    if args.cmd == "parse":
        controller = ParseController(args)
    else:
        controller = DiagController(args)
    controller.start_job()
