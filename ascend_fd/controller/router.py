# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. All rights reserved.
from ascend_fd.tool import path_check
from ascend_fd.controller.controller import ParseController, DiagController


def router(args):
    """
    Perform parsing or diagnostic tasks based on command-line arguments
    :param args: the command-line arguments
    :return: None
    """
    args.input_path, args.output_path = path_check(args.input_path, args.output_path)
    if args.cmd == "parse":
        controller = ParseController(args)
    else:
        controller = DiagController(args)
    controller.start_job()
