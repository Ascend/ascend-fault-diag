# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. ALL rights reserved.
import os

FAULT_TEMP = {
    "0": {
        "root_cause_zh_CN": None,
        "root_cause_en_US": None,
        "description_zh_CN": "无NPU过载降频异常的计算节点",
        "description_en_US": "No npu overload occurs, all compute nodes are normal.",
        "suggestion_zh_CN": None,
        "suggestion_en_US": None,
        "fault_detail": None,
        "key_metrics": None
    },
    "21": {
        "root_cause_zh_CN": "NPU过载降频",
        "root_cause_en_US": "NPU overload frequency reduction",
        "description_zh_CN": "计算节点NPU{dev_id}过载降频异常",
        "description_en_US": "NPU{dev_id} overload occurs on the compute node. Frequency reduction is abnormal.",
        "suggestion_zh_CN": "检查节点NPU{dev_id}状态",
        "suggestion_en_US": "Check the status of NPU{dev_id}.",
        "fault_detail": {
            "node_iip": "{IP}",
            "begin_time": "{begin_time}",
            "end_time": "{end_time}"
        },
        "key_metrics": [
            "npu_freq"
        ]
    },
    "22": {
        "root_cause_zh_CN": "NPU过载降频",
        "root_cause_en_US": "NPU overload frequency reduction",
        "description_zh_CN": "计算节点NPU{dev_id}过载降频异常",
        "description_en_US": "NPU{dev_id} overload occurs on the compute node. Frequency reduction is abnormal.",
        "suggestion_zh_CN": "节点{fan_id}不在位，请检查风扇或更换风扇",
        "suggestion_en_US": "{fan_id} of the node is not in position. Check the fan or replace the fan.",
        "fault_detail": {
            "node_iip": "{IP}",
            "begin_time": "{begin_time}",
            "end_time": "{end_time}"
        },
        "key_metrics": [
            "npu_freq",
            "npu_temp",
            "fan_speed"
        ]
    },
    "23": {
        "root_cause_zh_CN": "NPU过载降频",
        "root_cause_en_US": "NPU overload frequency reduction",
        "description_zh_CN": "计算节点NPU{dev_id}过载降频异常",
        "description_en_US": "NPU{dev_id} overload occurs on the compute node. Frequency reduction is abnormal.",
        "suggestion_zh_CN": "节点{fan_id}转速低，请检查风扇或更换风扇",
        "suggestion_en_US": "The fan speed of node {fan_id} is low. Check the fan or replace the fan.",
        "fault_detail": {
            "node_iip": "{IP}",
            "begin_time": "{begin_time}",
            "end_time": "{end_time}"
        },
        "key_metrics": [
            "npu_freq",
            "npu_temp",
            "fan_speed"
        ]
    },
    "24": {
        "root_cause_zh_CN": "NPU过载降频",
        "root_cause_en_US": "NPU overload frequency reduction",
        "description_zh_CN": "计算节点NPU{dev_id}过载降频异常",
        "description_en_US": "NPU{dev_id} overload occurs on the compute node. Frequency reduction is abnormal.",
        "suggestion_zh_CN": "检查机房温度或进风口是否堵塞",
        "suggestion_en_US": "Check the temperature of the equipment room or whether the air intake vent is blocked.",
        "fault_detail": {
            "node_iip": "{IP}",
            "begin_time": "{begin_time}",
            "end_time": "{end_time}"
        },
        "key_metrics": [
            "npu_freq",
            "npu_temp"
        ]
    },
    "10": {
        "root_cause_zh_CN": "CPU抢占（全部）",
        "root_cause_en_US": "CPU preemption (All CPU preemption)",
        "description_zh_CN": "计算节点发生CPU资源抢占异常",
        "description_en_US": "CPU resource preemption exception occurred on compute node.",
        "suggestion_zh_CN": "查看节点是否有非法进程抢占CPU资源",
        "suggestion_en_US": "Check whether an unauthorized process preempts CPU resources on node.",
        "fault_detail": {
            "begin_time": "{begin_time}",
            "end_time": "{end_time}"
        },
        "key_metrics": [
            "cpu_percent",
            "cpu_load1",
            "cpu_load5"
        ]
    },
    "20": {
        "root_cause_zh_CN": "CPU抢占（部分）",
        "root_cause_en_US": "CPU preemption (Partial CPU preemption)",
        "description_zh_CN": "计算节点发生CPU资源抢占异常",
        "description_en_US": "CPU resource preemption exception occurred on compute node.",
        "suggestion_zh_CN": "查看节点是否有非法进程抢占CPU资源",
        "suggestion_en_US": "Check whether an unauthorized process preempts CPU resources on node.",
        "fault_detail": {
            "begin_time": "{begin_time}",
            "end_time": "{end_time}"
        },
        "key_metrics": [
            "cpu_percent",
            "cpu_load1",
            "cpu_load5"
        ]
    },
    "30": {
        "root_cause_zh_CN": "CPU抢占（多CPU）",
        "root_cause_en_US": "CPU preemption (Partial CPU preemption)",
        "description_zh_CN": "计算节点发生CPU资源抢占异常",
        "description_en_US": "CPU resource preemption exception occurred on compute node.",
        "suggestion_zh_CN": "查看节点是否有非法进程抢占CPU资源",
        "suggestion_en_US": "Check whether an unauthorized process preempts CPU resources on node.",
        "fault_detail": {
            "begin_time": "{begin_time}",
            "end_time": "{end_time}"
        },
        "key_metrics": [
            "cpu_percent",
            "cpu_load1",
            "cpu_load5"
        ]
    },
    "60": {
        "root_cause_zh_CN": "内存抢占",
        "root_cause_en_US": "Memory preemption",
        "description_zh_CN": "计算节点在发生内存资源抢占异常",
        "description_en_US": "A memory resource preemption exception occurred on compute node.",
        "suggestion_zh_CN": "查看节点是否有非法进程抢占CPU资源",
        "suggestion_en_US": "Check whether an unauthorized process preempts CPU resources on node.",
        "fault_detail": {
            "begin_time": "{begin_time}",
            "end_time": "{end_time}"
        },
        "key_metrics": [
            "mem_percent",
            "mem_used"
        ]
    }
}

PWD_PATH = os.path.dirname(os.path.realpath(__file__))

MODEL_CONF = {
    "predictdirjsonpath": "",
    "debugpath": "",
    "resultsavepath": "",
    "outputJsonFilename": "",
    "processcpu_modelpath": os.path.join(PWD_PATH, "AIServerAnomalyDetection/models/l3/process_cpu_model"),
    "servermemory_modelpath": os.path.join(PWD_PATH, "AIServerAnomalyDetection/models/l3/memory_leak_model"),
    "processcpu_modeltype": 0,
    "servermemory_modeltype": 0,
    "meanNormalDataNumber": 10,
    "spath": None,
    "isTimeisStr": None,
    "server_feature": [
        "mem_used",
        "pgfree",
        "freq",
        "usr_cpu",
        "kernel_cpu"
    ],
    "server_accumulate_feature": [
        "pgfree",
        "usr_cpu",
        "kernel_cpu"
    ],
    "process_feature": [
        "usr_cpu",
        "kernel_cpu",
        "rss",
        "read_chars",
        "read_bytes"
    ],
    "normalpath": None,
    "normalDataMean": {
        "server": {
            "cpu": 0.13037273413896955
        },
        "process": {}
    },
    "cpuReadCharsMax": 100000000000,
    "memleakpermin": 10773.908684800002,
    "abnormalCpuTimeThread": 0.07716314213981888,
    "randomcpuThreshold": 60.8699677419
}
