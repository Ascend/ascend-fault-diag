# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. ALL rights reserved.
from collections import defaultdict
import logging
import os
import re
import subprocess

import pandas as pd

from ascend_fd.status import FileNotExistError, InfoNotFoundError
from ascend_fd.tool import safe_read_csv
from ascend_fd.config import NPU_DETAILS_RE, MODEL_ARTS_RANK_RE, EPOCH_TIME_RE

net_logger = logging.getLogger("net_parse.log")

DELAY_PARSE_RULE = "epoch time.*per step time"
NIC_REMAIN_COLUNMS = ['mac_tx_pfc_pkt_num', 'mac_rx_pfc_pkt_num', 'roce_tx_cnp_pkt_num', 'roce_rx_cnp_pkt_num',
                      'roce_tx_rc_pkt_num', 'roce_rx_rc_pkt_num', 'roce_tx_err_pkt_num', 'roce_rx_err_pkt_num']
NIC_OUTPUT_FILE_NAME = 'nic_clean.csv'


def start_net_parse_job(input_path, output_path, files_path_dict):
    """
    start net parse job
    """
    npu_files, delay_files = files_path_dict.get("npu_detail_path", None), files_path_dict.get("delay_path", None)
    worker_id = files_path_dict.get("worker_id", None)
    pair_dict = pair_npu_and_delay_file(npu_files, delay_files, worker_id)
    parse_df = parse_files(pair_dict)
    parse_df.to_csv(os.path.join(output_path, NIC_OUTPUT_FILE_NAME))
    net_logger.info(f"the parsing result is saved in dir {os.path.basename(output_path)}.")


def check_pair_result(pair_dict):
    """
    check pair dict, each key of dict must contain two subkey: npu and delay.
    :param pair_dict: npu_tail csv and modelarts-job log pair dict, the key is "worker-{worker_id}-rank-{rank-id}"
    :return: pair_dict
    """
    for key in pair_dict:
        npu_file = pair_dict[key].get("npu", None)
        delay_file = pair_dict[key].get("delay", None)
        if not npu_file:
            net_logger.error(f'{key} lack npu detail csv')
            raise FileNotExistError(f'{key} lacks npu_detail csv')
        if not delay_file:
            net_logger.error(f'{key} lack modelarts-job csv')
            raise FileNotExistError(f'{key} lacks modelarts-job csv')
    return pair_dict


def pair_npu_and_delay_file(npu_files, delay_files, worker_id):
    """
    pair npu_detail csv files and modelarts-job log files by rank id
    :param npu_files: npu_detail csv files
    :param delay_files: modelarts-job log files
    :param worker_id: worker id
    :return: pair_dict: pair dict, the key of dict is 'work-{work_index}-rank-{rank_index}'
    """
    pair_dict = defaultdict(defaultdict)
    for file in npu_files:
        rank_re = re.match(NPU_DETAILS_RE, os.path.basename(file))
        if not rank_re:
            continue
        key = f"{worker_id}-rank-{rank_re[1]}"
        pair_dict[key]["npu"] = file

    for file in delay_files:
        rank_re = re.match(MODEL_ARTS_RANK_RE, os.path.basename(file))
        if not rank_re:
            continue
        key = f"{worker_id}-rank-{rank_re[1]}"
        pair_dict[key]["delay"] = file
    return check_pair_result(pair_dict)


def parse_files(pair_files):
    """
    parse each rank's npu_details csv file and modelarts-job file, adn concat parse results
    :param pair_files: pair dict each key of dict contain two subkey: npu and delay.
    :return: pandas dataformat
    """
    net_logger.info("start parse npu and delay files.")
    if not pair_files:
        net_logger.error("no npu_detail csv file and modelarts-job log files that"
                         " meets the path specifications is found.")
        raise FileNotExistError("no npu_detail csv file and modelarts-job log files that"
                                " meets the path specifications is found.")

    parse_list = list()
    for raw_name in pair_files:
        npu_file, delay_file = pair_files[raw_name].get("npu", None), pair_files[raw_name].get("delay", None)
        npu_df = parse_single_npu_file(raw_name, npu_file)
        delay_df = parse_single_delay_file(raw_name, delay_file)
        parse_list.append(pd.concat([delay_df, npu_df], axis=1))
        net_logger.info(f"npu_detail csv file and modelarts-job log file of {raw_name} parse succeed.")
    return pd.concat(parse_list)


def parse_single_npu_file(raw_name, npu_file):
    """
    parse single npu_file. 1) select a part of columns, 2) calculate mean, 3) change the columns name and raw name
    :param raw_name: e.g. work-{work_index}-rank-{rank_index}
    :param npu_file: npu_detail csv file
    :return:
    """
    npu_pd = safe_read_csv(npu_file)
    npu_pd = npu_pd[NIC_REMAIN_COLUNMS]
    npu_pd = npu_pd.mean().to_frame().T
    npu_pd.columns = [col + '_mean' for col in NIC_REMAIN_COLUNMS]
    npu_pd.index = [raw_name]
    return npu_pd


def get_step_value_from_file(delay_file):
    """
    get "per step time" value from modelarts-jobs log
    :param delay_file: modelarts-jobs log path
    :return: "per step time" value list
    """
    step_value = list()
    grep = subprocess.Popen(["/usr/bin/grep", DELAY_PARSE_RULE, delay_file],
                            shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logs = grep.stdout.readlines()
    if not logs:
        net_logger.error(f'no "epoch-time" or "per step time" in {os.path.basename(delay_file)}')
        raise InfoNotFoundError(f'no "epoch-time" or "per step time" in {os.path.basename(delay_file)}')
    for log in logs:
        # only 'per_step_time' is userful
        delay_re = re.match(EPOCH_TIME_RE, log.decode())
        if not delay_re:
            continue
        epoch_time, per_step_time = delay_re[1], delay_re[2]
        step_value.append(float(per_step_time))
    if not step_value:
        net_logger.error(f'no "per step time" in {os.path.basename(delay_file)}')
        raise InfoNotFoundError(f'no "per step time" in {os.path.basename(delay_file)}')
    return step_value


def calculate_metric_by_step_value(delay_df):
    """
    calculate metric by step value, the first column data is not userful
    :param delay_df: step value
    :return: metric statistics
    """
    median_df = delay_df.loc[:, 1:].median(axis=1)
    median_df.name = "median"

    mean_df = delay_df.loc[:, 1:].mean(axis=1)
    mean_df.name = "mean"

    std_df = delay_df.loc[:, 1:].std(axis=1)
    std_df.name = "std"

    var_df = delay_df.loc[:, 1:].var(axis=1)
    var_df.name = "var"

    max_df = delay_df.loc[:, 1:].var(axis=1)
    max_df.name = "max"

    min_df = delay_df.loc[:, 1:].max(axis=1)
    min_df.name = "min"
    return pd.concat([median_df, mean_df, std_df, var_df, max_df, min_df], axis=1)


def parse_single_delay_file(raw_name, delay_file):
    """
    parse single modelarts-jobs log
    :param raw_name: e.g. work-{work_index}-rank-{rank_index}
    :param delay_file: modelarts-jobs log
    :return:
    """
    delay_df_dict = dict()
    delay_df_dict[raw_name] = get_step_value_from_file(delay_file)
    delay_df = pd.DataFrame(delay_df_dict).T
    return calculate_metric_by_step_value(delay_df)
