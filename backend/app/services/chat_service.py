"""
Chat Service — LocalVoice streaming AI guide chat.
RAG-augmented with relevant gems context for factual grounding.
"""
from __future__ import annotations

from typing import AsyncIterator

from app.core.security import sanitize_input
from app.infrastructure.llm_client import get_llm_client
from app.infrastructure.vector_store import get_vector_store
from app.models.schemas import ChatRequest
from app.prompts.system_prompts import LOCAL_GUIDE_SYSTEM


class ChatService:
    async def stream_response(self, req: ChatRequest) -> AsyncIterator[str]:
        clean_dest = sanitize_input(req.destination)

        # RAG: Retrieve relevant gems context to ground the guide's answers
        vs = get_vector_store()
        last_user_msg = req.messages[-1].content
        rag_hits = vs.search(f"{clean_dest} {last_user_msg}", n_results=3)
        rag_context = "\n".join(
            f"- {h['metadata']['name']}: {h['document'][:200]}" for h in rag_hits
        ) if rag_hits else "No specific gem data available."

        # Build system prompt with destination and RAG context
        system_content = (
            LOCAL_GUIDE_SYSTEM.replace("{{destination}}", clean_dest)
            + f"\n\nRelevant local knowledge:\n{rag_context}"
        )

        # Build conversation history (sanitize all messages)
        messages = [{"role": "system", "content": system_content}]
        for msg in req.messages:
            clean_content = sanitize_input(msg.content)
            messages.append({"role": msg.role, "content": clean_content})

        llm = get_llm_client()
        async for chunk in llm.stream(
            messages=messages,
            temperature=0.8,
            max_tokens=400,
        ):
            yield chunk
