# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
import os
import shutil
import unittest
import pytest

from ascend_fd.pkg.rc_parse import start_rc_parse_job

from ascend_fd.status import FileNotExitsError

TEST_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
DT_DIR = os.path.join(TEST_DIR, "dt_dir")


class RCParseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = os.path.join(DT_DIR, "rc_dir")
        self.plog_file = os.path.join(self.temp_dir, "plog", "plog-12345_67890.log")
        self.cfg = {
            "plog_path": [self.plog_file]
        }
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def test_empty_input_path(self):
        with pytest.raises(FileNotExitsError, match="no plog file that meets the path specifications is found."):
            start_rc_parse_job(self.temp_dir, self.temp_dir, self.cfg)

    def test_plog_file(self):
        plog_dir = os.path.join(self.temp_dir, "plog")
        if not os.path.exists(plog_dir):
            os.makedirs(plog_dir)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        with os.fdopen(os.open('testfile.txt', flags, 0o600), 'w') as test:
            test.write('test!')
        start_rc_parse_job(self.temp_dir, self.temp_dir, self.cfg)
        shutil.rmtree(plog_dir)

    def tearDown(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
