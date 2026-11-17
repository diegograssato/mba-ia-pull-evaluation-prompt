"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml

DICAS DE IMPLEMENTAÇÃO:

- O pull é feito pelo cliente do LangSmith:

      from langsmith import Client
      client = Client()
      prompt = client.pull_prompt(
          "leonanluppi/bug_to_user_story_v1",
          dangerously_pull_public_prompt=True,
      )

- O parâmetro `dangerously_pull_public_prompt=True` é obrigatório sempre que o
  identificador tem dono explícito ("owner/nome"). O LangSmith bloqueia esse pull
  por padrão porque um prompt do Hub é um objeto LangChain serializado, que pode
  vir de terceiros. Aqui o prompt é o do desafio, então o risco é conhecido.

- O retorno é um ChatPromptTemplate. Para extrair o conteúdo das mensagens,
  use a serialização nativa do LangChain (`prompt.messages`, e o atributo
  `.prompt.template` de cada mensagem).

- Use `save_yaml` de utils.py para gravar o resultado no arquivo .yml.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client

from utils import check_env_vars, print_section_header, save_yaml

load_dotenv()

SEED_PROMPT = "leonanluppi/bug_to_user_story_v1"
OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent / "prompts" / "bug_to_user_story_v1.yml"
)


def _message_template(message: object) -> str:
    """Extrai o template textual de uma mensagem LangChain serializada."""
    prompt = getattr(message, "prompt", None)
    template = getattr(prompt, "template", None)
    if not isinstance(template, str):
        raise TypeError(f"Mensagem sem template textual: {type(message).__name__}")
    return template


def pull_prompts_from_langsmith() -> Path:
    """Baixa o prompt semente e o serializa no formato YAML do laboratório."""
    prompt = Client().pull_prompt(
        SEED_PROMPT,
        dangerously_pull_public_prompt=True,
    )
    if len(prompt.messages) < 2:
        raise ValueError("O prompt remoto deve conter mensagens system e user.")

    data = {
        "bug_to_user_story_v1": {
            "description": "Prompt inicial obtido do LangSmith Prompt Hub",
            "system_prompt": _message_template(prompt.messages[0]),
            "user_prompt": _message_template(prompt.messages[1]),
            "version": "v1",
            "source": SEED_PROMPT,
            "tags": ["bug-analysis", "user-story", "baseline"],
        }
    }
    if not save_yaml(data, str(OUTPUT_FILE)):
        raise RuntimeError(f"Não foi possível salvar {OUTPUT_FILE}.")
    return OUTPUT_FILE


def main() -> int:
    """Executa o pull e informa o arquivo produzido."""
    print_section_header("PULL DO PROMPT INICIAL")
    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    try:
        output_file = pull_prompts_from_langsmith()
    # Fronteira da CLI: o SDK pode propagar diferentes erros HTTP/serialização.
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Erro ao fazer pull do prompt: {exc}")
        return 1

    print(f"✓ Prompt '{SEED_PROMPT}' salvo em {output_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
