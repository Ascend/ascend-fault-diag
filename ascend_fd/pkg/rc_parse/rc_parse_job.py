# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. ALL rights reserved.
import logging
import os
import re

from ascend_fd.tool import safe_open, safe_chmod, popen_grep
from ascend_fd.status import FileNotExistError, InnerError
from ascend_fd.regular_rule import PLOG_ORIGIN_RE


rc_logger = logging.getLogger("rc_parse")
PARSE_RULE = {
    "trace": "\\[TRACE\\] HCCL",
    "event": "\\[EVENT\\] HCCL",
    "error": "\\[ERROR\\]"
}
CATEGORY = ["trace", "event", "error"]
PID_DEBUG_MAX_PLOG_NUM = 3
PID_RUN_MAX_PLOG_NUM = 2


def start_rc_parse_job(output_path, cfg):
    """
    start rc parse job.
    :param output_path: the parsed data output path
    :param cfg: parse config
    """
    plog_files_dict = cfg.plog_path

    plog_files = list()
    for plog_list in plog_files_dict.values():
        debug_plog_heap, run_plog_heap = plog_list
        if len(debug_plog_heap) > PID_DEBUG_MAX_PLOG_NUM:
            debug_plog_heap = debug_plog_heap[:1] + debug_plog_heap[-2:]
        if len(run_plog_heap) > PID_RUN_MAX_PLOG_NUM:
            run_plog_heap = run_plog_heap[-2:]
        plog_files.extend(debug_plog_heap)
        plog_files.extend(run_plog_heap)

    if not plog_files:
        rc_logger.error("no plog file that meets the path specifications is found.")
        raise FileNotExistError("no plog file that meets the path specifications is found.")

    pid_write_flag = dict()
    pid_error_flag = dict()
    for file in plog_files:
        file_name = os.path.basename(file)
        pid_re = re.match(PLOG_ORIGIN_RE, file_name)
        if not pid_re:
            continue
        pid = pid_re[1]
        out_file = os.path.join(output_path, f"plog-parser-{pid}.log")

        is_write = False
        for cate in CATEGORY:
            rc_logger.info(f"start grep {cate} information in file {file_name}.")
            is_write, is_error = get_info_from_file(cate, file, out_file)
            if is_write:
                pid_write_flag.update({pid: out_file})
            if is_error:
                pid_error_flag.update({pid: pid_error_flag.get(pid, 0) + 1})
        if is_write:
            rc_logger.info(f"the {file_name} parsing result is saved in dir {os.path.basename(output_path)}.")
        else:
            rc_logger.info(f"the {file_name} does not have effective results.")

    for key, src_file in pid_write_flag.items():
        if pid_error_flag.get(key, 0) > 0:
            dst_file = os.path.join(output_path, f"plog-parser-{key}-1.log")
        else:
            dst_file = os.path.join(output_path, f"plog-parser-{key}-0.log")
        os.rename(src_file, dst_file)
        safe_chmod(dst_file, 0o640)
    rc_logger.info("logs are printed and copied to the specified path.")


def get_info_from_file(cate, in_file, out_file):
    """
    use grep to filter the corresponding content from origin plog file.
    :param cate: grep rule
    :param in_file: the filtered file
    :param out_file: the output file
    """
    is_write = False
    is_error = False
    rule = PARSE_RULE.get(cate, None)
    if not rule:
        rc_logger.error(f"{cate} doesn't exist in PARSE_RULE")
        raise InnerError(f"{cate} doesn't exist in PARSE_RULE")
    grep = popen_grep(rule, file=in_file)
    logs = grep.stdout.readlines()
    if not logs:
        return is_write, is_error
    for line in logs:
        is_write = True
        with safe_open(out_file, "a+") as out:
            out.write(line)
    if cate == "error":
        is_error = True

    return is_write, is_error
