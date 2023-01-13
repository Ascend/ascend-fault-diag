#!/user/bin/env python3
# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
import os

from ascend_fd.pkg.kg_parse.utils import logger
from ascend_fd.pkg.kg_parse.log_parser.parser.bmc_log_package_parser_temp import BMCLogPackageParser


class SingleJsonFileProcessing:
    """single json file process class"""

    def __init__(self, config):
        self.config = config

    def export_json_file(self, result_path):
        """
        export json file
        :param result_path: the path to export json result
        :return:
        """
        if not os.path.isdir(result_path):
            raise FileNotFoundError("result path '%s' not found" % result_path)
        _package_parser = BMCLogPackageParser(self.config["log_package_parser"])
        logger.info("____start parse____")
        _package_parser.parse()
        logger.info("____end parse____")
        desc = _package_parser.get_log_data_descriptor()
        json_path = os.path.join(self.config["log_package_parser"]["result_path"],
                                 self.config["log_package_parser"]["result_file"])
        logger.info("json file is %s", json_path)
        desc.dump_to_json_file(json_path)
        desc.clear()
