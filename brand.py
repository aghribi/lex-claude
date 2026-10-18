"""ag brand: run Claude Code behind a PTY that repaints its startup logo, name and title.

usage: brand.py CLAUDE_BIN [ARGS...]
env:   LEX_CLAUDE_BRAND_NAME (max 11 cells), LEX_CLAUDE_BRAND_RGB (default "63;169;245")

Works on cells, not bytes: a small tokenizer tracks the cursor and the SGR state,
so the logo is caught however the renderer splits it (fullscreen or classic,
inherited colour, cursor jumps across blank cells). Not a TTY: exec straight through.
"""
import codecs, fcntl, os, pty, re, select, signal, struct, sys, termios, tty, unicodedata

NAME = os.environ.get("LEX_CLAUDE_BRAND_NAME", "Betatron")[:11].ljust(11)
RGB = os.environ.get("LEX_CLAUDE_BRAND_RGB", "63;169;245")
ART = ["╭───●───╮ ",
       "│   β   │ ",
       "╰───────╯ "]
LOGO_COLS, NAME_COL = range(0, 10), 11      # logo footprint; the name starts at col 11
ACCENT = f"\x1b[0;1;38;2;{RGB}m"
NAME_STYLE = "\x1b[0;1m"
ANCHOR_TTL = 4000                            # chars after the anchor during which the name region is live
CTRL_Z = re.compile(rb"\x1a|\x1b\[122;5(?::1)?u")  # legacy byte and kitty keyboard encoding

TOKEN = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"               # CSI
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"    # OSC
    r"|\x1b[PX^_][^\x1b]*\x1b\\"             # DCS/SOS/PM/APC
    r"|\x1b[ -/]*[0-~]"                      # other ESC
    r"|[\x00-\x1f\x7f]"                      # C0
    r"|[^\x00-\x1f\x7f\x1b]+",               # text
    re.S)


class Rewriter:
    def __init__(self, cols):
        self.cols = cols
        self.row = self.col = 0
        self.saved = (0, 0)
        self.fg = None
        self.bold = False
        self.anchor = self.logo_fg = None
        self.since_anchor = 0
        self.pending = ""
        self.modes = {}                      # DEC private modes the child set, replayed after a suspend
        self.kitty = []                      # kitty keyboard flags stack

    def sgr(self, params):
        p = [int(x) if x.isdigit() else 0 for x in re.split("[;:]", params)] if params else [0]
        i = 0
        while i < len(p):
            v = p[i]
            if v == 0:
                self.fg, self.bold = None, False
            elif v == 1:
                self.bold = True
            elif v == 22:
                self.bold = False
            elif 30 <= v <= 37 or 90 <= v <= 97:
                self.fg = str(v)
            elif v == 39:
                self.fg = None
            elif v in (38, 48):
                n = 3 if p[i + 1:i + 2] == [5] else 5 if p[i + 1:i + 2] == [2] else 1
                if v == 38:
                    self.fg = ";".join(map(str, p[i:i + n]))
                i += n - 1
            i += 1

    def csi(self, tok):
        body, final = tok[2:-1], tok[-1]
        if body.startswith("?") and final in "hl":
            for m in body[1:].split(";"):
                self.modes[m] = final == "h"
            return
        if body.startswith(">") and final == "u":
            self.kitty.append(body[1:])
            return
        if body.startswith("<") and final == "u":
            n = int(body[1:]) if body[1:].isdigit() else 1
            del self.kitty[-n:]
            return
        if body.startswith(("?", ">", "<", "=")):
            return
        if final == "m":
            return self.sgr(body)
        args = [int(x) if x.isdigit() else 0 for x in body.split(";")] if body else []
        n = max(args[0], 1) if args else 1
        if final in "Hf":
            self.row = max(args[0], 1) - 1 if args else 0
            self.col = max(args[1], 1) - 1 if len(args) > 1 else 0
        elif final == "A":
            self.row -= n
        elif final in "Be":
            self.row += n
        elif final in "Ca":
            self.col += n
        elif final == "D":
            self.col = max(self.col - n, 0)
        elif final == "E":
            self.row, self.col = self.row + n, 0
        elif final == "F":
            self.row, self.col = self.row - n, 0
        elif final in "G`":
            self.col = n - 1
        elif final == "d":
            self.row = n - 1
        elif final == "s":
            self.saved = (self.row, self.col)
        elif final == "u":
            self.row, self.col = self.saved

    def paint(self, start, text, style):
        """Paint `text` from column `start` on the current row, keep cursor and attributes."""
        return f"\x1b7\x1b[{start + 1}G{style}{text}\x1b8\x1b[C"

    def cell(self, ch):
        w = 0 if unicodedata.combining(ch) else 2 if unicodedata.east_asian_width(ch) in "WF" else 1
        if self.col + w > self.cols:
            self.row, self.col = self.row + 1, 0
        out = ch
        if ch == "▐" and self.col <= 2:   # ▐ opens logo row 0
            self.anchor, self.logo_fg, self.since_anchor = self.row, self.fg, 0
        r = None if self.anchor is None else self.row - self.anchor
        if r in (0, 1, 2) and w == 1:
            if self.col in LOGO_COLS and self.fg == self.logo_fg and (ch == " " or "▀" <= ch <= "▟"):
                out = self.paint(0, ART[r], ACCENT)
            elif (self.bold and ch != " " and NAME_COL <= self.col < NAME_COL + len(NAME)
                  and self.since_anchor < ANCHOR_TTL):
                out = self.paint(NAME_COL, NAME, NAME_STYLE)
        self.col += w
        self.since_anchor += 1
        return out

    def feed(self, data):
        s = self.pending + data
        out, pos = [], 0
        for m in TOKEN.finditer(s):
            if m.start() != pos:
                break
            tok = m.group(0)
            if len(tok) == 2 and tok[0] == "\x1b" and tok[1] in "[]PX^_":
                break                          # CSI/OSC/DCS cut by the read boundary: wait for more
            pos = m.end()
            if tok[0] == "\x1b":
                if tok.startswith("\x1b["):
                    self.csi(tok)
                elif tok.startswith("\x1b]"):
                    tok = re.sub(r"^(\x1b\][02];.*?)Claude Code", lambda g: g.group(1) + NAME.strip(), tok, flags=re.S)
                elif tok == "\x1b7":
                    self.saved = (self.row, self.col)
                elif tok == "\x1b8":
                    self.row, self.col = self.saved
                out.append(tok)
            elif len(tok) == 1 and tok < " " or tok == "\x7f":
                if tok == "\r":
                    self.col = 0
                elif tok == "\n":
                    self.row += 1
                elif tok == "\b":
                    self.col = max(self.col - 1, 0)
                elif tok == "\t":
                    self.col = (self.col // 8 + 1) * 8
                out.append(tok)
            else:
                out.extend(self.cell(ch) for ch in tok)
        self.pending = s[pos:]
        if len(self.pending) > 65536:           # never stall on garbage
            out.append(self.pending)
            self.pending = ""
        return "".join(out)

    def leave(self):
        """Sequences that hand the real terminal back to the shell."""
        on = [m for m, v in self.modes.items() if v]
        return "\x1b[0m" + "".join(f"\x1b[?{m}l" for m in reversed(on)) + "\x1b[<u" * len(self.kitty) + "\x1b[?25h"

    def enter(self):
        """Replay the child's terminal modes after a resume."""
        on = [m for m, v in self.modes.items() if v]
        return "".join(f"\x1b[?{m}h" for m in on) + "".join(f"\x1b[>{f}u" for f in self.kitty)


def winsize(fd):
    return fcntl.ioctl(fd, termios.TIOCGWINSZ, b"\0" * 8)


def main():
    stdin, stdout = sys.stdin.fileno(), sys.stdout.fileno()
    if not (os.isatty(stdin) and os.isatty(stdout)):
        os.execvp(sys.argv[1], sys.argv[1:])

    pid, fd = pty.fork()
    if pid == 0:
        os.execvp(sys.argv[1], sys.argv[1:])

    size = winsize(stdin)
    rw = Rewriter(struct.unpack("HHHH", size)[1])
    fcntl.ioctl(fd, termios.TIOCSWINSZ, size)

    def on_winch(*_):
        size = winsize(stdin)
        rw.cols = struct.unpack("HHHH", size)[1]
        fcntl.ioctl(fd, termios.TIOCSWINSZ, size)
    signal.signal(signal.SIGWINCH, on_winch)

    def out(s):
        os.write(stdout, s.encode("utf-8", "surrogateescape"))

    def suspend():
        # The child leads its own session, so the kernel drops its SIGTSTP:
        # job control has to happen here.
        os.kill(pid, signal.SIGSTOP)
        out(rw.leave())
        termios.tcsetattr(stdin, termios.TCSADRAIN, saved)
        os.kill(os.getpid(), signal.SIGSTOP)
        tty.setraw(stdin)
        out(rw.enter())
        os.kill(pid, signal.SIGCONT)
        r, c, x, y = struct.unpack("HHHH", winsize(stdin))
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", r, max(c - 1, 1), x, y))
        on_winch()                           # two size changes force a full repaint

    saved = termios.tcgetattr(stdin)
    tty.setraw(stdin)
    dec = codecs.getincrementaldecoder("utf-8")("surrogateescape")
    watch = [fd, stdin]
    try:
        while True:
            r, _, _ = select.select(watch, [], [])
            if fd in r:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                out(rw.feed(dec.decode(chunk)))
            if stdin in r:
                data = os.read(stdin, 65536)
                if not data:
                    watch = [fd]
                    continue
                parts = CTRL_Z.split(data)
                for i, part in enumerate(parts):
                    if part:
                        os.write(fd, part)
                    if i < len(parts) - 1:
                        suspend()
    finally:
        termios.tcsetattr(stdin, termios.TCSADRAIN, saved)
        _, status = os.waitpid(pid, 0)
    sys.exit(os.waitstatus_to_exitcode(status))


if __name__ == "__main__":
    main()
