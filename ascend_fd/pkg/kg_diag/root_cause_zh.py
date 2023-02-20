# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. All rights reserved.

class RootCauseZhTranslater:
    DEFAULT_CAUSE_ZH = "未知根因"

    ROOT_CAUSE_EN_TO_ZH = {
        "RuntimeTaskException_Alarm": "RUNTIME报错：任务异常",
        "RuntimeAicoreError_Alarm": "RUNTIME报错：aicore错误",
        "RuntimeModelExecuteTaskFailed_Alarm": "RUNTIME报错：模型执行任务失败",
        "RuntimeAicoreKernelExecuteFailed_Alarm": "RUNTIME报错：aicore内核执行失败",
        "RuntimeStreamSyncFailed_Alarm": "RUNTIME报错：流同步失败",
        "GEModelStreamSyncFailed_Alarm": "GE报错：模型流同步失败",
        "GERunModelFail_Alarm": "GE报错：运行模型失败",

        "FailedToApplyForResources_Alarm": "资源申请失败",
        "RegisteredResourcesExceedsTheMaximum_Alarm": "注册资源超过最大值失败",
        "FailedToexecuteTheAICoreOperator_Alarm": "AI Core算子执行失败",
        "ExecuteModelFailed_Alarm": "执行模型失败",
        "FailedToexecuteTheAICpuOperator_Alarm": "AI Cpu算子执行失败",
        "MemoryAsyncCopyFailed_Alarm": "Memcpy异步拷贝算子执行失败",
        "NotifyWaitExecuteFailed_Alarm": "Notify算子执行失败",

        "TaskRunFailed_Alarm": "任务运行失败",
        "TheTrainingTaskExitsAbnormally_Alarm": "AI Core算子执行失败",
        "RuntimeFaulty_Alarm": "Runtime故障",
        "FailedToRestartTheProcess_Alarm": "重启进程失败",
        "FailedToLoadTheModel_Alarm": "加载模型失败",
    }

    def __init__(self):
        pass

    @classmethod
    def get_root_cause_zh(cls, root_cause_en, sep=','):
        root_cause_en_list = root_cause_en.split(sep)
        return ", ".join([cls.ROOT_CAUSE_EN_TO_ZH.get(root_cause.strip(), cls.DEFAULT_CAUSE_ZH)
                         for root_cause in root_cause_en_list])
