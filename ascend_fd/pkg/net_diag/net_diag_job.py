# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. ALL rights reserved.
import json
import logging
import os

import pandas as pd
import numpy as np
from xgboost import XGBClassifier

from ascend_fd.status import FileNotExistError
from ascend_fd.tool import safe_open, safe_read_csv

net_logger = logging.getLogger("net_diag.log")

ZERO = 0
FAULT_LABEL = 1
LEARNING_RATE = 0.05
DEPTH = 5
PWD_PATH = os.path.dirname(os.path.realpath(__file__))


def start_net_diag_job(input_path, output_path, cfg):
    net_logger.info("start network interface congestion fault diagnosis task.")
    nic_files = get_nic_files(cfg)
    if not nic_files:
        net_logger.error("no nic_clean csv file that meets the path specification is found.")
        raise FileNotExistError("no nic_clean csv file that meets the path specification is found.")
    input_path = concat_nic_files(nic_files)

    models = load_model()
    predict_label = predict(models, input_path)

    result = wrap_result(predict_label.tolist(), input_path.index.tolist())
    out_file = os.path.join(output_path, "net_diag_report.json")
    with safe_open(out_file, 'w+', encoding='utf8') as file_stream:
        file_stream.write(json.dumps(result, ensure_ascii=False, indent=4))
    return result


def wrap_result(predict_label, predict_name):
    fault_detail_list = list()
    for idx, label in enumerate(predict_label):
        if label == FAULT_LABEL:
            fault_detail_list.append(predict_name[idx])

    fault_detail = "congestion npu:" + ",".join(fault_detail_list) if fault_detail_list else "no congestion npu"

    result = {
        "Ascend-Net-Fault-Diag Result": {
            "analyze_success": True,
            "engine_ver": "v1.0.0",
            "root_cause_zh_CN": "暂不涉及",
            "root_cause_en_US": "Not involved currently",
            "description_zh_CN": "暂不涉及",
            "description_en_US": "Not involved currently",
            "solution_zh_CN": "暂不涉及",
            "solution_en_US": "Not involved currently",
            "fault_detail": fault_detail
        }
    }
    return result


def concat_nic_files(nic_files):
    """
    concat all worker-{index} nic_clean csv, and convert to pandas dataForamat
    :param nic_files: nic_clean csv list
    :return:
    """
    concat_list = list()
    for file in nic_files:
        concat_list.append(safe_read_csv(file, header=ZERO, encoding='unicode_escape', index_col=ZERO))
    concat_df = pd.concat(concat_list)
    return concat_df.sort_index()


def load_model():
    model_path = os.path.join(PWD_PATH, "models")
    model_files = os.listdir(model_path)
    model_list = list()

    for file_name in model_files:
        model = XGBClassifier(learning_rate=LEARNING_RATE, max_depth=DEPTH)
        model.load_model(os.path.join(model_path, file_name))
        model_list.append(model)

    if not model_list:
        net_logger.error("No pkl model file exists")
        raise FileNotFoundError("No pkl model file exists")
    return model_list


def predict(models, data):
    prediction_cat = np.zeros(data.shape[0])
    model_number = len(models)
    for model in models:
        prediction_cat += model.predict_proba(data)[:, 1] / model_number
    return np.round(prediction_cat)


def get_nic_files(cfg):
    nic_files_list = list()
    parse_data = cfg.get('parse_data', None)
    for worker in parse_data:
        nic_file = parse_data[worker].get('nic_clean_path', None)
        if nic_file:
            nic_files_list.append(nic_file)
    return nic_files_list
