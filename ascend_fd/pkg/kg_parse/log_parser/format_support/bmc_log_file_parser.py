# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
from abc import ABC, abstractmethod


class BMCLogFileParser(ABC):
    VALID_PARAMS = {}
    TARGET_FILE_PATTERNS = []

    def __init__(self):
        super(BMCLogFileParser, self).__init__()

    @abstractmethod
    def parse(self, file_path: str) -> dict:
        return dict()

    def find_log(self, file_dict):
        files_list = []
        for target in self.TARGET_FILE_PATTERNS:
            if file_dict.get(target):
                files_list.extend(file_dict.get(target))
        return files_list
