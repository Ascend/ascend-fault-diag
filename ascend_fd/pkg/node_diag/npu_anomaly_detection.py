# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. ALL rights reserved.
import logging
import os
import re
import time

import numpy as np
import pandas as pd

from ascend_fd.config import IP_ADDR_RE, WORKER_DIR_RE
from ascend_fd.status import FileNotExistError
from ascend_fd.tool import safe_read_csv
from ascend_fd.pkg.node_diag.template import FAULT_TEMP

node_logger = logging.getLogger("node_diag.log")
RATE_FREQ_THRESHOLD = 900
TEMP_THRESHOLD = 105
SPEED_THRESHOLD = 10000


def start_npu_anomaly_detection_job(input_path, cfg):
    result = {
        'analyze_success': True
    }
    try:
        result['root_causes'] = nad_job(input_path, cfg)
    except Exception as err:
        result['analyze_success'] = False
        node_logger.error("npu anomaly detection job error: %s.", err)
    return result


def nad_job(input_path, cfg):
    npu_data = get_all_nad_csv(cfg)
    fan_data = None
    events = list()

    conf = upload_conf()

    rated_freq = conf.get("rated_freq", RATE_FREQ_THRESHOLD)
    if 'rated_freq' in npu_data.columns:
        rated_freq = np.max(npu_data['rated_freq'])
    anomaly_data = npu_data[npu_data['freq'] < rated_freq]
    if anomaly_data.empty:
        events.append(get_event_detail('0'))
        return events
    anomaly = get_anomaly(anomaly_data)
    ip_addr = re.findall(IP_ADDR_RE, input_path)
    if ip_addr:
        anomaly['ip'] = ip_addr[0]
    if not is_temp_high(anomaly, anomaly_data, conf.get("temp_threshold", TEMP_THRESHOLD)):
        # temperature does not exceed the threshold, npu frequency reduction
        events.append(get_event_detail('21', anomaly))
        return events
    if fan_data is None:
        # temperature exceeds threshold, no fan data, over-temperature frequency
        events.append(get_event_detail('24', anomaly))
        return events
    if fan_status_failure(anomaly, fan_data):
        # fan failure
        events.append(get_event_detail('22', anomaly))
        return events
    if fan_speed_low(anomaly, fan_data, conf.get("speed_threshold", SPEED_THRESHOLD)):
        # low fan speed
        events.append(get_event_detail('23', anomaly))
        return events
    # fan ok
    events.append(get_event_detail('24', anomaly))
    return events


def get_all_nad_csv(cfg):
    df_list = list()
    parse_data = cfg.get('parse_data', None)
    for worker in parse_data:
        file = parse_data[worker].get('nad_clean_path', None)
        if file:
            data_frame = safe_read_csv(file, dtype={"dev_id": str})
            data_frame["dev_id"] = worker + "-rank-" + data_frame["dev_id"]
            df_list.append(data_frame)
    return pd.concat(df_list)


def upload_conf():
    return {
        "rated_freq": RATE_FREQ_THRESHOLD,
        "temp_threshold": TEMP_THRESHOLD,
        "speed_threshold": SPEED_THRESHOLD
    }


def get_event_detail(event_type, anomaly=None):
    event = FAULT_TEMP[str(event_type)]
    if event_type == '0':
        return event
    event['fault_detail']['begin_time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(anomaly['begin']))
    event['fault_detail']['end_time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(anomaly['end']))
    event['fault_detail']['node_ip'] = anomaly['ip'] if 'ip' in anomaly else 'unknown'
    event['description_zh_CN'] = event['description_zh_CN'].format(dev_id=anomaly['npu_list'])
    event['description_en_US'] = event['description_en_US'].format(dev_id=anomaly['npu_list'])
    if event_type == '21':
        event['suggestion_zh_CN'] = event['suggestion_zh_CN'].format(dev_id=anomaly['npu_list'])
        event['suggestion_en_US'] = event['suggestion_en_US'].format(dev_id=anomaly['npu_list'])
    elif event_type == '22' or event_type == '23':
        event['suggestion_zh_CN'] = event['suggestion_zh_CN'].format(dev_id=anomaly['fan_list'])
        event['suggestion_en_US'] = event['suggestion_en_US'].format(dev_id=anomaly['fan_list'])
    return event


def get_anomaly(anomaly_data):
    if anomaly_data:
        return dict()
    npu_list = list(set(anomaly_data['dev_id']))
    begin = np.min(anomaly_data['time'])
    end = np.max(anomaly_data['time'])
    npu_list.sort()
    return {
        'npu_list': npu_list,
        'begin': begin,
        'end': end
    }


def is_temp_high(anomaly, anomaly_data, temp_threshold):
    temp_high = anomaly_data[(anomaly['temp'] >= temp_threshold) & (anomaly_data['time'] >= anomaly['begin']) &
                             (anomaly_data['time'] <= anomaly['end'])]
    return len(temp_high) > 0


def fan_status_failure(anomaly, fan_data):
    fan_failure = fan_data[((fan_data['rspeed'] == 'no') | (fan_data['fspeed'] == 'no')) &
                           (fan_data['time'] >= anomaly['begin']) & (fan_data['time'] <= anomaly['end'])]
    fan_list = list(set(fan_failure['fan_id']))
    fan_list.sort()
    anomaly['fan_list'] = fan_list
    return len(fan_list) > 0


def fan_speed_low(anomaly, fan_data, speed_threshold):
    fan_failure = fan_data[(fan_data['rspeed'] != 'no') & (fan_data['fspeed'] != 'no') &
                           (fan_data['time'] >= anomaly['begin']) & (fan_data['time'] <= anomaly['end'])]
    fan_failure[["rspeed"]] = fan_failure[["rspeed"]].astype(int)
    fan_failure[["fspeed"]] = fan_failure[["fspeed"]].astype(int)
    fan_failure = fan_failure[(fan_failure["rspeed"] < speed_threshold) |
                              (fan_failure['fspeed'] < speed_threshold)]
    fan_list = list(set(fan_failure['fan_id']))
    fan_list.sort()
    anomaly['fan_list'] = fan_list
    return len(fan_list) > 0
