# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
import logging
import os
import re
import json
import subprocess
from datetime import datetime

from ascend_fd.status import FileNotExistError, InfoNotFoundError, InfoIncorrectError
from ascend_fd.tool import safe_open
from ascend_fd.config import PLOG_PARSE_RE, WORKER_DIR_RE

rc_logger = logging.getLogger("kg_diag.log")

MAX_TIME = '9999-12-31-23:59:59.999.999'
MAX_WORKER_NUM = 5
UNKNOWN_RANK = "Unknown"


class Mode:
    FORCE_KILL = 0
    NO_FORCE_KILL = 1


class RCDiagJob:
    TIMEOUT_CONTENT = ["HCCL_CONNECT_TIMEOUT is set", "ExecTimeOut is set"]
    HCCL_ERR_REASON = ["get socket timeout", "connected p2p timeout",
                       "taskType[Reduce Inline]", "taskType[Memcpy]",
                       "taskType[Notify Wait]", "Open TsdClient failed"]

    def __init__(self, input_path, cfg):
        """
        init rc diag job.
        :param input_path: the input parsed log files path.
        :param cfg: the task config.
        """
        self.input_path = input_path
        self.cfg = cfg
        self.mode = self.cfg.get("mode", 0)

        self.plog_files = self.get_plog_parser_files()
        if not self.plog_files:
            rc_logger.error("no plog file that meets the path specifications is found.")
            raise FileNotExistError("no plog file that meets the path specifications is found.")

        self.timeouts = {'CONNECT_TIMEOUT': 120, 'Set_connect_time': 0,
                         'NOTIFY_TIMEOUT': 600, 'Set_notify_time': 0}

        self.rank_num = -1

        self.worker_map = dict()
        self.server_device_map = dict()
        self.rank_id_files = dict()
        self.heartbeat_status = dict()
        self.first_and_last_result = dict()
        self.first_and_last_err_time = dict()

        self.no_heartbeat_rank_id = set()
        self.no_log_rank_id = set()
        self.no_error_rank_id = set()
        self.error_rank_id = set()
        self.pid_rankid_table = set()

    def start_rc_diag_job(self):
        """
        get root cluster diag job result: reason and rank_id. Then format the output result.
        :return: diag format result
        """
        reason, rank_id = self.rc_job()

        if not self.first_and_last_result.get("First", None):
            first_rank = UNKNOWN_RANK
        else:
            first_rank = self.first_and_last_result["First"]["Rank_Id"]
        if not self.first_and_last_result.get("Last", None):
            last_rank = UNKNOWN_RANK
        else:
            last_rank = self.first_and_last_result["Last"]["Rank_Id"]

        rank_id = first_rank if rank_id == UNKNOWN_RANK else rank_id
        worker_id = self.map_worker_id(rank_id)

        result = {
            "Ascend-RC-Worker-Rank-Analyze Result": {
                "analyze_success": True,
                "engine_ver": "v1.0.0",
                "root_cause_worker": list(worker_id),
                "root_cause_rank": list(rank_id),
                "first_error_rank": first_rank,
                "last_error_rank": last_rank,
                "root_cause_description": reason
            }
        }
        return result, list(worker_id)

    def get_plog_parser_files(self):
        plog_files = list()
        parse_data = self.cfg.get('parse_data', None)
        for worker in parse_data:
            plog_files.extend(parse_data[worker].get('plog_parser_path', None))
        return plog_files

    def map_worker_id(self, rank_id):
        worker_set = set()
        if rank_id == UNKNOWN_RANK:
            return worker_set

        if isinstance(rank_id, str):
            worker_id = self.worker_map.get(rank_id, None)
            if not worker_id:
                return worker_set
            worker_set.add(worker_id)
            return worker_set

        rank_list = list(rank_id)[:MAX_WORKER_NUM]
        for single_rank in rank_list:
            worker_id = self.worker_map.get(single_rank, None)
            if worker_id:
                worker_set.add(worker_id)
        return worker_set

    def rc_job(self):
        """
        start root cluster diag job.
        :return: reason, rank_id
        """
        for plog_file in self.plog_files:
            self.get_timeout_in_plog_file(plog_file)
            self.get_rank_id_in_plog_file(plog_file)

        if not self.check_rank_nums():
            return self.get_rank_nums_reason()

        parse_err_info = self.get_err_content()

        if len(self.no_log_rank_id) == self.rank_num:
            return self.get_all_rank_no_err_reason()

        if self.no_log_rank_id and self.mode == Mode.NO_FORCE_KILL:
            reason = f"rank_{self.no_log_rank_id} no errs in the log. The possible cause is that the process is hung."
            return reason, self.no_log_rank_id

        err_list = self.get_err_list_by_time(parse_err_info)

        return self.get_error_reason(parse_err_info, err_list)

    def get_rank_nums_reason(self):
        """
        get the rank num error reason and err rank id.
        :return: reason, rank_id
        """
        no_rank_id = set()
        id_list = list(self.rank_id_files.keys())
        for idx in range(self.rank_num):
            if str(idx) not in id_list:
                no_rank_id.add(str(idx))
        reason = f"the following rank IDs {no_rank_id} do not have log records. " \
                 f"Please check whether the plog file is correct."
        return reason, no_rank_id

    def get_all_rank_no_err_reason(self):
        """
        get error reason when all rank have no error info.
        :return: reason, rank_id
        """
        if self.mode == Mode.NO_FORCE_KILL:
            reason = "no errors on all ranks."
            return reason, UNKNOWN_RANK
        heartbeat_items = self.get_heartbeat_log()
        if len(self.heartbeat_status) == len(self.no_log_rank_id):
            reason = "no error logs are found for all Ranks. And at the same time all ranks have heartbeats."
            return reason, UNKNOWN_RANK
        if self.heartbeat_status:
            rank_ids = set()
            for dead_server_device in self.heartbeat_status[heartbeat_items[0][0]]:
                rank_ids.add(self.server_device_map[dead_server_device])
            rank_id = rank_ids if len(rank_ids) > 1 else list(rank_ids)[0]
            reason = f"In chronological order. heartbeat was lost on rank_{rank_id}. " \
                     f"Please check the training process on this device."
            return reason, rank_id
        reason = "no error logs are found for all Ranks. And at the same time all ranks don't have heartbeats."
        return reason, UNKNOWN_RANK

    def get_error_reason(self, parse_err_info, err_list_by_time):
        """
        get error reason.
        :param parse_err_info: parsed error info
        :param err_list_by_time: error detail info sorted by time
        :return: reason, rank_id
        """
        earliest_rank = err_list_by_time[0]
        if earliest_rank[1]['Hccl_count'] == 0 and earliest_rank[1]['Hccp_count'] == 0:
            reason = "The first rank to report the error does not contain HCCL or HCCP errors. " \
                     "Please turn to the relevant engineer to solve this problem."
            rank_id = earliest_rank[0]
            return reason, rank_id
        if earliest_rank[1]['Hccl_count'] == 0 and earliest_rank[1]['Hccp_count'] != 0:
            reason = "The first rank to report the error is HCCP error. "
            rank_id = earliest_rank[0]
            return reason, rank_id
        reason, rank_id = self.check_hccl_error(parse_err_info, err_list_by_time)
        return reason, rank_id

    def get_err_content(self):
        """
        use grep to find error content in plog files.
        :return: parsed error info.
        """
        parse_err_info = dict()

        rank_id_file_list = list(self.rank_id_files.items())
        rank_id_file_list.sort(key=lambda x: x[0])
        for single_rank_file in rank_id_file_list:
            file_err_info = []
            rank_id = single_rank_file[0]
            error_grep = subprocess.Popen(["/usr/bin/grep", "ERROR",
                                           os.path.join(single_rank_file[1]["Path"], single_rank_file[1]["File"])],
                                          shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            error_infos = error_grep.stdout.readlines()
            if not error_infos:
                self.no_log_rank_id.add(rank_id)
            for info in error_infos:
                file_err_info.append(info.decode().strip())
            parse_err_info.update({rank_id: file_err_info})
        return parse_err_info

    def get_err_list_by_time(self, parse_err_info):
        """
        get the time, error type and error count info from parsed error info.
        And return the error detail info sorted by time.
        :param parse_err_info: parsed error info
        :return: error detail info sorted by time
        """
        parse_err_list = []
        for rank_id, err_info_list in parse_err_info.items():
            if not err_info_list:
                self.no_error_rank_id.add(rank_id)
                parse_err_list.append([rank_id, {
                    "First_err_time": MAX_TIME, 'First_err_group': 'NA',
                    'Hccl_count': 0, 'Hccp_count': 0,
                    'Others_count': 0, 'Hccl_err_type': 'hccl_err_type',
                    'Total_err_Count': 0, 'Heartbeat_num': 0
                }])
            else:
                self.error_rank_id.add(rank_id)
                groups = err_info_list[0].split()[1].split("(")[0]
                times = err_info_list[0].split()[1].split(')')[1].strip(":")
                err_time = times[:-4] + times[-3:]
                hccl_count, hccp_count, heartbeat_num = 0, 0, 0
                hccl_err_type = 'hcclerrtype'
                for err_info in err_info_list:
                    if err_info.find('[ERROR] HCCL') != -1:
                        hccl_count += 1
                    if err_info.find('[ERROR] HCCP') != -1:
                        hccp_count += 1
                    if err_info.find('error status[1') != -1:
                        heartbeat_num += 1
                others_count = len(err_info_list) - hccl_count - hccp_count
                parse_err_list.append([rank_id, {
                    "First_err_time": err_time, 'First_err_group': groups,
                    'Hccl_count': hccl_count, 'Hccp_count': hccp_count,
                    'Others_count': others_count, 'Hccl_err_type': hccl_err_type,
                    'Total_err_count': len(err_info_list), 'Heartbeat_num': heartbeat_num
                }])
        err_list_by_time = sorted(parse_err_list, key=lambda x: x[1]['First_err_time'])
        return err_list_by_time

    def get_first_err_rank(self, err_list_by_time):
        """
        obtains the rank of the earliest error alarm.
        """
        earliest_rank = err_list_by_time[0]
        server_id = self.rank_id_files[earliest_rank[0]]["Server_Id"]
        device_id = self.rank_id_files[earliest_rank[0]]["Device_Id"]
        first_time = earliest_rank[1]['First_err_time']
        self.first_and_last_err_time["First"] = first_time
        self.first_and_last_result.update({
            "First": {
                "Rank_Id": earliest_rank[0],
                "Server_Id": server_id,
                "Device_Id": device_id,
                "Time": first_time
            }
        })

    def get_last_err_rank(self, err_list_by_time):
        """
        obtains the rank of the latest error alarm.
        """
        for err_rank in err_list_by_time[::-1]:
            if err_rank[1]["Hccl_count"] != 0 and err_rank[1]["First_err_time"] != MAX_TIME:
                server_id = self.rank_id_files[err_rank[0]]["Server_Id"]
                device_id = self.rank_id_files[err_rank[0]]["Device_Id"]
                last_time = err_rank[1]['First_err_time']
                self.first_and_last_err_time["Last"] = last_time
                self.first_and_last_result.update({
                    "Last": {
                        "Rank_Id": err_rank[0],
                        "Server_Id": server_id,
                        "Device_Id": device_id,
                        "Time": last_time
                    }
                })
                break

    def get_heartbeat_log(self):
        """
        get the heartbeat info form plog by grep.
        """
        heartbeat_dicts = dict()
        err_flag = False
        for plog_file in self.plog_files:
            error_grep = subprocess.Popen(["/usr/bin/grep", "error status", plog_file],
                                          shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            error_logs = error_grep.stdout.readlines()
            if not error_logs:
                continue
            heartbeat_count = 0
            for error_log in error_logs:
                if error_log.decode().find("[EVENT] HCCL") != -1:
                    err_flag = True
                    live_server_device = error_log.decode().split("]]")[0].split("[[")[1].split("][")
                    dead_server_device_id = error_log.decode().split("]]")[1].split("[[")[1].split("][")
                    self.heartbeat_status.setdefault(tuple(live_server_device), list()). \
                        append(tuple(dead_server_device_id))
                    self.no_heartbeat_rank_id.add(self.server_device_map[tuple(dead_server_device_id)])
                    heartbeat_count += error_log.decode().count('error status')
                    heartbeat_dicts[tuple(live_server_device)] = heartbeat_count

        if not err_flag:
            rc_logger.error("event log is not enabled for training. Please check.")
            raise InfoNotFoundError("event log is not enabled for training. Please check.")
        heartbeat_items = sorted(heartbeat_dicts.items(), key=lambda x: x[1], reverse=True)
        return heartbeat_items

    def get_timeout_in_plog_file(self, plog_file):
        """
        get the timeout param from plog files by grep.
        """
        category = ['CONNECT_TIMEOUT', 'NOTIFY_TIMEOUT']
        operation = ['Set_connect_time', 'Set_notify_time']
        for index, err in enumerate(self.TIMEOUT_CONTENT):
            event_grep = subprocess.Popen(["/usr/bin/grep", "\\[EVENT\\] HCCL", plog_file],
                                          shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            err_grep = subprocess.Popen(["/usr/bin/grep", err], shell=False,
                                        stdin=event_grep.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            timeout_logs = err_grep.stdout.readlines()
            if not timeout_logs:
                continue
            for timeout_log in timeout_logs:
                timeout_re = re.search(r"timeOut\[(\d+)]", timeout_log.decode())
                if timeout_re:
                    self.timeouts.update({category[index]: int(timeout_re[1])})
                    self.timeouts.update({operation[index]: 1})
                    break

    def get_rank_id_in_plog_file(self, plog_file):
        """
        get rank info such as rank id, server id and device id from plog files by grep.
        """
        pid = int(re.match(r"plog-parser-(\d+).log$", os.path.basename(plog_file))[1])
        trace_grep = subprocess.Popen(["/usr/bin/grep", "\\[TRACE\\] HCCL", plog_file],
                                      shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        rank_grep = subprocess.Popen(["/usr/bin/grep", ", rank\\["], shell=False,
                                     stdin=trace_grep.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        rank_logs = rank_grep.stdout.readlines()
        if not rank_logs:
            error_grep = subprocess.Popen(["/usr/bin/grep", "\\[ERROR\\] HCCL", plog_file],
                                          shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            rank_grep = subprocess.Popen(["/usr/bin/grep", ", rank\\["], shell=False,
                                         stdin=error_grep.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            rank_logs = rank_grep.stdout.readlines()
            if not rank_logs:
                return

        for rank_log in rank_logs:
            info_re = re.search(r"rankNum\[(\d+)], rank\[(\d+)],server\[(\d+).(\d+).(\d+).(\d+)], device\[(\d+)]",
                                rank_log.decode())
            if info_re:
                rank_num_temp = int(info_re[1])
                if self.rank_num != -1 and rank_num_temp != self.rank_num:
                    rc_logger.error("the value of rank_num in the plog file is not unique. "
                                    "Please check whether the plog file is correct.")
                    raise InfoIncorrectError("the value of rank_num in the plog file is not unique. "
                                             "Please check whether the plog file is correct.")
                self.rank_num = rank_num_temp
                rank_id = info_re[2]
                server_id = f"{info_re[3]}.{info_re[4]}.{info_re[5]}.{info_re[6]}"
                device_id = info_re[7]
                self.rank_id_files.update(
                    {rank_id: {'Path': os.path.dirname(plog_file), 'File': os.path.basename(plog_file),
                               'Server_Id': server_id, 'Device_Id': device_id}})

                worker_re = re.match(r"worker-(\d+)$", os.path.basename(os.path.dirname(plog_file)))
                worker_id = worker_re[1]
                self.worker_map.update({rank_id: worker_id})
                self.server_device_map.update({(server_id, device_id): rank_id})
                self.server_device_map.update({rank_id: (server_id, device_id)})

                self.pid_rankid_table.add(f"{pid}-{rank_id}")
                return

    def check_rank_nums(self):
        """
        Check whether log files are valid, including missing logs or redundant logs..
        """
        if self.rank_num == -1:
            rc_logger.error("not found rank_num value. Please check whether the plog file is correct.")
            raise InfoNotFoundError("not found rank_num value. Please check whether the plog file is correct.")
        all_rank_id = [pid_rank.split("-")[1] for pid_rank in list(self.pid_rankid_table)]
        if len(set(all_rank_id)) != len(all_rank_id):
            rc_logger.error("the input file path may contain logs of more than one training session. "
                            "Please check whether the plog file is correct.")
            raise InfoIncorrectError("the input file path may contain logs of more than one training session. "
                                      "Please check whether the plog file is correct.")
        if len(self.rank_id_files) != self.rank_num:
            return False
        return True

    def check_hccl_error(self, parse_err_info, err_list_by_time):
        """
        check hccl error reason and rank_id.
        """
        self.get_first_err_rank(err_list_by_time)
        self.get_last_err_rank(err_list_by_time)
        time_difference = datetime.strptime(self.first_and_last_err_time["Last"], '%Y-%m-%d-%H:%M:%S.%f') - \
                          datetime.strptime(self.first_and_last_err_time["First"], '%Y-%m-%d-%H:%M:%S.%f')
        times = time_difference.total_seconds()
        for reason_index, err_reason in enumerate(self.HCCL_ERR_REASON):
            for rank_id, err_info_list in parse_err_info.items():
                for err_info in err_info_list:
                    if err_reason in err_info and 'HCCL' in err_info:
                        return self.check_hccl_time_out(times, reason_index, rank_id)
        return "all reason do not meet and cannot continue diagnosis. It is not a common error.", UNKNOWN_RANK

    def check_hccl_time_out(self, times, reason_index, rank_id):
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
        if int(self.timeouts['CONNECT_TIMEOUT']) < times:
            reason = f"The cause of this error is '{cate[index]}' due to the fail of Inter-card synchronization. " \
                     f"Please set a longer timeout period."
            return reason, UNKNOWN_RANK
        if self.mode == Mode.FORCE_KILL:
            rankids = self.no_log_rank_id if self.no_log_rank_id else self.error_rank_id
            reason = f"The cause of this error is '{cate[index]}'."
            return reason, rankids
        reason = f"The cause of this error is '{cate[index]}'."
        return reason, UNKNOWN_RANK

    def check_notify_timeout(self, times):
        """
        check notify timeout reason and rank_id.
        """
        if int(self.timeouts['NOTIFY_TIMEOUT']) < times:
            reason = "The cause of this error is 'notify timeout' due to the fail of Inter-card synchronization. " \
                     "Please set a longer timeout period."
            return reason, UNKNOWN_RANK
        if self.mode == Mode.FORCE_KILL:
            if self.no_error_rank_id:
                reason = f"The cause of this error is 'notify timeout'. " \
                         f"Maybe the {self.no_error_rank_id} is/are too slow or core dump"
                return reason, self.no_error_rank_id

            reason = "The cause of this error is 'notify timeout', Notify wait timeout is reported for all ranks."
            return reason, self.error_rank_id

        reason = "The cause of this error is 'notify timeout."
        return reason, UNKNOWN_RANK


def start_rc_diag_job(input_path, output_path, cfg):
    rc_logger.info("start root cluster diagnosis task.")
    rc_diagnosis = RCDiagJob(input_path, cfg)
    rc_result, worker_list = rc_diagnosis.start_rc_diag_job()

    rc_out_file = os.path.join(output_path, "rc_diag_report.json")
    with safe_open(rc_out_file, 'w+', encoding='utf8') as file_stream:
        file_stream.write(json.dumps(rc_result, ensure_ascii=False, indent=4))

    return rc_result, worker_list
