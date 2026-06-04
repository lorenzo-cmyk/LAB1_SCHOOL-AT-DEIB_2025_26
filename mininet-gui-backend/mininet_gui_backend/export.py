import json
from typing import List, Tuple

from mininet_gui_backend.schema import Host, Switch, Controller


# json schema
def export_net_to_json(
    switches: List[Switch],
    hosts: List[Host],
    controllers: List[Controller],
    links: List[Tuple[str, str]],
) -> str:
    net_data = {
        "switches": [switch.model_dump() for switch in switches.values()],
        "hosts": [host.model_dump() for host in hosts.values()],
        "controllers": [controller.model_dump() for controller in controllers.values()],
        "links": [list(link) for link in links],
    }

    return json.dumps(net_data, indent=4)
