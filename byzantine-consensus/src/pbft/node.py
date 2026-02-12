import hashlib
import json
import logging
from dataclasses import asdict
from typing import List, Dict, Set, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)

from .messages import (
    Message, MessageType, RequestMessage, PrePrepareMessage, 
    PrepareMessage, CommitMessage, ReplyMessage,
    ViewChangeMessage, NewViewMessage
)
from .network import Network

class RequestState:
    def __init__(self, request_id: int):
        self.request_id = request_id
        self.committed = False
        self.result = None

class PBFTNode:
    def __init__(self, node_id: int, total_nodes: int, network: Optional[Network] = None):
        self.node_id = node_id
        self.total_nodes = total_nodes
        self.f = (total_nodes - 1) // 3
        self.network = network
        
        self.view = 0
        self.seq_num = 0 # Last assigned sequence number (if primary) or last executed (if replica) - slightly mixed in simple impl
        self.last_executed_seq = 0
        
        # Logs
        # (view, seq_num) -> PrePrepareMessage
        self.pre_prepares: Dict[tuple, PrePrepareMessage] = {}
        # (view, seq_num) -> set of (sender_id, digest)
        self.prepares: Dict[tuple, Set[tuple]] = defaultdict(set)
        # (view, seq_num) -> set of (sender_id, digest)
        self.commits: Dict[tuple, Set[tuple]] = defaultdict(set)
        
        # View Change state
        # view -> set of ViewChangeMessage
        self.view_change_log: Dict[int, List[ViewChangeMessage]] = defaultdict(list)
        self.status = "NORMAL" # NORMAL, VIEW_CHANGE
        
        # State tracking
        self.prepared_predicate: Set[tuple] = set() # (view, seq) that are prepared
        self.committed_predicate: Set[tuple] = set() # (view, seq) that are committed_local
        
        # Client request tracking
        self.client_requests: Dict[int, RequestState] = {}
        
        if self.network:
            self.network.register_node(self)

    def is_primary(self) -> bool:
        return self.node_id == (self.view % self.total_nodes)

    def get_primary_id(self) -> int:
        return self.view % self.total_nodes

    def propose(self, operation: Any) -> RequestState:
        """
        Called by a client (simulated) or internally to initiate a request.
        For the 'Quick Start', this node acts as the entry point.
        """
        # In a real system, a client would send a REQUEST message.
        # Here we simulate the client request arrival at this node.
        req_id = int(self.node_id * 1000000 + (self.seq_num + 1) * 1000) # Simple unique ID generation
        # Better ID generation in production
        import time
        req_id = int(time.time() * 1000000) + self.node_id
        
        req_state = RequestState(req_id)
        self.client_requests[req_id] = req_state
        
        req_msg = RequestMessage(
            sender=self.node_id, # Acting as client proxy
            view=self.view,
            client_id=str(self.node_id),
            operation=operation,
            request_id=req_id
        )
        
        # If I am primary, start protocol. If not, forward to primary.
        if self.is_primary():
            self.handle_request(req_msg)
        else:
            primary = self.get_primary_id()
            if self.network:
                self.network.send(req_msg, primary)
            else:
                # If no network and not primary, we can't do much in this limited scope
                pass
                
        return req_state

    def receive(self, message: Any):
        """Entry point for incoming messages from Network."""
        if isinstance(message, dict):
             # Handle raw dict if network passes that
             message = Message.from_dict(message)
        
        if message.msg_type == MessageType.REQUEST:
            if isinstance(message, RequestMessage):
                self.handle_request(message)
        elif message.msg_type == MessageType.PRE_PREPARE:
            if isinstance(message, PrePrepareMessage):
                self.handle_pre_prepare(message)
        elif message.msg_type == MessageType.PREPARE:
            if isinstance(message, PrepareMessage):
                self.handle_prepare(message)
        elif message.msg_type == MessageType.COMMIT:
            if isinstance(message, CommitMessage):
                self.handle_commit(message)
        elif message.msg_type == MessageType.REPLY:
            if isinstance(message, ReplyMessage):
                self.handle_reply(message)
        elif message.msg_type == MessageType.VIEW_CHANGE:
            if isinstance(message, ViewChangeMessage):
                self.handle_view_change(message)
        elif message.msg_type == MessageType.NEW_VIEW:
            if isinstance(message, NewViewMessage):
                self.handle_new_view(message)

    def _digest(self, data: Any) -> str:
        s = json.dumps(data, sort_keys=True).encode('utf-8')
        return hashlib.sha256(s).hexdigest()

    def handle_reply(self, msg: ReplyMessage):
        # Clients handle replies, nodes usually don't unless they are proxies.
        pass

    def trigger_view_change(self):
        """Manually trigger a view change to view + 1."""
        self.status = "VIEW_CHANGE"
        new_view = self.view + 1
        logger.info(f"Node {self.node_id} triggering VIEW CHANGE to {new_view}")
        
        # Create ViewChange message
        # In reality we should include checkpoint proofs and prepared messages
        vc_msg = ViewChangeMessage(
            sender=self.node_id,
            view=new_view,
            checkpoint_seq=0 # Simplified
        )
        
        # Log my own
        self.view_change_log[new_view].append(vc_msg)
        
        if self.network:
            self.network.broadcast(vc_msg, self.node_id)
            
    def handle_view_change(self, msg: ViewChangeMessage):
        logger.debug(f"Node {self.node_id} received VIEW_CHANGE for view {msg.view} from {msg.sender}")
        if msg.view <= self.view:
            return # Old view change
            
        self.view_change_log[msg.view].append(msg)
        
        # Check if we have 2f+1 view changes for this view
        # We need to count unique senders
        senders = set(m.sender for m in self.view_change_log[msg.view])
        if len(senders) >= 2 * self.f + 1:
            # If I am the primary for this new view, send NEW-VIEW
            if (msg.view % self.total_nodes) == self.node_id:
                self.send_new_view(msg.view, self.view_change_log[msg.view])
                
    def send_new_view(self, new_view, view_changes):
        logger.info(f"Node {self.node_id} becoming PRIMARY for view {new_view}")
        
        # Construct NEW-VIEW message
        # Simplified: no complex O set calculation
        new_view_msg = NewViewMessage(
            sender=self.node_id,
            view=new_view,
            view_change_messages=[asdict(vc) for vc in view_changes]
        )
        
        self.view = new_view
        self.status = "NORMAL"
        
        if self.network:
            self.network.broadcast(new_view_msg, self.node_id)
            
    def handle_new_view(self, msg: NewViewMessage):
        logger.info(f"Node {self.node_id} received NEW_VIEW for view {msg.view}")
        # Verify (omitted)
        self.view = msg.view
        self.status = "NORMAL"
        # Process embedded pre-prepares (omitted)

    def handle_request(self, msg: RequestMessage):
        logger.debug(f"Node {self.node_id} received REQUEST: {msg}")
        if not self.is_primary():
            # Forward to primary
            primary_id = self.get_primary_id()
            logger.debug(f"Node {self.node_id} is not primary. Forwarding to {primary_id}")
            if self.network:
                self.network.send(msg, primary_id)
            return

        # Assign sequence number
        self.seq_num += 1
        digest = self._digest(msg.operation)
        
        logger.info(f"Node {self.node_id} (Primary) starting consensus for seq {self.seq_num}")

        # Create PrePrepare
        pre_prepare = PrePrepareMessage(
            sender=self.node_id,
            view=self.view,
            sequence_number=self.seq_num,
            digest=digest,
            request=asdict(msg) # Embed full request
        )
        
        # Log it
        self.pre_prepares[(self.view, self.seq_num)] = pre_prepare
        
        # Broadcast
        if self.network:
            self.network.broadcast(pre_prepare, self.node_id)
            # Primary also treats this as its own "Prepare" (logically)
            # but in standard PBFT, primary sends PrePrepare, others send Prepare.
            # Primary doesn't send Prepare usually, but participates in Commit phase.
            
    def handle_pre_prepare(self, msg: PrePrepareMessage):
        logger.debug(f"Node {self.node_id} received PRE-PREPARE: {msg}")
        # 1. Validate: check view, digest, signature (omitted), and watermark (omitted)
        if msg.view != self.view:
            logger.warning(f"Node {self.node_id} received PrePrepare with wrong view {msg.view} != {self.view}")
            return # Ignore wrong view messages
        
        key = (msg.view, msg.sequence_number)
        if key in self.pre_prepares:
            logger.debug(f"Node {self.node_id} ignoring duplicate PrePrepare for {key}")
            return # Duplicate
            
        self.pre_prepares[key] = msg
        
        # 2. Enter Pre-Prepared state (conceptually)
        # 3. Multicast PREPARE
        prepare = PrepareMessage(
            sender=self.node_id,
            view=self.view,
            sequence_number=msg.sequence_number,
            digest=msg.digest
        )
        
        # Log my own prepare (needed for counting?)
        # Standard PBFT: Replica sends Prepare to all.
        self.prepares[key].add((self.node_id, msg.digest))
        
        if self.network:
            self.network.broadcast(prepare, self.node_id)

        # Check if we are already prepared (unlikely this early, but maybe)
        self.check_prepared(key, msg.digest)

    def handle_prepare(self, msg: PrepareMessage):
        logger.debug(f"Node {self.node_id} received PREPARE: {msg}")
        if msg.view != self.view:
            return
            
        key = (msg.view, msg.sequence_number)
        self.prepares[key].add((msg.sender, msg.digest))
        
        # Check if prepared
        # Need PrePrepare + 2f Prepares (including potentially my own if I sent one)
        # Actually usually it's "PrePrepare from primary" + "2f Prepares from different backups".
        # Total matching messages including PrePrepare: 2f + 1.
        
        # We need the PrePrepare to verify the digest matches
        if key not in self.pre_prepares:
            # We got prepares but not the pre-prepare yet. Buffer or just wait.
            # In this simple implementation, the state is in `self.prepares`, 
            # so when PrePrepare arrives later, we can re-check.
            return
            
        digest = self.pre_prepares[key].digest
        if msg.digest != digest:
            # Hash mismatch (Byzantine behavior?)
            logger.warning(f"Node {self.node_id} detected digest mismatch in Prepare from {msg.sender}")
            return
            
        self.check_prepared(key, digest)

    def check_prepared(self, key, digest):
        if key in self.prepared_predicate:
            return # Already prepared
            
        # Count matching prepares
        # Filter for current digest
        matching_prepares = [p for p in self.prepares[key] if p[1] == digest]
        
        # We need 2f prepares from *other* replicas? 
        # PBFT Paper: "prepared(m, v, n, i) is true iff replica i has inserted in its log:
        # The request m, a pre-prepare for m in view v with sequence number n, 
        # and 2f prepares from different backups that match the pre-prepare."
        # Total participating nodes = 3f+1. 
        # Primary doesn't send prepare.
        # So we need 2f prepares.
        
        if len(matching_prepares) >= 2 * self.f:
            logger.info(f"Node {self.node_id} is PREPARED for {key}")
            self.prepared_predicate.add(key)
            
            # Send COMMIT
            commit = CommitMessage(
                sender=self.node_id,
                view=self.view,
                sequence_number=key[1],
                digest=digest
            )
            
            self.commits[key].add((self.node_id, digest))
            
            if self.network:
                self.network.broadcast(commit, self.node_id)
                
            self.check_committed(key, digest)

    def handle_commit(self, msg: CommitMessage):
        logger.debug(f"Node {self.node_id} received COMMIT: {msg}")
        if msg.view != self.view:
            return
            
        key = (msg.view, msg.sequence_number)
        self.commits[key].add((msg.sender, msg.digest))
        
        if key not in self.pre_prepares:
            return
            
        digest = self.pre_prepares[key].digest
        if msg.digest != digest:
            return
            
        self.check_committed(key, digest)

    def check_committed(self, key, digest):
        if key in self.committed_predicate:
            return
            
        # PBFT: "committed-local(m, v, n, i) is true iff prepared(m,v,n,i) is true 
        # and replica i has accepted 2f+1 commits (possibly including its own)."
        
        if key not in self.prepared_predicate:
            return # Must be prepared first
            
        matching_commits = [c for c in self.commits[key] if c[1] == digest]
        
        if len(matching_commits) >= 2 * self.f + 1:
            logger.info(f"Node {self.node_id} is COMMITTED LOCAL for {key}")
            self.committed_predicate.add(key)
            self.execute_request(key)

    def execute_request(self, key):
        # Execute the operation
        logger.info(f"Node {self.node_id} EXECUTING request {key}")
        pre_prepare = self.pre_prepares[key]
        request_data = pre_prepare.request
        # For this example, we just mark it as done
        
        req_id = request_data.get('request_id') if request_data else 0
        
        # If we are tracking this request (e.g. we are the proxy for the client)
        if req_id in self.client_requests:
            self.client_requests[req_id].committed = True
            self.client_requests[req_id].result = "Executed"
            logger.info(f"Node {self.node_id} finished client request {req_id}")
