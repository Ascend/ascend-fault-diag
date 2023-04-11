# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. ALL rights reserved.
import re
import logging
from datetime import datetime

from ascend_fd import regular_rule
from ascend_fd.pkg import fault_code
from ascend_fd.tool import popen_grep
from ascend_fd.status import InfoNotFoundError
from ascend_fd.pkg.note_msg import MULTI_RANK_NOTE_MSG, MAX_RANK_NOTE_MSG


rc_logger = logging.getLogger("kg_diag")


class Rank:
    """
    This class is used to store information about a single rank.
    Includes rank ID, server ID, device ID, raw error log, and parsed error content.
    """
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
    root_ranks = Rank()
    first_error_rank = None
    last_error_rank = None
    error_code = fault_code.RC_DIAGNOSIS_NORMAL
    note_msg = []

    def __init__(self, rank_table, warn_msg=None):
        self.rank_table = rank_table
        if warn_msg:
            self.note_msg.append(warn_msg)

    def get_root_worker_set(self):
        """
        get root worker from root cluster(rank) info.
        :return: root clusters list, root worker list
        """
        if self.root_ranks == Rank() and self.first_error_rank:
            # Rank() means unknown rank. If the first error rank exists, it is considered the root cluster.
            self.root_ranks = self.first_error_rank

        ranks = self.root_ranks
        worker_set = set()
        if isinstance(ranks, Rank):
            worker_id, server_id = ranks.worker_id, ranks.server_id
            if worker_id != "-1":
                # -1 means unknown worker. Unknown workers are not output.
                worker_set.add((worker_id, server_id))
            return [ranks], list(worker_set)

        if isinstance(ranks, (list, set)):
            # Multiple root cluster may be diagnosed.
            # If there are more than 5 root clusters, the first five are prioritized.
            if len(ranks) > self.MAX_RANK_NUM:
                self.note_msg.append(MAX_RANK_NOTE_MSG)
                ranks = list(ranks)[:self.MAX_RANK_NUM]
            elif len(ranks) > 1:
                self.note_msg.append(MULTI_RANK_NOTE_MSG)
            for single_rank in ranks:
                worker_id, server_id = single_rank.worker_id, single_rank.server_id
                if worker_id != "-1":
                    worker_set.add((worker_id, server_id))
        return ranks, list(worker_set)

    def check(self, plog_map, mode):
        pass

    def format_output(self):
        ranks, worker_set = self.get_root_worker_set()
        result = {"analyze_success": True,
                  "root_cause_rank": [single_rank.__repr__() for single_rank in ranks],
                  "root_cause_worker": worker_set,
                  "first_error_rank": self.first_error_rank.__repr__() if self.first_error_rank else None,
                  "last_error_rank": self.last_error_rank.__repr__() if self.last_error_rank else None,
                  "error_code": self.error_code,
                  "note_msgs": self.note_msg}

        return result, worker_set


class AllRankNoErrChecker(BaseChecker):
    HEARTBEAT_RE_LENGTH = 3

    def check(self, plog_map, mode):
        if mode == Mode.NO_FORCE_KILL:
            self.error_code = fault_code.RC_UNKOWN_ERROR_ONE
            self.root_ranks = Rank()
            return

        heartbeat_relation = self._parse_heartbeat_content(plog_map)
        if len(heartbeat_relation) == self.rank_table.rank_num:
            self.error_code = fault_code.RC_UNKOWN_ERROR_TWO
            self.root_ranks = Rank()
            return

        if heartbeat_relation:
            # heartbeat lost error
            heartbeat_relation_list = sorted(heartbeat_relation.values(), key=lambda x: len(x), reverse=True)
            self.error_code = fault_code.HEARTBEAT_LOST_ERROR
            self.root_ranks = set(heartbeat_relation_list[0])
            return

        self.error_code = fault_code.RC_UNKOWN_ERROR_THREE
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
            heartbeat_grep = popen_grep(regular_rule.HEARTBEAT_INFO, file=plog_file)
            heartbeat_logs = heartbeat_grep.stdout.readlines()
            if not heartbeat_logs:
                continue
            for heartbeat_log in heartbeat_logs:
                if re.search(regular_rule.EVENT_HCCL, heartbeat_log):
                    # According to the regular rules, 3 sets of matching results will be found,
                    # which are record node, lost heartbeat node, and report node.
                    # Each set of results includes (ip_addr, device_id)
                    heartbeat_re = re.findall(regular_rule.HEARTBEAT_RANK, heartbeat_log)
                    if not heartbeat_re or len(heartbeat_re) != self.HEARTBEAT_RE_LENGTH:
                        continue
                    flag = True
                    live_re, dead_re = heartbeat_re[0], heartbeat_re[1]
                    # The record node is live server, the lost heartbeat node is dead server.
                    live_server, live_device = live_re[0], live_re[1]
                    dead_server, dead_device = dead_re[0], dead_re[1]
                    live_rank = self.rank_table.get_rank_from_server_device_id(live_server, live_device)
                    dead_rank = self.rank_table.get_rank_from_server_device_id(dead_server, dead_device)
                    heartbeat_relation.setdefault(live_rank, list()).append(dead_rank)
        if not flag:
            rc_logger.error("no heartbeat error is recorded in the log. "
                            "Or the heartbeat is not enabled for training. Please check.")
            raise InfoNotFoundError("no heartbeat error is recorded in the log. "
                                    "Or the heartbeat is not enabled for training. Please check.")
        return heartbeat_relation


class HCCLErrorChecker(BaseChecker):
    HCCL_ERR_REASON = ["get socket timeout", "connected p2p timeout", "taskType[Notify Wait]",
                       "taskType[Reduce Inline]", "taskType[Memcpy]", "Open TsdClient failed"]

    @staticmethod
    def update_err_content_from_log(rank, error_logs):
        # The log example:
        # "[ERROR] XXXX(**,**):20yy-mm-dd-xx:xx:xx.xxx.xxx ********************"
        first_err_info = error_logs[0].strip()

        # get the first error log's time stamp and remove the separation point of millisecond.
        times = first_err_info.split()[1].split(")")[1].strip(":")
        err_time = times[:-4] + times[-3:]  # "20yy-mm-dd-xx:xx:xx.xxx.xxx" -> "20yy-mm-dd-xx:xx:xx.xxxxxx"

        hccl_count = 0
        for err_info in error_logs:
            err_info = err_info.strip()
            if re.search(regular_rule.ERROR_HCCL, err_info):
                hccl_count += 1
            rank.add_err_log(err_info)
        total_err_count = len(error_logs)
        others_count = total_err_count - hccl_count

        err_content = {'First_err_time': err_time, 'Hccl_count': hccl_count,
                       'Others_count': others_count, 'Total_err_count': total_err_count}
        rank.update_err_content(err_content)

    def check(self, plog_map, mode):
        if not self.rank_table.err_rank:
            # The error ranks list is empty.
            self.error_code = fault_code.RC_UNKOWN_ERROR_SIX
            self.root_ranks = Rank()
            return
        self._parse_err_content(plog_map)
        first_err_rank = self.rank_table.err_rank[0]
        self.first_error_rank = first_err_rank
        first_err_time = first_err_rank.err_time

        if first_err_rank.hccl_count == 0:
            self.error_code = fault_code.RC_UNKOWN_ERROR_FOUR
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
            err_grep = popen_grep(regular_rule.ERROR, file=plog_file)
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
        check hccl error reason and rank_id.
        """
        if reason_index < 3:
            self._check_timeout_err(times, reason_index, mode)
            return
        if reason_index == 3:
            self.error_code = fault_code.HCCL_SDMA_FAULT
            self.root_ranks = rank
            return
        if reason_index == 4:
            self.error_code = fault_code.HCCL_MEMCPY_FAULT
            self.root_ranks = rank
            return

        self.error_code = fault_code.HCCL_TSDCLIENT_FAULT
        self.root_ranks = rank
        return

    def _check_timeout_err(self, times, reason_index, mode):
        """
        check the hccl timeout err reason.
        :param times: the timeout parameter value.
        :param reason_index: the error index. 0->socket fault; 1->p2p fault; 2->notify fault
        :param mode: run mode
        """
        if reason_index < 2:
            timeout = self.rank_table.get_timeout('CONNECT_TIMEOUT')
        else:
            timeout = self.rank_table.get_timeout('NOTIFY_TIMEOUT')

        if int(timeout) < times:
            error_codes = [fault_code.HCCL_SOCKET_FAULT_SYNC,
                           fault_code.HCCL_P2P_FAULT_SYNC,
                           fault_code.HCCL_NOTIFY_FAULT_SYNC]
            self.error_code = error_codes[reason_index]
            self.root_ranks = Rank()
            return

        if mode == Mode.FORCE_KILL:
            if self.rank_table.no_err_rank:
                error_codes = [fault_code.HCCL_SOCKET_FAULT_UNKNOWN,
                               fault_code.HCCL_P2P_FAULT_UNKNOWN,
                               fault_code.HCCL_NOTIFY_FAULT_CORE_DUMP]
                self.error_code = error_codes[reason_index]
                self.root_ranks = self.rank_table.no_err_rank
                return
            error_codes = [fault_code.HCCL_SOCKET_FAULT_UNKNOWN,
                           fault_code.HCCL_P2P_FAULT_UNKNOWN,
                           fault_code.HCCL_NOTIFY_FAULT_UNKNOWN]
            self.error_code = error_codes[reason_index]
            self.root_ranks = self.rank_table.err_rank
            return

        error_codes = [fault_code.HCCL_SOCKET_FAULT_UNKNOWN,
                       fault_code.HCCL_NOTIFY_FAULT_UNKNOWN,
                       fault_code.HCCL_P2P_FAULT_UNKNOWN]
        self.error_code = error_codes[reason_index]
        self.root_ranks = Rank()
        return


class NoErrInNFKChecker(BaseChecker):
    def check(self, plog_map, mode):
        self.error_code = fault_code.RC_UNKOWN_ERROR_FIVE
        self.root_ranks = self.rank_table.no_err_rank


class SingleRankChecker(BaseChecker):
    def check(self, plog_map, mode):
        self.error_code = fault_code.SINGLE_CLUSTER_ERROR
        self.root_ranks = Rank(worker_id="0", rank_id="0", server_id="NA")
