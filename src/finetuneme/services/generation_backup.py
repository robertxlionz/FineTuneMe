"""
Service for handling LLM generation via multiple providers.
Supports Ollama (local), Groq, OpenAI, and Anthropic.
Generates Q&A pairs from document chunks with role-based prompts.
"""
import requests
from openai import OpenAI
from typing import List, Dict, Optional
from src.finetuneme.core.config import settings
from src.finetuneme.services.ingestion import DocumentChunk
from src.finetuneme.services.providers import get_provider, list_all_providers, LLMProvider
import json
import re

# Role-based system prompts
# Role definitions for Expert Prompt V5
ROLE_DESCRIPTIONS = {
    "strict_auditor": """You are a strict auditor analyzing documents for compliance and accuracy.
Your primary focus is identifying potential non-compliance risks and testing the organization's adherence to regulations.
You prioritize practical, scenario-based audit simulations over simple fact retrieval.""",

    "teacher": """You are an experienced teacher creating educational content.
Your primary focus is ensuring students understand key concepts, definitions, and requirements.
You prioritize clear, foundational 'Knowledge QA' pairs that explain 'What', 'Why', and 'How'.""",

    "technical_analyst": """You are a technical analyst breaking down complex specifications.
Your primary focus is accuracy and technical precision.
You prioritize detailing specific parameters, device specifications, and engineering requirements.""",

    "researcher": """You are a researcher synthesizing information.
Your primary focus is connecting dots between different sections and understanding the broader implications.
You prioritize insights that link multiple concepts together."""
}

EXPERT_PROMPT_TEMPLATE = """# System Prompt: Expert Dataset Generation

You are an expert knowledge engineer and data synthesizer acting in the role of: **{ROLE_NAME}**.

{ROLE_DESCRIPTION}

## Objective
Analyze the provided document chunk and extract high-quality training data. Your goal is to create a dataset that trains other models to be top-tier experts in this domain.

## Output Format
You must output a JSON array of objects. Each object represents a distinct piece of knowledge or scenario derived *strictly* from the text.

### Schema Types

#### 1. Knowledge QA (`knowledge_qa`)
Use this for definitions, factual requirements, and clear explanations.
{{
  "type": "knowledge_qa",
  "question": "Specific question testing understanding",
  "answer": "Comprehensive, accurate answer citing the text.",
  "context": "Verbatim excerpt from the text used to derive this answer",
  "section": "Section header or reference ID (e.g., '§ 820.3(a)')",
  "source_file": "{SOURCE_FILENAME}"
}}

#### 2. Audit Simulation (`audit_simulation`)
Use this when the text describes a process, requirement, or rule that can be audited. Create a realistic "Compliance vs. Non-Compliance" scenario.
{{
  "type": "audit_simulation",
  "section": "Section header or reference ID",
  "requirement": "The specific rule being tested (verbatim or summarized)",
  "compliant_scenario": {{
    "company_name": "MediTech Solutions Inc.",
    "document_type": "Procedure/Record",
    "excerpt": "Realistic text of a compliant document..."
  }},
  "non_compliant_scenario": {{
    "company_name": "BioHealth Corp.",
    "document_type": "Procedure/Record",
    "excerpt": "Realistic text of a non-compliant document (subtle failure)..."
  }},
  "audit_finding": {{
    "finding": "Clear statement of non-compliance",
    "severity": "Major/Minor",
    "objective_evidence": "Why the non-compliant scenario fails the requirement"
  }},
  "source_file": "{SOURCE_FILENAME}"
}}

## Rules
1.  **Strict JSON**: Output *only* the JSON array. No markdown, no conversation.
2.  **Role Adherence**:
    *   If **Strict Auditor**: Prioritize `audit_simulation` for every actionable requirement.
    *   If **Teacher**: Prioritize `knowledge_qa` with clear, instructional answers.
    *   If **Technical**: Focus on implementation details.
3.  **Accuracy**: Do not hallucinate. If the chunk is just a header or footer with no content, return an empty array `[]`.
4.  **Verification**: Ensure `context` and `section` are extracted accurately to allow traceability.
"""

def get_expert_system_prompt(role: str, source_filename: str = "Unknown", custom_prompt: Optional[str] = None) -> str:
    """Get the dynamic system prompt based on role using Prompt V5"""
    if role == "custom" and custom_prompt:
        return sanitize_prompt(custom_prompt)
        
    role_key = role.lower()
    role_desc = ROLE_DESCRIPTIONS.get(role_key, ROLE_DESCRIPTIONS["teacher"])
    role_name = role.replace("_", " ").title()
    
    return EXPERT_PROMPT_TEMPLATE.format(
        ROLE_NAME=role_name,
        ROLE_DESCRIPTION=role_desc,
        SOURCE_FILENAME=source_filename
    )

def get_system_prompt(role: str, custom_prompt: Optional[str] = None) -> str:
    """Legacy wrapper for backward compatibility"""
    return get_expert_system_prompt(role, "Legacy Document", custom_prompt)

def sanitize_prompt(prompt: str) -> str:
    """Sanitize user input to prevent prompt injection"""
    dangerous_patterns = [
        r"ignore (previous|above|all) instructions?",
        r"system:",
        r"assistant:",
        r"</?(system|user|assistant)>",
        r"you are now",
        r"forget (everything|all|previous)",
    ]

    cleaned = prompt
    for pattern in dangerous_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    return cleaned[:500]

def check_ollama_available() -> bool:
    """Check if Ollama is running locally"""
    try:
        response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False

def list_ollama_models() -> List[str]:
    """List available Ollama models"""
    try:
        response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
        if response.status_code == 200:
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        return []
    except:
        return []

def generate_with_ollama(
    system_prompt: str,
    user_prompt: str,
    model: str
) -> Optional[str]:
    """Generate response using local Ollama"""
    try:
        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": f"System: {system_prompt}\n\nUser: {user_prompt}",
                "stream": False,
                "options": {
                    "temperature": 0.7
                }
            },
            timeout=120
        )

        if response.status_code == 200:
            return response.json().get("response")
        return None

    except Exception as e:
        print(f"Ollama generation error: {str(e)}")
        return None

def generate_with_openrouter(
    system_prompt: str,
    user_prompt: str,
    model: str
) -> Optional[str]:
    """Generate response using OpenRouter API"""
    try:
        client = OpenAI(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY,
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"OpenRouter generation error: {str(e)}")
        return None

def generate_qa_from_chunk(
    chunk: DocumentChunk,
    role: str,
    custom_prompt: Optional[str] = None,
    model: str = None,
    use_ollama: bool = True
) -> List[Dict]:
    """
    Generate Q&A pairs from a single document chunk.

    Args:
        chunk: DocumentChunk object
        role: Role for generation
        custom_prompt: Optional custom system prompt
        model: Model name
        use_ollama: Use Ollama if True, OpenRouter if False

    Returns:
        List of Q&A dictionaries
    """
    if not model:
        model = settings.DEFAULT_MODEL

    system_prompt = get_system_prompt(role, custom_prompt)

    user_prompt = f"""Based on the following text, generate 2-3 high-quality question-answer pairs.

Text:
{chunk.text}

Requirements:
1. Questions should be clear and specific
2. Answers should be comprehensive and accurate
3. Focus on the most important information
4. Ensure answers are grounded in the provided text

Return ONLY a JSON array of objects with 'question' and 'answer' fields.
Example format:
[
  {{"question": "What is...", "answer": "..."}},
  {{"question": "How does...", "answer": "..."}}
]
"""

    # Choose generation method
    if use_ollama and check_ollama_available():
        content = generate_with_ollama(system_prompt, user_prompt, model)
    else:
        if not settings.OPENROUTER_API_KEY:
            print("Warning: No Ollama or OpenRouter available")
            return []
        content = generate_with_openrouter(system_prompt, user_prompt, model)

    if not content:
        return []

    # Extract JSON from response
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        qa_pairs = json.loads(content)
        return qa_pairs

    except Exception as e:
        print(f"Error parsing Q&A: {str(e)}")
        return []

def generate_dataset(
    chunks: List[DocumentChunk],
    role: str,
    custom_prompt: Optional[str] = None,
    model: str = None,
    use_ollama: bool = True,
    progress_callback=None
) -> List[Dict]:
    """
    Generate complete dataset from all chunks.
    DEPRECATED: Use generate_dataset_with_provider for new code.

    Args:
        chunks: List of DocumentChunk objects
        role: Role for generation
        custom_prompt: Optional custom system prompt
        model: Model name
        use_ollama: Use Ollama if True, OpenRouter if False
        progress_callback: Optional callback function(current, total)

    Returns:
        List of conversation dictionaries in ShareGPT format
    """
    if not model:
        model = settings.DEFAULT_MODEL

    all_conversations = []
    total_chunks = len(chunks)

    for idx, chunk in enumerate(chunks):
        # Generate Q&A pairs for this chunk
        qa_pairs = generate_qa_from_chunk(chunk, role, custom_prompt, model, use_ollama)

        # Convert to ShareGPT format
        for qa in qa_pairs:
            conversation = {
                "conversations": [
                    {"from": "human", "value": qa.get("question", "")},
                    {"from": "gpt", "value": qa.get("answer", "")}
                ],
                "source": chunk.metadata.get("source", ""),
                "page": chunk.page_num
            }
            all_conversations.append(conversation)

        # Update progress
        if progress_callback:
            progress_callback(idx + 1, total_chunks)

    return all_conversations


# ===== NEW MULTI-PROVIDER FUNCTIONS =====

def generate_qa_from_chunk_with_provider(
    chunk: DocumentChunk,
    provider: LLMProvider,
    role: str,
    custom_prompt: Optional[str] = None
) -> List[Dict]:
    """
    Generate Q&A pairs from a single document chunk using a provider.
    Now supports V5 Expert Schema (Polymorphic).

    Args:
        chunk: DocumentChunk object
        provider: LLMProvider instance
        role: Role for generation
        custom_prompt: Optional custom system prompt

    Returns:
        List of Q&A dictionaries (structure varies by type)
    """
    # Use the new expert prompt with source filename
    source_file = chunk.metadata.get("source", "Unknown") if chunk.metadata else "Unknown"
    system_prompt = get_expert_system_prompt(role, source_file, custom_prompt)

    user_prompt = f"""Analyze the following text and extract relevant training data according to your Role and Schema.

Text:
{chunk.text}
"""

    # Generate using provider
    content = provider.generate(system_prompt, user_prompt, temperature=0.7)

    if not content:
        return []

    # Extract JSON from response
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        qa_pairs = json.loads(content)
        
        # Validate list
        if isinstance(qa_pairs, list):
            return qa_pairs
        elif isinstance(qa_pairs, dict):
            return [qa_pairs]
        return []

    except Exception as e:
        print(f"Error parsing Q&A: {str(e)}")
        return []


def generate_dataset_with_provider(
    chunks: List[DocumentChunk],
    provider_type: str,
    role: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    custom_prompt: Optional[str] = None,
    progress_callback=None
) -> List[Dict]:
    """
    Generate complete dataset from all chunks using specified provider.
    Supports V5 Polymorphic Schema mapping to ShareGPT.

    Args:
        chunks: List of DocumentChunk objects
        provider_type: Provider type ("ollama", "groq", "openai", "anthropic")
        role: Role for generation
        api_key: API key for cloud providers (not needed for Ollama)
        model: Model name (uses provider default if not specified)
        custom_prompt: Optional custom system prompt
        progress_callback: Optional callback function(current, total)

    Returns:
        List of conversation dictionaries in ShareGPT format
    """
    # Get provider
    provider = get_provider(provider_type, api_key=api_key, model=model)

    # Check if provider is available
    if not provider.is_available():
        raise RuntimeError(f"Provider {provider_type} is not available. Check configuration and API keys.")

    all_conversations = []
    total_chunks = len(chunks)

    for idx, chunk in enumerate(chunks):
        # Generate data points for this chunk
        data_points = generate_qa_from_chunk_with_provider(chunk, provider, role, custom_prompt)

        # Convert to ShareGPT format with polymorphic handling
        for item in data_points:
            human_msg = ""
            gpt_msg = ""
            
            # 1. Audit Simulation Strategy
            if item.get("type") == "audit_simulation":
                scenario = item.get("non_compliant_scenario", {}).get("excerpt", "")
                section = item.get("section", "Global")
                
                # Human acts as the 'Lead Auditor' asking the finding
                human_msg = f"Review the following scenario against regulation {section}:\n\n{scenario}"
                
                # GPT acts as the 'Auditor' documenting the finding
                finding = item.get("audit_finding", {})
                gpt_msg = f"**Finding:** {finding.get('finding', 'Non-compliance detected')}\n\n**Severity:** {finding.get('severity', 'Major')}\n\n**Objective Evidence:** {finding.get('objective_evidence', 'No evidence provided')}"
            
            # 2. Default Knowledge QA Strategy
            else:
                human_msg = item.get("question", "")
                gpt_msg = item.get("answer", "")
            
            # Skip empty generations
            if not human_msg or not gpt_msg:
                continue

            conversation = {
                "conversations": [
                    {"from": "human", "value": human_msg},
                    {"from": "gpt", "value": gpt_msg}
                ],
                "source": chunk.metadata.get("source", ""),
                "page": chunk.page_num,
                "provider": provider_type,
                "model": provider.model,
                # Preserving valid ShareGPT format while keeping rich metadata flat at root
                **{k: v for k, v in item.items() if k not in ['question', 'answer', 'type']}
            }
            # Explicitly set type
            conversation["type"] = item.get("type", "knowledge_qa")
            
            all_conversations.append(conversation)

        # Update progress
        if progress_callback:
            progress_callback(idx + 1, total_chunks)

    return all_conversations
