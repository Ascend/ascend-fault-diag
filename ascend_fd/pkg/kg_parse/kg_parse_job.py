# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
import os
import re

from ascend_fd.status import FileNotExistError
from ascend_fd.pkg.kg_parse.utils import PLATFORM_INFO, logger
from ascend_fd.pkg.kg_parse.log_parser import SingleJsonFileProcessing


DEFAULT_CFG_TEMPLATE = {
    "worker_count": 10,
    "worker_configs": {
        "log_package_parser": {
            "data_descriptor": {},
            "unpacker": {
                "info_to_stdout": False
            },
            "file_parser": {
                "fdm_decoder": os.path.join(PLATFORM_INFO.bin_path, "FDMDecoder1.3.6.exe"),
            },
            "result_file": "ascend-kg-parser.json",
        },
        "json_suffix": "package_desc",
    },
}


def start_kg_parse_job(input_path, output_path, files_path_dict):
    """
    execute the knowledge graph parsing task and invoke the knowledge graph parsing code.
    """
    log_path_list = get_file_list(files_path_dict)
    if not log_path_list:
        raise FileNotExistError("no log file that meets the path specifications is found.")

    pl_type = {"platform_type": "NAIE", "log_type": "Atlas", "result_path": output_path}
    if pl_type["log_type"] == "Atlas":
        pl_type["log_type"] = "TaiShan"

    configs = DEFAULT_CFG_TEMPLATE
    configs["worker_configs"]["log_package_parser"].update(pl_type)

    log_list = {"log_path_list": log_path_list}
    configs["worker_configs"]["log_package_parser"].update(log_list)

    logger.info("init json file processing")
    worker = SingleJsonFileProcessing(configs["worker_configs"])
    logger.info("start parse kg data")
    worker.export_json_file(output_path)


def get_file_list(files_path_dict):
    """
    generate plog files list and env check files for kg parse.
    """
    log_file = list()
    log_file.extend(files_path_dict.get("plog_path", None))
    log_file.extend(files_path_dict.get("npu_info_path", None))
    return log_file
