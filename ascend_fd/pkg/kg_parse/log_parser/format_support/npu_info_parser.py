# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. All rights reserved.
import os
import re
import time

from ascend_fd.pkg.kg_parse.log_parser.format_support.bmc_log_file_parser import BMCLogFileParser
from ascend_fd.pkg.kg_parse.utils.log_record import logger
from ascend_fd.tool import safe_open
from ascend_fd.status import FileNotExistError, InfoNotFoundError


class NpuInfoLineParser:
    """Line info parser for npu info."""
    def __init__(self, name):
        self.name = name
        self.regex = re.compile(r".*?hccn_tool -i.*?-stat -g.*?")
        self.npu_id_regex = re.compile(r"(hccn_tool -i \d+)")
        self.npu_id_dict_func = lambda p: {"npu_id": p.split(" ")[2]}  # the "2" use to get the (\d+) in regex
        self.rx_err_regex = re.compile(r"(roce_rx_err_pkt_num:\d+)")
        self.rx_err_dict_func = lambda p: {"rx_err_num": p.split(":")[1]}  # the "1" use to get the (\d+) in regex
        self.tx_err_regex = re.compile(r"(roce_tx_err_pkt_num:\d+)")
        self.tx_err_dict_func = lambda p: {"tx_err_num": p.split(":")[1]}  # the "1" use to get the (\d+) in regex

    def parse(self, desc):
        """
        parse each paragraph in npu info file.
        :param desc: single paragraph
        :return: evnet_dict: parsed event saved by dict
        """
        event_dict = dict()
        ret = self.regex.findall(desc)
        if ret:
            event_dict["key_info"] = desc.split("\n")[0]
            event_dict["event_type"] = self.name
            # Regular matches the NPU ID
            ret = self.npu_id_regex.findall(desc)
            if not ret:
                logger.error("cannot find npu id in npu info file.")
                raise InfoNotFoundError("cannot find npu id in npu info file.")
            npu_id = self.npu_id_dict_func(ret[0])
            event_dict.update(npu_id)

            # Regular matches the RX Err NUM
            ret = self.rx_err_regex.findall(desc)
            if not ret:
                logger.error("cannot find rx err num in npu info file.")
                raise InfoNotFoundError("cannot find rx err num in npu info file.")
            rx_err_num = self.rx_err_dict_func(ret[0])
            event_dict.update(rx_err_num)

            # Regular matches the TX Err NUM
            ret = self.tx_err_regex.findall(desc)
            if not ret:
                logger.error("cannot find tx err num in npu info file.")
                raise InfoNotFoundError("cannot find tx err num in npu info file.")
            tx_err_num = self.tx_err_dict_func(ret[0])
            event_dict.update(tx_err_num)
        return event_dict


class NpuInfoParser(BMCLogFileParser):
    """The NPU Info parser."""
    LINE_PARSERS = [
        NpuInfoLineParser("NpuRxTxErrBefore"),   # npu info before lineparser
        NpuInfoLineParser("NpuRxTxErrAfter")   # npu info after lineparser
        ]

    VALID_PARAMS = {}
    TARGET_FILE_PATTERNS = ["npu_info_path"]

    def __init__(self):
        super().__init__()

    @classmethod
    def parse(cls, file_path_list: list):
        """
        parse the npu_info_before.txt and npu_info_after.txt.
        :param file_path_list: [npu_info_before.txt, npu_info_after.txt]
        :return: the event_dict list: [event_dict, ...]
        """
        desc = dict()
        desc["events"] = list()
        tmp_event_list_before = list()
        tmp_event_list_after = list()

        before_parse_flag = False
        after_parse_flag = False

        for file_path in file_path_list:
            if not os.path.isfile(file_path):
                logger.error(f"file {os.path.basename(file_path)} not exists.")
                raise FileNotExistError(f"file {os.path.basename(file_path)} not exists.")
            logger.info("start parse %s", file_path)
            with safe_open(file_path, mode='r', encoding='utf-8') as _log:
                content = _log.read()
                # the hccn_tool command execution result is separated by '\n\n' in npu_info_{before/after}.txt file
                event_message_list = content.split("\n\n")
                for event_message in event_message_list:
                    if "npu_info_before" in file_path:
                        event_dict_before = cls.LINE_PARSERS[0].parse(event_message)
                        if event_dict_before:
                            tmp_event_list_before.append(event_dict_before)
                        before_parse_flag = True
                        continue
                    if "npu_info_after" in file_path:
                        file_time = time.strftime("%Y-%m-%d %H:%M:%S",
                                                  time.localtime(float(os.path.getmtime(file_path))))
                        event_dict_after = cls.LINE_PARSERS[1].parse(event_message)
                        if event_dict_after:
                            tmp_event_list_after.append(event_dict_after)
                        after_parse_flag = True
                        continue
            logger.info("end parse %s", file_path)

        if not before_parse_flag:
            logger.error("the npu_info_before.txt file is missing.")
            raise FileNotExistError("the npu_info_before.txt file is missing.")
        if not after_parse_flag:
            logger.error("the npu_info_after.txt file is missing.")
            raise FileNotExistError("the npu_info_after.txt file is missing.")

        tmp_event_list_before.sort(key=lambda x: int(x.get("npu_id")), reverse=False)
        tmp_event_list_after.sort(key=lambda x: int(x.get("npu_id")), reverse=False)
        for err_before, err_after in zip(tmp_event_list_before, tmp_event_list_after):
            event_dict = dict()
            event_dict["time"] = file_time
            event_dict["npu_id"] = err_after["npu_id"]
            event_dict["key_info"] = err_after["key_info"]
            if int(err_before["rx_err_num"]) < int(err_after["rx_err_num"]):  # add the NpuRxErrIncreased event
                event_dict["event_type"] = "NpuRxErrIncreased"
                event_dict["rx_err_num"] = err_after["rx_err_num"]
                desc.setdefault("events", []).append(event_dict)
            if int(err_before["tx_err_num"]) < int(err_after["tx_err_num"]):  # add the NpuTxErrIncreased event
                event_dict["event_type"] = "NpuTxErrIncreased"
                event_dict["tx_err_num"] = err_after["tx_err_num"]
                desc.setdefault("events", []).append(event_dict)

        if "events" in desc and len(desc.get("events", [])) > 0:
            desc["parse_next"] = True
            return desc
        return {"parse_next": True}
