from typing import Dict, Union


class VaultResponseException(Exception):
    def __init__(self, status: int, data: Union[Dict, str]):
        self.status = status
        self.data = data
        try:
            self.message = data.get("message", None)  # type: ignore
        except AttributeError:
            self.message = data

    def __str__(self):
        return f"VaultResponseException => HTTP STATUS: {self.status}, MESSAGE: '{self.message}'\n\nRAW RESPONSE: {self.data}"
