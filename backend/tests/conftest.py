import os

# Os testes não chamam a API; a chave só precisa existir para o Settings carregar
os.environ.setdefault("ANTHROPIC_API_KEY", "test")
