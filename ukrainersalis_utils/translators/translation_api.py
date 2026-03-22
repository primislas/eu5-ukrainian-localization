from abc import ABC


class Translator(ABC):

    def translate(self, text: str) -> str:
        raise NotImplementedError(
            f"Method translate is not implemented in {self.__class__.__name__}"
        )

    async def translate_async(self, text: str) -> str:
        raise NotImplementedError(
            f"Method translate_async is not implemented in {self.__class__.__name__}"
        )
