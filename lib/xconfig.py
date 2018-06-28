# coding:utf-8
"""Easy Config
"""

import copy


class CfgData(object):
    """配置数据，主要为了实现类似JSON格式数据的ReadOnly。
    """

    def __init__(self, data):
        self._data = data

    def __getitem__(self, i):
        return self.deco_data(self._data[i])

    def __len__(self):
        return len(self._data)

    @classmethod
    def deco_data(cls, data):
        """修饰数据，如果是最基本的几个类型就不用修饰直接返回。
        """
        if data is None or isinstance(data, (str, int, float, unicode, bool)):
            return data
        else:
            return cls(data)


if __name__ == '__main__':
    d = CfgData({
        'a': {
            'b': [1, 2, 3],
        },
        'c': 'ccc',
    })
    print(d['a'], d['a']['b'], d['a']['b'][1], d['c'])
    print(len(d), len(d['a']['b']))
    d['a']['bb'] = 'asdf'

