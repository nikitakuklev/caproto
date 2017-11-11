import pytest
import time
import logging
import contextlib
import curio

import caproto as ca


ioc_handler = None
logger = logging.getLogger(__name__)


def setup_module():
    global ioc_handler

    import _asv_shim
    logging.basicConfig()
    logger.setLevel('DEBUG')
    _asv_shim.logger.setLevel('DEBUG')
    logging.getLogger('benchmarks.util').setLevel('DEBUG')
    logging.getLogger('caproto').setLevel('INFO')

    db_text = ca.benchmarking.make_database(
        {('wfioc:wf{}'.format(sz), 'waveform'): dict(FTVL='LONG', NELM=sz)
         for sz in (4000, 8000, 1000000, 2000000)
         },
    )

    ioc_handler = ca.benchmarking.IocHandler(logger=logger)
    ioc_handler.setup_ioc(db_text=db_text, max_array_bytes='10000000')
    # give time for the server to startup
    time.sleep(1.0)


def teardown_module():
    if ioc_handler is not None:
        ioc_handler.teardown()


@contextlib.contextmanager
def temporary_pyepics_access(pvname, **kwargs):
    import epics
    pv = epics.PV(pvname, **kwargs)
    assert pv.wait_for_connection(), 'unable to connect to {}'.format(pv)
    yield pv
    epics.ca.clear_cache()


@contextlib.contextmanager
def bench_pyepics_get_speed(pvname, initial_value=None):
    with temporary_pyepics_access(pvname) as pv:
        def pyepics():
            value = pv.get(use_monitor=False)
            if initial_value is not None:
                assert len(value) == len(initial_value)

        if initial_value is not None:
            pv.put(initial_value, wait=True)
        yield pyepics
        logger.debug('Disconnecting pyepics pv %s', pv)
        pv.disconnect()


@contextlib.contextmanager
def bench_threading_get_speed(pvname, initial_value=None):
    from caproto.threading.client import (PV, SharedBroadcaster,
                                          Context as ThreadingContext)

    shared_broadcaster = SharedBroadcaster()
    context = ThreadingContext(broadcaster=shared_broadcaster,
                               log_level='ERROR')

    def threading():
        value = pv.get(use_monitor=False)
        if initial_value is not None:
            assert len(value) == len(initial_value)

    pv = PV(pvname, auto_monitor=False, context=context)
    if initial_value is not None:
        pv.put(initial_value, wait=True)
    yield threading
    logger.debug('Disconnecting threading pv %s', pv)
    pv.disconnect()
    logger.debug('Disconnecting shared broadcaster %s', shared_broadcaster)
    shared_broadcaster.disconnect()
    logger.debug('Done')


@contextlib.contextmanager
def bench_curio_get_speed(pvname, initial_value=None):
    kernel = curio.Kernel()

    async def curio_setup():
        logger.debug('Registering...')
        broadcaster = ca.curio.client.SharedBroadcaster(log_level='ERROR')
        await broadcaster.register()
        ctx = ca.curio.client.Context(broadcaster, log_level='ERROR')
        logger.debug('Registered')

        logger.debug('Searching for %s...', pvname)
        await ctx.search(pvname)
        logger.debug('... found!')
        chan = await ctx.create_channel(pvname)
        await chan.wait_for_connection()
        logger.debug('Connected to %s', pvname)

        if initial_value is not None:
            logger.debug('Writing initial value')
            await chan.write(initial_value)
            logger.debug('Wrote initial value')
        logger.debug('Init complete')
        return chan

    def curio_client():
        async def get():
            reading = await chan.read()
            if initial_value is not None:
                assert len(reading.data) == len(initial_value)
        kernel.run(get())

    chan = kernel.run(curio_setup())

    assert chan.channel.states[ca.CLIENT] is ca.CONNECTED, 'Not connected'

    yield curio_client

    logger.debug('Shutting down the kernel')
    kernel.run(shutdown=True)
    logger.debug('Done')


@pytest.mark.parametrize('waveform_size', [4000, 8000, ])
@pytest.mark.parametrize('backend', ['pyepics', 'curio', 'threading'])
def test_waveform_get(benchmark, waveform_size, backend):
    pvname = 'wfioc:wf{}'.format(waveform_size)
    ca.benchmarking.set_logging_level(logging.DEBUG, logger=logger)

    context = {'pyepics': bench_pyepics_get_speed,
               'curio': bench_curio_get_speed,
               'threading': bench_threading_get_speed
               }[backend]

    val = list(range(waveform_size))
    with context(pvname, initial_value=val) as bench_fcn:
        benchmark(bench_fcn)