import os
os.system("color")

class Color:
    BOLD        = '\033[1m'
    UNDERLINE   = '\033[4m'
    CROSSED_OUT = '\033[9m'
    ENDC        = '\033[0m'

    GREY = "\033[30m" + "\033[37m"

    # Black
    FG_BLACK        = "\033[30m"
    FG_BRIGHT_BLACK = "\033[30;1m"
    BG_BLACK        = "\033[40m"
    BG_BRIGHT_BLACK = "\033[40;1m"

    # Red
    FG_RED        = "\033[31m"
    FG_BRIGHT_RED = "\033[31;1m"
    BG_RED        = "\033[41m"
    BG_BRIGHT_RED = "\033[41;1m"

    # Green
    FG_GREEN        = "\033[32m"
    FG_BRIGHT_GREEN = "\033[32;1m"
    BG_GREEN        = "\033[42m"
    BG_BRIGHT_GREEN = "\033[42;1m"

    # Yellow
    FG_YELLOW = "\033[33m"
    fgBrightYellow = "\033[33;1m"
    bgYellow = "\033[43m"
    bgBrightYellow = "\033[43;1m"

    # Blue
    fgBlue = "\033[34m"
    fgBrightBlue = "\033[34;1m"
    bgBlue = "\033[44m"
    bgBrightBlue = "\033[44;1m"

    # Magenta
    fgMagenta = "\033[35m"
    fgBrightMagenta = "\033[35;1m"
    bgMagenta = "\033[45m"
    bgBrightMagenta = "\033[45;1m"

    # Cyan
    fgCyan = "\033[36m"
    fgBrightCyan = "\033[36;1m"
    bgCyan = "\033[46m"
    bgBrightCyan = "\033[46;1m"

    # White
    fgWhite = "\033[37m"
    fgBrightWhite = "\033[37;1m"
    bgWhite = "\033[47m"
    bgBrightWhite = "\033[47;1m"



# if __name__ == '__main__':
#     print(Color.YELLOW, "Hello!", Color.ENDC)