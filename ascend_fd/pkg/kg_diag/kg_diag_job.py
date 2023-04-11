# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. All rights reserved.
import json
import os
import logging
import re
import subprocess
import tarfile

from ascend_fd.pkg import fault_code
from ascend_fd.status import FileNotExistError, JavaError, InfoNotFoundError, FileOpenError
from ascend_fd.pkg.note_msg import MULTI_KG_ROOT_CAUSE_MSG

kg_logger = logging.getLogger("kg_diag")
PWD_PATH = os.path.dirname(os.path.realpath(__file__))
KG_JAR_PATH = os.path.join(PWD_PATH, "kginfer.jar")
KG_REPO = os.path.join(PWD_PATH, "knowledge-repository")
MAX_WORKER_NUM = 5


ROOT_CAUSE_TO_FAULTCODE = {
    "FailedToApplyForResources_Alarm": fault_code.RUNTIME_RESOURCEAPPLY_FAULT,
    "RegisteredResourcesExceedsTheMaximum_Alarm": fault_code.RUNTIME_REGISTERED_FAULT,
    "FailedToexecuteTheAICoreOperator_Alarm": fault_code.RUNTIME_AICORE_FAULT,
    "FailedToexecuteTheAICpuOperator_Alarm": fault_code.RUNTIME_AICPU_FAULT,
    "MemoryAsyncCopyFailed_Alarm": fault_code.RUNTIME_MEMASYNCCOPY_FAULT,
}


def start_kg_diag_job(worker_server_list, cfg):
    kg_result = {
        'analyze_success': True
    }
    parsed_data = cfg.parse_data
    for worker_server_id in worker_server_list:
        result_json = kg_diag_job(worker_server_id, parsed_data)
        kg_result.update(result_json)
    return kg_result


def kg_diag_job(worker_server_id, parsed_data):
    worker_id, server_id = worker_server_id
    kg_logger.info(f"start knowledge graph diagnosis task for worker-{worker_id}.")
    java_path = get_java_env()
    input_json_zip = get_kg_input_zip(worker_id, parsed_data)

    # call the kg-engine to analyze root cause
    sub_res = subprocess.run([java_path, "-Xms128m", "-Xmx128m", "-jar", KG_JAR_PATH, KG_REPO, input_json_zip],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, encoding="utf-8")
    result_find = re.compile(r"{.*?analyze_success.*?}$").findall(sub_res.stdout)
    os.remove(input_json_zip)

    if not result_find:
        engine_err = sub_res.stderr
        kg_logger.error(f"the kg-engine analyze worker-{worker_id} failed. The reason is: {engine_err}")
        raise InfoNotFoundError(f"the kg-engine analyze worker-{worker_id} failed. Please check the detail log.")

    result_str = result_find[0]  # only match one reasoning result
    return diag_json_wrapper(result_str, worker_server_id)


def diag_json_wrapper(result_str, worker_server_id, sep=','):
    note_msgs = list()
    diag_json = json.loads(result_str)
    rlt_graph = json.loads(diag_json["rlt_graph"])
    root_cause_en = diag_json.get("root_cause_en_US", "")

    fault_code_list = list()
    for cause in root_cause_en.split(sep):
        code = ROOT_CAUSE_TO_FAULTCODE.get(cause, None)
        if not code:
            continue
        fault_code_list.append(code)

    if not fault_code_list:
        kg_logger.warning("Knowledge graph diagnosis normally, "
                          "maybe 1. No related faults have occurred, 2. Unknown faults exist")
        # if kg-engine doesn't diagnose the root cause, set a default code
        fault_code_list.append(fault_code.KG_DIAGNOSIS_NORMAL)

    if len(fault_code_list) > 1:
        note_msgs.append(MULTI_KG_ROOT_CAUSE_MSG)

    return {worker_server_id: {
        'error_code': fault_code_list,
        'all_root_cause_entity': root_cause_en,
        'rlt_graph': rlt_graph,
        'note_msgs': note_msgs
    }}


def get_kg_input_zip(rc_worker_id, parsed_data):
    """
    get kg-engine input file.
    """
    worker_parse_data = parsed_data.get(f'worker-{rc_worker_id}')
    if not worker_parse_data:
        kg_logger.error(f'worker-{rc_worker_id} dir is not exist')
        raise FileNotExistError(f'worker-{rc_worker_id} dir is not exist')

    file_name = worker_parse_data.get("kg_parse_path", None)
    if not file_name:
        kg_logger.error(f'ascend-kg-parser.json is not exist in worker-{rc_worker_id}')
        raise FileNotExistError(f'ascend-kg-parser.json is not exist in worker-{rc_worker_id}')

    if os.path.islink(file_name):
        kg_logger.error(f'ascend_kg_parser.json should not be a symbolic link file')
        raise FileOpenError(f'ascend_kg_parser.json should not be a symbolic link file')

    # kg-engine doesn't support JSON format, need to compress *.json file to *.tar.gz
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
