# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
import os
import stat
import subprocess

from ascend_fd.status import FileNotExistError, FileOpenError


MAX_SIZE = 1024 * 1024 * 1024
GB_SHIFT = 30


def path_check(input_path, output_path):
    """
    check if the path exists.
    :param input_path: the input data path.
    :param output_path: the output data path.
    :return: (input_real_path, output_real_path)
    """
    input_path = os.path.realpath(input_path)
    if not os.path.exists(input_path):
        raise FileNotExistError("The input path does not exist.")
    output_path = os.path.realpath(output_path)
    if not os.path.exists(output_path):
        raise FileNotExistError("The output path does not exist.")
    return input_path, output_path


def verify_file(file):
    """
    check whether the file has at least the read permission.
    :param file: file path.
    """
    if int(oct(os.stat(file).st_mode)[-3:]) < 400:
        raise FileOpenError("failed to parse log due to insufficient permission.")


def safe_open(file, *args, **kwargs):
    """
    safe open file. Function will check if the file is a soft link or the file size is too large.
    :param file: file path.
    :param args: the open function parameters.
    :param kwargs: the open function parameters.
    :return: file_stream
    """
    file_real_path = os.path.realpath(file)
    file_stream = open(file_real_path, *args, **kwargs)
    file_info = os.stat(file_stream.fileno())
    if stat.S_ISLNK(file_info.st_mode):
        file_stream.close()
        raise FileOpenError(f"{os.path.basename(file)} should not be a symbolic link file.")
    if file_info.st_size > MAX_SIZE:
        file_stream.close()
        raise FileOpenError(f"the size of {os.path.basename(file)} should be less than {MAX_SIZE >> GB_SHIFT} GB.")
    return file_stream


def safe_chmod(file, mode):
    """
    safe chmod file.
    """
    with safe_open(file) as file_stream:
        os.fchmod(file_stream.fileno(), mode)


def popen_grep(para_list, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    cmd_list = ["/usr/bin/grep"] + para_list
    if stdin:
        return subprocess.Popen(cmd_list, shell=False, stdin=stdin, stdout=stdout, stderr=stderr)
    return subprocess.Popen(cmd_list, shell=False, stdout=stdout, stderr=stderr)
