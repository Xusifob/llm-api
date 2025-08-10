import json, time, uuid
from typing import Any, Dict, List, AsyncGenerator
import httpx
from fastapi import APIRouter, Body, Header, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from ..settings import OLLAMA_HOST, DEFAULT_MODEL, ALLOWED_MODELS
from ..db import get_db
from ..models import Conversation, Message
from fastapi import HTTPException, Request

router = APIRouter(tags=["openai"])

def now_ts() -> int:
    return int(time.time())

def make_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"

def to_openai_usage(ollama_resp: Dict[str, Any]) -> Dict[str, int]:
    prompt = int(ollama_resp.get("prompt_eval_count") or 0)
    completion = int(ollama_resp.get("eval_count") or 0)
    return {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": prompt + completion}

def map_options(body: Dict[str, Any]) -> Dict[str, Any]:
    opts: Dict[str, Any] = {}
    if (t := body.get("temperature")) is not None: opts["temperature"] = t
    if (p := body.get("top_p")) is not None: opts["top_p"] = p
    if (k := body.get("top_k")) is not None: opts["top_k"] = k
    if (m := body.get("max_tokens")) is not None: opts["num_predict"] = m
    if (s := body.get("stop")) is not None: opts["stop"] = s if isinstance(s, list) else [s]
    if (rp := body.get("presence_penalty")) is not None: opts["presence_penalty"] = rp
    if (fp := body.get("frequency_penalty")) is not None: opts["frequency_penalty"] = fp
    return opts

@router.get("/v1/models")
async def list_models():
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{OLLAMA_HOST}/api/tags")
        r.raise_for_status()
        data = r.json()
    installed = {m["name"] for m in data.get("models", [])}
    visible = installed & ALLOWED_MODELS
    models = [{"id": name, "object": "model", "owned_by": "ollama", "created": now_ts()} for name in sorted(visible)]
    return {"object": "list", "data": models}

@router.post("/v1/completions")
async def completions(body: Dict[str, Any] = Body(...)):
    model = body.get("model", DEFAULT_MODEL)
    prompt = body.get("prompt", "")
    stream = bool(body.get("stream", False))
    options = map_options(body)

    if stream:
        async def event_stream() -> AsyncGenerator[bytes, None]:
            created = now_ts()
            cid = make_id("cmpl")
            async with httpx.AsyncClient(timeout=None) as client:
                req = {"model": model, "prompt": prompt, "stream": True, "options": options}
                async with client.stream("POST", f"{OLLAMA_HOST}/api/generate", json=req) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line: continue
                        chunk = json.loads(line)
                        if chunk.get("done"):
                            usage = to_openai_usage(chunk)
                            final = {"id": cid, "object": "text_completion", "created": created, "model": model,
                                     "choices": [{"index": 0, "text": "", "finish_reason": chunk.get("done_reason") or "stop", "logprobs": None}],
                                     "usage": usage}
                            yield f"data: {json.dumps(final)}\n\n".encode()
                            yield b"data: [DONE]\n\n"; return
                        delta = chunk.get("response", "")
                        sse = {"id": cid, "object": "text_completion", "created": created, "model": model,
                               "choices": [{"index": 0, "text": delta, "finish_reason": None, "logprobs": None}]}
                        yield f"data: {json.dumps(sse)}\n\n".encode()
        return StreamingResponse(event_stream(), media_type="text/event-stream")

    async with httpx.AsyncClient(timeout=None) as client:
        req = {"model": model, "prompt": prompt, "stream": False, "options": options}
        r = await client.post(f"{OLLAMA_HOST}/api/generate", json=req); r.raise_for_status(); data = r.json()
    usage = to_openai_usage(data); text = data.get("response", "")
    return {"id": make_id("cmpl"), "object": "text_completion", "created": now_ts(), "model": model,
            "choices": [{"index": 0, "text": text, "finish_reason": data.get("done_reason") or "stop", "logprobs": None}],
            "usage": usage}

@router.post("/v1/chat/completions")
async def chat_completions(
    body: Dict[str, Any] = Body(...),
    x_conversation_id: str | None = Header(default=None, convert_underscores=False),
    db: Session = Depends(get_db),
):
    model = body.get("model", DEFAULT_MODEL)
    user_messages: List[Dict[str, Any]] = body.get("messages", [])
    stream = bool(body.get("stream", False))
    options = map_options(body)

    # Optional server-side history if X-Conversation-Id is provided
    history: List[Dict[str, str]] = []
    user_id = getattr(request.state, "user_id", None)
    if x_conversation_id:
        q = db.query(Conversation).filter(Conversation.id == x_conversation_id)
        if user_id: q = q.filter(Conversation.user_id == user_id)
        convo = q.first()
        if not convo:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if convo:
            for m in convo.messages:
                history.append({"role": m.role, "content": m.content})

    merged_messages = history + user_messages
    req = {"model": model, "messages": merged_messages, "stream": stream, "options": options}

    if stream:
        async def event_stream() -> AsyncGenerator[bytes, None]:
            created = now_ts()
            cid = make_id("chatcmpl")
            buffer = []
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", f"{OLLAMA_HOST}/api/chat", json=req) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line: continue
                        chunk = json.loads(line)
                        if chunk.get("done"):
                            usage = to_openai_usage(chunk)
                            # persist last user msg + assistant reply if convo exists
                            if convo and user_messages:
                                for msg in user_messages:
                                    db.add(Message(conversation_id=convo.id, role=msg.get("role","user"), content=msg.get("content","")))
                                db.add(Message(conversation_id=convo.id, role="assistant", content="".join(buffer)))
                                db.commit()
                            final = {"id": cid, "object": "chat.completion.chunk", "created": created, "model": model,
                                     "choices": [{"index": 0, "delta": {}, "finish_reason": chunk.get("done_reason") or "stop"}],
                                     "usage": usage}
                            yield f"data: {json.dumps(final)}\n\n".encode()
                            yield b"data: [DONE]\n\n"; return

                        msg = chunk.get("message")
                        content_delta = (msg.get("content", "") if isinstance(msg, dict) else chunk.get("response", "")) or ""
                        buffer.append(content_delta)
                        sse = {"id": cid, "object": "chat.completion.chunk", "created": created, "model": model,
                               "choices": [{"index": 0, "delta": {"role": "assistant", "content": content_delta}, "finish_reason": None}]}
                        yield f"data: {json.dumps(sse)}\n\n".encode()
        return StreamingResponse(event_stream(), media_type="text/event-stream")

    async with httpx.AsyncClient(timeout=None) as client:
        r = await client.post(f"{OLLAMA_HOST}/api/chat", json=req); r.raise_for_status(); data = r.json()

    usage = to_openai_usage(data)
    content = data.get("message", {}).get("content") if isinstance(data.get("message"), dict) else data.get("response", "")
    content = content or ""

    # persist if convo exists
    if convo and user_messages:
        for msg in user_messages:
            db.add(Message(conversation_id=convo.id, role=msg.get("role","user"), content=msg.get("content","")))
        db.add(Message(conversation_id=convo.id, role="assistant", content=content))
        db.commit()

    return {"id": make_id("chatcmpl"), "object": "chat.completion", "created": now_ts(), "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": data.get("done_reason") or "stop"}],
            "usage": usage}

@router.get("/")
def root():
    return JSONResponse({"ok": True, "service": "openai-compatible", "backend": "ollama", "model": DEFAULT_MODEL})

@router.get("/health")
def health():
    return {"ok": True}