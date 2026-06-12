"""Tests for the intake classifier (Phase 10 C1)."""

from aethon.agent.intake import classify_intake
from aethon.config import CoreLoopConfig


WORK = CoreLoopConfig().intake_work_phrases
CHAT = CoreLoopConfig().intake_chat_phrases


def _c(text):
    return classify_intake(text, work_phrases=WORK, chat_phrases=CHAT)


def test_question_is_chat():
    assert _c("merhaba, bugün nasılsın?") == "chat"
    assert _c("bu fonksiyon nasıl çalışıyor?") == "chat"


def test_short_message_is_chat():
    assert _c("selam") == "chat"
    assert _c("dosyayı sil") == "chat"  # a command, but not a project


def test_clear_project_is_work():
    assert _c(
        "Kullanıcı girişi ve yorumları olan bir blog API'si geliştir, "
        "PostgreSQL kullan ve testleri de yaz."
    ) == "work"
    assert _c(
        "Build a CLI tool that ingests CSV files and produces a summary report "
        "with charts, and add tests for it."
    ) == "work"


def test_explicit_work_override_wins():
    # Short + no verb would be chat, but the override forces work.
    assert _c("bunu bir iş olarak ele al: rapor") == "work"
    assert _c("treat as work please") == "work"


def test_explicit_chat_override_wins_even_with_work_words():
    # A work verb + length would be work, but the chat override forces chat.
    assert _c(
        "sadece soru: bir blog API'si nasıl geliştirilir, merak ediyorum?"
    ) == "chat"


def test_high_bar_substantial_but_no_verb_is_chat():
    # Long, no question mark, but no project/creation signal → stays chat.
    assert _c(
        "Bugün hava çok güzeldi ve uzun bir yürüyüş yaptım, sonra kahve içtim."
    ) == "chat"


def test_empty_is_chat():
    assert _c("") == "chat"
    assert _c("   ") == "chat"


def test_work_signal_respects_word_boundary():
    # Turkish inflections must not trip a bare work stem: "yaptım" (past tense)
    # must not match "yap"; both stay chat.
    assert _c("bugün çok güzel bir resim yaptım ve sonra arkadaşlarla buluştum") == "chat"
    assert _c("çok yazık oldu bugün, üzücü bir durum yaşandı maalesef arkadaşlar") == "chat"


def test_generic_verb_without_project_noun_is_chat():
    """Review fix: a creation verb alone must not hijack chat — without a project
    noun, common verbs like build/create stay chat."""
    assert _c(
        "I want to build a stronger relationship with my team over the next year."
    ) == "chat"
    assert _c(
        "Bence kendine yeni bir hedef koy ve onu adım adım gerçekleştirmeye çalış."
    ) == "chat"
    assert _c(
        "Let's create a warm and welcoming atmosphere for the guests tonight here."
    ) == "chat"


def test_verb_plus_project_noun_is_work():
    """A creation verb paired with a project/artifact noun clears the bar."""
    assert _c("Refactor the authentication module and add tests for it please.") == "work"
    assert _c("Veritabanı şemasını yeniden tasarla ve migration script'i hazırla.") == "work"


def test_project_noun_word_boundary():
    # "kapı" (door) contains "api" but must not match the "api" project noun.
    assert _c(
        "Bugün eve geldiğimde kapı açıktı ve içerisi çok soğuktu maalesef dostum."
    ) == "chat"
