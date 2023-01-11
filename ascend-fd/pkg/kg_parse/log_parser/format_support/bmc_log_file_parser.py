# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
from abc import ABC, abstractmethod

from ascend_fd.pkg.kg_parse.utils import PathFilter


class BMCLogFileParser(ABC):
    VALID_PARAMS = {}
    TARGET_FILE_PATTERNS = []

    def __init__(self, configs: dict = None):
        super(BMCLogFileParser, self).__init__()
        self.configs = configs
        self.filters = list()
        self.__load_filters()

    def __load_filters(self):
        for item in self.TARGET_FILE_PATTERNS:
            _filter = PathFilter()
            _filter.add_path_pattern(item, sep='/')
            self.filters.append(_filter)

    @abstractmethod
    def parse(self, file_path: str) -> dict:
        return dict()

    def find_log(self, file_list):
        logs = list()
        for _f in self.filters:
            _res = _f.filter(file_list)
            if len(_res) == 0:
                continue
            for _path in _res:
                if _path not in logs:  # 存在不同规则筛选出相同的文件的情况，需要去重
                    logs.append(_path)
        return logs

