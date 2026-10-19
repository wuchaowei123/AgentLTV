import os


ea_ascii = """  @@@@@@@@@@@@@@@@@@@@@      闁崇粯鍨熼弸鍛村煝閸碍鐎伴柍璇茬墐閺嬪懘鍩㈤崼姘闁宠鐗冮弸鍛村煛濡炵粯鐎块柍缁樺灍閺嬪懘鍩㈤崼姘闁宠鐗冮弸鍛村煛濡炵粯鐎伴柍璇茬墐閺嬪懘鍩″缁樼€块柍缁樺灍閺嬪懘鍩㈤崼姘闁宠鐗冮弸鍛村煛濡炵粯鐎块柍缁樺灍閺嬪懘鍩㈤崼姘闁崇粯鍨熼弸鍛村煝閸碍鐎伴柍璇茬墐閺嬪懘鍩″缁樼€?  @                   @      闁宠鐗冮弸鍛村煛閺傜儤娅滈柍鐑樺姀閺呮煡鍩￠幇銊︽畷闁宠鐗冮弸鍛村煛閹存梹鐎块柍缁樺灍閺嬪懘鍩㈤崼姘珴闁宠鐗冮弸鍛村煛閹存梹鐎伴柍璇茬墐閺嬪懘鍩㈤崼姘闁崇粯鍨熼弸鍛村煝閸碍娅濋柍璇茬墐閺嬪懘鍩￠幋鏃€鐎块柍璇茬墐閺嬪懘鍩￠弬鐑樻畷闁宠鐗冮弸鍛村煛閺傜儤娅滈柍鐑樺姀閺嬪懘鍩㈤崼姘
  @          @        @      闁崇儤鍩冮弸鍛村煝閸碍鐎伴柍璇茬墐閺嬪懘鍩″缁樼€块柍璇茬墐閺嬪懘鍩㈤崼姘€伴柍璇茬墐閺嬪懘鍩㈤崼姘珴闁宠鐗冮弸鍛村煛閹存梹鐎伴柍璇茬墐閺呭綊鍩㈤崼姘€伴柍鐑樸仜閺嬪懘鍩㈤崼姘珴闁宠鐗冮弸鍛村煝閸碍鐎伴柍璇茬墐閺呮煡鍩″┑鍐╃€块柍璇茬墐閺嬪懘鍩㈤崼姘€伴柍璇茬墐閺嬪懘鍩㈤崼姘珴
  @    @@   @@  @@    @      闁崇粯鍨熼弳渚€鍩￠幇銊︽珳闁崇儤鍔忛弸鍛村煝閸碍娅ч柍璇茬墐閺嬪懘鍩￠弬鐑樻珳闁崇儤鍔忛弸鍛村煝閸碍娅濋柍璇茬墐閺嬪懘鍩￠幋鏃€鐎伴柍璇茬墐閺呮娊鍩″锝嗙€伴柍璇茬墐閺嬪懘鍩㈤崼姘珴闁宠鐗冮弸鍛村煛閺傜儤娅滈柍璇茬墐閺嬪懘鍩″缁樼€块柍璇茬墐閺嬪懘鍩￠弬鐑樻珳闁崇儤鍔忛弸鍛村煝閸碍娅?  @   @     @    @@   @      闁宠鐗冮弸鍛村煝閸碍鐎伴柍璇茬墐閺嬪懘鍩￠弬鐑樻畷闁宠鐗冮弸鍛村煛閹存梹鐎块柍缁樺灍閺嬪懘鍩㈤崼姘珴闁宠鐗冮弸鍛村煛閹存梹鐎伴柍璇茬墐閺呮娊鍩㈤幋鏃€娈庨柍璇茬墐閺嬪懘鍩㈤崼姘珴闁宠鐗冮弸鍛村煛閹存梹鐎块柍鐑樺焹閺嬪懘鍩㈤崼姘闁宠鐗冮弸鍛村煛閹存梹鐎块柍缁樺灍閺嬪懘鍩㈤崼姘珴
  @    @@  @    @     @      闁崇儤鍩冮弲鏌ュ煛閹般劍娅滈柍鐑樺姀閺呮煡鍩″┑鍐╃€块柍鐑樺焹閺呮煡鍩″┑鍐╃€块柍缁樺灍閺嗕線鍩￠幇銊︽畷闁崇儤鍩冮弲鏌ュ煛濠靛啯娈庨柍鐑樺姀閺嗗棝鍩㈤幋鏃€鐎块柍鐑樺焹閺呮煡鍩￠幇銊︽畷闁崇儤鍩冮弲鏌ュ煛濠靛啯鐎块柍缁樺灍閺嗕線鍩￠幇銊︽畷闁崇儤鍩冮弲鏌ュ煛濠靛啯鐎块柍缁樺灍閺嗕線鍩￠幇銊︽畷
  @        @          @      @@@@@@@@@@@@@@@
  @                   @   @@                 @@@@@
  @@@@@@@@@@@@@@@@@@@@ @@                       @  @@                 闁宠鐗冮弶鎼佸煝閳?                      @                          @@  @                闁宠鐗冮弸鍛村煝?                    @      @@                      @  @@
                   @       @         @              @   @             闁宠鐗冮弸鎺楀煝?                   @                 @               @  @             闁崇儵鍋撻柍璇插閺?                     @@@@@          @     @           @  @
                      @            @          @       @ @@            闁宠鐗冮弶鎼佸煝?                   @@    @@     @@       @@   @        @              闁宠鐗冮弶浠嬪煝?                  @@        @@         @     @         @
                 @@       @@   @@       @@@@@          @        @@    闁宠鐗冮弸鎺楀煝?              @ @@                @                    @              闁宠鐗冮弶浠嬪煝?             @ @@@@@             @@ @@                 @      @@
            @                  @       @@              @    @@        闁宠鐗冮弸鎺楀煝?       @@@@@@@@@@@@@@@@@@@@@@             @@@          @@@@@@@  @@    闁崇儵鍋撻柍璇插閺?       @     @         @                      @@         @@@  @@
        @@               @                      @      @   @  @@      闁宠鐗冮弶鎼佸煝閳?          @@@@@@@@@@@@@@@@@@                   @    @   @   @@        闁宠鐗冮弸鍛村煝?                                               @  @  @   @
                                               @  @  @@@@
                                               @  @@
"""


def rgb_to_ansi(r, g, b):
    """Convert RGB values to ANSI 256-color code."""
    # Use the 216-color cube (16-231) for better color precision
    r = int(r * 5 / 255)
    g = int(g * 5 / 255)
    b = int(b * 5 / 255)
    return 16 + 36 * r + 6 * g + b


def create_gradient_colors(start_color, end_color, steps):
    """Create a list of RGB colors forming a gradient."""
    colors = []
    for i in range(steps):
        ratio = i / (steps - 1) if steps > 1 else 0
        r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
        g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
        b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
        colors.append((r, g, b))
    return colors


def print_gradient_logo(start_color=(255, 100, 50), end_color=(100, 200, 255)):
    """
    Print the EA logo with a color gradient.

    Args:
        start_color: RGB tuple for the starting color (default: orange-red)
        end_color: RGB tuple for the ending color (default: light blue)
    """
    # Check if terminal supports colors
    if os.getenv("NO_COLOR") or not (
        hasattr(os.sys.stdout, "isatty") and os.sys.stdout.isatty()
    ):
        print(ea_ascii)
        return

    lines = ea_ascii.split("\n")
    num_lines = len(lines)

    # Create gradient colors for each line
    gradient_colors = create_gradient_colors(start_color, end_color, num_lines)

    # Print each line with its corresponding gradient color
    for i, line in enumerate(lines):
        r, g, b = gradient_colors[i]
        ansi_color = rgb_to_ansi(r, g, b)
        print(f"\033[38;5;{ansi_color}m{line}\033[0m")


# Alternative gradient presets
GRADIENT_PRESETS = {
    "fire": ((255, 0, 0), (255, 255, 0)),  # Red to yellow
    "ocean": ((0, 100, 200), (0, 255, 255)),  # Deep blue to cyan
    "sunset": ((255, 100, 50), (255, 200, 100)),  # Orange to light orange
    "forest": ((0, 100, 0), (150, 255, 150)),  # Dark green to light green
    "purple": ((100, 0, 200), (200, 100, 255)),  # Purple to light purple
    "rainbow": ((255, 0, 0), (0, 0, 255)),  # Red to blue (simplified rainbow)
    "monochrome": ((100, 100, 100), (255, 255, 255)),  # Gray to white
    "red_white": ((255, 0, 0), (255, 255, 255)),  # Red to white
}


def print_preset_gradient_logo(preset="sunset"):
    """
    Print the logo with a preset gradient.

    Args:
        preset: Name of the gradient preset ('fire', 'ocean', 'sunset',
            'forest', 'purple', 'rainbow', 'monochrome', 'red_white')
    """
    if preset in GRADIENT_PRESETS:
        start_color, end_color = GRADIENT_PRESETS[preset]
        print_gradient_logo(start_color, end_color)
    else:
        print(
            f"Unknown preset '{preset}'. Available presets: "
            f"{list(GRADIENT_PRESETS.keys())}"
        )
        print_gradient_logo()  # Use default gradient


# https://fsymbols.com/text-art/
