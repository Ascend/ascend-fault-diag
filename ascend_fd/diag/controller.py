# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
import os
import re
import json
import multiprocessing

from ascend_fd.tool import safe_open
from ascend_fd.status import BaseError
from ascend_fd.log import init_main_logger, LOG_WIDTH
from ascend_fd.diag.diagnoser import KgDiagnoser
from ascend_fd.regular_rule import PLOG_PARSE_RE


class DiagController:
    TASK_CATEGORY = {
        1: "Kg",
    }
    OUT_DIR = "fault_diag_result"

    def __init__(self, args):
        self.cfg = self.init_cfg(args.input_path, args.mode)
        self.input_path = args.input_path
        self.output_path = os.path.join(args.output_path, self.OUT_DIR)
        os.makedirs(self.output_path, 0o700, exist_ok=True)
        self.is_print = args.print
        self.logger = init_main_logger(self.output_path)

        self.diag_task = ["Kg"]
        self.diagnosers = self.generate_diagnoser()
        self.diag_results = dict()

    @staticmethod
    def init_cfg(input_path, mode):
        parse_data = dict()
        worker_dirs = os.listdir(input_path)
        for worker_dir in worker_dirs:
            if not worker_dir.startswith("worker-"):
                continue
            plog_parser_path = list()
            kg_parse_path = ""

            worker_path = os.path.join(input_path, worker_dir)
            files = os.listdir(worker_path)
            for file in files:
                file_path = os.path.join(worker_path, file)
                if re.match(PLOG_PARSE_RE, file):
                    plog_parser_path.append(file_path)
                    continue
                if file == "ascend-kg-parser.json":
                    kg_parse_path = file_path
                    continue
            parse_data.update({
                worker_dir: {
                    "plog_parser_path": plog_parser_path,
                    "kg_parse_path": kg_parse_path
                }
            })

        return {
            "mode": mode,
            "parse_data": parse_data
        }

    def start_job(self):
        """
        start the falt-diag job
        """
        self.logger.info("Start the falt-diag job.".center(LOG_WIDTH, "-"))
        pool = multiprocessing.Pool(len(self.diag_task))
        for name in self.diag_task:
            pool.apply_async(self.diagnosers.get(name).diag, callback=self.log_callback)
        pool.close()
        pool.join()
        self.logger.info("The falt-diag job is complete.".center(LOG_WIDTH, "-"))

        self.export_results()

    def export_results(self):
        out_file = os.path.join(self.output_path, "all_diag_report.json")
        save_result = {
            "Ascend-RC-Worker-Rank-Analyze Result":
                self.diag_results.get("Ascend-RC-Worker-Rank-Analyze Result"),
            "Ascend-Knowledge-Graph-Fault-Diag Result":
                self.diag_results.get("Ascend-Knowledge-Graph-Fault-Diag Result")
        }

        with safe_open(out_file, "w+", encoding="utf-8") as file_stream:
            file_stream.write(json.dumps(save_result, ensure_ascii=False, indent=4))
        if self.is_print:
            self.logger.info(json.dumps(save_result, ensure_ascii=False, indent=4))

    def log_callback(self, result):
        err, job_name, result_json = result
        if isinstance(err, BaseError):
            self.logger.error(f"{job_name} diag job failed. {err}")
        else:
            self.logger.info(f"{job_name} diag job succeeded.")
        self.diag_results.update(result_json)

    def generate_diagnoser(self):
        """
        generate 3 diagnosers
        """
        diagnoser = dict()
        diagnoser["Kg"] = KgDiagnoser(self.input_path, self.output_path, self.cfg)
        return diagnoser
