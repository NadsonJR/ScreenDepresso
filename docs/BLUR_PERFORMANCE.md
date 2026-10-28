# Investigação de desempenho do desfoque — 0.7.2

## Causa

Na 0.7.1, cada `Canvas.paintEvent` chamava `render_image(True)`: copiava o bitmap inteiro, convertia os canais para o Pillow, executava o filtro Gaussiano em resolução completa, restaurava as áreas nítidas e compunha as anotações. Expor a janela, arrastar ou redimensionar uma área repetia esse trabalho, mesmo sem mudar a imagem original ou a intensidade.

O perfil de uma imagem 8K atribuiu aproximadamente 1,43 s de 2,11 s ao filtro Gaussiano em uma única renderização; conversões e cópias adicionavam o restante. Portanto, diminuir apenas o tamanho da janela ou o zoom não eliminava o gargalo.

## Correção

- Cache por identidade/revisão do QImage e intensidade, compartilhado entre abas. Alterar somente os retângulos de áreas nítidas não exige outro filtro.
- Pintura direta da área visível, com recortes disjuntos para o fundo desfocado e a união das áreas nítidas. Isso evita cópias completas e aplicação duplicada de transparência a cada quadro.
- Para imagens acima de 2 megapixels, o cálculo exato roda em um trabalhador; enquanto isso, há uma prévia temporária de até 262.144 pixels. As áreas nítidas e anotações continuam na resolução original. Ao concluir, o resultado exato substitui a prévia.
- Uma tarefa em execução e apenas a solicitação pendente mais recente, evitando acumular filtros ao mudar rapidamente a intensidade ou a aba. Resultados antigos não substituem os atuais.
- Cache com orçamento de 256 MiB. Se uma única camada exceder o orçamento, ela ocupa o cache sozinha. Futures concluídas não mantêm cópias extras presas em cada aba. O prefixo de composição do modo legado é descartado ao ocultar a aba.
- Remoção de cópias de buffer desnecessárias na conversão Qt/Pillow. Copiar/salvar obtêm a imagem final uma única vez por operação.
- A exportação usa sempre a resolução completa e o mesmo Gaussiano da 0.7.1. Se o cálculo estiver em andamento, salvar/copiar aguardam a camada exata, sem recalculá-la em paralelo. A prévia reduzida nunca é usada como arquivo final ou conteúdo da área de transferência.

## Medições

Linux x86_64, Python 3.12, Pillow e Qt das dependências travadas, execução offscreen. Imagens sintéticas de faixas coloridas, raio 14, janela de desenho em memória de 1280×720 e zoom 100%. Cada resolução roda em processo novo; arraste é a mediana de três quadros após a camada completa ficar pronta. A primeira pintura nova usa a prévia temporária. A memória é o pico do processo completo, incluindo a exportação.

| Resolução | Arraste 0.7.1 | Arraste 0.7.2, cache pronto | Primeira pintura 0.7.2 | Camada exata pronta | Pico de memória |
|---|---:|---:|---:|---:|---:|
| 3840x2160 | 401.7 ms | 1.45 ms | 33.0 ms | 0.43 s | 267 → 208 MiB |
| 7680x4320 | 1986.9 ms | 1.06 ms | 79.2 ms | 1.61 s | 932 → 683 MiB |
| 12000x8000 | 5707.7 ms | 1.98 ms | 183.2 ms | 4.72 s | 2610 → 1882 MiB |

O modo legado foi medido separadamente em 8K, com uma camada e uma região em arraste: **3664.2 ms → 2.95 ms** por quadro após o cache ficar pronto. Alterar um objeto anterior a várias camadas legadas pode exigir recompor os prefixos; o modo compartilhado oferece o caso de reutilização mais simples.

Estes números medem o renderizador de edição em memória. Não são FPS de monitor, latência completa de mouse/Qt, tempo de captura, codificação de PNG/JPEG ou escrita em disco. São amostras de um ambiente compartilhado, sem promessa de tempos iguais em outro computador. O primeiro cálculo Gaussiano continua proporcional à resolução e pode levar vários segundos; a diferença é que a edição não o repete a cada movimento, e o trabalho completo fica em segundo plano. Exportar antes de ele terminar ainda pode aguardar o cálculo. A prévia temporária não tem a mesma definição da camada final.

## Reproduzir

```bash
uv run --frozen python packaging/benchmark_blur.py
uv run --frozen python packaging/benchmark_blur.py --mode sequential --sizes 7680x4320
```

Para comparar com a 0.7.1 sem alterar seu checkout atual:

```bash
mkdir -p /tmp/screendepresso-071
git archive v0.7.1 screendepresso | tar -x -C /tmp/screendepresso-071
uv run --frozen python packaging/benchmark_blur.py --source /tmp/screendepresso-071
```

A medição não lê capturas do usuário. Os resultados registrados estão em [benchmarks/blur-072.json](benchmarks/blur-072.json).

## Verificação funcional

Os testes comparam a exportação com uma implementação independente do renderizador da 0.7.1, pixel a pixel: áreas sobrepostas, bordas fora da imagem, transparência, anotações e modo legado. Também verificam invalidação por imagem/raio/recorte, desfazer/refazer, orçamento do cache, descarte de resultados antigos, fechamento da aba durante o cálculo e ausência de filtros repetidos ao mover regiões. Não há limites de tempo frágeis nos testes automatizados.

O smoke test dos instaladores exercita uma imagem acima do limiar assíncrono para validar Pillow, buffers Qt e o trabalhador nos pacotes Linux, Windows e macOS Intel/Apple Silicon. As medidas de desempenho acima foram feitas em Linux; os outros sistemas recebem validação funcional, não uma afirmação de desempenho idêntico.
