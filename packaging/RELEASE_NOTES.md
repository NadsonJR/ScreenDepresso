## Novidades da versão 0.6.2

- Zoom pelo scroll do mouse, mantendo o ponto sob o cursor; Shift+scroll mantém a rolagem da imagem.
- Modelos de seta clássica, preenchida, dupla, tracejada e linha simples no menu do botão de seta, com cores e edição de objetos existentes.
- Botões e fundos dos ícones quadrados.
- Desfoque em uma camada compartilhada: todas as áreas selecionadas continuam nítidas e a intensidade é comum. O modo anterior continua disponível como **Sequential blur (legacy)** no menu do desfoque.
- Consulta de atualizações automática, sem botão durante a verificação ou quando já está na versão mais recente.
- Barra de progresso real no download, com validação de tamanho e SHA-256 preservada.
- Botão **Restart application** ao concluir: no Linux, reabre após a instalação; no Windows, instala e reabre a aplicação quando o usuário decide reiniciar.

## Novidades da versão 0.6.1

- Nenhuma aba visível quando não há imagens abertas.
- Balões de fala oval, arredondado, pensamento e grito, com modelos e cores de preenchimento/contorno no menu do botão lateral.
- Balões editáveis, incluindo controle independente da ponta, com desfazer/refazer.
- Ícone de colar em formato de prancheta.
- Slider de zoom de 10% a 400% no canto inferior esquerdo, independente por aba, sem alterar a resolução da exportação.
- Fonte, tamanho e cor do texto configuráveis no menu do botão de texto e em objetos existentes.
- Caixa de texto cresce automaticamente; se necessário, a área da imagem aumenta com transparência para evitar cortes. A expansão também pode ser desfeita.

## Novidades da versão 0.6.0

- Várias capturas abertas em abas, com edição, seleção, cores e desfazer/refazer independentes.
- Novas capturas abrem em outra aba sem substituir a edição atual.
- Abas podem ser reordenadas arrastando; Ctrl+Tab e Ctrl+Shift+Tab alternam entre capturas e Ctrl+W fecha a aba atual.
- Aviso para salvar, descartar ou cancelar ao fechar uma aba com alterações. Cancelar o salvamento mantém a aba aberta.
- Histórico abre capturas em abas e reutiliza a aba existente quando a imagem já está aberta.
- Salvar, copiar, colar, recortar e os controles de edição atuam na aba ativa.

## Novidades da versão 0.5.2

- Pillow atualizado para 13.0.0, com correções de segurança.
- Instalações pelo código-fonte agora exigem Python 3.11 ou posterior, conforme o requisito do Pillow. Os instaladores continuam incluindo Python.

## Novidades da versão 0.5.1

- Apenas uma instância do ScreenDepresso por perfil de usuário no Windows e Linux.
- Abrir o aplicativo novamente restaura a janela existente, inclusive quando estiver na bandeja, preservando a edição atual.
- Inicializações simultâneas não criam janelas ou atalhos duplicados.
- Recuperação automática da trava após encerramento forçado ou queda do processo.

## Novidades da versão 0.5.0

- Suporte a Windows 10/11 x64: capturas, janelas, seleção de região, atalhos globais, bandeja e atualização pelo instalador.
- Instalador `.exe` por usuário, com atalhos no menu Iniciar e desinstalador; inclui o runtime Python.
- Versão do aplicativo sempre visível no rodapé.
- Release com instaladores Windows e Ubuntu, além de manifesto e checksums comuns.

### Windows

Baixe `screendepresso_*_windows_amd64_setup.exe`. Requer Windows 10 build 19041+ ou Windows 11 x64. O instalador não é assinado com Authenticode nesta versão; o SmartScreen pode exibir um aviso. Baixe somente a release oficial. Capturas e preferências ficam em `%LOCALAPPDATA%\ScreenDepresso` e são preservadas ao desinstalar ou atualizar.

Para atualizar, salve as edições e use Settings → Updates. O aplicativo fecha após iniciar o instalador verificado.

## Novidades da versão 0.4.2

- Intensidade do desfoque integrada ao menu do próprio botão lateral.
- Recorte somente na barra superior; botão X lateral e barra de menus removidos. Delete continua excluindo objetos.
- Ao fechar a janela, escolha minimizar em segundo plano, encerrar ou cancelar.
- Ícone da bandeja com comandos para abrir, capturar, configurar, verificar atualizações e sair.
- Ao minimizar, os atalhos globais e a imagem em edição permanecem ativos.
- Sem suporte à bandeja no desktop, a janela fica minimizada na barra de tarefas para continuar acessível.

No GNOME, a bandeja usa a integração AppIndicator. As opções e mensagens estão disponíveis em inglês e português BR.

## Novidades da versão 0.4.1

- Seletores de cor integrados aos menus dos botões laterais de marcadores, retângulos e setas.
- Setas com cor personalizável para o objeto selecionado e as próximas setas, incluindo desfazer/refazer.
- Ícones atualizados: disquete para salvar, duas folhas para copiar e mão aberta para selecionar/mover.
- Controles de cor removidos da faixa superior, com indicação da cor nos próprios ícones laterais.

## Novidades da versão 0.4.0

- Dicas ao passar o mouse nos botões e controles, com nomes e atalhos traduzidos.

- Marcadores circulares numerados automaticamente em sequência, com indicador e ponto de destino.
- Clique para inserir; arraste para apontar; use Selecionar para ajustar o círculo e a ponta separadamente.
- Seletor de cor para todos os marcadores, com contraste automático dos números.
- Seletor de cor para o retângulo selecionado e os próximos retângulos.
- Numeração sem lacunas após exclusão, com suporte a desfazer/refazer.
- Novos controles disponíveis em inglês e português BR.

## Novidades da versão 0.3.1

- Slider e campo numérico para intensidade do desfoque, de 1 a 100, com edição de efeitos existentes.
- Colar imagens como objetos sobre a imagem atual (Ctrl+V), com movimento, redimensionamento, transparência e desfazer/refazer.
- Interface em inglês por padrão; aba Language nas configurações permite alternar imediatamente entre English e Português (Brasil).

- Interface escura com ações no topo, ferramentas na lateral, imagem centralizada e histórico recolhível.
- Texto diretamente na imagem: arraste uma caixa, digite e confirme com Ctrl+Enter ou clique fora. Esc cancela.
- Duplo clique para reeditar o texto no mesmo local, com suporte a múltiplas linhas.
- Corrigida a prévia de texto incompleta que podia interromper a pintura e deixar a tela preta durante o popup.
- Copiar e salvar incluem o texto em edição, com desfazer/refazer após a confirmação.

## Novidades da versão 0.3.0

- Ctrl+Z para desfazer e Ctrl+Y para refazer.
- Configurações com abas de hotkeys, diretório de arquivos e verificação de atualizações.
- Prévia real de seta durante o arraste.
- Objetos editáveis: selecionar, mover, redimensionar, excluir e editar o texto por duplo clique.
- Desfoque fora da região selecionada, com intensidade ajustável de 1 a 100.

As anotações são editáveis durante a sessão de edição. Exportações e imagens reabertas do histórico são rasterizadas. Alterar o diretório não move capturas antigas.

## Instalação no Ubuntu 24.04 ou mais recente (x86_64 / X11)

Baixe o arquivo `screendepresso_*_amd64.deb` abaixo. Abra-o no instalador de aplicativos do Ubuntu ou execute:

```bash
sudo apt install ./screendepresso_*_amd64.deb
```

O pacote inclui Python e as dependências Python: não precisa de Python, pip nem build instalado no computador. Abra **ScreenDepresso** no menu de aplicativos.

Para novas versões, abra **Atualizações… → Verificar atualizações → Baixar e instalar**. O pacote é conferido com SHA-256 antes de ser entregue ao gerenciador de pacotes. O Ubuntu pede autorização de administrador. Feche e abra o aplicativo após atualizar; o histórico é preservado.

Inclui captura de tela, janela visível ou região, atalhos globais, editor com setas, texto, retângulos, desfoque, recorte e desfazer, histórico, copiar e exportar imagens.

Requer sessão X11; Wayland e ARM ainda não são suportados. Captura de janela não inclui conteúdo oculto por outras janelas.
