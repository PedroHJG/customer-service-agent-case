# Perguntas fora do escopo, circuit breaker e retomada do atendimento

> Relógio simulado: `REFERENCE_DATETIME=2026-03-25T10:00`
> Configuração do teste: `OUT_OF_SCOPE_THRESHOLD=2`
> Conversa gerada pelo agente real (Claude Opus 5.5) e transcrita sem edição.

**Cliente:** Me passa uma receita de bolo de cenoura?

> 🛡️ guardrail: receita culinária (bolo de cenoura)

**Lia:** Oi! Aqui é a Lia, da Empório da Música. Bolo de cenoura é ótimo, mas receita não é comigo 😅 Só consigo ajudar com assuntos da loja.  
  
Se estiver procurando um instrumento, quiser saber das promoções ou acompanhar um pedido, é só falar!

**Cliente:** Quem ganhou a copa de 2002?

> 🛡️ guardrail: futebol / Copa do Mundo 2002

**Lia:** Futebol também foge do que eu posso responder por aqui, foi mal! Eu só ajudo com assuntos da Empório da Música.  
  
Se quiser, posso te mostrar opções de instrumentos, as promoções da semana ou ver como está um pedido seu. Como posso te ajudar?

**Cliente:** Qual a capital da França?

> 🛡️ guardrail: atendimento automático pausado após várias mensagens fora do escopo

**Lia:** Por aqui eu só consigo ajudar com assuntos da Empório da Música: instrumentos, preços, estoque, pedidos, trocas, pagamento e entrega. Quando quiser falar sobre algum desses, é só mandar! 🎵

**Cliente:** Tá bom kkk. Vocês têm ukulele?

> 🔧 `buscar_produtos` {"categoria": "Ukuleles"}

**Lia:** Temos sim, e bastante opção! 🎶 Separei alguns:  
  
Soprano (o menor, ótimo pra começar):  
• Shelby SU-21S Sunburst: R$ 159,90 (R$ 151,91 no PIX ou 3x de R$ 53,30)  
• Kalani KAL-300S Natural: R$ 179,90 (R$ 170,91 no PIX ou 3x de R$ 59,97)  
• Kala KA-15S Mogno: R$ 199,90 (R$ 189,91 no PIX ou 3x de R$ 66,63)  
• Ohana SK-10 Natural: R$ 249,90 (R$ 237,41 no PIX ou 3x de R$ 83,30)  
  
Concert (um pouco maior, mais volume):  
• Kala KA-C Mogno: R$ 349,90 (R$ 332,41 no PIX ou 4x de R$ 87,48)  
• Ohana CK-20 (tampo sólido): de R$ 549,00 por R$ 439,20, 20% off (5x de R$ 87,84)  
• Kalani KAL-500C Elétrico: R$ 479,00 (R$ 455,05 no PIX ou 5x de R$ 95,80)  
  
Tenor e barítono (mais graves):  
• Kalani KAL-700T Tenor: de R$ 359,00 por R$ 323,10, 10% off (4x de R$ 80,78)  
• Kala KA-T Tenor: R$ 449,90 (R$ 427,41 no PIX ou 5x de R$ 89,98)  
• Kala KA-B Barítono: R$ 599,00 (R$ 569,05 no PIX ou 6x de R$ 99,83)  
  
Nos que estão em promoção, o desconto do PIX não soma com o da oferta.  
  
O ukulele é pra você começar a tocar ou você já toca? Me conta que eu te ajudo a escolher o melhor.

<details><summary>Estado do circuit breaker após cada mensagem</summary>

1. `streak=1 breaker_open=False`
2. `streak=2 breaker_open=True`
3. `streak=2 breaker_open=True`
4. `streak=0 breaker_open=False`

</details>
