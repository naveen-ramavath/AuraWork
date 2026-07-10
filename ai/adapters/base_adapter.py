from abc import ABC, abstractmethod


class BaseAdapter(ABC):

    @abstractmethod
    def create_chat(
        self,
        user_message,
        tools,
        system_instruction,
    ):
        pass