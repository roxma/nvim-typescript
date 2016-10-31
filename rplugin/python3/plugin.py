import os
import sys
import re
import json
import neovim

from tempfile import NamedTemporaryFile

sys.path.insert(1, os.path.dirname(__file__))

from client import Client

@neovim.plugin
class DeopletTypescript(object):

    def __init__(self, nvim):
        self.nvim = nvim
        self.client = Client(log_fn=self.log)

    def log(self, message):
        self.nvim.command("echom '{}'".format(re.sub("'", "\'", message)))

    def reload(self):
        filename = self.nvim.current.buffer.name
        contents = self.nvim.eval("join(getline(1,'$'), \"\n\")")

        tmpfile = NamedTemporaryFile(delete=False)
        tmpfile.write(contents.encode("utf-8"))
        tmpfile.close()

        self.client.reload(filename, tmpfile.name)

        os.unlink(tmpfile.name)

    def open_file_in_preview_window(self, filename):
        """ Open the supplied filename in the preview window """
        self.nvim.command("silent! pedit! " + filename)

    def close_preview_window(self):
        """ Close the preview window if it is present, otherwise do nothing """
        self.nvim.command("silent! pclose!")

    def jump_to_preview_window(self):
        """
            Jump the vim cursor to the preview window, which must be active. Returns
            boolean indicating if the cursor ended up in the preview window
        """
        self.nvim.command("silent! wincmd P")
        return self.nvim.current.window.options["previewwindow"]

    def jump_to_previous_window(self):
        """ Jump the vim cursor to its previous window position """
        self.nvim.command("silent! wincmd p")

    def write_to_preview_window(self, message):
        """
            Display the supplied message in the preview window
            (greatly inspired by YouCompletMe implementation)
        """
        self.close_preview_window()

        self.open_file_in_preview_window(self.nvim.eval("tempname()"))

        if self.jump_to_preview_window():
            # We actually got to the preview window. By default the preview window can't
            # be changed, so we make it writable, write to it, then make it read only
            # again.
            self.nvim.current.buffer.options["modifiable"] = True
            self.nvim.current.buffer.options["readonly"]   = False

            self.nvim.current.buffer[:] = message.splitlines()

            self.nvim.current.buffer.options["buftype"]    = 'nofile'
            self.nvim.current.buffer.options["swapfile"]   = False
            self.nvim.current.buffer.options["modifiable"] = False
            self.nvim.current.buffer.options["readonly"]   = True

            # We need to prevent closing the window causing a warning about unsaved
            # file, so we pretend to Vim that the buffer has not been changed.
            self.nvim.current.buffer.options["modified"]   = False

            self.jump_to_previous_window()

    def join_display_parts(self, parts, separator=""):
        return separator.join([part["text"] for part in parts])

    @neovim.command("DeopleteTypescriptSignature", sync=True)
    def signature(self):
        file = self.nvim.current.buffer.name
        line, col = self.nvim.current.window.cursor

        self.reload()

        signature = self.client.signature_help(file, line, col + 1)

        if not signature or "items" not in signature:
            return

        output = []
        items = signature["items"]

        for item in signature["items"]:
            prefix = self.join_display_parts(item["prefixDisplayParts"])
            suffix = self.join_display_parts(item["suffixDisplayParts"])
            separator = self.join_display_parts(item["separatorDisplayParts"])
            parameters = []

            for param in item["parameters"]:
                parameters.append(self.join_display_parts(param["displayParts"]))

            item_signature = re.sub("\s+", " ", "".join([prefix, separator.join(parameters), suffix]))

            output.append(item_signature)

        self.write_to_preview_window("\n".join(output))
