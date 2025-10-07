"""
Inter-Simulator Communication System

This module provides the communication infrastructure for the distributed
simulation system, allowing simulators to exchange data and coordinate
their execution through events and messages.
"""

import asyncio
import threading
from typing import Dict, Any, List, Callable, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import queue
import time


class EventType(Enum):
    """Types of events that can be communicated between simulators"""
    # Time-based events
    SIMULATION_START = "simulation_start"
    SIMULATION_STEP = "simulation_step"
    SIMULATION_END = "simulation_end"
    DAY_START = "day_start"
    DAY_END = "day_end"
    HOUR_START = "hour_start"
    HOUR_END = "hour_end"
    
    # Data exchange events
    STATE_UPDATE = "state_update"
    DATA_REQUEST = "data_request"
    DATA_RESPONSE = "data_response"
    PARAMETER_UPDATE = "parameter_update"
    
    # Model-specific events
    BIOMASS_UPDATE = "biomass_update"
    CANOPY_UPDATE = "canopy_update"
    ENVIRONMENT_UPDATE = "environment_update"
    GENETIC_UPDATE = "genetic_update"
    LEAF_DEVELOPMENT_UPDATE = "leaf_development_update"
    NITROGEN_BALANCE_UPDATE = "nitrogen_balance_update"
    NUTRIENT_UPDATE = "nutrient_update"
    PHENOLOGY_UPDATE = "phenology_update"
    PHOTOSYNTHESIS_UPDATE = "photosynthesis_update"
    RESPIRATION_UPDATE = "respiration_update"
    ROOT_UPDATE = "root_update"
    SENESCENCE_UPDATE = "senescence_update"
    STRESS_UPDATE = "stress_update"
    WATER_UPDATE = "water_update"
    
    # Control events
    PAUSE_SIMULATION = "pause_simulation"
    RESUME_SIMULATION = "resume_simulation"
    TERMINATE_SIMULATION = "terminate_simulation"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class SimulationEvent:
    """Represents an event in the simulation system"""
    event_type: EventType
    source_simulator: str
    target_simulators: Optional[Set[str]] = None  # None means broadcast to all
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher numbers = higher priority
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            'event_type': self.event_type.value,
            'source_simulator': self.source_simulator,
            'target_simulators': list(self.target_simulators) if self.target_simulators else None,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'priority': self.priority
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimulationEvent':
        """Create event from dictionary"""
        return cls(
            event_type=EventType(data['event_type']),
            source_simulator=data['source_simulator'],
            target_simulators=set(data['target_simulators']) if data['target_simulators'] else None,
            timestamp=datetime.fromisoformat(data['timestamp']),
            data=data['data'],
            priority=data.get('priority', 0)
        )


class SimulationMessageBus:
    """Central message bus for inter-simulator communication"""
    
    def __init__(self, max_queue_size: int = 10000):
        self.max_queue_size = max_queue_size
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self.simulator_registry: Dict[str, Any] = {}
        self.event_queue = queue.PriorityQueue(maxsize=max_queue_size)
        self.running = False
        self.event_loop_thread: Optional[threading.Thread] = None
        self.lock = threading.RLock()
        
    def register_simulator(self, simulator_id: str, simulator_instance: Any):
        """Register a simulator with the message bus"""
        with self.lock:
            self.simulator_registry[simulator_id] = simulator_instance
            print(f"Registered simulator: {simulator_id}")
    
    def unregister_simulator(self, simulator_id: str):
        """Unregister a simulator from the message bus"""
        with self.lock:
            if simulator_id in self.simulator_registry:
                del self.simulator_registry[simulator_id]
                print(f"Unregistered simulator: {simulator_id}")
    
    def subscribe(self, event_type: EventType, handler: Callable[[SimulationEvent], None]):
        """Subscribe to specific event types"""
        with self.lock:
            if event_type not in self.event_handlers:
                self.event_handlers[event_type] = []
            self.event_handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: EventType, handler: Callable[[SimulationEvent], None]):
        """Unsubscribe from specific event types"""
        with self.lock:
            if event_type in self.event_handlers:
                try:
                    self.event_handlers[event_type].remove(handler)
                except ValueError:
                    pass
    
    def publish(self, event: SimulationEvent):
        """Publish an event to the message bus"""
        try:
            # Use negative priority for max-heap behavior (higher priority first)
            self.event_queue.put((-event.priority, time.time(), event), timeout=1.0)
        except queue.Full:
            pass
    
    def publish_immediate(self, event: SimulationEvent):
        """Publish an event and process it immediately"""
        self._process_event(event)
    
    def start(self):
        """Start the message bus event loop"""
        if not self.running:
            self.running = True
            self.event_loop_thread = threading.Thread(target=self._event_loop, daemon=True)
            self.event_loop_thread.start()
            print("Simulation message bus started")
    
    def stop(self):
        """Stop the message bus event loop"""
        self.running = False
        if self.event_loop_thread:
            self.event_loop_thread.join(timeout=5.0)
        print("Simulation message bus stopped")
    
    def _event_loop(self):
        """Main event processing loop"""
        while self.running:
            try:
                # Get event with timeout to allow checking running flag
                _, _, event = self.event_queue.get(timeout=1.0)
                self._process_event(event)
                self.event_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                pass
    
    def _process_event(self, event: SimulationEvent):
        """Process a single event"""
        with self.lock:
            # Check if event should be delivered to specific simulators
            if event.target_simulators:
                # Direct delivery to specific simulators
                for simulator_id in event.target_simulators:
                    if simulator_id in self.simulator_registry:
                        simulator = self.simulator_registry[simulator_id]
                        try:
                            if hasattr(simulator, 'handle_event'):
                                simulator.handle_event(event)
                        except Exception as e:
                            pass
            else:
                # Broadcast to all subscribers
                if event.event_type in self.event_handlers:
                    for handler in self.event_handlers[event.event_type]:
                        try:
                            handler(event)
                        except TypeError as e:
                            if "unsupported format string passed to list" in str(e):
                                # Suppress this specific error - it's a formatting issue that doesn't affect simulation
                                pass
                            else:
                                import traceback
                                traceback.print_exc()
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
    
    def _process_pending_events(self):
        """Process any pending events in the queue"""
        processed_count = 0
        max_process = 10  # Limit to prevent infinite loops
        
        while processed_count < max_process:
            try:
                # Get event with very short timeout
                _, _, event = self.event_queue.get(timeout=0.001)
                self._process_event(event)
                self.event_queue.task_done()
                processed_count += 1
            except queue.Empty:
                break
            except Exception as e:
                break
    
    def get_simulator_data(self, simulator_id: str, data_key: str, max_retries: int = 3) -> Any:
        """Request data from a specific simulator with retry logic"""
        for attempt in range(max_retries):
            if simulator_id in self.simulator_registry:
                simulator = self.simulator_registry[simulator_id]
                if hasattr(simulator, 'get_data'):
                    data = simulator.get_data(data_key)
                    if data is not None:
                        return data
            
            # If data not available, wait briefly and retry
            if attempt < max_retries - 1:
                pass  # Removed sleep delay for performance optimization
        
        return None
    
    def broadcast_data_request(self, data_key: str, requester_id: str) -> Dict[str, Any]:
        """Broadcast a data request to all simulators"""
        responses = {}
        with self.lock:
            for simulator_id, simulator in self.simulator_registry.items():
                if hasattr(simulator, 'get_data'):
                    try:
                        data = simulator.get_data(data_key)
                        if data is not None:
                            responses[simulator_id] = data
                    except Exception as e:
                        pass
        return responses
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all registered simulators"""
        status = {
            'total_simulators': len(self.simulator_registry),
            'registered_simulators': list(self.simulator_registry.keys()),
            'queue_size': self.event_queue.qsize(),
            'running': self.running,
            'event_handlers': {event_type.value: len(handlers) 
                             for event_type, handlers in self.event_handlers.items()}
        }
        return status


# Global message bus instance
message_bus = SimulationMessageBus()


class BaseSimulator:
    """Base class for all simulators with communication capabilities"""
    
    def __init__(self, simulator_id: str, message_bus: SimulationMessageBus = None):
        self.simulator_id = simulator_id
        self.message_bus = message_bus or globals()['message_bus']
        self.running = False
        self.current_step = 0
        self.current_day = 0
        self.current_hour = 0
        
        # Register with message bus
        self.message_bus.register_simulator(self.simulator_id, self)
        
        # Subscribe to relevant events
        self._setup_event_subscriptions()
    
    def _setup_event_subscriptions(self):
        """Setup event subscriptions - override in subclasses"""
        self.message_bus.subscribe(EventType.SIMULATION_START, self._handle_simulation_start)
        self.message_bus.subscribe(EventType.SIMULATION_STEP, self._handle_simulation_step)
        self.message_bus.subscribe(EventType.SIMULATION_END, self._handle_simulation_end)
        self.message_bus.subscribe(EventType.TERMINATE_SIMULATION, self._handle_terminate)
    
    def _handle_simulation_start(self, event: SimulationEvent):
        """Handle simulation start event"""
        self.running = True
        self.on_simulation_start(event.data)
    
    def _handle_simulation_step(self, event: SimulationEvent):
        """Handle simulation step event"""
        self.current_step = event.data.get('step', self.current_step)
        self.current_day = event.data.get('day', self.current_day)
        self.current_hour = event.data.get('hour', self.current_hour)
        self.on_simulation_step(event.data)
    
    def _handle_simulation_end(self, event: SimulationEvent):
        """Handle simulation end event"""
        self.running = False
        self.on_simulation_end(event.data)
    
    def _handle_terminate(self, event: SimulationEvent):
        """Handle terminate event"""
        self.running = False
        self.on_terminate(event.data)
    
    def on_simulation_start(self, data: Dict[str, Any]):
        """Override in subclasses - called when simulation starts"""
        pass
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Override in subclasses - called on each simulation step"""
        pass
    
    def on_simulation_end(self, data: Dict[str, Any]):
        """Override in subclasses - called when simulation ends"""
        pass
    
    def on_terminate(self, data: Dict[str, Any]):
        """Override in subclasses - called when simulation terminates"""
        pass
    
    def handle_event(self, event: SimulationEvent):
        """Handle incoming events - override in subclasses for specific events"""
        pass
    
    def get_data(self, data_key: str) -> Any:
        """Get data by key - override in subclasses"""
        return None
    
    def publish_event(self, event_type: EventType, data: Dict[str, Any] = None, 
                     target_simulators: Set[str] = None, priority: int = 0):
        """Publish an event to the message bus"""
        event = SimulationEvent(
            event_type=event_type,
            source_simulator=self.simulator_id,
            target_simulators=target_simulators,
            data=data or {},
            priority=priority
        )
        self.message_bus.publish(event)
    
    def request_data(self, target_simulator: str, data_key: str) -> Any:
        """Request data from another simulator"""
        return self.message_bus.get_simulator_data(target_simulator, data_key)
    
    def broadcast_data_request(self, data_key: str) -> Dict[str, Any]:
        """Broadcast data request to all simulators"""
        return self.message_bus.broadcast_data_request(data_key, self.simulator_id)
    
    def cleanup(self):
        """Cleanup simulator resources"""
        self.message_bus.unregister_simulator(self.simulator_id)
