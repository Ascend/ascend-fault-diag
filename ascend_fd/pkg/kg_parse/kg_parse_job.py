# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
from ascend_fd.status import FileNotExistError
from ascend_fd.pkg.kg_parse.utils import logger
from ascend_fd.pkg.kg_parse.log_parser import SingleJsonFileProcessing


def start_kg_parse_job(output_path, files_path_dict):
    """
    execute the knowledge graph parsing task and invoke the knowledge graph parsing code.
    """
    log_path = get_file_list(files_path_dict)
    if not log_path:
        raise FileNotExistError("no log file that meets the path specifications is found.")

    config = {"log_path": log_path}
    logger.info("init json file processing")
    worker = SingleJsonFileProcessing(config)
    logger.info("start parse kg data")
    worker.export_json_file(output_path)


def get_file_list(files_path_dict):
    """
    generate plog files list and env check files for kg parse.
    """
    log_file = dict()
    if files_path_dict.get("plog_path", None):
        log_file.update({
            "plog_path": files_path_dict.get("plog_path")
        })
    if files_path_dict.get("npu_info_path", None):
        log_file.update({
            "npu_info_path": files_path_dict.get("npu_info_path")
        })
    return log_file
