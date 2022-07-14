import numpy as np
import copy
from multicast_method import simple_multicast
from mesh_hetero import *
from matplotlib import pyplot as plt
from basicParam_noc_nop import *

degrade_ratio_list = []
excel_datas = []

def setmappingSet(height, lenth, set1, set2):
    num = height * lenth
    assert(num == set1 * set2)
    list1 = {}
    list2 = {}
    node_list = []
    ID = 0
    for i in range(num):
        if i % lenth == 0:
            ID += 1
        node_list.append(ID)
        ID += 1
    print(node_list)
    for i in range(num):
        set1_id = i // set2
        if set1_id not in list1:
            list1[set1_id] = []
        list1[set1_id].append(node_list[i])

    for i in range(num):
        set2_id = i // set1
        if set2_id not in list2:
            list2[set2_id] = []
        list2[set2_id].append(list1[i % set1][set2_id])

    print(list1, list2)
    return list1, list2

def cal_degrade_ratio(HW_param, NoC_param, topology, set_act, set_wgt, set_out, act_bw, wgt_bw, if_multicast = True, debug = False, ol2_node = 0, al2_node = [5, 5, 5, 5], wl2_node = 10):
    route_table = NoC_param["route_table"]
    bw_scales = NoC_param["bw_scales"]
    F = NoC_param["F"]

    CoreNum = HW_param["PE"][0] * HW_param["PE"][1]
    PE_lenth = HW_param["PE"][1]
    PE_height = HW_param["PE"][0]

    F_cur = F.copy()
    print(al2_node)

    # 对act构建通信需求
    for i, act_transfer in enumerate(set_act.values()):
        if (if_multicast == False):
            for dst in act_transfer:
                # print('dst = ', dst)
                for link in route_table[(al2_node[i] + 1000, dst + 1000)]:
                    if debug:
                        print(al2_node[i] + 1000, dst + 1000)
                        print(link)

                    F_cur[link] += ( act_bw / bw_scales[link] )
        else :
            link_set = simple_multicast(al2_node[i] + 1000, [dst + 1000 for dst in act_transfer], route_table) 
            for link in link_set:
                if debug:
                    print(al2_node[i] + 1000, act_transfer)
                    print(link)

                F_cur[link] += ( act_bw / bw_scales[link] )

    # 对wgt构建通信需求
    for wgt_transfer in set_wgt.values():
        if (if_multicast == False):
            for dst in wgt_transfer:
                for link in route_table[(wl2_node + 1000, dst + 1000)]:
                    if debug:
                        print(wl2_node + 1000, dst + 1000)
                        print(link)

                    F_cur[link] += ( wgt_bw / bw_scales[link] )
        
        else:
            link_set = simple_multicast(wl2_node + 1000, [dst + 1000 for dst in wgt_transfer], route_table) 
            for link in link_set:
                if debug:
                    print(wl2_node + 1000, wgt_transfer)
                    print(link)

                F_cur[link] += ( wgt_bw / bw_scales[link] )
    
    # 对out构建通信需求
    out_bw = 1
    for out_transfer in set_out.values():
        for dst in out_transfer:					#写output不存在多播可能
            for link in route_table[(dst + 1000, ol2_node + 1000)]:
                if debug:
                    print(dst + 1000, ol2_node + 1000)
                    print(link)

                F_cur[link] += ( out_bw / bw_scales[link] )

    F_cur[(ol2_node, ol2_node + 1000)] = 0
    for al2 in al2_node:
        F_cur[(al2 + 1000, al2)] = 0
    F_cur[(wl2_node + 1000, wl2_node)] = 0

    if (max(F_cur.values()) < 1):
            degrade_ratio = 1
    else:
        degrade_ratio = max(F_cur.values()) 
        
    return degrade_ratio, F_cur

def check_topology():
    topology = 'RandomRouterless'
    HW_param = {"Chiplet":[1, 1], "PE":[4, 4], "intra_PE":{"C":8,"K":8}}
    act_wgt_group = [2, 8]
    Sample_Num = 20
    
    NoC_w = HW_param["PE"][1] + 1
    NOC_NODE_NUM = NoC_w * HW_param["PE"][0]
    NoP_w = HW_param["Chiplet"][1]
    NOP_SIZE = NoP_w * HW_param["Chiplet"][0]
    
    TOPO_param = {"NoC_w":NoC_w, "NOC_NODE_NUM": NOC_NODE_NUM, "NoP_w": NoP_w, "NOP_SIZE": NOP_SIZE,"nop_scale_ratio": nop_bandwidth/noc_bandwidth}

    if_multicast = True
    debug = False
    set_out = {0: [1,2,3,4, 6,7,8,9, 11,12,13,14, 16,17,18,19]}
    set_act, set_wgt = setmappingSet(4, 4, act_wgt_group[0], act_wgt_group[1])
    if debug:
        print('set_act = ', set_act)
        print('set_wgt = ', set_wgt)

    act_bw_array = np.linspace(2, 16, Sample_Num)
    wgt_bw_array = np.linspace(2, 16, Sample_Num)
    degrade_ratio_array = np.zeros((Sample_Num, Sample_Num))
    X, Y = np.meshgrid(act_bw_array, wgt_bw_array)

    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    ax.set_xlabel('act_bw')
    ax.set_ylabel('wgt_bw')
    ax.set_zlabel('degrade_ratio')
    
    plt.title('act_wgt_group = %s, topology = %s' % (str(act_wgt_group), topology))
    NoC_param, all_sim_node_num = construct_noc_nop_topo(TOPO_param["NOC_NODE_NUM"],TOPO_param["NoC_w"], TOPO_param["NOP_SIZE"],TOPO_param["NoP_w"], TOPO_param["nop_scale_ratio"], topology = topology)

    for j, act_bw in enumerate(act_bw_array):
        for k, wgt_bw in enumerate(wgt_bw_array):
            print('###### act_bw = %f, wgt_bw = %f ######' % (act_bw, wgt_bw))
            degrade_ratio, F_cur = cal_degrade_ratio(HW_param, NoC_param, topology, set_act, set_wgt, set_out, act_bw, wgt_bw, if_multicast, debug = debug)

            if debug:
                print('degrade_ratio = ', degrade_ratio)
                print("F_cur = ", F_cur)
            else:
                print('degrade_ratio = ', degrade_ratio)
            degrade_ratio_array[k, j] = degrade_ratio
    
    # Plot a basic wireframe.
    ax.plot_wireframe(X, Y, degrade_ratio_array)
    if debug:
        print(X)
        print(Y)
        print(degrade_ratio_array)

    plt.show()

def search_random(TOPO_param, HW_param, set_act, set_wgt, set_out, if_multicast, debug, ol2_node, al2_node, wl2_node):
    NoC_param, all_sim_node_num = construct_noc_nop_topo(TOPO_param["NOC_NODE_NUM"], TOPO_param["NoC_w"], TOPO_param["NOP_SIZE"],TOPO_param["NoP_w"], TOPO_param["nop_scale_ratio"], 'RandomRouterless', TOPO_param["NoC_w"] - 1)
    degrade_ratio, F_cur = cal_degrade_ratio(HW_param, NoC_param, 'RandomRouterless', set_act, set_wgt, set_out, 16, 16, if_multicast, debug, ol2_node, al2_node, wl2_node)
    
    return NoC_param, degrade_ratio

def search_random_singlethread(TOPO_param, HW_param, set_act, set_wgt, set_out, if_multicast, debug, ol2_node, al2_node, wl2_node):
    # find min RandomRouterless
    min_degrade_ratio = float('inf')
    for i in range(40):
        NoC_param, degrade_ratio = search_random(TOPO_param, HW_param, set_act, set_wgt, set_out, if_multicast, debug, ol2_node, al2_node, wl2_node)
        if (degrade_ratio < min_degrade_ratio):
            min_degrade_ratio = degrade_ratio
            min_NoC_param = NoC_param

        if degrade_ratio == min_degrade_ratio and len(NoC_param['Ring']) < len(min_NoC_param['Ring']):
            min_degrade_ratio = degrade_ratio
            min_NoC_param = NoC_param

    return min_NoC_param

def search_random_multithread(TOPO_param, HW_param, set_act, set_wgt, set_out, if_multicast, debug, ol2_node, al2_node, wl2_node):
    from multiprocessing import Process, Pipe

    class myProcess(Process):
        def __init__(self, processID, child_pipe, TOPO_param, HW_param, set_act, set_wgt, set_out, if_multicast, debug, ol2_node, al2_node, wl2_node):
            super().__init__()
            self.processID = processID
            self.child_pipe = child_pipe
            self.TOPO_param = TOPO_param
            self.HW_param = HW_param
            self.set_act = set_act
            self.set_wgt = set_wgt
            self.set_out = set_out
            self.if_multicast = if_multicast
            self.debug = debug 
            self.ol2_node = ol2_node 
            self.al2_node = al2_node 
            self.wl2_node = wl2_node 


        def run(self):
            NoC_param, degrade_ratio = search_random(self.TOPO_param, self.HW_param, self.set_act, self.set_wgt, self.set_out, self.if_multicast, self.debug, self.ol2_node, self.al2_node, self.wl2_node)
            self.child_pipe.send([NoC_param, float(degrade_ratio)])

    process_list = []
    parent_pipe_list = []
    parallel_thread = 50

    # simulator
    for i in range(parallel_thread):
        parent, child = Pipe()
        process_list.append(myProcess(i, child, TOPO_param, HW_param, set_act, set_wgt, set_out, if_multicast, debug, ol2_node, al2_node, wl2_node))
        parent_pipe_list.append(parent)
        process_list[i].start()


    # find min RandomRouterless
    min_degrade_ratio = float('inf')

    for i in range(parallel_thread):
        process_list[i].join()
        message = parent_pipe_list[i].recv()
        degrade_ratio = message[1]
        NoC_param = message[0]
        print(i, degrade_ratio)
        if (degrade_ratio < min_degrade_ratio):
            min_degrade_ratio = degrade_ratio
            min_NoC_param = NoC_param

        if degrade_ratio == min_degrade_ratio and len(NoC_param['Ring']) < len(min_NoC_param['Ring']):
            min_degrade_ratio = degrade_ratio
            min_NoC_param = NoC_param

    return min_NoC_param, min_degrade_ratio

def check_random():
    HW_param = {"Chiplet":[1, 1], "PE":[4, 4], "intra_PE":{"C":8,"K":8}}
    # Topology_list = ['Mesh', 'Torus', 'Routerless', 'Ring']
    # color_list = ['b', 'r', 'y', 'g']
    Topology_list = ['Mesh']
    color_list = ['b', 'r']
    Sample_Num = 20

    NoC_w = HW_param["PE"][1] + 1
    NOC_NODE_NUM = NoC_w * HW_param["PE"][0]
    NoP_w = HW_param["Chiplet"][1]
    NOP_SIZE = NoP_w * HW_param["Chiplet"][0]
    
    if_multicast = True
    debug = False
    act_wgt_group = [4, 4]
    set_act, set_wgt = setmappingSet(4, 4, act_wgt_group[0], act_wgt_group[1])
    set_out = {0: [0,1, 3,4, 5,6, 8,9, 10,11, 13,14, 15,16, 18,19]}
    ol2_node = A_W_offset['o']
    if A_W_offset['o'] == 0:
        al2_node = [A_W_offset['a']] * 4
    else:
        al2_node = [A_W_offset['a']] * 2 + [A_W_offset['a'] + NoC_w * 2] * 2 
    wl2_node = A_W_offset['w']

    TOPO_param = {"NoC_w":NoC_w, "NOC_NODE_NUM": NOC_NODE_NUM, "NoP_w": NoP_w, "NOP_SIZE": NOP_SIZE,"nop_scale_ratio": nop_bandwidth/noc_bandwidth, "ol2_node":ol2_node, "al2_node":al2_node, "wl2_node":wl2_node, }

    if debug:
        print('set_act = ', set_act)
        print('set_wgt = ', set_wgt)

    # min_NoC_param = search_random_singlethread(TOPO_param, HW_param, set_act, set_wgt, set_out, if_multicast, debug, ol2_node, al2_node, wl2_node)
    min_NoC_param, min_degrade_ratio = search_random_multithread(TOPO_param, HW_param, set_act, set_wgt, set_out, if_multicast, debug, ol2_node, al2_node, wl2_node)

    print(min_NoC_param['Ring'])
    print(min_degrade_ratio)
    print(min_NoC_param['route_table'])
    debug = False

    act_bw_array = np.linspace(2, 16, Sample_Num)
    wgt_bw_array = np.linspace(2, 16, Sample_Num)
    degrade_ratio_array = np.zeros((Sample_Num, Sample_Num))
    X, Y = np.meshgrid(act_bw_array, wgt_bw_array)

    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    ax.set_xlabel('act_bw')
    ax.set_ylabel('wgt_bw')
    ax.set_zlabel('degrade_ratio')
    plt.title('act_wgt_group = ' + str(act_wgt_group))

    for j, act_bw in enumerate(act_bw_array):
        for k, wgt_bw in enumerate(wgt_bw_array):
            print('###### act_bw = %f, wgt_bw = %f ######' % (act_bw, wgt_bw))
            degrade_ratio, F_cur = cal_degrade_ratio(HW_param, min_NoC_param, 'RandomRouterless', set_act, set_wgt, set_out, act_bw, wgt_bw, if_multicast, debug, ol2_node, al2_node, wl2_node)

            if debug:
                print('degrade_ratio = ', degrade_ratio)
                print("F_cur = ", F_cur)
            else:
                print('degrade_ratio = ', degrade_ratio)
            degrade_ratio_array[k, j] = degrade_ratio
        
    # Plot wireframe.
    ax.plot_wireframe(X, Y, degrade_ratio_array, color = 'black')

    # --- 生成noc-nop结构图
    for i, topology in enumerate(Topology_list):
        NoC_param, all_sim_node_num = construct_noc_nop_topo(TOPO_param["NOC_NODE_NUM"],TOPO_param["NoC_w"], TOPO_param["NOP_SIZE"],TOPO_param["NoP_w"], TOPO_param["nop_scale_ratio"], topology = topology)

        print('topology = ', topology)

        for j, act_bw in enumerate(act_bw_array):
            for k, wgt_bw in enumerate(wgt_bw_array):
                print('###### act_bw = %f, wgt_bw = %f ######' % (act_bw, wgt_bw))
                degrade_ratio, F_cur = cal_degrade_ratio(HW_param, NoC_param, topology, set_act, set_wgt, set_out, act_bw, wgt_bw, if_multicast, debug, ol2_node, al2_node, wl2_node)

                if debug:
                    print('degrade_ratio = ', degrade_ratio)
                    print("F_cur = ", F_cur)
                else:
                    print('degrade_ratio = ', degrade_ratio)
                degrade_ratio_array[k, j] = degrade_ratio
        
        # Plot wireframe.
        ax.plot_wireframe(X, Y, degrade_ratio_array, color = color_list[i])
        if debug:
            print(degrade_ratio_array)

    plt.legend(['RandomRouterless'] + [t for t in Topology_list], loc = 'best')
    plt.show()



def check_mesh():
    HW_param = {"Chiplet":[1, 1], "PE":[4, 4], "intra_PE":{"C":8,"K":8}}
    topology = 'Mesh'
    color_list = ['b', 'r', 'y', 'g']
    # act_wgt_group = [[1, 16], [2, 8], [4, 4], [8, 2], [16, 1]]
    act_wgt_group = [4, 4]
    Sample_Num = 20
    
    NoC_w = HW_param["PE"][1] + 1
    NOC_NODE_NUM = NoC_w * HW_param["PE"][0]
    NoP_w = HW_param["Chiplet"][1]
    NOP_SIZE = NoP_w * HW_param["Chiplet"][0]
    
    TOPO_param = {"NoC_w":NoC_w, "NOC_NODE_NUM": NOC_NODE_NUM, "NoP_w": NoP_w, "NOP_SIZE": NOP_SIZE,"nop_scale_ratio": nop_bandwidth/noc_bandwidth}

    if_multicast = True
    debug = False
    set_act, set_wgt = setmappingSet(4, 4, act_wgt_group[0], act_wgt_group[1])
    print('set_act = ', set_act)
    print('set_wgt = ', set_wgt)
    set_out = {0: [0,1, 3,4, 5,6, 8,9, 10,11, 13,14, 15,16, 18,19]}

    param = {'set_act': set_act, 'set_wgt': set_wgt, 'set_out': set_out, 'ol2_node': 0, 'al2_node': [5] * 16, 'wl2_node':10}
    Param_list = []
    Param_list.append(param)

    set_act = {0: [0, 1, 3, 4], 1: [5, 6, 8, 9], 2: [10, 11, 13, 14], 3: [15, 16, 18, 19]}
    set_wgt = {0: [0, 5, 10, 15], 1: [1, 6, 11, 16], 2: [3, 8, 13, 18], 3: [4, 9, 14, 19]}
    # set_act = {0: [0, 1, 3, 4, 5, 6, 8, 9], 1: [10, 11, 13, 14, 15, 16, 18, 19]}
    # set_wgt = {0: [0, 10], 1: [1, 11], 2: [3, 13], 3: [4, 14], 4: [5, 15], 5: [6, 16], 6: [8, 18], 7: [9, 19]}
    # set_act = {0: [0, 1, 3, 4, 5, 6, 8, 9, 10, 11, 13, 14, 15, 16, 18, 19]}
    # set_wgt = {0: [0], 1: [1], 2: [3], 3: [4], 4: [5], 5: [6], 6: [8], 7: [9], 8: [10], 9: [11], 10: [13], 11: [14], 12: [15], 13: [16], 14: [18], 15: [19]}
    # set_act = {0: [0, 1], 1: [3, 4], 2: [5, 6], 3: [8, 9], 4: [10, 11], 5: [13, 14], 6: [15, 16], 7: [18, 19]}
    # set_wgt = {0: [0, 5, 10, 15, 1, 6, 11, 16], 1: [3, 8, 13, 18, 4, 9, 14, 19]}
    # set_act = {0: [0], 1: [1], 2: [3], 3: [4], 4: [5], 5: [6], 6: [8], 7: [9], 8: [10], 9: [11], 10: [13], 11: [14], 12: [15], 13: [16], 14: [18], 15: [19]}
    # set_wgt = {0: [0, 5, 10, 15, 1, 6, 11, 16, 3, 8, 13, 18, 4, 9, 14, 19]}

    ol2_node = 2
    al2_node = [7, 7, 17, 17]
    # al2_node = [7, 17]
    # al2_node = [7, 7, 7, 7, 17, 17, 17, 17]
    # al2_node = [7, 7, 7, 7, 7, 7, 7, 7, 17, 17, 17, 17, 17, 17, 17, 17]
    wl2_node = 12

    param = {'set_act': set_act, 'set_wgt': set_wgt, 'set_out': set_out, 'ol2_node': ol2_node, 'al2_node': al2_node, 'wl2_node': wl2_node}
    Param_list.append(param)

    if debug:
        print('set_act = ', set_act)
        print('set_wgt = ', set_wgt)

    act_bw_array = np.linspace(2, 16, Sample_Num)
    wgt_bw_array = np.linspace(2, 16, Sample_Num)
    degrade_ratio_array = np.zeros((Sample_Num, Sample_Num))
    X, Y = np.meshgrid(act_bw_array, wgt_bw_array)

    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    ax.set_xlabel('act_bw')
    ax.set_ylabel('wgt_bw')
    ax.set_zlabel('degrade_ratio')
    plt.title('act_wgt_group = ' + str(act_wgt_group))

    # --- 生成noc-nop结构图
    for i, param in enumerate(Param_list):
        NoC_param, all_sim_node_num = construct_noc_nop_topo(TOPO_param["NOC_NODE_NUM"],TOPO_param["NoC_w"], TOPO_param["NOP_SIZE"],TOPO_param["NoP_w"], TOPO_param["nop_scale_ratio"], topology = topology)

        print('topology = ', topology)

        for j, act_bw in enumerate(act_bw_array):
            for k, wgt_bw in enumerate(wgt_bw_array):
                print('###### act_bw = %f, wgt_bw = %f ######' % (act_bw, wgt_bw))
                degrade_ratio, F_cur = cal_degrade_ratio(HW_param, NoC_param, topology, param['set_act'], param['set_wgt'], param['set_out'], act_bw, wgt_bw, if_multicast, debug, param['ol2_node'], param['al2_node'], param['wl2_node'])

                if debug:
                    print('degrade_ratio = ', degrade_ratio)
                    print("F_cur = ", F_cur)
                else:
                    print('degrade_ratio = ', degrade_ratio)
                degrade_ratio_array[k, j] = degrade_ratio
        
        # Plot wireframe.
        ax.plot_wireframe(X, Y, degrade_ratio_array, color = color_list[i])
        if debug:
            print(degrade_ratio_array)

    plt.legend(['SRAM on Left', 'SRAM on Middle'], loc = 'best')
    plt.show()



def noc_topology_explore():
    HW_param = {"Chiplet":[1, 1], "PE":[4, 4], "intra_PE":{"C":8,"K":8}}
    Topology_list = ['Mesh', 'Torus', 'CMesh']
    color_list = ['b', 'r', 'y', 'g']
    act_wgt_list = [[1, 16], [2, 8], [4, 4], [8, 2], [16, 1]]
    # act_wgt_group = [4, 4]
    Sample_Num = 20
    
    NoC_w = HW_param["PE"][1] + 1
    NOC_NODE_NUM = NoC_w * HW_param["PE"][0]
    NoP_w = HW_param["Chiplet"][1]
    NOP_SIZE = NoP_w * HW_param["Chiplet"][0]
    
    TOPO_param = {"NoC_w":NoC_w, "NOC_NODE_NUM": NOC_NODE_NUM, "NoP_w": NoP_w, "NOP_SIZE": NOP_SIZE,"nop_scale_ratio": nop_bandwidth/noc_bandwidth}

    if_multicast = True
    debug = False
    
    # set_act = {0: [1, 2, 3, 4], 1: [6, 7, 8, 9], 2: [11, 12, 13, 14], 3: [16, 17, 18, 19]}
    # set_wgt = {0: [1, 6, 11, 16], 1: [2, 7, 12, 17], 2: [3, 8, 13, 18], 3: [4, 9, 14, 19]}
    set_out = {0: [1,2,3,4, 6,7,8,9, 11,12,13,14, 16,17,18,19]}
    ol2_node = 0
    al2_node = [5] * 16
    wl2_node = 10

    if debug:
        print('set_act = ', set_act)
        print('set_wgt = ', set_wgt)

    act_bw_array = np.linspace(2, 16, Sample_Num)
    wgt_bw_array = np.linspace(2, 16, Sample_Num)
    degrade_ratio_array = np.zeros((Sample_Num, Sample_Num))
    X, Y = np.meshgrid(act_bw_array, wgt_bw_array)

    for act_wgt_group in act_wgt_list:
        fig = plt.figure()
        set_act, set_wgt = setmappingSet(4, 4, act_wgt_group[0], act_wgt_group[1])
        ax = fig.add_subplot(projection='3d')
        ax.set_xlabel('act_bw')
        ax.set_ylabel('wgt_bw')
        ax.set_zlabel('degrade_ratio')
        plt.title('act_wgt_group = ' + str(act_wgt_group))

        # --- 生成noc-nop结构图
        for i, topology in enumerate(Topology_list):
            NoC_param, all_sim_node_num = construct_noc_nop_topo(TOPO_param["NOC_NODE_NUM"],TOPO_param["NoC_w"], TOPO_param["NOP_SIZE"],TOPO_param["NoP_w"], TOPO_param["nop_scale_ratio"], topology = topology)

            print('topology = ', topology)

            for j, act_bw in enumerate(act_bw_array):
                for k, wgt_bw in enumerate(wgt_bw_array):
                    print('###### act_bw = %f, wgt_bw = %f ######' % (act_bw, wgt_bw))
                    degrade_ratio, F_cur = cal_degrade_ratio(HW_param, NoC_param, topology, set_act, set_wgt, set_out, act_bw, wgt_bw, if_multicast, debug, ol2_node, al2_node, wl2_node)

                    if debug:
                        print('degrade_ratio = ', degrade_ratio)
                        print("F_cur = ", F_cur)
                    else:
                        print('degrade_ratio = ', degrade_ratio)
                    degrade_ratio_array[k, j] = degrade_ratio
            
            # Plot wireframe.
            ax.plot_wireframe(X, Y, degrade_ratio_array, color = color_list[i])
            if debug:
                print(degrade_ratio_array)

        plt.legend([t for t in Topology_list], loc = 'best')
        plt.show()


if __name__ == '__main__':
    # noc_topology_explore()
    # check_topology()
    # check_random()
    check_mesh()
