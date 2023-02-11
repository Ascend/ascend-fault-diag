# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. All rights reserved.
import json
import os
import shutil
import unittest

from ascend_fd.controller import router

TEST_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class ParseSTArgs:
    cmd = "parse"

    def __init__(self, input_dir, output_dir):
        self.input_path = input_dir
        self.output_path = output_dir


class DiagSTArgs:
    cmd = "diag"

    def __init__(self, input_dir, output_dir, mode=0, p=True):
        self.input_path = input_dir
        self.output_path = output_dir
        self.mode = mode
        self.print = p


class STTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.parse_input = os.path.join(TEST_DIR, "st_testcase")
        self.output = os.path.join(TEST_DIR, "st_output")
        self.diag_input = os.path.join(self.output, "fault_diag_data")

        if not os.path.exists(self.output):
            os.makedirs(self.output)
        self.parse_args = ParseSTArgs(self.parse_input, self.output)
        self.diag_args = ParseSTArgs(self.diag_input, self.output)

    def test_parse(self):
        router(self.parse_args)

    def test_diag(self):
        router(self.diag_args)
        fault_diag_data_dir = os.path.join(self.output, "fault_diag_data", "worker-0")
        all_diag_report = os.path.join(fault_diag_data_dir, "all_diag_report.json")
        with open(all_diag_report, 'r') as file_stream:
            report = json.loads(file_stream.read())
            self.assertTrue(report["Ascend-Knowledge-Graph-Fault-Diag Result"]["worker-0"]["analyze_success"])
            self.assertTrue(report["Ascend-RC-Worker-Rank-Analyze Result"]["worker-0"]["analyze_success"])

    def tearDown(self) -> None:
        if os.path.exists(self.output):
            shutil.rmtree(self.output)


