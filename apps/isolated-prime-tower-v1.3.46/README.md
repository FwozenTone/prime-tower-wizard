# Prime Tower Wizard 1.3.46

Generates a material-isolated prime tower for toolchangers using Mainline OrcaSlicer or Snapmaker Orca. This is a standalone utility, not a slicer plugin.

## Updates in 1.3.46

Prime areas retire as each material’s remaining peak filament count decreases. Areas nearest the outer end walls are retained first; material groups remain contiguous. The initial footprint retains at least two areas, while upper layers may use one. Shell and ribs continue to the last filament-change layer.

## Updates in 1.3.45

Automatic reference slicing and the generated project disable Independent support layer height, matching the support-grid alignment required by native prime towers. This project-wide setting may round support Z gaps to the model layer grid. The original project remains unchanged; nozzle limits are retained. Manual reference exports must use aligned support layers.

## Updates in 1.3.44

Marks native prime tower disabling as an explicit process override so Orca GUI preset loading retains it.

## Updates in 1.3.43

Requires an explicit outer-wall filament selection for every selected plate before starting. The unselected prompt is red; filament choices and selected filaments are black.

## Updates in 1.3.42

Disables the slicer’s native prime tower through the supported project setting when generating a wizard tower. This applies to all plates in the output 3MF; the original project is unchanged.

## Updates in 1.3.41

The complete agreed [Tower Generation Rules](TOWER_GENERATION_RULES.md) are implemented. Each selected plate uses peak simultaneous filament counts by material type, with a minimum of two initial areas. Single-filament plates are skipped with an informational message. Choose the wall/rib filament explicitly for each plate; this selection resets with the other parameters for a new project. Non-wall material areas stop after their final use, while at least one wall-material area continues through the final filament-change layer. Additional areas retire as remaining peak demand falls. The CLI now requires reference G-code and an explicit frame slot for plates that need a tower.

## Updates in 1.3.40

Default slicer selection now matches version last used to save 3mf

The red heading reads “Select slicer version that matches the 3mf”. The wizard detects Mainline or Snapmaker from saved application metadata and selects the remembered executable for that branch. Manual override remains available; unidentified or ambiguous metadata prompts the user to check the selection. Detection selects the slicer branch, not a specific installed version number.

## Updates in 1.3.38

- Failed plates show their actual failure reason in a red highlighted box; other selected plates continue.
- Starting generation immediately clears the previous log, results, and errors, including reruns of the same project. Delayed status responses cannot restore stale output.
- Tower geometry and slicing behavior are unchanged from 1.3.36.

## Installation and workflow

See the [repository installation instructions](../../README.md#installation). On macOS, run `Install Prime Tower Wizard.command`; the installer prompts for the installation location and builds the app locally. Windows and Linux launchers are included.

Choose the original 3MF, slicer, and plates. Configure each tower, then generate. The wizard slices the original plates for reference, adds the towers, saves a new 3MF beside the original, and opens it in the selected slicer for placement review and final slicing. Existing tower plates cannot be selected. Generation does not perform a final audit or final slice.

The final filename adds `_tower_vN` without overwriting existing files. Working folders are removed unless the debugging option is selected.

## Current tower design

- Up to 12 used filament slots, mapped directly to T0–T11. Area count follows peak per-layer use by material type, not the total number of used slots.
- Separate vertical sections for different materials; matching filaments share areas across layers. Every still-needed area is maintained, including gaps in that material’s use. Finished non-wall materials stop growing.
- Compact rounded cells and same-material X-direction cross-ribs, with solid bases. Cross-rib volume counts toward the requested minimum priming volume.
- Frame, outer ribs, brim, and reinforcing gussets use the selected frame filament. Frame connections do not intrude into the internal priming sections.
- Tower-only settings disable scarf seams, use normal-flow extrusion starts, and suppress tiny inner-wall and infill paths at cross-rib junctions.
- Tower width, rib size, brim width, brim thickness, and minimum priming volume are per-plate settings. Defaults: 30 mm, 5 mm, 5 mm, 0.6 mm, and 5 mm³. Brim thickness range: 0.5–1.5 mm.
- Brim is built into the geometry with zero gap. Slicer brim generation is disabled for the tower only; original model brim settings remain unchanged.
- Gusset run follows brim width; height is up to twice brim width, limited by tower height.
- Tower height and variable layer boundaries follow the reference pickup schedule. Regenerate after changing geometry, tools, or layer heights.
- Fixed initial placement includes an additional 5 mm inward offset in X and Y. There is no automatic rotation or collision-search placement. Move the complete assembly in XY in Orca as needed.

Retain printing by layer, object-list order, tower-first ordering, and the disabled native prime tower. Do not split, scale, rotate, or rename the assembly.

## Validation and limits

Tested with Mainline OrcaSlicer 2.5.1 and Snapmaker Orca 2.4.1 on macOS. Tests covered 20/30 mm widths and 5/15 mm³ requested volumes. Eight sliced fixtures passed checks for normal-flow starts, no scarf ramps, no exactly repeated extrusion segments, sufficient volume, and gentle priming-path turns. Combined model/tower fixtures without separate model brims passed 83 pickup checks per slicer.

The optional CLI audit additionally checks material assignments, layer coverage, tower visits and volume before model/support extrusion, sharp priming reversals, and repeated paths. Firmware macro behavior is outside its scope. It still rejects model-brim-first initial priming; this known conservative audit limitation does not affect generation.

These checks do not guarantee blob-free printing, collision clearance, or tall-tower stability on every printer. Physical validation remains necessary. The original printer's startup, pickup macros, temperatures, and retraction settings are preserved.

## Previous version

[Version 1.3.38](../isolated-prime-tower-v1.3.38/) and [version 1.3.25](../isolated-prime-tower-v1.3.25/) remain available for rollback. Close the running wizard before switching versions.

## License

GPL-3.0-only; see the repository [LICENSE](../../LICENSE). Provided as is, without warranty, subject to the license's warranty and liability provisions.
