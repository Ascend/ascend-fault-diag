# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
import os
import re
import heapq
import json
import multiprocessing
from dataclasses import dataclass

from ascend_fd.tool import safe_open
from ascend_fd import regular_rule
from ascend_fd.status import BaseError, PathError
from ascend_fd.log import init_main_logger, LOG_WIDTH
from ascend_fd.controller.job_worker import RcParser, KgParser, KgDiagnoser


@dataclass
class PCFG:
    plog_path: dict
    npu_info_path: list
    worker_id: str


@dataclass
class DCFG:
    mode: int
    parse_data: dict


class ParseController:
    """
    The parse job controller.
    """
    PARSE_CATEGORY = ["Rc"]
    OUT_DIR = "fault_diag_data"

    def __init__(self, args):
        self.cfg = self.init_cfg(args.input_path)
        self.input_path = args.input_path
        self.output_path = self.generate_output_path(args.output_path)
        self.logger = init_main_logger(self.output_path)
        self.parsers = self.generate_parser()

    @staticmethod
    def init_cfg(input_path):
        """
        init parse config. The config dict contains three parts:
        plog_path: {PID: [[], []]}, (each PID corresponds to two lists of plogs--debug folder and run folder)
        npu_info_path: [],
        worker_id: "",
        :param input_path: the origin log data path
        :return: parse config dict
        """
        plog_path = dict()
        npu_info_path = list()
        worker_id = "0"
        for root, _, files in os.walk(input_path):
            for file in files:
                file_path = os.path.join(root, file)
                if re.match(regular_rule.PLOG_ORIGIN_RE, file) and os.path.basename(root) == "plog":
                    pid = re.match(regular_rule.PLOG_ORIGIN_RE, file)[1]
                    if os.path.basename(os.path.dirname(root)) == "debug":
                        heapq.heappush(plog_path.setdefault(pid, [[], []])[0], file_path)
                    elif os.path.basename(os.path.dirname(root)) == "run":
                        heapq.heappush(plog_path.setdefault(pid, [[], []])[1], file_path)
                    continue

                if re.match(regular_rule.NPU_INFO_RE, file) and \
                        re.match(regular_rule.WORKER_DIR_RE, os.path.basename(root)) \
                        and os.path.basename(os.path.dirname(root)) == "environment_check":
                    npu_info_path.append(file_path)
                    continue

                worker_re = re.match(regular_rule.MODEL_ARTS_WORKER_RE, file)
                if worker_re:
                    worker_id = worker_re[1]

        return PCFG(plog_path, npu_info_path, worker_id)

    def start_job(self):
        """
        use multiprocessing to start parse tasks.
        Now the component contains two parse tasks:
        1. RC parse job; 2. KG parse job.
        """
        self.logger.info("Start the log-parse job.".center(LOG_WIDTH, "-"))
        pool = multiprocessing.Pool(len(self.PARSE_CATEGORY))
        for name in self.PARSE_CATEGORY:
            pool.apply_async(self.parsers.get(name).work, callback=self.log_callback)
        pool.close()

        # The knowledge graph uses multiprocess parsing. But the child process cannot be started new child process.
        # So only the main process can be used to start the knowledge graph parse task.
        self.log_callback(self.parsers.get("Kg").work())

        pool.join()
        self.logger.info("The log-parse job is complete.".center(LOG_WIDTH, "-"))

    def log_callback(self, result):
        """
        receive the execution results of child processes and print logs.
        :param result: the result of subprocess
        """
        err, job_name, _ = result
        if isinstance(err, BaseError):
            self.logger.error(f"{job_name} parse job failed. {err}")
            return
        self.logger.info(f"{job_name} parse job succeeded.")

    def generate_parser(self):
        """
        generate two parsers.
        :return: parser dict
        """
        parsers = dict()
        parsers["Rc"] = RcParser(self.input_path, self.output_path, self.cfg)
        parsers["Kg"] = KgParser(self.input_path, self.output_path, self.cfg)
        return parsers

    def generate_output_path(self, output_path):
        """
        generate the output_path.
        The parse job have a format output path:<pararm_output_path>/fault_diag_data/worker-{id}/
        :param output_path: the specified output path
        :return: the final output dir path
        """
        worker_id = self.cfg.worker_id
        output_path = os.path.join(output_path, self.OUT_DIR)
        if os.listdir(output_path):
            raise PathError("the output path already has a fault_diag_data folder that is not empty.")

        output_path = os.path.join(output_path, f"worker-{worker_id}")
        os.makedirs(output_path, 0o700, exist_ok=True)
        return output_path


class DiagController:
    """
    The diag job controller.
    """
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
        """
        init diag config. The config contains two parts:
        mode: "0/1",
        parse_data:
            {worker_id:
                {
                plog_parser_path: [],
                kg_parse_path: "",
                },
            },
        :param input_path: the parsed log data path
        :param mode: scene mode
        :return: diag config dict
        """
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
                if re.match(regular_rule.PLOG_PARSE_RE, file):
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

        return DCFG(mode, parse_data)

    def start_job(self):
        """
        use multiprocessing to start diag tasks.
        Now the component contains one diag task:
        1. KG parse job.
        """
        self.logger.info("Start the falt-diag job.".center(LOG_WIDTH, "-"))
        pool = multiprocessing.Pool(len(self.diag_task))
        for name in self.diag_task:
            pool.apply_async(self.diagnosers.get(name).work, callback=self.log_callback)
        pool.close()
        pool.join()
        self.logger.info("The falt-diag job is complete.".center(LOG_WIDTH, "-"))

        self.export_results()

    def export_results(self):
        """
        sort the diagnostic results and save results to output path.
        If print parameter is true, func will print the results.
        """
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
        """
        receive the execution results of child processes and print logs.
        :param result: the result of subprocess
        """
        err, job_name, result_json = result
        if isinstance(err, BaseError):
            self.logger.error(f"{job_name} diag job failed. {err}")
        else:
            self.logger.info(f"{job_name} diag job succeeded.")
        self.diag_results.update(result_json)

    def generate_diagnoser(self):
        """
        generate one diagnoser.
        :return: parser dict
        """
        diagnoser = dict()
        diagnoser["Kg"] = KgDiagnoser(self.input_path, self.output_path, self.cfg)
        return diagnoser
