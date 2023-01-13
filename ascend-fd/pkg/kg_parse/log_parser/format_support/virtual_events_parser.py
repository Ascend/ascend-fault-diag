# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
import os
import time

from ascend_fd.pkg.kg_parse.utils import PathFilter


class VirtualEventsParser:

    VIRTUAL_EVENTS = [
        "OSFault",
        "UnableToAccessTheSystem",
        "TheHardwareNormal",
        "ServiceAbnormal",
        "vmware_PSOD",
        "TheNicCannotBeIdentified",
        "NICFault",
        "LOMFault",
        "PCIelinkIsUnstable",
        "FanIsLoud",
        "FailedToSendDHCPPackets",
        "RiserCardAbnormal",
        "LOMiDriverBug",
        "RaidCardFWBug",
        "RaidFault",
        "BBUAbnormal",
        "DiskBackplaneFWHang",
        "BIOSIdentifyRaidFailure",
        "IBMCIdentifyRaidFailure",
        "HighDiskLatency"
    ]

    TARGET_FILE_PATTERNS = [
        "dump_log",
    ]

    def __init__(self, config):
        self.config = config
        self.filters = list()
        self.__load_filters()

    def __load_filters(self):
        for item in self.TARGET_FILE_PATTERNS:
            _filter = PathFilter()
            _filter.add_path_pattern(item, sep='/')
            self.filters.append(_filter)

    def find_log(self, file_list):
        logs = list()
        for _f in self.filters:
            _res = _f.filter(file_list)
            if len(_res) > 0:
                for _path in _res:
                    if _path not in logs:  # 存在不同规则筛选出相同的文件的情况，需要去重
                        logs.append(_path)
        return logs

    def parse(self, file_path):
        desc = dict()
        for item in self.VIRTUAL_EVENTS:
            event_obj = dict()
            if item == "TheHardwareNormal":
                detail = "No hardware exception is detected in the current system. The fault may be caused by the OS"
                event_obj["original"] = detail
                event_obj["key_info"] = detail
            else:
                event_obj["original"] = item
                event_obj["key_info"] = item
                event_obj["key_info"] = item
            event_obj["event_type"] = item
            event_obj["time"] = time.strftime("%Y-%m-%d %H:%M:%S",
                                              time.localtime(float(os.path.getmtime(file_path))))
            event_obj["file_name"] = "systemcom_dat"
            event_obj["file_path"] = "dump_info" + file_path.split("dump_info")[-1]
            if "events" not in desc:
                desc["events"] = list()
            desc["events"].append(event_obj)
        desc["parse_next"] = False
        return desc