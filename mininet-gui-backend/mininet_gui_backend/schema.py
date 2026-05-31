from typing import Union

from pydantic import BaseModel


class Node(BaseModel):
    id: str
    type: str
    name: str
    label: str
    x: float
    y: float


class Controller(Node):
    controller_type: str = "default"
    remote: bool
    ip: Union[str, None]
    port: Union[int, None]
    color: Union[str, None] = None
    of_version: Union[str, None] = "OpenFlow13"

    def format_controller(self) -> str:
        controller_type = (self.controller_type or "").lower()
        if self.remote or controller_type == "remote":
            return f'{self.name} = net.addController("{self.name}", controller=RemoteController, ip="{self.ip}", port={self.port})'
        if self.port:
            return f'{self.name} = net.addController("{self.name}", port={self.port})'
        return f'{self.name} = net.addController("{self.name}")'


class Host(Node):
    ip: str
    mac: str


class Switch(Node):
    ports: int
    controller: Union[str, None]
    switch_type: str = "ovskernel"
    of_version: Union[str, None] = None

    def format_switch(self) -> str:
        switch_type = (self.switch_type or "").lower()
        if switch_type == "ovskernel":
            return f'{self.name} = net.addSwitch("{self.name}", cls=OVSKernelSwitch)'
        return f'{self.name} = net.addSwitch("{self.name}")'
