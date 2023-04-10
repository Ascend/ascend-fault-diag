# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. ALL rights reserved.
import json
import logging
from dataclasses import asdict

from prettytable import PrettyTable

from ascend_fd.tool import get_version
from ascend_fd.pkg import experience as exp
from ascend_fd.pkg.note_msg import NoteMsg


logger = logging.getLogger("ascend_fd")


class TableWrapper:
    SEP = "+--------+"

    def __init__(self, result):
        self.version_info = get_version()
        self.result = result
        self.table = PrettyTable()

        self.table.title = "Ascend Fault-Diag Report"
        self.table.field_names = ["版本信息", self.version_info, ""]
        self.table.align[""] = "l"
        self.add_result_rows()

    @staticmethod
    def parse_error_code(error_code):
        rows = []
        if not hasattr(exp, f"E{error_code}"):
            logger.error("Can not parse the error code(%s)", error_code)
            return rows
        key_value = {"code": "状态码", "cause_zh": "错误类型", "description_zh": "错误描述",
                     "suggestion_zh": "建议方案", "reference_url": "参考链接"}
        exp_err = getattr(exp, f"E{error_code}")()
        for key, value in key_value.items():
            if not getattr(exp_err, key):
                continue
            this_row = ["", value, getattr(exp_err, key)]
            rows.append(this_row)
        return rows

    @staticmethod
    def parse_note_msgs(note_msgs):
        if isinstance(note_msgs, NoteMsg):
            note_msgs = [note_msgs]
        note = ""
        for ind, msg in enumerate(note_msgs):
            note += f"{ind + 1}. {msg.Note_zh}\n"
        return note.rstrip()

    def add_result_rows(self):
        rc_result = self.result.get("Rc")
        if rc_result:
            self.add_rc_rows(rc_result)
        kg_result = self.result.get("Kg")
        if kg_result:
            self.add_kg_rows(kg_result)

    def get_format_table(self):
        return f'\n{self.table.get_string()}'

    def add_rc_rows(self, result):
        self.table.add_row(["首节点分析", "类型", "描述"], divider=True)
        rc_rows = []
        analyze_success = result.get("analyze_success", False)
        if not analyze_success:
            rc_rows.append(["", "分析失败", "请查看日志报错信息"])
            self.add_paragraph(rc_rows)
            return
        root_ranks = result.get("root_cause_rank")
        if root_ranks:
            rc_rows.append(["", "根因节点", root_ranks])
        root_workers = result.get("root_cause_worker")
        if root_workers:
            rc_rows.append(["", "根因设备", [f"Worker {worker[0]}->{worker[1]}" for worker in root_workers]])
        error_code = result.get("error_code")
        if error_code:
            rc_rows.extend(self.parse_error_code(error_code))
        note_msgs = result.get("note_msgs")
        if note_msgs:
            rc_rows.append(["", "说明", self.parse_note_msgs(note_msgs)])
        self.add_paragraph(rc_rows)

    def add_kg_rows(self, result):
        self.table.add_row(["知识图谱分析", "类型", "描述"], divider=True)
        analyze_success = result.get("analyze_success", False)
        if not analyze_success:
            kg_rows = [["", "分析失败", "请查看日志报错信息"]]
            self.add_paragraph(kg_rows)
            return
        for key, val in result.items():
            if key == "analyze_success":
                continue
            self.add_kg_worker_rows(key, val)

    def add_kg_worker_rows(self, worker_server_id, result):
        kg_rows = [["", "根因设备", f"Worker {worker_server_id[0]}->{worker_server_id[1]}"]]
        error_codes = result.get("error_code", [])
        sep_flag = True if len(error_codes) > 1 else False
        for error_code in error_codes:
            if sep_flag:
                kg_rows.append(["", self.SEP, ""])
            kg_rows.extend(self.parse_error_code(error_code))

        note_msgs = result.get("note_msgs", [])
        if note_msgs:
            if sep_flag:
                kg_rows.append(["", self.SEP, ""])
            kg_rows.append(["", "说明", self.parse_note_msgs(note_msgs)])
        self.add_paragraph(kg_rows)

    def add_paragraph(self, rows):
        if not rows:
            return
        pre_rows = rows[:-1]
        if pre_rows:
            self.table.add_rows(pre_rows)
        self.table.add_row(rows[-1], divider=True)


class JsonWrapper:
    def __init__(self, result):
        self.result = result
        self.json = dict()
        self.format_json()

    @staticmethod
    def parse_error_code(error_code):
        if not hasattr(exp, f"E{error_code}"):
            logger.error("Can not parse the error code(%s)", error_code)
            return dict()
        exp_err = getattr(exp, f"E{error_code}")()
        return asdict(exp_err)

    @staticmethod
    def parse_note_msgs(note_msgs):
        if isinstance(note_msgs, NoteMsg):
            note_msgs = [note_msgs]
        note_zh, note_en = "", ""
        for ind, msg in enumerate(note_msgs):
            note_zh += f"{ind + 1}. {msg.Note_zh}\n"
            note_en += f"{ind + 1}. {msg.Note_en}\n"
        return {"Note_zh": note_zh.rstrip(), "Note_en": note_en.rstrip()}

    def format_json(self):
        rc_result = self.result.get("Rc")
        if rc_result:
            self.json.update({"Ascend-RC-Worker-Rank-Analyze Result": self.format_rc_result(rc_result)})
        kg_result = self.result.get("Kg")
        if kg_result:
            self.json.update({"Ascend-Knowledge-Graph-Fault-Diag Result": self.format_kg_result(kg_result)})

    def get_format_json(self):
        return json.dumps(self.json, ensure_ascii=False, indent=4)

    def format_rc_result(self, result):
        rc_result = dict()
        for key, value in result.items():
            if key == "error_code":
                rc_result.update(self.parse_error_code(value))
                continue
            if key == "note_msgs":
                rc_result.update(self.parse_note_msgs(value))
                continue
            if key == "root_cause_worker":
                rc_result.update({key: [f"Worker {worker[0]}->{worker[1]}" for worker in value]})
                continue
            rc_result.update({key: value})
        return rc_result

    def format_kg_result(self, result):
        kg_result = dict()
        for key, value in result.items():
            if key == "analyze_success":
                kg_result.update({key: value})
                continue
            kg_result.update({f"Worker {key[0]}->{key[1]}": self.format_kg_worker_result(value)})
        return kg_result

    def format_kg_worker_result(self, result):
        worker_result = dict()
        for key, value in result.items():
            if key == "error_code":
                for single_code in value:
                    worker_result.update({single_code: self.parse_error_code(single_code)})
                continue
            if key == "note_msgs":
                worker_result.update(self.parse_note_msgs(value))
                continue
            worker_result.update({key: value})
        return worker_result
