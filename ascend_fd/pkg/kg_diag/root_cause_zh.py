# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. All rights reserved.

class RootCauseZhTranslater:
    DEFAULT_CAUSE_ZH = "未知根因"

    ROOT_CAUSE_EN_TO_ZH = {
        "RuntimeTaskException_Alarm": "RUNTIME报错任务异常告警",
        "RuntimeAicoreError_Alarm": "RUNTIME报错aicore错误告警",
        "RuntimeModelExecuteTaskFailed_Alarm": "RUNTIME报错模型执行任务失败告警",
        "RuntimeAicoreKernelExecuteFailed_Alarm": "RUNTIME报错aicore内核执行失败告警",
        "RuntimeStreamSyncFailed_Alarm": "RUNTIME报错流同步告警",
        "GEModelStreamSyncFailed_Alarm": "GE报错模型流同步失败告警",
        "GERunModelFail_Alarm": "GE报错运行模型失败告警",

        "FailedToApplyForResources_Alarm": "资源申请失败告警",
        "RegisteredResourcesExceedsTheMaximum_Alarm": "注册资源超过最大值失败告警",
        "FailedToexecuteTheAICoreOperator_Alarm": "AI Core算子执行失败告警",
        "ExecuteModelFailed": "执行模型失败告警",
        "FailedToexecuteTheAICpuOperator_Alarm": "AI Cpu算子执行失败告警",
        "MemoryAsyncCopyFailed_Alarm": "Memcpy异步拷贝算子执行失败告警",
        "NotifyWaitExecuteFailed_Alarm": "Notify算子执行失败告警",

        "TaskRunFailed_Alarm": "任务运行失败告警",
        "TheTrainingTaskExitsAbnormally_Alarm": "AI Core算子执行失败告警",
        "RuntimeFaulty_Alarm": "Runtime故障告警",
        "FailedToRestartTheProcess_Alarm": "重启进程失败告警",
        "FailedToLoadTheModel_Alarm": "加载模型失败告警",
    }

    def __init__(self):
        pass

    @classmethod
    def get_root_cause_zh(cls, root_cause_en, sep=','):
        root_cause_en_list = root_cause_en.split(sep)
        return ", ".join([cls.ROOT_CAUSE_EN_TO_ZH.get(root_cause.strip(), cls.DEFAULT_CAUSE_ZH)
                         for root_cause in root_cause_en_list])
