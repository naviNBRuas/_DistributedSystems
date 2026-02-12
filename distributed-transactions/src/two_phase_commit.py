"""
Two-Phase Commit (2PC) Implementation

Coordinator and Participant implementations for atomic
distributed transactions across multiple services.
"""

import time
import threading
import uuid
from enum import Enum
from typing import List, Dict, Callable, Any, Optional, Union
from dataclasses import dataclass, field
import logging

# Configure logger
logger = logging.getLogger(__name__)


class TransactionState(Enum):
    """Transaction state machine"""
    INIT = "INIT"
    PREPARING = "PREPARING"
    PREPARED = "PREPARED"
    COMMITTING = "COMMITTING"
    COMMITTED = "COMMITTED"
    ABORTING = "ABORTING"
    ABORTED = "ABORTED"


class VoteResponse(Enum):
    """Participant vote response"""
    YES = "YES"
    NO = "NO"


@dataclass
class TransactionContext:
    """Transaction context and state"""
    txn_id: str
    operations: List[tuple] = field(default_factory=list)
    state: TransactionState = TransactionState.INIT
    votes: Dict[str, VoteResponse] = field(default_factory=dict)
    timeout: float = 30.0  # seconds
    start_time: float = field(default_factory=time.time)
    
    def is_expired(self) -> bool:
        """Check if transaction has timed out"""
        return time.time() - self.start_time > self.timeout
    
    def can_commit(self, expected_participant_count: int) -> bool:
        """Check if all participants voted YES"""
        if not self.votes:
            return False
        if len(self.votes) != expected_participant_count:
            return False
        return all(v == VoteResponse.YES for v in self.votes.values())


class TwoPhaseParticipant:
    """
    Two-Phase Commit Participant interface.
    
    Responds to coordinator requests with YES/NO vote.
    """
    
    def __init__(self, participant_id: str):
        """
        Initialize participant
        
        Args:
            participant_id: Unique participant identifier
        """
        self.participant_id = participant_id
        self.undo_logs: Dict[str, List[Callable]] = {}
        self.locks = threading.Lock()
        
        # Failure simulation flags
        self.should_fail_prepare = False
        self.should_fail_commit = False
        self.should_fail_abort = False
        self.delay_prepare = 0.0
    
    def prepare(self, txn_id: str, operation: tuple) -> VoteResponse:
        """
        Prepare phase: check if can commit
        
        Args:
            txn_id: Transaction ID
            operation: Operation tuple (action, args) or (participant, action, args)
            
        Returns:
            VoteResponse: YES or NO
        """
        if self.delay_prepare > 0:
            time.sleep(self.delay_prepare)

        if self.should_fail_prepare:
            logger.warning(f"[Participant {self.participant_id}] Simulated prepare failure for {txn_id}")
            return VoteResponse.NO

        logger.info(f"[Participant {self.participant_id}] Preparing {txn_id} with op {operation}")
        
        with self.locks:
            try:
                # Validate and reserve resources
                if not self._validate_operation(operation):
                    return VoteResponse.NO
                
                # Create undo log (simplistic implementation)
                undo_fn = self._create_undo(txn_id, operation)
                if txn_id not in self.undo_logs:
                    self.undo_logs[txn_id] = []
                self.undo_logs[txn_id].append(undo_fn)
                
                return VoteResponse.YES
            
            except Exception as e:
                logger.error(f"[Participant {self.participant_id}] Prepare exception: {e}")
                return VoteResponse.NO
    
    def commit(self, txn_id: str) -> bool:
        """
        Commit transaction
        
        Args:
            txn_id: Transaction ID
            
        Returns:
            True if committed successfully
        """
        if self.should_fail_commit:
             logger.warning(f"[Participant {self.participant_id}] Simulated commit failure for {txn_id}")
             return False

        logger.info(f"[Participant {self.participant_id}] Committing {txn_id}")
        
        with self.locks:
            # In a real system, we would apply changes permanently here
            # For this simulation, we just clear the undo log
            if txn_id in self.undo_logs:
                del self.undo_logs[txn_id]
        
        return True
    
    def abort(self, txn_id: str) -> bool:
        """
        Abort transaction and rollback
        
        Args:
            txn_id: Transaction ID
            
        Returns:
            True if aborted successfully
        """
        if self.should_fail_abort:
             logger.warning(f"[Participant {self.participant_id}] Simulated abort failure for {txn_id}")
             return False

        logger.info(f"[Participant {self.participant_id}] Aborting {txn_id}")
        
        with self.locks:
            # Rollback: execute undo operations in reverse order
            if txn_id in self.undo_logs:
                for undo_fn in reversed(self.undo_logs[txn_id]):
                    try:
                        undo_fn()
                    except Exception as e:
                        logger.error(f"Undo operation failed: {e}")
                
                del self.undo_logs[txn_id]
        
        return True
    
    def _validate_operation(self, operation: tuple) -> bool:
        """Validate operation can be performed"""
        # Hook for validation logic
        return True
    
    def _create_undo(self, txn_id: str, operation: tuple) -> Callable:
        """Create undo function for operation"""
        return lambda: logger.debug(f"[Participant {self.participant_id}] Undoing {operation}")


class TwoPhaseCoordinator:
    """
    Two-Phase Commit Coordinator
    
    Orchestrates distributed transactions with prepare and commit phases.
    """
    
    def __init__(self, timeout: float = 30.0):
        """
        Initialize coordinator
        
        Args:
            timeout: Transaction timeout in seconds
        """
        self.timeout = timeout
        self.transactions: Dict[str, TransactionContext] = {}
        self.locks = threading.Lock()
        self.participants: Dict[str, TwoPhaseParticipant] = {}
    
    def register_participant(self, participant: TwoPhaseParticipant):
        """Register a participant with the coordinator"""
        self.participants[participant.participant_id] = participant

    def begin_transaction(self, operations: List[tuple]) -> str:
        """
        Begin a new transaction
        
        Args:
            operations: List of (participant_id, action, args) tuples
            
        Returns:
            Transaction ID
        """
        txn_id = str(uuid.uuid4())
        
        with self.locks:
            ctx = TransactionContext(
                txn_id=txn_id,
                operations=operations,
                timeout=self.timeout
            )
            self.transactions[txn_id] = ctx
        
        logger.info(f"[Coordinator] Transaction {txn_id} started")
        return txn_id
    
    def execute_transaction(self, operations: List[tuple]) -> bool:
        """
        Execute complete 2PC transaction
        
        Args:
            operations: List of (participant_id, action, args) tuples
            
        Returns:
            True if transaction committed successfully
        """
        # Validate participants exist
        for op in operations:
            pid = op[0]
            if pid not in self.participants:
                logger.error(f"[Coordinator] Unknown participant: {pid}")
                return False

        txn_id = self.begin_transaction(operations)
        
        try:
            if self.prepare(txn_id):
                return self.commit(txn_id)
            else:
                self.abort(txn_id)
                return False
        
        except Exception as e:
            logger.error(f"[Coordinator] Transaction {txn_id} failed: {e}")
            self.abort(txn_id)
            return False

    def prepare(self, txn_id: str) -> bool:
        """
        Prepare phase: ask participants if they can commit
        """
        with self.locks:
            if txn_id not in self.transactions:
                raise ValueError(f"Unknown transaction: {txn_id}")
            ctx = self.transactions[txn_id]
            ctx.state = TransactionState.PREPARING

        try:
            # Group operations by participant
            participant_ops = {}
            for op in ctx.operations:
                pid = op[0]
                # Pass the full op or just the action/args? Passing full op tuple for now
                participant_ops[pid] = op 

            # Send prepare to relevant participants
            for pid, op in participant_ops.items():
                if ctx.is_expired():
                    logger.warning(f"[Coordinator] Transaction {txn_id} timed out during PREPARE")
                    return False

                vote = self._send_prepare(txn_id, pid, op)
                
                with self.locks:
                    ctx.votes[pid] = vote
                
                if vote == VoteResponse.NO:
                    logger.warning(f"[Coordinator] {pid} voted NO for {txn_id}")
                    return False

            with self.locks:
                # Check if we have votes from all participants involved in this transaction
                if ctx.can_commit(len(participant_ops)):
                    # Final timeout check before declaring prepared
                    if ctx.is_expired():
                        logger.warning(f"[Coordinator] Transaction {txn_id} timed out after receiving votes")
                        return False
                        
                    ctx.state = TransactionState.PREPARED
                    logger.info(f"[Coordinator] Prepare phase complete for {txn_id}")
                    return True
                else:
                    return False
        
        except Exception as e:
            logger.error(f"[Coordinator] Prepare phase exception for {txn_id}: {e}")
            return False

    def commit(self, txn_id: str) -> bool:
        """
        Commit phase: tell participants to commit
        """
        with self.locks:
            if txn_id not in self.transactions:
                raise ValueError(f"Unknown transaction: {txn_id}")
            ctx = self.transactions[txn_id]
            
            # Re-verify before committing
            involved_participants = set(op[0] for op in ctx.operations)
            if not ctx.can_commit(len(involved_participants)):
                logger.error(f"[Coordinator] Cannot commit {txn_id}: consensus not reached")
                return False
            
            ctx.state = TransactionState.COMMITTING

        all_committed = True
        involved_participants = set(op[0] for op in ctx.operations)

        for pid in involved_participants:
            if not self._send_commit(txn_id, pid):
                all_committed = False
                logger.error(f"[Coordinator] {pid} failed to commit {txn_id}")
                # In a real system, we'd need a recovery mechanism here (retry, alarm, etc.)
        
        with self.locks:
            if all_committed:
                ctx.state = TransactionState.COMMITTED
                logger.info(f"[Coordinator] Transaction {txn_id} fully committed")
                return True
            else:
                # Partial commit is a critical error in strict 2PC
                logger.critical(f"[Coordinator] Transaction {txn_id} partially committed! Consistency broken.")
                return False

    def abort(self, txn_id: str) -> bool:
        """
        Abort transaction
        """
        with self.locks:
            if txn_id not in self.transactions:
                return False
            ctx = self.transactions[txn_id]
            # Don't abort if already committed
            if ctx.state == TransactionState.COMMITTED:
                 return False
            
            ctx.state = TransactionState.ABORTING

        involved_participants = set(op[0] for op in ctx.operations)
        for pid in involved_participants:
             self._send_abort(txn_id, pid)
            
        with self.locks:
            ctx.state = TransactionState.ABORTED
            logger.info(f"[Coordinator] Transaction {txn_id} aborted")
            return True

    def _send_prepare(self, txn_id: str, participant_id: str, operation: tuple) -> VoteResponse:
        """Send prepare request to participant"""
        participant = self.participants.get(participant_id)
        if not participant:
            logger.error(f"Participant {participant_id} not found")
            return VoteResponse.NO
        
        try:
            return participant.prepare(txn_id, operation)
        except Exception:
            return VoteResponse.NO

    def _send_commit(self, txn_id: str, participant_id: str) -> bool:
        """Send commit request to participant"""
        participant = self.participants.get(participant_id)
        if not participant:
            return False
        try:
            return participant.commit(txn_id)
        except Exception:
            return False

    def _send_abort(self, txn_id: str, participant_id: str) -> bool:
        """Send abort request to participant"""
        participant = self.participants.get(participant_id)
        if not participant:
            return False
        try:
            return participant.abort(txn_id)
        except Exception:
            return False