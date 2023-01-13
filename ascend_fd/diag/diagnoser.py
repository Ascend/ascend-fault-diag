# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
from ascend_fd.log import init_job_logger
from ascend_fd.status import BaseError, InnerError, SuccessRet
from ascend_fd.pkg import start_rc_diag_job, start_kg_diag_job, start_net_diag_job, start_node_diag_job


class BaseDiagnoser:
    JOB_NAME = "base_diag"
    err_result = {
        "Result": {
            "analyze_success": False,
            "engine_ver": "v1.0.0"
        }
    }

    def __init__(self, input_path, output_path, cfg):
        self.input = input_path,
        self.output = output_path
        self.cfg = cfg
        self.log = init_job_logger(output_path, self.JOB_NAME)

    def start_job(self):
        return self.err_result

    def diag(self):
        """
        use try except to catch errors during diag to return success or failure of parsing.
        """
        self.log.info(f"The {self.JOB_NAME} start.")
        try:
            result = self.start_job()
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


class KgDiagnoser(BaseDiagnoser):
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

    def start_job(self):
        result, worker_list = start_rc_diag_job(self.input, self.output, self.cfg)
        self.err_result.update(result)

        if not worker_list:
            self.log.warning("the root cause node is not found, so the knowledge graph diag task is not started.")
            raise InnerError("the root cause node is not found, so the knowledge graph diag task is not started.")

        kg_result = start_kg_diag_job(self.input, self.output, worker_list, self.cfg)
        result.update(kg_result)
        return result


class NodeDiagnoser(BaseDiagnoser):
    JOB_NAME = "node_diag"
    err_result = {
        "Ascend-Node-Fault-Diag Result": {
            "analyze_success": False,
            "engine_ver": "v1.0.0"
        }
    }

    def start_job(self):
        return start_node_diag_job(self.input, self.output, self.cfg)


class NetDiagnoser(BaseDiagnoser):
    JOB_NAME = "net_diag"
    err_result = {
        "Ascend-Net-Fault-Diag Result": {
            "analyze_success": False,
            "engine_ver": "v1.0.0"
        }
    }

    def start_job(self):
        return start_net_diag_job(self.input, self.output, self.cfg)
