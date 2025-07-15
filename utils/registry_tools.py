from typing import Callable, Dict, Type

# Central registry for protocol handlers
_protocol_registry: Dict[str, Type] = {}


def register_protocol(name: str) -> Callable[[Type], Type]:
    """
    Decorator to register a protocol handler class under a given name.

    :param name: Protocol name (e.g., Receiver.SIA_DCS.value)
    :return: The class registered in the protocol registry
    :raises ValueError: If the protocol name is already registered
    """
    def decorator(cls: Type) -> Type:
        if name in _protocol_registry:
            raise ValueError(f"Protocol '{name}' is already registered.")
        _protocol_registry[name] = cls
        return cls
    return decorator


def get_protocol_handler(name: str) -> Type:
    """
    Retrieve a registered protocol handler class by its name.

    :param name: The protocol name
    :return: The handler class implementing the run() method
    :raises ValueError: If the protocol is not registered
    """
    if name not in _protocol_registry:
        raise ValueError(f"Protocol '{name}' is not registered.")
    return _protocol_registry[name]


# Convenience aliases matching handler usage
register = register_protocol
get = get_protocol_handler

# For backward compatibility
protocol_registry = _protocol_registry
