import random
import time
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass

class MemberStatus(Enum):
    ALIVE = "alive"
    SUSPECT = "suspect"
    DEAD = "dead"
    LEFT = "left"

@dataclass
class Member:
    node_id: str
    address: Tuple[str, int] # (host, port)
    status: MemberStatus
    incarnation: int
    last_update: float

class Membership:
    def __init__(self, local_node_id: str, local_address: Tuple[str, int]):
        self.local_node_id = local_node_id
        self.local_address = local_address
        self.members: Dict[str, Member] = {}
        # Add self
        self.update_member(local_node_id, local_address, MemberStatus.ALIVE, 0)

    def update_member(self, node_id: str, address: Tuple[str, int], status: MemberStatus, incarnation: int) -> bool:
        """
        Update member state if the information is new.
        Returns True if the state was updated.
        """
        if node_id == self.local_node_id:
            # We are the authority on our own state.
            # Only update if we are refuting a suspicion (incarnation is higher).
            current = self.members.get(node_id)
            if current and incarnation > current.incarnation:
                 current.incarnation = incarnation
                 return True
            return False

        current = self.members.get(node_id)
        
        if not current:
            self.members[node_id] = Member(node_id, address, status, incarnation, time.time())
            return True
        
        # SWIM Dissemination Rules
        if incarnation > current.incarnation:
            current.incarnation = incarnation
            current.status = status
            current.address = address # Update address just in case
            current.last_update = time.time()
            return True
        elif incarnation == current.incarnation:
            # Status override rules: DEAD > SUSPECT > ALIVE
            if status == MemberStatus.DEAD and current.status != MemberStatus.DEAD:
                current.status = MemberStatus.DEAD
                current.last_update = time.time()
                return True
            elif status == MemberStatus.SUSPECT and current.status == MemberStatus.ALIVE:
                current.status = MemberStatus.SUSPECT
                current.last_update = time.time()
                return True
        
        return False

    def get_member(self, node_id: str) -> Optional[Member]:
        return self.members.get(node_id)

    def get_alive_members(self) -> List[Member]:
        return [m for m in self.members.values() 
                if m.status == MemberStatus.ALIVE and m.node_id != self.local_node_id]

    def get_gossip_peers(self, count: int = 1, exclude: Set[str] = None) -> List[Member]:
        """Select random ALIVE members to gossip with."""
        candidates = self.get_alive_members()
        if exclude:
            candidates = [m for m in candidates if m.node_id not in exclude]
        
        if not candidates:
            return []
        
        return random.sample(candidates, min(len(candidates), count))
    
    def get_address(self, node_id: str) -> Optional[Tuple[str, int]]:
        m = self.members.get(node_id)
        return m.address if m else None

    def get_all_members_data(self) -> List[dict]:
        """Return serializable list of members."""
        return [
            {
                "node_id": m.node_id,
                "host": m.address[0],
                "port": m.address[1],
                "status": m.status.value,
                "incarnation": m.incarnation
            }
            for m in self.members.values()
        ]

    def merge_membership_list(self, remote_members: List[dict]):
        """Merge a list of members received from gossip."""
        for m_data in remote_members:
            self.update_member(
                m_data["node_id"],
                (m_data["host"], m_data["port"]),
                MemberStatus(m_data["status"]),
                m_data["incarnation"]
            )
