# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. All rights reserved.

# normal rules
WORKER_DIR_RE = r"worker-(\d+)$"
MODEL_ARTS_WORKER_RE = r"modelarts-job.*?-worker-(\d+).log$"


# Rc job
# parse
PLOG_ORIGIN_RE = r"plog-(\d+)_(\d+).log$"
# diag
PLOG_PARSE_RE = r"plog-parser-(\d+)-(\d+).log$"
RANKNUM_AND_ID_RE = r"rankNum\[(\d+)\], rank\[(\d+)\]"
SERVER_AND_DEVICE_RE = r"server\[(\d+.\d+.\d+.\d+)], device\[(\d+)\]"
TIME_OUT_RE = r"timeOut\[(\d+)\]"
ERROR = "ERROR"
RANK_INFO = r", rank\["
TRACE_HCCL = r"\[TRACE\] HCCL"
ERROR_HCCL = r"\[ERROR\] HCCL"
ERROR_HCCP = r"\[ERROR\] HCCP"
EVENT_HCCL = r"\[EVENT\] HCCL"
HEARTBEAT_INFO = "error status"
HEARTBEAT_RANK = r"rank \[\[(\d+.\d+.\d+.\d+)]\[(\d+)\]\]"


# Kg job
# parse
NPU_INFO_RE = r"npu_info_(\w+).txt$"
# diag
