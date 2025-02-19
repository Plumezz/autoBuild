import argparse
from collections import deque
import os
import select
import shutil
import subprocess
import sys

from graphviz import Digraph

# hello 
DATA = "/home/qiguanxiao/Desktop/work/data/"
ROSDATA = "/home/qiguanxiao/Desktop/work/data/rosData/"
PICTURE = "/home/qiguanxiao/Desktop/work/data/rosPicture"
PKGDEPS = "/home/qiguanxiao/Desktop/work/data/rosData/pkgDeps.txt"
DEPGRAPHDATA = "/home/qiguanxiao/Desktop/work/data/rosData/"
DEPENDENTPKGS = "/home/qiguanxiao/ws/dependencies/"
WS = "/home/qiguanxiao/ws/"

# ROS1 = {"roscpp": "roscpp_core"}
ROS1 = [
    "catkin", 
    "roscpp", 
    "dynamic_reconfigure", 
    "rviz_plugin_tutorials", 
    "rosunit", 
    "nodelet", 
    "rosbag_storage", 
    "message_generation", 
    "ira_laser_tools", 
    "actionlib", 
    "rosbash", 
    "map_server", 
    "roslaunch", 
    "sophus", 
    "tf", 
    "robotont_msgs", 
    "roscpp_serialization", 
    "ros_type_introspection", 
    "rosbag_migration_rule", 
    "rosconsole", 
    "base_local_planner", 
    "dwa_local_planner", 
    "hector_mapping", 
    "move_base", 
    "sbpl_lattice_planner", 
    "teb_local_planner", 
    "fake_localization", 
    "nav_core2", 
    "nav_grid_iterators", 
    "gazebo_ros_control",
    "message_runtime"
]
VERSION = ["humble",]


def getAllOriDir(wsName):
    ans = list()
    if not os.path.exists(wsName):
        print(f"错误: 路径 {wsName} 不存在！")
        return
    for dirpath, dirnames, filenames in os.walk(wsName):
        
        # 列出该目录中的所有子目录
        if dirnames:
            # print('子目录:', dirnames)
            ans.append(dirnames)

    return ans



def getPicture(pkgName, curDepGraDir, num):
    # 创建有向图对象
    dot = Digraph(comment=f'{pkgName} Dependency Graph')

    # 定义节点集合，用于去重添加节点，避免重复添加
    nodes = set()

    # 逐行解析数据并添加节点和边到有向图中
    data_lines = []

    added_edges = set()

    fileName = f"{curDepGraDir}/{num}.txt"
    with open(fileName, 'r') as f:
        contents = f.readlines()
        for line in contents:
            if line.startswith("len path") or line.startswith("not in ") or line == '\n':
                continue
            else:
                data_lines.append(line)

    
    for line in data_lines:
        parts = line.split(' -> ')
        for node_name in parts[0:]:  # 从第二个元素开始是节点名，第一个元素是无关描述信息跳过
            node_name = node_name.strip()  # 去除节点名两边的空白字符
            nodes.add(node_name)
            dot.node(node_name)  # 添加节点到图中

    for line in data_lines:
        parts = line.split(' -> ')
        for i in range(0, len(parts) - 1):  # 依次添加边，连接相邻的节点
            source = parts[i].strip()
            target = parts[i + 1].strip()
            edge = (source, target)
            if edge not in added_edges:
                dot.edge(source, target)
                added_edges.add(edge)

    # 渲染并保存图形为文件，默认格式是PDF，也可以指定其他格式如'dot.png'等
    pirDir = f"{PICTURE}/{pkgName}"
    if not os.path.exists(pirDir):
        os.mkdir(pirDir)
    dot.render(f'{pirDir}/{pkgName}_dependency_graph_{num}', view=True)

    graph_dict = {}

    for node in nodes:
        graph_dict[node] = []
    for edge in added_edges:
        graph_dict[edge[0]].append(edge[1])

    # 找到根节点（入度为0的节点）
    in_degrees = {node: 0 for node in graph_dict}
    for node in graph_dict:
        for neighbor in graph_dict[node]:
            in_degrees[neighbor] += 1
    root = [node for node in in_degrees if in_degrees[node] == 0]

    # 从根节点开始的广度优先遍历
    queue = deque(root)
    
    visited = set()
    num = 0
    ans = list()
    while queue:
        count  = len(queue)
        num += 1
        traversed_order = []
        while count > 0:
            current_node = queue.popleft()
            if current_node not in visited:
                traversed_order.append(current_node)
                visited.add(current_node)
                for neighbor in graph_dict[current_node]:
                    queue.append(neighbor)
            count -= 1
        # print(f"{num} layers: {traversed_order}")
        ans.append(traversed_order)

    return ans


def getPkglist(file):

    pkg = {}
    pkgName = ""
    with open(file, 'r') as f:
        content = f.readlines()
        for line in content:
            if line.startswith("pkg:"):
                pkgName = (line[8:-1])
            elif line.startswith("page"):
                pkg[pkgName] = line[9:-1]
    
    return pkg


def getRepo(pkgName):
    repoDir = {}
    for version in VERSION:
        verData = ROSDATA + version
        repos = verData + "/repository.txt"
        with open(repos, 'r') as f:
            contents = f.readlines()
            for i in range(len(contents)):
                if contents[i].startswith("  reposity:"):
                    pkgList = []
                    repoName = contents[i + 1][4:-1]
                    i = i + 2
                    while not contents[i].startswith('*'):
                        #pkgList.append(contents[i][4:-1])
                        curPkgName = contents[i][4:-1]
                        i += 1
                        if curPkgName == pkgName:
                            return repoName
                # repoDir[repoName] = []
                # for item in pkgList:
                #     repoDir[repoName].append(item)

    return pkgName


def getGitFile(targetPkg):
    pkgInfo = list()
    pkgName = ""
    for version in VERSION:
        verData = ROSDATA + version
        pkginfo = verData + "/pkgInfo.txt"
        with open(pkginfo, 'r') as f:
            contents = f.readlines()

            for i in range(len(contents)):
                if not contents[i].startswith("    "):
                    pkgName = contents[i][2:-2]
                    if pkgName == targetPkg:
                        gitUrl = contents[i + 7]
                        break
    if not gitUrl.startswith("    Checkout"):
        print(f"{targetPkg} cannot find git file")
        sys.exit(1)
    lists = gitUrl.split("/")
    git = lists[-1][:-5]
    return git

def splitInfoStr(infoList):
    pkgDir = {}
    for info in infoList:
        items = info.split(': ')
        pkgDir[items[0]] = items[1][:-1]
    return pkgDir


def getPkgInfo(targetPkg):
    pkgInfo = list()
    pkgName = ""
    for version in VERSION:
        verData = ROSDATA + version
        pkginfo = verData + "/pkgInfo.txt"
        with open(pkginfo, 'r') as f:
            contents = f.readlines()

            for i in range(len(contents)):
                if not contents[i].startswith("    "):
                    pkgName = contents[i][2:-2]
                    if pkgName == targetPkg:
                        for j in range(10):
                            pkgInfo.append(contents[i + j + 1][4:])
                        break
    return pkgInfo


def getPkgDep(targetPkg):
    dir = {}
    for version in VERSION:
        verData = ROSDATA + version
        pkgdeps = verData + "/pkgDeps.txt"
        with open(pkgdeps, 'r') as f:
            contents = f.readlines()
            for i in range(len(contents)):
                if not contents[i].startswith("    "):
                    pkgName = contents[i][2:-3]
                    if pkgName == targetPkg:
                        i += 1
                        tagName = ""
                        depsList = list()

                        while True:
                            if contents[i].endswith(':\n'):
                                if tagName:
                                    dir[tagName] = depsList
                                tagName = contents[i][4:-2]
                                depsList = list()
                            else:
                                con = contents[i]
                                depsList.append(contents[i][6:-1])
                            i += 1
                            if i == len(contents) or not contents[i].startswith("    "):
                                dir[tagName] = depsList
                                break
                        return dir
    
    return dir
                    

def setLocal(depName):
    bash_command = f"bash -c 'source /home/qiguanxiao/ws/dependencies/{depName}/install/local_setup.bash && env'"
    try:
        result = subprocess.run(bash_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode('utf-8')
        # 解析输出的环境变量，格式通常是VAR=VALUE的形式，每行一个
        env_vars = {}
        for line in output.splitlines():
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
        # 将解析出的环境变量设置到Python的os.environ中
        # env = os.environ
        # print(env)
        os.environ.update(env_vars)
        
        print(f"set environment successfully: {depName}\n")
    except subprocess.CalledProcessError as e:
        print("failed set environment:  ", e.stderr.decode('utf-8'))


def mkdirAndGitClone(pkgName, wsName, dep):
    targetPkgInfo = getPkgInfo(pkgName)

    repo = getRepo(pkgName)

    if len(targetPkgInfo) == 0:
            print(f"no target pkg:  {pkgName}")
            return False
    
    # input ws name
    if dep == 0:
        curWs = f"{WS}/{wsName}"
    # inner dep ws name 
    else:
        curWs = f"{DEPENDENTPKGS}/{wsName}"

    pkgInfoDir = splitInfoStr(targetPkgInfo)


    mkdirCmd = f"mkdir {curWs}; cd {curWs}; mkdir src; cd src"
    
    gitUrl = pkgInfoDir.get("Checkout URI")
    gitBranch = pkgInfoDir.get("VCS Version")
    gitCmd = f"git clone {gitUrl} -b {gitBranch};"
    

    # check target src file has been existed
    srcFile = curWs + "/src"
    if os.path.exists(srcFile):
        if os.listdir(srcFile):
            # not empty do nothing 
            print("do not need change")
            return True
        else:
            mkdirCmd = f"cd {curWs}; cd src"
        

    result = subprocess.run(f"{mkdirCmd}; {gitCmd}", shell=True)
    

    # failed clone 
    if not os.listdir(f"{curWs}/src"):
        print("src files not correct")
        return False
    return True


def buildTask(wsName, dep, cmakeArgs = None):
    if dep == 0:
        curWs = f"{WS}/{wsName}"
    else:
        curWs = f"{DEPENDENTPKGS}/{wsName}"
    buildCmd = f"cd {curWs}; colcon build"
    if wsName == "ws_moveit2":
        buildCmd = f"cd {curWs}; colcon build --packages-skip-regex moveit_planners_ompl --cmake-args -DCMAKE_BUILD_TYPE=Release"
    result = subprocess.run(f"{buildCmd}", shell=True)


def checkInstalled(depName):
    # mkdir dir with the name of its repo
    wsName = getRepo(depName)
    # installed in the dep dir
    curDep = DEPENDENTPKGS + f"/{wsName}/install"
    if not os.path.exists(curDep):
        # totally not exist
        if mkdirAndGitClone(depName, wsName, 1):
            buildTask(wsName, 1)
            setLocal(wsName)
            return True
    else:
        setLocal(wsName)
        return True
    return False


def checkDep(curDepGraDataDir, depPkgName, path, num):
    

    # print("debug here 1")
    bash_command = "env"
    result1 = subprocess.run(bash_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    env = result1.stdout.decode('utf-8')
    # print("debug here 2")
    deps = getPkgDep(depPkgName)
    # ros1 = getROS1Pkg()
    # print("debug here 3")
    # print(depPkgName)
    # print(output)
    # print(depPkgName)

    curPath = f"/{depPkgName}/"
    curPath2 = f"/{depPkgName}:"


    # srcDir = f"/home/qiguanxiao/ws/ws_{path[0]}/"
    # epo = getRepo(depPkgName)

    # newDir = getRepo(depPkgName)
    # if len(path) == 1:
    #     cmd = f"cd {srcDir}; rosdep keys --from-paths src"
    # else:
    #     # this package does not originally exist
    #     # if not os.path.exists(f"/home/qiguanxiao/ws/ws_{path[0]}/src/{path[0]}/{depPkgName}"):
    #     if not depPkgName in dirList:
    #         srcDir = f"/home/qiguanxiao/ws/dependencies/{repo}/"
    #     cmd = f"cd {srcDir}/src/{repo}; rosdep keys --from-paths {depPkgName}"

    # if not os.path.exists(srcDir):
    #     if curPath not in env and curPath2 not in env:
    #         print(depPkgName)
    #         print(srcDir)
    #         mkdirAndGitClone(depPkgName, repo, 1)
    # every package 
    
    # result2 = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # output = result2.stdout.decode('utf-8')
    # deps = output.split("\n")
    # if depPkgName in ROS1:
    #     depPkgName = ROS1[depPkgName]

    

    curTxt = f"{curDepGraDataDir}/{num}.txt"
    if curPath not in env and curPath2 not in env:
        # not self pkg
        # print("debug here 2")
        with open(curTxt, 'a') as f:
            #f.write("not in environment \n")
            f.write('\n')
            for i in range(len(path)):
                #print(path[i])
                f.write(path[i])
                if path[i] == "catkin":
                    print("here1")
                if not i == len(path) - 1:
                    f.write(" -> ")
                    
            f.write("\n")
    else:
        return
    
    # print(path)
    if len(deps) == 0:
        # with open(curTxt, 'a') as f:
        #     f.write("len path == 0 \n")
        #     for i in range(len(path)):
        #         f.write(path[i])
        #         if not i == len(path) - 1:
        #             f.write(" -> ")
                    
        #     f.write("\n")
        return
    
    curDeps = deps["Package Dependencies"]
    
    # sysList = getDepSystems()

    for depPkg in curDeps:
        if depPkg == "rtcm_msgs":
            print("here")
        if depPkg in path:
            continue
        if not depPkg:
            continue
        if depPkg in ROS1:
            continue
        path.append(depPkg)
        # if depPkg == "catkin":
        #     print("here")
        # if depPkg == "message_runtime":
        #     print("here")
        # if depPkg == "message_generation":
        #     print("here")
        checkDep(curDepGraDataDir, depPkg, path, num)
        path.pop()
    

def addDepEnv(pkgName, depList, curWs, num):
    # with open(depGra, 'r') as f:
    #     contents = f.readlines()
    ifContinue = False
    depList = reversed(depList)
    git = getGitFile(pkgName)
    dirs = getAllOriDir(f"{curWs}/src/")
    for layer in depList:
        # depRelations = line.split('->')
        for missPkg in layer:
        #missPkg = depRelations[-1].strip()
            print(f"{num} times, start with {missPkg}\n")
            targetPkgInfo = getPkgInfo(missPkg)
            repo = getRepo(missPkg)
            # targetPkgPath = f"{curWs}/src/{git}/{missPkg}"
            # if missPkg == "roscpp":
            #     print(missPkg)
            # the package is in the root dir
            # if os.path.exists(targetPkgPath):
            if missPkg in dirs:
                # print(curWs)
                continue
            if repo == pkgName:
                continue
            # if missPkg in ROS1:
            #     ifContinue = True
            #     checkInstalled(ROS1[missPkg])
            #     break
            if len(targetPkgInfo) == 0:
                continue
            else:
                ifContinue = True
                checkInstalled(missPkg)
    print("\n")
    return ifContinue


def autoBuild(pkgName, workSpace):


    curWs = f"/home/qiguanxiao/ws/{workSpace}"

    print(" ***** start mkdir and git clone ***** ")
    while not mkdirAndGitClone(pkgName, workSpace, 0):
        continue
    print(" ***** end mkdir and git clone ***** \n")


    print(" ***** start check dependences ***** ")
    oriFile = getGitFile(pkgName)
    path = [f"{oriFile}"]
    ifContinue = True
    num = 1
    curDepGraDataDir = f"{DEPGRAPHDATA}/{pkgName}/"

    if os.path.exists(curDepGraDataDir):
        shutil.rmtree(curDepGraDataDir)
    os.mkdir(curDepGraDataDir)

    # dirList = getAllOriDir(curWs)
    # ros1 = getROS1Pkg()
    while ifContinue:

        print("checking and getting dep data")
        checkDep(curDepGraDataDir, pkgName, path, num)
        depList = getPicture(pkgName, curDepGraDataDir, num)
        # print(depList)
        print("adding dep")
        ifContinue = addDepEnv(pkgName, depList, curWs, num)
        num += 1
    print(" ***** end check dependences ***** \n")
    
    # if os.path.exists(curWs):
    #     shutil.rmtree(curWs)
    
    # checkDepsCmd = f"cd {curWs}; rosdep install -i --from-path src --rosdistro humble -y"
    
    # result = subprocess.run(f"{checkDepsCmd}", shell=True)

    # print(" ***** start set local ***** \n")
    # setLocal()
    # print(" ***** end set local ***** \n")


    
    print(" ***** start build ***** ")
    buildTask(workSpace, 0)
    print(" ***** end build ***** \n")


def getROS1Pkg():
    noeticPkg = getPkglist("/home/qiguanxiao/Desktop/work/data/rosData/noetic/rosPkg.txt")

    humblePkg = getPkglist("/home/qiguanxiao/Desktop/work/data/rosData/humble/rosPkg.txt")

    file = "./differenct.txt"
    # if os.path.exists(file):
    #     os.remove(file)
    totalDif = list()

    for pkg in humblePkg:
        deps = getPkgDep(pkg)
        depList = deps["Package Dependencies"]
        difList = list()
        for val in depList:
            if val not in humblePkg and val in noeticPkg:
                difList.append(val)
                if val not in totalDif:
                    totalDif.append(val)
        # if not len(difList) == 0:
        #     with open(file, 'a') as f:
        #         f.write(f"  {pkg}:\n")
        #         for item in difList:
        #             f.write(f"    {item}\n")
    
    # totalRepo = list()
    # with open(file, 'a') as f:
    #             f.write(f"  totalPkg:\n")
    #             for item in totalDif:
    #                 repo = getRepo(item)
    #                 if repo not in totalRepo:
    #                     totalRepo.append(repo)
    #                 f.write(f"    {item}    ")
    #                 f.write(f"    {repo}    \n")

    # with open(file, 'a') as f:
    #             f.write(f"  totalRepo:\n")
    #             for item in totalRepo:
    #                 f.write(f"    {item}\n")

    return totalDif


def getDepSystems():
    file = ROSDATA + "./systemDeps.txt"
    if os.path.exists(file):
        os.remove(file)
    
    sysList = list()
    with open(PKGDEPS, 'r') as f:
        contents = f.readlines()
        for i in range(len(contents)):
            if contents[i].startswith("    System"):
                i += 1

                while True:
                    if not contents[i].endswith(':\n'):
                        sys = contents[i][6:-1]
                        if not sys in sysList:
                            sysList.append(sys)
                    else:
                        break
                    i += 1

    return sysList




if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--pkgName', type=str)
    # parser.add_argument(
    #     '--cmake-args', 
    #     type=str, 
    #     nargs='*',  # 允许多个参数
    #     help='Pass arguments to CMake, e.g., -DCMAKE_BUILD_TYPE=Release'
    # )
    # parser.add_argument('-d', type=str)
    args = parser.parse_args()
    pkgName = args.pkgName

    # if args.cmake_args:
    #     cmake_args = ' '.join(args.cmake_args)  # 将所有的 CMake 参数连接成一个字符串
    #     # print(f"Running CMake with arguments: {cmake_args}")
    # else:
    #     print("No CMake arguments provided.")

    # dir = args.d

    # pkgName = "ublox"
    git = getGitFile(pkgName)
    dir = f"ws_{git}"
    
    # dir = f"ws_moveit2"
    # path = [f"{pkgName}"]
    # curDepGraDataDir = f"{DEPGRAPHDATA}/{pkgName}/"
    # getPicture(pkgName, curDepGraDataDir, 1)
    # getDifference()
    # checkDep(pkgName, path)
    # addDepEnv(pkgName, DEPGRAPH)
    # checkDep(pkgName, path)
    # buildTask(dir, 0)
    autoBuild(pkgName, dir)
    # getAllOriDir("/home/qiguanxiao/ws/ws_moveit2")
    # getDepSystems()

    
    
