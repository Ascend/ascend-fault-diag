# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
import json
import time

from ascend_fd.pkg.kg_parse.utils import logger
from ascend_fd.tool import safe_open, safe_chmod
from ascend_fd.status import InnerError


TIME_MAX_DIFF = 30 * 60
MAX_EVENT_COUNT = 30


class BMCLogDataDescriptor:
    VALID_FLAGS = {
        "parse_next",
    }

    def __init__(self):
        self.data = dict()

    def __str__(self):
        return json.dumps(self.data, sort_keys=False, indent=4, separators=(',', ':'), ensure_ascii=False)

    @staticmethod
    def get_time_stamp(event: dict):
        struct_time = time.strptime(event["RaiseTime"], "%Y-%m-%d %H:%M:%S")
        try:
            time_stamp = time.mktime(struct_time)
        except OverflowError:
            time_stamp = 0
            pass
        return time_stamp

    @staticmethod
    def judge_same_event(event: dict, next_event: dict):
        for item in event:
            if item in ["RaiseTime", "alarmRaisedTime", "keyinfo"]:
                continue
            else:
                if event[item] != next_event[item]:
                    return False
        return True

    def clear(self):
        self.data.clear()

    def update_events(self, desc):
        pass

    def update(self, desc: dict):
        for name, val in desc.items():
            if name == "events":
                self.update_events(val)
                continue
            if name in self.VALID_FLAGS:
                continue
            logger.error(f"can not find a update method for {name}.")
            raise InnerError(f"can not find a update method for {name}.")

    # 增加 训练任务异常退出(TheTrainingTaskExitsAbnormally)事件
    def add_atlas_virtual_event(self, event_list: list):
        raise_time = "false"
        for ename in event_list:
            event_keyname = "%s_list" % ename
            event_keyname_list = self.data.get(event_keyname, None)
            if event_keyname_list:
                raise_time = event_keyname_list[0].get("RaiseTime", None)
                break
        # If no ATLAS-related fault events are found, the virtual_event_list events are not added.
        if raise_time == "false":
            return
        virtual_event_list = ["TheTrainingTaskExitsAbnormally", "RuntimeFaulty", "FailedToRestartTheProcess",
                              "FailedToLoadTheModel"]
        for event_name in virtual_event_list:
            key_name = "%s_list" % event_name
            if key_name in self.data:
                continue
            event_dict = dict()
            event_dict["keyinfo"] = event_name
            event_dict["RaiseTime"] = raise_time
            event_dict["name"] = event_name
            event_dict["typeName"] = "%s_Alarm" % event_name
            event_dict["alarmRaisedTime"] = raise_time
            event_dict["alarmId"] = event_dict.get("typeName")
            event_dict["alarmName"] = event_dict.get("name")
            event_dict["alarmLevel"] = "重要"
            self.data.setdefault(key_name, []).append(event_dict)

    def add_not_existed_parts(self, part_list: list):
        for entity_name in part_list:
            entity_keyname = "%s_list" % entity_name
            if entity_keyname not in self.data:
                entity_dict = dict()
                if entity_keyname == "NPU_list":
                    entity_dict["board_id"] = "Board1-Board2"
                    entity_dict["npu_id"] = "NPU1-NPU8"
                    entity_dict["name"] = entity_name
                    entity_dict["typeName"] = entity_name
                    self.data.setdefault(entity_keyname, []).append(entity_dict)
                    continue
                if entity_keyname == "Dev_os_list":
                    for dev_os_id in ["dev-os-7", "dev-os-3"]:
                        entity_dict = dict()
                        entity_dict["dev_os_id"] = dev_os_id
                        entity_dict["name"] = entity_name
                        entity_dict["typeName"] = entity_name
                        self.data.setdefault(entity_keyname, []).append(entity_dict)
                    continue
                if entity_keyname == "Dev_npu_list":
                    for numth in range(8):
                        entity_dict = dict()
                        entity_dict["device_id"] = "device-%d" % numth
                        entity_dict["name"] = entity_name
                        entity_dict["typeName"] = entity_name
                        self.data.setdefault(entity_keyname, []).append(entity_dict)
                    continue
                entity_dict["version"] = "V1.0"
                entity_dict["name"] = entity_name
                entity_dict["typeName"] = entity_name
                self.data.setdefault(entity_keyname, []).append(entity_dict)

    def merge_same_entity(self, entities):
        if len(entities) == 1:
            entities[0]["times"] = 1
            return entities

        entities.sort(key=lambda x: x["RaiseTime"])
        reduced_entities = []

        pre_event_dict = entities[0]
        pre_time_stamp = self.get_time_stamp(pre_event_dict)
        count = 1
        for index, event_dict in enumerate(entities[1:]):
            now_time_stamp = self.get_time_stamp(event_dict)
            timing_difference = now_time_stamp - pre_time_stamp
            if not self.judge_same_event(pre_event_dict, event_dict) or \
                    timing_difference > TIME_MAX_DIFF or count >= MAX_EVENT_COUNT:
                pre_event_dict["times"] = str(count)
                reduced_entities.append(pre_event_dict)
                pre_event_dict = event_dict
                pre_time_stamp = now_time_stamp
                count = 1
            else:
                count += 1

            # If it is the last element, it is appended directly into the list.
            if index == len(entities[1:]) - 1:
                pre_event_dict["times"] = str(count)
                reduced_entities.append(pre_event_dict)

        return reduced_entities


class DataDescriptorOfNAIE(BMCLogDataDescriptor):
    ENTITY_PART_NAMES = [
        "OS", "BMC", "BIOS",
        "CPU", "DIMM", "RaidCard",
        "RiserModule", "Disk", "HddBackPlane",
        "PCIE", "VideoCard", "Power",
        "Fan", "MainBoard", "PC_HBA", "Disk",
        "Host", "Device_os", "Device", "Hccn_tool",
        "Dev_os", "Dev_npu", "NPU", "RUNTIME", "GE"
    ]
    ATLAS_EVENT_NAMES = [
        "RuntimeTaskException", "RuntimeAicoreError", "RuntimeModelExecuteTaskFailed",
        "RuntimeAicoreKernelExecuteFailed", "RuntimeStreamSyncFailed", "GEModelStreamSyncFailed", "GERunModelFail"
    ]

    def __init__(self):
        super().__init__()

    def update_events(self, desc):
        desc.sort(key=lambda x: x["time"])
        for item in desc:
            event = dict()
            event["keyinfo"] = item["key_info"]
            event["RaiseTime"] = item["time"]
            if "param0" in item:
                event.update(item["param0"])
            if "param1" in item:
                event.update(item["param1"])
            event["name"] = item["event_type"]
            event["typeName"] = "%s_Alarm" % item["event_type"]
            event["alarmRaisedTime"] = event.get("RaiseTime")
            event["alarmId"] = event.get("typeName")
            event["alarmName"] = event.get("name")
            event["alarmLevel"] = "重要"
            key_name = "%s_list" % item.get("event_type")
            self.data.setdefault(key_name, []).append(event)

    def dump_to_json_file(self, file_path: str):
        self.add_atlas_virtual_event(self.ATLAS_EVENT_NAMES)
        count = 1
        merge_data = dict()
        for key_name, entities in self.data.items():
            merge_entities = self.merge_same_entity(entities)
            for event in merge_entities:
                event["serialNo"] = "key%d" % count
                event["_id"] = "key%d" % count
                count += 1
            merge_data.update({key_name: merge_entities})
        self.data = merge_data
        self.add_not_existed_parts(self.ENTITY_PART_NAMES)
        with safe_open(file_path, "w", encoding="utf-8") as f_dump:
            f_dump.write(self.__str__())
        safe_chmod(file_path, 0o640)
