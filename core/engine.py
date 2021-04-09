#!/usr/bin/env python
# -*- coding:utf-8 -*-
# author:owefsad
# datetime:2021/1/26 下午4:05
# software: PyCharm
# project: lingzhi-engine
import logging

from kombu.utils import cached_property

logger = logging.getLogger('dongtai-engine')


class VulEngine(object):
    """
    根据策略和方法池查找是否存在漏洞，此类不进行策略和方法池的权限验证
    """

    def __init__(self):
        """
        构造函数，初始化相关数据
        """
        self._method_pool = None
        self.method_pool_asc = None
        self._vul_method_signature = None
        self.hit_vul = False
        self.vul_stack = None
        self.pool_value = None
        self.vul_source_signature = None
        self.graphy_data = {
            'nodes': [],
            'edges': []
        }
        self.method_counts = 0
        self.taint_link_size = 0
        self.edge_code = 1

    @property
    def method_pool(self):
        """
        方法池数据
        :return:
        """
        return self._method_pool

    @method_pool.setter
    def method_pool(self, method_pool):
        """
        设置方法池数据，根据方法调用ID对数据进行倒序排列，便于后续检索漏洞
        :param method_pool:
        :return:
        """
        self._method_pool = sorted(method_pool, key=lambda e: e.__getitem__('invokeId'), reverse=True)

    @property
    def vul_method_signature(self):
        return self._vul_method_signature

    @vul_method_signature.setter
    def vul_method_signature(self, vul_method_signature):
        self._vul_method_signature = vul_method_signature

    def prepare(self, method_pool, vul_method_signature):
        """
        对方法池、漏洞方法签名及其他数据进行预处理
        :param method_pool: 方法池，list
        :param vul_method_signature: 漏洞方法签名，str
        :return:
        """
        self.method_pool = method_pool
        self.vul_method_signature = vul_method_signature
        self.hit_vul = False
        self.vul_stack = list()
        self.pool_value = -1
        self.vul_source_signature = ''
        self.method_counts = len(self.method_pool)

    def hit_vul_method(self, method):
        if f"{method.get('className')}.{method.get('methodName')}" == self.vul_method_signature:
            self.hit_vul = True
            # self.vul_stack.append(method)
            self.pool_value = method.get('sourceHash')
            logger.debug(f'==> current taint hash: {self.pool_value}')
            return True

    def do_propagator(self, method, current_link):
        is_source = method.get('source')
        target_hash = method.get('targetHash')

        for hash in target_hash:
            if hash in self.pool_value:
                if is_source:
                    current_link.append(method)
                    self.vul_source_signature = f"{method.get('className')}.{method.get('methodName')}"
                    return True
                else:
                    current_link.append(method)
                    logger.debug(f'=== taint hash propagator: {self.pool_value} > {method.get("sourceHash")}')
                    self.pool_value = method.get('sourceHash')
                    break

    @cached_property
    def method_pool_signatures(self):
        signatures = list()
        for method in self.method_pool:
            signatures.append(f"{method.get('className').replace('/', '.')}.{method.get('methodName')}")
        return signatures

    def search(self, method_pool, vul_method_signature):
        self.prepare(method_pool, vul_method_signature)
        size = len(self.method_pool)
        for index in range(size):
            method = self.method_pool[index]
            if self.hit_vul_method(method):
                current_link = list()
                current_link.append(method)
                for sub_method in self.method_pool[index + 1:]:
                    if self.do_propagator(sub_method, current_link):
                        self.vul_stack.append(current_link[::-1])
                        break

    def search_sink(self, method_pool, vul_method_signature):
        self.prepare(method_pool, vul_method_signature)
        if vul_method_signature in self.method_pool_signatures:
            return True

    def search_all_link(self):
        """
        从方法池中搜索所有的污点传播链
        :return:
        """
        self.edge_code = 1
        self.method_pool_asc = self.method_pool[::-1]
        self.create_node()
        self.create_edge()

    def create_edge(self):
        """
        创建污点链的边
        :return:
        """
        for index in range(self.method_counts):
            data = self.method_pool_asc[index]
            if data['source']:
                current_hash = set(data['targetHash'])
                left_node = str(data['invokeId'])
                self.dfs(current_hash, left_node, index)

    def dfs(self, current_hash, left_node, left_index):
        """
        深度优先搜索，搜索污点流图中的边
        :param current_hash: 当前污点数据，set()
        :param left_node: 上层节点方法的调用ID
        :param left_index: 上层节点方法在方法队列中的编号
        :return:
        """
        not_found = True
        for index in range(left_index + 1, self.method_counts):
            data = self.method_pool_asc[index]
            if current_hash & set(data['sourceHash']):
                not_found = False
                right_node = str(data['invokeId'])
                self.graphy_data['edges'].append({
                    'id': str(self.edge_code),
                    'source': left_node,
                    'target': right_node,
                })
                self.edge_code = self.edge_code + 1
                data['sourceHash'] = list(set(data['sourceHash']) - current_hash)
                self.dfs(set(data['targetHash']), right_node, index)

        if not_found:
            self.taint_link_size = self.taint_link_size + 1

    def create_node(self):
        """
        创建污点流图中使用的节点数据
        :return:
        """
        for data in self.method_pool_asc:
            source = ','.join([str(_) for _ in data['sourceHash']])
            target = ','.join([str(_) for _ in data['targetHash']])
            node = {
                'id': str(data['invokeId']),
                'name': f"{data['className'].replace('/', '.').split('.')[-1]}.{data['methodName']}({source}) => {target}",
                'dataType': 'source' if data['source'] else 'sql',
                'conf': [
                    {'label': 'source', 'value': source},
                    {'label': 'target', 'value': target},
                    {'label': 'caller', 'value': f"{data['callerClass']}.{data['callerMethod']}()"}
                ]
            }
            self.graphy_data['nodes'].append(node)

    def result(self):
        if self.vul_source_signature:
            return True, self.vul_stack, self.vul_source_signature, self.vul_method_signature
        return False, None, None, None

    def get_taint_links(self):
        return self.graphy_data, self.taint_link_size, self.method_counts
