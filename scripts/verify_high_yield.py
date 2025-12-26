import sys
from pathlib import Path
import json

# Add src to path
# Add src directory to sys.path so we can import 'finetuneme' package directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from finetuneme.core.config import settings
from finetuneme.services.ingestion import DocumentChunk
from finetuneme.services.generation import generate_dataset_with_provider, MultiPassGenerator, DynamicPromptBuilder
from finetuneme.services.providers import LLMProvider

class MockProvider(LLMProvider):
    def __init__(self):
        self.model = "mock-model"

    @property
    def provider_name(self) -> str:
        return "mock"

    def get_default_model(self) -> str:
        return "mock-model"

    def list_models(self) -> list:
        return ["mock-model"]
        
    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        # Simulate Multi-Pass Output based on prompt content
        
        # Pass 1: Knowledge QA
        if "Atomic Knowledge Extraction" in system_prompt:
            return json.dumps([
                {
                    "type": "knowledge_qa",
                    "question": "What is the chunk size?",
                    "answer": "The chunk size is 600.",
                    "context": "size is 600",
                    "section": "Test"
                },
                {
                    "type": "knowledge_qa",
                    "question": "What is the overlap?",
                    "answer": "The overlap is 100.",
                    "context": "overlap is 100",
                    "section": "Test"
                },
                {
                    "type": "knowledge_qa",
                    "question": "What is the density?",
                    "answer": "High density.",
                    "context": "High density",
                    "section": "Test"
                }
            ])
            
        # Pass 2: Scenarios (Triggers present)
        if "Create audit simulation" in system_prompt or "compliant/non-compliant" in system_prompt:
             return json.dumps([
                {
                    "type": "audit_simulation",
                    "section": "Section Test",
                    "requirement": "Must have high density",
                    "compliant_scenario": {"company_name": "Good", "excerpt": "We have high density"},
                    "non_compliant_scenario": {"company_name": "Bad", "excerpt": "Low density"},
                    "audit_finding": {"finding": "Low density detected", "severity": "Major", "objective_evidence": "Bad excerpt"}
                }
            ])
            
        return "[]"
        
    def is_available(self) -> bool:
        return True

def test_high_yield_config():
    print("Testing Config...")
    assert settings.CHUNK_SIZE == 600, f"CHUNK_SIZE should be 600, got {settings.CHUNK_SIZE}"
    assert settings.CHUNK_OVERLAP == 100, f"CHUNK_OVERLAP should be 100, got {settings.CHUNK_OVERLAP}"
    print("✓ Config verified")

def test_multipass_logic():
    print("\nTesting Multi-Pass Logic...")
    
    # 1. Create a mock chunk with triggers
    text = "The system must ensure high density. Compliance is required. The chunk size shall be 600."
    chunk = DocumentChunk(text=text, page_num=1, metadata={"source": "test_doc.pdf"})
    
    # 2. Check Scenario Trigger
    should_run = MultiPassGenerator.should_run_scenario_pass(text, "strict_auditor")
    print(f"Trigger Check (Auditor + 'must'): {should_run}")
    assert should_run == True, "Should trigger scenario pass for auditor + 'must'"
    
    should_run_teacher = MultiPassGenerator.should_run_scenario_pass(text, "teacher")
    print(f"Trigger Check (Teacher + 'must'): {should_run_teacher}")
    assert should_run_teacher == True, "Should trigger scenario pass for teacher + 'must'"
    
    should_run_generic = MultiPassGenerator.should_run_scenario_pass("Simple text", "user")
    print(f"Trigger Check (User + 'Simple'): {should_run_generic}")
    assert should_run_generic == False, "Should NOT trigger scenario pass for generic user/text"

    # 3. Simulate Generation
    provider = MockProvider()
    results = MultiPassGenerator.generate_multipass(chunk, provider, "strict_auditor")
    
    print(f"\nGenerated Items: {len(results)}")
    for item in results:
        print(f"- {item.get('type')}")
        
    assert len(results) >= 4, "Should generate at least 4 items (3 QA + 1 Audit)"
    
    types = [item.get("type") for item in results]
    assert "knowledge_qa" in types
    assert "audit_simulation" in types
    print("✓ Multi-Pass Logic Verified")

if __name__ == "__main__":
    try:
        test_high_yield_config()
        test_multipass_logic()
        print("\nSUCCESS: High-Yield Logic Verified Locally")
    except AssertionError as e:
        print(f"\nFAILURE: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
