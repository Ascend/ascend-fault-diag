# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. All rights reserved.
import logging
import os
import re

from ascend_fd import regular_rule
from ascend_fd.tool import popen_grep
from ascend_fd.pkg.note_msg import LOST_LOG_NOTE_MSG
from ascend_fd.status import FileNotExistError, InfoNotFoundError, InfoIncorrectError
from ascend_fd.pkg.rc_diag.err_checker import (AllRankNoErrChecker, SingleRankChecker, HCCLErrorChecker,
                                               NoErrInNFKChecker, Mode, Rank)


rc_logger = logging.getLogger("kg_diag")


class RankTable:
    """
    this class use to save the rank, worker, server, device relationship.
    worker 1-------* rank
    server 1-------* device

    worker 1-------1 server
    rank   1-------1 server-device
    """
    def __init__(self):
        self._rank_num = -1

        self.rank_map = dict()
        self.server_device_map = dict()

        self.err_rank = list()
        self.no_err_rank = list()

        self.timeouts = {'CONNECT_TIMEOUT': 120, 'NOTIFY_TIMEOUT': 600}

    @property
    def rank_num(self):
        return self._rank_num

    @rank_num.setter
    def rank_num(self, num):
        self._rank_num = num

    def add_rank(self, rank):
        """
        rank map: {rank_id: rank}
        server device map: {"server_id-device_id": rank}
        :return:
        """
        self.rank_map.update({rank.rank_id: rank})
        self.server_device_map.update({(rank.server_id, rank.device_id): rank})

    def get_rank_from_server_device_id(self, server_id, device_id):
        return self.server_device_map.get((server_id, device_id), Rank())

    def add_err_rank(self, rank):
        self.err_rank.append(rank)

    def add_no_err_rank(self, rank):
        self.no_err_rank.append(rank)

    def update_timeout(self, key, timeout_value):
        if not self.timeouts.get(key):
            rc_logger.error(f"The timeouts parameters don't contain {key}.")
            raise InfoNotFoundError(f"The timeouts parameters don't contain {key}.")
        self.timeouts[key] = timeout_value

    def get_timeout(self, key):
        if not self.timeouts.get(key):
            rc_logger.error(f"The timeouts parameters don't contain {key}.")
            raise InfoNotFoundError(f"The timeouts parameters don't contain {key}.")
        return self.timeouts.get(key)


class RCDiagWorker:
    def __init__(self, cfg):
        """
        init rc diag job.
        """
        self.cfg = cfg
        self.mode = cfg.mode
        self.rank_table = RankTable()

        self.rank_pid_map = dict()
        self.plog_map = dict()

    @staticmethod
    def get_rank_info_from_plog(worker_id, plog_file):
        """
        get a Rank (worker id, rank id, server id and device id) and rank num from plog files by grep.
        """
        rc_logger.info(f"get the rank info from plog file {os.path.basename(plog_file)} by grep trace log.")
        rank_num = -1
        trace_grep = popen_grep(regular_rule.TRACE_HCCL, file=plog_file)
        rank_grep = popen_grep(regular_rule.SERVER_INFO, stdin=trace_grep.stdout)
        rank_logs = rank_grep.stdout.readlines()
        if not rank_logs:
            rc_logger.info(f"cannot get rank info by grep trace log. "
                           f"Get the rank info from plog file {os.path.basename(plog_file)} by grep error log.")
            error_grep = popen_grep(regular_rule.ERROR_HCCL, file=plog_file)
            rank_grep = popen_grep(regular_rule.SERVER_INFO, stdin=error_grep.stdout)
            rank_logs = rank_grep.stdout.readlines()
            if not rank_logs:
                return rank_num, Rank()

        for rank_log in rank_logs:
            info_re = re.search(regular_rule.RANK_SERVER_DEVICE_RE, rank_log)
            if info_re:
                rank_num = int(info_re[1])
                rank_id, server_id, device_id = info_re[2], info_re[3], info_re[4]
                return rank_num, Rank(worker_id, rank_id, server_id, device_id)
        return rank_num, Rank()

    def start_job(self):
        """
        get root cluster diag job result: reason, rank_id and worker_id. Then format the output result.
        """
        self.init_plog_file()
        err_checker = self.generate_checker()
        err_checker.check(self.plog_map, self.mode)
        result, worker_list = err_checker.format_output()
        return result, worker_list

    def generate_checker(self):
        """
        start root cluster diag job.
        :return: the reason and rank_id.
        """
        if self.rank_table.rank_num == -1:
            return SingleRankChecker(self.rank_table)

        lost_log_warn = None
        if len(self.plog_map) != self.rank_table.rank_num:
            lost_log_warn = self.get_lost_log_rank()
            rc_logger.warning(lost_log_warn)

        if len(self.rank_table.no_err_rank) == self.rank_table.rank_num:
            return AllRankNoErrChecker(self.rank_table, lost_log_warn)
        if self.mode == Mode.NO_FORCE_KILL and self.rank_table.no_err_rank:
            return NoErrInNFKChecker(self.rank_table, lost_log_warn)
        return HCCLErrorChecker(self.rank_table, lost_log_warn)

    def init_plog_file(self):
        plog_files = self.get_plog_parser_files()
        for worker_id, plog_list in plog_files.items():
            for plog in plog_list:
                self.add_plog_path(worker_id, plog)

    def get_plog_parser_files(self):
        plog_files = dict()
        parse_data = self.cfg.parse_data
        for worker_dir, parse_data_dict in parse_data.items():
            worker_re = re.match(regular_rule.WORKER_DIR_RE, worker_dir)
            if not worker_re:
                rc_logger.error("worker dir path incorrect. Please check input path.")
                raise FileNotExistError("worker dir path incorrect. Please check input path.")
            worker_id = worker_re[1]
            plog_files.update({worker_id: parse_data_dict.get('plog_parser_path', [])})
        if not plog_files:
            rc_logger.error("no plog file that meets the path specifications is found.")
            raise FileNotExistError("no plog file that meets the path specifications is found.")
        return plog_files

    def get_timeout_param(self, plog_file):
        """
        get the timeout param from plog files by grep.
        """
        category = ['CONNECT_TIMEOUT', 'NOTIFY_TIMEOUT']
        timeout_content = ["HCCL_CONNECT_TIMEOUT is set", "ExecTimeOut is set"]

        for index, op in enumerate(timeout_content):
            event_grep = popen_grep(regular_rule.EVENT_HCCL, file=plog_file)
            op_grep = popen_grep(op, stdin=event_grep.stdout)
            timeout_logs = op_grep.stdout.readlines()
            if not timeout_logs:
                continue
            for timeout_log in timeout_logs:
                timeout_re = re.search(regular_rule.TIME_OUT_RE, timeout_log)
                if timeout_re:
                    self.rank_table.update_timeout(category[index], int(timeout_re[1]))
                    break

    def add_plog_path(self, worker_id, plog_file):
        self.get_timeout_param(plog_file)

        pid_re = re.match(regular_rule.PLOG_PARSE_RE, os.path.basename(plog_file))
        if not pid_re:
            rc_logger.error(f"the plog file name {os.path.basename(plog_file)} is incorrect. "
                            f"Please check input plog file.")
            raise InfoIncorrectError(f"the plog file name {os.path.basename(plog_file)} is incorrect. "
                                     f"Please check input plog file.")
        pid = pid_re[1]
        is_error = (pid_re[2] == "1")

        rank_num, rank = self.get_rank_info_from_plog(worker_id, plog_file)
        if rank_num == -1:
            rc_logger.warning(f"cannot get rank info from {os.path.basename(plog_file)} file.")
            return
        if self.rank_table.rank_num != -1 and rank_num != self.rank_table.rank_num:
            rc_logger.error("the value of rank_num in the plog file is not unique. "
                            "Please check whether the plog file is correct.")
            raise InfoIncorrectError("the value of rank_num in the plog file is not unique. "
                                     "Please check whether the plog file is correct.")

        self.rank_table.rank_num = rank_num

        if self.rank_pid_map.get(rank) and pid != self.rank_pid_map.get(rank):
            rc_logger.error("the input file path may contain logs of more than one training session. "
                            "Please check whether the plog file is correct.")
            raise InfoIncorrectError("the input file path may contain logs of more than one training session. "
                                     "Please check whether the plog file is correct.")
        self.rank_pid_map[rank] = pid

        self.rank_table.add_rank(rank)
        if is_error:
            self.rank_table.add_err_rank(rank)
        else:
            self.rank_table.add_no_err_rank(rank)
        self.plog_map.update({rank: plog_file})

    def get_lost_log_rank(self):
        """
        get the lost log rank id.
        :return: lost log rank ids set
        """
        all_rank_id = {str(i) for i in range(self.rank_table.rank_num)}
        exist_rank_id = set()

        rank_list = list(self.plog_map.keys())
        for rank in rank_list:
            exist_rank_id.add(rank.rank_id)
        lost_log_rank_ids = all_rank_id - exist_rank_id
        return LOST_LOG_NOTE_MSG.format(list(lost_log_rank_ids))


def start_rc_diag_job(cfg):
    rc_logger.info("start root cluster diagnosis task.")
    rc_diagnosis = RCDiagWorker(cfg)
    rc_result, worker_list = rc_diagnosis.start_job()
    return rc_result, worker_list
