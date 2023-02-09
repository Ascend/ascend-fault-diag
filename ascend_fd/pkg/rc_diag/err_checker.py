# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
import re
import logging
from datetime import datetime

from ascend_fd import regular_rule
from ascend_fd.tool import popen_grep
from ascend_fd.status import InfoNotFoundError


rc_logger = logging.getLogger("kg_diag")


class Rank:
    def __init__(self, worker_id="-1", rank_id="-1", server_id="-1", device_id="-1"):
        self.worker_id = worker_id
        self.rank_id = rank_id
        self.server_id = server_id
        self.device_id = device_id

        self.origin_err_log = []
        self.err_content = {}

    def __hash__(self):
        return hash(self.worker_id + self.rank_id + self.server_id + self.device_id)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return hash(self) == hash(other)
        return False

    def __repr__(self):
        if self.rank_id == "-1":
            return "Unknown Rank"
        return f"Rank {self.rank_id}"

    @property
    def err_time(self):
        max_time = '9999-12-31-23:59:59.999.999'
        return self.err_content.get("First_err_time", max_time)

    @property
    def hccl_count(self):
        return self.err_content.get("Hccl_count", 0)

    def add_err_log(self, log):
        self.origin_err_log.append(log)

    def update_err_content(self, err_content):
        self.err_content.update(err_content)


class Mode:
    FORCE_KILL = 0
    NO_FORCE_KILL = 1


class BaseChecker:
    MAX_RANK_NUM = 5
    name = "Base error"
    description = "Unknown errors happen in the training process."
    solution = "Please turn to the relevant engineer to solve this problem."
    root_ranks = Rank()
    first_error_rank = None
    last_error_rank = None

    def __init__(self, rank_table):
        self.rank_table = rank_table

    def __str__(self):
        return f"{self.name}: {self.description} " \
               f"Root cause rank(s) is/are: {str(self.root_ranks)}. " \
               f"Solution: {self.solution}"

    def get_root_worker_set(self):
        if self.root_ranks == Rank() and self.first_error_rank:
            self.root_ranks = self.first_error_rank

        ranks = self.root_ranks
        worker_set = set()
        if isinstance(ranks, Rank):
            worker_id = ranks.worker_id
            if worker_id == "-1":
                return ranks, worker_set
            worker_set.add(worker_id)
            return [ranks], worker_set
        if isinstance(ranks, (list, set)):
            ranks = list(ranks)[:self.MAX_RANK_NUM]
            for single_rank in ranks:
                worker_id = single_rank.worker_id
                if worker_id != "-1":
                    worker_set.add(worker_id)
        return ranks, worker_set

    def check(self, plog_map, mode):
        pass

    def format_output(self):
        result = {"analyze_success": True, "engine_ver": "v1.0.0", "root_cause_worker": [], "root_cause_rank": [],
                  "first_error_rank": None, "last_error_rank": None, "root_cause_description": ""}

        ranks, worker_set = self.get_root_worker_set()
        result["root_cause_worker"] = str(list(worker_set))
        result["root_cause_rank"] = str(ranks)
        result["root_cause_description"] = self.__str__()

        if self.first_error_rank:
            result["first_error_rank"] = self.first_error_rank.__repr__()
        if self.last_error_rank:
            result["last_error_rank"] = self.last_error_rank.__repr__()
        return result, list(worker_set)


class AllRankNoErrChecker(BaseChecker):
    HEARTBEAT_RE_LENGTH = 3
    name = "All rank have no error"

    def check(self, plog_map, mode):
        if mode == Mode.NO_FORCE_KILL:
            self.description = "No errors logs are found on all ranks when the mode is NO_FORCE_KILL."
            self.root_ranks = Rank()
            return

        heartbeat_relation = self._parse_heartbeat_content(plog_map)
        if len(heartbeat_relation) == self.rank_table.rank_num:
            self.description = "No error logs are found on all Ranks. And all ranks have heartbeats."
            self.root_ranks = Rank()
            return

        if heartbeat_relation:
            heartbeat_relation_list = sorted(heartbeat_relation.values(), key=lambda x: len(x), reverse=True)
            no_heartbeat_max_set = set(heartbeat_relation_list[0])
            self.description = f"In the FORCE_KILL mode, heartbeat was lost on rank {str(no_heartbeat_max_set)}"
            self.solution = "Please check the training process on the lost heartbeat device."
            self.root_ranks = no_heartbeat_max_set
            return

        self.description = "No error logs are found on all Ranks. And all ranks don't have heartbeats."
        self.root_ranks = Rank()

    def _parse_heartbeat_content(self, plog_map):
        """
        parse heartbeat info from plog by grep.
        :param plog_map: the plog file map.
        :return: heartbeat relation info
        """
        heartbeat_relation = dict()
        flag = False
        for plog_file in plog_map.values():
            heartbeat_grep = popen_grep(regular_rule.HEARTBEAT_INFO, plog_file)
            heartbeat_logs = heartbeat_grep.stdout.readlines()
            if not heartbeat_logs:
                continue
            for heartbeat_log in heartbeat_logs:
                heartbeat_log = heartbeat_log.decode()
                if re.search(regular_rule.EVENT_HCCL, heartbeat_log):
                    heartbeat_re = re.findall(regular_rule.HEARTBEAT_RANK, heartbeat_log)
                    if not heartbeat_re or len(heartbeat_re) != self.HEARTBEAT_RE_LENGTH:
                        continue
                    flag = True
                    live_re, dead_re = heartbeat_re[0], heartbeat_re[1]
                    live_server, live_device = f"{live_re[0]}.{live_re[1]}.{live_re[2]}.{live_re[3]}", live_re[4]
                    dead_server, dead_device = f"{dead_re[0]}.{dead_re[1]}.{dead_re[2]}.{dead_re[3]}", dead_re[4]
                    live_rank = self.rank_table.get_rank_from_server_device_id(live_server, live_device)
                    dead_rank = self.rank_table.get_rank_from_server_device_id(dead_server, dead_device)
                    heartbeat_relation.setdefault(live_rank, list()).append(dead_rank)
        if not flag:
            rc_logger.error("no heartbeat error is recorded in the log. "
                            "Or the heartbeat is not enabled for training. Please check.")
            raise InfoNotFoundError("no heartbeat error is recorded in the log. "
                                    "Or the heartbeat is not enabled for training. Please check.")
        return heartbeat_relation


class ErrorInfoChecker(BaseChecker):
    HCCL_ERR_REASON = ["get socket timeout", "connected p2p timeout", "taskType[Notify Wait]",
                       "taskType[Reduce Inline]", "taskType[Memcpy]", "Open TsdClient failed"]

    @staticmethod
    def update_err_content_from_log(rank, error_logs):
        first_err_info = error_logs[0].decode().strip()
        times = first_err_info.split()[1].split(")")[1].strip(":")
        err_time = times[:-4] + times[-3:]

        hccl_count = 0
        for err_info in error_logs:
            err_info = err_info.decode().strip()
            if re.search(regular_rule.ERROR_HCCL, err_info):
                hccl_count += 1
            rank.add_err_log(err_info)
        total_err_count = len(error_logs)
        others_count = total_err_count - hccl_count

        err_content = {'First_err_time': err_time, 'Hccl_count': hccl_count,
                       'Others_count': others_count, 'Total_err_count': total_err_count}
        rank.update_err_content(err_content)

    def check(self, plog_map, mode):
        self._parse_err_content(plog_map)
        first_err_rank = self.rank_table.err_rank[0]
        self.first_error_rank = first_err_rank
        first_err_time = first_err_rank.err_time

        if first_err_rank.hccl_count == 0:
            self.name = "Unknown error"
            self.description = "The first rank to report the error does not contain HCCL errors. " \
                               "This component only supports HCCL error detection."
            self.root_ranks = Rank()
            return

        last_err_time = self._get_last_hccl_err_time()
        interval_times = (datetime.strptime(last_err_time, '%Y-%m-%d-%H:%M:%S.%f') -
                          datetime.strptime(first_err_time, '%Y-%m-%d-%H:%M:%S.%f')).total_seconds()
        for reason_index, err_reason in enumerate(self.HCCL_ERR_REASON):
            for rank in self.rank_table.err_rank:
                for err_log in rank.origin_err_log:
                    if err_reason in err_log and 'HCCL' in err_log:
                        self._check_hccl_error(interval_times, reason_index, rank, mode)
                        return

    def _parse_err_content(self, plog_map):
        """
        get rank error content.
        [rank_id, origin error log list, error info dict]
        """
        for rank in self.rank_table.err_rank:
            plog_file = plog_map.get(rank, None)
            if not plog_file:
                continue
            err_grep = popen_grep(regular_rule.ERROR, plog_file)
            error_logs = err_grep.stdout.readlines()
            if not error_logs:
                continue
            self.update_err_content_from_log(rank, error_logs)
        self.rank_table.err_rank.sort(key=lambda x: x.err_time)

    def _get_last_hccl_err_time(self):
        for rank in self.rank_table.err_rank[::-1]:
            if rank.hccl_count != 0 and rank.err_time != '9999-12-31-23:59:59.999.999':
                self.last_error_rank = rank
                return rank.err_time
        rc_logger.error("cannot find the last hccl error rank info. Please check input plog.")
        raise InfoNotFoundError("cannot find the last hccl error rank info. Please check input plog.")

    def _check_hccl_error(self, times, reason_index, rank, mode):
        """
        check hccl time out error reason and rank_id.
        """
        if reason_index < 3:
            self._check_timeout_err(times, reason_index, mode)
            return
        if reason_index == 3:
            self.name = "SDMA error"
            self.description = f"The cause of this error is 'SDMA overflowing' and data overflow occurred on {rank}."
            self.root_ranks = rank
            return
        if reason_index == 4:
            self.name = "Memcpy error"
            self.description = f"The cause of the error is Memcpy failed and rankid is {rank}."
            self.root_ranks = rank
            return

        self.name = "TsdClient error"
        self.description = f"Other HCCP process on the rank {rank}."
        self.solution = "Please wait some times or log in to the device " \
                        "and kill the hccp process or restart the environment."
        self.root_ranks = rank
        return

    def _check_timeout_err(self, times, reason_index, mode):
        self.name = "Timeout error"

        err_cate = ["get socket timeout", "connected p2p timeout", "notify timeout"]
        if reason_index < 2:
            timeout = self.rank_table.get_timeout('CONNECT_TIMEOUT')
        else:
            timeout = self.rank_table.get_timeout('NOTIFY_TIMEOUT')

        if int(timeout) < times:
            self.description = f"The cause of this error is '{err_cate[reason_index]}' " \
                               f"due to the fail of Inter-card synchronization."
            self.solution = f"Now the timeout is {timeout}, please set a longer timeout period."
            return

        if mode == Mode.FORCE_KILL:
            if self.rank_table.no_err_rank:
                self.description = f"The cause of this error is '{err_cate[reason_index]}'. " \
                                   f"Maybe the {self.rank_table.no_err_rank} is/are too slow or core dump."
                self.root_ranks = self.rank_table.no_err_rank
                return
            self.description = f"The cause of this error is '{err_cate[reason_index]}', " \
                               f"Timeout is reported for all ranks."
            self.root_ranks = self.rank_table.err_rank
            return

        self.description = f"The cause of this error is '{err_cate[reason_index]}'."
        self.root_ranks = Rank()
        return


class LostLogChecker(BaseChecker):
    name = "Lost log error"

    def check(self, plog_map, mode):
        all_rank_id = {str(i) for i in range(self.rank_table.rank_num)}
        exit_rank_id = set()

        rank_list = list(plog_map.keys())
        for rank in rank_list:
            exit_rank_id.add(rank.rank_id)
        lost_log_rank_ids = all_rank_id - exit_rank_id
        lost_log_rank = set()

        for rank_id in lost_log_rank_ids:
            lost_log_rank.add(Rank(rank_id=rank_id))
        self.description = f"The following rank IDs {list(lost_log_rank)} do not have log records."
        self.solution = f"Please check: 1. logs are complete; 2.training has started on {list(lost_log_rank)}."
        self.root_ranks = lost_log_rank


class NoErrInNFKChecker(BaseChecker):
    name = "No error in no-force-kill mode"

    def check(self, plog_map, mode):
        self.description = f"Rank {self.rank_table.no_err_rank} have no errs in the log. " \
                           f"The possible cause is that the process is hung."
        self.solution = "Please check the train process on the wrong rank ids."
        self.root_ranks = self.rank_table.no_err_rank
