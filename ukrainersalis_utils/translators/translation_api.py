from abc import ABC


class Translator(ABC):

    def translate(self, text: str) -> str:
        raise NotImplementedError(
            f"Method translate is not implemented in {self.__class__.__name__}"
        )
