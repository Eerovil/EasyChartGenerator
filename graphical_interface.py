import tkinter as tk
from tkinter import filedialog, messagebox
import argparse
import logging
import sys
from EasyChartGenerator.easygen import main as easygen_main, parse_args

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TextHandler(logging.Handler):
    def __init__(self, text):
        logging.Handler.__init__(self)
        self.text = text

    def emit(self, record):
        msg = self.format(record)
        self.text.insert(tk.END, msg + "\n")
        self.text.see(tk.END)

# Define the main GUI application
class EasyChartGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Easy Chart Generator")

        class TKInterAgrparser():
            tk_root = root
            current_row = -1
            keys = []
            types = {}

            def parse_args(self):
                return self

            def args_as_obj(self):
                logger.info("Parsing arguments: %s", self.__dict__)
                ret = {}
                for key in self.keys:
                    ret[key] = getattr(self, key).get()
                    if key in self.types:
                        try:
                            ret[key] = self.types[key](ret[key])
                        except ValueError:
                            if self.types[key] == int or self.types[key] == float:
                                ret[key] = 0
                return argparse.Namespace(**ret)

            def add_argument(self, *args, **kwargs):
                self.current_row += 1
                dest = kwargs.get("dest") if kwargs.get("dest") else args[0][2:]
                if not dest:
                    dest = args[1][2:]
                self.keys.append(dest)
                logger.warning("Adding argument: %s", dest)

                if kwargs.get("widget") == "FileChooser":
                    tk.Label(self.tk_root, text=f"{dest}: {kwargs.get("help")}").grid(row=self.current_row, column=0, padx=10, pady=10)
                    self.current_row += 1
                    setattr(self, dest, tk.Entry(self.tk_root, width=50))
                    getattr(self, dest).grid(row=self.current_row, column=0)
                    self.filebutton = filedialog.Button(self.tk_root, text="Browse")
                    self.filebutton.grid(row=self.current_row, column=1)
                    return
                if kwargs.get("widget") == "DirChooser":
                    tk.Label(self.tk_root, text=f"{dest}: {kwargs.get("help")}").grid(row=self.current_row, column=0, padx=10, pady=10)
                    self.current_row += 1
                    setattr(self, dest, tk.Entry(self.tk_root, width=50))
                    getattr(self, dest).grid(row=self.current_row, column=0)
                    self.dirbutton = filedialog.Button(self.tk_root, text="Browse")
                    self.dirbutton.grid(row=self.current_row, column=1)
                    return
                if kwargs.get("action") == "store_true":
                    setattr(self, dest, tk.BooleanVar())
                    tk.Checkbutton(self.tk_root, text=f"{dest}: {kwargs.get("help")}", variable=getattr(self, dest)).grid(row=self.current_row, column=0, columnspan=3)
                    return
                if kwargs.get("type") == int or kwargs.get("type") == float:
                    self.types[dest] = kwargs.get("type")
                    tk.Label(self.tk_root, text=f"{dest}: {kwargs.get("help")}").grid(row=self.current_row, column=0, padx=10, pady=10)
                    self.current_row += 1
                    setattr(self, dest, tk.Entry(self.tk_root, width=10, text=kwargs.get("default")))
                    getattr(self, dest).grid(row=self.current_row, column=0)
                    # Set default value
                    getattr(self, dest).insert(0, kwargs.get("default"))
                    return

        self.arg_parser_class = TKInterAgrparser

    def ask_func(self, msg):
        return messagebox.askyesno("Question", msg)

    def run_main(self):
        args = self.args.args_as_obj()
        easygen_main(args=args, dont_exit=True, ask_func=self.ask_func)

    def add_logic(self):
        # When args.filebutton is clicked, clear dir
        def _set_filename():
            filename = filedialog.askopenfilename()
            self.args.directory.delete(0, tk.END)
            self.args.filename.delete(0, tk.END)
            self.args.filename.insert(0, filename)
            self.args.batch.set(False)

        self.args.filebutton.config(command=_set_filename)
        # When args.dirbutton is clicked, clear file
        def _set_directory():
            directory = filedialog.askdirectory()
            self.args.filename.delete(0, tk.END)
            self.args.directory.delete(0, tk.END)
            self.args.directory.insert(0, directory)
            self.args.batch.set(True)

        self.args.dirbutton.config(command=_set_directory)
        self.args.in_place.set(True)
        
    def add_rest_of_ui(self):
        submit_button = tk.Button(root, text="Submit", command=self.run_main)
        submit_button.grid(row=30, columnspan=2, pady=10)

        # Add a text box to display the output
        output_text = tk.Text(root, height=20, width=100)
        output_text.grid(row=31, columnspan=2)
        # Add new logging handler to redirect stdout to the text box

        handler = TextHandler(output_text)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(handler)


if __name__ == "__main__":
    root = tk.Tk()
    app = EasyChartGeneratorApp(root)
    # Add args from CLI to GUI
    app.args = parse_args(app.arg_parser_class)
    # Add rest of UI
    app.add_rest_of_ui()
    # Add logic
    app.add_logic()
    root.mainloop()
