"""English is the default; preferences select English or Brazilian Portuguese."""
from PySide6.QtCore import QTranslator
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QApplication, QLabel, QAbstractButton, QLineEdit, QPlainTextEdit, QTabWidget, QDockWidget, QToolBar

# English source strings and their Brazilian Portuguese translations.
CATALOG = {
 'Settings…': 'Configurações…', 'Settings': 'Configurações', 'Updates…': 'Atualizações…',
 'About': 'Sobre', 'Actions': 'Ações', 'Save': 'Salvar', 'Copy image': 'Copiar imagem',
 'Paste image': 'Colar imagem', 'Undo': 'Desfazer', 'Redo': 'Refazer', 'Crop': 'Recortar',
 'Full screen': 'Tela inteira', 'Window': 'Janela', 'Region': 'Região',
 'Tools': 'Ferramentas', 'Select / move': 'Selecionar / mover', 'Arrow': 'Seta',
 'Rectangle': 'Retângulo', 'Text — drag and type': 'Texto — arraste e digite',
 'Blur outside selection': 'Desfocar fora da seleção', 'Crop selection': 'Recorte',
 'Delete object (Delete)': 'Excluir objeto (Delete)', 'History': 'Histórico',
 'Capture history': 'Histórico de capturas', 'Blur strength:': 'Intensidade do desfoque:',
 'Arrow • Drag on the image to draw': 'Seta • Arraste na imagem para desenhar',
 'Select • Drag to move; use handles to resize': 'Selecionar • Arraste para mover; use as alças para redimensionar',
 'Text • Drag a box and type; Ctrl+Enter confirms; Esc cancels': 'Texto • Arraste a caixa e digite; Ctrl+Enter confirma; Esc cancela',
 'Rectangle • Drag on the image to draw': 'Retângulo • Arraste na imagem para desenhar',
 'Crop • Drag the area you want to keep': 'Recorte • Arraste a região que deseja manter',
 'Blur • Drag the area you want to keep sharp': 'Desfoque • Arraste a região que deseja preservar nítida',
 'No image • Capture a screen to get started': 'Nenhuma imagem • Capture uma tela para começar',
 'Clipboard does not contain an image.': 'A área de transferência não contém uma imagem.',
 'Image copied. Keep the application open to provide clipboard data.': 'Imagem copiada. Mantenha o aplicativo aberto para disponibilizar a área de transferência.',
 'Save image': 'Salvar imagem', 'Could not save the capture.': 'Não foi possível salvar a captura.',
 'Could not save to this path or format.': 'Não foi possível salvar nesse caminho ou formato.',
 'Capture window': 'Capturar janela', 'Visible window (unobstructed):': 'Janela visível (sem obstruções):',
 'Window capture': 'Captura de janela', 'No windows available.': 'Nenhuma janela disponível.',
 'Capture unavailable. Run in an X11 session.': 'Captura indisponível. Execute numa sessão X11.',
 'Capture error': 'Erro de captura', 'Quit': 'Sair', 'Open': 'Abrir', 'Capture ': 'Capturar ',
 'Hotkeys unavailable: ': 'Atalhos indisponíveis: ',
 'This MVP requires an X11 session. Select Ubuntu on Xorg at login.': 'Este MVP requer uma sessão X11. Selecione Ubuntu on Xorg no login.',
 'Type here…': 'Digite aqui…',
 'Ctrl+Enter confirms • Esc cancels • Click outside to confirm': 'Ctrl+Enter confirma • Esc cancela • Clique fora para confirmar',
 'Hotkeys': 'Atalhos', 'Files': 'Arquivos', 'Updates': 'Atualizações',
 'Directory for new captures and exports:': 'Diretório para novas capturas e exportações:',
 'Browse…': 'Escolher…',
 'Existing files stay in the previous directory. History displays the selected directory.': 'Arquivos existentes permanecem no diretório anterior. O histórico mostra o diretório escolhido.',
 'Check for updates': 'Verificar atualizações', 'Capture directory': 'Diretório das capturas',
 'Use a combination with Ctrl, Alt, Shift or Meta.': 'Use uma combinação com Ctrl, Alt, Shift ou Meta.',
 'Choose a letter, number, F1–F35, Print or a navigation key.': 'Escolha letra, número, F1–F35, Print ou uma tecla de navegação.',
 'Invalid hotkeys': 'Atalhos inválidos', 'Invalid directory': 'Diretório inválido',
 'Each capture must have a different hotkey.': 'Cada captura deve ter um atalho diferente.',
 'Enter an absolute directory path.': 'Informe um diretório absoluto.',
 'Could not stop the previous hotkeys.': 'Não foi possível encerrar os atalhos anteriores.',
 'Hotkey is in use by another application. Choose another combination.': 'Atalho ocupado por outro aplicativo. Escolha outra combinação.',
 'Duplicate hotkeys.': 'Atalhos duplicados.', 'Key unavailable on this keyboard: ': 'Tecla não disponível neste teclado: ',
 'Invalid update version.': 'Versão de atualização inválida.', 'Download destination is not allowed.': 'Destino de download não permitido.',
 'Updates are only available for Linux x86_64.': 'Atualização disponível somente para Linux x86_64.',
 'Invalid package source.': 'Origem do pacote inválida.', 'Invalid package metadata.': 'Metadados do pacote inválidos.',
 'Update manifest exceeds the size limit.': 'Manifesto de atualização excede o limite.',
 'Download is larger than the announced package.': 'Download maior que o pacote anunciado.',
 'SHA-256 verification failed. The package was discarded.': 'Falha na verificação SHA-256. O pacote foi descartado.',
 'Update ScreenDepresso': 'Atualizar ScreenDepresso', 'Installed version: ': 'Versão instalada: ',
 'Checking published versions on GitHub…': 'Consultando versões publicadas no GitHub…',
 'Install update': 'Instalar atualização', 'Download and install version ': 'Baixar e instalar a versão ',
 '?\nUbuntu will request administrator authorization. Your captures will be preserved.': '?\nO Ubuntu solicitará autorização de administrador. Suas capturas serão preservadas.',
 'Downloading and verifying the package…': 'Baixando e verificando o pacote…',
 'You are on the latest version (': 'Você está na versão mais recente (', 'New version: ': 'Nova versão: ',
 'Download and install': 'Baixar e instalar', 'Verified package saved to:\n': 'Pacote verificado salvo em:\n',
 '\nInstall it using the Ubuntu package manager.': '\nInstale pelo gerenciador de pacotes do Ubuntu.',
 'Waiting for Ubuntu authorization and installation…': 'Aguardando autorização e instalação pelo Ubuntu…',
 'Could not start the Ubuntu installer.': 'Não foi possível iniciar o instalador do Ubuntu.',
 'Update installed. Close and reopen ScreenDepresso to use the new version.\nSave your edits before closing.': 'Atualização instalada. Feche e abra o ScreenDepresso para usar a nova versão.\nSalve suas edições antes de fechar.',
 'Installation was cancelled or failed. The current version remains available.\n': 'Instalação cancelada ou malsucedida. A versão atual continua disponível.\n',
 'Could not complete the update. Check your connection and try again.': 'Não foi possível concluir a atualização. Verifique a conexão e tente novamente.',
 'Update': 'Atualização', 'Language': 'Idioma', 'Interface language:': 'Idioma da interface:',
 'Language changes apply immediately when you save.': 'A alteração de idioma é aplicada imediatamente ao salvar.',
 'Select a blur effect to change its strength.': 'Selecione um efeito de desfoque para alterar a intensidade.',
 'Cancel': 'Cancelar', 'Close': 'Fechar', 'Yes': 'Sim', 'No': 'Não',
 '&Save': '&Salvar', '&Cancel': '&Cancelar', '&Open': '&Abrir', '&Close': '&Fechar', '&Yes': '&Sim', '&No': '&Não',
 'File name:': 'Nome do arquivo:', 'Files of type:': 'Arquivos do tipo:', 'Look in:': 'Examinar:',
 'Name': 'Nome', 'Size': 'Tamanho', 'Type': 'Tipo', 'Date Modified': 'Data de modificação',
 'Show ': 'Mostrar ', 'All Files (*)': 'Todos os arquivos (*)', 'Choose': 'Escolher',
}
CATALOG.update({'Capture full screen': 'Capturar tela inteira', 'Capture window': 'Capturar janela', 'Capture region': 'Capturar região', 'Unsupported language': 'Idioma não suportado'})
CATALOG.update({
 'Blur strength (1–100)': 'Intensidade do desfoque (1–100)',
 'Click a capture to open it in the editor.': 'Clique em uma captura para abri-la no editor.',
 'Arrow color…': 'Cor da seta…',
 'Arrow color': 'Cor da seta',
 'Rectangle color…': 'Cor do retângulo…',
 'Rectangle color': 'Cor do retângulo',
 'Change the selected rectangle and the color of new rectangles.': 'Altere o retângulo selecionado e a cor dos novos retângulos.',
 'Numbered markers': 'Marcadores numerados',
 'Marker color…': 'Cor dos marcadores…',
 'Marker color': 'Cor dos marcadores',
 'Change the color of all markers in this image.': 'Altere a cor de todos os marcadores desta imagem.',
 'Numbers • Click for the next number; drag from the circle to its target': 'Números • Clique para o próximo número; arraste do círculo até o alvo',
 'Basic colors': 'Cores básicas', '&Basic colors': '&Cores básicas',
 'Custom colors': 'Cores personalizadas', '&Custom colors': 'Cores &personalizadas',
 '&Add to Custom Colors': '&Adicionar às cores personalizadas',
 '&Pick Screen Color': '&Capturar cor da tela', 'Select Color': 'Selecionar cor',
 'Hu&e:': '&Matiz:', '&Sat:': '&Saturação:', '&Val:': '&Valor:',
 '&Red:': '&Vermelho:', '&Green:': '&Verde:', 'Bl&ue:': '&Azul:',
 'A&lpha channel:': 'Canal a&lfa:', 'HTML:': 'HTML:',
})
CATALOG.update({
 'Close ScreenDepresso': 'Fechar ScreenDepresso',
 'Keep ScreenDepresso running in the background or quit?': 'Manter o ScreenDepresso em segundo plano ou encerrar?',
 'Minimizing keeps your image and capture hotkeys available. Save your edits before quitting.': 'Minimizar mantém a imagem e os atalhos de captura disponíveis. Salve suas edições antes de encerrar.',
 'The system tray is unavailable. The window will remain minimized in the taskbar.': 'A bandeja do sistema está indisponível. A janela ficará minimizada na barra de tarefas.',
 'Minimize to tray': 'Minimizar para a bandeja',
 'Minimize to taskbar': 'Minimizar para a barra de tarefas',
})
CATALOG.update({
 'Application version': 'Versão do aplicativo',
 'This key is not supported on Windows.': 'Esta tecla não é suportada no Windows.',
 'Could not register global hotkeys.': 'Não foi possível registrar os atalhos globais.',
 'Updates are only available for Windows and Linux x86_64.': 'Atualizações disponíveis somente para Windows e Linux x86_64.',
 '?\nThe app will close to install the update. Save your edits first. Your captures will be preserved.': '?\nO aplicativo será fechado para instalar a atualização. Salve suas edições antes. Suas capturas serão preservadas.',
 'Installer started. The application will now close.': 'Instalador iniciado. O aplicativo será fechado agora.',
})
CATALOG.update({
 'Could not create the application instance lock.': 'Não foi possível criar a trava de instância do aplicativo.',
 'Could not start the application activation channel.': 'Não foi possível iniciar o canal de ativação do aplicativo.',
 'ScreenDepresso is already running. Open it from the tray or taskbar.': 'O ScreenDepresso já está em execução. Abra-o pela bandeja ou pela barra de tarefas.',
})
REVERSE = {value: key for key, value in CATALOG.items()}
_language = 'en'
_translator = None


def tr(source):
    english = REVERSE.get(source, source)
    return CATALOG.get(english, english) if _language == 'pt_BR' else english


def mode_label(mode):
    return tr({'tela': 'Full screen', 'janela': 'Window', 'região': 'Region'}[mode])


class NativeTranslator(QTranslator):
    def isEmpty(self):
        return False

    def translate(self, context, sourceText, disambiguation=None, n=-1):
        return tr(sourceText)


def translate_tree(root):
    root.setWindowTitle(tr(root.windowTitle()))
    for widget in [root] + root.findChildren(QAction) + root.findChildren(QLabel) + root.findChildren(QAbstractButton):
        if hasattr(widget, 'text') and hasattr(widget, 'setText'):
            widget.setText(tr(widget.text()))
    for widget in [root] + root.findChildren(QWidget) + root.findChildren(QAction):
        shortcut = widget.property('hoverShortcut')
        if shortcut is not None:
            widget.setToolTip(widget.text() + (f' ({shortcut})' if shortcut else ''))
        else:
            widget.setToolTip(tr(widget.toolTip()))
    for widget in [root] + root.findChildren(QDockWidget) + root.findChildren(QToolBar):
        if isinstance(widget, (QDockWidget, QToolBar)):
            widget.setWindowTitle(tr(widget.windowTitle()))
    for tabs in root.findChildren(QTabWidget):
        for index in range(tabs.count()):
            tabs.setTabText(index, tr(tabs.tabText(index)))
            tabs.setTabToolTip(index, tr(tabs.tabToolTip(index)))


def set_language(language):
    global _language, _translator
    _language = language if language in ('en', 'pt_BR') else 'en'
    app = QApplication.instance()
    if app is not None:
        if _translator is None:
            _translator = NativeTranslator(app)
            app.installTranslator(_translator)
        for widget in app.topLevelWidgets():
            translate_tree(widget)
