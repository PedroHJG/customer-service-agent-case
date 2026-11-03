"""
Ferramentas do agente: schema (o que o Claude vê) + executor (o que o backend roda).

Os nomes precisam bater com TOOL_LABELS do frontend (frontend/src/lib/constants.ts),
que define o texto do badge "Consultando..." exibido durante a chamada.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.services import store_repository, vector_store


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Mesmos nomes da tabela categories (data/... - categories.csv); enum impede o modelo de inventar categoria
Categoria = Literal[
    "Guitarras",
    "Baixos",
    "Baterias e Percussão",
    "Teclados e Pianos",
    "Violões",
    "Instrumentos de Sopro (Madeiras)",
    "Instrumentos de Sopro (Metais)",
    "Cordas Orquestrais",
    "Ukuleles",
]


class BuscarProdutosInput(ToolInput):
    termo: str | None = Field(
        None,
        description="Marca, modelo ou característica, sem o tipo do instrumento. "
        "Ex.: 'Takamine GD20', 'nylon', 'elétrico', '7 cordas', 'iniciante'",
    )
    categoria: Categoria | None = Field(None, description="Tipo do instrumento")
    preco_maximo: float | None = Field(None, description="Preço máximo em reais (considera promoções)")
    apenas_disponiveis: bool = Field(
        True, description="true: só produtos à venda com estoque. Use false para checar um modelo específico"
    )


class ConsultarPedidoInput(ToolInput):
    numero_pedido: str = Field(description="Número do pedido informado pelo cliente")
    email_ou_telefone: str = Field(description="E-mail ou telefone do cadastro, para confirmar a identidade")


class ConsultarPoliticasInput(ToolInput):
    pergunta: str = Field(description="Dúvida do cliente reescrita como busca. Ex.: 'prazo para devolução por arrependimento'")


class ListarPromocoesInput(ToolInput):
    pass


class ForaDeEscopoInput(ToolInput):
    motivo: str = Field(description="Resumo curto do assunto fora do escopo. Ex.: 'receita culinária'")


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_model: type[ToolInput]
    handler: Callable[[Any], Awaitable[Any]]
    # Tools silenciosas não geram badge de "consultando" na UI (ex.: guardrail)
    silent: bool = False

    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
            "eager_input_streaming": True,
        }


async def _buscar_produtos(args: BuscarProdutosInput) -> Any:
    produtos = await store_repository.search_products(
        args.termo, args.categoria, args.preco_maximo, args.apenas_disponiveis
    )
    return {"produtos": produtos} if produtos else {"produtos": [], "aviso": "Nenhum produto encontrado"}


async def _consultar_pedido(args: ConsultarPedidoInput) -> Any:
    pedido = await store_repository.get_order_status(args.numero_pedido, args.email_ou_telefone)
    # Mesma resposta para "não existe" e "não é seu": não revela a existência de pedidos de terceiros
    return pedido or {"erro": "Pedido não encontrado para esse número e identificação"}


async def _consultar_politicas(args: ConsultarPoliticasInput) -> Any:
    return {"trechos": await vector_store.search_policies(args.pergunta)}


async def _listar_promocoes(_: ListarPromocoesInput) -> Any:
    return {"promocoes": await store_repository.list_active_promotions()}


async def _fora_de_escopo(args: ForaDeEscopoInput) -> Any:
    return {"registrado": True, "motivo": args.motivo}


TOOLS: dict[str, Tool] = {
    tool.name: tool
    for tool in [
        Tool(
            "buscar_produtos",
            "Busca produtos no catálogo com preço e estoque atuais. Use para qualquer pergunta sobre "
            "preço, disponibilidade ou opções de instrumentos e acessórios.",
            BuscarProdutosInput,
            _buscar_produtos,
        ),
        Tool(
            "consultar_pedido",
            "Consulta status, itens, pagamento, rastreio e prazos de um pedido. Exige o número do pedido e "
            "o e-mail ou telefone do cadastro; peça os dois ao cliente antes de chamar.",
            ConsultarPedidoInput,
            _consultar_pedido,
        ),
        Tool(
            "consultar_politicas",
            "Busca trechos do manual de políticas da loja: trocas, devoluções, garantia, pagamento, "
            "entrega, horários, endereço e contato.",
            ConsultarPoliticasInput,
            _consultar_politicas,
        ),
        Tool(
            "listar_promocoes",
            "Lista as promoções vigentes da loja.",
            ListarPromocoesInput,
            _listar_promocoes,
        ),
        Tool(
            "registrar_fora_de_escopo",
            "Registra que a mensagem do cliente foge do escopo da loja. Chame antes de recusar educadamente.",
            ForaDeEscopoInput,
            _fora_de_escopo,
            silent=True,
        ),
    ]
}

TOOL_DEFINITIONS = [tool.definition() for tool in TOOLS.values()]


class ToolExecutionError(Exception):
    pass


async def execute_tool(name: str, raw_input: Any) -> Any:
    tool = TOOLS.get(name)
    if tool is None:
        raise ToolExecutionError(f"Ferramenta desconhecida: {name}")
    try:
        # Com eager_input_streaming a API não valida o input: validamos aqui
        args = tool.input_model.model_validate(raw_input)
    except ValidationError as exc:
        raise ToolExecutionError(f"Parâmetros inválidos: {exc.errors(include_url=False)}") from exc
    return await tool.handler(args)
