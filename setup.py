# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
import shutil
from pathlib import Path
from setuptools import setup, find_packages


def get_version():
    from ascend_fd.cli.cli import VERSION
    return VERSION


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
