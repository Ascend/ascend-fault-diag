# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. ALL rights reserved.
import logging
import os
import re
import subprocess

from ascend_fd.tool import verify_file, safe_open
from ascend_fd.status import FileNotExistError, InnerError
from ascend_fd.config import PLOG_ORIGIN_RE

rc_logger = logging.getLogger("rc_parse.log")
PARSE_RULE = {
    "trace": "\\[TRACE\\] HCCL",
    "event": "\\[EVENT\\] HCCL",
    "error": "\\[ERROR\\]"
}
CATEGORY = ["trace", "event", "error"]


def start_rc_parse_job(input_path, output_path, cfg):
    """
    start root cluster parse job.
    """
    plog_files = cfg.get("plog_path", None)
    if not plog_files:
        rc_logger.error("no plog file that meets the path specifications is found.")
        raise FileNotExistError("no plog file that meets the path specifications is found.")
    for file in plog_files:
        verify_file(file)
        file_name = os.path.basename(file)
        pid_re = re.match(PLOG_ORIGIN_RE, file_name)
        if not pid_re:
            continue
        pid = pid_re[1]
        out_file = os.path.join(output_path, f"plog-parser-{pid}.log")
        for cate in CATEGORY:
            rc_logger.info(f"start grep {cate} information in file {file_name}.")
            get_info_from_file(cate, file, out_file)
        rc_logger.info(f"the {file_name} parsing result is saved in dir {os.path.basename(output_path)}.")
    rc_logger.info("logs are printed and copied to the specified path.")


def get_info_from_file(cate, in_file, out_file):
    """
    obtain info from the plog files by grep.
    """
    rule = PARSE_RULE.get(cate, None)
    if not rule:
        rc_logger.error(f"{cate} doesn't exist in PARSE_RULE")
        raise InnerError(f"{cate} doesn't exist in PARSE_RULE")
    grep = subprocess.Popen(["/usr/bin/grep", rule, in_file],
                            shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logs = grep.stdout.readlines()
    if not logs:
        return
    for line in logs:
        with safe_open(out_file, "a+") as out:
            out.write(line.decode())
