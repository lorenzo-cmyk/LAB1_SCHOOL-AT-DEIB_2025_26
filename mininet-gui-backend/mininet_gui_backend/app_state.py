net = None
controllers = {}
switches = {}
hosts = {}
nats = {}
routers = {}
links = {}
link_attrs = {}
terminals = {}
sniffers = {}
sniffer_manager = None
pingall_running = False
iperf_running = False


def reset_state():
    global net, controllers, switches, hosts, nats, routers
    global links, link_attrs, terminals, sniffers, sniffer_manager
    global pingall_running, iperf_running
    net = None
    controllers.clear()
    switches.clear()
    hosts.clear()
    nats.clear()
    routers.clear()
    links.clear()
    link_attrs.clear()
    terminals.clear()
    sniffers.clear()
    sniffer_manager = None
    pingall_running = False
    iperf_running = False
