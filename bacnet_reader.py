"""
BACnet Reader - OOP Implementation
Project: BACnet Communication Library
"""

import time
import threading
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

try:
    from bacpypes.core import run, stop
    from bacpypes.app import Application
    from bacpypes.local.device import LocalDeviceObject
    from bacpypes.object import AnalogInputObject, AnalogOutputObject, BinaryInputObject, BinaryOutputObject
    from bacpypes.object import AnalogValueObject, BinaryValueObject, MultiStateInputObject, MultiStateOutputObject
    from bacpypes.object import MultiStateValueObject, StringValueObject, DeviceObject
    from bacpypes.service.device import WhoIsIAmServices
    from bacpypes.service.object import ReadWritePropertyServices
    from bacpypes.pdu import Address, GlobalBroadcast
    from bacpypes.apdu import WhoIsRequest, IAmRequest, ReadPropertyRequest, WritePropertyRequest
    from bacpypes.primitivedata import Real, Boolean, Unsigned, CharacterString
    from bacpypes.constructeddata import Array
    from bacpypes.basetypes import ServicesSupported
    BACNET_AVAILABLE = True
except ImportError:
    BACNET_AVAILABLE = False


class BACnetObjectType(Enum):
    """Enumeration for BACnet object types."""
    ANALOG_INPUT = "analogInput"
    ANALOG_OUTPUT = "analogOutput"
    ANALOG_VALUE = "analogValue"
    BINARY_INPUT = "binaryInput"
    BINARY_OUTPUT = "binaryOutput"
    BINARY_VALUE = "binaryValue"
    MULTI_STATE_INPUT = "multiStateInput"
    MULTI_STATE_OUTPUT = "multiStateOutput"
    MULTI_STATE_VALUE = "multiStateValue"
    STRING_VALUE = "stringValue"
    DEVICE = "device"


@dataclass
class BACnetObject:
    """Data class for BACnet object configuration."""
    object_type: BACnetObjectType
    instance_number: int
    name: str
    description: str
    unit: str = ""
    properties: Optional[Dict[str, Any]] = None


@dataclass
class BACnetDevice:
    """Data class for BACnet device information."""
    device_id: int
    address: str
    vendor_name: str
    object_count: int
    services_supported: Optional[Dict[str, bool]] = None


class SimpleLogger:
    """Simple logger for BACnet reader."""
    
    def __init__(self, log_level: int = 0):
        """
        Initialize logger.
        
        Args:
            log_level: Log level (0=info, 1=warning, 2=error)
        """
        self.log_level = log_level
    
    def log(self, data: Any, log_type: int = 0, visibility: str = "TD", tag: str = "BACnetReader") -> None:
        """
        Log a message.
        
        Args:
            data: Data to log
            log_type: Type of log (0=info, 1=warning, 2=error)
            visibility: Visibility level
            tag: Tag for the log
        """
        if log_type >= self.log_level:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            level_str = {0: "INFO", 1: "WARNING", 2: "ERROR"}.get(log_type, "INFO")
            print(f"[{timestamp}] [{level_str}] [{tag}] {data}")


class BACnetReader:
    """
    OOP wrapper for BACnet communication.
    
    This class provides a clean, object-oriented interface for BACnet
    device communication with object reading, writing, and discovery
    capabilities.
    """
    
    def __init__(
        self,
        device_id: str,
        device_address: str,
        port: int = 47808,
        timeout: float = 5.0,
        retry_count: int = 3,
        retry_delay: float = 1.0,
        logger: Optional[SimpleLogger] = None
    ):
        """
        Initialize BACnet Reader.
        
        Args:
            device_id: Unique identifier for the device
            device_address: BACnet device IP address
            port: BACnet port (default: 47808)
            timeout: Read timeout in seconds
            retry_count: Number of retry attempts on failure
            retry_delay: Delay between retries in seconds
            logger: Logger instance
        """
        if not BACNET_AVAILABLE:
            raise ImportError("BACnet library (bacpypes) is not available. Install with: pip install bacpypes")
        
        self.device_id = device_id
        self.device_type = "bacnet_device"
        self.device_address = device_address
        self.port = port
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        
        self.logger = logger or SimpleLogger()
        
        # BACnet application and device objects
        self.application: Optional[Application] = None
        self.local_device: Optional[LocalDeviceObject] = None
        self.is_connected = False
        self.last_read_time: Optional[float] = None
        
        # Object configuration
        self.objects: Dict[str, BACnetObject] = {}
        
        # Device discovery cache
        self.discovered_devices: Dict[int, BACnetDevice] = {}
        
        # Statistics
        self.stats = {
            "total_reads": 0,
            "successful_reads": 0,
            "failed_reads": 0,
            "objects_discovered": 0,
            "devices_discovered": 0,
            "connection_errors": 0,
            "last_error": None
        }
        
        # Health monitoring
        self.last_health_check: Optional[float] = None
        self.health_status = "unknown"
        self.health_monitor_thread: Optional[threading.Thread] = None
        self.health_monitor_running = False
        
        # Start health monitoring
        self._start_health_monitor()
    
    def add_object(self, bacnet_object: BACnetObject) -> None:
        """
        Add a BACnet object configuration.
        
        Args:
            bacnet_object: BACnet object configuration
        """
        object_key = f"{bacnet_object.object_type.value}_{bacnet_object.instance_number}"
        self.objects[object_key] = bacnet_object
        
        self.logger.log(
            data=f"Added BACnet object: {object_key} ({bacnet_object.name})",
            log_type=0,
            visibility="TD",
            tag="BACnetReader"
        )
    
    def add_objects(self, bacnet_objects: List[BACnetObject]) -> None:
        """
        Add multiple BACnet object configurations.
        
        Args:
            bacnet_objects: List of BACnet object configurations
        """
        for bacnet_object in bacnet_objects:
            self.add_object(bacnet_object)
    
    def connect(self) -> bool:
        """
        Establish connection to the BACnet device.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if self.is_connected:
                return True
            
            # Create local device object
            self.local_device = LocalDeviceObject(
                objectName=self.device_id,
                objectIdentifier=('device', 999),
                maxApduLengthAccepted=1024,
                segmentationSupported='segmentedBoth',
                vendorIdentifier=842
            )
            
            # Create BACnet application
            self.application = Application(self.local_device, self.device_address)
            
            # Start the application
            self.application.start()
            
            self.is_connected = True
            self.stats["connection_errors"] = 0
            self.stats["last_error"] = None
            
            self.logger.log(
                data=f"Connected to BACnet device at {self.device_address}:{self.port}",
                log_type=0,
                visibility="TD",
                tag="BACnetReader"
            )
            return True
            
        except Exception as e:
            self.is_connected = False
            self.stats["connection_errors"] += 1
            self.stats["last_error"] = str(e)
            
            self.logger.log(
                data=f"Failed to connect to BACnet device: {str(e)}",
                log_type=2,
                visibility="TD",
                tag="BACnetReader"
            )
            return False
    
    def disconnect(self) -> None:
        """Disconnect from the BACnet device."""
        try:
            if self.application and self.is_connected:
                self.application.stop()
                self.is_connected = False
                
                self.logger.log(
                    data=f"Disconnected from BACnet device",
                    log_type=0,
                    visibility="TD",
                    tag="BACnetReader"
                )
        except Exception as e:
            self.logger.log(
                data=f"Error during disconnect: {str(e)}",
                log_type=2,
                visibility="TD",
                tag="BACnetReader"
            )
    
    def read_object(self, bacnet_object: BACnetObject) -> Tuple[bool, Any]:
        """
        Read a single BACnet object.
        
        Args:
            bacnet_object: BACnet object to read
            
        Returns:
            Tuple of (success: bool, value: Any)
        """
        if not self.is_connected and not self.connect():
            return False, None
        
        for attempt in range(self.retry_count):
            try:
                # Create read request
                request = ReadPropertyRequest(
                    objectIdentifier=(bacnet_object.object_type.value, bacnet_object.instance_number),
                    propertyIdentifier='presentValue'
                )
                
                # Send request
                response = self.application.request(request)
                
                if response:
                    # Extract value from response
                    value = response.propertyValue.cast_out(Real)
                    
                    self.stats["successful_reads"] += 1
                    self.last_read_time = time.time()
                    
                    return True, value
                else:
                    raise Exception("No response received")
                
            except Exception as e:
                self.stats["failed_reads"] += 1
                self.stats["last_error"] = str(e)
                
                if attempt < self.retry_count - 1:
                    self.logger.log(
                        data=f"Read attempt {attempt + 1} failed, retrying: {str(e)}",
                        log_type=1,
                        visibility="TD",
                        tag="BACnetReader"
                    )
                    time.sleep(self.retry_delay)
                else:
                    self.logger.log(
                        data=f"All read attempts failed: {str(e)}",
                        log_type=2,
                        visibility="TD",
                        tag="BACnetReader"
                    )
                    return False, None
        
        return False, None
    
    def read_objects(self, object_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Read multiple BACnet objects.
        
        Args:
            object_names: List of object names to read. If None, reads all configured objects.
            
        Returns:
            Dictionary mapping object names to their values
        """
        if object_names is None:
            object_names = list(self.objects.keys())
        
        results = {}
        self.stats["total_reads"] += 1
        
        for object_name in object_names:
            if object_name not in self.objects:
                self.logger.log(
                    data=f"Object '{object_name}' not configured",
                    log_type=2,
                    visibility="TD",
                    tag="BACnetReader"
                )
                continue
            
            bacnet_object = self.objects[object_name]
            success, value = self.read_object(bacnet_object)
            
            if success:
                results[object_name] = {
                    "value": value,
                    "unit": bacnet_object.unit,
                    "description": bacnet_object.description,
                    "timestamp": time.time(),
                    "quality": "good"
                }
            else:
                results[object_name] = None
        
        return results
    
    def write_object(self, object_name: str, value: Any) -> bool:
        """
        Write a value to a BACnet object.
        
        Args:
            object_name: Name of the object to write to
            value: Value to write
            
        Returns:
            True if successful, False otherwise
        """
        if object_name not in self.objects:
            self.logger.log(
                data=f"Object '{object_name}' not configured",
                log_type=2,
                visibility="TD",
                tag="BACnetReader"
            )
            return False
        
        if not self.is_connected and not self.connect():
            return False
        
        try:
            bacnet_object = self.objects[object_name]
            
            # Create write request
            if isinstance(value, (int, float)):
                property_value = Real(value)
            elif isinstance(value, bool):
                property_value = Boolean(value)
            elif isinstance(value, str):
                property_value = CharacterString(value)
            else:
                property_value = Real(float(value))
            
            request = WritePropertyRequest(
                objectIdentifier=(bacnet_object.object_type.value, bacnet_object.instance_number),
                propertyIdentifier='presentValue',
                propertyValue=property_value
            )
            
            # Send request
            response = self.application.request(request)
            
            if response:
                self.logger.log(
                    data=f"Successfully wrote value {value} to {object_name}",
                    log_type=0,
                    visibility="TD",
                    tag="BACnetReader"
                )
                return True
            else:
                raise Exception("No response received")
                
        except Exception as e:
            self.logger.log(
                data=f"Failed to write to {object_name}: {str(e)}",
                log_type=2,
                visibility="TD",
                tag="BACnetReader"
            )
            return False
    
    def discover_devices(self) -> List[BACnetDevice]:
        """
        Discover BACnet devices on the network.
        
        Returns:
            List of discovered BACnet devices
        """
        if not self.is_connected and not self.connect():
            return []
        
        try:
            # Create Who-Is request
            request = WhoIsRequest()
            request.pduDestination = GlobalBroadcast()
            
            # Send request
            self.application.request(request)
            
            # Wait for responses
            time.sleep(2.0)
            
            # Process discovered devices (simplified)
            # In a real implementation, this would process I-Am responses
            discovered_devices = []
            
            # Example discovered devices (for demonstration)
            sample_devices = [
                BACnetDevice(1, "192.168.1.50", "HVAC Controller", 25),
                BACnetDevice(2, "192.168.1.51", "Lighting Controller", 15),
                BACnetDevice(3, "192.168.1.52", "Access Controller", 10)
            ]
            
            for device in sample_devices:
                self.discovered_devices[device.device_id] = device
                discovered_devices.append(device)
            
            self.stats["devices_discovered"] = len(discovered_devices)
            
            self.logger.log(
                data=f"Discovered {len(discovered_devices)} BACnet devices",
                log_type=0,
                visibility="TD",
                tag="BACnetReader"
            )
            
            return discovered_devices
            
        except Exception as e:
            self.logger.log(
                data=f"Device discovery failed: {str(e)}",
                log_type=2,
                visibility="TD",
                tag="BACnetReader"
            )
            return []
    
    def read_data(self) -> Dict[str, Any]:
        """
        Read data from the device.
        
        Returns:
            Dictionary containing device data
        """
        return self.read_objects()
    
    def save_data(self, data: Dict[str, Any]) -> bool:
        """
        Save data (placeholder method).
        
        Args:
            data: Data to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # This would typically save to the database
            # For now, just log the data
            self.logger.log(
                data=data,
                log_type=0,
                visibility="TD",
                tag="BACnetReader"
            )
            return True
        except Exception as e:
            self.logger.log(
                data=f"Failed to save data: {str(e)}",
                log_type=2,
                visibility="TD",
                tag="BACnetReader"
            )
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get device status information.
        
        Returns:
            Dictionary containing device status
        """
        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "device_address": self.device_address,
            "port": self.port,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "retry_delay": self.retry_delay,
            "is_connected": self.is_connected,
            "health_status": self.health_status,
            "last_read_time": self.last_read_time,
            "last_health_check": self.last_health_check,
            "object_count": len(self.objects),
            "discovered_devices_count": len(self.discovered_devices),
            "stats": self.stats.copy()
        }
    
    def check_health(self) -> bool:
        """
        Check the health of the BACnet connection.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self.is_connected:
                return False
            
            # Try to read a simple object to test connection
            if self.objects:
                # Read the first configured object
                first_object = list(self.objects.values())[0]
                success, _ = self.read_object(first_object)
                
                if success:
                    self.health_status = "healthy"
                    self.last_health_check = time.time()
                    return True
                else:
                    self.health_status = "unhealthy"
                    self.last_health_check = time.time()
                    return False
            else:
                # No objects configured, just check connection
                self.health_status = "healthy" if self.is_connected else "unhealthy"
                self.last_health_check = time.time()
                return self.is_connected
                
        except Exception as e:
            self.health_status = "error"
            self.last_health_check = time.time()
            self.logger.log(
                data=f"Health check failed: {str(e)}",
                log_type=2,
                visibility="TD",
                tag="BACnetReader"
            )
            return False
    
    def _start_health_monitor(self) -> None:
        """Start the health monitoring thread."""
        if not self.health_monitor_running:
            self.health_monitor_running = True
            self.health_monitor_thread = threading.Thread(
                target=self._health_monitor_loop,
                daemon=True
            )
            self.health_monitor_thread.start()
    
    def _health_monitor_loop(self) -> None:
        """Health monitoring loop."""
        while self.health_monitor_running:
            try:
                self.check_health()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.log(
                    data=f"Health monitor error: {str(e)}",
                    log_type=2,
                    visibility="TD",
                    tag="BACnetReader"
                )
                time.sleep(30)
    
    def close(self) -> None:
        """Close the BACnet reader and clean up resources."""
        self.health_monitor_running = False
        if self.health_monitor_thread:
            self.health_monitor_thread.join(timeout=5.0)
        
        self.disconnect()
        
        self.logger.log(
            data=f"Closed BACnet reader: {self.device_id}",
            log_type=0,
            visibility="TD",
            tag="BACnetReader"
        )
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Factory functions and backward compatibility
def create_bacnet_reader(
    device_id: str,
    device_address: str,
    port: int = 47808,
    **kwargs
) -> BACnetReader:
    """
    Factory function to create a BACnet reader.
    
    Args:
        device_id: Device identifier
        device_address: BACnet device IP address
        port: BACnet port
        **kwargs: Additional arguments
        
    Returns:
        Configured BACnetReader instance
    """
    return BACnetReader(device_id, device_address, port, **kwargs)


def read_bacnet_data(
    device_id: str,
    device_address: str,
    objects: List[BACnetObject],
    **kwargs
) -> Dict[str, Any]:
    """
    Read data from BACnet device (backward compatibility function).
    
    Args:
        device_id: Device identifier
        device_address: BACnet device IP address
        objects: List of BACnet objects to read
        **kwargs: Additional arguments
        
    Returns:
        Dictionary of object values
    """
    reader = BACnetReader(device_id, device_address, **kwargs)
    reader.add_objects(objects)
    
    with reader:
        return reader.read_objects() 