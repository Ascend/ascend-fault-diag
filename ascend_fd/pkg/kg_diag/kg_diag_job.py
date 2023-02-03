# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
import json
import os
import logging
import re
import subprocess
import tarfile

from ascend_fd.status import FileNotExistError, JavaError, InfoNotFoundError
from ascend_fd.tool import safe_open, safe_chmod


kg_logger = logging.getLogger("kg_diag")
PWD_PATH = os.path.dirname(os.path.realpath(__file__))
KG_JAR_PATH = os.path.join(PWD_PATH, "kginfer.jar")
KG_REPO = os.path.join(PWD_PATH, "knowledge-repository")
MAX_WORKER_NUM = 5


def start_kg_diag_job(output_path, worker_list, cfg):
    kg_result = dict()
    kg_relation = dict()
    cfg = cfg.get("parse_data", {})
    for worker_id in worker_list:
        result_json, relation_json = kg_diag_job(worker_id, cfg)
        kg_result.update(result_json)
        kg_relation.update(relation_json)

    kg_result = {"Ascend-Knowledge-Graph-Fault-Diag Result": kg_result}
    kg_out_file = os.path.join(output_path, "kg_diag_report.json")
    with safe_open(kg_out_file, 'w+', encoding='utf8') as file_stream:
        file_stream.write(json.dumps(kg_result, ensure_ascii=False, indent=4))
    safe_chmod(kg_out_file, 0o640)

    return kg_result


def kg_diag_job(worker_id, cfg):
    kg_logger.info(f"start knowledge graph diagnosis task for worker-{worker_id}.")
    java_path = get_java_env()
    input_json_zip = get_kg_input_zip(worker_id, cfg)

    sub_res = subprocess.run([java_path, "-Xms128m", "-Xmx128m", "-jar", KG_JAR_PATH, KG_REPO, input_json_zip],
                              capture_output=True, shell=False)
    result_find = re.search(r"{(\"analyze_success.*?)}$", sub_res.stdout.decode())
    os.remove(input_json_zip)

    if not result_find:
        kg_logger.error(f"the kg-engine analyze worker-{worker_id} error, "
                        f"the analysis results in the corresponding format is not found.")
        raise InfoNotFoundError(f"the analysis results in the corresponding format "
                                f"is not found for worker-{worker_id}.")

    result_str = "{" + result_find[1] + "}"
    diag_json = json.loads(result_str)
    if diag_json.get("fault_chain", None):
        diag_json["fault_chain"] = json.loads(diag_json["fault_chain"])

    relation_json = dict()
    if diag_json.get("fault_chain", None):
        relation_json["rlt_graph"] = json.loads(diag_json["rlt_graph"])

    result_json = {
        f"worker-{worker_id}": diag_json
    }
    relation_json = {
        f"worker-{worker_id}": relation_json
    }

    return result_json, relation_json


def get_kg_input_zip(rc_worker_id, cfg):
    worker_parse_data = cfg.get(f'worker-{rc_worker_id}')
    if not worker_parse_data:
        kg_logger.error(f'worker-{rc_worker_id} dir is not exist')
        raise FileNotExistError(f'worker-{rc_worker_id} dir is not exist')

    file_name = worker_parse_data.get("kg_parse_path", None)
    if not file_name:
        kg_logger.error(f'ascend-kg-parser.json is not exist in worker-{rc_worker_id}')
        raise FileNotExistError(f'ascend-kg-parser.json is not exist in worker-{rc_worker_id}')

    dir_path = os.path.dirname(file_name)
    tarfile_name = os.path.join(dir_path, "ascend-kg-parser.tar.gz")
    with tarfile.open(tarfile_name, "w:gz") as tar_file:
        tar_file.add(file_name, arcname="ascend-kg-parser.json", recursive=False)
    return tarfile_name


def get_java_env():
    """
    get java environment path
    """
    java_home = os.getenv("JAVA_HOME")
    if not java_home:
        kg_logger.error('JAVA_HOME is not find, please configure Java environment variables')
        raise JavaError('JAVA_HOME is not find, please configure Java environment variables')
    return os.path.join(java_home, "bin/java")
