#!/bin/bash
# Copyright Huawei Technologies Co., Ltd. 2022-2023. All rights reserved.

set -e

CUR_PATH=$(cd "$(dirname "$0")" || exit; pwd)
ROOT_PATH=$(readlink -f "$CUR_PATH"/..)

OUTPUT_PATH="${ROOT_PATH}/output"
DT_RESULT_PATH="${ROOT_PATH}/DT"
DT_RESULT_COV_DIR="${DT_RESULT_PATH}/cov_data"
DT_RESULT_XML_DIR="${DT_RESULT_PATH}/xmls"
DT_RESULT_HTMLS_DIR="${DT_RESULT_PATH}/htmls"

ASCEND_FD_VENV_DIR="${OUTPUT_PATH}/.venvs/ascend_fd"
ASCEND_FD_DT_REQUIREMENTS_FILE_PATH="${CUR_PATH}/requirements.txt"


function run_tests_of_ascend_fd() {
  python3 -m pip install virtualenv
  python3 -m virtualenv -p "$(which python3)" "${ASCEND_FD_VENV_DIR}"
  source ${ASCEND_FD_VENV_DIR}/bin/activate

  pip install -r "${ROOT_PATH}/requirements.txt"
  pip install -r "$ASCEND_FD_DT_REQUIREMENTS_FILE_PATH"

  cd "${ROOT_PATH}" || exit 3
  python3 setup.py develop -i https://repo.huaweicloud.com/repository/pypi/simple/

  pytest "${ROOT_PATH}" \
  --cov="${ROOT_PATH}" --cov-branch \
  --junit-xml="${DT_RESULT_XML_DIR}"/final.xml \
  --html="${DT_RESULT_HTMLS_DIR}"/asecndfd.html \
  --self-contained-html

  mkdir -p "${DT_RESULT_COV_DIR}"
  mv .coverage "${DT_RESULT_COV_DIR}"
  cd "${DT_RESULT_COV_DIR}" || exit 3
  coverage xml
  coverage html -d coverage_result

  cd "${ROOT_PATH}" || exit 3
  python3 setup.py develop --uninstall

  deactivate
  [ -d "${ASCEND_FD_VENV_DIR}"] && rm -rf "${OUTPUT_PATH}/.venvs"

  echo "Running DT for ascend_fd over."
}

function main() {
  echo "Running DT for ascend_fd now..."
  run_tests_of_ascend_fd
  echo "All DT for ascend_fd over, now working in dir:"
  pwd
}

main
echo "DT running took :$(expr "$end" - "$start")" seconds
