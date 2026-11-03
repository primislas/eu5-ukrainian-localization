from abc import ABC


class Translator(ABC):

    def translate(self, text: str) -> str:
        raise NotImplementedError(
            f"Method translate is not implemented in {self.__class__.__name__}"
        )

    async def translate_batch_async(self, text: str) -> str:
        """Translate a single batch of lines.

        Args:
            text: Text to be translated.

        Returns:
            Translated text.
        """
        raise NotImplementedError(
            f"Method translate_batch_async is not implemented in {self.__class__.__name__}"
        )

    async def translate_async(self, text: str) -> str:
        """Convenience wrapper: translate a newline-joined text as a single batch."""
        return "\n".join(await self.translate_batch_async(text))
