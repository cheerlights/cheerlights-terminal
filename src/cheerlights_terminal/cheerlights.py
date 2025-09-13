"""CheerLights API interaction module."""

from cheerlights_api import cheerlights_api
import sys

def get_current_color():
    """Fetch the current CheerLights color and hex code."""
    try:
        # Get both color name and hex code
        color_data = cheerlights_api.get_current_color()
        return color_data.get('color', 'white'), color_data.get('hex', '#FFFFFF')
    except Exception as e:
        print(f"Error fetching CheerLights color: {e}", file=sys.stderr)
        # Return default white color on error
        return 'white', '#FFFFFF'

def get_current_color_name():
    """Fetch just the current CheerLights color name."""
    try:
        return cheerlights_api.get_current_color_name()
    except Exception as e:
        print(f"Error fetching CheerLights color name: {e}", file=sys.stderr)
        return 'white'

def get_current_hex():
    """Fetch just the current CheerLights hex color."""
    try:
        return cheerlights_api.get_current_hex()
    except Exception as e:
        print(f"Error fetching CheerLights hex color: {e}", file=sys.stderr)
        return '#FFFFFF'