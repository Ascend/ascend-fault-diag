# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
from ascend_fd.pkg.kg_parse.log_parser.format_support import PlogParser, BMCLogFileParser, NpuInfoParser
from ascend_fd.pkg.kg_parse.log_parser.parser.bmc_log_data_descriptor import DataDescriptorOfNAIE
from ascend_fd.pkg.kg_parse.utils import logger
from ascend_fd.status import InnerError


class BMCLogPackageParser(object):
    """log parser base class"""
    VALID_PARAMS = {
        "package_repo_prefix": None,
        BMCLogFileParser.__name__: BMCLogFileParser.VALID_PARAMS,
        NpuInfoParser.__name__: NpuInfoParser.VALID_PARAMS,
    }

    def __init__(self, log_path_dict):
        super(BMCLogPackageParser, self).__init__()
        self.file_dict = log_path_dict

        self.parsers = list()
        self.desc = DataDescriptorOfNAIE()

        self.add_parser(PlogParser)
        self.add_parser(NpuInfoParser)

    def add_parser(self, parser_cls):
        """add parser class object"""
        if not issubclass(parser_cls, BMCLogFileParser):
            logger.error("'parser_cls' must be sub-class of BMCLogFileParser")
            raise InnerError("'parser_cls' must be sub-class of BMCLogFileParser")
        self.parsers.append(parser_cls())

    def parse(self):
        for parser in self.parsers:
            files = parser.find_log(self.file_dict)
            if not files:
                logger.warning(f"don't find the origin file for parser {parser.__class__.__name__}")
                continue

            # NpuInfoParser only parse two file, "npu_info_before.txt" and "npu_info_after.txt"
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
        """return log_data_descriptor instance"""
        return self.desc
