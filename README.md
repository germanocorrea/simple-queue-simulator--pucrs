# Rede de filas: atendimento de incidentes de TI

Trabalho T2 de Simulação e Métodos Analíticos (PUCRS). Modela o atendimento de chamados de TI como uma rede de filas com retorno, a partir de um log real do ServiceNow ([Incident Management Process Enriched Event Log](https://archive.ics.uci.edu/dataset/498/incident+management+process+enriched+event+log), UCI), simula a rede e compara o modelo atual com um modelo melhorado.

Video da apresentação: [https://youtu.be/XfX66la6c9s](https://youtu.be/XfX66la6c9s)

## Modelo

4 filas, tempo em minutos úteis (8h–18h, dias úteis, abr–mai/2016), capacidade infinita:

| Fila | Grupo real | Kendall |
|---|---|---|
| N1 | Group 70 (1º nível) | G/G/358 |
| N2a | Group 20 | G/G/151 |
| N2b | Group 39 | G/G/88 |
| OUTROS | 75 grupos agregados | G/G/1212 |

Os chamados vão do N1 para os especialistas e voltam (ex.: 33,7% do que sai do N2a retorna ao N1).

## Resultado

- **Gargalo:** OUTROS (U = 0,98; servidores todos ocupados 55% do tempo).
- **Melhoria** (`modelos/melhorado.yml`): N1 encaminha menos para OUTROS (0,19 → 0,10) e OUTROS ganha vagas (1212 → 1300). A espera em OUTROS zera (W 3.175 → 3.090 min) e U cai para 0,81.

## Estrutura

- `simulator.py`: simulador de redes de filas.
- `modelos/`: `base.yml` (atual), `melhorado.yml` e as melhorias isoladas (`melhoria_*.yml`).
- `tratamento.ipynb`: extrai os parâmetros do log e calcula os índices (N, D, U, W).
- `resultados/`: saídas das simulações e índices em CSV.

## Como rodar

```sh
./simulator.py modelos/base.yml
./simulator.py modelos/melhorado.yml
```
