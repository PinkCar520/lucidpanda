import httpx
import json
import asyncio
import websockets
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from src.lucidpanda.config.config import settings

router = APIRouter()

class VoiceSessionResponse(BaseModel):
    client_secret: dict

@router.post("/sessions", response_model=VoiceSessionResponse)
async def create_voice_session():
    """
    Generate an ephemeral token for OpenAI Realtime API.
    """
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    url = "https://api.openai.com/v1/realtime/sessions"
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-realtime-preview-2024-12-17",
        "voice": "verse"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return VoiceSessionResponse(client_secret=data.get("client_secret", {}))
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"OpenAI API Error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create voice session: {str(e)}")

@router.websocket("/gemini/stream")
async def gemini_voice_stream(websocket: WebSocket):
    """
    WebSocket proxy for Gemini Multimodal Live API.
    Accepts frontend WS, dials Gemini WS, and relays binary & text frames.
    """
    if not settings.GEMINI_API_KEY:
        await websocket.accept()
        await websocket.close(code=1011, reason="GEMINI_API_KEY is not configured")
        return

    await websocket.accept()

    api_key = settings.GEMINI_API_KEY
    url = f"wss://generativelanguage.googleapis.com/ws/google.aistudio.live.v1.GenerativeService.BidiGenerateContent?key={api_key}"

    try:
        async with websockets.connect(url) as gemini_ws:

            # Send Initial Setup Frame to Gemini
            setup_msg = {
                "setup": {
                    "model": "models/gemini-2.0-flash",
                    "generationConfig": {
                        "responseModalities": ["AUDIO"]
                    }
                }
            }
            await gemini_ws.send(json.dumps(setup_msg))

            async def client_to_gemini():
                try:
                    while True:
                        data = await websocket.receive_text()
                        await gemini_ws.send(data)
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    print(f"Proxy Client->Gemini error: {e}")

            async def gemini_to_client():
                try:
                    while True:
                        msg = await gemini_ws.recv()
                        await websocket.send_text(msg)
                except websockets.ConnectionClosed:
                    pass
                except Exception as e:
                    print(f"Proxy Gemini->Client error: {e}")

            await asyncio.gather(
                client_to_gemini(),
                gemini_to_client()
            )
            
    except Exception as e:
        print(f"Gemini WS Handshake failed: {e}")
        if websocket.client_state.CONNECTED:
            await websocket.close(code=1011, reason=str(e))

