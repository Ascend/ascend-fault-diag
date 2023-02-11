# ascend-fault-diag
**1、依赖开源软件**:

无

## Ascned-fd parse

**1、运行说明**

wheel包安装后，命令执行

`ascend-fd parse -i {INPUT_PATH} -o {OUTPUT_PATH}`

示例：`ascend-fd parse -i modelarts-log-dir/ -o ascend/`

**2、参数说明**

`-i {INPUT_PATH}`，输入目录，指定到需要清洗的日志目录

`-o {OUTPUT_PATH}`，输出目录，指定到清洗完毕的数据输出目录

**3、运行结果**

日志清洗文件存放在`{OUTPUT_PATH}/fault_diag_data/worker-{task_index}/`下

**4、源码打包**

`python3 setup.py bdist_wheel`

--------

## Ascned-fd diag

**1、运行说明**

wheel包安装后，命令执行

`ascend-fd diag -i {INPUT_PATH} -o {OUTPUT_PATH}`

示例：

1）不打屏：`ascend-fd parse -i xx/fault_diag_data/ -o ascend/`
2）打屏：`ascend-fd parse -i xx/fault_diag_data/ -o ascend/ -p`

**2、参数说明**

`-i {INPUT_PATH}`，输入目录，指定到清洗后的数据目录，需要强制指定到`fault_diag_data/`此级

`-o {OUTPUT_PATH}`，输出目录，指定到诊断完毕的报告输出目录

`-p`，指定后开启输入打屏，默认不打屏

`-m`，是否为心跳force-kill场景，默认为0，即force-kill场景。可选[0,1]；1：force-kill，2：no force-kill

**3、运行结果**

诊断报告文件存放在`{OUTPUT_PATH}/fault_diag_result/`下

**4、源码打包**

`python3 setup.py bdist_wheel`

--------

## 镜像使用示例

**1、启动镜像，挂在清洗后数据目录**

ma-user执行：`docker run -it --rm -v /xxx/ascend:/home/ma-user/job/ascend/ ascned-fd-ubuntu-20.04-py38:v0.3`

root执行：`docker run -it --rm --user=root -v /xxx/ascend:/home/ma-user/job/ascend/ ascned-fd-ubuntu-20.04-py38:v0.3`

**2、执行诊断命令**

`ascend-fd diag -i {INPUT_PATH} -o {OUTPUT_PATH}`

示例：`ascend-fd diag -i /home/ma-user/job/ascend/fault_diag_data/ -o /home/ma-user/job/ascend/ -p`