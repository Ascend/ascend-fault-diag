# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
import os
import re
import multiprocessing

from ascend_fd import config
from ascend_fd.status import BaseError, InfoNotFoundError
from ascend_fd.log import init_main_logger, LOG_WIDTH
from ascend_fd.parse.parser import RcParser, KgParser, NodeParser, NetParser


class ParseController:
    PARSE_CATEGORY = ["Rc", "Node", "Net"]
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
        npu_smi_path = list()
        npu_info_path = list()
        npu_detail_path = list()
        delay_path = list()
        worker_id = ""
        for root, _, files in os.walk(input_path):
            for file in files:
                file_path = os.path.join(root, file)
                if re.match(config.PLOG_ORIGIN_RE, file) and "plog" in root:
                    plog_path.append(file_path)
                    continue
                if re.match(config.NPU_SMI_RE, file) and re.match(config.WORKER_DIR_RE, os.path.basename(root)):
                    npu_smi_path.append(file_path)
                    continue
                if re.match(config.NPU_DETAILS_RE, file) and re.match(config.WORKER_DIR_RE, os.path.basename(root)):
                    npu_detail_path.append(file_path)
                    continue
                if re.match(config.NPU_INFO_RE, file) and re.match(config.WORKER_DIR_RE, os.path.basename(root)) \
                        and os.path.basename(os.path.dirname(root)) == "environment_check":
                    npu_info_path.append(file_path)
                    continue
                if re.match(config.MODEL_ARTS_RANK_RE, file):
                    delay_path.append(file_path)
                    continue

                worker_re = re.match(config.MODEL_ARTS_WORKER_RE, file)
                if worker_re:
                    worker_id = worker_re[1]

        return {
            "plog_path": plog_path,
            "npu_smi_path": npu_smi_path,
            "npu_info_path": npu_info_path,
            "npu_detail_path": npu_detail_path,
            "delay_path": delay_path,
            "worker_id": worker_id
        }

    def start_job(self):
        """
        start the parse log job
        """
        self.logger.info("Start the log-parse job.".center(LOG_WIDTH, "-"))
        pool = multiprocessing.Pool(3)
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
        generate 4 parsers
        """
        parsers = dict()
        parsers["Rc"] = RcParser(self.input_path, self.output_path, self.cfg)
        parsers["Kg"] = KgParser(self.input_path, self.output_path, self.cfg)
        parsers["Node"] = NodeParser(self.input_path, self.output_path, self.cfg)
        parsers["Net"] = NetParser(self.input_path, self.output_path, self.cfg)
        return parsers

    def generate_output_path(self, output_path):
        """
        generate the output_path.
        final output path: <pararm_output_path>/fault_diag_data/worker-{id}/
        """
        worker_id = self.cfg.get("worker_id", None)
        if not worker_id:
            self.logger.error()
            raise InfoNotFoundError("cannot find worker id, please check whether the input path is correct.")
        output_path = os.path.join(output_path, self.OUT_DIR, f"worker-{worker_id}")
        os.makedirs(output_path, 0o700, exist_ok=True)
        return output_path
