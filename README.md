# ScreenDepresso

Aplicativo de captura de tela, edição de imagens e gravação de vídeo para **Ubuntu/GNOME em X11, Windows e macOS**. Os instaladores incluem Python e as dependências da aplicação: não é necessário compilar para usar.

[Baixar instaladores](https://github.com/NadsonJR/ScreenDepresso/releases/latest) · [Histórico de versões](CHANGELOG.md) · [Desenvolvimento e publicação](docs/DEVELOPMENT.md)

## Principais funcionalidades

- Captura de todos os monitores, de um monitor específico, de janela por miniatura ou de região.
- Atalhos globais configuráveis e várias imagens abertas em abas independentes.
- Editor com setas, linhas, retângulos, texto, balões, marcadores numerados, desfoque dentro/fora da seleção e recorte.
- Objetos editáveis, cores e estilos, desfazer/refazer, zoom e colagem de imagens como camadas.
- Workspace com miniaturas, cópia de imagens, exclusão pela lixeira e limite de imagens configurável.
- Gravação em MP4 de monitor, janela ou região, com pausa, contagem regressiva e áudio opcional do microfone.
- Cópia de imagens para outros aplicativos, exportação PNG/JPEG e atualizações pelo próprio software.
- Interface escura em inglês e português brasileiro, dicas ao passar o mouse e funcionamento em segundo plano.

## Instalação

Baixe o pacote do seu sistema na [última release](https://github.com/NadsonJR/ScreenDepresso/releases/latest). Não é necessário instalar Python separadamente.

| Sistema | Requisitos | Pacote |
|---|---|---|
| Linux | Ubuntu 24.04+, x86_64, sessão X11 | `screendepresso_*_amd64.deb` |
| Windows | Windows 10 build 19041+ ou Windows 11, x64 | `screendepresso_*_windows_amd64_setup.exe` |
| macOS Apple Silicon | macOS 15+ | `screendepresso_*_macos_arm64.dmg` |
| macOS Intel | macOS 15+ | `screendepresso_*_macos_amd64.dmg` |

### Ubuntu / GNOME

Instale o `.deb` pelo instalador de aplicativos do Ubuntu ou pelo terminal. Substitua `VERSAO` pelo número do arquivo baixado e execute na pasta do download:

```bash
sudo apt install ./screendepresso_VERSAO_amd64.deb
```

Abra **ScreenDepresso** no menu de aplicativos. Use uma sessão **X11**; Wayland não é suportado. Para remover o app, use `sudo apt remove screendepresso`; capturas e preferências são preservadas.

Para exibir a bandeja no GNOME, pode ser necessário instalar e habilitar a extensão AppIndicator:

```bash
sudo apt install gnome-shell-extension-appindicator
```

Sem suporte à bandeja, o aplicativo pode permanecer minimizado na barra de tarefas.

### Windows

Execute o instalador `.exe` e abra **ScreenDepresso** pelo menu Iniciar. A instalação é por usuário, em `%LOCALAPPDATA%\Programs\ScreenDepresso`.

O instalador não possui assinatura Authenticode; o SmartScreen pode exibir um aviso. Use os arquivos da release oficial. Para desinstalar, use as configurações de aplicativos do Windows; capturas e preferências são preservadas.

### macOS

Abra o `.dmg` correspondente à arquitetura do Mac e arraste **ScreenDepresso.app** para **Aplicativos**. Abra o app e conceda acesso em **Ajustes do Sistema → Privacidade e Segurança → Gravação de Tela e Áudio do Sistema**. Se solicitado, encerre e abra novamente.

O aplicativo usa assinatura ad hoc, sem notarização Apple. Se o macOS bloquear a primeira abertura, use **Privacidade e Segurança → Abrir Mesmo Assim**. O microfone solicita autorização separada; se ela for negada, o app informa que o vídeo será gravado sem áudio.

## Primeiros passos

1. Capture uma tela, janela ou região pelos botões superiores ou por um atalho global. Também é possível usar **Open image**, **Paste image** ou arrastar uma imagem para o editor vazio.
2. Escolha uma ferramenta na lateral e desenhe sobre a imagem. Os controles acima do editor e os menus dos botões permitem ajustar suas propriedades.
3. Use **Select / move** para selecionar e ajustar objetos existentes.
4. Use **Copy image** para colar o resultado em outro aplicativo ou **Save** para exportar. Cada nova captura abre em sua própria aba.

A interface inicia em inglês. Para usar português brasileiro, abra **Settings → Language**, escolha **Português (Brasil)** e salve.

Na barra superior, **Full screen** e **Record** têm uma faixa inferior de opções. O ícone executa a ação principal; a seta inferior abre o menu. Nos botões laterais, a pequena seta também abre opções da ferramenta. Mantenha o cursor sobre um controle para ver sua dica e atalho.

## Capturas de tela

| Comando | Atalho padrão | Comportamento |
|---|---|---|
| **Full screen** | `Ctrl+Shift+1` | Captura todos os monitores. A seta inferior permite escolher apenas um monitor. |
| **Window** | `Ctrl+Shift+2` | Abre uma grade de miniaturas; escolha uma janela e confirme ou dê um clique duplo. |
| **Region** | `Ctrl+Shift+3` | Arraste a seleção sobre a tela. Ela pode atravessar monitores; `Esc` cancela. |

Altere os atalhos em **Settings → Hotkeys**, inclusive para combinações com Print quando a plataforma permitir. Atalhos duplicados ou ocupados são informados ao configurar. No macOS, os atalhos exibem símbolos nativos: o `Ctrl` dos exemplos corresponde a **Command**.

Capturas originais são salvas automaticamente no workspace. Abrir uma imagem externa não a move nem a duplica nesse diretório.

## Editor de imagens

As ferramentas de desenho continuam ativas para inserir vários objetos. Selecione **Select / move** para ajustar o que já desenhou: arraste o objeto para mover e use suas alças para redimensionar ou ajustar as pontas. `Delete` exclui o objeto selecionado.

| Ferramenta | Opções e uso |
|---|---|
| **Arrow** | Setas clássica, preenchida, dupla e tracejada, além de linha simples; cor configurável. |
| **Rectangle** | Cor, espessura de 1 a 40 px e cantos retos ou arredondados, com raio ajustável. |
| **Text** | Fonte, tamanho de 6 a 200 px e cor. Arraste uma caixa e digite diretamente na imagem. |
| **Speech balloon** | Modelos de fala, arredondado, pensamento e grito; preenchimento, contorno e ponta ajustável. |
| **Numbered markers** | Numeração sequencial com seis modelos. Clique para inserir ou arraste até o alvo; a cor vale para todos os marcadores da imagem. |
| **Blur** | Desfoque dentro/fora da seleção, intensidade de 1 a 100 e modo de composição configurável. |
| **Crop** | Recorte pela área desenhada; a operação pode ser desfeita. |

### Texto, cores e colagem

No texto, `Ctrl+Enter` ou um clique fora confirma; `Esc` cancela e Enter insere uma nova linha. Clique duas vezes em um texto para editá-lo novamente. A caixa cresce com o conteúdo; quando necessário, a imagem é ampliada com transparência, sem cortar as letras.

Selecione um objeto para alterar suas propriedades nos controles acima da imagem ou no menu da ferramenta. Cores de setas e retângulos alteram o objeto selecionado e o padrão dos próximos; a cor dos marcadores altera todos os marcadores da aba. Excluir um marcador renumera os restantes sem lacunas.

**Paste image / Ctrl+V** insere a imagem da área de transferência como um objeto sobre a imagem atual. Ela pode ser movida, redimensionada, excluída e desfeita/refeita. Sem uma imagem aberta, a colagem inicia uma nova imagem. Também é possível arrastar uma imagem ou uma miniatura do workspace para o editor.

### Desfoque

No menu de **Blur** ou nos controles de edição, escolha:

- **Blur outside selection**: mantém a área selecionada nítida e desfoca o restante; é o padrão.
- **Blur inside selection**: desfoca somente a área desenhada.

Cada área mantém sua direção. Use **Select / move** para selecionar um efeito e mudar sua direção ou intensidade. A direção escolhida também vale para as próximas áreas desenhadas.

Em **Shared blur layer**, as áreas usam uma camada e uma intensidade comuns. Áreas de desfoque interno prevalecem sobre áreas nítidas sobrepostas, sem acumular intensidade. **Sequential blur (legacy)** aplica os efeitos em ordem e permite intensidades individuais.

Imagens grandes usam cache e cálculo em segundo plano. Uma prévia temporária aparece até o resultado completo ficar pronto; copiar e salvar sempre usam a resolução original e podem aguardar esse cálculo. Veja a [investigação de desempenho](docs/BLUR_PERFORMANCE.md).

### Zoom, desfazer e exportar

Use o slider no canto inferior esquerdo ou o scroll do mouse para ampliar/reduzir entre **10% e 400%**. O ponto sob o cursor é preservado; **Shift+scroll** rola a imagem. O zoom não altera a resolução de cópia ou exportação.

**Ctrl+Z** desfaz e **Ctrl+Y** refaz. Uma nova edição após desfazer descarta o caminho de refazer. **Copy image** copia o resultado editado e **Save** exporta PNG/JPEG. No X11, mantenha o aplicativo aberto para servir a imagem copiada a outros aplicativos.

Anotações permanecem editáveis durante a sessão. PNG/JPEG exportados são rasterizados: reabrir o arquivo não recupera as camadas de edição.

## Gravação de vídeo

Abra **Record** ou o menu da bandeja e escolha um monitor, uma janela ou uma região. **Ctrl+Alt+R** inicia a gravação do monitor sob o mouse e, durante a gravação, para e salva. Personalize o atalho em **Settings → Hotkeys**. Ao migrar preferências antigas, o app pode escolher outra combinação para evitar conflito com seus atalhos existentes.

Em **Settings → Recording**, ajuste:

- Taxa de quadros: **15, 24, 30 ou 60 fps**.
- Qualidade: baixa, normal, alta ou muito alta.
- Contagem regressiva: desativada, 3 ou 5 segundos.
- Gravação do microfone e dispositivo de entrada.

A barra flutuante permite **pausar/retomar**, **silenciar o microfone**, **parar e salvar** ou **descartar**. Descartar pede confirmação e restaura o editor. Os vídeos são salvos em **MP4**, com H.264 quando há codificador disponível e fallback para MPEG-4. Áudio do sistema não é capturado.

Cada gravação acompanha um monitor. Uma região que cruza monitores fica limitada ao monitor escolhido; a captura de janela pode usar sua área visível como fallback. No Linux/X11, os controles aparecem na gravação de tela inteira. Em regiões que ocupam quase toda a tela, pode não haver espaço externo para a barra. A exclusão dos controles da captura depende do suporte do sistema.

## Abas e workspace

Cada captura abre em uma aba independente, com objetos, cores, zoom, rolagem e desfazer/refazer próprios. Arraste as abas para reordenar. Um asterisco no título indica alterações não salvas; ao fechar, escolha salvar, descartar ou cancelar.

O clique direito em uma aba permite **fechar esta**, **fechar outras** ou **fechar todas**. Fechar uma aba não exclui arquivos do workspace. As abas ficam na memória durante a sessão: salve as edições antes de encerrar.

O **Workspace** mostra miniaturas do diretório configurado:

- Clique duplo em uma imagem abre sua aba ou retorna à aba existente, preservando as edições.
- Clique direito em uma imagem permite **Duplicate** ou **Delete**. A exclusão usa a lixeira do sistema.
- Arraste uma miniatura de imagem para o editor para inseri-la como camada, preservando o arquivo original.
- Vídeos têm reprodução pelo player padrão e exclusão pelo menu de contexto.
- As miniaturas atualizam automaticamente; o ícone de refresh permite atualização manual.

O limite padrão é de **25 imagens**. Em **Settings → Files**, escolha **25, 50, 75, 100 ou sem limite**. Ao salvar imagens ou aplicar um limite menor, as mais antigas são movidas para a lixeira. Vídeos e subpastas não entram nesse limite; abas abertas mantêm sua edição.

## Configurações e arquivos

Abra **Settings** na barra superior ou na bandeja. As abas são **Hotkeys**, **Files**, **Updates**, **Recording** e **Language**.

Em **Files**, escolha o diretório do workspace e o limite de imagens. O diretório também é o destino inicial de exportação. Alterá-lo não move arquivos anteriores; selecione a pasta antiga para vê-los novamente.

| Sistema | Workspace padrão | Preferências |
|---|---|---|
| Linux | `~/.local/share/screendepresso` | `~/.config/screendepresso/settings.json` |
| Windows | `%LOCALAPPDATA%\ScreenDepresso\captures` | `%LOCALAPPDATA%\ScreenDepresso\settings.json` |
| macOS | `~/Library/Application Support/ScreenDepresso/captures` | `~/Library/Application Support/ScreenDepresso/settings.json` |

As variáveis `XDG_DATA_HOME` e `XDG_CONFIG_HOME`, quando definidas, substituem esses caminhos usando a subpasta `screendepresso`.

## Atualizações

Use **Settings → Updates → Check for updates**. Consulta, progresso do download e instalação aparecem na própria aba. Se houver uma versão nova, escolha **Download and install** ou **Keep current version**. Se não houver, o painel informa que o app está atualizado. **Release notes** mostra as notas da versão instalada, disponíveis offline.

Salve as edições antes de atualizar:

- **Ubuntu**: o pacote verificado é instalado pelo `apt`, com autorização via Polkit; depois, use **Restart application**.
- **Windows**: **Restart application** inicia o instalador verificado, encerra a versão anterior e permite reabrir o app ao terminar.
- **macOS**: **Open installer** abre o DMG correto. Encerre o app, substitua-o em Aplicativos e abra a nova versão; a substituição pelo Finder é manual.

Capturas e preferências são preservadas. O atualizador verifica origem, tamanho e SHA-256, requer HTTPS/acesso ao GitHub e oferece apenas versões estáveis mais recentes. O hash verifica integridade em relação ao manifesto da release; não é uma assinatura independente do publicador. O histórico completo está no [CHANGELOG](CHANGELOG.md).

## Segundo plano e atalhos

Ao fechar a janela, escolha **Minimize to tray**, **Quit** ou **Cancel**. Minimizar mantém capturas, edições e atalhos globais disponíveis. Clique no ícone da bandeja ou use **Open** para restaurar; **Quit** encerra o app. Sem bandeja, a janela permanece acessível pela barra de tarefas.

O ScreenDepresso permite apenas uma instância por perfil de usuário. Abri-lo novamente restaura a instância existente, sem criar outro editor ou registrar atalhos duplicados. A versão instalada aparece no rodapé.

| Atalho padrão | Função |
|---|---|
| `Ctrl+Shift+1` / `Ctrl+Shift+2` / `Ctrl+Shift+3` | Capturar tela / janela / região |
| `Ctrl+Alt+R` | Iniciar/parar gravação |
| `Ctrl+S` / `Ctrl+C` / `Ctrl+V` | Salvar / copiar imagem / colar imagem |
| `Ctrl+Z` / `Ctrl+Y` | Desfazer / refazer |
| `Delete` | Excluir objeto selecionado; no workspace, excluir arquivo selecionado |
| `Ctrl+D` | Duplicar a imagem selecionada no workspace |
| `Ctrl+Tab` / `Ctrl+Shift+Tab` | Próxima aba / aba anterior |
| `Ctrl+W` | Fechar aba atual |
| `Ctrl+Enter` / `Esc` | Confirmar / cancelar texto; Esc também cancela seleção de captura |

No macOS, use **Command** nos atalhos descritos com Ctrl. As dicas dos botões mostram a combinação nativa da plataforma.

## Limitações e suporte

- Wayland e instaladores Linux/Windows ARM não são suportados. O macOS possui instaladores separados para Intel e Apple Silicon.
- Capturas de janela podem incluir apenas o conteúdo visível; janelas minimizadas não são oferecidas. Sobreposição e conteúdo protegido podem limitar o resultado. No X11, a área do cliente é capturada sem a decoração do gerenciador de janelas.
- Monitores com escalas diferentes e janelas entre monitores precisam de validação no hardware correspondente.
- O workspace é local e pode conter informações sensíveis. Desfoque é um efeito visual, sem garantia de remoção de informação confidencial.
- Os testes automatizados verificam os instaladores, a edição e a codificação/decodificação de vídeo com quadros sintéticos. Captura real, microfone, permissões e integração com outros apps exigem teste em sessão gráfica.

Para relatar um problema, informe a versão exibida no rodapé, o sistema operacional, a sessão gráfica, os monitores e os passos para reproduzir nas [Issues](https://github.com/NadsonJR/ScreenDepresso/issues).

Para executar pelo código-fonte, testar ou gerar instaladores, consulte [Desenvolvimento e publicação](docs/DEVELOPMENT.md). As mudanças por versão ficam no [CHANGELOG](CHANGELOG.md).
