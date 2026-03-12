"""Specialist agent factory.

Creates and caches specialist agents for multi-agent delegation.
"""

import logging

from strands import Agent
from strands_tools import (
    file_read, file_write, editor, shell, think, current_time,
    python_repl, http_request, calculator,
)


logger = logging.getLogger("aethon.specialists")


SPECIALIST_CONFIGS = {
    "coder": {
        "name": "Kodcu",
        "system_prompt": (
            "Sen bir yazilim gelistirme uzmanisin.\n"
            "Gorevlerin: kod yazma, test etme, debug etme, refactoring.\n"
            "TDD prensiplerini takip et: once test yaz, sonra implement et.\n"
            "Kisa, temiz, yorumsuz kod yaz.\n"
            "Isini bitirdiginde sonucu acikca bildir."
        ),
        "tools": [file_read, file_write, editor, shell, python_repl, think],
    },
    "researcher": {
        "name": "Arastirmaci",
        "system_prompt": (
            "Sen bir arastirma uzmanisin.\n"
            "Gorevlerin: web arastirmasi, dokumantasyon okuma, bilgi toplama.\n"
            "Kaynaklari belirt. Ozet ve analizle sun.\n"
            "Net, dogrulanabilir bilgiler ver."
        ),
        "tools": [http_request, file_read, think, current_time],
    },
    "analyst": {
        "name": "Analist",
        "system_prompt": (
            "Sen bir veri analisti ve raporlamacisin.\n"
            "Gorevlerin: veri analizi, hesaplama, grafik olusturma, rapor yazma.\n"
            "Net, olculebilir sonuclar sun.\n"
            "Sayisal verileri tablo formatinda goster."
        ),
        "tools": [python_repl, calculator, file_read, file_write, think],
    },
    "planner": {
        "name": "Planlayici",
        "system_prompt": (
            "Sen bir proje planlayicisisin.\n"
            "Gorevlerin: karmasik gorevleri adim adim bolme, onceliklendirme.\n"
            "Her adimi net, somut ve uygulanabilir yap.\n"
            "Bagimliliklar ve riskleri belirt."
        ),
        "tools": [file_read, file_write, think],
    },
}


class SpecialistFactory:
    """Create and cache specialist agents."""

    def __init__(self, model):
        self.model = model
        self._cache: dict[str, Agent] = {}

    def get(self, specialist_name: str) -> Agent:
        """Get or create a specialist agent."""
        if specialist_name not in self._cache:
            config = SPECIALIST_CONFIGS.get(specialist_name)
            if not config:
                raise ValueError(f"Bilinmeyen uzman: {specialist_name}")

            self._cache[specialist_name] = Agent(
                model=self.model,
                system_prompt=config["system_prompt"],
                tools=config["tools"],
                name=config["name"],
                agent_id=specialist_name,
            )
            logger.info(f"Uzman agent olusturuldu: {config['name']}")

        return self._cache[specialist_name]

    def get_all(self) -> dict[str, Agent]:
        """Get all specialist agents."""
        return {name: self.get(name) for name in SPECIALIST_CONFIGS}
