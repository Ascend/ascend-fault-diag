# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
from ascend_fd.log import init_job_logger
from ascend_fd.status import BaseError, SuccessRet, InnerError
from ascend_fd.pkg import (start_rc_parse_job, start_kg_parse_job,
                           start_rc_diag_job, start_kg_diag_job)


class BaseWorker:
    """
    This is a Base class for job worker.
    """
    JOB_NAME = "base_worker"
    err_result = {}

    def __init__(self, input_path, output_path, cfg):
        self.input = input_path,
        self.output = output_path
        self.cfg = cfg
        self.log = init_job_logger(output_path, self.JOB_NAME)

    def _job(self):
        """
        Use to implement specific task actions.
        :return: job result
        """
        return self.err_result

    def work(self):
        """
        Use try except to catch subprocess errors during job, then return success or failure result and error info.
        :return: err or success, job name, job result
        """
        self.log.info(f"The {self.JOB_NAME} start.")
        try:
            result = self._job()
        except BaseError as err:
            return err, self.JOB_NAME, self.err_result
        except Exception as err:
            self.log.error("An inner error occurred: %s.", err)
            return InnerError(), self.JOB_NAME, self.err_result
        else:
            self.log.info(f"{self.JOB_NAME} succeeded.")
            return SuccessRet(), self.JOB_NAME, result
        finally:
            self.log.info(f"The {self.JOB_NAME} is complete.")


class RcParser(BaseWorker):
    """
    This class is used to perform RC parse job.
    """
    JOB_NAME = "rc_parse"

    def _job(self):
        start_rc_parse_job(self.output, self.cfg)
        return


class KgParser(BaseWorker):
    """
    This class is used to perform KG parse job.
    """
    JOB_NAME = "kg_parse"

    def _job(self):
        start_kg_parse_job(self.output, self.cfg)
        return


class KgDiagnoser(BaseWorker):
    """
    This class is used to perform KG diag job.
    """
    JOB_NAME = "kg_diag"
    err_result = {
        "Ascend-Rc-Worker-Rank-Analyze Result": {
            "analyze_success": False,
            "engine_ver": "v1.0.0"
        },
        "Ascend-Knowledge-Graph-Rank-Analyze Result": {
            "analyze_success": False,
            "engine_ver": "v1.0.0"
        }
    }

    def _job(self):
        """
        The KG diag job contains two subtasks.
        1. RC diag job: it returns the job result and err worker list.
        2. KG diag job: it will check each worker in the err worker list, and return the diag result.
        :return: the combined results of RC diag job and KG diag job
        """
        result, worker_list = start_rc_diag_job(self.output, self.cfg)
        self.err_result.update(result)

        if not worker_list:
            self.log.warning("the root cause node is not found, so the knowledge graph diag task is not started.")
            raise InnerError("the root cause node is not found, so the knowledge graph diag task is not started.")

        kg_result = start_kg_diag_job(self.output, worker_list, self.cfg)
        result.update(kg_result)
        return result
