from typing import Callable, Dict, Type

# Центральний реєстр протоколів
_protocol_registry: Dict[str, Type] = {}


def register_protocol(name: str) -> Callable:
    """
    Декоратор для реєстрації класу протоколу за ім'ям.
    :param name: Ім'я протоколу (наприклад, Receiver.CMS_SIA_DCS.value)
    :return: клас, зареєстрований у протокольному реєстрі
    """
    def decorator(cls: Type) -> Type:
        if name in _protocol_registry:
            raise ValueError(f"Protocol '{name}' is already registered.")
        _protocol_registry[name] = cls
        return cls
    return decorator


def get_protocol_handler(name: str) -> Type:
    """
    Отримати клас протоколу за ім'ям.
    :param name: Ім'я протоколу
    :return: Клас протоколу, який реалізує метод run()
    """
    if name not in _protocol_registry:
        raise ValueError(f"Protocol '{name}' is not registered.")
    return _protocol_registry[name]


# Для зворотної сумісності
protocol_registry = _protocol_registry
