# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. ALL rights reserved.
import json
import os

from ascend_fd.tool import safe_open
from ascend_fd.pkg.node_diag.npu_anomaly_detection import start_npu_anomaly_detection_job


def start_node_diag_job(input_path, output_path, cfg):
    result = {
        "Ascend-Node-Fault-Diag Result": {
            "engine_ver": "v1.0.0.0",
            "npu_anomaly_detection": start_npu_anomaly_detection_job(input_path, cfg)
        }
    }
    out_file = os.path.join(output_path, "node_diag_report.json")
    with safe_open(out_file, 'w+', encoding='utf8') as file_stream:
        file_stream.write(json.dumps(result, ensure_ascii=False, indent=4))
    return result
