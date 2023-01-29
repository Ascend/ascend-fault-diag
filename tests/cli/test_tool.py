# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
import os
import shutil
import unittest
from ascend_fd import tool

from ascend_fd.status import FileNotExistError

TEST_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
DT_DIR = os.path.join(TEST_DIR, "dt_dir")


class PathCheckTestCase(unittest.TestCase):
    
    def setUp(self) -> None:
        self.input_path = os.path.join(DT_DIR, "path_check_in")
        self.output_path = os.path.join(DT_DIR, "path_check_out")
        if os.path.exists(self.input_path):
            shutil.rmtree(self.input_path)
        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path)

    def test_check_pass(self):
        if not os.path.exists(self.input_path):
            os.makedirs(self.input_path)
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
        self.assertEqual((os.path.realpath(self.input_path), os.path.realpath(self.output_path)), tool.path_check(
            self.input_path, self.output_path))

    def test_check_error_one(self):
        if os.path.exists(self.input_path):
            shutil.rmtree(self.input_path)
        self.assertRaisesRegex(FileNotExistError, "The input path does not exist.",
                               tool.path_check, self.input_path, self.output_path)

    def test_check_error_two(self):
        if not os.path.exists(self.input_path):
            os.makedirs(self.input_path)
        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path)
        self.assertRaisesRegex(FileNotExistError, "The output path does not exist.",
                               tool.path_check, self.input_path, self.output_path)

    def tearDown(self) -> None:
        if os.path.exists(self.input_path):
            shutil.rmtree(self.input_path)
        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path)
