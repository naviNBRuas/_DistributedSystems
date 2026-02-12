"""
Raft Consensus Node Implementation

This module implements the core Raft consensus algorithm, including:
- Leader election with randomized timeouts
- Log replication with consistency checks
- Safety guarantees (leader completeness, log matching)
- Membership changes via joint consensus (Future work)

Reference: https://raft.github.io/raft.pdf
"""

import time
import random
import threading
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from concurrent.futures import Future

from config import RaftConfig
from storage import Storage, FileStorage, LogEntry
from log import RaftLog
from state_machine import StateMachine, KeyValueStateMachine
from rpc import RPCProvider, InMemoryRPC


class NodeState(Enum):
    """Possible states for a Raft node"""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class RaftNode:
    """
    Core Raft consensus node implementation
    """
    
    def __init__(
        self,
        node_id: str,
        peers: List[str],
        state_machine: StateMachine = None,
        storage: Storage = None,
        rpc: RPCProvider = None,
        config: RaftConfig = None
    ):
        """
        Initialize a Raft node
        
        Args:
            node_id: Unique identifier for this node
            peers: List of peer node IDs (not including self)
            state_machine: State machine to apply committed commands to
            storage: Storage backend for persistence
            rpc: RPC provider for network communication
            config: RaftConfig object
        """
        self.node_id = node_id
        self.peers = set(peers)
        self.all_nodes = {node_id} | self.peers
        
        # Config
        self.config = config or RaftConfig()
        
        # Components
        self.storage = storage or FileStorage(f"/tmp/raft/{node_id}", node_id)
        self.log = RaftLog(self.storage)
        self.state_machine = state_machine or KeyValueStateMachine()
        self.rpc = rpc # Must be set/started
        
        # Restore state
        current_term, voted_for = self.storage.load_state()
        self.current_term = current_term
        self.voted_for = voted_for
        
        # Restore state machine from snapshot
        snapshot_bytes, last_index, last_term = self.storage.load_snapshot()
        if snapshot_bytes:
            self.state_machine.restore(snapshot_bytes)
            # Log already handles last_included_index/term via storage
            
        # Volatile state
        self.commit_index = self.log.last_included_index
        self.last_applied = self.log.last_included_index
        self.state = NodeState.FOLLOWER
        
        # Volatile state (leaders)
        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}
        
        # Pending commands (index -> Future)
        self.pending_commits: Dict[int, Future] = {}
        
        # Timing
        self.last_heartbeat = time.time()
        self.election_timeout = self._random_election_timeout()
        
        # Threading
        self.lock = threading.RLock()
        self.running = False
        self.election_timer = None
        self.heartbeat_timer = None
        
        # Start RPC if provided
        if self.rpc:
            self.rpc.start(self)
        
    def _random_election_timeout(self) -> float:
        return random.uniform(
            self.config.election_timeout_min / 1000.0,
            self.config.election_timeout_max / 1000.0
        )
    
    def start(self):
        """Start the Raft node"""
        with self.lock:
            if self.running:
                return
            self.running = True
            self._start_election_timer()
            print(f"[{self.node_id}] Started as FOLLOWER in term {self.current_term}")
    
    def stop(self):
        """Stop the Raft node gracefully"""
        with self.lock:
            self.running = False
            if self.election_timer:
                self.election_timer.cancel()
            if self.heartbeat_timer:
                self.heartbeat_timer.cancel()
            if self.rpc:
                self.rpc.stop()
            print(f"[{self.node_id}] Stopped")
    
    def shutdown(self):
        self.stop()
    
    def _save_state(self):
        """Save current term and voted_for"""
        self.storage.save_state(self.current_term, self.voted_for)

    def _start_election_timer(self):
        if self.election_timer:
            self.election_timer.cancel()
        
        self.election_timeout = self._random_election_timeout()
        self.election_timer = threading.Timer(
            self.election_timeout,
            self._election_timeout_handler
        )
        self.election_timer.start()
    
    def _election_timeout_handler(self):
        with self.lock:
            if not self.running or self.state == NodeState.LEADER:
                return
            self._start_election()
    
    def _schedule_next_heartbeat(self):
        if self.state != NodeState.LEADER or not self.running:
            return
        
        self.heartbeat_timer = threading.Timer(
            self.config.heartbeat_interval / 1000.0,
            self._send_heartbeats
        )
        self.heartbeat_timer.start()
    
    def _start_election(self):
        self.current_term += 1
        self.state = NodeState.CANDIDATE
        self.voted_for = self.node_id
        self._save_state()
        
        print(f"[{self.node_id}] Starting election for term {self.current_term}")
        
        self._start_election_timer()
        
        votes_received = {self.node_id}
        
        # Prepare RPC arguments
        last_log_index = len(self.log)
        last_log_term = self.log.get_term(last_log_index)
        
        # Send RequestVote in parallel (using threads here for simplicity, 
        # normally RPC lib handles async)
        for peer in self.peers:
            threading.Thread(
                target=self._request_vote_worker,
                args=(peer, self.current_term, last_log_index, last_log_term, votes_received)
            ).start()

    def _request_vote_worker(self, peer, term, last_log_index, last_log_term, votes_received):
        if not self.rpc: return
        
        try:
            reply_term, vote_granted = self.rpc.send_request_vote(
                peer, term, self.node_id, last_log_index, last_log_term
            )
            
            with self.lock:
                if not self.running or self.state != NodeState.CANDIDATE:
                    return
                
                if reply_term > self.current_term:
                    self._update_term(reply_term)
                    return
                
                if vote_granted:
                    votes_received.add(peer)
                    if len(votes_received) > len(self.all_nodes) // 2:
                        self._become_leader()
        except Exception as e:
            # print(f"Error requesting vote from {peer}: {e}")
            pass

    def _become_leader(self):
        print(f"[{self.node_id}] Became LEADER for term {self.current_term}")
        self.state = NodeState.LEADER
        
        last_log_index = len(self.log)
        for peer in self.peers:
            self.next_index[peer] = last_log_index + 1
            self.match_index[peer] = 0
        
        if self.election_timer:
            self.election_timer.cancel()
            
        # Send initial heartbeat immediately
        self._send_heartbeats()
    
    def _send_heartbeats(self):
        if self.state != NodeState.LEADER or not self.running:
            return
        
        for peer in self.peers:
            threading.Thread(target=self._append_entries_worker, args=(peer,)).start()
        
        self._schedule_next_heartbeat()
        
    def _append_entries_worker(self, peer):
        if not self.rpc: return
        
        with self.lock:
            if self.state != NodeState.LEADER: return
            
            next_idx = self.next_index.get(peer, 1)
            prev_log_index = next_idx - 1
            
            # If prev_log_index is inside snapshot, we should send snapshot instead
            # For this iteration, we'll focus on log replication. 
            # Production would check: if prev_log_index < self.log.last_included_index: send_snapshot()
            if prev_log_index < self.log.last_included_index:
                 # print(f"Peer {peer} lags behind snapshot. InstallSnapshot not implemented yet.")
                 return
            
            prev_log_term = self.log.get_term(prev_log_index)
            entries = self.log.get_entries(next_idx)
            leader_commit = self.commit_index
            current_term = self.current_term
            
        try:
            reply_term, success = self.rpc.send_append_entries(
                peer, current_term, self.node_id, prev_log_index, prev_log_term, entries, leader_commit
            )
            
            with self.lock:
                if not self.running: return
                
                if reply_term > self.current_term:
                    self._update_term(reply_term)
                    return
                
                if self.state != NodeState.LEADER: return
                
                if success:
                    # Update match_index and next_index
                    num_entries = len(entries)
                    if num_entries > 0:
                        self.match_index[peer] = prev_log_index + num_entries
                        self.next_index[peer] = self.match_index[peer] + 1
                        self._update_commit_index()
                else:
                    # Decrement next_index and retry later (next heartbeat)
                    # Simple optimization: decrement by 1 or skip to conflict index
                    self.next_index[peer] = max(1, self.next_index[peer] - 1)
                    
        except Exception as e:
            # print(f"Error sending AppendEntries to {peer}: {e}")
            pass

    def _update_commit_index(self):
        """Check if we can advance commit_index"""
        # Finds match_index N such that N > commit_index and majority of match_index[i] >= N
        # and log[N].term == current_term
        match_indices = sorted(self.match_index.values() if self.match_index else [])
        match_indices.append(len(self.log)) # Leader always matches itself
        match_indices.sort()
        
        # Element at index len(all_nodes)//2 (from end?)
        # Let's do it explicitly:
        # We need N such that count(match_index >= N) > total // 2
        
        # Sort desc
        matches = sorted(
            list(self.match_index.values()) + [len(self.log)],
            reverse=True
        )
        majority_index = len(self.all_nodes) // 2
        N = matches[majority_index]
        
        if N > self.commit_index and self.log.get_term(N) == self.current_term:
            self.commit_index = N
            self._apply_committed_entries()

    def submit_command(self, command: dict) -> Future:
        """
        Submit a command for consensus
        Returns a Future that resolves when command is applied.
        """
        with self.lock:
            if self.state != NodeState.LEADER:
                f = Future()
                f.set_exception(Exception("Not Leader"))
                return f
            
            index = len(self.log) + 1
            entry = LogEntry(
                term=self.current_term,
                index=index,
                command=command
            )
            self.log.append(entry)
            
            # Create future
            f = Future()
            self.pending_commits[index] = f
            
            # print(f"[{self.node_id}] Appended command to log at index {index}")
            
            # Trigger replication immediately for lower latency
            self._send_heartbeats()
            
            return f

    def _apply_committed_entries(self):
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            
            result = self.state_machine.apply(entry.command)
            
            # Notify pending future if this node is leader
            if self.last_applied in self.pending_commits:
                self.pending_commits[self.last_applied].set_result(result)
                del self.pending_commits[self.last_applied]
                
            print(f"[{self.node_id}] Applied entry {self.last_applied}: {entry.command}")
            
            # Check for snapshotting
            self._check_snapshot()

    def _check_snapshot(self):
        """Check if log needs compaction"""
        if self.last_applied - self.log.last_included_index >= self.config.snapshot_interval:
            print(f"[{self.node_id}] Creating snapshot at index {self.last_applied}")
            snapshot = self.state_machine.snapshot()
            last_idx = self.last_applied
            last_term = self.log.get_term(last_idx)
            
            self.log.compact(last_idx, last_term, snapshot)

    def handle_request_vote(self, term, candidate_id, last_log_index, last_log_term) -> tuple[int, bool]:
        with self.lock:
            if term < self.current_term:
                return self.current_term, False
            
            if term > self.current_term:
                self._update_term(term)
            
            can_vote = (self.voted_for is None or self.voted_for == candidate_id)
            
            # Log completeness check
            our_last_index = len(self.log)
            our_last_term = self.log.get_term(our_last_index)
            
            log_is_fresh = (
                last_log_term > our_last_term or
                (last_log_term == our_last_term and last_log_index >= our_last_index)
            )
            
            if can_vote and log_is_fresh:
                self.voted_for = candidate_id
                self._save_state()
                self._start_election_timer()
                return self.current_term, True
            
            return self.current_term, False

    def handle_append_entries(self, term, leader_id, prev_log_index, prev_log_term, entries, leader_commit) -> tuple[int, bool]:
        with self.lock:
            if term < self.current_term:
                return self.current_term, False
            
            if term > self.current_term:
                self._update_term(term)
                
            self._start_election_timer()
            
            # Consistency check
            if not self.log.match_log(prev_log_index, prev_log_term):
                return self.current_term, False
                
            # Append new entries
            for i, entry in enumerate(entries):
                # entry is LogEntry object
                # Check conflict
                idx = prev_log_index + 1 + i
                if idx <= len(self.log):
                    if self.log.get_term(idx) != entry.term:
                        self.log.truncate(idx)
                        self.log.append(entry)
                else:
                    self.log.append(entry)
            
            if leader_commit > self.commit_index:
                self.commit_index = min(leader_commit, len(self.log))
                self._apply_committed_entries()
            
            return self.current_term, True

    def _update_term(self, new_term):
        self.current_term = new_term
        self.voted_for = None
        self._save_state()
        self.state = NodeState.FOLLOWER
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()
        self._start_election_timer()

    # Public Getters
    @property
    def is_leader(self) -> bool:
        return self.state == NodeState.LEADER
        
    def read_state(self, key: str) -> Any:
        # Production: ReadIndex or Lease
        return self.state_machine.apply({"op": "get", "key": key})