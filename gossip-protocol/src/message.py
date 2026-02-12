import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from enum import Enum

class MessageType(str, Enum):
    PUSH = "push"
    PULL_REQUEST = "pull_request"
    PULL_RESPONSE = "pull_response"
    PING = "ping"
    ACK = "ack"
    PING_REQ = "ping_req"

@dataclass
class GossipMessage:
    type: MessageType
    sender_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "sender_id": self.sender_id,
            "payload": self.payload,
            "timestamp": self.timestamp
        })

    @classmethod
    def from_json(cls, json_str: str) -> 'GossipMessage':
        data = json.loads(json_str)
        return cls(
            type=MessageType(data["type"]),
            sender_id=data["sender_id"],
            payload=data["payload"],
            timestamp=data["timestamp"]
        )

    def to_bytes(self) -> bytes:
        return self.to_json().encode('utf-8')

    @classmethod
    def from_bytes(cls, data: bytes) -> 'GossipMessage':
        return cls.from_json(data.decode('utf-8'))
