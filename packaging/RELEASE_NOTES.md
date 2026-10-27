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
