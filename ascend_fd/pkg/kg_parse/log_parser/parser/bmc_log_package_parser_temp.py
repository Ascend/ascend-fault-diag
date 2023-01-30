# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
from ascend_fd.pkg.kg_parse.log_parser.format_support import PlogParser, BMCLogFileParser, NpuInfoParser
from ascend_fd.pkg.kg_parse.log_parser.parser.bmc_log_data_descriptor import DataDescriptorOfNAIE
from ascend_fd.pkg.kg_parse.utils import logger
from ascend_fd.status import InnerError


class InvalidPackageTypeError(RuntimeError):
    pass


class UnpackPackageError(RuntimeError):
    pass


class BMCLogPackageParser(object):
    """日志包解析类"""
    VALID_PARAMS = {
        "package_repo_prefix": None,
        BMCLogFileParser.__name__: BMCLogFileParser.VALID_PARAMS,
        NpuInfoParser.__name__: NpuInfoParser.VALID_PARAMS,
    }

    def __init__(self, configs: dict = None):
        super(BMCLogPackageParser, self).__init__()
        if configs is not None:
            self.configs = configs
        else:
            self.configs = dict()
        self.desc = DataDescriptorOfNAIE()

        self.parsers = list()
        self.file_dict = configs.get("log_path", {})
        # 添加解析器
        self.add_parser(PlogParser)
        self.add_parser(NpuInfoParser)

    def add_parser(self, parser_cls):
        """添加解析器类"""
        if not issubclass(parser_cls, BMCLogFileParser):
            logger.error("'parser_cls' must be sub-class of BMCLogFileParser")
            raise InnerError("'parser_cls' must be sub-class of BMCLogFileParser")
        self.parsers.append(parser_cls())

    def parse(self):
        """解析方法"""
        self.desc.clear()
        for parser in self.parsers:
            files = parser.find_log(self.file_dict)
            if isinstance(parser, NpuInfoParser):
                res = parser.parse(files)
                if res:
                    self.desc.update(res)
                if not res.get("parse_next", False):
                    logger.info(f'parsing ends, current parser type:{parser.__class__.__name__}')
                    break
                continue

            for log_f in files:
                res = parser.parse(log_f)
                if res:
                    self.desc.update(res)
                if not res.get("parse_next", False):
                    logger.info(f'parsing ends, current parser type:{parser.__class__.__name__}')
                    break

    def get_log_data_descriptor(self):
        """返回当前log_data_descriptor实例"""
        return self.desc
