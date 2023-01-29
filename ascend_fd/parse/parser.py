# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
from ascend_fd.log import init_job_logger
from ascend_fd.status import BaseError, SuccessRet, InnerError
from ascend_fd.pkg import start_rc_parse_job, start_kg_parse_job


class BaseParser:
    JOB_NAME = "base_parse"

    def __init__(self, input_path, output_path, cfg):
        self.input = input_path,
        self.output = output_path
        self.cfg = cfg
        self.log = init_job_logger(output_path, self.JOB_NAME)

    def start_job(self):
        pass

    def parse(self):
        """
        use try except to catch errors during parsing to return success or failure of parsing.
        """
        self.log.info(f"The {self.JOB_NAME} start.")
        try:
            self.start_job()
        except BaseError as err:
            return err, self.JOB_NAME
        except Exception as err:
            self.log.error("An inner error occurred: %s.", err)
            return InnerError(), self.JOB_NAME
        else:
            self.log.info(f"{self.JOB_NAME} succeeded.")
            return SuccessRet(), self.JOB_NAME
        finally:
            self.log.info(f"The {self.JOB_NAME} is complete.")


class RcParser(BaseParser):
    JOB_NAME = "rc_parse"

    def start_job(self):
        start_rc_parse_job(self.output, self.cfg)


class KgParser(BaseParser):
    JOB_NAME = "kg_parse"

    def start_job(self):
        start_kg_parse_job(self.output, self.cfg)
