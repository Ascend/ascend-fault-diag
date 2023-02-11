# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. All rights reserved.
import json
import os
import logging
import re
import subprocess
import tarfile

from ascend_fd.status import FileNotExistError, JavaError, InfoNotFoundError, FileOpenError
from ascend_fd.tool import safe_open, safe_chmod
from ascend_fd.pkg.kg_diag.root_cause_zh import RootCauseZhTranslater

kg_logger = logging.getLogger("kg_diag")
PWD_PATH = os.path.dirname(os.path.realpath(__file__))
KG_JAR_PATH = os.path.join(PWD_PATH, "kginfer.jar")
KG_REPO = os.path.join(PWD_PATH, "knowledge-repository")
MAX_WORKER_NUM = 5


def start_kg_diag_job(output_path, worker_list, cfg):
    kg_result = dict()
    kg_relation = dict()
    parsed_data = cfg.parse_data
    for worker_id in worker_list:
        result_json, relation_json = kg_diag_job(worker_id, parsed_data)
        kg_result.update(result_json)
        kg_relation.update(relation_json)

    kg_result = {"Ascend-Knowledge-Graph-Fault-Diag Result": kg_result}
    kg_out_file = os.path.join(output_path, "kg_diag_report.json")
    with safe_open(kg_out_file, 'w+', encoding='utf8') as file_stream:
        file_stream.write(json.dumps(kg_result, ensure_ascii=False, indent=4))
    safe_chmod(kg_out_file, 0o640)

    return kg_result


def kg_diag_job(worker_id, parsed_data):
    kg_logger.info(f"start knowledge graph diagnosis task for worker-{worker_id}.")
    java_path = get_java_env()
    input_json_zip = get_kg_input_zip(worker_id, parsed_data)

    sub_res = subprocess.run([java_path, "-Xms128m", "-Xmx128m", "-jar", KG_JAR_PATH, KG_REPO, input_json_zip],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, encoding="utf-8")
    result_find = re.compile(r"{.*?analyze_success.*?}").findall(sub_res.stdout)
    os.remove(input_json_zip)

    if not result_find:
        engine_err = sub_res.stderr
        kg_logger.error(f"the kg-engine analyze worker-{worker_id} failed. The reason is: {engine_err}")
        raise InfoNotFoundError(f"the kg-engine analyze worker-{worker_id} failed. Please check the detail log.")

    result_str = result_find[0]  # only match one reasoning result
    return diag_json_wrapper(result_str, worker_id)


def diag_json_wrapper(result_str, worker_id):
    result_json = {
        "analyze_success": None,
        "engine_ver": None,
        "root_cause_zh_CN": None,
        "root_cause_en_US": None,
        "rlt_graph": None
    }
    relation_json = dict()

    diag_json = json.loads(result_str)
    for key in result_json:
        if key == "rlt_graph":
            relation_json["rlt_graph"] = json.loads(diag_json["rlt_graph"])
        result_json[key] = diag_json.get(key, None)

    root_cause_en = result_json.get("root_cause_en_US", None)
    if root_cause_en:
        result_json["root_cause_zh_CN"] = RootCauseZhTranslater.get_root_cause_zh(root_cause_en)
    else:
        result_json["root_cause_zh_CN"] = ""

    result_json = {
        f"worker-{worker_id}": result_json
    }
    relation_json = {
        f"worker-{worker_id}": relation_json
    }

    return result_json, relation_json


def get_kg_input_zip(rc_worker_id, parsed_data):
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
