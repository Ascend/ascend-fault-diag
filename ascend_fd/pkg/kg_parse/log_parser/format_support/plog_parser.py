#!/user/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import math
from multiprocessing import Pool

from ascend_fd.status import FileNotExistError
from ascend_fd.tool import safe_open
from ascend_fd.pkg.kg_parse.log_parser.format_support.bmc_log_file_parser import BMCLogFileParser
from ascend_fd.pkg.kg_parse.utils.log_record import logger

# 文件行数大于LINE_NUM则开启多进程解析
LINE_NUM = 50000
MAX_PROCESS_NUM = 10


class LineParser:
    """每一行的解析器"""
    def __init__(self, name, regex, file_filter=None,
                 parm_regex=None, parm_dict_func=None,
                 parm_regex1=None, parm_dict_func1=None,
                 keywords=None):
        self.name = name
        self.regex = regex
        self.file_filter = file_filter
        self.parm_regex = parm_regex
        self.parm_dict_func = parm_dict_func
        self.parm_regex1 = parm_regex1
        self.parm_dict_func1 = parm_dict_func1
        self.keywords = keywords

    def parse(self, desc, file_path):
        """解析方法"""
        event_dict = dict()
        if self.file_filter is not None and self.file_filter not in file_path:
            return event_dict
        ret = self.regex.findall(desc)
        if ret:
            time = desc[desc.index(":") + 1:]
            time = time[0:time.index(".")]
            delete_char_index = time.rindex("-")
            time = time[0:delete_char_index] + " " + time[delete_char_index + 1:]

            event_dict["key_info"] = desc
            event_dict["time"] = time

            event_dict["event_type"] = self.name
            if self.parm_regex is not None:
                ret = self.parm_regex.findall(file_path)
                if ret:
                    params = self.parm_dict_func(ret)
                    event_dict["params"] = params
            if self.parm_regex1 is not None:
                ret = self.parm_regex1.findall(desc)
                if ret:
                    params = self.parm_dict_func1(ret)
                    event_dict["params1"] = params
        return event_dict

    def file_check(self, file_path):
        if self.parm_regex is None:
            return True
        ret = self.parm_regex.findall(file_path)
        if ret:
            return True
        return False

    def get_keywords(self):
        return self.keywords


class PlogParser(BMCLogFileParser):
    """根据提供的正则表达式对文件每行数据进行解析及数据提取"""
    """parm_regex， parm_dict_func 以文件路径作为输入获取device id；parm_regex1，parm_dict_func1以文本中参数匹配获取module"""
    LINE_PARSERS = [
        LineParser(name="RuntimeTaskException",
                   regex=re.compile(
                       r".*?(ReportExceptProc:task exception).*?"),
                   file_filter="plog",
                   parm_regex1=re.compile(r"(RUNTIME)"),
                   parm_dict_func1=lambda p: {"module": p.replace(" ", "")},
                   keywords=["ReportExceptProc:task exception"],
                   ),
        LineParser(name="RuntimeAicoreError",
                   regex=re.compile(
                       r".*?(device\(\d+\)).*?(aicore error).*?(error code = 0x800000).*?"),
                   file_filter="plog",
                   parm_regex1=re.compile(r"(RUNTIME)"),
                   parm_dict_func1=lambda p: {"module": p.replace(" ", "")},
                   keywords=["device", "aicore error", "error code = 0x800000"],
                   ),
        LineParser(name="RuntimeModelExecuteTaskFailed",
                   regex=re.compile(
                       r".*?(model execute task failed, device_id=\d+).*?"),
                   file_filter="plog",
                   parm_regex1=re.compile(r"(RUNTIME)"),
                   parm_dict_func1=lambda p: {"module": p.replace(" ", "")},
                   keywords=["model execute task failed, device_id="],
                   ),
        LineParser(name="RuntimeAicoreKernelExecuteFailed",
                   regex=re.compile(
                       r".*?(aicore kernel execute failed, device_id=\d+).*?"),
                   file_filter="plog",
                   parm_regex1=re.compile(r"(RUNTIME)"),
                   parm_dict_func1=lambda p: {"module": p.replace(" ", "")},
                   keywords=["aicore kernel execute failed, device_id="],
                   ),
        LineParser(name="RuntimeStreamSyncFailed",
                   regex=re.compile(
                       r".*?(Stream Synchronize failed).*?"),
                   file_filter="plog",
                   parm_regex1=re.compile(r"(RUNTIME)"),
                   parm_dict_func1=lambda p: {"module": p.replace(" ", "")},
                   keywords=["Stream Synchronize failed"],
                   ),
        LineParser(name="GEModelStreamSyncFailed",
                   regex=re.compile(
                       r".*?(Model stream sync failed).*?"),
                   file_filter="plog",
                   parm_regex1=re.compile(r"(GE)"),
                   parm_dict_func1=lambda p: {"module": p.replace(" ", "")},
                   keywords=["Model stream sync failed"],
                   ),
        LineParser(name="GERunModelFail",
                   regex=re.compile(
                       r".*?(Run model fail).*?"),
                   file_filter="plog",
                   parm_regex1=re.compile(r"(GE)"),
                   parm_dict_func1=lambda p: {"module": p.replace(" ", "")},
                   keywords=["Run model fail"],
                   ),
        LineParser(name="FailedToApplyForResources",
                   regex=re.compile(
                       r".*?halResourceIdAlloc.*?failed.*?"),
                   file_filter="plog",
                   keywords=["halResourceIdAlloc", "failed"],
                   ),
        LineParser(name="RegisteredResourcesExceedsTheMaximum",
                   regex=re.compile(
                       r".*?Program register failed.*?"),
                   file_filter="plog",
                   keywords=["Program register failed"],
                   ),
        LineParser(name="FailedToexecuteTheAICoreOperator",
                   regex=re.compile(
                       r".*?PrintErrorInfo.*?fault kernel_name.*?func_name.*?"),
                   file_filter="plog",
                   keywords=["PrintErrorInfo", "fault kernel_name", "func_name"],
                   ),
        LineParser(name="ExecuteModelFailed",
                   regex=re.compile(
                       r".*?ModelExecute.*?Execute model failed.*?"),
                   file_filter="plog",
                   keywords=["ModelExecute", "Execute model failed"],
                   ),
        LineParser(name="FailedToexecuteTheAICpuOperator",
                   regex=re.compile(
                       r".*?PrintAicpuErrorInfo.*?"),
                   file_filter="plog",
                   keywords=["PrintAicpuErrorInfo"],
                   ),
        LineParser(name="MemoryAsyncCopyFailed",
                   regex=re.compile(
                       r".*?Memory async copy failed.*?"),
                   file_filter="plog",
                   keywords=["Memory async copy failed"],
                   ),
        LineParser(name="NotifyWaitExecuteFailed",
                   regex=re.compile(
                       r".*?Notify wait execute failed.*?"),
                   file_filter="plog",
                   keywords=["Notify wait execute failed"],
                   ),
        LineParser(name="TaskRunFailed",
                   regex=re.compile(
                       r".*?Task run failed.*?Notify Wait.*?"),
                   file_filter="plog",
                   keywords=["Task run failed", "Notify Wait"],
                   ),
    ]

    VALID_PARAMS = {}
    TARGET_FILE_PATTERNS = ["plog_path"]

    def __init__(self):
        super().__init__()

    def parse(self, file_path: str):
        desc = dict()
        if not os.path.isfile(file_path):
            logger.error(f"file {os.path.basename(file_path)} not exists.")
            raise FileNotExistError(f"file {os.path.basename(file_path)} not exists.")
        logger.info("start parse %s", file_path)
        with safe_open(file_path, mode='r', encoding='utf-8') as _log:
            lines = _log.readlines()
            results = list()
            if len(lines) <= LINE_NUM:
                pool = Pool(1)
                results.append(pool.apply_async(self.handle_parse, args=(lines, file_path)))
                pool.close()
            else:
                if LINE_NUM != 0:
                    process_num = math.ceil(len(lines) / LINE_NUM)
                else:
                    process_num = MAX_PROCESS_NUM
                logger.info("len(lines): %d", len(lines))
                logger.info("process_num: %d", process_num)
                pool = Pool(min(process_num, MAX_PROCESS_NUM))
                for i in range(0, process_num):
                    start_index = i * LINE_NUM
                    end_index = min(start_index + LINE_NUM, len(lines))
                    logger.info("start index: %d, end index: %d", start_index, end_index)
                    results.append(pool.apply_async(self.handle_parse, args=(lines[start_index:end_index], file_path)))
                pool.close()
            for result in results:
                rst = result.get()
                if rst:
                    desc.setdefault("events", []).extend(rst)
        logger.info("end parse %s", file_path)

        if "events" in desc and len(desc.get("events", [])) > 0:
            desc["parse_next"] = True
            return desc
        return {"parse_next": True}

    def handle_parse(self, lines, file_path):
        parser_results = []
        matched = [0 for _ in range(len(lines))]
        for line_parser in self.LINE_PARSERS:
            if not line_parser.file_check(file_path):
                continue
            keywords = line_parser.get_keywords()
            for index, line in enumerate(lines):
                if matched[index] == 1:
                    continue
                line = line.strip()
                """ts.txt可能存在\00字符，导致循环无法退出"""
                line = line.replace('\00', '')

                keyword_num = 0
                for keyword in keywords:
                    if keyword not in line:
                        break
                    keyword_num += 1
                if keyword_num != len(keywords):
                    continue

                event_dict = line_parser.parse(line, file_path)
                if event_dict:
                    matched[index] = 1
                    parser_results.append(event_dict)
        return parser_results
