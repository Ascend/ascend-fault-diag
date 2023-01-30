# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
import logging
import os
import re
import json
from datetime import datetime

from ascend_fd.status import FileNotExistError, InfoNotFoundError, InfoIncorrectError
from ascend_fd.tool import safe_open, popen_grep, safe_chmod
from ascend_fd import regular_rule

rc_logger = logging.getLogger("kg_diag.log")

MAX_TIME = '9999-12-31-23:59:59.999.999'
MAX_WORKER_NUM = 5
UNKNOWN_RANK = "Unknown"
HEARTBEAT_RE_LENGTH = 3


class Mode:
    FORCE_KILL = 0
    NO_FORCE_KILL = 1


class RankMap:
    """
    this class use to save the rank, worker, server, device relationship.
    worker 1-------* rank
    server 1-------* device

    worker 1-------1 server
    rank   1-------1 server-device
    """
    def __init__(self):
        self._rank_num = -1

        self.worker_rank_map = dict()
        self.rank_info_map = dict()

        self.err_rank = list()
        self.no_err_rank = list()

    @property
    def rank_num(self):
        return self._rank_num

    @rank_num.setter
    def rank_num(self, num):
        self._rank_num = num

    def add_relation(self, worker_id, rank_id, server_id, device_id):
        self.worker_rank_map.setdefault(worker_id, list()).append(rank_id)
        self.rank_info_map.update({rank_id: (worker_id, server_id, device_id)})
        self.rank_info_map.update({f"{server_id}-{device_id}": (worker_id, rank_id)})

    def get_all_rank_from_worker(self, worker_id):
        return self.worker_rank_map.get(worker_id, list())

    def get_all_info_from_rank(self, rank_id):
        return self.rank_info_map.get(rank_id, (-1, -1, -1))

    def get_worker_from_rank(self, rank_id):
        return self.get_all_info_from_rank(rank_id)[0]

    def get_rank_from_server_device(self, server_id, device_id):
        return self.rank_info_map.get(f"{server_id}-{device_id}", (-1, -1))[1]

    def add_err_rank(self, rank_id):
        self.err_rank.append(rank_id)

    def add_no_err_rank(self, rank_id):
        self.no_err_rank.append(rank_id)


class RankInfoParser:
    """
    this class use to save all plog file path and parse the content from plog.
    """
    def __init__(self, rank_map):
        self.rank_map = rank_map

        self.pid_map = dict()
        self.rank_plog_map = dict()

    @staticmethod
    def get_rank_info_from_plog(plog_file):
        """
        get rank info (rank num, rank id, server id and device id) from plog files by grep.
        """
        rc_logger.info(f"get the rank info from plog file {os.path.basename(plog_file)} by grep trace log.")
        trace_grep = popen_grep([regular_rule.TRACE_HCCL, plog_file])
        rank_grep = popen_grep([regular_rule.RANK_INFO], stdin=trace_grep.stdout)
        rank_logs = rank_grep.stdout.readlines()
        if not rank_logs:
            rc_logger.info(f"cannot get rank info by grep trace log. "
                           f"Get the rank info from plog file {os.path.basename(plog_file)} by grep error log.")
            error_grep = popen_grep([regular_rule.ERROR_HCCL, plog_file])
            rank_grep = popen_grep([regular_rule.RANK_INFO], stdin=error_grep.stdout)
            rank_logs = rank_grep.stdout.readlines()
            if not rank_logs:
                return False, []

        for rank_log in rank_logs:
            rank_log = rank_log.decode()
            info_re = re.search(regular_rule.RANKNUM_AND_ID_RE, rank_log)
            if info_re:
                rank_num = int(info_re[1])
                rank_id = info_re[2]
                server_id, device_id = "-1", "-1"
                ser_dev_re = re.search(regular_rule.SERVER_AND_DEVICE_RE, rank_log)
                if ser_dev_re:
                    server_id = f"{ser_dev_re[1]}.{ser_dev_re[2]}.{ser_dev_re[3]}.{ser_dev_re[4]}"
                    device_id = ser_dev_re[5]
                return True, [rank_num, rank_id, server_id, device_id]
        return False, []

    @staticmethod
    def get_err_content_from_log(rank_id, error_logs):
        first_err_info = error_logs[0].decode().strip()
        groups = first_err_info.split()[1].split("(")[0]
        times = first_err_info.split()[1].split(")")[1].strip(":")
        err_time = times[:-4] + times[-3:]

        hccl_count, hccp_count, heartbeat_num = 0, 0, 0
        origin_err_log = list()
        for err_info in error_logs:
            err_info = err_info.decode().strip()
            if re.search(regular_rule.ERROR_HCCL, err_info):
                hccl_count += 1
            if re.search(regular_rule.ERROR_HCCP, err_info):
                hccp_count += 1
            if re.search(regular_rule.HEARTBEAT_INFO, err_info):
                heartbeat_num += 1
            origin_err_log.append(err_info)
        others_count = len(error_logs) - hccl_count - hccp_count
        return [rank_id, origin_err_log, {
            'First_err_time': err_time, 'First_err_group': groups, 'Hccl_count': hccl_count, 'Hccp_count': hccp_count,
            'Others_count': others_count, 'Total_err_count': len(error_logs), 'Heartbeat_num': heartbeat_num
        }]

    def add_plog_path(self, worker_id, plog_file):
        pid_re = re.match(regular_rule.PLOG_PARSE_RE, os.path.basename(plog_file))
        if not pid_re:
            rc_logger.error(f"the plog file name {os.path.basename(plog_file)} is incorrect. "
                            f"Please check input plog file.")
            raise InfoIncorrectError(f"the plog file name {os.path.basename(plog_file)} is incorrect. "
                                     f"Please check input plog file.")
        pid = pid_re[1]

        is_ok, rank_info_list = self.get_rank_info_from_plog(plog_file)
        if not is_ok:
            rc_logger.warning(f"cannot get rank info from {os.path.basename(plog_file)} file.")
            return
        if self.rank_map.rank_num != -1 and rank_info_list[0] != self.rank_map.rank_num:
            rc_logger.error("the value of rank_num in the plog file is not unique. "
                            "Please check whether the plog file is correct.")
            raise InfoIncorrectError("the value of rank_num in the plog file is not unique. "
                                     "Please check whether the plog file is correct.")

        self.rank_map.rank_num = rank_info_list[0]
        rank_id = rank_info_list[1]

        if self.pid_map.get(pid) and rank_id != self.pid_map.get(pid):
            rc_logger.error("the input file path may contain logs of more than one training session. "
                            "Please check whether the plog file is correct.")
            raise InfoIncorrectError("the input file path may contain logs of more than one training session. "
                                     "Please check whether the plog file is correct.")
        self.pid_map[pid] = rank_id

        self.rank_map.add_relation(worker_id, *rank_info_list[1:])
        self.rank_plog_map.update({rank_id: plog_file})

    def parse_err_content(self):
        """
        get rank error content.
        [rank_id, origin error log list, error info dict]
        """
        rank_err_content = list()
        for rank_id, plog_file in self.rank_plog_map.items():
            err_grep = popen_grep([regular_rule.ERROR, plog_file])
            error_logs = err_grep.stdout.readlines()
            if not error_logs:
                self.rank_map.add_no_err_rank(rank_id)
                rank_err_content.append([rank_id, [], {
                    'First_err_time': MAX_TIME, 'First_err_group': 'NA', 'Hccl_count': 0, 'Hccp_count': 0,
                    'Others_count': 0, 'Total_err_count': 0, 'Heartbeat_num': 0
                }])
                continue
            self.rank_map.add_err_rank(rank_id)
            rank_err_content.append(self.get_err_content_from_log(rank_id, error_logs))
        return sorted(rank_err_content, key=lambda x: x[2].get('First_err_time', MAX_TIME))

    def parse_heartbeat_content(self):
        """
        get heartbeat info.
        """
        heartbeat_relation = dict()
        flag = False
        for plog_file in self.rank_plog_map.values():
            heartbeat_grep = popen_grep([regular_rule.HEARTBEAT_INFO, plog_file])
            heartbeat_logs = heartbeat_grep.stdout.readlines()
            if not heartbeat_logs:
                continue
            for heartbeat_log in heartbeat_logs:
                heartbeat_log = heartbeat_log.decode()
                if re.search(regular_rule.EVENT_HCCL, heartbeat_log):
                    heartbeat_re = re.findall(regular_rule.HEARTBEAT_RANK, heartbeat_log)
                    if not heartbeat_re or len(heartbeat_re) != HEARTBEAT_RE_LENGTH:
                        continue
                    flag = True
                    live_re, dead_re = heartbeat_re[0], heartbeat_re[1]
                    live_server, live_device = f"{live_re[0]}.{live_re[1]}.{live_re[2]}.{live_re[3]}", live_re[4]
                    dead_server, dead_device = f"{dead_re[0]}.{dead_re[1]}.{dead_re[2]}.{dead_re[3]}", dead_re[4]
                    live_rank = self.rank_map.get_rank_from_server_device(live_server, live_device)
                    dead_rank = self.rank_map.get_rank_from_server_device(dead_server, dead_device)
                    heartbeat_relation.setdefault(live_rank, list()).append(dead_rank)
        if not flag:
            rc_logger.error("no heartbeat error is recorded in the log. "
                            "Or the heartbeat is not enabled for training. Please check.")
            raise InfoNotFoundError("no heartbeat error is recorded in the log. "
                                    "Or the heartbeat is not enabled for training. Please check.")
        return heartbeat_relation


class RCDiagJob:
    def __init__(self, cfg):
        """
        init rc diag job.
        """
        self.cfg = cfg
        self.mode = cfg.get("mode", 0)
        self.rank_map = RankMap()
        self.rank_info_parser = RankInfoParser(self.rank_map)

        self.timeouts = {'CONNECT_TIMEOUT': 120, 'Set_connect_time': 0,
                         'NOTIFY_TIMEOUT': 600, 'Set_notify_time': 0}
        self.result = {
            "analyze_success": True,
            "engine_ver": "v1.0.0",
            "root_cause_worker": [],
            "root_cause_rank": [],
            "first_error_rank": None,
            "last_error_rank": None,
            "root_cause_description": ""
        }

    def start_job(self):
        """
        get root cluster diag job result: reason, rank_id and worker_id. Then format the output result.
        """
        reason, rank_id = self.diag_job()
        if rank_id == UNKNOWN_RANK and self.result.get("first_error_rank"):
            rank_id = self.result.get("first_error_rank")
        worker_set = self.get_worker_set_from_rank(rank_id)

        self.result["root_cause_worker"] = list(worker_set)
        self.result["root_cause_rank"] = list(rank_id)
        self.result["root_cause_description"] = reason

        return {"Ascend-RC-Worker-Rank-Analyze Result": self.result}, list(worker_set)

    def get_worker_set_from_rank(self, rank_id):
        worker_set = set()
        if rank_id == UNKNOWN_RANK:
            return worker_set

        if isinstance(rank_id, str):
            worker_id = self.rank_map.get_worker_from_rank(rank_id)
            if worker_id == -1:
                return worker_set
            worker_set.add(worker_id)
            return worker_set

        rank_list = list(rank_id)[:MAX_WORKER_NUM]
        for single_rank in rank_list:
            worker_id = self.rank_map.get_worker_from_rank(single_rank)
            if worker_id != -1:
                worker_set.add(worker_id)
        return worker_set

    def diag_job(self):
        """
        start root cluster diag job.
        :return: the reason and rank_id.
        """
        self.init_plog_file_and_timeout_params()
        if not self.check_rank_num():
            return self.check_lost_rank_log()

        rank_err_content = self.rank_info_parser.parse_err_content()
        if len(self.rank_map.no_err_rank) == self.rank_map.rank_num:
            return self.check_all_rank_no_err()
        if self.rank_map.no_err_rank and self.mode == Mode.NO_FORCE_KILL:
            reason = f"rank_{self.rank_map.no_err_rank} no errs in the log. " \
                     f"The possible cause is that the process is hung."
            return reason, self.rank_map.no_err_rank
        return self.check_rank_error(rank_err_content)

    def init_plog_file_and_timeout_params(self):
        plog_files = self.get_plog_parser_files()
        for worker_id, plog_list in plog_files.items():
            for plog in plog_list:
                self.update_timeout_params_from_plog(plog)
                self.rank_info_parser.add_plog_path(worker_id, plog)

    def get_plog_parser_files(self):
        plog_files = dict()
        parse_data = self.cfg.get("parse_data", None)
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

    def update_timeout_params_from_plog(self, plog_file):
        """
        get the timeout param from plog files by grep.
        """
        category = ['CONNECT_TIMEOUT', 'NOTIFY_TIMEOUT']
        operation = ['Set_connect_time', 'Set_notify_time']
        timeout_content = ["HCCL_CONNECT_TIMEOUT is set", "ExecTimeOut is set"]

        for index, op in enumerate(timeout_content):
            event_grep = popen_grep([regular_rule.ERROR_HCCL, plog_file])
            op_grep = popen_grep([op], stdin=event_grep.stdout)
            timeout_logs = op_grep.stdout.readlines()
            if not timeout_logs:
                continue
            for timeout_log in timeout_logs:
                timeout_re = re.search(regular_rule.TIME_OUT_RE, timeout_log.decode())
                if timeout_re:
                    self.timeouts.update({category[index]: int(timeout_re[1])})
                    self.timeouts.update({operation[index]: 1})
                    break

    def check_rank_num(self):
        """
        Check whether log files are valid, including missing logs or redundant logs.
        """
        rank_num = self.rank_map.rank_num
        if rank_num == -1:
            rc_logger.error("not found rank_num value. Please check whether the plog file is correct.")
            raise InfoNotFoundError("not found rank_num value. Please check whether the plog file is correct.")
        return len(self.rank_info_parser.rank_plog_map) == rank_num

    def check_lost_rank_log(self):
        """
        get the rank num error reason and err rank id.
        :return: reason, rank_id
        """
        no_log_rank_id = set()
        id_list = list(self.rank_info_parser.rank_plog_map.keys())
        for idx in range(self.rank_map.rank_num):
            if str(idx) not in id_list:
                no_log_rank_id.add(str(idx))
        reason = f"the following rank IDs {no_log_rank_id} do not have log records. " \
                 f"Please check whether the plog file is correct."
        return reason, no_log_rank_id

    def check_all_rank_no_err(self):
        """
        get error reason when all rank have no error info.
        """
        if self.mode == Mode.NO_FORCE_KILL:
            reason = "no errors on all ranks. Please turn to the relevant engineer to solve this problem."
            return reason, UNKNOWN_RANK
        heartbeat_relation = self.rank_info_parser.parse_heartbeat_content()
        if len(heartbeat_relation) == self.rank_map.rank_num:
            reason = "no error logs are found for all Ranks. And all ranks have heartbeats. " \
                     "Please turn to the relevant engineer to solve this problem."
            return reason, UNKNOWN_RANK
        if heartbeat_relation:
            heartbeat_relation_list = sorted(heartbeat_relation.values(), key=lambda x: len(x), reverse=True)
            no_heartbeat_max_set = set(heartbeat_relation_list[0])
            reason = f"In chronological order. heartbeat was lost on rank_{no_heartbeat_max_set}. " \
                     f"Please check the training process on this device."
            return reason, no_heartbeat_max_set
        reason = "no error logs are found for all Ranks. And at the same time all ranks don't have heartbeats. " \
                 "Please turn to the relevant engineer to solve this problem."
        return reason, UNKNOWN_RANK

    def check_rank_error(self, rank_err_content):
        hccl_err_reason = ["get socket timeout", "connected p2p timeout",
                           "taskType[Reduce Inline]", "taskType[Memcpy]",
                           "taskType[Notify Wait]", "Open TsdClient failed"]
        first_rank_id, _, first_rank_content = rank_err_content[0]
        self.result["first_error_rank"] = first_rank_id
        first_err_time = first_rank_content.get("First_err_time", MAX_TIME)

        if first_rank_content.get('Hccl_count', 0) == 0 and first_rank_content.get('Hccp_count', 0) == 0:
            reason = "The first rank to report the error does not contain HCCL or HCCP errors. " \
                     "Please turn to the relevant engineer to solve this problem."
            return reason, first_rank_id
        if first_rank_content.get('Hccl_count', 0) == 0 and first_rank_content.get('Hccp_count', 0) != 0:
            reason = "The first rank to report the error is HCCP error. " \
                     "Please turn to the relevant engineer to solve this problem."
            return reason, first_rank_id
        if first_rank_content.get("First_err_group", "NA") == "HCCP":
            reason = "The first rank to report the error is HCCP error. " \
                     "Please turn to the relevant engineer to solve this problem."
            return reason, first_rank_id

        last_err_time = self.get_last_hccl_err_time(rank_err_content)
        interval_times = (datetime.strptime(first_err_time, '%Y-%m-%d-%H:%M:%S.%f') -
                          datetime.strptime(last_err_time, '%Y-%m-%d-%H:%M:%S.%f')).total_seconds()
        for reason_index, err_reason in enumerate(hccl_err_reason):
            for rank_id, origin_err_logs, _ in rank_err_content:
                for err_log in origin_err_logs:
                    if err_reason in err_log and 'HCCL' in err_log:
                        return self.check_hccl_error(interval_times, reason_index, rank_id)
        reason = "all reason do not meet and cannot continue diagnosis. " \
                 "Please turn to the relevant engineer to solve this problem."
        return reason, UNKNOWN_RANK

    def check_hccl_error(self, times, reason_index, rank_id):
        """
        check hccl time out error reason and rank_id.
        """
        if reason_index < 2:
            return self.check_socket_or_p2p_timeout(times, reason_index)
        if reason_index == 2:
            return f"The cause of this error is 'SDMA overflowing' and data overflow occurred on {rank_id}.", rank_id
        if reason_index == 3:
            return f"The cause of the error is Memcpy failed and rankid is {rank_id}.", rank_id
        if reason_index == 4:
            return self.check_notify_timeout(times)
        return "Other HCCP process on the device, please wait some times or log in to the device " \
               "and kill the hccp preocess or restart the environment.", UNKNOWN_RANK

    def check_socket_or_p2p_timeout(self, times, index):
        """
        check socket or p2p timeout reason and rank_id.
        """
        cate = ["get socket timeout", "connected p2p timeout"]
        if int(self.timeouts.get('CONNECT_TIMEOUT')) < times:
            reason = f"The cause of this error is '{cate[index]}' due to the fail of Inter-card synchronization. " \
                     f"Please set a longer timeout period."
            return reason, UNKNOWN_RANK
        if self.mode == Mode.FORCE_KILL:
            rankids = self.rank_map.no_err_rank if self.rank_map.no_err_rank else self.rank_map.err_rank
            reason = f"The cause of this error is '{cate[index]}'."
            return reason, rankids
        reason = f"The cause of this error is '{cate[index]}'."
        return reason, UNKNOWN_RANK

    def check_notify_timeout(self, times):
        """
        check notify timeout reason and rank_id.
        """
        if int(self.timeouts.get('NOTIFY_TIMEOUT')) < times:
            reason = "The cause of this error is 'notify timeout' due to the fail of Inter-card synchronization. " \
                     "Please set a longer timeout period."
            return reason, UNKNOWN_RANK
        if self.mode == Mode.FORCE_KILL:
            if self.rank_map.no_err_rank:
                reason = f"The cause of this error is 'notify timeout'. " \
                         f"Maybe the {self.rank_map.no_err_rank} is/are too slow or core dump"
                return reason, self.rank_map.no_err_rank

            reason = "The cause of this error is 'notify timeout', Notify wait timeout is reported for all ranks."
            return reason, self.rank_map.err_rank

        reason = "The cause of this error is 'notify timeout."
        return reason, UNKNOWN_RANK

    def get_last_hccl_err_time(self, rank_err_content):
        for rank_id, _, rank_content in rank_err_content[::-1]:
            if rank_content.get("Hccl_count", 0) != 0 and rank_content.get("First_err_time", MAX_TIME) != MAX_TIME:
                self.result["last_error_rank"] = rank_id
                last_err_time = rank_content.get("First_err_time", MAX_TIME)
                return last_err_time
        rc_logger.error("cannot find the last hccl error rank info. Please check input plog.")
        raise InfoNotFoundError("cannot find the last hccl error rank info. Please check input plog.")


def start_rc_diag_job(output_path, cfg):
    rc_logger.info("start root cluster diagnosis task.")
    rc_diagnosis = RCDiagJob(cfg)
    rc_result, worker_list = rc_diagnosis.start_job()

    rc_out_file = os.path.join(output_path, "rc_diag_report.json")
    with safe_open(rc_out_file, 'w+', encoding='utf8') as file_stream:
        file_stream.write(json.dumps(rc_result, ensure_ascii=False, indent=4))
    safe_chmod(rc_out_file, 0o640)
    return rc_result, worker_list
