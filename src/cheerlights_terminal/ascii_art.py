"""ASCII Art generation and coloring for CheerLights terminal app using Rich."""

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from rich.columns import Columns
from rich.rule import Rule
from rich.layout import Layout

CHEERLIGHTS_ASCII = """
 ██████╗ ██╗  ██╗ ███████╗ ███████╗ ██████╗ 
██╔════╝ ██║  ██║ ██╔════╝ ██╔════╝ ██╔══██╗
██║      ███████║ █████╗   █████╗   ██████╔╝
██║      ██╔══██║ ██╔══╝   ██╔══╝   ██╔══██╗
╚██████╗ ██║  ██║ ███████╗ ███████╗ ██║  ██║
 ╚═════╝ ╚═╝  ╚═╝ ╚══════╝ ╚══════╝ ╚═╝  ╚═╝

██╗     ██╗  ██████╗  ██╗  ██╗ ████████╗ ███████╗
██║     ██║ ██╔════╝  ██║  ██║ ╚══██╔══╝ ██╔════╝
██║     ██║ ██║  ███╗ ███████║    ██║    ███████╗
██║     ██║ ██║   ██║ ██╔══██║    ██║    ╚════██║
███████╗██║ ╚██████╔╝ ██║  ██║    ██║    ███████║
╚══════╝╚═╝  ╚═════╝  ╚═╝  ╚═╝    ╚═╝    ╚══════╝
"""

# Decorative elements for enhanced styling (Windows-safe)
DECORATIVE_TOP = "=" * 50
DECORATIVE_BOTTOM = "-" * 50

# Mapping CheerLights colors to Rich color names
COLOR_MAP = {
    'red': 'bright_red',
    'green': 'bright_green',
    'blue': 'bright_blue',
    'cyan': 'bright_cyan',
    'white': 'bright_white',
    'yellow': 'bright_yellow',
    'purple': 'bright_magenta',
    'magenta': 'bright_magenta',
    'orange': 'orange1',
    'pink': 'hot_pink',
    'oldlace': 'wheat1',
    'warmwhite': 'wheat1',
}

console = Console()

def display_cheerlights_app(color_name, hex_color):
    """Display the complete CheerLights terminal app using Rich with enhanced styling."""
    # Get Rich color for the current CheerLights color
    rich_color = COLOR_MAP.get(color_name.lower(), 'bright_white')

    # Create the main ASCII art with gradient-like effect (no decorative borders)
    ascii_art = Text()
    lines = CHEERLIGHTS_ASCII.strip().split('\n')
    for i, line in enumerate(lines):
        # Create a subtle gradient effect by varying brightness
        if i in [0, 5, 7, 11]:  # Top and bottom lines of CHEER and LIGHTS get extra brightness
            ascii_art.append(line + '\n', style=f"bold {rich_color}")
        elif i in [1, 4, 8, 10]:  # Second lines get medium brightness
            ascii_art.append(line + '\n', style=f"{rich_color}")
        else:  # Middle lines and empty line get standard brightness
            ascii_art.append(line + '\n', style=f"dim {rich_color}")

    # Create styled panel for ASCII art
    ascii_panel = Panel(
        Align.center(ascii_art),
        title=f"[bold bright_white on {rich_color}] * CHEERLIGHTS TERMINAL * [/]",
        title_align="center",
        border_style=f"bold {rich_color}",
        padding=(1, 3),
        expand=False
    )

    # Display everything with streamlined layout
    console.clear()
    console.print()
    console.print(ascii_panel)
    console.print()

    # Add Discord CTA panel
    discord_cta = Text()
    discord_cta.append("🎉 ", style="bold bright_yellow")
    discord_cta.append("Join the CheerLights Community!", style="bold bright_white")
    discord_cta.append("\n\n")
    discord_cta.append("💬 ", style="bright_blue")
    discord_cta.append("Connect with makers, share projects, and discuss IoT lighting!", style="bright_white")
    discord_cta.append("\n")
    discord_cta.append("🔗 ", style="bright_green")
    discord_cta.append("Discord: ", style="bold bright_white")
    discord_cta.append("https://cheerlights.com/discord", style=f"bold {rich_color} underline")

    discord_panel = Panel(
        discord_cta,
        title="[bold bright_white on bright_blue] * JOIN OUR COMMUNITY * [/]",
        title_align="center",
        border_style="bright_blue",
        padding=(1, 2),
        expand=False
    )

    console.print(discord_panel)
