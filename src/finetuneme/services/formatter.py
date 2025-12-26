"""
Service for formatting datasets into different formats.
Supports ShareGPT and Alpaca formats for LLM fine-tuning.
"""
import json
from typing import List, Dict
from datetime import datetime
import uuid

def format_conversations_to_jsonl(conversations: List[Dict], format_type: str = "sharegpt") -> str:
    """
    Format conversations to JSONL string.

    Args:
        conversations: List of conversation dictionaries
        format_type: "sharegpt", "alpaca", or "jsonl" (flat)

    Returns:
        JSONL formatted string
    """
    if format_type.lower() == "alpaca":
        jsonl_lines = format_alpaca(conversations)
    elif format_type.lower() == "jsonl" or format_type.lower() == "flat": # Handle user's "JSONL" selection
        jsonl_lines = format_simple(conversations)
    else:
        jsonl_lines = format_sharegpt(conversations)

    return "\n".join(jsonl_lines) + "\n"

def format_sharegpt(conversations: List[Dict]) -> List[str]:
    """Format conversations into ShareGPT JSONL format"""
    jsonl_lines = []

    for conv in conversations:
        # Check if already in ShareGPT format (has 'conversations' key)
        if "conversations" in conv:
            formatted = {
                "conversations": conv["conversations"],
                "id": conv.get("id", str(uuid.uuid4())),
                "source": conv.get("source", ""),
                "metadata": {
                    "page": conv.get("page"),
                    "generated_at": datetime.utcnow().isoformat()
                }
            }
        else:
             # Legacy/Flat dict fallback -> Convert to ShareGPT
             formatted = {
                "conversations": [
                    {"from": "human", "value": conv.get("question", "")},
                    {"from": "gpt", "value": conv.get("answer", "")}
                ],
                "id": str(uuid.uuid4()),
                "source": conv.get("source", ""),
                "metadata": {
                    "page": conv.get("page"),
                    "generated_at": datetime.utcnow().isoformat()
                }
             }

        jsonl_lines.append(json.dumps(formatted, ensure_ascii=False))

    return jsonl_lines

def format_alpaca(conversations: List[Dict]) -> List[str]:
    """Format conversations into Alpaca JSONL format"""
    jsonl_lines = []

    for conv in conversations:
        # Standardize input
        if "conversations" in conv:
            conversations_list = conv.get("conversations", [])
            if len(conversations_list) >= 2:
                question = conversations_list[0].get("value", "")
                answer = conversations_list[1].get("value", "")
            else:
                continue
        else:
            question = conv.get("question", "")
            answer = conv.get("answer", "")

        formatted = {
            "instruction": question,
            "input": "",
            "output": answer,
            "source": conv.get("source", ""),
            "metadata": {
                "page": conv.get("page"),
                "generated_at": datetime.utcnow().isoformat()
            }
        }

        jsonl_lines.append(json.dumps(formatted, ensure_ascii=False))

    return jsonl_lines

def format_simple(conversations: List[Dict]) -> List[str]:
    """Format conversations into Flat JSONL format (Reference Style)"""
    jsonl_lines = []

    for conv in conversations:
        # Extract Q/A from ShareGPT structure if needed
        if "conversations" in conv:
            conversations_list = conv.get("conversations", [])
            if len(conversations_list) >= 2:
                question = conversations_list[0].get("value", "")
                answer = conversations_list[1].get("value", "")
            else:
                continue
        else:
            question = conv.get("question", "")
            answer = conv.get("answer", "")

        # Try to infer 'type' from answer content if not present
        item_type = conv.get("type", "knowledge_qa")
        
        formatted = {
            "type": item_type,
            "question": question,
            "answer": answer,
            "source": conv.get("source", ""),
            "page": conv.get("page")
        }

        jsonl_lines.append(json.dumps(formatted, ensure_ascii=False))

    return jsonl_lines
