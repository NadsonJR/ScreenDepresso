# Histórico de versões

Histórico consolidado das notas de versão e das seções cronológicas anteriormente presentes no README. Os detalhes arquivados preservam o texto documentado à época e podem descrever comportamentos depois substituídos. Para instalação e uso atuais, consulte o [README](README.md).

Os instaladores publicados ficam nas [Releases](https://github.com/NadsonJR/ScreenDepresso/releases).

## 0.7.5

- Layout da barra superior ajustado: os menus de **Tela inteira** e **Gravar** ficam na faixa inferior dos respectivos botões, com espaço separado para ícone, texto e seta.
- Corrigido o dimensionamento da faixa do menu: ela usa a largura real do botão, inclusive ao redimensionar, alternar layouts compacto/expandido, trocar de idioma ou iniciar/parar uma gravação.
- Clique no ícone continua executando a ação principal; clique na seta inferior abre as opções.
- Notas de atualização traduzidas e testes de geometria e interação em inglês/português. As funções de captura, gravação, desfoque e edição da 0.7.4 continuam disponíveis.

<details>
<summary>Detalhes da documentação original</summary>

### Barra superior (0.7.5)

Os botões **Full screen** e **Record** possuem uma faixa inferior para abrir suas opções. Clique no ícone para executar a ação principal; clique na seta inferior para abrir o menu. A faixa acompanha a largura real do botão, inclusive nos layouts compacto/expandido e ao trocar o idioma.

</details>

## 0.7.4

- Gravação de um monitor, janela ou região em MP4, pelo botão **Gravar**, bandeja ou atalho configurável (padrão **Ctrl+Alt+R**).
- Controles flutuantes para pausar/retomar, silenciar o microfone, parar e salvar ou descartar. Taxa de quadros, qualidade, contagem regressiva e microfone configuráveis.
- H.264 quando há codificador disponível, com fallback para MPEG-4. Áudio opcional do microfone; áudio do sistema não é capturado.
- Vídeos na workspace, com miniaturas, reprodução no player padrão e exclusão pela lixeira. O limite de imagens não exclui gravações.
- Preferências antigas preservadas ao adicionar o atalho de gravação, inclusive quando há conflito. Descartar uma gravação restaura o editor. O macOS solicita consentimento antes de abrir o microfone.
- Funções de desfoque e edição da 0.7.3 preservadas.
- Instaladores verificados com codificação e decodificação de um MP4 sintético, além dos testes existentes. Captura real e diálogos de permissão requerem validação em sessão gráfica.

Limitações: cada gravação acompanha um monitor; regiões que cruzam monitores são limitadas ao monitor escolhido. Janelas podem usar a captura de sua área como fallback. No Linux/X11, a barra aparece na gravação de tela inteira; quando uma região ocupa quase toda a tela, pode não haver espaço externo para os controles. A captura de tela do sistema e o microfone dependem das permissões e dispositivos disponíveis.

<details>
<summary>Detalhes da documentação original</summary>

### Validação dos pacotes de vídeo (0.7.4)

O teste `--smoke-test` de cada instalador codifica quadros sintéticos em MP4 com MPEG-4 e decodifica o arquivo usando os plugins Qt/FFmpeg incluídos. Ele não solicita acesso à tela nem ao microfone. Captura real de monitor/janela/região, áudio e consentimento do macOS continuam precisando de teste em sessão gráfica. O Actions também verifica pull requests destinados à `main`; a publicação continua exclusiva de tags.

</details>

## 0.7.3

- Nova opção **Desfocar dentro da seleção**, disponível na seta do botão de desfoque e nos controles de edição. O modo padrão **Desfocar fora da seleção** continua disponível.
- Cada área mantém sua direção: use Selecionar/mover para selecionar um efeito e alternar dentro/fora. A escolha também define a direção dos próximos efeitos desenhados.
- Compatível com intensidade ajustável, desfazer/refazer, recorte, abas, copiar e salvar em resolução original.
- Na camada única, áreas internas de desfoque somam-se ao fundo desfocado; se houver sobreposição, a região marcada para desfocar por dentro prevalece. Sobreposições não acumulam intensidade.
- Cache e cálculo em segundo plano da 0.7.2 preservados, inclusive ao alternar a direção. No modo sequencial, a ordem dos efeitos continua sendo respeitada.
- Interface e notas de atualização em inglês e português brasileiro.

<details>
<summary>Detalhes da documentação original</summary>

### Desfocar dentro ou fora da seleção (0.7.3)

Abra a seta do botão **Blur** e escolha **Blur inside selection** para desfocar somente a área desenhada, ou **Blur outside selection** para manter a área nítida e desfocar o restante. A direção também está nos controles de edição acima da imagem. A intensidade funciona nos dois modos.

Use **Select / move** para selecionar uma área existente e alterar sua direção; a escolha vale também para as próximas áreas desenhadas. As áreas permanecem editáveis, com desfazer/refazer, e cada aba mantém sua escolha. Na camada única, as regiões de desfoque interno se somam ao fundo desfocado e prevalecem sobre áreas nítidas sobrepostas, sem aumentar a intensidade na interseção. O modo sequencial mantém a ordem de composição. Copiar e salvar sempre usam a resolução original.

</details>

## 0.7.2

- Corrigido o gargalo que recalculava o desfoque da imagem inteira a cada repintura, movimento ou redimensionamento de uma área nítida.
- Camada de desfoque reutilizada por imagem/intensidade, com cache de memória compartilhado entre abas e orçamento de 256 MiB (uma camada maior pode ocupar o cache sozinha).
- Pintura direta da área visível, evitando copiar/renderizar o bitmap completo a cada quadro.
- Preparação da camada completa em segundo plano para imagens grandes, com prévia temporária leve e aviso no rodapé. A prévia exata substitui a temporária ao concluir.
- Copiar e salvar continuam usando a resolução original e o filtro Gaussiano anterior, sem exportar a prévia reduzida; se necessário, aguardam o cálculo completo. Renderizações duplicadas dessas ações foram removidas.
- Ordem de composição do modo legado, áreas nítidas sobrepostas, transparência, recorte e desfazer/refazer preservados e cobertos por testes.
- Benchmark reproduzível para 4K, 8K e 96 megapixels: [investigação de desempenho](https://github.com/NadsonJR/ScreenDepresso/blob/v0.7.2/docs/BLUR_PERFORMANCE.md). Tempos de desenho em cache não representam FPS completo do app; o primeiro cálculo continua proporcional ao tamanho da imagem.
- A 0.7.1 substitui os antigos instaladores da 0.7.0. A página antiga aponta para o novo download; a tag de código foi mantida no histórico.

<details>
<summary>Detalhes da documentação original</summary>

### Desfoque em imagens grandes (0.7.2)

O editor reutiliza a camada de desfoque enquanto você desenha, move ou redimensiona áreas nítidas. A tela pinta a área visível diretamente, evitando criar uma imagem completa a cada movimento. O cálculo de resolução completa é feito em segundo plano, com apenas um trabalhador e cancelamento de solicitações que ainda não iniciaram quando surge uma mais recente.

Enquanto o cálculo termina, uma prévia temporária de até 262 mil pixels mantém a edição disponível; as áreas nítidas e anotações continuam sendo desenhadas na resolução original. O rodapé mostra **Preparing full-resolution blur…**. A prévia temporária é substituída automaticamente pela camada exata. Não há novo popup ou ajuste obrigatório.

**Copiar e salvar sempre usam a resolução completa e o mesmo filtro Gaussiano anterior.** Se acionados antes do cálculo terminar, aguardam a camada completa; a prévia reduzida nunca é exportada. Copiar/salvar também evitam renderizar a mesma imagem várias vezes por operação.

O cache é compartilhado entre abas, com orçamento de 256 MiB; uma camada individual maior pode ocupar o cache sozinha. Assim ele não cresce a cada região ou valor de intensidade. Mudanças na imagem, recorte, intensidade e desfazer/refazer invalidam ou reutilizam a camada correta. O modo **Sequential blur (legacy)** mantém sua ordem original de composição e reutiliza o prefixo anterior à última camada; sequências longas ainda podem precisar de cálculos adicionais ao alterar objetos anteriores.

Veja [a investigação e os benchmarks reproduzíveis](docs/BLUR_PERFORMANCE.md). Os valores medem o renderizador em memória num ambiente Linux, não o FPS completo do aplicativo nem gravação de arquivos. Builds e testes funcionais também são executados no Windows e nas duas arquiteturas macOS.

</details>

## 0.7.1

- Nova identidade visual seguindo o guia: paleta escura, ícones consistentes, fonte de interface do sistema e controles de janela nativos.
- Barra superior agrupada, ferramentas laterais com rótulos e seleção azul com contraste reforçado.
- Barra contextual para as propriedades já existentes, sincronizada com a ferramenta, seleção, aba e desfazer/refazer. Menus laterais preservados.
- Estado vazio com captura, abertura, colagem e arraste de imagens.
- Layout compacto com ícones/overflow, rolagem de propriedades, tooltips traduzidos, atalhos nativos do macOS e suporte HiDPI/Retina.
- Sem alterações nos formatos de imagem, diretórios, configurações ou mecanismos de captura.

**Versão substituída:** os instaladores da 0.7.0 foram retirados a pedido do mantenedor. Use a [0.7.1](https://github.com/NadsonJR/ScreenDepresso/releases/tag/v0.7.1) ou uma versão mais recente. A tag de código antiga permanece no histórico.

<details>
<summary>Detalhes da documentação original</summary>

### Identidade visual (0.7.1)

A 0.7.1 aplica o guia de identidade visual: paleta escura, fonte de interface do sistema, ícones desenhados com traços consistentes, barra superior agrupada, ferramentas com rótulos, propriedades contextuais e rodapé legível. Botões e inputs têm foco visível. Os estados ativos usam uma variação mais escura do azul para manter contraste AA nos rótulos. O desenho dos controles nativos da janela é preservado em cada plataforma.

A barra contextual expõe apenas propriedades já suportadas pelas ferramentas atuais: cores e estilos de setas, espessura/cantos de retângulos, fonte/tamanho/cor do texto, modelos e cores de balões/marcadores e intensidade/modo do desfoque. Os menus dos próprios botões continuam disponíveis. Os exemplos de novas ferramentas e propriedades citados no mockup não adicionam novas operações ao mecanismo de edição nesta versão.

Sem imagem, o editor oferece **Capture screen**, **Open image** e **Paste image**, além de aceitar arraste. Abrir uma imagem não a move nem a duplica no Workspace. Em janelas compactas, as barras usam ícones com tooltips e o overflow nativo do Qt; a barra contextual admite rolagem horizontal. A interface respeita escalonamento HiDPI/Retina e usa símbolos nativos de atalhos no macOS.

#### Versão substituída

Os instaladores da 0.7.0 foram substituídos pela [0.7.1](https://github.com/NadsonJR/ScreenDepresso/releases/tag/v0.7.1), conforme solicitado. A página da 0.7.0 agora informa a substituição; sua tag de código foi preservada no histórico, sem renomear binários de outra versão.

</details>

## 0.7.0

- Aba Atualizações com a versão instalada centralizada e botões lado a lado, incluindo as notas da versão instalada.
- Seta, retângulo, texto, balões e desfoque permanecem ativos para criar vários objetos em sequência. Selecione **Selecionar/Mover** para ajustar objetos existentes.
- Confirmação/cancelamento de texto e desfazer/refazer preservam a ferramenta ativa.
- Primeiros instaladores nativos **macOS 15+**, separados para **Apple Silicon (arm64)** e **Intel (amd64)**, em formato DMG.
- Backend macOS com permissão de gravação de tela, descoberta e miniaturas de janelas, captura nativa de janela, atalhos globais Carbon e diretórios do perfil do usuário.
- Atualizador macOS seleciona e verifica o DMG correto. **Abrir instalador** abre a imagem de disco; encerre o app e substitua-o em Aplicativos antes de reabrir. A substituição pelo Finder é manual nesta versão.
- Apps macOS possuem assinatura ad hoc, sem notarização Apple. Na primeira abertura, pode ser necessário usar **Ajustes do Sistema → Privacidade e Segurança → Abrir Mesmo Assim** e conceder permissão de gravação de tela. Não é necessário compilar.
- Builds e testes automatizados em runners nativos Intel/Apple Silicon; capturas reais e permissões exigem validação em uma sessão de usuário no Mac.

<details>
<summary>Detalhes da documentação original</summary>

### Desenho contínuo e macOS (0.7.0)

Seta, retângulo, texto, balão e desfoque permanecem ativos após criar um objeto. Continue clicando/arrastando para adicionar outros, inclusive sobre objetos anteriores. Para mover, redimensionar ou reeditar texto com duplo clique, escolha **Select / move**. Texto é confirmado com Ctrl+Enter (Command+Enter no Mac), clique fora ou troca de ferramenta; Esc cancela apenas o texto atual. Desfazer/refazer preserva a ferramenta ativa. O comportamento dos marcadores numerados foi mantido.

Em **Settings → Updates**, a versão instalada fica centralizada e os botões ficam na mesma linha, incluindo **Release notes**.

#### macOS 15 ou posterior

Há instaladores DMG separados para **Apple Silicon (arm64)** e **Intel (amd64)** nas Releases. Baixe o pacote correspondente ao seu Mac, abra o DMG e arraste **ScreenDepresso.app** para **Applications/Aplicativos**. Não é necessário Python, pip, X11 ou compilar. O workflow usa runners macOS nativos em ambas as arquiteturas para executar os testes, montar os DMGs, copiar o app e verificar a abertura do pacote instalado.

Esta primeira versão usa assinatura ad hoc e **não é notarizada pela Apple**. O Gatekeeper pode exigir **Ajustes do Sistema → Privacidade e Segurança → Abrir Mesmo Assim** na primeira abertura. Distribuição assinada/notarizada exige certificado Developer ID e credenciais de notarização do proprietário. Nenhuma credencial Apple foi incluída no código.

Na primeira captura, permita o ScreenDepresso em **Ajustes do Sistema → Privacidade e Segurança → Gravação de Tela e Áudio do Sistema** (o nome pode variar conforme a versão/idioma do macOS) e reabra o app. Capturas não gravam áudio. Sem a permissão, o app mostra instruções, preservando a edição atual. Captura de tela inteira/região usa o desktop do Qt, inclusive Retina e múltiplos monitores; captura de janela usa o utilitário nativo `screencapture`, com miniaturas via Quartz. Conteúdo protegido pelo macOS pode não ser capturado.

Os atalhos globais usam Carbon, sem Xlib e sem monitorar todas as teclas. O padrão é **Command+Shift+1/2/3**, seguindo a convenção do Qt: `Ctrl` no formato de configuração corresponde a Command no Mac e `Meta` a Control. Teclas ausentes no Mac, como Print e F21–F35, são recusadas ao configurar. O ícone da bandeja fica na barra de menus. Configurações e capturas ficam em `~/Library/Application Support/ScreenDepresso`, respeitando diretórios personalizados.

O atualizador escolhe o DMG da arquitetura em execução e verifica origem, tamanho e SHA-256. Ao terminar, **Open installer** abre o DMG. Salve suas edições, encerre o app, substitua-o em Aplicativos e abra a nova versão. A substituição pelo Finder é manual nesta primeira versão; as configurações e o workspace são preservados.

Os testes automatizados do macOS não concedem permissão de gravação de tela: a validação real de capturas, atalhos físicos, múltiplos monitores e permissões deve ser feita numa sessão de usuário no Mac.

</details>

## 0.6.7

- Clique direito nas abas: **Fechar todas as abas**, **Fechar essa aba** e **Fechar outras abas**, atuando sobre a aba clicada mesmo quando ela não está ativa.
- Edições não salvas continuam oferecendo salvar, descartar ou cancelar. Cancelar interrompe o fechamento das abas restantes; fechar abas não exclui arquivos do workspace.
- Ações **Duplicar** e **Excluir** movidas para o menu de clique direito nas miniaturas do Workspace. Atalhos de teclado e arraste para o editor preservados.
- Atualização manual das miniaturas por um ícone de refresh sem botão retangular, no canto superior direito do Workspace.
- Botão **Notas de atualização** em **Configurações → Atualizações**, com notas da versão instalada na própria aba, disponíveis offline em inglês e português BR.

<details>
<summary>Detalhes da documentação original</summary>

### Menus de contexto e notas de atualização (0.6.7)

Clique com o botão direito em uma aba para **Close all tabs**, **Close this tab** ou **Close other tabs**. A ação usa a aba clicada, mesmo quando outra está ativa. Abas com edições não salvas mantêm as opções de salvar, descartar ou cancelar. Cancelar interrompe o fechamento das abas restantes; abas já fechadas continuam fechadas. Fechar todas retorna ao editor vazio, sem abas visíveis, preservando os arquivos no Workspace.

No **Workspace**, clique com o botão direito na miniatura para **Duplicate** ou **Delete**. Os três botões superiores foram substituídos por um ícone de atualização no canto superior direito. **Ctrl+D**, **Delete**, atualização automática e arraste para o editor continuam disponíveis. Excluir ainda move para a lixeira do sistema.

Em **Settings → Updates**, clique em **Release notes** para expandir as notas da versão instalada na própria aba. As notas acompanham o aplicativo, funcionam offline e seguem o idioma escolhido. Uma versão nova disponível não substitui essas notas pelas da versão ainda não instalada.

</details>

## 0.6.6

- Histórico substituído por **Workspace**, com miniaturas do diretório, atualização automática e ações de duplicar e excluir.
- Clique duplo abre uma imagem em uma aba; arrastar uma miniatura para o editor insere uma camada editável, com zoom e desfazer/refazer.
- Limite padrão de 25 imagens, configurável em **Settings → Files** para 25, 50, 75, 100 ou sem limite.
- Ao salvar imagens ou aplicar um novo limite, as imagens mais antigas são movidas para a lixeira do sistema. Arquivos em subpastas não são alterados e abas abertas preservam a edição.
- Revisão dos textos em inglês e português BR, incluindo menus, avisos, placeholders e formatação numérica.
- Catálogo brasileiro do Qt incluído nos instaladores para traduzir diálogos de arquivos e menus de contexto. Nomes de arquivos, fontes e textos do usuário são preservados.

<details>
<summary>Detalhes da documentação original</summary>

### Workspace e idiomas (0.6.6)

O painel **Workspace** substitui o histórico e mostra miniaturas das imagens no diretório configurado. Um clique seleciona a imagem para as ações; um clique duplo abre ou restaura sua aba. **Duplicate** (**Ctrl+D**) cria uma cópia independente no mesmo diretório; **Delete** move a imagem selecionada para a lixeira do sistema. Abas abertas preservam seus pixels e edições mesmo quando o arquivo original sai do workspace.

Arraste uma miniatura para a imagem em edição para adicioná-la como uma camada que pode ser movida, redimensionada e desfeita/refeita. O arraste copia a imagem, preservando o arquivo de origem. Também funciona com zoom e sobre a área vazia do editor. Miniaturas são carregadas em pequenos lotes; mudanças no diretório são observadas automaticamente e **Refresh** permite atualizar manualmente.

Em **Settings → Files**, escolha **25** (padrão), **50**, **75**, **100** ou **No limit**. O limite conta imagens PNG, JPEG, WebP, BMP, GIF e TIFF no próprio diretório, incluindo cópias e imagens externas com esses formatos. Ao salvar/duplicar uma imagem ou aplicar um novo limite/diretório, as mais antigas são movidas para a lixeira, mantendo o limite escolhido. A data de modificação define a ordem. Subpastas, arquivos de outros tipos e links simbólicos não são removidos automaticamente.

Diretórios existentes não são reduzidos apenas ao iniciar ou atualizar o aplicativo: se já excederem o limite, o painel informa que ele será aplicado no próximo salvamento. Para preservar todos os arquivos no diretório, selecione **No limit** antes de salvar novas imagens. Se a lixeira estiver indisponível, os arquivos são preservados e o painel informa que não foi possível aplicar o limite. Não há fallback para exclusão permanente.

A interface inclui traduções revisadas em inglês e português BR, com o catálogo brasileiro do Qt incluído nos instaladores para diálogos de arquivos e menus de contexto. Trocar o idioma atualiza os controles, status e placeholders sem traduzir nomes de arquivos, fontes nem o conteúdo escrito nas imagens. Quantidades decimais usam o formato do idioma selecionado. Mensagens externas do sistema operacional continuam sujeitas ao idioma do sistema.

</details>

## 0.6.5

- Fluxo de atualização incorporado à aba **Settings → Updates**, sem popups extras de consulta, confirmação ou reinício.
- Indicador de carregamento no lugar do botão durante a consulta; quando já está atualizado, o botão reaparece junto à mensagem de versão atual.
- Ao encontrar uma versão nova, exibe **Download and install** e **Keep current version** na própria aba.
- Download, progresso, erros, instalação e botão de reinício permanecem no mesmo painel.
- Fechar e reabrir as configurações preserva a operação e o estado da atualização.
- Aviso para salvar edições exibido junto ao reinício; a autorização de instalação do sistema permanece quando necessária.

<details>
<summary>Detalhes da documentação original</summary>

### Atualizações dentro das configurações (0.6.5)

Abra **Settings → Updates** e clique em **Check for updates**. Um indicador de carregamento ocupa o lugar do botão durante a consulta. Se não houver atualização, o botão volta e a mensagem informa que a versão instalada já é a mais recente.

Quando uma versão nova é encontrada, o painel mostra o número e o tamanho do pacote, com **Download and install** ou **Keep current version**. Manter a versão atual encerra a oferta e permite verificar novamente depois. Baixar e instalar inicia o download imediatamente, sem confirmação adicional.

Progresso, erros, instalação e **Restart application** aparecem na mesma aba. Salve suas edições antes de reiniciar; o aviso fica no próprio painel. O Ubuntu continua solicitando autorização do sistema para instalar o pacote, e o instalador Windows continua sendo iniciado no momento do reinício. As validações de origem, tamanho e SHA-256 e a proteção de instância única foram preservadas.

As configurações podem ser fechadas durante a operação. Ao reabrir a aba, o painel mantém o progresso ou o estado de pronto para reiniciar. O comando de atualização na bandeja abre essa mesma aba, sem uma segunda janela de atualização. As opções gerais de salvar/cancelar configurações são substituídas por **Close** enquanto a aba Updates estiver selecionada.

</details>

## 0.6.4

- Captura de tela inteira combina todos os monitores, incluindo telas à esquerda/acima da principal e monitores com escalas diferentes.
- Menu no botão **Full screen** para capturar todos os monitores ou apenas um monitor específico; o atalho global continua capturando todos.
- Seleção de janela por grade de miniaturas, com título, clique duplo e confirmação. A janela escolhida é trazida para a frente antes da captura.
- Seleção de região com uma sobreposição por monitor, cobrindo a geometria completa da tela, inclusive barras do sistema. Permite arrastar entre monitores e cancelar com Esc.
- Cantos suavemente arredondados nos botões e nos fundos dos ícones.

<details>
<summary>Detalhes da documentação original</summary>

### Vários monitores, miniaturas e seleção de região (0.6.4)

**Full screen** e o atalho global capturam a área completa dos monitores, respeitando suas posições, inclusive telas à esquerda ou acima da principal. Abra a seta do botão para escolher **All monitors** ou um monitor específico, identificado pelo nome e pela resolução. O menu é atualizado quando aberto; monitores desconectados são informados, sem retornar uma captura parcial silenciosamente.

Com escalas diferentes, a composição usa a maior densidade de pixels entre os monitores selecionados. Os demais são ajustados a essa escala comum para preservar o alinhamento com a seleção de região; espaços sem monitor ficam transparentes. Capturar um único monitor mantém sua resolução nativa. A validação automatizada cobre posições negativas, telas empilhadas, espaços entre telas e escala fracionária; ainda é recomendável conferir configurações físicas de escala mista no hardware de uso.

**Window** abre uma grade de miniaturas. Clique duas vezes ou escolha uma prévia e confirme em **Capture selected window**. As miniaturas usam a captura nativa da janela quando disponível, com fallback para a área visível do desktop. Janelas minimizadas não entram na seleção. A janela escolhida é ativada e sua posição é consultada novamente antes de capturar. Cancelar restaura o editor e preserva todas as abas.

**Region** abre uma sobreposição independente em cada monitor, usando a geometria completa em vez da área de trabalho reduzida pelas barras do sistema. No X11, a sobreposição ignora o reposicionamento do gerenciador de janelas, evitando que o GNOME desloque a imagem para cima do dock. A seleção pode atravessar monitores; **Esc** cancela e libera o mouse e o teclado.

</details>

## 0.6.3

- Espessura da borda de retângulos ajustável de 1 a 40 px no menu do botão lateral.
- Opção de cantos arredondados, com raio de 1 a 100 px; desmarque para voltar aos cantos retos.
- Seis modelos de marcador numerado: círculo clássico, círculo sólido, quadrado, losango, círculo com contorno e hexágono.
- Modelos no menu do próprio botão de marcadores, preservando a numeração sequencial, a cor global e o controle independente da ponta.
- Alterações de espessura, cantos e modelos aplicáveis a objetos existentes, com prévia durante o desenho e desfazer/refazer.
- Preferências de desenho e controles preservados por aba.

<details>
<summary>Detalhes da documentação original</summary>

### Retângulos e modelos de marcadores (0.6.3)

Abra o menu do botão **Rectangle** para escolher a cor, a **Border thickness** (1–40 px), ativar **Rounded corners** e ajustar o **Corner radius** (1–100 px). Desative a opção para desenhar cantos retos. Em retângulos pequenos, espessura e raio são limitados pelo tamanho da forma para evitar bordas cortadas. Os controles modificam o retângulo selecionado e definem o padrão dos próximos desenhos na mesma aba.

O menu de **Numbered markers** oferece seis modelos: **Classic circle**, **Flat circle**, **Square marker**, **Diamond marker**, **Outlined circle** e **Hexagon marker**. É possível misturar modelos na mesma imagem, mantendo uma única sequência de números. Escolher um modelo altera o marcador selecionado e o padrão dos próximos; a cor continua sendo comum a todos os marcadores da imagem. Centro, linha e ponta mantêm os controles de movimento existentes.

Todas as opções aparecem na prévia durante o desenho, funcionam com zoom e podem ser desfeitas/refeitas. Os menus acompanham o idioma escolhido nas configurações.

</details>

## 0.6.2

- Zoom pelo scroll do mouse, mantendo o ponto sob o cursor; Shift+scroll mantém a rolagem da imagem.
- Modelos de seta clássica, preenchida, dupla, tracejada e linha simples no menu do botão de seta, com cores e edição de objetos existentes.
- Botões e fundos dos ícones quadrados.
- Desfoque em uma camada compartilhada: todas as áreas selecionadas continuam nítidas e a intensidade é comum. O modo anterior continua disponível como **Sequential blur (legacy)** no menu do desfoque.
- Consulta de atualizações automática, sem botão durante a verificação ou quando já está na versão mais recente.
- Barra de progresso real no download, com validação de tamanho e SHA-256 preservada.
- Botão **Restart application** ao concluir: no Linux, reabre após a instalação; no Windows, instala e reabre a aplicação quando o usuário decide reiniciar.

<details>
<summary>Detalhes da documentação original</summary>

### Scroll, setas, camada de desfoque e atualizações (0.6.2)

- O **scroll do mouse** amplia/reduz a captura em passos de 10%, entre 10% e 400%, mantendo o ponto sob o cursor. Use **Shift+scroll** para rolar a imagem. O slider acompanha o valor e o zoom continua independente por aba.
- A seta do botão **Arrow** abre os modelos **Classic arrow**, **Filled arrow**, **Double arrow**, **Dashed arrow** e **Line**, além do seletor de cor. Selecionar um objeto existente permite mudar seu modelo e cor sem redesenhar.
- **Shared blur layer** é o padrão: a imagem é desfocada uma única vez, preservando a união de todas as áreas selecionadas; anotações ficam por cima e a intensidade vale para toda a camada. Para restaurar o comportamento anterior, escolha **Sequential blur (legacy)** no menu do desfoque. Esse modo aplica cada efeito em sequência, com intensidades individuais. A escolha é independente por aba, não exclui os objetos e pode ser desfeita. Os dois renderizadores ficam separados em `screendepresso/blur.py`.
- **Settings → Updates → Check for updates** consulta automaticamente ao abrir o popup, sem botão de consulta dentro dele. Se houver nova versão, aparece **Download and install**; durante o download, uma barra mostra o progresso em bytes. Tamanho, origem e SHA-256 continuam sendo verificados.
- Ao concluir, **Restart application** permite escolher quando reiniciar. No Ubuntu, o pacote é instalado mediante autorização do sistema antes de oferecer o reinício. No Windows, o download verificado fica pronto e o botão inicia a instalação e reabre o aplicativo. Salve as edições antes de reiniciar. A proteção de instância única aguarda o encerramento do processo anterior.

</details>

## 0.6.1

- Nenhuma aba visível quando não há imagens abertas.
- Balões de fala oval, arredondado, pensamento e grito, com modelos e cores de preenchimento/contorno no menu do botão lateral.
- Balões editáveis, incluindo controle independente da ponta, com desfazer/refazer.
- Ícone de colar em formato de prancheta.
- Slider de zoom de 10% a 400% no canto inferior esquerdo, independente por aba, sem alterar a resolução da exportação.
- Fonte, tamanho e cor do texto configuráveis no menu do botão de texto e em objetos existentes.
- Caixa de texto cresce automaticamente; se necessário, a área da imagem aumenta com transparência para evitar cortes. A expansão também pode ser desfeita.

<details>
<summary>Detalhes da documentação original</summary>

### Balões, texto e zoom (0.6.1)

- **Speech balloon**: arraste na imagem para desenhar um balão. A seta do próprio botão lateral abre os modelos **Speech**, **Rounded**, **Thought** e **Shout**, além das cores de preenchimento e contorno. Selecione o balão para alterar seu modelo ou cores; use os controles nos cantos para redimensionar e o controle da ponta para indicar outro objeto.
- **Text**: a seta do botão lateral permite escolher fonte, tamanho de **6 a 200 px** e cor. Os controles também alteram um texto selecionado. Arraste uma caixa e digite; **Ctrl+Enter** confirma, **Esc** cancela e um clique duplo permite editar novamente. A caixa cresce conforme o conteúdo; textos que excedem a imagem ampliam a tela com transparência, preservando todas as linhas e o tamanho escolhido. Essa expansão pode ser desfeita.
- **Zoom**: use o slider no canto inferior esquerdo para visualizar de **10% a 400%**. O zoom fica salvo por aba durante a sessão e não modifica a resolução das imagens copiadas ou exportadas. Desenho, seleção, recorte e texto usam as coordenadas originais mesmo com zoom.

Menus, dicas e controles estão disponíveis em inglês e português BR.

</details>

## 0.6.0

- Várias capturas abertas em abas, com edição, seleção, cores e desfazer/refazer independentes.
- Novas capturas abrem em outra aba sem substituir a edição atual.
- Abas podem ser reordenadas arrastando; Ctrl+Tab e Ctrl+Shift+Tab alternam entre capturas e Ctrl+W fecha a aba atual.
- Aviso para salvar, descartar ou cancelar ao fechar uma aba com alterações. Cancelar o salvamento mantém a aba aberta.
- Histórico abre capturas em abas e reutiliza a aba existente quando a imagem já está aberta.
- Salvar, copiar, colar, recortar e os controles de edição atuam na aba ativa.

<details>
<summary>Detalhes da documentação original</summary>

### Abas de capturas (0.6.0)

Cada print fica em uma aba, sem substituir a captura anterior. Alterne entre elas clicando no título ou usando **Ctrl+Tab** / **Ctrl+Shift+Tab**. Arraste as abas para reordenar.

Cada aba mantém seus objetos editáveis, seleção, intensidade de desfoque, cores, posição de rolagem e histórico de desfazer/refazer. Salvar, copiar, colar e os atalhos de edição atuam somente na aba ativa. Abrir uma captura já aberta pelo histórico seleciona a aba existente.

Um **asterisco** no título indica alterações não salvas. Use o botão de fechar na aba ou **Ctrl+W**; se houver alterações, escolha salvar, descartar ou cancelar. Quando não há imagens abertas, a barra de abas fica oculta, pronta para a próxima captura. Fechar uma aba não exclui imagens do histórico. As abas ficam na memória durante a sessão; ao encerrar o aplicativo, salve as edições que deseja manter.

</details>

## 0.5.2

- Pillow atualizado para 13.0.0, com correções de segurança.
- Instalações pelo código-fonte agora exigem Python 3.11 ou posterior, conforme o requisito do Pillow. Os instaladores continuam incluindo Python.

## 0.5.1

- Apenas uma instância do ScreenDepresso por perfil de usuário no Windows e Linux.
- Abrir o aplicativo novamente restaura a janela existente, inclusive quando estiver na bandeja, preservando a edição atual.
- Inicializações simultâneas não criam janelas ou atalhos duplicados.
- Recuperação automática da trava após encerramento forçado ou queda do processo.

<details>
<summary>Detalhes da documentação original</summary>

### Instância única (0.5.1)

O aplicativo permite apenas uma instância por perfil de usuário, tanto no Windows quanto no Linux. Ao abri-lo novamente pelo atalho ou instalador, a segunda abertura solicita que a primeira restaure o editor e termina sem criar outra janela ou registrar atalhos novamente. A imagem em edição é preservada, inclusive quando o aplicativo estava minimizado na bandeja.

A proteção usa uma trava no diretório das preferências e um canal local de ativação restrito ao usuário. A trava não expira enquanto o processo permanece vivo, mesmo após muito tempo minimizado. Encerrar libera a trava; depois de uma queda ou encerramento forçado, a próxima abertura recupera a trava e o canal abandonados automaticamente. Não é necessário excluir arquivos manualmente.

Se a primeira instância ainda estiver iniciando, a ativação será entregue quando ela estiver pronta. Se estiver em execução mas seu canal de ativação não responder, a segunda abertura apenas informa que o aplicativo já está aberto; ela não inicia uma instância adicional. O comando `--version` continua disponível sem abrir o editor.

</details>

## 0.5.0

- Suporte a Windows 10/11 x64: capturas, janelas, seleção de região, atalhos globais, bandeja e atualização pelo instalador.
- Instalador `.exe` por usuário, com atalhos no menu Iniciar e desinstalador; inclui o runtime Python.
- Versão do aplicativo sempre visível no rodapé.
- Release com instaladores Windows e Ubuntu, além de manifesto e checksums comuns.

### Windows

Baixe `screendepresso_*_windows_amd64_setup.exe`. Requer Windows 10 build 19041+ ou Windows 11 x64. O instalador não é assinado com Authenticode nesta versão; o SmartScreen pode exibir um aviso. Baixe somente a release oficial. Capturas e preferências ficam em `%LOCALAPPDATA%\ScreenDepresso` e são preservadas ao desinstalar ou atualizar.

Para atualizar, salve as edições e use Settings → Updates. O aplicativo fecha após iniciar o instalador verificado.

<details>
<summary>Detalhes da documentação original</summary>

### Windows e versão no rodapé (0.5.0)

A mesma aplicação agora possui backend Windows para capturar tela inteira, janela visível ou região, atalhos globais via RegisterHotKey, edição, histórico, área de transferência, bandeja e preferências. A versão atual fica sempre no canto inferior direito, mesmo quando a barra de status mostra outra mensagem.

#### Instalar no Windows

Baixe `screendepresso_0.7.5_windows_amd64_setup.exe` nas [Releases](https://github.com/NadsonJR/ScreenDepresso/releases). Execute o instalador e abra ScreenDepresso no menu Iniciar. Requer Windows 10 (build 19041 ou posterior) ou Windows 11, de 64 bits. Não é necessário instalar Python ou ferramentas de build.

A instalação é por usuário em `%LOCALAPPDATA%\Programs\ScreenDepresso`; capturas ficam por padrão em `%LOCALAPPDATA%\ScreenDepresso\captures` e as preferências em `%LOCALAPPDATA%\ScreenDepresso\settings.json`. O desinstalador preserva capturas e preferências. As variáveis XDG de testes continuam podendo sobrescrever esses diretórios.

Use **Settings → Updates** para atualizar. O atualizador seleciona o instalador Windows, verifica tamanho e SHA-256 e inicia o assistente de instalação. Salve suas edições antes de confirmar: a aplicação será encerrada para permitir substituir seus arquivos. O instalador oferece reabri-la ao terminar. O instalador baixado permanece temporariamente no diretório temporário do usuário.

Este primeiro instalador Windows não possui assinatura Authenticode. O Windows pode mostrar um aviso do SmartScreen; baixe somente os arquivos da release oficial. O SHA-256 verifica integridade em relação ao manifesto; não substitui uma assinatura do publicador.

#### Desenvolvimento e publicação

No Windows, use Python 3.12 e Inno Setup 6 no computador de build:

```powershell
uv sync --frozen --extra dev --extra build
uv run python packaging/build_windows.py
```

O workflow **Build installers** executa jobs independentes em Ubuntu 24.04 e Windows Server 2022. O Windows inclui testes das APIs nativas de atalhos, captura e enumeração de janelas; o job também instala silenciosamente o `.exe` gerado e executa o smoke test do aplicativo instalado. A publicação da tag depende do sucesso de ambos os jobs e valida os checksums antes de juntar os metadados em `update.json`.

Revisão manual recomendada no Windows real: capturar três modos, trocar atalhos, copiar/colar em outro aplicativo, minimizar/restaurar pela bandeja e atualizar pelo instalador. Capturas de janelas continuam incluindo o que está visível na tela; janelas minimizadas não são oferecidas. Monitores com escalas diferentes e janelas entre monitores exigem validação no hardware correspondente; a composição usa coordenadas lógicas do desktop Qt.

</details>

## 0.4.2

- Intensidade do desfoque integrada ao menu do próprio botão lateral.
- Recorte somente na barra superior; botão X lateral e barra de menus removidos. Delete continua excluindo objetos.
- Ao fechar a janela, escolha minimizar em segundo plano, encerrar ou cancelar.
- Ícone da bandeja com comandos para abrir, capturar, configurar, verificar atualizações e sair.
- Ao minimizar, os atalhos globais e a imagem em edição permanecem ativos.
- Sem suporte à bandeja no desktop, a janela fica minimizada na barra de tarefas para continuar acessível.

No GNOME, a bandeja usa a integração AppIndicator. As opções e mensagens estão disponíveis em inglês e português BR.

<details>
<summary>Detalhes da documentação original</summary>

### Interface simplificada e segundo plano (0.4.2)

- Abra a pequena seta do botão lateral **Blur outside selection** para ajustar **Blur strength** de 1 a 100. O controle continua alterando o efeito selecionado e a intensidade dos próximos efeitos; a seta principal do botão ativa a ferramenta.
- **Crop** fica somente na barra superior. O botão X lateral foi removido; **Delete** continua excluindo o objeto selecionado.
- A barra de menus Settings / Updates / About foi removida. As configurações permanecem no botão superior **Settings**, e as atualizações também estão disponíveis na aba **Updates** das configurações. O menu do ícone da bandeja inclui Settings, Check for updates e About.
- Ao fechar pelo X da janela, o aplicativo pergunta se deseja **Minimize to tray**, **Quit** ou **Cancel**. Minimizar preserva a imagem em edição e os atalhos globais de captura. Clique no ícone da bandeja ou use **Open** no menu dele para reabrir o editor. **Quit** no menu da bandeja encerra explicitamente o aplicativo e libera os atalhos.
- No GNOME, o ícone da bandeja depende do suporte a AppIndicator (normalmente já disponível no Ubuntu). Se não houver suporte, a opção muda para **Minimize to taskbar** e mantém a janela minimizada, com acesso pela barra de tarefas. O aplicativo não fica oculto sem um caminho para reabri-lo.

Se o Ubuntu/GNOME não mostrar ícones de bandeja, instale a extensão de integração pelo sistema e habilite-a nas Extensões do GNOME:

```bash
sudo apt install gnome-shell-extension-appindicator
```

Não é necessário configurar inicialização automática para continuar em segundo plano após minimizar; o processo atual permanece ativo até a opção de encerrar. A visibilidade real do ícone e o comportamento do painel devem ser conferidos no GNOME; os testes cloud exercitam as escolhas de fechar, restaurar, manter os serviços e o fallback sem bandeja.

</details>

## 0.4.1

- Seletores de cor integrados aos menus dos botões laterais de marcadores, retângulos e setas.
- Setas com cor personalizável para o objeto selecionado e as próximas setas, incluindo desfazer/refazer.
- Ícones atualizados: disquete para salvar, duas folhas para copiar e mão aberta para selecionar/mover.
- Controles de cor removidos da faixa superior, com indicação da cor nos próprios ícones laterais.

<details>
<summary>Detalhes da documentação original</summary>

### Menus de cor nas ferramentas laterais (0.4.1)

Os botões laterais de **Arrow**, **Rectangle** e **Numbered markers** têm dois controles: clique no ícone para selecionar a ferramenta; clique na pequena seta ao lado para abrir seu menu de cor. O próprio ícone exibe a cor atual.

- **Arrow color…** e **Rectangle color…** alteram o objeto selecionado do tipo correspondente e a cor dos próximos objetos desse tipo. Outros objetos existentes mantêm suas cores.
- **Marker color…** continua alterando todos os marcadores da imagem e os próximos marcadores.
- Mudar ou cancelar uma cor preserva a seleção; as alterações podem ser desfeitas e refeitas. Os menus e dicas acompanham o idioma escolhido.

A barra superior usa um disquete para **Save** e duas folhas sobrepostas para **Copy image**. A ferramenta **Select / move** usa uma mão aberta.

</details>

## 0.4.0

- Dicas ao passar o mouse nos botões e controles, com nomes e atalhos traduzidos.

- Marcadores circulares numerados automaticamente em sequência, com indicador e ponto de destino.
- Clique para inserir; arraste para apontar; use Selecionar para ajustar o círculo e a ponta separadamente.
- Seletor de cor para todos os marcadores, com contraste automático dos números.
- Seletor de cor para o retângulo selecionado e os próximos retângulos.
- Numeração sem lacunas após exclusão, com suporte a desfazer/refazer.
- Novos controles disponíveis em inglês e português BR.

<details>
<summary>Detalhes da documentação original</summary>

### Marcadores numerados e cores (0.4.0)

- Selecione **Numbered markers** (ícone **1**) na barra lateral. Clique para inserir o próximo número ou arraste do centro do círculo até o ponto que deseja indicar. A ferramenta continua ativa para inserir **1, 2, 3…** sem precisar selecioná-la a cada vez.
- Para ajustar um marcador existente, use **Select / move**: arraste o círculo para reposicioná-lo sem mudar o alvo; arraste a alça na ponta do indicador para apontar para outro objeto. Arrastar o segmento move o conjunto.
- **Marker color…** altera a cor de todos os marcadores da imagem e dos próximos marcadores. Os números usam contraste claro ou escuro automaticamente.
- Ao excluir um marcador, os restantes são renumerados sem lacunas. Desfazer/refazer restaura tanto a sequência quanto as mudanças de posição e cor. Uma nova imagem começa em 1.
- **Rectangle color…** altera o retângulo selecionado e define a cor dos próximos, sem mudar outros retângulos existentes. Se nenhum retângulo estiver selecionado, apenas a cor dos próximos é alterada.

Os controles também estão traduzidos em **Português (Brasil)**. Marcadores e retângulos permanecem objetos editáveis durante a sessão; copiar ou exportar inclui os números, indicadores e cores na imagem final.

#### Dicas ao passar o mouse

Mantenha o cursor sobre um botão ou controle para ver o nome da função. As dicas incluem atalhos quando disponíveis, como **Save (Ctrl+S)**, **Paste image (Ctrl+V)** e **Undo (Ctrl+Z)**. Estão disponíveis nas barras superior e lateral, no menu, nos controles de cor e desfoque e nas configurações. As dicas seguem o idioma escolhido em **Settings → Language**.

</details>

## 0.3.1

- Slider e campo numérico para intensidade do desfoque, de 1 a 100, com edição de efeitos existentes.
- Colar imagens como objetos sobre a imagem atual (Ctrl+V), com movimento, redimensionamento, transparência e desfazer/refazer.
- Interface em inglês por padrão; aba Language nas configurações permite alternar imediatamente entre English e Português (Brasil).

- Interface escura com ações no topo, ferramentas na lateral, imagem centralizada e histórico recolhível.
- Texto diretamente na imagem: arraste uma caixa, digite e confirme com Ctrl+Enter ou clique fora. Esc cancela.
- Duplo clique para reeditar o texto no mesmo local, com suporte a múltiplas linhas.
- Corrigida a prévia de texto incompleta que podia interromper a pintura e deixar a tela preta durante o popup.
- Copiar e salvar incluem o texto em edição, com desfazer/refazer após a confirmação.

<details>
<summary>Detalhes da documentação original</summary>

### Edição e configurações (0.3.1)

- **Ctrl+Z** desfaz; **Ctrl+Y** refaz. Uma nova edição após desfazer descarta o caminho de refazer.
- Após inserir uma anotação, o editor entra em **Selecionar**. Arraste o objeto para mover; arraste uma das duas alças para redimensionar ou ajustar as extremidades de uma seta. **Delete** exclui o objeto selecionado. Dê duplo clique no texto para editar seu conteúdo. O recorte preserva as anotações como objetos e também pode ser desfeito.
- A seta aparece como seta durante o arraste, inclusive na horizontal ou vertical.
- **Desfoque** preserva a região selecionada e desfoca o restante da imagem. Ajuste a intensidade de **1 a 100** no menu do próprio botão. No modo padrão, todas as áreas nítidas são combinadas e a intensidade vale para a camada inteira; o modo em sequência permanece disponível no mesmo menu.
- **Configurações → Hotkeys** permite alterar os três atalhos globais, inclusive usar Print. Atalhos duplicados ou ocupados são rejeitados; os anteriores são restaurados se o novo registro falhar. As alterações entram em vigor ao salvar.
- **Configurações → Arquivos** define o diretório das novas capturas, do histórico e o destino inicial de exportação. O padrão continua sendo `$XDG_DATA_HOME/screendepresso` ou `~/.local/share/screendepresso`. Arquivos antigos não são movidos; selecione o diretório anterior para vê-los novamente no histórico.
- **Configurações → Atualizações → Verificar atualizações** inicia a consulta de versões do GitHub.

As preferências ficam em `$XDG_CONFIG_HOME/screendepresso/settings.json` ou `~/.config/screendepresso/settings.json`. Anotações permanecem editáveis enquanto a imagem está aberta no editor. PNG/JPEG e o histórico de imagens são rasterizados; reabri-los não recupera as camadas de edição. Salve antes de trocar de imagem ou encerrar o aplicativo.

Os testes de atalhos globais usam um servidor X11 virtual isolado quando `Xvfb` está instalado (`sudo apt install xvfb`). Sem ele, esse teste é explicitamente marcado como ignorado; o workflow do Actions instala o servidor para executá-lo.

### Interface e texto direto na imagem (0.3.1)

A interface usa tons escuros, barra superior de ações, ferramentas na lateral esquerda e imagem centralizada. O botão **Histórico** abre ou recolhe a lista de capturas à direita. A ferramenta ativa fica destacada; a faixa acima da imagem mostra instruções de uso.

Para inserir texto, selecione **A**, arraste a caixa na imagem e digite nela. Um clique simples também cria uma caixa com tamanho inicial. Use **Ctrl+Enter** ou clique fora para confirmar; **Esc** cancela; Enter sozinho insere uma nova linha. O duplo clique sobre um texto existente abre a edição no próprio local. Use Selecionar para mover ou redimensionar a caixa. O texto usa tamanho de fonte estável de 24 px e quebra de linha dentro da caixa.

Não há popup de texto. A imagem permanece visível durante a edição, e copiar/salvar confirma o texto pendente antes de exportar. Confirmar uma anotação conta como uma operação de desfazer/refazer; uma caixa vazia ou cancelada não altera a imagem.

#### Colagem, desfoque e idiomas

- **Paste image / Ctrl+V** insere a imagem da área de transferência como uma camada sobre a imagem aberta. Ela pode ser movida, redimensionada, excluída e desfeita/refeita. Imagens grandes são ajustadas ao tamanho da tela de edição; a transparência é preservada. Sem uma imagem aberta, a colagem inicia uma nova imagem.
- O slider **Blur strength** e o campo numérico aceitam intensidades de **1 a 100**. Selecione o objeto de desfoque e ajuste o controle para modificar um efeito existente. O valor também define a intensidade do próximo efeito. A área selecionada continua nítida.
- A interface usa **English** por padrão. Em **Settings → Language**, escolha **English** ou **Português (Brasil)** e salve. Menus, ferramentas, configurações e mensagens mudam imediatamente; a preferência é mantida ao reabrir o aplicativo.

</details>

## 0.3.0

- Ctrl+Z para desfazer e Ctrl+Y para refazer.
- Configurações com abas de hotkeys, diretório de arquivos e verificação de atualizações.
- Prévia real de seta durante o arraste.
- Objetos editáveis: selecionar, mover, redimensionar, excluir e editar o texto por duplo clique.
- Desfoque fora da região selecionada, com intensidade ajustável de 1 a 100.

As anotações são editáveis durante a sessão de edição. Exportações e imagens reabertas do histórico são rasterizadas. Alterar o diretório não move capturas antigas.

### Instalação no Ubuntu 24.04 ou mais recente (x86_64 / X11)

Baixe o arquivo `screendepresso_*_amd64.deb` abaixo. Abra-o no instalador de aplicativos do Ubuntu ou execute:

```bash
sudo apt install ./screendepresso_*_amd64.deb
```

O pacote inclui Python e as dependências Python: não precisa de Python, pip nem build instalado no computador. Abra **ScreenDepresso** no menu de aplicativos.

Para novas versões, abra **Atualizações… → Verificar atualizações → Baixar e instalar**. O pacote é conferido com SHA-256 antes de ser entregue ao gerenciador de pacotes. O Ubuntu pede autorização de administrador. Feche e abra o aplicativo após atualizar; o histórico é preservado.

Inclui captura de tela, janela visível ou região, atalhos globais, editor com setas, texto, retângulos, desfoque, recorte e desfazer, histórico, copiar e exportar imagens.

Requer sessão X11; Wayland e ARM ainda não são suportados. Captura de janela não inclui conteúdo oculto por outras janelas.
