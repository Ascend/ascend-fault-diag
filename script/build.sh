# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. ALL rights reserved.

set -e

CUR_PATH=$(cd "$(dirname "$0")" || exit; pwd)
ROOT_PATH=$(readlink -f "$CUR_PATH"/..)
APP_PATH=$ROOT_PATH/ascend_fd

function log_base() {
    echo "$(date "+%Y-%m-%d %H:%M:%S") [$1]: $2 ${*:3}"
}

shopt -s expand_aliases
alias log_error='log_base ERROR $LINENO'
alias log_info='log_base INFO $LINENO'
alias log_warn='log_base WARN $LINENO'
alias log_debug='log_base DEBUG $LINENO'

function clear() {
  cd ${CUR_PATH}
  rm -rf "${ROOT_PATH}/ascend_fd.egg-info"
  rm -rf "${ROOT_PATH}/dist"
  rm -rf "${ROOT_PATH}/build"
}

function check_result() {
    ret=$?
    message=$1

    if [ $ret -eq 0 ]; then
      log_info "$message success."
      return 0
    else
      log_error "$message failed."
      exit 1
    fi
}

function build_ascend_fd() {
    log_info "begin to build ascend_fd package"
    cd $ROOT_PATH
    python3 ./setup.py bdist_wheel --plat-name=linux_"$(arch)"
    check_result "build ascend_fd package"
}

function package() {
  mkdir -p "${ROOT_PATH}/output/"
  cp -rf "${ROOT_PATH}"/dist/ascend_fd*.whl "${ROOT_PATH}/output/"
}

function main() {
    build_ascend_fd
    package
    clear
}

echo "begin to build ascend_fd"
main;ret=$?
echo "finish build ascend_fd, check_result is $ret"