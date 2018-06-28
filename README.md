# cbweb
一个基于tornado的web开发框架

## 环境要求
* Git
* Python 3.6.4
* Tornado 4.4.3
* Pyenv 1.2
## 准备工作
0. 安装基础扩展
`yum -y install zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel xz-devel libcurl-devel`

1. 使用Pyenv构建 Python3 环境，相关资料
[Pyenv说明][1][1]: https://zhuanlan.zhihu.com/p/27294128
[离线安装Python版本][2][2]: https://www.zhihu.com/question/49371634


2. 使用Git下载本基础框架

3. 配置环境变量
新增如下环境变量值`~/.bash_profile`文件中

`export PYCURL_SSL_LIBRARY=nss`
`export PYENV_LIBS_ROOT="$HOME/pylibs-7-36"`

将`PYENV_LIBS_ROOT`添加至PATH变量中
`export PATH="$PYENV_ROOT/bin:$PYENV_LIBS_ROOT:$PATH"`

修改完成后，`source ~/.bash_profile`

4. 安装依赖包
新建目录并将项目中的文件`requirements-3.6.txt`复制到`pylibs-7-36`中
`$ mkdir /path/to/your/pylibs-7-36 && cd /path/to/your/pylibs-7-36`

进入该目录，执行如下命令
`pip install -r requirements-3.6.txt -i https://pypi.douban.com/simple/ -t /path/to/your/pylibs-7-36/`

## 框架说明
```
.
├── bin                 # 启动服务
├── etc                 # 配置文件
├── biz                 # web-http业务
└── websock             # web-socket业务
├── jobs                # 定时任务业务
├── msg                 # 异步消息业务
├── tests               # 单元测试代码 
├── lib                 # 框架类库
├── log                 # 日志
```

## 启动服务
进入项目bin目录，启动相关服务
`cd /path/to/your/cbweb/`

启动http服务
`python ./bin/appsvr.py -c ./etc/app.json -p 8000`

启动websocket服务
`python ./bin/websocksvr.py -c ./etc/msg.json -p 8001`

启动任务服务
`python ./bin/jobsvr.py -c ./etc/jobsvr.json`

启动消息服务
`python ./bin/msgsvr.py -c ./etc/msgsvr.json`
