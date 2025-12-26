"""
Multi-Provider AI abstraction layer.
Supports Ollama (local), Groq, OpenAI, and Anthropic.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
import os
import requests

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

from finetuneme.core.config import settings


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the provider.

        Args:
            api_key: API key for cloud providers (not used for Ollama)
            model: Model name to use
        """
        self.api_key = api_key
        self.model = model or self.get_default_model()

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, images: Optional[List[str]] = None) -> Optional[str]:
        """
        Generate a response from the LLM.

        Args:
            system_prompt: System/role prompt
            user_prompt: User content/question
            temperature: Sampling temperature (0.0 to 1.0)
            images: Optional list of base64 encoded images

        Returns:
            Generated text response, or None if error
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured correctly"""
        pass

    @abstractmethod
    def list_models(self) -> List[str]:
        """List available models for this provider"""
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model name for this provider"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name"""
        pass


class OllamaProvider(LLMProvider):
    """Provider for local Ollama models"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key=None, model=model)  # Ollama doesn't use API keys
        self.base_url = settings.OLLAMA_BASE_URL

    @property
    def provider_name(self) -> str:
        return "ollama"

    def get_default_model(self) -> str:
        return settings.DEFAULT_MODEL

    def is_available(self) -> bool:
        """Check if Ollama is running locally"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False

    def list_models(self) -> List[str]:
        """List available Ollama models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except:
            return []

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, images: Optional[List[str]] = None) -> Optional[str]:
        """Generate response using local Ollama with optional image support"""
        try:
            payload = {
                "model": self.model,
                "prompt": f"System: {system_prompt}\n\nUser: {user_prompt}",
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }

            # Add images if provided (for multimodal models like llama3.2-vision)
            if images:
                payload["images"] = images

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=600
            )

            if response.status_code == 200:
                return response.json().get("response")
            return None

        except Exception as e:
            print(f"Ollama generation error: {str(e)}")
            return None


class GroqProvider(LLMProvider):
    """Provider for Groq Cloud API"""

    # Groq available models
    AVAILABLE_MODELS = [
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]

    @property
    def provider_name(self) -> str:
        return "groq"

    def get_default_model(self) -> str:
        return "llama-3.3-70b-versatile"

    def is_available(self) -> bool:
        """Check if Groq is configured with an API key"""
        return bool(self.api_key) and Groq is not None

    def list_models(self) -> List[str]:
        """List available Groq models"""
        return self.AVAILABLE_MODELS.copy()

    def list_models_dynamic(self) -> List[str]:
        """Fetch current models from Groq API"""
        if not self.api_key:
            return []
        try:
            url = "https://api.groq.com/openai/v1/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [m['id'] for m in data.get('data', [])]
            return []
        except Exception as e:
            print(f"Error fetching Groq models: {e}")
            return []

    def _get_active_vision_model(self) -> Optional[str]:
        """Find the first available vision model dynamically"""
        models = self.list_models_dynamic()
        # Prefer models with 'vision' in name
        # Exclude known decommissioned if they still appear in list (unlikely)
        vision_models = [m for m in models if "vision" in m.lower()]
        
        if vision_models:
            print(f"[GroqProvider] Found active vision models: {vision_models}")
            # simple heuristic: prefer largest parameter count or newest?
            # actually just pick the first one that looks stable
            # Llama 3.2 90b is preferred if available
            vp_90 = next((m for m in vision_models if "90b" in m), None)
            if vp_90: return vp_90
            
            vp_11 = next((m for m in vision_models if "11b" in m), None)
            if vp_11: return vp_11
            
            # Fallback to any vision model
            return vision_models[0]
            
        print("[GroqProvider] Dynamic vision model lookup failed. Using hardcoded fallback.")
        # HARD FALLBACK: Ensure we never return None if we need vision
        # 3.2-Vision is dead. Llama 4 Scout is the new multimodal standard.
        return "meta-llama/llama-4-scout-17b-16e-instruct"

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, images: Optional[List[str]] = None) -> Optional[str]:
        """Generate response using Groq API with optional image support"""
        # Configure logging
        import logging
        logger = logging.getLogger("finetuneme.providers.groq")
        
        if Groq is None:
            raise ImportError("groq library is required for Groq support. Install with: pip install groq")

        if not self.api_key:
            logger.error("Error: Groq API key is required")
            return None

        try:
            client = Groq(api_key=self.api_key)
            
            # Determine effective model
            effective_model = self.model
            
            # Smart switch for Vision
            if images and "vision" not in effective_model:
                # Dynamically find a valid vision model
                vision_model = self._get_active_vision_model()
                
                if vision_model:
                    logger.info(f"Switching from {effective_model} to {vision_model} (dynamically resolved) to handle {len(images)} images.")
                    effective_model = vision_model
                else:
                    logger.warning("No active vision model found on Groq! Falling back to text-only (images will be dropped).")

            # Build user message content (text + images if provided)
            # CHECK: Model must be a known vision model (has 'vision' in name OR is Llama 4/Scout)
            is_vision_model = "vision" in effective_model.lower() or "llama-4" in effective_model.lower() or "scout" in effective_model.lower()

            if images and is_vision_model:
                # OPTIMIZATION: Put images FIRST in the list, then text.
                # Llama 3.2 Vision often attends better when images come before instructions.
                user_content = []
                
                # LIMIT IMAGES: Max 3 images to prevent payload issues / timeouts
                MAX_IMAGES = 3
                if len(images) > MAX_IMAGES:
                    logger.warning(f"Limiting images from {len(images)} to {MAX_IMAGES}")
                    images = images[:MAX_IMAGES]

                for img_base64 in images:
                    user_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_base64}"
                        }
                    })
                
                # Add text prompt LAST
                user_content.append({"type": "text", "text": user_prompt})
            else:
                if images:
                    logger.warning(f"Dropping images for text-only model {effective_model}")
                user_content = user_prompt

            # DEBUG: Dump payload to file
            try:
                import json
                debug_payload = {
                    "model": effective_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "[(Image data hidden)] " + str(user_prompt)}
                    ]
                }
                # Write to file
                with open("payload_debug.json", "w", encoding="utf-8") as f:
                    json.dump(debug_payload, f, indent=2)
            except Exception as e:
                print(f"Failed debug dump: {e}")

            response = client.chat.completions.create(
                model=effective_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=temperature,
                max_tokens=2000
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Groq generation error: {str(e)}")
            if hasattr(e, 'response') and e.response:
                error_body = e.response.text
                logger.error(f"GROQ ERROR BODY: {error_body}")
                
                # AUTO-DISCOVERY ON ERROR
                # If model is decommissioned, fetch and log active models to help debug
                if "decommissioned" in str(error_body) or e.response.status_code == 400:
                    try:
                        logger.info("Attempting to fetch active models for debugging...")
                        active_models = self.list_models_dynamic()
                        with open("groq_models.log", "w") as f:
                            f.write("\n".join(active_models))
                        logger.info(f"Dumped {len(active_models)} active models to groq_models.log")
                    except Exception as listing_error:
                        logger.error(f"Failed to list models during error handling: {listing_error}")

            return None


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI API"""

    # OpenAI available models
    AVAILABLE_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ]

    @property
    def provider_name(self) -> str:
        return "openai"

    def get_default_model(self) -> str:
        return "gpt-4o-mini"

    def is_available(self) -> bool:
        """Check if OpenAI is configured with an API key"""
        return bool(self.api_key) and OpenAI is not None

    def list_models(self) -> List[str]:
        """List available OpenAI models"""
        return self.AVAILABLE_MODELS.copy()

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, images: Optional[List[str]] = None) -> Optional[str]:
        """Generate response using OpenAI API with optional image support"""
        if OpenAI is None:
            raise ImportError("openai library is required for OpenAI support. Install with: pip install openai")

        if not self.api_key:
            print("Error: OpenAI API key is required")
            return None

        try:
            client = OpenAI(api_key=self.api_key)

            # Smart switch for OpenAI: gpt-3.5-turbo does not support vision
            effective_model = self.model
            if images and "gpt-3.5" in effective_model:
                print(f"[OpenAI] Switching from {effective_model} to gpt-4o-mini to handle images.")
                effective_model = "gpt-4o-mini"
            
            # Additional safety: verify model supports vision before sending images
            # (Simplification: assume all non-3.5 models in our list support vision)
            supports_vision = "gpt-3.5" not in effective_model

            # Build user message content (text + images if provided)
            if images and supports_vision:
                user_content = [{"type": "text", "text": user_prompt}]
                for img_base64 in images:
                    user_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_base64}"
                        }
                    })
            else:
                if images:
                    print(f"[OpenAI] Warning: Dropping images for model {effective_model}")
                user_content = user_prompt

            response = client.chat.completions.create(
                model=effective_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=temperature,
                max_tokens=2000
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"OpenAI generation error: {str(e)}")
            return None


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic Claude API"""

    # Anthropic available models
    AVAILABLE_MODELS = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
    ]

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def get_default_model(self) -> str:
        return "claude-3-5-sonnet-20241022"

    def is_available(self) -> bool:
        """Check if Anthropic is configured with an API key"""
        return bool(self.api_key) and Anthropic is not None

    def list_models(self) -> List[str]:
        """List available Anthropic models"""
        return self.AVAILABLE_MODELS.copy()

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, images: Optional[List[str]] = None) -> Optional[str]:
        """Generate response using Anthropic API with optional image support"""
        if Anthropic is None:
            raise ImportError("anthropic library is required for Anthropic support. Install with: pip install anthropic")

        if not self.api_key:
            print("Error: Anthropic API key is required")
            return None

        try:
            client = Anthropic(api_key=self.api_key)

            # Build user message content (text + images if provided)
            if images:
                user_content = [{"type": "text", "text": user_prompt}]
                for img_base64 in images:
                    user_content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": img_base64
                        }
                    })
            else:
                user_content = user_prompt

            response = client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_content}
                ]
            )

            return response.content[0].text

        except Exception as e:
            print(f"Anthropic generation error: {str(e)}")
            return None


# Factory function to get appropriate provider
def get_provider(
    provider_type: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> LLMProvider:
    """
    Get the appropriate LLM provider based on type.

    Args:
        provider_type: Type of provider ("ollama", "groq", "openai", "anthropic")
        api_key: API key for cloud providers
        model: Model name to use

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider type is not supported
    """
    provider_type = provider_type.lower()

    providers = {
        "ollama": OllamaProvider,
        "groq": GroqProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }

    provider_class = providers.get(provider_type)
    if not provider_class:
        raise ValueError(f"Unsupported provider type: {provider_type}. Supported: {list(providers.keys())}")

    return provider_class(api_key=api_key, model=model)


def list_all_providers() -> Dict[str, Dict]:
    """
    List all available providers and their status.

    Respects FTM_DEPLOYMENT_MODE environment variable:
    - "cloud": Disables Ollama (local AI)
    - "local" or unset: Enables all providers

    Returns:
        Dictionary with provider info
    """
    providers_info = {}

    # Check deployment mode
    deployment_mode = os.getenv("FTM_DEPLOYMENT_MODE", "local").lower()
    is_cloud_only = deployment_mode == "cloud"

    # Ollama - disabled in cloud mode
    if is_cloud_only:
        # Force Ollama to unavailable in cloud mode
        providers_info["ollama"] = {
            "name": "Ollama (Local)",
            "available": False,
            "requires_api_key": False,
            "models": []
        }
    else:
        # Normal behavior in local mode
        ollama = OllamaProvider()
        providers_info["ollama"] = {
            "name": "Ollama (Local)",
            "available": ollama.is_available(),
            "requires_api_key": False,
            "models": ollama.list_models() if ollama.is_available() else []
        }

    # Groq
    providers_info["groq"] = {
        "name": "Groq",
        "available": Groq is not None,
        "requires_api_key": True,
        "models": GroqProvider.AVAILABLE_MODELS
    }

    # OpenAI
    providers_info["openai"] = {
        "name": "OpenAI",
        "available": OpenAI is not None,
        "requires_api_key": True,
        "models": OpenAIProvider.AVAILABLE_MODELS
    }

    # Anthropic
    providers_info["anthropic"] = {
        "name": "Anthropic Claude",
        "available": Anthropic is not None,
        "requires_api_key": True,
        "models": AnthropicProvider.AVAILABLE_MODELS
    }

    return providers_info
