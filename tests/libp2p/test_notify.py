"""
Test Notify and Notifee by ensuring that the proper events get
called, and that the stream passed into opened_stream is correct

Note: Listen event does not get hit because MyNotifee is passed
into network after network has already started listening

TODO: Add tests for closed_stream disconnected, listen_close when those
features are implemented in swarm
"""

import pytest

from tests.utils import *
from libp2p import new_node
from libp2p.network.notifee_interface import INotifee

# pylint: disable=too-many-locals

class MyNotifee(INotifee):
    # pylint: disable=too-many-instance-attributes, cell-var-from-loop

    def __init__(self, events, val_to_append_to_event):
        self.events = events
        self.val_to_append_to_event = val_to_append_to_event

    async def opened_stream(self, network, stream):
        self.events.append(["opened_stream" + \
            self.val_to_append_to_event, stream])

    async def closed_stream(self, network, stream):
        pass

    async def connected(self, network, conn):
        self.events.append(["connected" + self.val_to_append_to_event,\
            conn])

    async def disconnected(self, network, conn):
        pass

    async def listen(self, network, multiaddr):
        pass

    async def listen_close(self, network, multiaddr):
        pass

class InvalidNotifee():
    # pylint: disable=too-many-instance-attributes, cell-var-from-loop

    def __init__(self):
        pass

    async def opened_stream(self):
        assert False

    async def closed_stream(self):
        assert False

    async def connected(self):
        assert False

    async def disconnected(self):
        assert False

    async def listen(self):
        assert False

async def perform_two_host_set_up_custom_handler(handler):
    transport_opt_list = [["/ip4/127.0.0.1/tcp/0"], ["/ip4/127.0.0.1/tcp/0"]]
    (node_a, node_b) = await set_up_nodes_by_transport_opt(transport_opt_list) 

    node_b.set_stream_handler("/echo/1.0.0", handler)

    # Associate the peer with local ip address (see default parameters of Libp2p())
    node_a.get_peerstore().add_addrs(node_b.get_id(), node_b.get_addrs(), 10)
    return node_a, node_b

@pytest.mark.asyncio
async def test_one_notifier():
    node_a, node_b = await perform_two_host_set_up_custom_handler(echo_stream_handler)

    # Add notifee for node_a
    events = []
    assert node_a.get_network().notify(MyNotifee(events, "0"))

    stream = await node_a.new_stream(node_b.get_id(), ["/echo/1.0.0"])

    # Ensure the connected and opened_stream events were hit in MyNotifee obj
    # and that stream passed into opened_stream matches the stream created on
    # node_a
    assert events == [["connected0", stream.mplex_conn], \
        ["opened_stream0", stream]]

    messages = ["hello", "hello"]
    for message in messages:
        await stream.write(message.encode())

        response = (await stream.read()).decode()

        assert response == ("ack:" + message)

    # Success, terminate pending tasks.
    await cleanup()

@pytest.mark.asyncio
async def test_one_notifier_on_two_nodes():
    events_b = []

    async def my_stream_handler(stream):
        # Ensure the connected and opened_stream events were hit in Notifee obj
        # and that the stream passed into opened_stream matches the stream created on
        # node_b
        assert events_b == [["connectedb", stream.mplex_conn], \
            ["opened_streamb", stream]]
        while True:
            read_string = (await stream.read()).decode()

            resp = "ack:" + read_string
            await stream.write(resp.encode())

    node_a, node_b = await perform_two_host_set_up_custom_handler(my_stream_handler)

    # Add notifee for node_a
    events_a = []
    assert node_a.get_network().notify(MyNotifee(events_a, "a"))

    # Add notifee for node_b
    assert node_b.get_network().notify(MyNotifee(events_b, "b"))

    stream = await node_a.new_stream(node_b.get_id(), ["/echo/1.0.0"])

    # Ensure the connected and opened_stream events were hit in MyNotifee obj
    # and that stream passed into opened_stream matches the stream created on
    # node_a
    assert events_a == [["connecteda", stream.mplex_conn], \
        ["opened_streama", stream]]

    messages = ["hello", "hello"]
    for message in messages:
        await stream.write(message.encode())

        response = (await stream.read()).decode()

        assert response == ("ack:" + message)

    # Success, terminate pending tasks.
    await cleanup()

@pytest.mark.asyncio
async def test_two_notifiers():
    node_a, node_b = await perform_two_host_set_up_custom_handler(echo_stream_handler)

    # Add notifee for node_a
    events0 = []
    assert node_a.get_network().notify(MyNotifee(events0, "0"))

    events1 = []
    assert node_a.get_network().notify(MyNotifee(events1, "1"))

    stream = await node_a.new_stream(node_b.get_id(), ["/echo/1.0.0"])

    # Ensure the connected and opened_stream events were hit in both Notifee objs
    # and that the stream passed into opened_stream matches the stream created on
    # node_a
    assert events0 == [["connected0", stream.mplex_conn], ["opened_stream0", stream]]
    assert events1 == [["connected1", stream.mplex_conn], ["opened_stream1", stream]]


    messages = ["hello", "hello"]
    for message in messages:
        await stream.write(message.encode())

        response = (await stream.read()).decode()

        assert response == ("ack:" + message)

    # Success, terminate pending tasks.
    await cleanup()

@pytest.mark.asyncio
async def test_ten_notifiers():
    num_notifiers = 10

    node_a, node_b = await perform_two_host_set_up_custom_handler(echo_stream_handler)

    # Add notifee for node_a
    events_lst = []
    for i in range(num_notifiers):
        events_lst.append([])
        assert node_a.get_network().notify(MyNotifee(events_lst[i], str(i)))

    stream = await node_a.new_stream(node_b.get_id(), ["/echo/1.0.0"])

    # Ensure the connected and opened_stream events were hit in both Notifee objs
    # and that the stream passed into opened_stream matches the stream created on
    # node_a
    for i in range(num_notifiers):
        assert events_lst[i] == [["connected" + str(i), stream.mplex_conn], \
            ["opened_stream" + str(i), stream]]

    messages = ["hello", "hello"]
    for message in messages:
        await stream.write(message.encode())

        response = (await stream.read()).decode()

        assert response == ("ack:" + message)

    # Success, terminate pending tasks.
    await cleanup()

@pytest.mark.asyncio
async def test_ten_notifiers_on_two_nodes():
    num_notifiers = 10
    events_lst_b = []

    async def my_stream_handler(stream):
        # Ensure the connected and opened_stream events were hit in all Notifee objs
        # and that the stream passed into opened_stream matches the stream created on
        # node_b
        for i in range(num_notifiers):
            assert events_lst_b[i] == [["connectedb" + str(i), stream.mplex_conn], \
                ["opened_streamb" + str(i), stream]]
        while True:
            read_string = (await stream.read()).decode()

            resp = "ack:" + read_string
            await stream.write(resp.encode())

    node_a, node_b = await perform_two_host_set_up_custom_handler(my_stream_handler)

    # Add notifee for node_a and node_b
    events_lst_a = []
    for i in range(num_notifiers):
        events_lst_a.append([])
        events_lst_b.append([])
        assert node_a.get_network().notify(MyNotifee(events_lst_a[i], "a" + str(i)))
        assert node_b.get_network().notify(MyNotifee(events_lst_b[i], "b" + str(i)))

    stream = await node_a.new_stream(node_b.get_id(), ["/echo/1.0.0"])

    # Ensure the connected and opened_stream events were hit in all Notifee objs
    # and that the stream passed into opened_stream matches the stream created on
    # node_a
    for i in range(num_notifiers):
        assert events_lst_a[i] == [["connecteda" + str(i), stream.mplex_conn], \
            ["opened_streama" + str(i), stream]]

    messages = ["hello", "hello"]
    for message in messages:
        await stream.write(message.encode())

        response = (await stream.read()).decode()

        assert response == ("ack:" + message)

    # Success, terminate pending tasks.
    await cleanup()

@pytest.mark.asyncio
async def test_invalid_notifee():
    num_notifiers = 10

    node_a, node_b = await perform_two_host_set_up_custom_handler(echo_stream_handler)

    # Add notifee for node_a
    events_lst = []
    for _ in range(num_notifiers):
        events_lst.append([])
        assert not node_a.get_network().notify(InvalidNotifee())

    stream = await node_a.new_stream(node_b.get_id(), ["/echo/1.0.0"])

    # If this point is reached, this implies that the InvalidNotifee instance
    # did not assert false, i.e. no functions of InvalidNotifee were called (which is correct
    # given that InvalidNotifee should not have been added as a notifee)
    messages = ["hello", "hello"]
    for message in messages:
        await stream.write(message.encode())

        response = (await stream.read()).decode()

        assert response == ("ack:" + message)

    # Success, terminate pending tasks.
    await cleanup()
