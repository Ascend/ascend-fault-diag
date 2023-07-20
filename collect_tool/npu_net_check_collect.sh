#!/bin/bash
save_file=$1
npu_num=8

for((i=0;i<npu_num;i++));
do
  echo "/usr/local/Ascend/driver/tools/hccn_tool -i ${i} -ip -g">>${save_file}
  hccn_tool -i ${i} -ip -g>>${save_file}
  echo -e "\n">>${save_file}
done


for((i=0;i<npu_num;i++));
do
  echo "/usr/local/Ascend/driver/tools/hccn_tool -i ${i} -stat -g">>${save_file}
  hccn_tool -i ${i} -stat -g>>${save_file}
  echo -e "\n">>${save_file}
done


for((i=0;i<npu_num;i++));
do
  echo "/usr/local/Ascend/driver/tools/hccn_tool -i ${i} -link_stat -g">>${save_file}
  hccn_tool -i ${i} -link_stat -g>>${save_file}
  echo -e "\n">>${save_file}
done
