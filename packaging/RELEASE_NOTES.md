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
