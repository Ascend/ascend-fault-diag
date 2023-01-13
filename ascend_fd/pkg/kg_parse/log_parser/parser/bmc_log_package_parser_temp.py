# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
from ascend_fd.pkg.kg_parse.log_parser.format_support import HcclAnalysisResultParserEvent, PlogParser, \
    BMCLogFileParser, VirtualEventsParser, NpuInfoParser
from ascend_fd.pkg.kg_parse.log_parser.parser.bmc_log_data_descriptor import DataDescriptorOfNAIE, \
    DataDescriptorOfDFSBrain
from ascend_fd.pkg.kg_parse.utils import logger


class InvalidPackageTypeError(RuntimeError):
    pass


class UnpackPackageError(RuntimeError):
    pass


class BMCLogPackageParser(object):
    """日志包解析类"""
    VALID_PARAMS = {
        "package_repo_prefix": None,
        BMCLogFileParser.__name__: BMCLogFileParser.VALID_PARAMS,
        HcclAnalysisResultParserEvent.__name__: HcclAnalysisResultParserEvent.VALID_PARAMS,
        NpuInfoParser.__name__: NpuInfoParser.VALID_PARAMS,
    }
    DESC_MAPPING = {
        "NAIE": DataDescriptorOfNAIE,
        "DFSBrain": DataDescriptorOfDFSBrain,
    }

    def __init__(self, configs: dict = None):
        super(BMCLogPackageParser, self).__init__()
        if configs is not None:
            self.configs = configs
        else:
            self.configs = dict()
        if "platform_type" in self.configs and self.configs["platform_type"] in self.DESC_MAPPING:
            self.desc = self.DESC_MAPPING[self.configs["platform_type"]](self.configs["data_descriptor"])
        else:
            raise RuntimeError("the platform is error")
        if "log_type" not in configs["file_parser"]:
            self.configs["file_parser"]["log_type"] = configs["log_type"]
        if "platform_type" not in configs["file_parser"]:
            self.configs["file_parser"]["platform_type"] = configs["platform_type"]
        self.parsers = list()
        self.file_list = configs["log_path_list"]
        # 添加解析器
        self.add_parser(HcclAnalysisResultParserEvent)
        self.add_parser(PlogParser)
        self.add_parser(NpuInfoParser)
        self.add_parser(VirtualEventsParser)

    def add_parser(self, parser_cls):
        """添加解析器类"""
        if issubclass(parser_cls, BMCLogFileParser):
            self.parsers.append(parser_cls(self.configs["file_parser"]))
        elif issubclass(parser_cls, VirtualEventsParser):
            self.parsers.append(parser_cls(self.configs["file_parser"]))
        else:
            raise TypeError("'parser_cls' must be sub-class of BMCLogFileParser")

    def parse(self):
        """解析方法"""
        self.desc.clear()
        for _parser in self.parsers:
            _files = _parser.find_log(self.file_list)
            _files.sort(reverse=False, key=lambda x: len(x))
            if isinstance(_parser, NpuInfoParser):
                _res = _parser.parse(_files)
                if _res is False:
                    continue
                if _res:
                    self.desc.update(_res)
                if "parse_next" in _res and _res["parse_next"] is False:
                    logger.info(f'parsing ends, current parser type:{_parser.__class__.__name__}')
                    break
                continue

            for _log_f in _files:
                _res = _parser.parse(_log_f)
                if _res is False:
                    continue
                if _res:
                    self.desc.update(_res)
                if "parse_next" in _res and _res["parse_next"] is False:
                    logger.info(f'parsing ends, current parser type:{_parser.__class__.__name__}')
                    break

    def get_log_data_descriptor(self):
        """返回当前log_data_descriptor实例"""
        return self.desc
