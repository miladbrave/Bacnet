# BACnet Communication Library

A standalone Python library for BACnet (Building Automation and Control Networks) communication. This library provides clean, object-oriented interfaces for BACnet device communication including object reading, writing, and discovery without external framework dependencies.

## Overview

The BACnet library provides functionality to:
- Connect to BACnet devices and networks
- Read and write BACnet objects (analog, binary, multi-state)
- Discover BACnet devices on the network
- Monitor BACnet object values
- Handle BACnet alarms and events
- Support multiple BACnet object types

## Features

- **Standalone Implementation**: No external framework dependencies
- **Device Discovery**: Automatic BACnet device discovery
- **Object Management**: Read/write BACnet objects
- **Multiple Object Types**: Analog, Binary, Multi-state, String, etc.
- **Network Management**: IP and MS/TP network support
- **Health Monitoring**: Built-in health checks and connection monitoring
- **Statistics Tracking**: Detailed performance and usage statistics
- **Thread Safety**: Thread-safe operations for concurrent access
- **Context Manager Support**: Safe resource management with `with` statements

## Installation

### Prerequisites

```bash
# For BACnet communication
pip install bacpypes
```

### Usage

Simply copy the `bacnet_reader.py` file into your project and import it:

```python
from bacnet_reader import BACnetReader, BACnetObject, BACnetObjectType
```

## Quick Start

```python
from bacnet_reader import BACnetReader, BACnetObject, BACnetObjectType

# Create BACnet reader
reader = BACnetReader(
    device_id="controller_001",
    device_address="192.168.1.100",
    port=47808,
    timeout=5.0
)

# Add BACnet objects to read
temperature_object = BACnetObject(
    object_type=BACnetObjectType.ANALOG_INPUT,
    instance_number=1,
    name="temperature_sensor",
    description="Room temperature sensor",
    unit="°C"
)
reader.add_object(temperature_object)

# Read data
data = reader.read_objects()
print(data)
```

## BACnet Object Types

### Supported Object Types

- **ANALOG_INPUT**: Analog input objects (sensors)
- **ANALOG_OUTPUT**: Analog output objects (actuators)
- **ANALOG_VALUE**: Analog value objects (setpoints)
- **BINARY_INPUT**: Binary input objects (switches)
- **BINARY_OUTPUT**: Binary output objects (relays)
- **BINARY_VALUE**: Binary value objects (status)
- **MULTI_STATE_INPUT**: Multi-state input objects
- **MULTI_STATE_OUTPUT**: Multi-state output objects
- **MULTI_STATE_VALUE**: Multi-state value objects
- **STRING_VALUE**: String value objects
- **DEVICE**: Device objects

### Object Properties

Common BACnet object properties:
- **Present_Value**: Current value of the object
- **Description**: Human-readable description
- **Units**: Units of measurement
- **Status_Flags**: Object status information
- **Reliability**: Reliability of the object
- **Out_Of_Service**: Whether object is out of service

## Examples

### Basic BACnet Reading

```python
from bacnet_reader import BACnetReader, BACnetObject, BACnetObjectType

# Create reader
reader = BACnetReader(
    device_id="hvac_controller",
    device_address="192.168.1.50",
    port=47808,
    timeout=3.0
)

# Add HVAC objects
objects = [
    BACnetObject(BACnetObjectType.ANALOG_INPUT, 1, "room_temp", "Room Temperature", "°C"),
    BACnetObject(BACnetObjectType.ANALOG_INPUT, 2, "humidity", "Room Humidity", "%"),
    BACnetObject(BACnetObjectType.BINARY_INPUT, 1, "occupancy", "Room Occupancy", ""),
    BACnetObject(BACnetObjectType.ANALOG_OUTPUT, 1, "setpoint", "Temperature Setpoint", "°C")
]

for obj in objects:
    reader.add_object(obj)

# Read all objects
with reader:
    data = reader.read_objects()
    print("HVAC Data:", data)
```

### Device Discovery

```python
from bacnet_reader import BACnetReader

# Create reader for discovery
reader = BACnetReader(
    device_id="discovery_tool",
    device_address="192.168.1.100",
    port=47808
)

# Discover devices on network
with reader:
    devices = reader.discover_devices()
    
    for device in devices:
        print(f"Device: {device['device_id']}")
        print(f"Address: {device['address']}")
        print(f"Vendor: {device['vendor_name']}")
        print(f"Objects: {device['object_count']}")
        print("-" * 30)
```

### Building Automation Example

```python
from bacnet_reader import BACnetReader, BACnetObject, BACnetObjectType
import time

# Create reader for building automation
reader = BACnetReader(
    device_id="building_controller",
    device_address="192.168.1.10",
    port=47808,
    timeout=5.0
)

# Add building automation objects
building_objects = [
    # Lighting control
    BACnetObject(BACnetObjectType.BINARY_OUTPUT, 1, "lighting_zone1", "Lighting Zone 1", ""),
    BACnetObject(BACnetObjectType.BINARY_OUTPUT, 2, "lighting_zone2", "Lighting Zone 2", ""),
    BACnetObject(BACnetObjectType.BINARY_INPUT, 1, "motion_sensor1", "Motion Sensor 1", ""),
    BACnetObject(BACnetObjectType.BINARY_INPUT, 2, "motion_sensor2", "Motion Sensor 2", ""),
    
    # HVAC control
    BACnetObject(BACnetObjectType.ANALOG_INPUT, 1, "supply_temp", "Supply Air Temperature", "°C"),
    BACnetObject(BACnetObjectType.ANALOG_INPUT, 2, "return_temp", "Return Air Temperature", "°C"),
    BACnetObject(BACnetObjectType.ANALOG_INPUT, 3, "supply_humidity", "Supply Air Humidity", "%"),
    BACnetObject(BACnetObjectType.ANALOG_OUTPUT, 1, "fan_speed", "Fan Speed", "%"),
    BACnetObject(BACnetObjectType.ANALOG_OUTPUT, 2, "cooling_valve", "Cooling Valve", "%"),
    
    # Access control
    BACnetObject(BACnetObjectType.BINARY_INPUT, 3, "door_contact", "Door Contact", ""),
    BACnetObject(BACnetObjectType.BINARY_OUTPUT, 3, "door_lock", "Door Lock", ""),
    BACnetObject(BACnetObjectType.BINARY_INPUT, 4, "card_reader", "Card Reader", ""),
    
    # Energy monitoring
    BACnetObject(BACnetObjectType.ANALOG_INPUT, 4, "power_consumption", "Power Consumption", "kW"),
    BACnetObject(BACnetObjectType.ANALOG_INPUT, 5, "energy_usage", "Energy Usage", "kWh")
]

for obj in building_objects:
    reader.add_object(obj)

# Continuous monitoring
with reader:
    while True:
        try:
            data = reader.read_objects()
            
            # Process lighting control
            if data.get('motion_sensor1', {}).get('value'):
                print("Motion detected in Zone 1 - Turning on lights")
                # reader.write_object('lighting_zone1', True)
            
            # Process HVAC control
            supply_temp = data.get('supply_temp', {}).get('value', 0)
            return_temp = data.get('return_temp', {}).get('value', 0)
            
            if supply_temp > 25.0:
                print(f"High supply temperature: {supply_temp}°C")
                # reader.write_object('cooling_valve', 80.0)
            
            # Process access control
            if data.get('card_reader', {}).get('value'):
                print("Card access detected - Unlocking door")
                # reader.write_object('door_lock', False)
            
            # Energy monitoring
            power = data.get('power_consumption', {}).get('value', 0)
            print(f"Current power consumption: {power} kW")
            
            time.sleep(10)  # Read every 10 seconds
            
        except KeyboardInterrupt:
            print("Monitoring stopped by user")
            break
```

### Alarm and Event Handling

```python
from bacnet_reader import BACnetReader, BACnetObject, BACnetObjectType

# Create reader for alarm monitoring
reader = BACnetReader(
    device_id="alarm_monitor",
    device_address="192.168.1.20",
    port=47808
)

# Add alarm objects
alarm_objects = [
    BACnetObject(BACnetObjectType.BINARY_INPUT, 1, "fire_alarm", "Fire Alarm", ""),
    BACnetObject(BACnetObjectType.BINARY_INPUT, 2, "security_alarm", "Security Alarm", ""),
    BACnetObject(BACnetObjectType.BINARY_INPUT, 3, "maintenance_alarm", "Maintenance Alarm", ""),
    BACnetObject(BACnetObjectType.ANALOG_INPUT, 1, "temperature_alarm", "Temperature Alarm", "°C")
]

for obj in alarm_objects:
    reader.add_object(obj)

# Monitor alarms
with reader:
    while True:
        data = reader.read_objects()
        
        # Check fire alarm
        if data.get('fire_alarm', {}).get('value'):
            print("🚨 FIRE ALARM ACTIVATED!")
            # Trigger emergency procedures
        
        # Check security alarm
        if data.get('security_alarm', {}).get('value'):
            print("🚨 SECURITY ALARM ACTIVATED!")
            # Trigger security procedures
        
        # Check maintenance alarm
        if data.get('maintenance_alarm', {}).get('value'):
            print("⚠️ MAINTENANCE ALARM ACTIVATED!")
            # Schedule maintenance
        
        # Check temperature alarm
        temp = data.get('temperature_alarm', {}).get('value', 0)
        if temp > 30.0:
            print(f"🌡️ HIGH TEMPERATURE ALARM: {temp}°C")
            # Trigger cooling procedures
        
        time.sleep(5)  # Check every 5 seconds
```

## Configuration

### Network Settings

```python
reader = BACnetReader(
    device_id="my_controller",
    device_address="192.168.1.100",  # BACnet device IP address
    port=47808,                       # BACnet port (default: 47808)
    timeout=5.0,                      # Read timeout
    retry_count=3,                    # Retry attempts
    retry_delay=1.0                   # Delay between retries
)
```

### Logging

```python
from bacnet_reader import SimpleLogger

# Create custom logger
logger = SimpleLogger(log_level=1)  # 0=info, 1=warning, 2=error

# Use with BACnet reader
reader = BACnetReader(device_id="test", logger=logger)
```

## Error Handling

The library includes comprehensive error handling:

- **Connection Errors**: Automatic retry with exponential backoff
- **Object Errors**: Invalid object type or instance handling
- **Network Errors**: BACnet network communication issues
- **Logging**: Detailed error logging with different levels

## Performance Considerations

- **Object Discovery**: Cache discovered objects for better performance
- **Read Frequency**: Adjust read intervals based on object update rates
- **Network Load**: Monitor BACnet network traffic
- **Object Count**: Limit number of objects per device for optimal performance

## Troubleshooting

### Common Issues

1. **Connection Failures**
   - Check BACnet device IP address and port
   - Verify network connectivity
   - Ensure BACnet device is online

2. **Object Read Errors**
   - Verify object type and instance number
   - Check object properties
   - Ensure object is readable

3. **Network Issues**
   - Check BACnet network configuration
   - Verify device addressing
   - Monitor network traffic

### Debug Mode

Enable debug logging by setting log level to 0:

```python
logger = SimpleLogger(log_level=0)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the examples
3. Create an issue with detailed information

## Version History

- **v1.0.0**: Initial release with BACnet support
- Standalone implementation without external framework dependencies
- Comprehensive object reading and writing
- Device discovery and monitoring
- Alarm and event handling
- Building automation examples

## References

- BACnet Standard: ANSI/ASHRAE 135-2020
- BACnet/IP Protocol
- Building Automation and Control Networks
- HVAC Control Systems 