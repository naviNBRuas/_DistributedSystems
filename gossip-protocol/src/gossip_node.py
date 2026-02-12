"""
Gossip Protocol Node Implementation

Implements epidemic-style gossip for decentralized state propagation.
Supports push, pull, and push-pull gossip variants.
"""

import time
import threading
import logging
from typing import Dict, List, Callable, Optional, Any
from dataclasses import asdict

from config import GossipConfig
from message import GossipMessage, MessageType
from transport import UDPTransport
from membership import Membership, MemberStatus
from failure_detector import PhiAccrualFailureDetector
from state_store import StateStore, StateEntry

class GossipMode:
    PUSH = "push"
    PULL = "pull"
    PUSH_PULL = "push_pull"

class GossipNode:
    """
    Gossip protocol node for decentralized state propagation.
    """

    def __init__(
        self,
        node_id: str,
        bind_address: str,
        seed_nodes: List[str] = None,
        config: GossipConfig = None,
        mode: str = GossipMode.PUSH_PULL
    ):
        self.node_id = node_id
        self.bind_address = bind_address
        self.host, self.port = self._parse_address(bind_address)
        self.seed_nodes = seed_nodes or []
        self.config = config or GossipConfig()
        self.mode = mode
        
        # Components
        self.transport = UDPTransport(self.host, self.port)
        self.membership = Membership(node_id, (self.host, self.port))
        self.failure_detector = PhiAccrualFailureDetector(
            threshold=self.config.phi_threshold,
            window_size=1000
        )
        self.state_store = StateStore(node_id)
        
        # Subscriptions
        self.subscribers: Dict[str, List[Callable]] = {}
        
        # Control
        self.running = False
        self.gossip_thread = None
        self.swim_thread = None
        self.logger = logging.getLogger(f"GossipNode-{node_id}")
        
        # Metrics
        self.metrics = {
            "gossip_rounds": 0,
            "messages_sent": 0,
            "messages_received": 0,
        }

    def _parse_address(self, addr: str) -> tuple:
        try:
            host, port = addr.split(":")
            return host, int(port)
        except ValueError:
            raise ValueError(f"Invalid address format '{addr}'. Expected 'host:port'")

    def start(self):
        """Start the gossip node."""
        if self.running:
            return

        self.running = True
        self.transport.start(self._handle_message)
        
        # Seed nodes
        for seed in self.seed_nodes:
            if seed == self.bind_address:
                continue
            try:
                host, port = self._parse_address(seed)
                # We don't know the ID yet, use address as ID temporarily or wait for handshake.
                # Simplification: Assume seed nodes are known or will respond.
                # We can just send a ping to seeds to discover them.
                # For membership, we add them as ALIVE.
                self.membership.update_member(f"seed_{host}_{port}", (host, port), MemberStatus.ALIVE, 0)
            except ValueError:
                self.logger.error(f"Invalid seed address: {seed}")

        self.gossip_thread = threading.Thread(target=self._gossip_loop, daemon=True)
        self.gossip_thread.start()
        
        self.swim_thread = threading.Thread(target=self._swim_loop, daemon=True)
        self.swim_thread.start()
        
        self.logger.info(f"Started node {self.node_id} at {self.bind_address}")

    def stop(self):
        """Stop the gossip node."""
        self.running = False
        self.transport.stop()
        if self.gossip_thread:
            self.gossip_thread.join(timeout=1)
        if self.swim_thread:
            self.swim_thread.join(timeout=1)
        self.logger.info("Stopped node")

    def _handle_message(self, data: bytes, addr: tuple):
        """Callback for incoming UDP messages."""
        self.metrics["messages_received"] += 1
        try:
            msg = GossipMessage.from_bytes(data)
            # Update sender liveness
            # If we receive anything from a node, it's alive.
            # We need to map sender_id to address if we don't have it.
            # Ideally the message payload contains the sender's info or we update membership.
            
            # Update failure detector
            self.failure_detector.report_heartbeat(msg.sender_id)
            
            # Update membership if needed (basic)
            self.membership.update_member(msg.sender_id, addr, MemberStatus.ALIVE, 0) # Incarnation?

            if msg.type == MessageType.PUSH:
                self._handle_push(msg)
            elif msg.type == MessageType.PULL_REQUEST:
                self._handle_pull_request(msg, addr)
            elif msg.type == MessageType.PULL_RESPONSE:
                self._handle_pull_response(msg)
            elif msg.type == MessageType.PING:
                self._handle_ping(msg, addr)
            elif msg.type == MessageType.ACK:
                pass # Handled by failure detector implicitly via report_heartbeat
            elif msg.type == MessageType.PING_REQ:
                self._handle_ping_req(msg, addr)

        except Exception as e:
            self.logger.error(f"Error handling message from {addr}: {e}")

    def _send(self, addr: tuple, msg: GossipMessage):
        """Send a message to a specific address."""
        try:
            data = msg.to_bytes()
            self.transport.send(addr, data)
            self.metrics["messages_sent"] += 1
        except Exception as e:
            self.logger.error(f"Send error: {e}")

    # --- Gossip Protocol ---

    def _gossip_loop(self):
        while self.running:
            try:
                self._perform_gossip_round()
                time.sleep(self.config.gossip_interval / 1000.0)
            except Exception as e:
                self.logger.error(f"Gossip loop error: {e}")

    def _perform_gossip_round(self):
        self.metrics["gossip_rounds"] += 1
        peers = self.membership.get_gossip_peers(self.config.gossip_fanout)
        
        for peer in peers:
            if self.mode in [GossipMode.PUSH, GossipMode.PUSH_PULL]:
                self._send_push(peer)
            if self.mode in [GossipMode.PULL, GossipMode.PUSH_PULL]:
                self._send_pull_request(peer)

    def _send_push(self, peer):
        # In a real efficient implementation, we might send only deltas.
        # Here we send full state or recent updates.
        entries = self.state_store.get_all_entries()
        # Filter entries? Or send all. For scalability, sending all is bad.
        # But for this implementation, we'll send all (anti-entropy).
        
        payload = {
            "entries": [asdict(e) for e in entries],
            "membership": self.membership.get_all_members_data()
        }
        
        msg = GossipMessage(MessageType.PUSH, self.node_id, payload)
        self._send(peer.address, msg)

    def _send_pull_request(self, peer):
        digest = self.state_store.get_digest()
        payload = {"digest": digest}
        msg = GossipMessage(MessageType.PULL_REQUEST, self.node_id, payload)
        self._send(peer.address, msg)

    def _handle_push(self, msg: GossipMessage):
        remote_entries = msg.payload.get("entries", [])
        self._merge_entries(remote_entries)
        
        remote_members = msg.payload.get("membership", [])
        self.membership.merge_membership_list(remote_members)

    def _handle_pull_request(self, msg: GossipMessage, addr: tuple):
        remote_digest = msg.payload.get("digest", {})
        delta = self.state_store.get_delta(remote_digest)
        
        payload = {
            "entries": [asdict(e) for e in delta],
            "membership": self.membership.get_all_members_data()
        }
        
        response = GossipMessage(MessageType.PULL_RESPONSE, self.node_id, payload)
        self._send(addr, response)

    def _handle_pull_response(self, msg: GossipMessage):
        remote_entries = msg.payload.get("entries", [])
        self._merge_entries(remote_entries)
        
        remote_members = msg.payload.get("membership", [])
        self.membership.merge_membership_list(remote_members)

    def _merge_entries(self, entries_data: List[dict]):
        for data in entries_data:
            # Reconstruct StateEntry
            try:
                entry = StateEntry(**data)
                updated = self.state_store.merge(entry)
                if updated:
                    self._notify_subscribers(entry.key, entry.value)
            except Exception as e:
                self.logger.error(f"Error merging entry: {e}")

    # --- SWIM Failure Detection ---

    def _swim_loop(self):
        while self.running:
            try:
                target = self.membership.get_gossip_peers(1)
                if target:
                    self._send_ping(target[0])
                time.sleep(self.config.failure_detection_interval / 1000.0)
            except Exception as e:
                self.logger.error(f"SWIM loop error: {e}")

    def _send_ping(self, member):
        msg = GossipMessage(MessageType.PING, self.node_id)
        self._send(member.address, msg)

    def _handle_ping(self, msg: GossipMessage, addr: tuple):
        ack = GossipMessage(MessageType.ACK, self.node_id)
        self._send(addr, ack)

    def _handle_ping_req(self, msg: GossipMessage, addr: tuple):
        # Request to ping another node
        target_id = msg.payload.get("target_id")
        target = self.membership.get_member(target_id)
        if target:
            # We would ping target and forward ACK back to original sender.
            # Implementing full indirect ping is complex for this snippet.
            # Simplified: just ACK back saying we'll try.
            pass

    # --- Public API ---

    def set(self, key: str, value: Any):
        """Set a value in the cluster."""
        entry = self.state_store.set(key, value)
        self._notify_subscribers(key, value)
        self.logger.info(f"Set {key}={value}")

    def get(self, key: str) -> Any:
        """Get a value."""
        return self.state_store.get(key)

    def get_prefix(self, prefix: str) -> Dict[str, Any]:
        """Get values matching prefix."""
        entries = self.state_store.get_all_entries()
        return {
            e.key: e.value 
            for e in entries 
            if e.key.startswith(prefix) and not e.tombstone
        }

    def delete(self, key: str):
        """Delete a value."""
        self.state_store.delete(key)
        self._notify_subscribers(key, None)

    def subscribe(self, pattern: str, callback: Callable[[str, Any], None]):
        """Subscribe to changes."""
        if pattern not in self.subscribers:
            self.subscribers[pattern] = []
        self.subscribers[pattern].append(callback)

    def _notify_subscribers(self, key: str, value: Any):
        for pattern, callbacks in self.subscribers.items():
            if self._matches_pattern(key, pattern):
                for cb in callbacks:
                    try:
                        cb(key, value)
                    except Exception as e:
                        self.logger.error(f"Subscriber callback error: {e}")

    def _matches_pattern(self, key: str, pattern: str) -> bool:
        if '*' not in pattern:
            return key == pattern
        prefix = pattern.rstrip('*')
        return key.startswith(prefix)

    def get_members(self) -> List[str]:
        return [m.node_id for m in self.membership.get_alive_members()]

    def get_metrics(self) -> Dict[str, Any]:
        self.metrics["state_size"] = len(self.state_store.get_all_entries())
        self.metrics["cluster_size"] = len(self.membership.get_alive_members())
        return self.metrics