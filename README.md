# Tiko Integration for Home Assistant

This is a custom integration for Home Assistant that allows you to control your Tiko heating system.

## Features

- Control room temperatures
- View current temperatures
- Set heating modes (Normal, Off, Frost Protection, Away)
- Automatic token management to avoid rate limits
- Full French translation

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots menu in the top right
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/CaptainIgl00/hacs-tiko`
6. Select category: "Integration"
7. Click "Add"
8. Click on "+ Explore & Download Repositories"
9. Search for "Tiko"
10. Click "Download"
11. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/tiko` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings -> Devices & Services
2. Click "+ Add Integration"
3. Search for "Tiko"
4. Enter your Tiko credentials (email and password)

## Usage

After configuration, the integration will create:
- A climate entity for each room
- Temperature sensors

You can control your heating system through:
- The Home Assistant UI
- Automations
- Scripts
- The REST API

## Support

If you have any issues or feature requests, please:
1. Search existing [issues](https://github.com/CaptainIgl00/hacs-tiko/issues)
2. Create a new issue if needed

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.