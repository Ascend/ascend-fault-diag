# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. ALL rights reserved.
import os
import logging

import pandas as pd

from ascend_fd.status import FileNotExistError
from ascend_fd.tool import safe_read_csv

node_logger = logging.getLogger("node_parse.log")
NAD_OUTPUT_FILE_NAME = "nad_clean.csv"
NAD_SORT_COLUMNS = ["dev_id", "time"]


def start_node_parse_job(input_path, output_path, files_path_dict):
    """
    executing Computing Exception parsing task.
    """
    node_logger.info("start parse npu smi file.")
    npu_smi_files = files_path_dict.get("npu_smi_path", None)
    if not npu_smi_files:
        node_logger.error("no npu_smi csv file that meets the path specification is found.")
        raise FileNotExistError("no npu_smi csv file that meets the path specifications is found")

    concat_list = []
    for file in npu_smi_files:
        concat_list.append(safe_read_csv(file))
    output_df = pd.concat(concat_list)
    output_df.sort_values(by=NAD_SORT_COLUMNS, inplace=True)

    out_file = os.path.join(output_path, NAD_OUTPUT_FILE_NAME)
    output_df.to_csv(out_file, index=False)
    node_logger.info(f"the parsing result is saved in dir {os.path.basename(output_path)}.")
    node_logger.info("logs are printed and copied to the specified path.")
