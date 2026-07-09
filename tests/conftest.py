"""Shared test fixtures. Builds a valid DecodeResult without calling the API."""

import pytest

from app.schema import ActionStep, DecodeResult, Deadline, Urgency


@pytest.fixture
def sample_result() -> DecodeResult:
    return DecodeResult(
        document_type="USCIS notice",
        summary_en="This letter confirms USCIS received your work permit application. It is not a decision.",
        summary_ru="Это письмо подтверждает, что USCIS получил вашу заявку на разрешение на работу. Это не решение.",
        deadline=Deadline(
            has_deadline=False,
            date=None,
            description_en="No deadline is stated. Check your case status online using the receipt number.",
            description_ru="Срок не указан. Проверьте статус дела онлайн по номеру квитанции.",
        ),
        action_steps=[
            ActionStep(
                step_en="Keep this notice and check your case status online with the receipt number.",
                step_ru="Сохраните это уведомление и проверьте статус дела онлайн по номеру квитанции.",
                urgency=Urgency.low,
            )
        ],
        urgency_level=Urgency.low,
        confidence=Urgency.high,
        notes="",
    )
