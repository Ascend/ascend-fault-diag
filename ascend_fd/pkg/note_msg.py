# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. ALL rights reserved.
from dataclasses import dataclass


@dataclass
class NoteMsg:
    Note_zh: str
    Note_en: str


@dataclass
class FormatNoteMsg(NoteMsg):
    def format(self, format_info):
        return NoteMsg(self.Note_zh.format(format_info), self.Note_en.format(format_info))


MULTI_RANK_NOTE_MSG = NoteMsg("首节点分析检测出了多个的疑似错误首节点，将优先排查这几个节点。",
                              "The root cluster analysis detected multiple suspected error root clusters, "
                              "and these clusters will be given priority.")

MAX_RANK_NOTE_MSG = NoteMsg("首节点分析检测出了超过5个的疑似错误首节点，将优先排查前五个节点。",
                            "The root cluster analysis detects more than 5 suspected error root clusters, "
                            "and will give priority to checking the first five.")

LOST_LOG_NOTE_MSG = FormatNoteMsg("以下Rank ID{}没有日志记录。诊断结果可能会受到影响从而不准确。",
                                  "The following rank IDs {} do not have log records. "
                                  "Diagnostic results may be affected and inaccurate.")

MULTI_KG_ROOT_CAUSE_MSG = NoteMsg("故障知识图谱检测出多个故障根因，请依次进行排查。",
                                  "The knowledge graph detects multiple root causes of faults, "
                                  "please troubleshoot them in turn.")
