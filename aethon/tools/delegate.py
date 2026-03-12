"""Delegate tools for multi-agent orchestration.

Each tool delegates a task to a specialist agent via SpecialistFactory.
"""

from strands import tool


_specialist_factory = None


def set_specialist_factory(factory):
    """Set the global specialist factory reference."""
    global _specialist_factory
    _specialist_factory = factory


def _extract_text(result) -> str:
    """Extract text from agent result."""
    return str(result).strip() or "Sonuc alinamadi."


@tool
def ask_coder(task: str) -> str:
    """Kodlama gorevini kodcu uzmanina devret.
    Kodcu; kod yazma, test etme, debug, refactoring yapar.

    Args:
        task: Kodlama gorevi aciklamasi
    """
    if not _specialist_factory:
        return "Hata: Specialist factory baslatilmamis."
    coder = _specialist_factory.get("coder")
    result = coder(task)
    return _extract_text(result)


@tool
def ask_researcher(query: str) -> str:
    """Arastirma gorevini arastirmaci uzmanina devret.
    Arastirmaci; web arastirmasi, dokumantasyon okuma, bilgi toplama yapar.

    Args:
        query: Arastirilacak konu veya soru
    """
    if not _specialist_factory:
        return "Hata: Specialist factory baslatilmamis."
    researcher = _specialist_factory.get("researcher")
    result = researcher(query)
    return _extract_text(result)


@tool
def ask_analyst(data_task: str) -> str:
    """Veri analizi gorevini analist uzmanina devret.
    Analist; veri analizi, hesaplama, grafik olusturma, rapor yazma yapar.

    Args:
        data_task: Analiz gorevi aciklamasi
    """
    if not _specialist_factory:
        return "Hata: Specialist factory baslatilmamis."
    analyst = _specialist_factory.get("analyst")
    result = analyst(data_task)
    return _extract_text(result)


@tool
def ask_planner(planning_task: str) -> str:
    """Planlama gorevini planlayici uzmanina devret.
    Planlayici; karmasik gorevleri adim adim boler, onceliklendirir.

    Args:
        planning_task: Planlanacak gorev aciklamasi
    """
    if not _specialist_factory:
        return "Hata: Specialist factory baslatilmamis."
    planner = _specialist_factory.get("planner")
    result = planner(planning_task)
    return _extract_text(result)
