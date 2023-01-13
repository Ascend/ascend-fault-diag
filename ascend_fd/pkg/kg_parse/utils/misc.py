# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
import os


def split_all_path(str_path: str) -> list:
    path_parts = list()
    dir_path = os.path.abspath(str_path)
    head, tail = os.path.split(dir_path)
    while len(head) != len(dir_path):
        if len(tail) > 0:
            path_parts.insert(0, tail)
        dir_path = head
        head, tail = os.path.split(dir_path)
    path_parts.insert(0, head)
    return path_parts
