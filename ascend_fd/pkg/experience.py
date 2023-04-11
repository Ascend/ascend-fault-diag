# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. ALL rights reserved.
from dataclasses import dataclass


@dataclass
class E00000:
    code: int = 0
    cause_zh: str = "正常"
    cause_en: str = "Normally"
    description_zh: str = ""
    description_en: str = ""
    suggestion_zh: str = ""
    suggestion_en: str = ""
    reference_url: str = ""


@dataclass
class E00001:
    code: int = 1
    cause_zh: str = "错误"
    cause_en: str = "Error"
    description_zh: str = ""
    description_en: str = ""
    suggestion_zh: str = ""
    suggestion_en: str = ""
    reference_url: str = ""


@dataclass
class E10000(E00000):
    code: int = 10000
    cause_zh: str = "首节点分析诊断无异常"
    cause_en: str = "Root cluster diagnosis normally"



@dataclass
class E10001(E00001):
    code: int = 10001
    cause_zh: str = "socket建链超时"
    cause_en: str = "get socket timeout"
    reference_url: str = "1. socket建链超时案例：\n" \
                         "https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/" \
                         "63RC1alpha002/troublemanage/troubleshooting/troubleshooting_0112.html"


@dataclass
class E10002(E10001):
    code: int = 10002
    description_zh: str = "该错误为'socket建链超时'错误。该错误可能是由于部分卡被某些耗时较长的任务阻塞而使得卡间同步失败而导致的。"
    description_en: str = "The cause of this error is 'get socket timeout' " \
                          "due to the fail of Inter-card synchronization."
    suggestion_zh: str = "请通过配置'export HCCL_CONNECT_TIMEOUT=xxx'设置一个较长的timeout参数。"
    suggestion_en: str = "Please set a longer timeout parameter by configuring 'export HCCL_CONNECT_TIMEOUT=xxx'."


@dataclass
class E10003(E10001):
    code: int = 10003
    description_zh: str = "该错误为'socket建链超时'错误。具体原因未知。"
    description_en: str = "The cause of this error is 'get socket timeout'. Specific reason is unknown."
    suggestion_zh: str = "1. 请检查故障首节点，或参考故障知识图谱检测结果。\n" \
                         "2. 该类问题需联系华为工程师定位排查。同时您也可参考故障案例了解详情"
    suggestion_en: str = "1. Please check the error root cluster, " \
                         "or refer to the results of the detection of the fault knowledge graph.\n" \
                         "2. Please turn to the relevant engineer to solve this problem. " \
                         "You can also refer to the fault case for details."


@dataclass
class E10004(E00001):
    code: int = 10004
    cause_zh: str = "notify wait超时"
    cause_en: str = "notify timeout"
    reference_url: str = "1. notify wait超时案例：\n" \
                         "https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/" \
                         "63RC1alpha002/troublemanage/troubleshooting/troubleshooting_0113.html"


@dataclass
class E10005(E10004):
    code: int = 10005
    description_zh: str = "该错误为'notify wait超时'错误。该错误可能是由于部分卡被某些耗时较长的任务阻塞而使得卡间同步失败而导致的。"
    description_en: str = "The cause of this error is 'notify timeout' due to the fail of Inter-card synchronization."
    suggestion_zh: str = "请通过配置'export HCCL_EXEC_TIMEOUT=xxx'设置一个较长的timeout参数。"
    suggestion_en: str = "Please set a longer timeout parameter by configuring 'export HCCL_EXEC_TIMEOUT=xxx'."


@dataclass
class E10006(E10004):
    code: int = 10006
    description_zh: str = "该错误为'notify wait超时'错误。具体原因未知。"
    description_en: str = "The cause of this error is 'notify timeout'. Specific reason is unknown."
    suggestion_zh: str = "1. 请检查故障首节点，或参考故障知识图谱检测结果。\n" \
                         "2. 该类问题需联系华为工程师定位排查。同时您也可参考故障案例了解详情"
    suggestion_en: str = "1. Please check the error root cluster, " \
                         "or refer to the results of the detection of the fault knowledge graph.\n" \
                         "2. Please turn to the relevant engineer to solve this problem. " \
                         "You can also refer to the fault case for details."


@dataclass
class E10007(E10006):
    code: int = 10007
    description_zh: str = "该错误为'notify wait超时'错误。可能是部分卡执行过慢或发生了core dump。"
    description_en: str = "The cause of this error is 'notify timeout'. Maybe the rank(s) is/are too slow or core dump."


@dataclass
class E10008(E00001):
    code: int = 10008
    cause_zh: str = "get P2P status超时"
    cause_en: str = "connected p2p timeout"
    reference_url: str = "1. get P2P status超时案例：\n" \
                         "https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/" \
                         "63RC1alpha002/troublemanage/troubleshooting/troubleshooting_0114.html"


@dataclass
class E10009(E10008):
    code: int = 10009
    description_zh: str = "该错误为'get P2P status超时'错误。该错误可能是由于部分卡被某些耗时较长的任务阻塞而使得卡间同步失败而导致的。"
    description_en: str = "The cause of this error is 'connected p2p timeout' due to " \
                          "the fail of Inter-card synchronization."
    suggestion_zh: str = "请通过配置'export HCCL_CONNECT_TIMEOUT=xxx'设置一个较长的timeout参数。"
    suggestion_en: str = "Please set a longer timeout parameter by configuring 'export HCCL_CONNECT_TIMEOUT=xxx'."


@dataclass
class E10010(E10008):
    code: int = 10010
    description_zh: str = "该错误为'get P2P status超时'错误。具体原因未知。"
    description_en: str = "The cause of this error is 'connected p2p timeout'. Specific reason is unknown."
    suggestion_zh: str = "1. 请检查故障首节点，或参考故障知识图谱检测结果。\n" \
                         "2. 该类问题需联系华为工程师定位排查。同时您也可参考故障案例了解详情"
    suggestion_en: str = "1. Please check the error root cluster, " \
                         "or refer to the results of the detection of the fault knowledge graph.\n" \
                         "2. Please turn to the relevant engineer to solve this problem. " \
                         "You can also refer to the fault case for details."


@dataclass
class E10011(E00001):
    code: int = 10011
    cause_zh: str = "SDMA错误"
    cause_en: str = "SDMA error"
    description_zh: str = "该错误为SDMA错误。错误首节点发生了数据溢出。"
    description_en: str = "The cause of this error is 'SDMA overflowing' " \
                          "and data overflow occurred on the error root cluster."
    suggestion_zh: str = "1. 请检查故障首节点，或参考故障知识图谱检测结果。\n" \
                         "2. 该类问题需联系华为工程师定位排查。"
    suggestion_en: str = "1. Please check the error root cluster, " \
                         "or refer to the results of the detection of the fault knowledge graph.\n" \
                         "2. Please turn to the relevant engineer to solve this problem."


@dataclass
class E10012(E00001):
    code: int = 10012
    cause_zh: str = "Memcpy错误"
    cause_en: str = "Memcpy error"
    description_zh: str = "该错误为Memcpy错误。"
    description_en: str = "The cause of the error is Memcpy failed."
    suggestion_zh: str = "1. 请检查故障首节点，或参考故障知识图谱检测结果。\n" \
                         "2. 该类问题需联系华为工程师定位排查。"
    suggestion_en: str = "1. Please check the error root cluster, " \
                         "or refer to the results of the detection of the fault knowledge graph.\n" \
                         "2. Please turn to the relevant engineer to solve this problem."


@dataclass
class E10013(E00001):
    code: int = 10013
    cause_zh: str = "TsdClient错误"
    cause_en: str = "TsdClient error"
    description_zh: str = "该错误为TsdClient错误。部分节点上存在其它HCCP进程。"
    description_en: str = "The cause of the error is 'TsdClient error'. " \
                          "There are other HCCP processes on some clusters."
    suggestion_zh: str = "请等待一段时间或登录设备，杀死HCCP进程或重新启动环境。"
    suggestion_en: str = "Please wait some times or log in to the device " \
                         "and kill the hccp process or restart the environment."


@dataclass
class E10014(E00001):
    code: int = 10014
    cause_zh: str = "心跳丢失错误"
    cause_en: str = "Heartbeat lost error"
    description_zh: str = "该错误为心跳丢失错误。在强杀场景下部分节点丢失心跳信息。"
    description_en: str = "The cause of the error is 'Heartbeat lost error'. " \
                          "Some clusters lost the heartbeat information in the force_kill mode."
    suggestion_zh: str = "请检查丢失心跳设备(卡)上的训练进程是否正常。"
    suggestion_en: str = "Please check the training process on the lost heartbeat device."


@dataclass
class E10015(E00001):
    code: int = 10015
    cause_zh: str = "未知错误"
    cause_en: str = "Unknown error"
    suggestion_zh: str = "该类问题需联系华为工程师定位排查。"
    suggestion_en: str = "Please turn to the relevant engineer to solve this problem."


@dataclass
class E10016(E10015):
    code: int = 10016
    description_zh: str = "在非强杀场景下，所有节点都没有错误日志信息。"
    description_en: str = "No errors logs are found on all ranks when the mode is NO_FORCE_KILL."


@dataclass
class E10017(E10015):
    code: int = 10017
    description_zh: str = "所有节点都没有错误日志信息，且所有节点都没有心跳信息。"
    description_en: str = "No error logs are found on all Ranks. And all ranks don't have heartbeats."


@dataclass
class E10018(E10015):
    code: int = 10018
    description_zh: str = "所有节点都没有错误日志信息，且所有节点都有心跳信息。"
    description_en: str = "No error logs are found on all Ranks. And all ranks have heartbeats."


@dataclass
class E10019(E10015):
    code: int = 10019
    description_zh: str = "第一个报告错误的节点不包含HCCL错误。本组件仅支持HCCL错误检测。"
    description_en: str = "The first rank to report the error does not contain HCCL errors. " \
                          "This component only supports HCCL error detection."


@dataclass
class E10020(E10015):
    code: int = 10020
    description_zh: str = "在非强杀场景下，存在节点不存在错误信息。可能由于该节点进程被挂起导致。"
    description_en: str = "Some clusters have no errs in the log in no-force-kill mode. " \
                          "The possible cause is that the process is hung."
    suggestion_zh: str = "请检查未报错节点上的训练进程。"
    suggestion_en: str = "Please check the train process on the clusters that don't have errs."


@dataclass
class E10021(E10015):
    code: int = 10021
    description_zh: str = "可能存在日志丢失情况，且当前剩余日志中无报错信息。"
    description_en: str = "There may be log loss, and there are no error messages in the remaining logs."
    suggestion_zh: str = "请检查提及的丢失日志节点的情况。"
    suggestion_en: str = "Please check the mentioned missing log clusters."


@dataclass
class E10022(E00001):
    code: int = 10022
    cause_zh: str = "单节点训练错误"
    cause_en: str = "Single cluster error"
    description_zh: str = "这是一个单节点训练任务，因此首节点诊断任务将被跳过。"
    description_en: str = "This is a single-card training task, and the root cluster diag task will skip."
    suggestion_zh: str = "1. 请检查参考故障知识图谱检测结果。\n" \
                         "2. 该类问题需联系华为工程师定位排查。"
    suggestion_en: str = "1. Please refer to the results of the detection of the fault " \
                         "knowledge graph.\n" \
                         "2. Please turn to the relevant engineer to solve this problem."


@dataclass
class E20000(E00000):
    code: int = 20000
    cause_zh: str = "故障知识图谱诊断无异常"
    cause_en: str = "Knowledge graph diagnosis normally"
    description_zh: str = "可能情况：1.无相关故障发生，2.存在未知故障。"
    description_en: str = "Maybe 1. No related faults have occurred, 2. Unknown faults exist."
    suggestion_zh: str = "若存在问题无法解决，请联系华为工程师定位排查，您可以通过https://gitee.com/ascend网站提交issue获取帮助。"
    suggestion_en: str = "If it cannot be resolved, please turn to the relevant engineer to solve this problem."


@dataclass
class E20001(E00001):
    code: int = 20001
    cause_zh: str = "资源申请失败"
    cause_en: str = "Failed to apply for resources"
    description_zh: str = "资源申请失败，可能资源已经被其他进程占用完，或资源已经被其他进程占用完等。"
    description_en: str = "Maybe resources have been occupied by other processes, " \
                          "or resources have been occupied by other processes."
    suggestion_zh: str = "1. 请等待一分钟后再重新启动进程，保证上一个进程资源释放完毕。\n" \
                         "2. 请停止其他进程或者等其他进程执行完成后再启动进程。\n" \
                         "3. 若无法解决，请检查是否超过可用资源上限，如果未超上限，则需要重启环境强行释放资源、恢复环境。"
    suggestion_en: str = "1. Please wait for a minute before restarting the process to ensure that the " \
                         "previous process resources are released.\n" \
                         "2. Please stop other processes or wait for other processes to " \
                         "start the process before starting the process\n" \
                         "3. Please check whether the upper limit of the available resource. If the upper " \
                         "limit is not over limit, need to restart the environment to forcibly release resources."
    reference_url: str = "1. 资源申请失败故障案例：\n" \
                         "https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/" \
                         "63RC1alpha002/troublemanage/troubleshooting/troubleshooting_0103.html"


@dataclass
class E20002(E00001):
    code: int = 20002
    cause_zh: str = "注册算子数超过最大规格"
    cause_en: str = "Registered resources exceeds the maximum setting"
    description_zh: str = "注册算子数超过最大规格，在一个进程内算子等资源注册超过最大规格。"
    description_en: str = "Resources such as the resource in a process exceed the maximum setting."
    suggestion_zh: str = "请自查分析模型代码。\n" \
                         "1. 简化模型或者降低动态batch大小。\n" \
                         "2. 避免同一算子在不同模型中反复注册。\n" \
                         "3. 注册算子数不超过最大规格。"
    suggestion_en: str = "Please self-check the analysis model code.\n" \
                         "1. Simplify the model or reduce the size of the dynamic batch.\n" \
                         "2. Avoid the same operator from registering repeatedly in different models.\n" \
                         "3. The number of registered operators does not exceed the maximum specification."
    reference_url: str = "1. 注册算子数超过最大规格故障案例：\n" \
                         "https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/" \
                         "63RC1alpha002/troublemanage/troubleshooting/troubleshooting_0104.html"


@dataclass
class E20003(E00001):
    code: int = 20003
    cause_zh: str = "AI Core算子执行失败"
    cause_en: str = "Failed to execute the AI Core operator"
    description_zh: str = "AI Core 算子执行失败，可能算子本身代码问题：数据输入不匹配、访问越界、计算溢出等异常。"
    description_en: str = "The execution of the AI Core operator failed, maybe the operator code problem: the data " \
                          "input does not match, access the cross -border, and the calculation overflow is abnormal."
    suggestion_zh: str = "该类问题需联系华为算子开发工程师定位排查。您可以通过https://gitee.com/ascend网站提交issue获取帮助。同时您也可参考故障案例了解详情。"
    suggestion_en: str = "Please turn to the relevant engineer to solve this problem. " \
                         "You can also refer to the [fault case] for details."
    reference_url: str = "1. AI Core故障案例：\n" \
                         "https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/" \
                         "63RC1alpha002/troublemanage/troubleshooting/troubleshooting_0105.html"


@dataclass
class E20004(E00001):
    code: int = 20004
    cause_zh: str = "AI CPU算子执行报错"
    cause_en: str = "Failed to execute the AI Cpu operator"
    description_zh: str = "AI CPU算子执行失败，可能算子本身代码问题：数据输入不匹配、访问越界、AI CPU线程挂死等问题。"
    description_en: str = "The execution of the AI CPU operator failed, maybe the operator code problem: data input " \
                          "does not match, access to the Vietnam boundary, and the AI CPU thread hanging to death."
    suggestion_zh: str = "该类问题需联系华为算子开发工程师定位排查。您可以通过https://gitee.com/ascend网站提交issue获取帮助。同时您也可参考故障案例了解详情。"
    suggestion_en: str = "Please turn to the relevant engineer to solve this problem. " \
                         "You can also refer to the fault case for details."
    reference_url: str = "1. AI Cpu故障案例：\n" \
                         "https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/" \
                         "63RC1alpha002/troublemanage/troubleshooting/troubleshooting_0106.html"


@dataclass
class E20005(E00001):
    code: int = 20005
    cause_zh: str = "Memcpy异步拷贝算子执行报错"
    cause_en: str = "Memory async copy failed"
    description_zh: str = "Memcpy异步拷贝算子执行报错, 可能计算溢出、拷贝地址错误、多P训练时进程退出等。"
    description_en: str = "The execution of memory asynchronous copy operator failed, " \
                          "which may be caused by the problem of calculation overflow, copy address error, " \
                          "and process exit during multiple rank training."
    suggestion_zh: str = "请参考故障案例进行排查。\n" \
                         "1. 通过msnpureport收集device日志，并搜索关键字 'last_cqe_status'。\n" \
                         "2. 通过last_cqe_status值计算错误码值，并依据错误码进行相应自查分析。\n" \
                         "3. 若无法解决，请联系华为HCCL开发工程师定位排查。 您可以通过https://gitee.com/ascend网站提交issue获取帮助。"
    suggestion_en: str = "Please refer to the fault case for investigation.\n" \
                         "1. Collect device log through msnpureport, and search for keywords 'last_cqe_status'. \n" \
                         "2. Calculate the error code through the last_cqe_status value, and perform a corresponding " \
                         "self-check analysis based on the error code.\n" \
                         "3. If it cannot be resolved, please turn to the relevant engineer to solve this problem."
    reference_url: str = "1. Memcpy异步拷贝故障案例：\n" \
                         "https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/" \
                         "63RC1alpha002/troublemanage/troubleshooting/troubleshooting_0107.html"
