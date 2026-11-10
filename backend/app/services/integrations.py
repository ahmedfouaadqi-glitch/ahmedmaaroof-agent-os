from app.config import Settings

def integration_status(settings: Settings) -> list[dict]:
    return [
        {"id":"openrouter","name":"Model Gateway","configured":bool(settings.openrouter_api_key),"mode":"cloud","note":"Server-side model provider"},
        {"id":"email","name":"Email Inbox","configured":bool(settings.email_provider_url and settings.email_provider_token),"mode":"connector","note":"Requires a configured email connector"},
        {"id":"calendar","name":"Calendar","configured":bool(settings.calendar_provider_url and settings.calendar_provider_token),"mode":"connector","note":"Requires a configured calendar connector"},
        {"id":"voice_stt","name":"Whisper Speech-to-Text","configured":bool(settings.whisper_service_url),"mode":"local-service","note":"Requires a reachable local Whisper service"},
        {"id":"voice_tts","name":"Kokoro Text-to-Speech","configured":bool(settings.kokoro_service_url),"mode":"local-service","note":"Requires a reachable local Kokoro service"},
        {"id":"designer","name":"Designer Engine","configured":bool(settings.image_provider_api_key and settings.designer_provider_endpoint and settings.designer_provider_model and settings.designer_cost_per_image_usd > 0 and settings.designer_max_cost_usd > 0),"mode":"provider","note":"Requires provider credentials, model, explicit per-image price and budget cap"},
    ]
