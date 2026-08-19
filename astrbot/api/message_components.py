from dataclasses import dataclass, field
from typing import Any


@dataclass
class Plain:
    text: str = ""


@dataclass
class Image:
    file: str = ""
    url: str = ""


@dataclass
class Node:
    name: str = ""
    uin: str = "0"
    content: list[Any] = field(default_factory=list)


@dataclass
class Nodes:
    nodes: list[Node] = field(default_factory=list)
