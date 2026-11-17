"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

DICAS DE IMPLEMENTAÇÃO:

- O push é feito pelo cliente do LangSmith:

      from langsmith import Client
      from langchain_core.prompts import ChatPromptTemplate

      client = Client()
      prompt = ChatPromptTemplate.from_messages([
          ("system", system_prompt),
          ("user", user_prompt),
      ])
      url = client.push_prompt(
          f"{username}/bug_to_user_story_v2",
          object=prompt,
          is_public=True,
          description="...",
          tags=[...],
      )

- `username` vem de USERNAME_LANGSMITH_HUB no .env e precisa ser o seu handle
  do Hub. Se você ainda não tem um handle, veja as instruções no .env.example.

- A variável do template precisa ser {bug_report}, que é a chave de entrada
  usada no dataset de avaliação.

- Use `load_yaml` de utils.py para ler o arquivo .yml.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langsmith import Client

from utils import check_env_vars, load_yaml, print_section_header

load_dotenv()

PROMPTS_FILE = (
    Path(__file__).resolve().parent.parent / "prompts" / "bug_to_user_story_v2.yml"
)


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print(f"❌ Prompt '{prompt_name}' inválido:")
        for error in errors:
            print(f"   - {error}")
        return False

    username = os.getenv("USERNAME_LANGSMITH_HUB", "").strip().strip("/")
    prompt_identifier = f"{username}/{prompt_name}"
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_data["system_prompt"]),
            ("user", prompt_data["user_prompt"]),
        ]
    )

    client = Client()
    repository_metadata = {
        "is_public": True,
        "description": prompt_data["description"],
        "tags": prompt_data.get("tags", []),
    }

    try:
        url = client.push_prompt(
            prompt_identifier,
            object=prompt,
            **repository_metadata,
            commit_description=(
                f"Versão {prompt_data.get('version', 'v2')} otimizada com "
                + ", ".join(prompt_data.get("techniques_applied", []))
            ),
        )
    # Fronteira da API: o SDK pode propagar diferentes erros HTTP/autenticação.
    except Exception as exc:  # noqa: BLE001
        if "nothing to commit" not in str(exc).lower():
            print(f"❌ Erro ao publicar '{prompt_identifier}': {exc}")
            return False

        # O conteúdo já é o commit mais recente. Atualiza os metadados para que
        # reexecuções sejam idempotentes e não sejam reportadas como falha.
        url = client.push_prompt(prompt_identifier, **repository_metadata)
        print(f"✓ Prompt sem alterações: {prompt_identifier}")

    print(f"✓ Prompt publicado: {prompt_identifier}")
    print(f"✓ {url}")
    return True


def validate_prompt(prompt_data: dict) -> tuple[bool, list[str]]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors: list[str] = []
    required_fields = (
        "description",
        "system_prompt",
        "user_prompt",
        "version",
        "techniques_applied",
    )
    for field in required_fields:
        if not prompt_data.get(field):
            errors.append(f"Campo obrigatório ausente ou vazio: {field}")

    system_prompt = prompt_data.get("system_prompt", "")
    user_prompt = prompt_data.get("user_prompt", "")
    if "{bug_report}" not in user_prompt:
        errors.append("user_prompt deve conter a variável {bug_report}")
    if "TODO" in system_prompt or "TODO" in user_prompt:
        errors.append("O prompt ainda contém TODO")
    if len(prompt_data.get("techniques_applied", [])) < 2:
        errors.append("Informe pelo menos duas técnicas em techniques_applied")

    try:
        template = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("user", user_prompt)]
        )
        if set(template.input_variables) != {"bug_report"}:
            errors.append(
                "O template deve possuir somente a variável {bug_report}; "
                f"encontradas: {template.input_variables}"
            )
    except (TypeError, ValueError) as exc:
        errors.append(f"Template LangChain inválido: {exc}")

    return not errors, errors


def main() -> int:
    """Valida e publica todos os prompts otimizados."""
    print_section_header("PUSH DOS PROMPTS OTIMIZADOS")
    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    prompts = load_yaml(str(PROMPTS_FILE))
    if not prompts:
        return 1

    success = True
    for prompt_name, prompt_data in prompts.items():
        success = push_prompt_to_langsmith(prompt_name, prompt_data) and success
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
