import json
import time
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Dict, List, Optional

class MessageType(str, Enum):
    REQUEST = "REQUEST"
    PRE_PREPARE = "PRE_PREPARE"
    PREPARE = "PREPARE"
    COMMIT = "COMMIT"
    REPLY = "REPLY"
    VIEW_CHANGE = "VIEW_CHANGE"
    NEW_VIEW = "NEW_VIEW"
    CHECKPOINT = "CHECKPOINT"

@dataclass
class Message:
    sender: int
    view: int
    msg_type: Optional[MessageType] = None
    timestamp: float = field(default_factory=time.time)
    
    def to_json(self) -> str:
        data = asdict(self)
        if self.msg_type:
            data['msg_type'] = self.msg_type.value
        return json.dumps(data, sort_keys=True)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Message':
        if 'msg_type' not in data:
            raise ValueError("Data dictionary must contain 'msg_type'")
            
        msg_type = MessageType(data['msg_type'])
        data_copy = data.copy()
        data_copy.pop('msg_type') # Remove msg_type as it's set in __post_init__ or passed as arg
        
        if msg_type == MessageType.REQUEST:
            return RequestMessage(**data_copy)
        elif msg_type == MessageType.PRE_PREPARE:
            return PrePrepareMessage(**data_copy)
        elif msg_type == MessageType.PREPARE:
            return PrepareMessage(**data_copy)
        elif msg_type == MessageType.COMMIT:
            return CommitMessage(**data_copy)
        elif msg_type == MessageType.REPLY:
            return ReplyMessage(**data_copy)
        elif msg_type == MessageType.VIEW_CHANGE:
            return ViewChangeMessage(**data_copy)
        elif msg_type == MessageType.NEW_VIEW:
            # Recursive parsing for nested messages is needed for robustness,
            # but for now we assume they are dicts or we let the constructor handle it if simplified.
            # Ideally:
            # if 'pre_prepares' in data_copy:
            #     data_copy['pre_prepares'] = [PrePrepareMessage(**p) if isinstance(p, dict) else p for p in data_copy['pre_prepares']]
            return NewViewMessage(**data_copy)
        else:
            # Fallback for base message or unknown types
            return Message(msg_type=msg_type, **data_copy)

@dataclass
class RequestMessage(Message):
    client_id: str = ""
    operation: Any = None
    request_id: int = 0
    # In a real system, we'd sign this.
    
    def __post_init__(self):
        self.msg_type = MessageType.REQUEST

@dataclass
class PrePrepareMessage(Message):
    sequence_number: int = 0
    digest: str = ""
    request: Optional[Dict] = None # The original request content
    
    def __post_init__(self):
        self.msg_type = MessageType.PRE_PREPARE

@dataclass
class PrepareMessage(Message):
    sequence_number: int = 0
    digest: str = ""
    
    def __post_init__(self):
        self.msg_type = MessageType.PREPARE

@dataclass
class CommitMessage(Message):
    sequence_number: int = 0
    digest: str = ""
    
    def __post_init__(self):
        self.msg_type = MessageType.COMMIT

@dataclass
class ReplyMessage(Message):
    client_id: str = ""
    request_id: int = 0
    result: Any = None
    
    def __post_init__(self):
        self.msg_type = MessageType.REPLY

@dataclass
class ViewChangeMessage(Message):
    checkpoint_seq: int = 0
    # In full PBFT, this includes prepared proofs (P set)
    # Here we simplify: send a list of prepared messages
    prepared_proofs: List[PrePrepareMessage] = field(default_factory=list) 
    
    def __post_init__(self):
        self.msg_type = MessageType.VIEW_CHANGE

@dataclass
class NewViewMessage(Message):
    # Proofs that justify the new view
    view_change_messages: List[Dict] = field(default_factory=list) # serialized ViewChangeMessages
    # New PrePrepares for the new view
    pre_prepares: List[PrePrepareMessage] = field(default_factory=list)
    
    def __post_init__(self):
        self.msg_type = MessageType.NEW_VIEW
