# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
import os
import time
import json

from ascend_fd.tool import safe_open
from ascend_fd.pkg.kg_parse.log_parser.format_support.bmc_log_file_parser import BMCLogFileParser


class HcclAnalysisResultParserEvent(BMCLogFileParser):
    VALID_PARAMS = {}
    TARGET_FILE_PATTERNS = {
        "/HCCLAnalysisResultFile.json"
    }

    def __init__(self, configs: dict):
        super().__init__(configs)

    def parse(self, file_path: str):
        _desc = dict()
        if not os.path.isfile(file_path):
            raise FileNotFoundError("file '%s' not exists" % file_path)

        with safe_open(file_path, "r", encoding="utf-8") as _fd:
            content = _fd.read()
            content_dict = dict(json.loads(content.strip()))

        for key, v_dict in content_dict.items():
            event_dict = dict()
            # 故障场景做为事件
            # invalid_event_list 为无效故障场景，不解析
            invalid_env_list = ["MissionHcclBandWidth", "MissionRaInitFailed"]
            if key in invalid_env_list:
                continue
            # MissionCheckRanktable、MissionCheckIp、MissionCheckNpuNetStatus三个场景名字修改为更好理解的事件名
            if key == "MissionCheckRanktable":
                key = "MissionConfigurationErr"
            if key == "MissionCheckIp":
                key = "MissionIpConfigurationErr"
            if key == "MissionCheckNpuNetStatus":
                key = "MissionNpuNetStatusErr"

            event_dict["original"] = key
            event_dict["key_info"] = key
            event_dict["event_type"] = key
            event_dict["time"] = time.strftime("%Y-%m-%d %H:%M:%S",
                                           time.localtime(float(os.path.getmtime(file_path))))
            event_dict["file_name"] = "HCCLAnalysisResultFile.json"
            event_dict["file_path"] = "HCCLAnalysisResultFile.json"
            if "events" not in _desc:
                _desc["events"] = list()
            _desc["events"].append(event_dict)
            # 故障事件做为事件
            # invalid_event_list 为无效故障事件，不解析
            invalid_event_list = ["LogLevelErrorInHostLog", "NoErrKeywordInHostLog", "LogLevelLowInHostLog",
                                  "TheEventNotEnabledInHostLog", "WorkingModeCheck", "NoErrKeywordInDeviceLog"]
            for e_key, e_value in v_dict.items():
                if e_key in invalid_event_list:
                    continue
                event_dict = dict()
                event_dict["original"] = e_key
                event_dict["key_info"] = e_value
                event_dict["event_type"] = e_key
                event_dict["time"] = time.strftime("%Y-%m-%d %H:%M:%S",
                                               time.localtime(float(os.path.getmtime(file_path))))
                event_dict["file_name"] = "HCCLAnalysisResultFile.json"
                event_dict["file_path"] = "HCCLAnalysisResultFile.json"
                _desc["events"].append(event_dict)

        # 添加虚拟事件 Hccl集群网络故障(HcclClusterNetworkFaulty)
        event_dict = dict()
        event_dict["original"] = "HcclClusterNetworkFaulty"
        event_dict["key_info"] = "HcclClusterNetworkFaulty"
        event_dict["event_type"] = "HcclClusterNetworkFaulty"
        event_dict["time"] = time.strftime("%Y-%m-%d %H:%M:%S",
                                       time.localtime(float(os.path.getmtime(file_path))))
        event_dict["file_name"] = "HCCLAnalysisResultFile.json"
        event_dict["file_path"] = "HCCLAnalysisResultFile.json"
        _desc["events"].append(event_dict)

        if "events" in _desc and len(_desc["events"]) > 0:
            _desc["parse_next"] = True
            return _desc
        return {"parse_next": True}
