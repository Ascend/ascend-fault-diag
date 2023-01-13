# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.

# regular rules
PLOG_ORIGIN_RE = r"plog-(\d+)_(\d+).log$"
NPU_SMI_RE = r"npu_smi_(\d+)_details.csv$"
NPU_INFO_RE = r"npu_info_(\w+).txt$"
NPU_DETAILS_RE = r"npu_(\d+)_details.csv$"
MODEL_ARTS_RANK_RE = r"modelarts-job.*?-rank-(\d+)-.*?.txt$"
MODEL_ARTS_WORKER_RE = r"modelarts-job.*?-worker-(\d+).log$"
WORKER_DIR_RE = r"worker-(\d+)$"
PLOG_PARSE_RE = r"plog-parser-(\d+).log$"
NIC_CLEAN_RE = r"nic_clean.csv"
NAD_CLEAN_RE = r"nad_clean.csv"
KG_PARSE_RE = r"ascend-kg-parser.json"
IP_ADDR_RE = r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
NIC_CSV_RE = r"nic_clean.csv"
EPOCH_TIME_RE = r"epoch time: (\d+\.?\d*) ms, per step time: (\d+\.?\d*) ms"
