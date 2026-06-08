"""Constants for the Grilla integration."""

from homeassistant.const import Platform

DOMAIN = "grilla"
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.EVENT]

CONF_REFRESH_TOKEN = "refresh_token"
CONF_EMAIL = "email"
CONF_MODELS = "models"  # options: {grill_id: friendly_model_name}

# Display names for the model picker (app-connected Grilla models). The picker also
# accepts a free-text custom value, so this list need not be exhaustive.
GRILLA_MODELS = [
    "Grilla",
    "Silverbac",
    "Silverbac Built-In",
    "Silverbac 2.0",
    "Silverbac 2.0 Built-In",
    "Silverbac XL",
    "Silverbac 2.0 XL",
    "Silverbac 2.0 XL Built-In",
    "Chimp",
    "Chimp 2.0",
    "Kong",
    "Mammoth",
    "Pie-Ro",
]
