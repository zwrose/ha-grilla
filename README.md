# ha-grilla

[![GitHub Release](https://img.shields.io/github/v/release/zwrose/ha-grilla?style=for-the-badge)](https://github.com/zwrose/ha-grilla/releases)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=for-the-badge)](LICENSE)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![CI](https://img.shields.io/github/actions/workflow/status/zwrose/ha-grilla/ci.yml?branch=main&style=for-the-badge)](https://github.com/zwrose/ha-grilla/actions/workflows/ci.yml)

Unofficial Home Assistant integration for Grilla Grills Alpha Connect smokers — live read-only telemetry via the Grilla cloud.

## Disclaimer

**ha-grilla is an unofficial, third-party integration. It is not affiliated with,
endorsed by, or supported by Grilla Grills or Fahrenheit Technologies, Inc.
"Grilla", "Alpha Connect", and any grill model names used here are trademarks of
their respective owner(s) and are used nominatively solely to identify the products
this integration works with. This integration is provided as-is and may stop
working at any time if the vendor changes their cloud service. Use is entirely at
your own risk, with no warranty of any kind.**

## What it does

ha-grilla signs in with your Grilla account and surfaces live grill telemetry in Home
Assistant. It is **read-only** — it does not send any
commands to the grill.

The integration is **cloud-push**: when the grill is on, updates arrive approximately
every few seconds. When the grill is off or the cloud connection drops, entities
become unavailable (except the connectivity binary sensor, which reflects the
disconnected state).

### Entities created per grill

**Sensors**

- Grill temperature
- Target grill temperature
- Probe temperature
- Target probe temperature
- Probe 2 temperature
- Target probe 2 temperature
- Status (off / igniting / running / hold / shutdown, etc.)
- Cook mode (smoke / grill / bake / etc.) — diagnostic
- Cook timer (finish timestamp, while a timer is active)

**Binary sensors**

- Grill connected (connectivity) — always available; reflects the cloud link state
- Problem — on when the grill reports an error code
- Probe connected — on when probe 1 is inserted
- Probe 2 connected — on when probe 2 is inserted

**Events**

- Alarm — fires on new error codes and on temperature-range breaches (rising edges only)

## Tested hardware

So far this integration has been verified against a **single grill**:

| Model | Controller | Firmware |
| --- | --- | --- |
| Grilla Silverbac 2.0 XL Built-In | Alpha Connect 2.0 | 1.0.70 |

Grilla's other connected grills use the same Alpha Connect cloud service, so they
**should** work too — but that hasn't been confirmed. **If you own a different
model, please give it a try and [open an issue](https://github.com/zwrose/ha-grilla/issues/new?template=compatibility_report.yml)
with your results** — your grill's model and firmware, what works, and anything
that looks wrong. Reports from other owners are how this list grows.

## Requirements

- Home Assistant **2025.11** or later
- A Grilla / Alpha Connect app account
- The grill already set up and paired in the Grilla app
- The [`aiogrilla`](https://github.com/zwrose/aiogrilla) library — Home Assistant installs it automatically when you add the integration; you do not need to install it yourself.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zwrose&repository=ha-grilla&category=integration)

Click the button above to add this repository to HACS, or add it manually:

1. In Home Assistant, open **HACS → Integrations → ⋮ → Custom repositories**.
2. Add `https://github.com/zwrose/ha-grilla` as a custom repository with category **Integration**.
3. Find "Grilla Grills" in HACS and click **Download**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & Services → Add Integration** and search for "Grilla Grills".
6. Enter your Grilla app **email** and **password**.

> Your password is used **once** to obtain a refresh token. Only the refresh token is
> stored in Home Assistant's configuration — the password itself is never saved or logged.

If your session expires, Home Assistant will prompt you to re-enter your password to
re-authenticate.

## Options

After setup, each grill's displayed model name can be customised:

**Settings → Devices & Services → Grilla Grills → Configure**

You can override the model name shown in the device registry for each grill (useful
when aiogrilla cannot resolve the model code reported by the hardware).

## Read-only scope

Version 1 of this integration is **monitoring only**. It exposes all available
telemetry but does not support sending commands (start/stop cook, temperature
setpoints, etc.). Write operations are a possible future addition but are
intentionally out of scope for the initial release.

## Privacy and security

This integration signs in with your Grilla account credentials and reads live telemetry
from Grilla's cloud service. No data is stored locally beyond a single
**refresh token**, which can be revoked by changing your Grilla account password.

See [SECURITY.md](SECURITY.md) for vulnerability reporting and sensitive-data guidance.

## Troubleshooting

Enable debug logging by adding the following to your `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.grilla: debug
    aiogrilla: debug
```

Restart Home Assistant, reproduce the issue, and download the logs from
**Settings → System → Logs**.

You can also download a **diagnostics bundle** from
**Settings → Devices & Services → Grilla Grills → ⋮ → Download diagnostics**.
Credentials and tokens are automatically redacted in the diagnostics output.

If you open a bug report, please attach the diagnostics bundle (after confirming no
sensitive data is present) rather than pasting raw logs.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md). This project uses
[Conventional Commits](https://www.conventionalcommits.org/) and release-please,
so commit messages drive versioning and the changelog.

## License

Apache-2.0. See [LICENSE](LICENSE).

The structure of this repository was adapted from the Home Assistant
[integration_blueprint](https://github.com/ludeeus/integration_blueprint) project
(MIT). See [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES) for the full attribution and
license text.
