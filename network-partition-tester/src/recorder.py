"""
Scenario Recorder

Record and replay network failure scenarios.
"""

import time
import yaml # type: ignore
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class RecordedEvent:
    """A single recorded event in a scenario"""
    timestamp: float
    type: str
    params: Dict[str, Any]


class ScenarioRecorder:
    """
    Records operations performed on the coordinator
    for later replay or analysis.
    """
    
    def __init__(self):
        self.events: List[RecordedEvent] = []
        self.start_time: float = 0
        self.recording: bool = False
        
    def start(self, name: str = "untitled"):
        """Start recording"""
        self.events = []
        self.start_time = time.time()
        self.recording = True
        print(f"[Recorder] Started recording: {name}")
        
    def stop(self):
        """Stop recording"""
        self.recording = False
        print(f"[Recorder] Stopped recording. {len(self.events)} events captured.")
        
    def record(self, event_type: str, **params):
        """
        Record an event.
        
        Args:
            event_type: Type of event (e.g., 'create_partition')
            **params: Event parameters
        """
        if not self.recording:
            return
            
        event = RecordedEvent(
            timestamp=time.time() - self.start_time,
            type=event_type,
            params=params
        )
        self.events.append(event)
        
    def save(self, filepath: str):
        """Save recorded scenario to YAML file"""
        if not filepath.endswith('.yaml') and not filepath.endswith('.yml'):
            filepath += '.yaml'
            
        data = {
            "version": "1.0",
            "events": [asdict(e) for e in self.events]
        }
        
        try:
            with open(filepath, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
            print(f"[Recorder] Saved scenario to {filepath}")
        except ImportError:
            print("[Recorder] Error: pyyaml not installed. Cannot save to YAML.")
        except Exception as e:
            print(f"[Recorder] Error saving file: {e}")


class ScenarioReplayer:
    """
    Replays recorded scenarios.
    """
    
    def __init__(self, coordinator=None):
        self.coordinator = coordinator
        self.events: List[Dict] = []
        
    def load(self, filepath: str):
        """Load scenario from YAML file"""
        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
                self.events = data.get("events", [])
            print(f"[Replayer] Loaded {len(self.events)} events from {filepath}")
        except ImportError:
            print("[Replayer] Error: pyyaml not installed. Cannot load YAML.")
        except Exception as e:
            print(f"[Replayer] Error loading file: {e}")
            
    def replay(self):
        """Replay the loaded scenario"""
        if not self.events:
            print("[Replayer] No events to replay")
            return
            
        print("[Replayer] Starting replay...")
        start_time = time.time()
        
        # Sort events by timestamp just in case
        sorted_events = sorted(self.events, key=lambda e: e['timestamp'])
        
        for event in sorted_events:
            # Wait until event time
            target_time = start_time + event['timestamp']
            sleep_time = target_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            self._execute_event(event)
            
        print("[Replayer] Replay complete")
        
    def _execute_event(self, event: Dict):
        """Execute a single event"""
        etype = event['type']
        params = event['params']
        
        print(f"[Replayer] Executing: {etype}")
        
        if not self.coordinator:
            print("  (No coordinator attached - skipping execution)")
            return

        # Dispatch to coordinator methods
        if etype == 'create_partition':
            self.coordinator.create_partition(**params)
        elif etype == 'heal_partition':
            self.coordinator.heal_partition(**params)
        elif etype == 'crash_node':
            self.coordinator.crash_node(**params)
        elif etype == 'recover_node':
            self.coordinator.recover_node(**params)
        else:
            print(f"  Unknown event type: {etype}")
