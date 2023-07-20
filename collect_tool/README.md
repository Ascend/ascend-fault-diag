## ascend-fault-diag collect_tool

故障诊断组件Ascend-FaultDiag的日志采集脚本


```
collect_tool
    |-- npu_net_stat_collect.py
    |-- npu_smi_stat_collect.py
    |-- npu_net_check_collect.sh
    |-- host_resource_collect.py
```

--------

### 一、npu_net_stat_collect.py
单机“NPU网口统计指标文件”采集脚本

**1、运行说明**

`python3 npu_net_stat_collect.py -n {NPU_NUM} -wt {WAIT_TIME} -ct {COLLECT_TIME} -o {OUTPUT_PATH}`

示例：
`python3 npu_net_stat_collect.py -n 8 -wt 15 -ct 3600 -o /xx/enviornment_check/worker-0`

执行结果： 在`{OUTPUT_PATH}`目录下生成`{NPU_NUM}`个`npu_(\d+)_details.csv`文件。  

**2、参数说明**

`-n {NPU_NUM}`，npu卡数，默认值为8

`-wt {WAIT_TIME}`，采集间隔时间，单位秒，默认值为15

`-ct {COLLECT_TIME}`，采集总时间，单位秒，默认值为60

`-o {OUTPUT_PATH}`，输出目录，必选


--------

### 二、npu_smi_stat_collect.py
单机“NPU状态监控指标文件”采集脚本

**1、运行说明**

`python3 npu_smi_stat_collect.py -it {INTERVAL_TIME} -o {OUTPUT_PATH}`

示例：
`python3 npu_smi_stat_collect.py -it 15 -o /xx/enviornment_check/worker-0`

执行结果： 在`{OUTPUT_PATH}`目录下生成8个`npu_(\d+)_details.csv`文件。  

**2、参数说明**

`-o {OUTPUT_PATH}`，输出目录，必选

`-it {INTERVAL_TIME}`，采集间隔时间，单位秒，默认值为15

--------

### 三、npu_net_check_collect.sh

单机“NPU网口检查文件”采集脚本，注：在训练前和训练后执行该脚本。

**1、运行说明**

`bash npu_net_check_collect.sh {SAVE_FILE}`

示例：
```
bash npu_net_check_collect.sh /xx/enviornment_check/worker-0/npu_info_before.txt
bash npu_net_check_collect.sh /xx/enviornment_check/worker-0/npu_info_after.txt
```

执行结果：生成文件。 

**2、参数说明**

{SAVE_FILE}：保存文件。

--------

### 四、host_resource_collect.py

单机“主机资源监控文件”采集脚本

**1、运行说明**

`python3 host_resource_collect.py -o {OUTPUT_PATH}`

示例：
`python3 host_resource_collect.py -o /xx/enviornment_check/worker-0`

执行结果： 在`{OUTPUT_PATH}`目录下生成`host_metrics_(\d+).json`文件。  

**2、参数说明**

`-o {OUTPUT_PATH}`，输出目录，必选