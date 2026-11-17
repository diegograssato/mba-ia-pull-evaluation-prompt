"""
Testes automatizados para validação de prompts.
"""

import sys
from pathlib import Path

import pytest
import yaml

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"


def load_prompts(file_path: Path) -> dict:
    """Carrega prompts do arquivo YAML."""
    with file_path.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


@pytest.fixture
def prompt() -> dict:
    """Disponibiliza o prompt v2 validado pelo schema YAML básico."""
    return load_prompts(PROMPT_FILE)["bug_to_user_story_v2"]


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt: dict):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert prompt.get("system_prompt", "").strip()

    def test_prompt_has_role_definition(self, prompt: dict):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        assert "você é um product manager" in prompt["system_prompt"].lower()

    def test_prompt_mentions_format(self, prompt: dict):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        system_prompt = prompt["system_prompt"].lower()
        assert "markdown" in system_prompt
        assert "como um [persona]" in system_prompt

    def test_prompt_has_few_shot_examples(self, prompt: dict):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        system_prompt = prompt["system_prompt"].lower()
        assert "exemplo 1" in system_prompt
        assert "exemplo 2" in system_prompt
        assert "entrada:" in system_prompt
        assert "saída:" in system_prompt

    def test_prompt_no_todos(self, prompt: dict):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        serialized = yaml.safe_dump(prompt, allow_unicode=True)
        assert "TODO" not in serialized
        valid, errors = validate_prompt_structure(prompt)
        assert valid, errors

    def test_minimum_techniques(self, prompt: dict):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt.get("techniques_applied", [])
        assert len(techniques) >= 2
        assert any("few-shot" in technique.lower() for technique in techniques)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
