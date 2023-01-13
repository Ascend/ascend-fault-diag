# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
import collections
import json
import re
import time

from ascend_fd.tool import safe_open
from ascend_fd.pkg.kg_parse.utils.log_record import logger


class UpdateMethodNotSupportedError(RuntimeError):
    pass


class BMCLogDataDescriptor:
    VALID_FLAGS = {
        "parse_next",
    }

    def __init__(self, config):
        self.config = config
        self.data = dict()
        self.efficiency_valid_param = dict()
        self.disk_command_timeout_param = dict()
        self.hardware_normal = True
        self.hardware_events = [
            "RaidFault",
            "RAIDSelf-checkIsFailure",
            "PowerFailure",
            "DiskAFailure",
            "DiskFault",
            "CPUCEThresholdByPFAE",
            "CPU_UCE",
            "CableConnectIncorrectly",
            "RAIDCardCommunicationLoss",
            "MainBoardPowerAbnormal",
            "MemCEThresholdByPFAE",
            "MemCE",
            "MemCEOverflow",
            "MemCEThresholdByPFAE",
            "MemFailure",
            "MemConfigurationEerror",
            "Mcerr",
            "CPUOverHeating",
            "Caterr",
            "CaterrDiagnose",
            "IERR",
            "CPU_UCE",
            "GetCPUTemperatureFailure",
            "GetMEMTemperatureFailure",
            "CPU_CE",
            "CPU_PollutionArea",
            "HostCheckerTimeout",
            "PowerFailure",
            "CPU_VRD_Failed",
            "ClockSignalLost",
            "hllc_int_re_training",
            "IERRDiagnoseFailure",
            "RAID_UCE",
            "RaidCEThreshold",
            "LinkBitError",
            "RAIDCardCommunicationLoss",
            "PCIE_Fault",
            "PCIE_UCE",
            "PCIE_CE",
            "Multi_PCIE_UCE",
        ]

    def clear(self):
        self.data.clear()

    def update_events(self, desc):
        pass

    def update_parts(self, desc):
        pass

    def update_time(self, desc):
        pass

    def update(self, desc: dict):
        for _name, _val in desc.items():
            if _name == "events":
                self.update_events(desc["events"])
            elif _name == "parts":
                self.update_parts(desc["parts"])
            elif _name == "time":
                self.update_time(desc["time"])
            elif _name in self.VALID_FLAGS:
                pass
            else:
                raise UpdateMethodNotSupportedError("can not find a update method for '%s'." % _name)

    # 增加 训练任务异常退出(TheTrainingTaskExitsAbnormally)事件
    def add_atlas_virtual_event(self, event_list: list):
        raise_time = "false"
        for ename in event_list:
            event_keyname = "%s_list" % ename
            if event_keyname in self.data:
                raise_time = self.data[event_keyname][0]["RaiseTime"]
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
            event_dict["alarmId"] = event_dict["typeName"]
            event_dict["alarmName"] = event_dict["name"]
            event_dict["alarmLevel"] = "重要"
            self.data[key_name] = list()
            self.data[key_name].append(event_dict)

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
                    self.data[entity_keyname] = list()
                    self.data[entity_keyname].append(entity_dict)
                    continue
                if entity_keyname == "Dev_os_list":
                    for dev_os_id in ["dev-os-7", "dev-os-3"]:
                        entity_dict = dict()
                        entity_dict["dev_os_id"] = dev_os_id
                        entity_dict["name"] = entity_name
                        entity_dict["typeName"] = entity_name
                        if entity_keyname not in self.data:
                            self.data[entity_keyname] = list()
                        self.data[entity_keyname].append(entity_dict)
                    continue
                if entity_keyname == "Dev_npu_list":
                    for numth in range(8):
                        entity_dict = dict()
                        entity_dict["device_id"] = "device-%d" % numth
                        entity_dict["name"] = entity_name
                        entity_dict["typeName"] = entity_name
                        if entity_keyname not in self.data:
                            self.data[entity_keyname] = list()
                        self.data[entity_keyname].append(entity_dict)
                    continue
                entity_dict["version"] = "V1.0"
                entity_dict["name"] = entity_name
                entity_dict["typeName"] = entity_name
                self.data[entity_keyname] = list()
                self.data[entity_keyname].append(entity_dict)

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

    def merge_same_entity(self, entities):
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

    def process_pcie(self, pcie_event):
        if "params" in pcie_event and "slot" in pcie_event["params"]:
            if pcie_event["params"]["slot"] != "unknown":
                pcie_event["params"]["slot"] = "SLOT" + pcie_event["params"]["slot"]
        elif "params" in pcie_event and "slot" not in pcie_event["params"]:
            pcie_event["params"]["slot"] = "unknown"
        else:
            pcie_event["params"] = dict()
            pcie_event["params"]["slot"] = "unknown"

    def __str__(self):
        return json.dumps(self.data, sort_keys=False, indent=4, separators=(',', ':'), ensure_ascii=False)


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
        "HcclClusterNetworkFaulty", "MissionSocketTimeout", "MissionNotifyWaitTimeout", "MissionP2PTimeout",
        "MissionConfigurationErr", "TheTimeoutThresholdTooLargeOnHccl", "InconsistentOperatorInitialization",
        "OperatorTagsInconsistent", "TLSInconsistentSettings", "DeviceNoErrorReportedONSomeCard",
        "ExistErr_task_type14", "TheErrReportingTimeGreaterThan500s", "TheKeywordErrorCqeExists",
        "RankEnterTimeGreaterThan120s", "RanktableConfigurationErr", "MissionIpConfigurationErr",
        "MissionNpuNetStatusErr", "SameDeviceIpErr", "VariedNetmaskErr", "SameNetSegErr", "DiffNetSegErr",
        "DeviceLinkDown", "NetHealthFail", "HbmMultibitEccError", "TsException", "Dma0x80Err", "DmpGetDieidFailed",
        "HwtsTimeoutException", "AicoreTaskException", "HisiTsException", "HisiDriverException", "HisiMultiEccErr",
        "AICoreAIC_ERROR", "HwtsAicReset", "ResetRunningSlot", "NpuHasCriticalProblem", "RuntimeTaskException",
        "RuntimeAicoreError", "RuntimeModelExecuteTaskFailed", "RuntimeAicoreKernelExecuteFailed",
        "RuntimeStreamSyncFailed", "GEModelStreamSyncFailed", "GERunModelFail"
    ]
    SERVER_BIOS_DICT = {
        "RH1288 V3": "5.13",
        "RH2288 V3": "5.13",
        "RH2288H V3": "5.13",
        "5288 V3": "5.13",
        "RH5885 V3": "8.28",
        "RH5885H V3": "8.28",
        "RH8100 V3": "8.28",
        "1288H V5": "0.81",
        "2288H V5": "0.81",
        "5288 V5": "0.81",
    }

    def __init__(self, config):
        super().__init__(config)

    def update_events(self, desc):
        desc.sort(key=lambda x: x["time"])
        for item in desc:
            if item["event_type"] in self.hardware_events:
                self.hardware_normal = False
            if item["event_type"] == "TheHardwareNormal" and not self.hardware_normal:
                continue
            if "PCIE" in item["event_type"] or "NIC" in item["event_type"]:
                self.process_pcie(item)
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
            event["alarmRaisedTime"] = event["RaiseTime"]
            event["alarmId"] = event["typeName"]
            event["alarmName"] = event["name"]
            event["alarmLevel"] = "重要"
            key_name = "%s_list" % item["event_type"]
            if key_name not in self.data:
                self.data[key_name] = list()
            self.data[key_name].append(event)

    def update_parts(self, desc):
        for key, parts in desc.items():
            if key in ["CustomPowerPolicy", "BIOS", "product_name"]:
                self.efficiency_valid_param[key] = desc[key]
                continue
            if key in self.ENTITY_PART_NAMES:
                for part in parts:
                    part["name"] = key
                    part["typeName"] = key
                    key_name = "%s_list" % key
                    if key_name not in self.data:
                        self.data[key_name] = list()
                    self.data[key_name].append(part)

    def _is_valid_efficiency(self):
        if "Efficiency_list" in self.data:
            if "CustomPowerPolicy" in self.efficiency_valid_param:
                c_key = self.data["Efficiency_list"][0]["value"]
                c_value = self.efficiency_valid_param["CustomPowerPolicy"][c_key]
                if c_value != "Efficiency":
                    del self.data["Efficiency_list"]
                    return
            if "BIOS" in self.efficiency_valid_param and "product_name" in self.efficiency_valid_param:
                bios_version = self.efficiency_valid_param["BIOS"]["version"]
                product_name = self.efficiency_valid_param["product_name"]["version"]
                std_bios_version = self.SERVER_BIOS_DICT[product_name] if product_name in self.SERVER_BIOS_DICT else None
                if std_bios_version is None or (float(bios_version) >= float(std_bios_version)):
                    del self.data["Efficiency_list"]
                    return

    def dump_to_json_file(self, file_path: str):
        self.add_atlas_virtual_event(self.ATLAS_EVENT_NAMES)
        self.add_not_existed_parts(self.ENTITY_PART_NAMES)
        count = 1
        for entity_name, entities in self.data.items():
            self.merge_same_entity(entities)
            for event in entities:
                event["serialNo"] = "key%d" % count
                event["_id"] = "key%d" % count
                count += 1
        self._is_valid_efficiency()
        with safe_open(file_path, "w", encoding="utf-8") as f_dump:
            f_dump.write(self.__str__())


class DataDescriptorOfDFSBrain(BMCLogDataDescriptor):

    def __init__(self, config):
        super().__init__(config)
        self.logs = set()

    def create_basic_structure(self, unpack=True):
        if not unpack:
            self.data["support"] = "false"
        else:
            self.data["support"] = "true"
            self.data["LogTime"] = "unknown"
            self.data["log_files"] = list()
            self.data["configs"] = dict()
            self.data["configs"]["hosts"] = list()
            host_dict = dict()
            host_dict["os"] = dict()
            host_dict["physical_machine"] = dict()
            self.data["configs"]["hosts"].append(host_dict)

    def update_events(self, desc):
        desc.sort(key=lambda x: x["time"])
        file_events_list = dict()
        for item in desc:
            if item["event_type"] in self.hardware_events:
                self.hardware_normal = False
            if item["event_type"] == "TheHardwareNormal" and not self.hardware_normal:
                continue
            if "PCIE" in item["event_type"] or "NIC" in item["event_type"]:
                self.process_pcie(item)
            file_name = item["file_name"]
            self.logs.update(file_name)
            file_path = item["file_path"]
            event_dict = dict()
            if file_name == "eo_sel":
                event_dict["id"] = item["original"]["EvtID"]
                event_dict["type"] = item["original"]["EventType"]
                event_dict["Severity"] = item["original"]["Severity"]
            if "f_time" in item:
                event_dict["OccurDateTime"] = item["f_time"]
            else:
                event_dict["OccurDateTime"] = item["time"]
            if "params" in item and "params1" in item:
                detail = item["key_info"]
                for key, value in item["params1"].items():
                    detail = "[%s: %s]%s" % (key, value, detail)
                for key, value in item["params"].items():
                    detail = "[%s: %s]%s" % (key, value, detail)
                event_dict["Detail"] = detail
            elif "params" in item and "params1" not in item:
                detail = item["key_info"]
                for key, value in item["params"].items():
                    detail = "[%s: %s]%s" % (key, value, detail)
                event_dict["Detail"] = detail
            elif "params1" in item and "params" not in item:
                detail = item["key_info"]
                for key, value in item["params1"].items():
                    detail = "[%s: %s]%s" % (key, value, detail)
                event_dict["Detail"] = detail
            else:
                event_dict["Detail"] = item["key_info"]
            event_dict["Detail"] = "[nodeName: %s]%s" % (item["event_type"], event_dict["Detail"])
            key_name = "%s_%s" % (file_name, file_path)
            if key_name not in file_events_list:
                file_events_list[key_name] = dict()
                file_events_list[key_name]["name"] = file_name
                file_events_list[key_name]["path"] = file_path
                if file_name == "eo_sel":
                    file_events_list[key_name]["alarms"] = list()
                else:
                    file_events_list[key_name]["events"] = list()
            if file_name == "eo_sel":
                file_events_list[key_name]["alarms"].append(event_dict)
            else:
                file_events_list[key_name]["events"].append(event_dict)
        for events in file_events_list.values():
            self.data["log_files"].append(events)

    def update_parts(self, desc):
        for key, parts in desc.items():
            if key in ["CustomPowerPolicy", "BIOS", "product_name"]:
                self.efficiency_valid_param[key] = desc[key]
                continue
            if key in ["IOExceedQueue", "ES3000V3_Model"]:
                self.disk_command_timeout_param[key] = desc[key]
                continue
            if key in ["memories", "CPUs", "PSU", "PCIE", "RAID", "Disk", "Disk_smart"]:
                for part in parts:
                    if key not in self.data["configs"]["hosts"][0]["physical_machine"]:
                        self.data["configs"]["hosts"][0]["physical_machine"][key] = list()
                    self.data["configs"]["hosts"][0]["physical_machine"][key].append(part)
            elif key in ["bmc", "cpu_field", "physical_machine", "os"]:
                if key == "os":
                    if "os" not in self.data["configs"]["hosts"][0]:
                        self.data["configs"]["hosts"][0]["os"] = dict()
                    self.data["configs"]["hosts"][0]["os"].update(desc["os"])
                elif key == "bmc":
                    is_host_exit = "configs" in self.data and "hosts" in self.data["configs"]
                    is_physical_machine_exit = self.data["configs"]["hosts"] and \
                                               "physical_machine" in self.data["configs"]["hosts"][0]
                    is_mainboard_exit = "mainboard" in self.data["configs"]["hosts"][0]["physical_machine"]
                    if is_host_exit and is_physical_machine_exit and is_mainboard_exit:
                        self.data["configs"]["hosts"][0]["physical_machine"]["mainboard"].update(desc)
                elif key == "cpu_field":
                    is_host_exit = "configs" in self.data and "hosts" in self.data["configs"]
                    is_physical_machine_exit = self.data["configs"]["hosts"] and \
                                               "physical_machine" in self.data["configs"]["hosts"][0]
                    is_cpus_exit = "CPUs" in self.data["configs"]["hosts"][0]["physical_machine"]
                    if is_host_exit and is_physical_machine_exit and is_cpus_exit:
                        for cpu in self.data["configs"]["hosts"][0]["physical_machine"]["CPUs"]:
                            cpu.update(desc["cpu_field"])
                elif key == "physical_machine":
                    if "physical_machine" not in self.data["configs"]["hosts"][0]:
                        self.data["configs"]["hosts"][0]["physical_machine"] = dict()
                    self.data["configs"]["hosts"][0]["physical_machine"].update(desc["physical_machine"])

    def update_time(self, desc):
        if "LogTime" in self.data:
            self.data["LogTime"] = desc["collect_time"]

    def _is_disk_command_timeout(self):
        for _, item in enumerate(self.data["log_files"]):
            if item["name"] == "RAID_Card1_com_log":
                events = item["events"]
                if "IOExceedQueue" in self.disk_command_timeout_param and \
                        "ES3000V3_Model" in self.disk_command_timeout_param:
                    for event in events:
                        event["Detail"] = event["Detail"].replace("DiskCommandTimeout", "ES3000V3DiskCommandTimeout")

    def _is_valid_efficiency(self):
        for index, item in enumerate(self.data["log_files"]):
            if item["name"] == "options":
                events = item["events"]
                if "CustomPowerPolicy" in self.efficiency_valid_param:
                    c_key = re.compile(r"\[value:\s*(\d+)\]").findall(events[0]["Detail"])[0]
                    c_value = self.efficiency_valid_param["CustomPowerPolicy"][c_key]
                    if c_value != "Efficiency":
                        del self.data["log_files"][index]
                        return
                    events[0]["Detail"] = events[0]["Detail"].replace("[value: %s]" % c_key, "")
                if "BIOS" in self.efficiency_valid_param and "product_name" in self.efficiency_valid_param:
                    bios_version = self.efficiency_valid_param["BIOS"]["version"]
                    product_name = self.efficiency_valid_param["product_name"]["version"]
                    std_bios_version = self.SERVER_BIOS_DICT[product_name] if product_name in self.SERVER_BIOS_DICT else None
                    if std_bios_version and (float(bios_version) >= float(std_bios_version)):
                        del self.data["log_files"][index]
                        return

    def dump_to_json_file(self, file_path: str):
        file_names = list()
        self._is_valid_efficiency()
        self._is_disk_command_timeout()
        for file in self.data["log_files"]:
            if "alarms" in file:
                if file["alarms"] is not None:
                    file_names.append(file["name"])
                else:
                    continue
            elif "events" in file:
                if file["events"] is not None:
                    file_names.append(file["name"])
                else:
                    continue
        try:
            self.data["configs"]["hosts"][0]["physical_machine"]["mainboard"]["bmc"]["logs"] = file_names
            self.data["configs"]["hosts"][0]["os"]["logs"] = file_names
        except Exception:
            logger.warning("set configs-hosts physical_machine-mainboard-bmc and os logs failed")
        with safe_open(file_path, "w", encoding="utf-8") as f_dump:
            f_dump.write(self.__str__())
