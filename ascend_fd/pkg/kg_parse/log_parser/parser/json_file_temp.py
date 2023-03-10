#!/user/bin/env python3
# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
import os

from ascend_fd.pkg.kg_parse.utils import logger
from ascend_fd.status import FileNotExistError
from ascend_fd.pkg.kg_parse.log_parser.parser.bmc_log_package_parser_temp import BMCLogPackageParser


class SingleJsonFileProcessing:
    """single json file process class"""
    RESULT_FILE = "ascend-kg-parser.json"

    def __init__(self, log_path):
        self.log_path = log_path

    def export_json_file(self, result_path):
        """
        export json file
        :param result_path: the path to export json result
        :return:
        """
        if not os.path.isdir(result_path):
            logger.error(f"result path {os.path.basename(result_path)} not found.")
            raise FileNotExistError(f"result path {os.path.basename(result_path)} not found.")
        package_parser = BMCLogPackageParser(self.log_path)
        logger.info("____start parse____")
        package_parser.parse()
        logger.info("____end parse____")
        desc = package_parser.get_log_data_descriptor()
        json_path = os.path.join(result_path, self.RESULT_FILE)
        logger.info("json file is %s", json_path)
        desc.dump_to_json_file(json_path)
        desc.clear()
