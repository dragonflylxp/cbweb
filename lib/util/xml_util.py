# coding: utf-8
"""XML Utilities
"""
import re
from xml.dom import minidom

from lxml import etree


def parse_string(s):
    """把字符串解析成minidom
    """
    if s[:5] == '<?xml':
        ss = s.split('?>', 1)
        m = re.search(r'encoding=\W([\w\-]+)\W', ss[0])
        if m:
            s = ss[1].decode(m.group(1)).encode('utf8')
        else:
            s = ss[1]
    return minidom.parseString(s)


def parse_file(fname):
    """把文件解析成minidom
    """
    f = open(fname, 'r')
    s = f.read()
    f.close()
    return parse_string(s)


def parse_to_dict(s, encoding='utf8', xlist=False):
    """把minidom解析成dict
        s           字符串
        encoding    输出dict的字符集
        xlist       重复的xpath合并成list
    """
    dom = parse_string(s)
    data = dom_to_dict(dom, encoding, xlist=xlist)
    dom.unlink()
    return data


def dom_to_dict(node, encoding='utf8', data=None, xlist=False):
    """把minidom解析成dict
        node        minidom当前节点
        encoding    输出dict的字符集
        data        dict的当前节点
        xlist       重复的xpath合并成list
    """
    if data == None:
        data = {}
    if node.nodeType == node.DOCUMENT_NODE:
        dom_to_dict(node.firstChild, encoding, data, xlist)
        return data
    d = {}
    if node.hasChildNodes():
        for i in node.childNodes:
            if i.nodeType == i.TEXT_NODE:
                if d.has_key('<text>'):
                    d['<text>'] += i.nodeValue.encode(encoding)
                else:
                    d['<text>'] = i.nodeValue.encode(encoding)
            elif i.nodeType == i.ELEMENT_NODE:
                dom_to_dict(i, encoding, d, xlist)
    if node.hasAttributes():
        d['<attrs>'] = dict([(i[0].encode(encoding), i[1].encode(encoding))
                                for i in node.attributes.items()])
    node_name = node.nodeName.encode(encoding)
    if not xlist or not data.has_key(node_name):
        data[node_name] = d
    elif type(data[node_name]) is list:
        data[node_name].append(d)
    else:
        data[node_name] = [data[node_name], d]


xml_encoding_pattern = re.compile(r'<\?xml[^\?]+encoding=\W([\w\-]+)\W[^\?]*\?>', re.I)
def parse_xml(xml):
    """分析xml，返回dom
    """
    match = xml_encoding_pattern.search(xml)
    if match and match.group(1).lower()[:2] == 'gb':
        xml = xml.split('?>', 1)[-1].decode('gb18030')
    elif not match:
        try:
            xml = xml.decode('utf8')
        except Exception as ex:
            pass
    return etree.XML(xml)

