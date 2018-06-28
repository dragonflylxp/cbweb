# coding: utf-8

import json
import traceback
import pika

from util import pika_pool
from util.tools import Log
from util.configer import JsonConfiger

logger = Log().getLog()

# 配置初始化
config = {}

# 生产者池
producer_pool = None

# 注册消息处理回调
ROUTING_TO_BIND = []
callbacks = {}


# 注册回调函数
def subscribe_callback_register(queue, routing_key=None):
    if not routing_key:
        routing_key = queue
    def decorator(func):
        if queue not in ROUTING_TO_BIND:
            ROUTING_TO_BIND.append({
                'queue': queue,
                'routing_key': routing_key,
            })
            callbacks[routing_key] = func
        else:
            logger.warning(f"[Queue:{queue}] already registered!")
        return func

    return decorator


def set_up(confs):
    config.update(confs.get("backends/rabbitmq/msgbus"))


def attach(ioloop):
    global tornado_ioloop
    tornado_ioloop = ioloop
    rabbitmq_subscribe(ROUTING_TO_BIND)
    create_producer_pool()


def rabbitmq_subscribe(bind_info):
    if isinstance(bind_info, dict):
        bind_info = [bind_info]
    # 队列监听
    # 消息消费者生成
    for info in bind_info:
        num = config['consumer_num'].get(info['queue'], 1)
        for n in range(num):
            RabbitMQConsumer(queue=info['queue'], custom_ioloop=tornado_ioloop, routing_key=info['routing_key']).run()


def create_producer_pool():
    global producer_pool, config
    if not config:
        config = JsonConfiger.get_instance().get("backends/rabbitmq/msgbus")
    params = pika.ConnectionParameters(host=config['host'], port=config['port'])

    producer_pool = pika_pool.QueuedPool(
        create=lambda: pika.BlockingConnection(parameters=params),
        max_size=10,
        max_overflow=10,
        timeout=10,
        recycle=3600,
        stale=45,
    )
    logger.info(f"Producer pool created")

def sub_callback(queue, msg):
    """订阅消息回调
       格式：Message(kind=u'message',
                     channel=u'channel#name',
                     body=u'bodystr',
                     pattern=u'channel#name')
    """
    try:
        callbacks[queue](queue, msg)
    except Exception:
        logger.error(traceback.format_exc())


def broadcast(msg, exchange='message'):
    """广播
    """
    if not producer_pool:
        create_producer_pool()
    with producer_pool.acquire() as conn:
        for queue in ROUTING_TO_BIND:
            conn.channel.queue_declare(queue=queue, durable=True)
            conn.channel.basic_publish(
                body=json.dumps(msg),
                exchange=exchange,
                routing_key=queue,
                properties=pika.BasicProperties(
                    content_type='application/json',
                    content_encoding='utf-8',
                    delivery_mode=2,
                )
            )


def send(queue, msg, routing_key=None, exchange='message'):
    """发消息
    """
    if not producer_pool:
        create_producer_pool()
    with producer_pool.acquire() as conn:
        conn.channel.queue_declare(queue=queue, durable=True)
        conn.channel.basic_publish(
            body=json.dumps(msg),
            exchange=exchange,
            routing_key=queue if not routing_key else routing_key,
            properties=pika.BasicProperties(
                app_id=f'{queue}-publisher',
                content_type='application/json',
                content_encoding='utf-8',
                delivery_mode=2,
            )
        )


class RabbitMQConsumer(object):
    """RabbitMQ消息消费者
    message 定义为消息交换机，以后若增加不同类型交换机需启动多个消费者
    """

    def __init__(self, exchange='message', exchange_type='topic', queue='', routing_key='#', custom_ioloop=None):
        """初始化"""
        self.host = config['host']
        self.port = config['port']
        self.exchange = exchange
        self.exchange_type = exchange_type
        self.queue = queue
        self.routing_key = routing_key
        self.custom_ioloop = custom_ioloop
        self._connection = None
        self._channel = None
        self._deliveries = []
        self._consumer_tag = None
        self._acked = 0
        self._nacked = 0
        self._message_number = 0
        self._stopping = False
        self._url = None
        self._closing = False

    def connect(self):
        """连接到rabbitmq服务器建立连接，关联tornado主服务的ioloop"""
        logger.debug(f"Consumer connecting to rabbitmq server [{self.host}:{self.port}]")
        return pika.adapters.TornadoConnection(pika.ConnectionParameters(host=self.host, port=self.port),
                                               on_open_callback=self.on_connection_open,
                                               stop_ioloop_on_close=False,
                                               custom_ioloop=self.custom_ioloop)

    def close_connection(self):
        """断开到rabbitmq的连接"""
        logger.info("Closing connection")
        self._connection.close()

    def add_on_connection_close_callback(self):
        """意外关闭连接的回调
        """
        self._connection.add_on_close_callback(self.on_connection_closed)

    def on_connection_closed(self, connection, reply_code, reply_text):
        """意外断开连接则尝试重连
        :param pika.connection.Connection connection: The closed connection obj
        :param int reply_code: The server provided reply_code if given
        :param str reply_text: The server provided reply_text if given
        """
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            logger.warning(f"Connection closed, reopening in 5 seconds: ({reply_code}) {reply_text}")
            self._connection.add_timeout(5, self.reconnect)

    def on_connection_open(self, unused_connection):
        """RabbitMQ连接建立回调， unused_connection为建立的连接
        :type unused_connection: pika.SelectConnection
        """
        self.add_on_connection_close_callback()
        self.open_channel()

    def reconnect(self):
        """重连"""
        if not self._closing:
            self._connection = self.connect()

    def add_on_channel_close_callback(self):
        """channel关闭回调
        """
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reply_code, reply_text):
        """channel关闭
        :param pika.channel.Channel channel: The closed channel
        :param int reply_code: The numeric reason the channel was closed
        :param str reply_text: The text reason the channel was closed

        """
        logger.warning(f"Channel[{channel}] was closed:({reply_code}) {reply_text}")
        self._connection.close()

    def on_channel_open(self, channel):
        """打开channel， 注册交换机
        :param pika.channel.Channel channel: The channel object
        """
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_exchange(self.exchange)

    def setup_exchange(self, exchange_name):
        """注册交换机
        :param str|unicode exchange_name: The name of the exchange to declare
        """
        self._channel.exchange_declare(self.on_exchange_declareok, exchange_name, self.exchange_type)

    def on_exchange_declareok(self, unused_frame):
        """交换机注册成功回调
        :param pika.Frame.Method unused_frame: Exchange.DeclareOk response frame

        """
        self.setup_queue(self.queue)

    def setup_queue(self, queue_name):
        """建立队列
        :param str|unicode queue_name: The name of the queue to declare.
        """
        self._channel.queue_declare(self.on_queue_declareok, queue_name, durable=True)

    def on_queue_declareok(self, method_frame):
        """队列创建成功回调
        :param pika.frame.Method method_frame: The Queue.DeclareOk frame
        """
        logger.info(f"Binding exchange[{self.exchange}] to queue[{self.queue}] with routing_key[{self.routing_key}]")
        self._channel.queue_bind(self.on_bindok, self.queue, self.exchange, self.routing_key)

    def add_on_cancel_callback(self):
        """撤销消费者
        """
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        """消费者被撤销则关闭连接
        :param pika.frame.Method method_frame: The Basic.Cancel frame

        """
        logger.info(f"Consumer was cancelled remotely, shutting down: {method_frame}")
        if self._channel:
            self._channel.close()

    def acknowledge_message(self, delivery_tag):
        """确认收到消息
        :param int delivery_tag: The delivery tag from the Basic.Deliver frame
        """
        self._channel.basic_ack(delivery_tag)

    def on_message(self, unused_channel, basic_deliver, properties, body):
        """收到并处理消息的主逻辑
        """
        logger.info(f"Received message # {basic_deliver.delivery_tag} from {properties.app_id}: {json.loads(body)}")
        self.acknowledge_message(basic_deliver.delivery_tag)
        sub_callback(self.queue, body)

    def on_cancelok(self, unused_frame):
        """确认干掉消费者
        :param pika.frame.Method unused_frame: The Basic.CancelOk frame
        """
        self.close_channel()

    def stop_consuming(self):
        """干掉消费者
        """
        if self._channel:
            logger.info("Sending a Basic.Cancel RPC command to RabbitMQ")
            self._channel.basic_cancel(self.on_cancelok, self._consumer_tag)

    def start_consuming(self):
        """开始监听
        """
        self.add_on_cancel_callback()
        logger.info(f"consumer[{self.queue}]Start consuming...")
        self._channel.basic_qos(prefetch_count=1)   # 最大接受任务数量
        self._consumer_tag = self._channel.basic_consume(self.on_message, self.queue)

    def on_bindok(self, unused_frame):
        """绑定成功
        :param pika.frame.Method unused_frame: The Queue.BindOk response frame
        """
        self.start_consuming()

    def close_channel(self):
        """关闭channel
        """
        self._channel.close()

    def open_channel(self):
        self._connection.channel(on_open_callback=self.on_channel_open)

    def run(self):
        """消费者启动连接并运行
        """
        self._connection = self.connect()
        # 此处仅建立连接，跟随tornado主服务ioloop的start来启动
        # self._connection.ioloop.start()

    def stop(self):
        logger.info("Stopping...")
        self._closing = True
        self.stop_consuming()
        self._connection.ioloop.start()
        logger.info("Stopped")
