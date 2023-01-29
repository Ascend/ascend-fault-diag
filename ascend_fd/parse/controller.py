# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
import os
import re
import multiprocessing

from ascend_fd import regular_rule
from ascend_fd.status import BaseError, InfoNotFoundError
from ascend_fd.log import init_main_logger, LOG_WIDTH
from ascend_fd.parse.parser import RcParser, KgParser


class ParseController:
    PARSE_CATEGORY = ["Rc"]
    OUT_DIR = "fault_diag_data"

    def __init__(self, args):
        self.cfg = self.init_config(args.input_path)
        self.input_path = args.input_path
        self.output_path = self.generate_output_path(args.output_path)
        self.logger = init_main_logger(self.output_path)
        self.parsers = self.generate_parser()

    @staticmethod
    def init_config(input_path):
        plog_path = list()
        npu_info_path = list()
        worker_id = ""
        for root, _, files in os.walk(input_path):
            for file in files:
                file_path = os.path.join(root, file)
                if re.match(regular_rule.PLOG_ORIGIN_RE, file) and "plog" in root:
                    plog_path.append(file_path)
                    continue
                if re.match(regular_rule.NPU_INFO_RE, file) and \
                        re.match(regular_rule.WORKER_DIR_RE, os.path.basename(root)) \
                        and os.path.basename(os.path.dirname(root)) == "environment_check":
                    npu_info_path.append(file_path)
                    continue

                worker_re = re.match(regular_rule.MODEL_ARTS_WORKER_RE, file)
                if worker_re:
                    worker_id = worker_re[1]

        return {
            "plog_path": plog_path,
            "npu_info_path": npu_info_path,
            "worker_id": worker_id
        }

    def start_job(self):
        """
        start the parse log job
        """
        self.logger.info("Start the log-parse job.".center(LOG_WIDTH, "-"))
        pool = multiprocessing.Pool(len(self.PARSE_CATEGORY))
        for name in self.PARSE_CATEGORY:
            pool.apply_async(self.parsers.get(name).parse, callback=self.log_callback)
        pool.close()

        # The knowledge graph uses multiprocess parsing. Therefore, only the main process can be used to
        # start the knowledge graph parse task. The child process cannot be started new child process.
        self.log_callback(self.parsers.get("Kg").parse())

        pool.join()
        self.logger.info("The log-parse job is complete.".center(LOG_WIDTH, "-"))

    def log_callback(self, result):
        """
        log callback func
        """
        err, job_name = result
        if isinstance(err, BaseError):
            self.logger.error(f"{job_name} parse job failed. {err}")
            return
        self.logger.info(f"{job_name} parse job succeeded.")

    def generate_parser(self):
        """
        generate parsers
        """
        parsers = dict()
        parsers["Rc"] = RcParser(self.input_path, self.output_path, self.cfg)
        parsers["Kg"] = KgParser(self.input_path, self.output_path, self.cfg)
        return parsers

    def generate_output_path(self, output_path):
        """
        generate the output_path.
        final output path: <pararm_output_path>/fault_diag_data/worker-{id}/
        """
        worker_id = self.cfg.get("worker_id", None)
        if not worker_id:
            raise InfoNotFoundError("cannot find worker id, please check whether the input path is correct.")
        output_path = os.path.join(output_path, self.OUT_DIR, f"worker-{worker_id}")
        os.makedirs(output_path, 0o700, exist_ok=True)
        return output_path
