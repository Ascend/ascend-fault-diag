# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
import os
import subprocess

from ascend_fd.status import FileNotExistError, FileOpenError

VERSION_FILE_READ_LIMIT = 100
MAX_SIZE = 512 * 1024 * 1024
MB_SHIFT = 20


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


def safe_open(file, *args, **kwargs):
    """
    safe open file. Function will check if the file is a soft link or the file size is too large.
    :param file: file path.
    :param args: the open function parameters.
    :param kwargs: the open function parameters.
    :return: file_stream
    """
    if os.path.islink(file):
        raise FileOpenError(f"{os.path.basename(file)} should not be a symbolic link file.")
    file_real_path = os.path.realpath(file)
    file_stream = open(file_real_path, *args, **kwargs)
    file_info = os.stat(file_stream.fileno())
    if file_info.st_size > MAX_SIZE:
        file_stream.close()
        raise FileOpenError(f"the size of {os.path.basename(file)} should be less than {MAX_SIZE >> MB_SHIFT} MB.")
    return file_stream


def safe_chmod(file, mode):
    """
    safe chmod file.
    :param file: file path
    :param mode: file mode
    """
    with safe_open(file) as file_stream:
        os.fchmod(file_stream.fileno(), mode)


def popen_grep(rule, file=None, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    """
    use subprocess.popen to perform grep operations. file and stdin param must exist one.
    :param rule: grep rule
    :param file: the file
    :param stdin: the popen stdin
    :param stdout: the popen stdout, default PIPE
    :param stderr: the popen stderr, default PIPE
    :return: popen instance
    """
    cmd_list = ["/usr/bin/grep", rule]
    if file:
        with safe_open(file) as file_stream:
            return subprocess.Popen(cmd_list, shell=False, stdin=file_stream,
                                    stdout=stdout, stderr=stderr, encoding="utf-8")
    return subprocess.Popen(cmd_list, shell=False, stdin=stdin,
                            stdout=stdout, stderr=stderr, encoding="utf-8")
