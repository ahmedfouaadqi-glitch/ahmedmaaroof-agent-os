import httpx
from fastapi import HTTPException
from app.config import Settings

class OpenRouterProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def complete(self, messages: list[dict[str, str]]) -> dict:
        if not self.settings.openrouter_api_key:
            raise HTTPException(status_code=503, detail="OPENROUTER_API_KEY is not configured on the backend")
        payload = {"models":[self.settings.openrouter_model, *self.settings.fallback_models],"messages":messages,"temperature":0.2}
        headers = {"Authorization":f"Bearer {self.settings.openrouter_api_key}","Content-Type":"application/json","HTTP-Referer":self.settings.openrouter_site_url,"X-Title":self.settings.openrouter_app_name}
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(75.0, connect=10.0)) as client:
                response = await client.post("https://openrouter.ai/api/v1/chat/completions",json=payload,headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504,detail="The model provider timed out") from exc
        except httpx.HTTPStatusError as exc:
            detail = "The model provider rejected the request"
            try: detail = exc.response.json().get("error",{}).get("message",detail)
            except ValueError: pass
            raise HTTPException(status_code=502,detail=detail[:500]) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502,detail="Unable to reach the model provider") from exc
        choices = data.get("choices") or []
        if not choices: raise HTTPException(status_code=502,detail="The model provider returned no completion")
        answer = choices[0].get("message",{}).get("content")
        if not isinstance(answer,str) or not answer.strip(): raise HTTPException(status_code=502,detail="The model provider returned an empty answer")
        usage = data.get("usage") or {}
        normalized = {k:int(usage[k]) for k in ("prompt_tokens","completion_tokens","total_tokens") if isinstance(usage.get(k),(int,float))}
        return {"answer":answer,"model":data.get("model",self.settings.openrouter_model),"usage":normalized or None}
