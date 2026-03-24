from abc import ABC


class Translator(ABC):

    def translate(self, text: str) -> str:
        raise NotImplementedError(
            f"Method translate is not implemented in {self.__class__.__name__}"
        )

    async def translate_batch_async(self, lines: list[str]) -> list[str]:
        """Translate a single batch of lines.

        Args:
            lines: List of text lines to translate (one batch, no splitting).

        Returns:
            List of translated lines, same length as input.
        """
        raise NotImplementedError(
            f"Method translate_batch_async is not implemented in {self.__class__.__name__}"
        )

    async def translate_async(self, text: str) -> str:
        """Convenience wrapper: translate a newline-joined text as a single batch."""
        lines = text.splitlines()
        if not lines:
            return ""
        return "\n".join(await self.translate_batch_async(lines))
