"""CheerLights Terminal App - Display the current CheerLights color in ASCII art."""

import sys
from rich.console import Console
from rich.spinner import Spinner
from rich.live import Live
from rich.text import Text
from .cheerlights import get_current_color
from .ascii_art import display_cheerlights_app

console = Console()

def main():
    """Main entry point for the CheerLights terminal app."""
    try:
        # Show a nice loading spinner while fetching data
        with console.status("Fetching current CheerLights color...", spinner="dots"):
            color_name, hex_color = get_current_color()

        # Display the beautiful Rich-formatted app
        display_cheerlights_app(color_name, hex_color)

    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye![/dim]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]An error occurred: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()