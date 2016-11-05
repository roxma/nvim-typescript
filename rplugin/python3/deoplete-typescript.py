import os
import sys
import re
import neovim
from tempfile import NamedTemporaryFile

sys.path.insert(1, os.path.dirname(__file__))

from client import Client


@neovim.plugin
class DeopletTypescript(object):
    def __init__(self, nvim):
        self.nvim = nvim

        # TSServer client
        self.client = Client(log_fn=self.log)

        # Preview window buffer
        # Don't get or set this value directly, use self.preview_window_buffer
        # property instead
        self.__preview_window_buffer = None

        # Preview window name
        # Don't get or set this value directly, use self.preview_window_name
        # property instead
        self.__preview_window_name = None

        # Plugin options
        self.enable_auto_signature_preview = self.nvim.eval(
            "g:deoplete#sources#tss#enable_auto_signature_preview"
        )

    @property
    def preview_window_buffer(self):
        if self.__preview_window_buffer and \
                not self.__preview_window_buffer.valid:
            self.__preview_window_buffer = None

        return self.__preview_window_buffer

    @preview_window_buffer.setter
    def preview_window_buffer(self, value):
        self.__preview_window_buffer = value

    @property
    def preview_window_name(self):
        if self.__preview_window_buffer and \
                not self.__preview_window_buffer.valid:
            self.__preview_window_name = None

        return self.__preview_window_name

    @preview_window_name.setter
    def preview_window_name(self, value):
        self.__preview_window_name = value

    def log(self, message):
        """ Logs the given message in vim """
        self.nvim.command("echom '{}'".format(re.sub("'", "''", message)))

    def reload(self):
        """ Reload TSServer with tmp content from current buffer """
        filename = self.nvim.current.buffer.name
        contents = self.nvim.eval("join(getline(1,'$'), \"\n\")")

        tmpfile = NamedTemporaryFile(delete=False)
        tmpfile.write(contents.encode("utf-8"))
        tmpfile.close()

        self.client.reload(filename, tmpfile.name)

        os.unlink(tmpfile.name)

    def resize_preview_window(self, height=None):
        """ Resize the preview window to fit it's content """
        preview_buffer = self.preview_window_buffer

        if not preview_buffer:
            return

        for win in self.nvim.windows:
            if win.buffer.number == preview_buffer.number:
                if height is not None:
                    win.height = height
                    return

                content = win.buffer[:]
                win.height = len(content) + 1

                return

    def open_preview_window(self, name, height=2):
        """ Open an empty preview window """
        # If preview window already opened by another function
        # we close it, otherwise we don't need to re-open it
        if self.preview_window_name:
            if self.preview_window_name != name:
                self.close_preview_window(self.preview_window_name)
            else:
                return self.preview_window_buffer

        # Set the new preview window name
        self.preview_window_name = name

        # Temporary filename used to create an empty buffer
        filename = self.nvim.eval("tempname()")

        # Open the temp file in preview window
        self.nvim.command("silent! pedit! {0}".format(filename))

        # Save the preview window buffer
        self.preview_window_buffer = self.nvim.buffers[
            self.get_buffer_number_for_filename(filename)
        ]

        # Resize it to the minimum to prevent the window from
        # hidding half of the screen until the content is updated
        self.resize_preview_window(height=height)

        return self.preview_window_buffer

    def close_preview_window(self, name):
        """ Close the preview window, and its buffer, if it is opened """
        # The preview window is used by another function
        # than the one that's trying to close it
        if self.preview_window_name != name:
            return

        # Close the preview window
        self.nvim.command("silent! pclose!")

        # Delete the buffer
        self.nvim.command("silent! bwipeout! {0}".format(
            self.preview_window_buffer.number
        ))

        # Reset preview window status
        self.preview_window_buffer = None
        self.preview_window_name = None

    def get_buffer_number_for_filename(self, filename):
        """ Return the number of buffer containing the given file """
        return int(self.nvim.eval("bufnr('{0}')".format(filename)))

    def write_to_preview_window(self, name, message):
        """
            Display the supplied message in the preview window
            (greatly inspired by YouCompletMe implementation)
        """
        preview_buffer = self.open_preview_window(name)

        try:
            # Make the preview window buffer editable,
            # so we can update it's content
            preview_buffer.options["modifiable"] = True
            preview_buffer.options["readonly"] = False

            # Update preview window content, and
            # resize it to fit it's content
            preview_buffer[:] = message.splitlines()
            self.resize_preview_window()

            # Turn back the preview window to an uneditable state
            preview_buffer.options["buftype"] = "nofile"
            preview_buffer.options["swapfile"] = False
            preview_buffer.options["modifiable"] = False
            preview_buffer.options["readonly"] = True
        except:
            pass

    def join_display_parts(self, parts, separator=""):
        """ Joins the "display_parts" of TSServer response """
        return separator.join([part["text"] for part in parts])

    @neovim.autocmd(
        "BufNewFile,BufRead",
        pattern="*.ts,*.tsx",
        eval="expand('%:p')"
    )
    def on_buffer_read(self, filename):
        self.client.open(filename)

    @neovim.autocmd(
        "BufDelete",
        pattern="*.ts,*.tsx",
        eval="expand('<afile>:p')"
    )
    def on_buffer_delete(self, filename):
        self.client.close(filename)

    # =*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=
    # Signature Hint
    #
    # command: DeopleteTypescriptSignature
    #   If called when the cursor is on a function's parameters, it shows the
    #   function's signature in a preview window.
    #
    # option: g:deoplete#sources#tss#enable_auto_signature_preview (default: 1)
    #   If set to 1, it automatically shows function's signature in a preview
    #   window while editing it's parameters.
    #
    # =*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=
    @neovim.command("DeopleteTypescriptSignature")
    def signature(self):
        # Always perform a TSServer reload first
        self.reload()

        # Current file, and cursor position
        file = self.nvim.current.buffer.name
        line, col = self.nvim.current.window.cursor

        # Ask TSServer the signature for the function under the cursor
        signature = self.client.signature_help(file, line, col + 1)

        # If TSServer returns an empty response
        if not signature or "items" not in signature:
            return False

        output = []

        # Join the signature output
        for item in signature["items"]:
            prefix = self.join_display_parts(item["prefixDisplayParts"])
            suffix = self.join_display_parts(item["suffixDisplayParts"])
            separator = self.join_display_parts(item["separatorDisplayParts"])
            parameters = []

            for parameter in item["parameters"]:
                parameter_text = self.join_display_parts(
                    parameter["displayParts"]
                )

                if "documentation" in parameter and \
                        len(parameter["documentation"]) > 0:
                    parameter_text += " /* "
                    parameter_text += self.join_display_parts(
                        parameter["documentation"]
                    )
                    parameter_text += " */"

                parameters.append(parameter_text)

            item_signature = re.sub("\s+", " ", "".join([
                prefix,
                separator.join(parameters),
                suffix
            ]))

            if "documentation" in item and len(item["documentation"]):
                documentation = self.join_display_parts(
                    item["documentation"],
                )
                item_signature += "\n/**\n * "
                item_signature += re.sub("\n", "\n * ", documentation)
                item_signature += "\n */"

            output.append(item_signature)

        # Write the signature in the preview window
        self.write_to_preview_window("signature", "\n".join(output))

        return True

    @neovim.autocmd("InsertEnter,InsertCharPre", pattern="*.ts,*.tsx")
    def on_insert(self):
        if not self.enable_auto_signature_preview:
            return

        # If the response from TSServer is empty we automatically close
        # the preview window
        if not self.signature():
            self.close_preview_window("signature")

    @neovim.autocmd("InsertLeave", pattern="*.ts,*.tsx")
    def on_insert_leave(self):
        if not self.enable_auto_signature_preview:
            return

        # Automatically close the preview window when leaving insert mode
        self.close_preview_window("signature")
