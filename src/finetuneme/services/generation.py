"""
Service for handling LLM generation via multiple providers.
Supports Ollama (local), Groq, OpenAI, and Anthropic.
Generates Q&A pairs from document chunks with role-based prompts.
Implemented Strategy: High-Yield Flexible Architecture (Phase 2.5)
"""
import requests
from openai import OpenAI
from typing import List, Dict, Optional, Any
from finetuneme.core.config import settings
from finetuneme.services.ingestion import DocumentChunk
from finetuneme.services.providers import get_provider, list_all_providers, LLMProvider
import json
import json_repair
import re
import time

# ============================================================================
# 1. DYNAMIC PROMPT BUILDER
# ============================================================================

class DynamicPromptBuilder:
    """
    Constructs high-yield system prompts dynamically.
    Injects "Atomic/Exhaustive" directives into every role.
    """
    
    HIGH_YIELD_DIRECTIVE = """
## Extraction Rules (CRITICAL)
1. **Atomic Extraction**: Break down complex concepts into multiple, distinct QA pairs. Do not compress information.
2. **Exhaustive Scope**: Extract EVERY definition, requirement, rule, and condition. If a chunk contains 5 distinct facts, generate 5 distinct pairs.
3. **Grounding**: Every answer must citation the specific text source.
4. **Density**: Aim for 3-5 records per chunk if data density permits.
"""

    UNIVERSAL_SCHEMA = """
## Output Schema
You must output a JSON LIST of objects. Support multiple types:

### 1. Knowledge QA (Default)
{
  "type": "knowledge_qa",
  "question": "Specific question...",
  "answer": "Comprehensive answer citation...",
  "context": "Verbatim snippet...",
  "section": "Section reference..."
}

### 2. Audit Simulation (If applicable)
{
  "type": "audit_simulation",
  "section": "Section...",
  "requirement": "The rule...",
  "compliant_scenario": {"company_name": "...", "excerpt": "..."},
  "non_compliant_scenario": {"company_name": "...", "excerpt": "..."},
  "audit_finding": {"finding": "...", "severity": "Major/Minor", "objective_evidence": "..."}
}
"""

    @staticmethod
    def build(role: str, custom_prompt: Optional[str] = None) -> str:
        # Determine Base Identity
        identity = ""
        if role == "custom" and custom_prompt:
            identity = f"You are an expert. Instruction: {custom_prompt}"
        else:
            # Simple identity mapping
            role_map = {
                "strict_auditor": "You are a strict auditor looking for risks and non-compliance.",
                "teacher": "You are an expert teacher explaining concepts clearly.",
                "technical_analyst": "You are a technical analyst focusing on specs and parameters.",
                "researcher": "You are a researcher connecting concepts."
            }
            identity = role_map.get(role.lower(), "You are an expert knowledge engineer.")

        # Assemble
        return f"{identity}\n{DynamicPromptBuilder.HIGH_YIELD_DIRECTIVE}\n{DynamicPromptBuilder.UNIVERSAL_SCHEMA}"

def get_expert_system_prompt(role: str, source_filename: str = "Unknown", custom_prompt: Optional[str] = None) -> str:
    """Legacy wrapper maintained for backward compatibility, mapped to Builder"""
    return DynamicPromptBuilder.build(role, custom_prompt)

def get_system_prompt(role: str, custom_prompt: Optional[str] = None) -> str:
    """Legacy wrapper"""
    return DynamicPromptBuilder.build(role, custom_prompt)


# ============================================================================
# 2. PROVIDER UTILS (Ollama/OpenAI)
# ============================================================================

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

# ============================================================================
# 3. MULTI-PASS GENERATION LOGIC
# ============================================================================

def clean_json_text(text: str) -> str:
    """Clean JSON text by identifying the JSON structure."""
    text = text.strip()
    
    # Handle markdown code blocks first
    if "```json" in text:
        try:
            return text.split("```json")[1].split("```")[0].strip()
        except IndexError:
            pass # Fallback to regex/finding brackets
    elif "```" in text:
        try:
            return text.split("```")[1].split("```")[0].strip()
        except IndexError:
            pass
            
    # Locate first '[' or '{'
    first_bracket = text.find('[')
    first_brace = text.find('{')
    
    start_idx = -1
    end_idx = -1
    
    # Determine if we are looking for a list or dict as the outer element
    if first_bracket != -1 and (first_brace == -1 or first_bracket < first_brace):
        # List
        start_idx = first_bracket
        end_idx = text.rfind(']')
    elif first_brace != -1:
        # Dict
        start_idx = first_brace
        end_idx = text.rfind('}')
        
    if start_idx != -1 and end_idx != -1:
        return text[start_idx : end_idx + 1]
        
    return text

def parse_polymorphic_response(content: str) -> List[Dict]:
    """Parse JSON that might be a list or single dict, handling errors content"""
    # 1. First cleaning: Strip markdown code blocks if present
    cleaned = clean_json_text(content)
    
    try:
        # 2. Use json_repair to handle unterminated strings, missing quotes, etc.
        data = json_repair.loads(cleaned)

        if isinstance(data, list):
            # Ensure "type" exists
            valid_items = []
            for item in data:
                # filter out non-dict items if any
                if not isinstance(item, dict):
                    continue
                if "question" in item and "type" not in item:
                    item["type"] = "knowledge_qa"
                valid_items.append(item)
            return valid_items
            
        elif isinstance(data, dict):
            if "qas" in data: # Handle legacy nesting
                return data["qas"]
            if "question" in data and "type" not in data:
                data["type"] = "knowledge_qa"
            return [data]
            
        return []
    except Exception as e:
        print(f"Error parsing JSON: {str(e)}")
        # Debug: Print a snippet of the failed content
        snippet = content[:200] + "..." if len(content) > 200 else content
        print(f"  > Content snippet: {snippet}")
        return []

class MultiPassGenerator:
    """
    Explicit Multi-Pass Generation Engine.
    Pass 1: Core Knowledge Extraction (always runs)
    Pass 2: Scenario/Application Generation (conditional based on content)
    """

    @staticmethod
    def should_run_scenario_pass(text: str, role: str) -> bool:
        """Determine if Pass 2 (scenarios) should run"""
        # Check role applicability
        scenario_roles = ["strict_auditor", "auditor", "teacher", "technical_analyst"]
        if role.lower() not in scenario_roles and role != "custom":
            return False

        # Check content triggers (must/shall/error/warning/compliance)
        triggers = ["must", "shall", "required", "mandatory", "error", "warning", "compliance", "violation"]
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in triggers)

    @staticmethod
    def pass1_knowledge_extraction(
        chunk: DocumentChunk,
        provider: LLMProvider,
        role: str
    ) -> List[Dict]:
        """Pass 1: Extract Core Knowledge as QA pairs (High-Yield) with vision support"""
        source_file = chunk.metadata.get("source", "Unknown") if chunk.metadata else "Unknown"

        # Use DynamicPromptBuilder to get the High-Yield Directive & Universal Schema
        # This ensures we get the "Atomic/Exhaustive" behavior
        system_prompt = DynamicPromptBuilder.build(role)

        # Check if chunk contains images
        has_images = chunk.images and len(chunk.images) > 0

        # Inject vision-specific instruction if images are present
        if has_images:
            system_prompt += """

## VISION EXTRACTION PROTOCOL (STRICT)
This document contains visual elements (charts, diagrams, slides, screenshots).
1. **Transcribe Everything**: If the image contains text, you MUST transcribe it verbatim.
2. **Describe Structure**: For charts/graphs, extract the data points and trends.
3. **No Placeholders**: NEVER say "There is an image of X". Instead, output "The image shows X, which consists of..."
4. **Integration**: Treat visual content as first-class knowledge. Extract QA pairs from the images just as you would from text."""

        user_prompt = f"""**Source**: {source_file} (Page {chunk.page_num})

**Text Chunk**:
{chunk.text}

**Task**: Extract ALL knowledge as atomic QA pairs.
- Follow the "Extraction Rules" in the system prompt.
- Generate valid JSON only. No markdown formatting. No conversational filler."""

        if has_images:
            user_prompt += f"\n\n**VISION TASK**: I have attached {len(chunk.images)} image(s) to this message. \nIGNORE any text placeholders like '[Image 1]'. \nINSTEAD, look at the actual image attachment and extract every piece of information visible in it."

        try:
            # Pass images to the provider if available
            content = provider.generate(
                system_prompt,
                user_prompt,
                temperature=0.6,
                images=chunk.images if has_images else None
            )
            if not content:
                return []
            return parse_polymorphic_response(content)
        except Exception as e:
            print(f"Pass 1 error (chunk {chunk.page_num}): {str(e)}")
            return []

    @staticmethod
    def pass2_scenario_generation(
        chunk: DocumentChunk,
        provider: LLMProvider,
        role: str
    ) -> List[Dict]:
        """Pass 2: Generate Scenarios/Applications"""
        source_file = chunk.metadata.get("source", "Unknown") if chunk.metadata else "Unknown"

        # Role-specific scenario prompts
        if "audit" in role.lower():
            scenario_type = "audit simulation with compliant/non-compliant examples"
            output_example = """{
  "type": "audit_simulation",
  "section": "Section X.Y",
  "requirement": "The specific rule...",
  "compliant_scenario": {"company_name": "GoodCo", "excerpt": "..."},
  "non_compliant_scenario": {"company_name": "BadCo", "excerpt": "..."},
  "audit_finding": {
      "reasoning": "Step-by-step analysis of why this violates the rule...",
      "finding": "...", 
      "severity": "Major", 
      "objective_evidence": "..."
  }
}"""
        elif "teacher" in role.lower():
            scenario_type = "teaching scenario with practical example"
            output_example = """{
  "type": "teaching_scenario",
  "concept": "The concept being taught...",
  "real_world_example": "Practical application...",
  "common_mistakes": "What students often get wrong...",
  "explanation": "Detailed breakdown..."
}"""
        else:
            scenario_type = "practical application scenario"
            output_example = """{
  "type": "application_scenario",
  "rule": "The rule or concept...",
  "scenario": "Practical situation...",
  "analysis": "How to apply the rule (step-by-step)..."
}"""

        system_prompt = f"""You are an expert {role} creating practical scenarios.

## Mission: Generate Real-World Applications

Create {scenario_type} based on the rules/concepts in the text.

## Output Format
Return a strictly valid JSON list with scenario objects. Do NOT include markdown blocks.
[
  {output_example}
]
"""

        user_prompt = f"""**Source**: {source_file} (Page {chunk.page_num})

**Text Chunk**:
{chunk.text}

**Task**: Create 1-2 practical scenarios that apply the rules/concepts from this text. Ensure output is a VALID JSON LIST."""

        try:
            content = provider.generate(system_prompt, user_prompt, temperature=0.7)
            if not content:
                return []
            return parse_polymorphic_response(content)
        except Exception as e:
            print(f"Pass 2 error (chunk {chunk.page_num}): {str(e)}")
            return []

    @staticmethod
    def generate_multipass(
        chunk: DocumentChunk,
        provider: LLMProvider,
        role: str,
        custom_prompt: Optional[str] = None
    ) -> List[Dict]:
        """Execute multi-pass generation on a single chunk"""
        all_results = []

        # Pass 1: Knowledge Extraction (ALWAYS RUNS)
        print(f"  - Pass 1 (Knowledge) - Chunk {chunk.page_num}...")
        pass1_results = MultiPassGenerator.pass1_knowledge_extraction(chunk, provider, role)
        all_results.extend(pass1_results)
        print(f"    + Extracted {len(pass1_results)} knowledge items")

        # Pass 2: Scenario Generation (CONDITIONAL)
        if MultiPassGenerator.should_run_scenario_pass(chunk.text, role):
            print(f"  - Pass 2 (Scenarios) - Chunk {chunk.page_num}...")
            pass2_results = MultiPassGenerator.pass2_scenario_generation(chunk, provider, role)
            all_results.extend(pass2_results)
            print(f"    + Generated {len(pass2_results)} scenarios")
        else:
            print(f"  x Pass 2 skipped (no scenario triggers)")

        return all_results

def generate_qa_from_chunk_with_provider(
    chunk: DocumentChunk,
    provider: LLMProvider,
    role: str,
    custom_prompt: Optional[str] = None
) -> List[Dict]:
    """
    Generate High-Yield Data from a single chunk.
    NOW uses explicit MultiPassGenerator.
    """
    return MultiPassGenerator.generate_multipass(chunk, provider, role, custom_prompt)


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
    Main Generation Loop with Explicit Multi-Pass Architecture.
    Iterates chunks and aggregates polymorphic results into ShareGPT format.

    This function implements the High-Density extraction strategy:
    - Uses small chunks (600 tokens) to prevent summary compression
    - Runs explicit Pass 1 (Knowledge) on every chunk
    - Runs Pass 2 (Scenarios) conditionally when triggers detected
    - Target: 10x density improvement (from ~3 to ~30 lines/page)
    """
    # Get provider
    provider = get_provider(provider_type, api_key=api_key, model=model)

    if not provider.is_available():
        raise RuntimeError(f"Provider {provider_type} is not available.")

    all_conversations = []
    total_chunks = len(chunks)

    print("=" * 70)
    print(">> HIGH-DENSITY MULTI-PASS EXTRACTION ENGINE")
    print("=" * 70)
    print(f"Strategy: Explicit Multi-Pass Generation")
    print(f"Chunk Size: {settings.CHUNK_SIZE} chars (overlap: {settings.CHUNK_OVERLAP})")
    print(f"Total Chunks: {total_chunks}")
    print(f"Role: {role}")
    print(f"Provider: {provider_type} ({provider.model})")
    print(f"Target Density: 3-5 records per chunk (10x improvement)")
    print("=" * 70)
    print()

    start_time = time.time()
    total_records = 0

    for idx, chunk in enumerate(chunks):
        # Garbage Chunk Filtering (Performance Optimization)
        # Refined Logic:
        # 1. Skip very short chunks (<20 chars) - likely noise (lowered from 50 for robust testing)
        # 2. Skip copyright/boilerplate ONLY if the chunk is short (<400 chars)
        #    This prevents skipping full content pages that just happen to have a copyright footer.
        # 3. NEVER skip chunks with images attached - they contain visual information
        text_len = len(chunk.text)
        text_lower = chunk.text.lower()
        has_images = chunk.images and len(chunk.images) > 0

        is_copyright_blob = ("copyright" in text_lower or "all rights reserved" in text_lower) and text_len < 400

        # Skip if low quality AND no images
        if (text_len < 20 or is_copyright_blob) and not has_images:
            print(f"[SKIP] Chunk {idx + 1}: Low information density (length: {text_len}). Threshold: 20.")
            # Update progress even for skipped chunks
            if progress_callback:
                progress_callback(idx + 1, total_chunks)
            continue

        print(f"[Chunk {idx + 1}/{total_chunks}] Processing page {chunk.page_num}...")

        # Generate raw data points using MultiPassGenerator
        data_points = generate_qa_from_chunk_with_provider(chunk, provider, role, custom_prompt)

        chunk_record_count = 0

        # Map to ShareGPT Format
        for item in data_points:
            try:
                conversation = convert_to_sharegpt(item, chunk, provider_type, provider.model)
                if conversation:
                    all_conversations.append(conversation)
                    chunk_record_count += 1
            except Exception as e:
                print(f"  [!] Error converting item: {e}")

        total_records += chunk_record_count
        print(f"  > Chunk complete: {chunk_record_count} records | Running total: {total_records}")
        print()

        # Update progress
        if progress_callback:
            progress_callback(idx + 1, total_chunks)

    elapsed_time = time.time() - start_time
    avg_per_chunk = total_records / total_chunks if total_chunks > 0 else 0

    print("=" * 70)
    print(">> EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Total Records Generated: {total_records}")
    print(f"Average per Chunk: {avg_per_chunk:.2f}")
    print(f"Processing Time: {elapsed_time:.1f}s ({elapsed_time/total_chunks:.1f}s per chunk)")
    print(f"High-Yield Multiplier: {avg_per_chunk / 1.0:.1f}x (baseline: 1 record/chunk)")
    print("=" * 70)

    return all_conversations

def convert_to_sharegpt(item: Dict, chunk: DocumentChunk, provider: str, model: str) -> Optional[Dict]:
    """
    Helper to convert various polymorphic schema types to ShareGPT format.
    Supports: knowledge_qa, audit_simulation, teaching_scenario, application_scenario
    """
    human_msg = ""
    gpt_msg = ""
    data_type = item.get("type", "knowledge_qa")

    # 1. Audit Simulation
    if data_type == "audit_simulation":
        scenario = item.get("non_compliant_scenario", {}).get("excerpt", "")
        section = item.get("section", "Global")
        finding = item.get("audit_finding", {})

        if not scenario or not finding:
            return None

        human_msg = f"Review this scenario against regulation {section}:\n\n{scenario}"
        
        # Add reasoning if available (CoT)
        reasoning = finding.get('reasoning', '')
        gpt_msg = ""
        if reasoning:
            gpt_msg += f"**Analysis:** {reasoning}\n\n"
            
        gpt_msg += f"**Finding:** {finding.get('finding')}\n**Severity:** {finding.get('severity')}\n**Evidence:** {finding.get('objective_evidence')}"

    # 2. Teaching Scenario
    elif data_type == "teaching_scenario":
        concept = item.get("concept", "")
        example = item.get("real_world_example", "")
        mistakes = item.get("common_mistakes", "")
        explanation = item.get("explanation", "")

        if not concept or not example:
            return None

        human_msg = f"Explain the concept: {concept}"
        gpt_msg = f"**Concept:** {concept}\n\n**Real-World Example:**\n{example}"
        
        if mistakes:
            gpt_msg += f"\n\n**Common Mistakes:**\n{mistakes}"
        
        if explanation:
            gpt_msg += f"\n\n**Deep Dive:**\n{explanation}"

    # 3. Application Scenario
    elif data_type == "application_scenario":
        rule = item.get("rule", "")
        scenario = item.get("scenario", "")
        analysis = item.get("analysis", "")

        if not rule or not scenario:
            return None

        human_msg = f"How does this rule apply?\n\nRule: {rule}\n\nScenario: {scenario}"
        gpt_msg = f"**Analysis:**\n{analysis}"

    # 4. Knowledge QA (Default)
    else:
        human_msg = item.get("question", "")
        gpt_msg = item.get("answer", "")

    if not human_msg or not gpt_msg:
        return None

    return {
        "conversations": [
            {"from": "human", "value": human_msg},
            {"from": "gpt", "value": gpt_msg}
        ],
        "source": chunk.metadata.get("source", ""),
        "page": chunk.page_num,
        "provider": provider,
        "model": model,
        "type": data_type,
        **{k: v for k, v in item.items() if k not in ['question', 'answer', 'type', 'conversations']}
    }

# ============================================================================
# 4. LEGACY FUNCTIONS (Backwards Compatibility)
# ============================================================================

def generate_qa_from_chunk(chunk, role, custom_prompt=None, model=None, use_ollama=True):
    """Deprecated: redirects to new system"""
    # Create a temporary provider wrapper
    from finetuneme.services.providers import get_provider
    provider = get_provider("ollama" if use_ollama else "openai", model=model)
    return generate_qa_from_chunk_with_provider(chunk, provider, role, custom_prompt)

def generate_dataset(chunks, role, custom_prompt=None, model=None, use_ollama=True, progress_callback=None):
    """Deprecated: redirects to new system"""
    return generate_dataset_with_provider(
        chunks, 
        "ollama" if use_ollama else "openai", 
        role, 
        model=model, 
        custom_prompt=custom_prompt, 
        progress_callback=progress_callback
    )
