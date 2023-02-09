# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
import shutil
from pathlib import Path
from setuptools import setup, find_packages

from ascend_fd.tool import safe_open, VERSION_FILE_READ_LIMIT

DEFAULT_VERSION = "5.0.RC1"


def get_version():
    src_path = Path(__file__).absolute().parent
    verison_file = src_path.joinpath('ascend_fd', 'Version.info')
    if not verison_file.exists():
        return DEFAULT_VERSION
    with safe_open(verison_file, 'r') as f:
        return f.read(VERSION_FILE_READ_LIMIT)


def clean():
    cache_folder = ('ascend_fd.egg-info', "build*")
    for pattern in cache_folder:
        for folder in Path().glob(pattern):
            if folder.exists():
                shutil.rmtree(folder)


clean()
setup(
    name='ascend-fd',
    version=get_version(),
    description='ascend fault diag',
    packages=find_packages(),
    include_package_data=True,
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'ascend-fd=ascend_fd.cli.cli:main'
        ]
    }
)
