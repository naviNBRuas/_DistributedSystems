"""
Ring Algorithm for Leader Election

Nodes are arranged in a logical ring, tokens circulate.
Initiator sends token with its ID, each node adds itself and forwards.
Winner is highest ID in the token.
"""

import time
import threading
import logging
from typing import Set, Optional, Callable, List, Dict, Any
from dataclasses import dataclass, asdict

from transport import Transport

logger = logging.getLogger(__name__)

@dataclass
class RingMessage:
    """Message payload for ring election"""
    type: str  # "election" or "elected"
    candidates: List[str]
    sender_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RingMessage':
        return cls(**data)


class RingElection:
    """
    Ring Algorithm Implementation
    
    Properties:
    - Nodes arranged in ring (by ID ordering)
    - Token passes around ring
    - Each node adds itself as candidate
    - Node with highest ID wins
    - O(N) messages per election
    """
    
    def __init__(
        self,
        node_id: str,
        peers: List[str],
        transport: Transport,
        election_timeout: float = 2.0
    ):
        """Initialize ring election"""
        self.node_id = node_id
        # Ensure we have a sorted list of all potential nodes to form the ring
        self.peers = set(peers) if not isinstance(peers, set) else peers
        self.all_nodes = sorted(list({node_id} | self.peers))
        self.transport = transport
        
        # Determine next node in the ring
        try:
            self.node_index = self.all_nodes.index(node_id)
            self.next_node = self.all_nodes[(self.node_index + 1) % len(self.all_nodes)]
        except ValueError:
             # Should not happen given construction above
            self.next_node = node_id

        self.election_timeout = election_timeout
        self.is_leader_flag = False
        self.current_leader: Optional[str] = None
        self.in_election = False
        
        self.lock = threading.RLock()
        self.running = False
        self.leader_change_callbacks = []
        self.last_heartbeat = time.time()
        
        self.transport.set_on_message(self._handle_message)
    
    def start(self):
        """Start participating"""
        with self.lock:
            if self.running:
                return
            self.running = True
            self.transport.start()
            
            # Start monitor thread (checks if we need to start election)
            monitor = threading.Thread(target=self._monitor_leader, daemon=True)
            monitor.start()
            
            logger.info(f"[{self.node_id}] Started ring election (Next: {self.next_node})")
            
            # In Ring, we usually wait for a trigger or timeout. 
            # If we just started and don't know the leader, we might initiate.
            if not self.current_leader:
                self._start_election()
    
    def stop(self):
        """Stop participating"""
        with self.lock:
            self.running = False
            self.transport.stop()
            if self.is_leader_flag:
                logger.info(f"[{self.node_id}] Stepping down")
                self.is_leader_flag = False
    
    def _start_election(self):
        """Initiate election by sending message to next node"""
        with self.lock:
            if self.in_election:
                return
            
            self.in_election = True
            logger.info(f"[{self.node_id}] Starting election")
            
            # Send election message with self as candidate
            self._send_election_message([self.node_id])
    
    def _send_election_message(self, candidates: List[str]):
        """Send election message to next node in ring"""
        msg = RingMessage("election", candidates, self.node_id)
        # If next node is self, we are the only node
        if self.next_node == self.node_id:
            self._election_complete(self.node_id)
            return
            
        logger.debug(f"[{self.node_id}] -> {self.next_node}: candidates={candidates}")
        self.transport.send(self.next_node, msg.to_dict())
    
    def _send_elected_message(self, winner: str):
        """Send ELECTED message around the ring"""
        msg = RingMessage("elected", [winner], self.node_id)
        if self.next_node != self.node_id:
             self.transport.send(self.next_node, msg.to_dict())

    def _handle_message(self, data: Any):
        """Handle incoming transport message"""
        try:
            if isinstance(data, dict):
                msg = RingMessage.from_dict(data)
            else:
                return
            
            if msg.type == "election":
                self.handle_election_message(msg)
            elif msg.type == "elected":
                self.handle_elected_message(msg)
                
        except Exception as e:
            logger.error(f"[{self.node_id}] Error handling message: {e}")

    def handle_election_message(self, message: RingMessage):
        """Handle election message from previous node in ring"""
        with self.lock:
            if not self.running:
                return
            
            candidates = message.candidates
            logger.debug(f"[{self.node_id}] Received election: {candidates}")
            
            # If this message is from us (we see ourselves in the list AND we initiated it/it completed circle)
            # Actually standard ring: list accumulates. If my ID is in list, the message went around.
            # But usually we check if the *first* candidate is me, or if I'm in the list.
            # Simplest Ring: If I receive an election message:
            # 1. Add myself.
            # 2. If I am already in the list, then the message has circulated. Find max.
            
            if self.node_id in candidates:
                # Cycle complete.
                winner = max(candidates)
                logger.info(f"[{self.node_id}] Election complete. Winner: {winner}")
                self._election_complete(winner)
                
                # Propagate the result
                self._send_elected_message(winner)
                return
            
            # Add ourselves and forward to next
            new_candidates = candidates + [self.node_id]
            self.in_election = True # We are now participating
            self._send_election_message(new_candidates)

    def handle_elected_message(self, message: RingMessage):
        """Handle ELECTED message"""
        with self.lock:
            winner = message.candidates[0] # Convention: winner is in candidates list
            
            if winner == self.current_leader and not self.in_election:
                # Already knew, stop forwarding if we initiated or it came back to us?
                # Usually ELECTED goes around once.
                # If we originated the ELECTED message (sender_id is us), stop.
                pass
            
            # If we sent this message originally (it came back around), stop it.
            if message.sender_id == self.node_id:
                return

            logger.info(f"[{self.node_id}] Agreed on leader: {winner}")
            self.current_leader = winner
            self.in_election = False
            
            if winner == self.node_id:
                self._become_leader()
            else:
                self._become_follower()
                
            # Forward to next
            self.transport.send(self.next_node, message.to_dict())

    def _election_complete(self, winner: str):
        """Local election completion logic"""
        self.in_election = False
        self.current_leader = winner
        
        if winner == self.node_id:
            self._become_leader()
        else:
            self._become_follower()
    
    def _become_leader(self):
        """Become the leader"""
        if not self.is_leader_flag:
            self.is_leader_flag = True
            logger.info(f"[{self.node_id}] *** I AM THE LEADER ***")
            self._notify_leader_change()
    
    def _become_follower(self):
        """Become a follower"""
        if self.is_leader_flag:
            self.is_leader_flag = False
            logger.info(f"[{self.node_id}] Follower of {self.current_leader}")
            self._notify_leader_change()
        elif self.current_leader and self.current_leader != self.node_id:
             # Just update state if we weren't leader
             pass
    
    def _monitor_leader(self):
        """
        Monitor leader. 
        In Ring, this is harder because there's no heartbeat usually built-in to the election algo itself 
        (unlike Bully). But we can assume an external heartbeat or add one.
        For now, we'll just check if we have a leader.
        """
        while self.running:
            time.sleep(self.election_timeout)
            
            # Simple check: if no leader known for a while, start election
            if not self.current_leader and not self.in_election:
                self._start_election()
    
    def is_leader(self) -> bool:
        return self.is_leader_flag
    
    def get_leader(self) -> Optional[str]:
        return self.current_leader
    
    def on_leader_change(self, callback: Callable):
        self.leader_change_callbacks.append(callback)
    
    def _notify_leader_change(self):
        for callback in self.leader_change_callbacks:
            try:
                callback(self.current_leader)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def trigger_election(self):
        self._start_election()
