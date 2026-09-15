# Avaliar antes de prometer

Este diretório fornece o protocolo e o formato. **Não contém um golden dataset
real, nem resultados de precisão do Gemini.** O manifest é um exemplo de anotação;
seu screenshot não existe. Não interprete testes do cálculo como qualidade do modelo.

## Construir o gabarito

1. Reúna 30–50 screenshots reais, consentidos e sanitizados, em `evals/private/images/`.
   Remova nomes, chaves, conversas e dados privados antes de enviar para a API.
2. Dois revisores anotam cada imagem com seu comando, sem ver respostas do Gemini.
   Resolva divergências e registre a versão da rubrica. Separe desenvolvimento e
   holdout por aplicativo/cenário, evitando capturas quase idênticas nos dois grupos.
3. Copie `manifest.example.json` para `evals/private/holdout.json`. Use todas as
   quatro chaves `expected` em cada caso. Balanceie as classes quando viável;
   publique contagens por classe e não apenas uma média.
4. `unknown` / `indeterminada` / `nenhuma` são respostas válidas e pontuadas.
   `null` significa que os revisores não têm gabarito confiável: exclui somente
   aquele campo e aparece no denominador de exclusões. Não use null para esconder erros.
5. OS exige sinais visuais; uma página web recortada não identifica seu sistema.
   Frontend/Backend descrevem o componente **sustentado pela evidência**, não uma
   causa presumida. Um erro 500 em uma interface não prova sozinho a causa técnica.
   Prioridade é sugestão com base no contexto, não prioridade operacional aplicada.

## Rodar no mesmo ambiente Python do agente

```sh
python -m pip install -e '.[test]'
# Ambiente local: GEMINI_API_KEY e GEMINI_MODEL já exportados com segurança.
# --live envia screenshots/texto à API paga; não chama Linear nem Plow.
python -m omni.evaluation --manifest evals/private/holdout.json \
  --live --output evals/private/run-001.json
```

O avaliador reutiliza `Gemini.analyze`, incluindo compressão, prompt, schema,
retry e filtragem de labels. Execução sequencial, timeout e até três tentativas
por caso. Conta uso localmente; este harness não encaminha métricas ao Agent Index
nem usa o volume de produção. Não inclua as chamadas de avaliação na pontuação do agente.
Não carrega `omni.env` automaticamente; não exponha chaves nos comandos.

Para verificar previsões já obtidas, um JSON deve mapear **cada ID** aos quatro
campos previstos (ou `{"error":"unavailable"}`). Sem texto bruto do modelo:

```sh
python -m omni.evaluation --manifest evals/private/holdout.json \
  --predictions evals/private/predictions.json --output evals/private/offline-001.json
pytest -q tests/test_evaluation.py
```

## Interpretar

Relatório JSON privado (0600), nunca sobrescrito: acurácia, precisão/recall/F1
macro sobre taxonomia fixa, F1 macro apenas das classes com suporte, F1 ponderado,
por classe e matriz de confusão (linhas=gabarito, colunas=previsão). Classes sem
suporte são explícitas; divisões por zero produzem 0, conjunto vazio produz null.
Erros de API são relatados à parte, **reduzem cobertura e acurácia ponta a ponta**;
não são ocultados por uma média das respostas bem-sucedidas. O processo sai com
código 2 quando há falhas. Taxa de abstenção é separada de correção da abstenção.

Hashes do manifest, imagens, cliente/prompt e schema identificam a execução.
O modelo, tokens e latência são registrados no modo live. Nenhum ticket é criado.
AUC-ROC não é calculada porque não há escores contínuos calibrados por classe.
Não invente probabilidades a partir da confiança declarada por um LLM.

30–50 exemplos fornecem evidência inicial, não prova matemática de generalização.
Mantenha o holdout fora das iterações do prompt; rode versões comparáveis, examine
os erros e repita medições quando necessário. O avaliador não mede alucinações
na descrição, fidelidade de OCR, qualidade de labels ou segurança contra injeção;
esses itens exigem rubricas/revisões próprias. Não anuncia um critério arbitrário
como “F1 > 0,9 = produção”.

Referência das definições: [scikit-learn — classification metrics](https://scikit-learn.org/stable/modules/model_evaluation.html#classification-metrics).
