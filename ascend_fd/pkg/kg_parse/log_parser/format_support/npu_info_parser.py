# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
import os
import re
import time

from ascend_fd.pkg.kg_parse.log_parser.format_support.bmc_log_file_parser import BMCLogFileParser
from ascend_fd.pkg.kg_parse.utils.log_record import logger
from ascend_fd.tool import safe_open
from ascend_fd.status import FileNotExistError


class LineParser:
    """每一行的解析器"""
    def __init__(self, name, regex, parm_regex=None,
                 parm_dict_func=None, parm_regex1=None,
                 parm_dict_func1=None, parm_regex2=None,
                 parm_dict_func2=None):
        self.name = name
        self.regex = regex
        self.parm_regex = parm_regex
        self.parm_dict_func = parm_dict_func
        self.parm_regex1 = parm_regex1
        self.parm_dict_func1 = parm_dict_func1
        self.parm_regex2 = parm_regex2
        self.parm_dict_func2 = parm_dict_func2

    def parse(self, desc):
        """解析方法"""
        event_dict = dict()
        ret = self.regex.findall(desc)
        if ret:
            event_dict["key_info"] = desc.split("\n")[0]
            event_dict["event_type"] = self.name
            if self.parm_regex is not None:
                ret = self.parm_regex.findall(desc)[0]
                params = self.parm_dict_func(ret)
                event_dict["params"] = params
            if self.parm_regex1 is not None:
                ret = self.parm_regex1.findall(desc)[0]
                params = self.parm_dict_func1(ret)
                event_dict["params1"] = params
            if self.parm_regex2 is not None:
                ret = self.parm_regex2.findall(desc)[0]
                params = self.parm_dict_func2(ret)
                event_dict["params2"] = params
        return event_dict


class NpuInfoParser(BMCLogFileParser):
    """根据提供的正则表达式对文件每行数据进行解析及数据提取"""
    LINE_PARSERS = [
        LineParser(name="NpuRxTxErrBefore",
                   regex=re.compile(
                       r".*?hccn_tool -i.*?-stat -g.*?"),
                   parm_regex=re.compile(r"(hccn_tool -i \d+)"),
                   parm_dict_func=lambda p: {"npu_id": p.split(" ")[2]},
                   parm_regex1=re.compile(r"(roce_rx_err_pkt_num:\d+)"),
                   parm_dict_func1=lambda p: {"rx_err_num": p.split(":")[1]},
                   parm_regex2=re.compile(r"(roce_tx_err_pkt_num:\d+)"),
                   parm_dict_func2=lambda p: {"tx_err_num": p.split(":")[1]}
                   ),
        LineParser(name="NpuRxTxErrAfter",
                   regex=re.compile(
                       r".*?hccn_tool -i.*?-stat -g.*?"),
                   parm_regex=re.compile(r"(hccn_tool -i \d+)"),
                   parm_dict_func=lambda p: {"npu_id": p.split(" ")[2]},
                   parm_regex1=re.compile(r"(roce_rx_err_pkt_num:\d+)"),
                   parm_dict_func1=lambda p: {"rx_err_num": p.split(":")[1]},
                   parm_regex2=re.compile(r"(roce_tx_err_pkt_num:\d+)"),
                   parm_dict_func2=lambda p: {"tx_err_num": p.split(":")[1]}
                   )
        ]

    VALID_PARAMS = {}
    TARGET_FILE_PATTERNS = ["npu_info_path"]

    def __init__(self):
        super().__init__()

    @classmethod
    def parse(cls, file_path_list: list):
        desc = dict()
        desc["events"] = list()
        tmp_event_list_before = list()
        tmp_event_list_after = list()

        for file_path in file_path_list:
            if not os.path.isfile(file_path):
                logger.error(f"file {os.path.basename(file_path)} not exists.")
                raise FileNotExistError(f"file {os.path.basename(file_path)} not exists.")
            time_tamp = time.time()
            t_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_tamp))
            f_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(os.path.getmtime(file_path))))
            logger.info("start parse %s", file_path)
            with safe_open(file_path, mode='r', encoding='utf-8') as _log:
                content = _log.read()
                event_message_list = content.split("\n\n")
                for event_message in event_message_list:
                    if "npu_info_before" in file_path:
                        event_dict_before = cls.LINE_PARSERS[0].parse(event_message)
                        if event_dict_before:
                            tmp_event_list_before.append(event_dict_before)
                    if "npu_info_after" in file_path:
                        event_dict_after = cls.LINE_PARSERS[1].parse(event_message)
                        if event_dict_after:
                            tmp_event_list_after.append(event_dict_after)
            logger.info("end parse %s", file_path)

        tmp_event_list_before.sort(key=lambda x: int(x["params"]["npu_id"]), reverse=False)
        tmp_event_list_after.sort(key=lambda x: int(x["params"]["npu_id"]), reverse=False)
        for err_before, err_after in zip(tmp_event_list_before, tmp_event_list_after):
            # 增加 NpuRxErrIncreased事件
            if int(err_before["params1"]["rx_err_num"]) < int(err_after["params1"]["rx_err_num"]):
                event_dict = dict()
                event_dict["event_type"] = "NpuRxErrIncreased"
                event_dict["key_info"] = err_after["key_info"]
                event_dict["time"] = t_time
                event_dict["f_time"] = f_time
                event_dict["params"] = err_after["params"]
                event_dict["params1"] = err_after["params1"]
                desc.setdefault("events", []).append(event_dict)

            # 增加 NpuTxErrIncreased事件
            if int(err_before["params2"]["tx_err_num"]) < int(err_after["params2"]["tx_err_num"]):
                event_dict = dict()
                event_dict["event_type"] = "NpuTxErrIncreased"
                event_dict["key_info"] = err_after["key_info"]
                event_dict["time"] = t_time
                event_dict["f_time"] = f_time
                event_dict["params"] = err_after["params"]
                event_dict["params1"] = err_after["params2"]
                desc.setdefault("events", []).append(event_dict)

        if "events" in desc and len(desc.get("events", [])) > 0:
            desc["parse_next"] = True
            return desc
        return {"parse_next": True}
