# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
import json
import time

from ascend_fd.pkg.kg_parse.utils import logger
from ascend_fd.tool import safe_open, safe_chmod
from ascend_fd.status import InnerError


class BMCLogDataDescriptor:
    VALID_FLAGS = {
        "parse_next",
    }

    def __init__(self):
        self.data = dict()
        self.efficiency_valid_param = dict()

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
                if event[item] == next_event[item]:
                    continue
                else:
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
            elif name in self.VALID_FLAGS:
                pass
            else:
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
        # 没有找到atlas相关的故障事件则不增加virtual_event_list事件
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
                if entity_keyname == "OS_list":
                    entity_dict["type"] = "OS"
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
        entities.sort(key=lambda x: x["RaiseTime"])
        now_length = len(entities)
        for index in range(now_length):
            try:
                pre_event_dict = entities[index]
            except IndexError:
                break
            if "RaiseTime" in pre_event_dict:
                pre_time_stamp = self.get_time_stamp(pre_event_dict)
                count = 1
                while count < 30:
                    try:
                        next_event_dict = entities[index + 1]
                    except IndexError:
                        break
                    if self.judge_same_event(pre_event_dict, next_event_dict):
                        next_time_stamp = self.get_time_stamp(next_event_dict)
                        timing_variance = next_time_stamp - pre_time_stamp
                        if timing_variance < 30 * 60:
                            del entities[index + 1]
                            count += 1
                        else:
                            break
                    else:
                        index += 1
                        continue
                pre_event_dict["times"] = str(count)
            else:
                continue


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
            if "f_time" in item:
                event["RaiseTime"] = item["f_time"]
            else:
                event["RaiseTime"] = item["time"]
            if "params" in item:
                event.update(item["params"])
            if "params1" in item:
                event.update(item["params1"])
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
        for _, entities in self.data.items():
            self.merge_same_entity(entities)
            for event in entities:
                event["serialNo"] = "key%d" % count
                event["_id"] = "key%d" % count
                count += 1
        self.add_not_existed_parts(self.ENTITY_PART_NAMES)
        with safe_open(file_path, "w", encoding="utf-8") as f_dump:
            f_dump.write(self.__str__())
        safe_chmod(file_path, 0o640)
