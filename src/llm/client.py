"""Unified Gemini API client with token counting and cost tracking."""

import json
import os
import time
from pathlib import Path
from typing import TypeVar

import google.generativeai as genai
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

from src.models import LLMUsage

T = TypeVar("T", bound=BaseModel)

# Project root for config loading
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class GeminiClient:
    """Unified LLM client routing all calls through Gemini Flash or Pro."""

    def __init__(self, settings_path: str | None = None):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        genai.configure(api_key=api_key)

        # Load settings
        if settings_path is None:
            settings_path = str(PROJECT_ROOT / "config" / "settings.yaml")
        with open(settings_path) as f:
            self._settings = yaml.safe_load(f)

        models_cfg = self._settings["models"]
        costs_cfg = self._settings["costs"]

        # Model names
        self._model_names = {
            "flash": models_cfg["generation"]["name"],
            "pro": models_cfg["evaluation"]["name"],
        }

        # Default temperatures
        self._temperatures = {
            "flash": models_cfg["generation"]["temperature"],
            "pro": models_cfg["evaluation"]["temperature"],
        }

        # Cost rates (per token, not per 1k)
        self._cost_rates = {
            "flash": {
                "input": costs_cfg["flash_input_per_1k"] / 1000,
                "output": costs_cfg["flash_output_per_1k"] / 1000,
            },
            "pro": {
                "input": costs_cfg["pro_input_per_1k"] / 1000,
                "output": costs_cfg["pro_output_per_1k"] / 1000,
            },
        }

        # Initialize model instances
        self._models = {
            "flash": genai.GenerativeModel(self._model_names["flash"]),
            "pro": genai.GenerativeModel(self._model_names["pro"]),
        }

        # Usage tracking
        self._usage_log: list[LLMUsage] = []

    def generate(
        self,
        prompt: str,
        model_type: str = "flash",
        temperature: float | None = None,
        call_type: str = "generation",
    ) -> tuple[str, LLMUsage]:
        """Generate text from a prompt. Returns (response_text, usage)."""
        if model_type not in self._models:
            raise ValueError(f"model_type must be 'flash' or 'pro', got '{model_type}'")

        model = self._models[model_type]
        temp = temperature if temperature is not None else self._temperatures[model_type]

        generation_config = genai.GenerationConfig(
            temperature=temp,
            response_mime_type="application/json",
        )

        start = time.time()
        response = model.generate_content(prompt, generation_config=generation_config)
        duration = time.time() - start

        # Extract token counts from usage metadata
        usage_metadata = response.usage_metadata
        input_tokens = usage_metadata.prompt_token_count or 0
        output_tokens = usage_metadata.candidates_token_count or 0

        # Compute cost
        rates = self._cost_rates[model_type]
        cost = (input_tokens * rates["input"]) + (output_tokens * rates["output"])

        usage = LLMUsage(
            model=self._model_names[model_type],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            call_type=call_type,
            duration_seconds=round(duration, 2),
        )
        self._usage_log.append(usage)

        # Rate limiting
        time.sleep(0.5)

        return response.text, usage

    def generate_structured(
        self,
        prompt: str,
        response_type: type[T],
        model_type: str = "flash",
        temperature: float | None = None,
        call_type: str = "generation",
    ) -> tuple[T, LLMUsage]:
        """Generate and parse into a Pydantic model. Retries once on parse failure."""
        for attempt in range(2):
            text, usage = self.generate(
                prompt=prompt,
                model_type=model_type,
                temperature=temperature,
                call_type=call_type,
            )
            try:
                data = json.loads(text)
                parsed = response_type.model_validate(data)
                return parsed, usage
            except (json.JSONDecodeError, Exception) as e:
                if attempt == 1:
                    raise ValueError(
                        f"Failed to parse LLM response into {response_type.__name__} "
                        f"after 2 attempts: {e}\nRaw response: {text[:500]}"
                    ) from e

        # Unreachable, but satisfies type checker
        raise RuntimeError("Unreachable")

    @property
    def total_cost(self) -> float:
        """Total cost of all LLM calls in USD."""
        return sum(u.cost_usd for u in self._usage_log)

    @property
    def usage_log(self) -> list[LLMUsage]:
        """All recorded LLM usage entries."""
        return list(self._usage_log)

    def reset_usage(self) -> None:
        """Clear the usage log."""
        self._usage_log.clear()
