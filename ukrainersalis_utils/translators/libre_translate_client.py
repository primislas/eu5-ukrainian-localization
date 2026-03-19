from typing import Any

import requests

from ukrainersalis_utils.translators.translation_api import Translator


class LibreTranslateClient(Translator):

    def __init__(self, url = "http://localhost:5000", source_language: str = "en", target_language: str = "uk"):
        self._url = url
        self._source_language = source_language
        self._target_language = target_language

    def get_translate_endpoint(self) -> str:
        return self._url + "/translate"

    def make_request_body(self, text: str, source_language: str | None = None, target_language: str | None = None) -> dict[str, Any]:
        return {
            "q": text,
            "source": source_language or self._source_language,
            "target": target_language or self._target_language,
            "format": "text",
            "alternatives": 0,
            "api_key": ""
        }

    def translate(self, text: str) -> str:
        res = requests.post(
            self.get_translate_endpoint(),
            headers={"Content-Type": "application/json"},
            json=self.make_request_body(text),
        )
        return res.json()["translatedText"]
