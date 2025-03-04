#!/bin/bash
echo "press ctrl+c to stop collapse"

# 定义目标目录路径（替换为你的实际路径）
dir="/home/qiguanxiao/Desktop/work/flamegraph/ws/${1}"

# 如果目录存在，则删除其所有内容（包括子目录和文件）
if [ -d "$dir" ]; then
    rm -rf "$dir"
    echo "已删除目录: $dir"
fi

# 创建目录（即使父目录不存在也会递归创建）
mkdir -p "$dir"
echo "已创建目录: $dir"

chown qiguanxiao:qiguanxiao ${dir}

echo "collect target command......."
bpftrace cxx_trace.bt > ${dir}/${1}_trace.log &

echo "collect total command......."
bpftrace mytrace.bt > ${dir}/${1}_data_raw.txt




python3 trans.py --pkgName ${1}

perl flamegraph.pl > ${dir}/${1}_result.svg ${dir}/${1}_data_processed.txt

chown qiguanxiao:qiguanxiao  ${dir}/${1}_result.svg ${dir}/${1}_data_raw.txt ${dir}/${1}_data_processed.txt ${dir}/${1}_trace.log

