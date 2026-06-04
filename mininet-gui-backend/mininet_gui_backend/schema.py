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


class Host(Node):
    ip: str
    mac: str


class Switch(Node):
    ports: int
    controller: Union[str, None]
    switch_type: str = "ovskernel"
    of_version: Union[str, None] = None
