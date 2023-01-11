# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
import multiprocessing
import os
import platform
import socket
import sys
from os.path import dirname, abspath


_cwd = dirname(abspath(__file__))
_prj_path = dirname(_cwd)


class PlatformInfo(object):
    """os class"""
    ALLOWED_SYSTEM = {"Windows", "Linux"}

    def __init__(self):
        super(PlatformInfo, self).__init__()
        self.system = platform.system()
        self.is_windows = True if self.system == "Windows" else False
        self.is_linux = True if self.system == "Linux" else False
        if self.system not in PlatformInfo.ALLOWED_SYSTEM:
            raise RuntimeError("unsupported platform '%s'" % self.system)
        self.python_version = dict()
        self.python_version['version'] = platform.python_version()
        py_ver_tuple = platform.python_version_tuple()
        self.python_version['major'] = int(py_ver_tuple[0])
        self.python_version['minor'] = int(py_ver_tuple[1])
        self.python_version['rev'] = int(py_ver_tuple[2])
        self.core_count = multiprocessing.cpu_count()
        self.os_platform = os.name
        self.hostname = socket.gethostname()
        exec_path, exec_name = os.path.split(sys.argv[0])
        self.exec_path = exec_path
        if exec_name.endswith(".py"):
            self.exec_name = exec_name[0:-3]
        elif exec_name.endswith(".exe"):
            self.exec_name = exec_name[0:-4]
        elif exec_name.endswith(".sh"):
            self.exec_name = exec_name[0:-3]
        else:
            self.exec_name = exec_name
        self.project_path = _prj_path
        self.config_path = os.path.join(_prj_path, 'etc')
        self.output_path = os.path.join(_prj_path, 'output')
        self.bin_path = os.path.join(_prj_path, 'bin')
        self.log_path = os.path.join(_prj_path, 'logs')
        self.utils_path = os.path.join(_prj_path, 'logs')
        self.resource_path = os.path.join(_prj_path, 'resource')
        self.path_variables = {
            '$(PRJ_ROOT)': self.project_path,
            '$(CONFIG_DIR)': self.config_path,
            '$(OUTPUT_DIR)': self.output_path,
            '$(BIN_DIR)': self.bin_path,
        }


PLATFORM_INFO = PlatformInfo()
