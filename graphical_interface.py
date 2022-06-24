from easygen import main
from gooey import Gooey, GooeyParser

import wx
app=wx.App()
def ask(question):
    dlg = wx.MessageDialog(None, question,'EasyChartGenerator',wx.YES_NO | wx.ICON_QUESTION)
    result = dlg.ShowModal()

    if result == wx.ID_YES:
        return True
    else:
        return False

if __name__ == '__main__':
    Gooey(
        main,
        show_restart_button=False
    )(argument_parser_class=GooeyParser, ask_func=ask)
