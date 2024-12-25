#!/bin/bash
set -x
#建立个当前目录
mkdir -p javalog
declare namespace=$1
declare str=$2
if [ -z "$3" ]; then
    config="config"
else
    config="$3"
fi


cd javalog
# 注意tr "\n"这个空格
deployments=$(sudo kubectl --kubeconfig=/root/.kube/"$config" get pods -o=jsonpath='{.items[*].metadata.name}'  -n $namespace | tr  ' '  '\n' |grep $str)


for dep in $deployments
do
sudo kubectl --kubeconfig=/root/.kube/"$config" cp "$dep":/gc.log.0.current "$dep"_gc.log -n $namespace
spid=$(sudo kubectl --kubeconfig=/root/.kube/"$config" exec -ti "$dep" -n $namespace -- /bin/bash -c 'pgrep -f "java -server" | grep -v "^1$"')
pid=$(echo "$spid" | head -n1 | tr -d '\r')
sudo kubectl --kubeconfig=/root/.kube/"$config" exec -ti "$dep" -n $namespace -- /bin/bash -c "jmap -dump:live,format=b,file=/tmp/$dep.hprof $pid"
sudo kubectl --kubeconfig=/root/.kube/"$config" -n $namespace cp "$dep":/tmp/"$dep".hprof  "$dep".hprof
sudo kubectl --kubeconfig=/root/.kube/"$config" exec -ti "$dep" -n $namespace   -- /bin/bash -c "jstack $pid" > "$dep"_jstack.log
done
