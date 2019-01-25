import asyncio
import logging
import threading
from random import Random

import zmq
import zmq.asyncio
from concurrent.futures import ThreadPoolExecutor
import msgpack
from .defs import ext_pack, ext_unpack

logger = logging.getLogger('AsyncCommThread')
# logger.setLevel(logging.DEBUG)
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# ch = logging.StreamHandler()
# ch.setLevel(logging.DEBUG)
# ch.setFormatter(formatter)
# logger.addHandler(ch)

class AsyncCommunication(threading.Thread):
    def __init__(self, local_address = None, callback=None, identity=None):

        self._receive_callback = None
        self._identity = identity
        self._callback = callback
        self._local_address = local_address
        self._timeout = 1000
        self.running = False
        self._loop = asyncio.new_event_loop()
        self._executor = ThreadPoolExecutor(max_workers=10,
                                           thread_name_prefix='executor')
        self._loop.set_default_executor(self._executor)
        asyncio.set_event_loop(self._loop)
        self._context = zmq.asyncio.Context()
        self._poller = zmq.asyncio.Poller()

        name = 'AsyncCommThread'
        if identity:
            name = name + identity
        threading.Thread.__init__(self, name=name)
    def run(self):
        self.running = True
        server_future = asyncio.ensure_future(
            self._run_server(),
            loop=self._loop)
        try:
            self._loop.run_until_complete(server_future)
        finally:
            self._loop.close()

    async def _send(self, request, remote):
        try:
            p = msgpack.packb(request, default=ext_pack, strict_types=True, encoding='utf-8')
        except Exception as e:
            logger.error("Error packing {}".format(e))
            raise e

        try:
            if self._identity is not None:
                logger.info("identity is %s" % self._identity)
                identity = msgpack.packb(self._identity, encoding='utf-8', strict_types=True)
                try:
                    self._client.setsockopt(zmq.IDENTITY, identity)
                except zmq.ZMQError as zmqerror:
                    logger.error("Error setting socket identity. {}".format(zmqerror))
                    raise zmqerror

            self._client = self._context.socket(zmq.DEALER)
            # No lingering after socket is closed.
            # This has proven to cause problems terminating asyncio if not 0
            self._client.setsockopt(zmq.LINGER, 1000)
            socket_address = 'tcp://{}'.format(remote)
            logger.info("{} connecting to {}".format(self._local_address, socket_address))
            self._client.connect(socket_address)
            self._poller.register(self._client, zmq.POLLIN)
            logger.info('{} sending {} to {}'.format(self._local_address, request, socket_address))
            await self._client.send_multipart([p])
            self._poller.unregister(self._client)
            self._client.close()
        except zmq.ZMQError as zmqerror:
            logger.error("Error connecting client socket to address {}. {}".format(socket_address, zmqerror))
            raise zmqerror

    async def _run_server(self):
        assert self._local_address is not None, 'local_address not set'
        assert self._callback is not None, 'callback is not set'
        logger.debug('Server listening on address tcp://{}.'.format(self._local_address))

        self._server = self._context.socket(zmq.ROUTER)
        self._server.bind('tcp://{}'.format(self._local_address))
        self._poller.register(self._server, zmq.POLLIN)
        logger.info('running server on tcp://{}.'.format(self._local_address))
        while self.running:
            items = dict(await self._poller.poll(self._timeout))
            if self._server in items and items[self._server] == zmq.POLLIN:
                logger.debug("receiving at server")
                _, msg = await self._server.recv_multipart()
                try:
                    p = msgpack.unpackb(msg, ext_hook=ext_unpack, encoding='utf-8')
                    #ident = msgpack.unpackb(ident, encoding='utf-8')
                except Exception as e:
                    raise e
                logger.debug('server received {}'.format(p))
                await self._loop.run_in_executor(self._executor,
                                                self._callback,
                                                p)
        logger.info("stopping server")
        self._poller.unregister(self._server)
        self._server.close()

    def send(self, request, remote):
        logger.debug("send {} to {}".format(request, remote))
        asyncio.run_coroutine_threadsafe(
            self._send(request, remote=remote), self._loop)

    def stop(self):
        logger.info("Stopping AsyncCommThread")
        self.running = False
