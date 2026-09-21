# Phase 4 -- Prior restore plan

## Identity that must match

- Model: `SM-T280`, never SM-T285.
- Codename: `gtexswifi`.
- Observed PDA/bootloader: `T280XXU0AQJ1`.
- Observed CSC: `TPA`; firmware CSC `T280UVS0AQJ1`.

## Mandatory requirements

1. Obtain a complete SM-T280 stock firmware compatible with the region/CSC and with no bootloader downgrade.
2. Keep the package's original name, size, SHA-256 and provenance.
3. Inspect the archive without flashing it and confirm it contains the expected partitions.
4. Have the Samsung USB driver and a compatible restore tool on Windows.
5. Confirm the laptop stays powered and that the USB cable/port are stable.
6. Prepare stop criteria and the exact restore order before entering Download Mode.

## Official-source status

The official Samsung support page confirms the SM-T280 model and offers manuals/USB driver, but does not currently publish a downloadable firmware package in its software section. Samsung documents Smart Switch Emergency Software Recovery for compatible recoveries, with a possible factory reset; it still needs confirming that the service recognizes this model and CSC.

The automated query to the Samsung firmware service for `SM-T280/TPA` currently
returns `403 Model or region not found`. An archived copy with exact identity
and published MD5 `a0bf55d45cfcaf9197055bdd7a670a62` was located, but its
download must be completed with a non-private browser and verified via
`sm-t280-phase4/scripts/verify-stock-package.ps1`.

## Stop criteria

- The shown identification is not exactly SM-T280.
- The restore package belongs to another variant or bootloader.
- The battery is not sufficiently charged or the USB connection is unstable.
- No verifiable path back to stock exists.
- An image exceeds its partition.
- The tool proposes repartitioning, wiping or upgrading the bootloader without specific approval.

It does not yet contain flash commands: they will be added only after closing the offline gate and obtaining explicit authorization.
