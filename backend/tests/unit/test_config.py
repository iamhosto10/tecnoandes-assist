from app.core.config import Settings


def test_settings_load_with_defaults():
    # No requiere ANTHROPIC_API_KEY ni un .env presente: todos los campos
    # tienen default, así los tests corren sin secretos ni internet.
    settings = Settings(_env_file=None)

    assert settings.anthropic_model == "claude-haiku-4-5-20251001"
    assert settings.embedding_dimensions == 384
    assert settings.confidence_threshold_low < settings.confidence_threshold_high
