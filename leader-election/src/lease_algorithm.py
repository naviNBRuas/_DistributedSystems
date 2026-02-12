"""
Lease-Based Leader Election

Leader holds a renewable lease.
When lease expires, any node can claim leadership.
Uses Quorum-based consensus to acquire lease.
"""

import time
import threading
import logging
import random
from typing import Optional, Callable, List, Dict, Any, Set
from dataclasses import dataclass, asdict

from transport import Transport

logger = logging.getLogger(__name__)

@dataclass
class LeaseMessage:
    """Message for lease negotiation"""
    type: str  # "request_lease", "grant_lease", "heartbeat"
    sender_id: str
    term: int  # Epoch/Term
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LeaseMessage':
        return cls(**data)

@dataclass
class Lease:
    """Leader lease with expiration"""
    holder: str
    issued_time: float
    duration: float
    term: int
    
    def is_valid(self) -> bool:
        """Check if lease is still valid"""
        return time.time() < self.issued_time + self.duration
    
    def time_remaining(self) -> float:
        """Get remaining lease time"""
        remaining = (self.issued_time + self.duration) - time.time()
        return max(0.0, remaining)


class LeaseBasedElection:
    """
    Lease-Based Leader Election
    
    Properties:
    - Leader holds time-limited lease
    - Must renew periodically
    - Others can challenge if lease expires
    - Requires Quorum to acquire lease
    """
    
    def __init__(
        self,
        node_id: str,
        peers: List[str],
        transport: Transport,
        lease_duration: float = 5.0,
        renew_interval: float = 1.0,
        quorum_size: Optional[int] = None
    ):
        """Initialize lease election"""
        self.node_id = node_id
        self.peers = set(peers)
        self.transport = transport
        self.all_nodes = {node_id} | self.peers
        
        self.lease_duration = lease_duration
        self.renew_interval = renew_interval
        self.quorum_size = quorum_size or (len(self.all_nodes) // 2 + 1)
        
        # State
        self.current_lease: Optional[Lease] = None
        self.term = 0
        self.votes_received: Set[str] = set()
        
        self.is_leader_flag = False
        self.in_contention = False
        
        self.lock = threading.RLock()
        self.running = False
        self.leader_change_callbacks = []
        
        # Local view of who we granted vote to (to prevent double voting in same term/window)
        self.voted_for: Optional[str] = None
        self.vote_timestamp: float = 0
        
        self.transport.set_on_message(self._handle_message)
    
    def start(self):
        """Start participating"""
        with self.lock:
            if self.running:
                return
            self.running = True
            self.transport.start()
            
            # Start monitor thread
            monitor = threading.Thread(target=self._monitor_lease, daemon=True)
            monitor.start()
            
            logger.info(f"[{self.node_id}] Started lease-based election (Quorum: {self.quorum_size})")
            
            # Start contention if no leader known
            self._start_contention()
    
    def stop(self):
        """Stop participating"""
        with self.lock:
            self.running = False
            self.transport.stop()
            if self.is_leader_flag:
                self._relinquish_lease()
    
    def _start_contention(self):
        """Start contending for leadership"""
        if self.in_contention or self.is_leader_flag:
            return
            
        self.in_contention = True
        
        # Random backoff to prevent split vote loops
        backoff = random.uniform(0.1, 0.5)
        
        def contend_after_delay():
            time.sleep(backoff)
            self._attempt_acquire_lease()
        
        threading.Thread(target=contend_after_delay, daemon=True).start()
    
    def _attempt_acquire_lease(self):
        """Try to acquire leadership lease"""
        with self.lock:
            if not self.running:
                return
            
            # If valid lease exists (and it's not us - handled by is_leader_flag check earlier), 
            # don't disturb it until it expires.
            if self.current_lease and self.current_lease.is_valid():
                self.in_contention = False
                return
            
            self.term += 1
            self.votes_received = {self.node_id} # Vote for self
            self.voted_for = self.node_id
            
            logger.info(f"[{self.node_id}] Requesting lease (Term {self.term})")
            
            msg = LeaseMessage("request_lease", self.node_id, self.term)
            for peer in self.peers:
                self.transport.send(peer, msg.to_dict())
                
            # Wait for responses is handled async via callbacks
            
            # Safety timeout to reset contention if failed
            threading.Timer(self.lease_duration, self._contention_timeout).start()

    def _contention_timeout(self):
        with self.lock:
            if self.in_contention and not self.is_leader_flag:
                # Failed to get quorum
                self.in_contention = False
                # Will retry via monitor loop

    def _handle_message(self, data: Any):
        try:
            if isinstance(data, dict):
                msg = LeaseMessage.from_dict(data)
            else:
                return
                
            if msg.type == "request_lease":
                self.handle_request_lease(msg)
            elif msg.type == "grant_lease":
                self.handle_grant_lease(msg)
            elif msg.type == "heartbeat":
                self.handle_heartbeat(msg)
                
        except Exception as e:
            logger.error(f"[{self.node_id}] Error handling message: {e}", exc_info=True)

    def handle_request_lease(self, msg: LeaseMessage):
        with self.lock:
            # Grant if:
            # 1. Term is higher or equal
            # 2. We haven't voted for someone else in this term/window
            # 3. Current lease is expired (or sender is current owner extending)
            
            is_lease_valid = self.current_lease and self.current_lease.is_valid()
            is_current_owner = self.current_lease and self.current_lease.holder == msg.sender_id
            
            should_grant = False
            
            if msg.term > self.term:
                self.term = msg.term
                self.voted_for = None
            
            if is_current_owner:
                # Always allow renewal
                should_grant = True
            elif not is_lease_valid:
                # No valid lease, free to vote
                if self.voted_for is None or self.voted_for == msg.sender_id:
                    should_grant = True
            
            if should_grant:
                self.voted_for = msg.sender_id
                self.vote_timestamp = time.time()
                
                logger.debug(f"[{self.node_id}] Granting lease to {msg.sender_id}")
                reply = LeaseMessage("grant_lease", self.node_id, msg.term)
                self.transport.send(msg.sender_id, reply.to_dict())

    def handle_grant_lease(self, msg: LeaseMessage):
        with self.lock:
            if not self.in_contention and not self.is_leader_flag:
                return
                
            if msg.term != self.term:
                return
                
            self.votes_received.add(msg.sender_id)
            
            if len(self.votes_received) >= self.quorum_size:
                if not self.is_leader_flag:
                    self._become_leader()

    def handle_heartbeat(self, msg: LeaseMessage):
        with self.lock:
            # Update local knowledge of lease
            if msg.term >= self.term:
                self.current_lease = Lease(
                    holder=msg.sender_id,
                    issued_time=time.time(), # Approximate
                    duration=self.lease_duration,
                    term=msg.term
                )
                self.term = msg.term
                self.in_contention = False
                
                if self.is_leader_flag and msg.sender_id != self.node_id:
                    # Split brain? Or I lost leadership
                    self._step_down()

    def _become_leader(self):
        self.is_leader_flag = True
        self.in_contention = False
        self.current_lease = Lease(
            holder=self.node_id,
            issued_time=time.time(),
            duration=self.lease_duration,
            term=self.term
        )
        logger.info(f"[{self.node_id}] *** ACQUIRED LEASE (Quorum met) ***")
        self._notify_leader_change()
        
        # Start renewal thread
        threading.Thread(target=self._renewal_loop, daemon=True).start()

    def _renewal_loop(self):
        while self.running and self.is_leader_flag:
            self._send_heartbeat()
            time.sleep(self.renew_interval)

    def _send_heartbeat(self):
        # Acts as lease renewal request and heartbeat
        msg = LeaseMessage("heartbeat", self.node_id, self.term)
        # Also send request_lease to keep votes (renewal)
        req = LeaseMessage("request_lease", self.node_id, self.term)
        
        for peer in self.peers:
            self.transport.send(peer, req.to_dict())
            self.transport.send(peer, msg.to_dict())

    def _step_down(self):
        logger.info(f"[{self.node_id}] Stepping down")
        self.is_leader_flag = False
        
    def _relinquish_lease(self):
        self._step_down()
        self.current_lease = None
    
    def _monitor_lease(self):
        """Monitor lease expiration"""
        while self.running:
            time.sleep(0.1)
            
            with self.lock:
                if self.current_lease and not self.current_lease.is_valid():
                    if self.is_leader_flag:
                        # Should have renewed!
                        self._step_down()
                    
                    # Lease expired, start election if we are not leader
                    if not self.in_contention:
                        logger.info(f"[{self.node_id}] Lease expired, contending...")
                        self._start_contention()

    def is_leader(self) -> bool:
        return self.is_leader_flag
    
    def get_leader(self) -> Optional[str]:
        if self.current_lease and self.current_lease.is_valid():
            return self.current_lease.holder
        return None
    
    def on_leader_change(self, callback: Callable):
        self.leader_change_callbacks.append(callback)
    
    def _notify_leader_change(self):
        for callback in self.leader_change_callbacks:
            try:
                callback(self.get_leader())
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def trigger_election(self):
        self._start_contention()
