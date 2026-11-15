# Prime Tower Wizard 1.3.25

The tower starts at the front corner, an additional 5 mm inward in X and Y. It is never automatically rotated or searched around other objects. Adjust placement in Orca as needed.

Snapmaker reference slicing now accepts Mainline-saved projects using its supported `--allow-newer-file` option. Mainline slicing is unchanged.

Choose your 3MF, plates, and tower settings, then select **Generate selected towers**. The wizard reads an initial reference slice to determine materials and layer heights, adds the towers and their combined brims, and opens the saved 3MF in your selected Orca application. Review placement, slice, and print in Orca. The wizard no longer performs a final slice or audit, even if a previous session saved that option.

Mainline and Snapmaker Orca remain selectable. Each plate's Outer brim width controls its built-in brim, assigned to the frame filament with zero gap. Slicer brim is disabled for the tower only. Previous versions remain available separately.

Both Mainline and Snapmaker Orca now use a generated brim, part of the same movable tower assembly and assigned to its outer wall/ribs filament. Each plate's **Outer brim width** controls the outward offset; zero omits it. The brim is one first layer thick and touches the tower with no gap. Slicer brim generation is disabled only for the tower. Original model brim settings are preserved.

The first nonzero-brim generation downloads the Shapely geometry library and its dependencies into a private user cache (internet access and Python with pip required). Later runs reuse it; no global Python packages are changed.

Select Mainline or Snapmaker in the Slicer panel; each remembers its own application location. Snapmaker 2.4.1 was tested on macOS. Its factory startup purge line still triggers the strict pickup audit; machine startup commands are not modified. No physical print validation has been performed.

Previous workflow notes follow.

# Isolated Prime Tower — Orca 2.4.2 companion prototype

This is a working project generator plus a conservative G-code auditor, **not an installable native Orca plugin**. Orca 2.4.2 has no native Python plugin system. This package does not replace Orca's internal tool-change scheduler and has not yet been validated with your StealthChanger project or printed on hardware.

## What it generates

- One continuous serpentine section for each actually used slot, up to twelve tools (T0–T11). PLA, PETG, ASA, ABS, nylon, PPS and dedicated support materials can have separate sections.
- Configurable internal rectangle width (default 30 mm), rounded outer rib size (default 25 mm), and minimum purge volume per pickup (default 5 mm³).
- Section depth increases with the requested volume and the thinnest reference layer. The final G-code audit measures actual volume; this is a minimum, not an exact-volume purge.
- A solid bottom up to 1 mm thick, 0.8 mm serpentine walls, and no top skin. Ribs and connections move outward as needed to avoid overlapping opposing ribs.
- Automatic rigid frame material selection, with a manual slot override. Preference: PPS, PEEK, PEI, PC, ASA, ABS, PETG, PLA, nylon. This is a deterministic starting preference, not a measured strength rating. Dedicated support and flexible materials cannot own the frame.
- Support material/tool selection from the project's filament slots, or detection from reference support paths. Selection must match the original support settings; change those in Orca before exporting if needed.
- Idle sections are maintained by an active tool with the identical material type. If that type is absent, one tool of that type maintains its sections. ABS and ASA, and distinct blends, remain separate. Plain NYLON and PA are treated as synonyms.
- With reference G-code, height ends at the last layer with a tool pickup followed by model/support extrusion. No extra 1 mm is added. The audit rejects a changed final schedule that needs priming beyond this height.
- Variable tower layers match the reference layer boundaries via an Orca height profile. Original objects' profiles are preserved. Layer intervals must satisfy every tower tool's configured limits; incompatible independent layer grids are rejected.

The project provides filament material types. Only tools actually extruding model/support paths create sections; unused loaded slots, startup-only tools, and tools used only in the original prime tower or brim do not. Painted models need no manual filament list when reference G-code is supplied. Filament colors retain individual sections, with same-type donors allowed.

The generator copies the original project, preserves the original model meshes and machine/tool-change templates, disables the normal prime tower and flush-into-object options, and sets **By layer / As object list**, with **the generated tower first on each target plate** in the build and object lists. It does not synthesize new StealthChanger commands or temperatures.

## Guided window (macOS, Windows, Linux)

Double-click **Start Prime Tower Wizard.command**, or run `python3 isolated_prime_tower.py gui`. A local browser window opens; keep its Terminal launcher running. Python 3.10+ is required, but Tk and additional packages are not.

1. Choose a 3MF and select one or more plates. Each selected plate has independent width, rib size, brim width, minimum purge, and outer-wall/rib filament settings. Defaults are 30 mm, 5 mm, 5 mm, 5 mm³, and Automatic, respectively. Choosing a new project resets these settings. The wizard no longer asks for a support-tool selection. Plates with an existing generated tower are shown but disabled. All other plates are selectable, including mixed-material plates without supports. The working-folder location can be changed; the final project is always saved beside the original.
2. Click **Slice & build selected towers**. Only selected plates are sliced. Each tower uses its own plate’s reference G-code and is added only to that plate. The result is one combined project beside the original, named `something_tower_v1.3mf` (or the next available version number), without overwriting existing files. A failure on one plate does not stop the remaining plates; the results identify successes and failures. Post-tower slicing and auditing are skipped by default; select **Run post-tower slicing and validation** when you want the full audit. Each run uses a working folder. After the final project is saved, the working folder and all sidecars, logs, and reports are removed. Only the generated 3MF remains. Enable **Keep working folder for debugging** to retain the working files; this option is off by default. Interrupted or failed saves retain working files for recovery. Other plates are retained. The original is not overwritten.
3. A passing result can open the tower project in Orca automatically. A failed audit is shown as a failure, never as verified output.

For a single selected plate, if command-line slicing fails, the **Guided manual export** controls appear immediately below the active Slice reference indicator. Export the selected original plate in Orca, choose that reference G-code and build the tower. The final-export manual validation controls are no longer shown. Plate selection is explicit; the utility does not guess plate identity from filenames.

Automatic slicing is implemented but **not yet validated end to end with the installed Orca 2.4.2**: the command-line test aborts in this environment. Logs are saved and the manual path remains available. Opening the result in Orca is for review; the utility never sends a print command. If you move the tower after a passing audit, save, reslice and audit again.

## Run

Requires Python 3.10 or later. Generated brims use Shapely, prepared automatically on first use. Keep this folder somewhere permanent.

For file dialogs:

```text
python3 isolated_prime_tower.py gui
```

Or generate directly from an unsliced, saved Orca project:

```text
python3 isolated_prime_tower.py generate "original.3mf" --output "with_tower.3mf"
```

**For same-material donors, minimum height, and variable layers**, first export the original reference print as plain G-code with feature comments and arc fitting disabled, then use:

```text
python3 isolated_prime_tower.py generate "original.3mf" --reference-gcode "reference.gcode" --output "with_tower.3mf"
```

The original project and reference export must describe the same print and settings. The generator builds closed material spans inside one movable multipart tower. Do not change the layer heights, materials, plate ordering or source model afterward; regenerate instead. Moving the whole tower in XY is supported, followed by saving, reslicing and auditing.

CLI controls are `--width 30 --rib-size 5 --purge-volume 5`, with rib sizes from 5–100 mm and optional `--support-slot N` and `--frame-slot N` (1-based slots). Without reference G-code the legacy fixed-tool mode retains model height and cannot infer pickup height or variable layers; the wizard always uses reference G-code.

Without reference G-code, if filament use cannot be inferred (for example material painting), specify the used **1-based Orca filament slots**, not zero-based tool numbers:

```text
python3 isolated_prime_tower.py generate "original.3mf" --output "with_tower.3mf" --filaments 1,2,6
```

Open the new copy **as a project** in Orca, retaining its settings. The tower appears as one **IPT_ASSEMBLY** object. Select the parent object to move all its material parts together in XY. Do not split the object, move individual parts, rename it, rotate it or scale it. After moving it, save the 3MF at the same filename, slice and export again, then audit that saved project and matching G-code. The auditor reads the assembly's saved position and adjusts section coordinates. Check clearance from other objects and the bed edges after moving; the audit is not collision simulation. `--origin X Y` still specifies the central rectangle's lower-left corner at generation, with ribs projecting beyond it.

Slice and export plain `.gcode`, with arc fitting off. Then check it:

```text
python3 isolated_prime_tower.py audit --project "with_tower.3mf" "exported.gcode"
```

For Orca's existing **Post-processing scripts** setting, the audit can be invoked automatically. Enter the following as one command, substituting permanent absolute paths. Orca appends the exported G-code filename:

```text
"/absolute/path/to/python3" "/absolute/path/to/isolated_prime_tower.py" audit --project "/absolute/path/to/with_tower.3mf"
```

The audit never changes G-code. A nonzero exit signals failure. Recheck how your Orca export/upload workflow handles a failed post-processor before relying on it to block a print.

## What the audit checks

- Literal `T0` through `T11` tool selections, with Orca slot N assumed to map to T(N−1).
- After each change of selected tool (including initial selection), the first explicit XY destination and first extrusion path must be within the tower. Z-only lifts, temperature waits and extrusion-only retraction moves may precede that visit. If object labels are present, a reference object must not be selected before tower extrusion. No particular filament order is required.
- Pickups with no following tower visit/extrusion fail, including at the end of the file. Moves internal to firmware pickup/drop-off macros remain outside this check. Drop-off may occur directly from the reference object.
- Matching scheduled owners in each section, and the assigned frame tool for the exterior. Material types in the saved project must still match generation.
- All assigned sections printed on every reported layer through the tower's height.
- The saved minimum purge volume after each pickup, using configured filament diameters. New projects also check maintenance-only pickups before drop-off and at end of file. `--min-volume` can explicitly override the audit threshold.
- Later pickups on the same layer that do not receive another prime are rejected.

**A generated project is not proof of correct priming order.** Ordinary objects are not guaranteed to be revisited on every pickup, especially when a filament is used again later on the same layer or when support and object paths are scheduled separately. The audit reports these failures; it cannot fix them. If the actual StealthChanger project fails, completing the replacement requires a scheduler change or a printer-specific G-code integration.

## Current limits

Rectangular-bed, millimeter Orca projects only. For multi-plate projects, select a plate in the wizard or add `--plate N` to generation. Plate coordinates follow Orca 2.4.2’s standard 20% plate spacing; keep the plate count/order unchanged after generation. Generic multi-toolhead mode must be enabled (`Single Extruder Multi Material` off). The auditor accepts absolute XY, either extrusion mode, configured filament diameters and standard `; Z:` layer comments. Arc moves, relative XY, missing Tn selections and unsupported setups are rejected. Firmware-side macro motions, collision clearance, bed adhesion, stable nozzle flow and a truly uninterrupted sliced extrusion path are not simulated.

Generation may create intersections between closed component solids, as the approved v8 STLs do; Orca must union these during slicing. Inspect the first layer and normal layers in Preview. The reference height calculation excludes explicitly tagged modifier components, but unusual project structures still need checking.

## Validation performed

Automated tests cover up to twelve sections, mixed-material donors, support/frame selection, variable-height profile sampling and preservation, last-pickup height, configurable geometry and volume, material separation, insufficient priming, changed final layer grids, frame coverage, original project preservation, and the existing assembly, placement and wizard workflows. These are synthetic tests; the new profiles and material spans still require an actual Orca 2.4.2 slice and audit.
The local Orca 2.4.2 command-line executable reported its version and supported plate-slicing flags, but aborted on the attempted slicing integration check. The existing user-exported StealthChanger G-code passed the audit; a successful automatic two-pass slice or physical print is not claimed.

Run tests:

```text
python3 -m unittest discover -s . -v
```

Official references:
- https://github.com/OrcaSlicer/OrcaSlicer/wiki/plugins_getting_started
- https://github.com/OrcaSlicer/OrcaSlicer/blob/v2.4.2/src/libslic3r/PrintConfig.cpp
- https://github.com/OrcaSlicer/OrcaSlicer/blob/v2.4.2/src/libslic3r/Format/bbs_3mf.cpp

## Audit metadata after saving in Orca

The command-line generator also writes `with_tower.3mf.ipt.json` beside its output project. The wizard keeps metadata embedded in the final 3MF and does not retain an external sidecar unless you keep its working folder for debugging. Keep that file with its matching project and preserve its filename. If Orca removes the embedded manifest on save, the audit uses this companion file. It records the original geometry and assignments; the audit derives XY translation from the saved IPT_ASSEMBLY object. Regenerate after changes beyond moving the whole assembly in XY. When saving under a new name, copy the matching companion file to the new `.3mf.ipt.json` filename. Existing projects without either metadata copy must be regenerated from the original reference project, using a new output filename.

## Choose an installation folder and add to Dock

Run `Install Prime Tower Wizard.command` in Terminal. It prompts in Terminal for a parent folder (default `~/Applications`), creates `Tower_Wizard` inside it, replaces the previous installation after confirmation, creates Prime Tower Wizard.app, adds it to the Dock if absent, and opens it. Existing running wizard sessions must be closed separately; use the newly opened window. The Dock is restarted to display the shortcut.

New towers default to a user-adjustable 5 mm outer-only brim with a zero object gap; automatic placement reserves the selected space. The accepted range is 0–100 mm, and the selection is retained through guided Step 3 recovery. The audit permits the assigned frame tool’s brim paths on the first layer and still rejects brim extrusion through material sections. Check the brim in Orca Preview: actual brim generation and filament assignment remain slicer-dependent. Existing generated projects need regeneration to receive these brim settings. Progress now displays elapsed step/total time, an animated activity indicator, and available live Orca log output.

## Choose a different Orca installation

Expand **Orca location**, choose or paste the app/executable path, and click **Save Orca location**. The chosen executable is used for both slicing passes and for opening the result. Generation also saves the selected location automatically. No shell arguments belong in this field.

- macOS: choose an Orca `.app` bundle anywhere, or its executable. The bundle's configured executable name is read from Info.plist. Start with `Start Prime Tower Wizard.command`.
- Windows: choose the installed `orca-slicer.exe`. Start with `Start Prime Tower Wizard.bat` (Python 3.10+ required).
- Linux: choose an Orca executable or `.AppImage`, with execute permission enabled. Start with `sh start-prime-tower-wizard.sh` (Python 3.10+ required). The AppImage's system dependencies still need to be installed.

Settings are stored per user under macOS `~/Library/Application Support/PrimeTowerWizard`, Windows `%APPDATA%/PrimeTowerWizard`, or Linux `$XDG_CONFIG_HOME/PrimeTowerWizard` (default `~/.config/PrimeTowerWizard`). The existing installer and Dock setup remain macOS-only; on Windows/Linux extract the ZIP to a writable folder and use the platform launcher. CLI compatibility targets Orca 2.4.2; this does not establish compatibility with every Orca release. Windows/Linux path and launch behavior has automated coverage but has not been exercised on those operating systems with Orca installed.

The package includes an original castle-tower icon in PNG, macOS ICNS, and Windows ICO formats. The macOS installer installs the icon into the app bundle and refreshes the Dock on both first installation and updates. The wizard also uses it as its browser icon.

The installer accepts paths containing spaces. Enter `q` to cancel before any installation changes. Replacing an installation removes the previous installed copy after confirmation; no installed-version backup is retained.

Version 1.3.6 opens the browser independently of the local server, with a bounded macOS browser-launch call. If opening fails, the local URL is recorded in `wizard.log` in the installation folder for manual access.

Version 1.3.6 uses a native stay-open macOS launcher so the Dock can track the application normally. Click its Dock icon to reopen the browser page. Quit the app from the Dock to stop its wizard server; closing the browser tab alone leaves it running. Force Quit bypasses normal server cleanup.

Version 1.3.9 adds independent towers on multiple plates and per-plate audit metadata. To audit an individual plate from a combined project, add `--plate N` to the audit command. For a failed batch plate, select just that plate to retry with guided manual export; use the combined project to retain successfully generated towers. The existing progressive interface remains: progress appears only after processing starts, and guided reference export appears only after automatic reference slicing fails. Selecting a different original 3MF resets the prior flow. Step indicators, manual final-export validation controls, and the troubleshooting log were removed; optional automatic post-tower validation remains available. The completed-project message embeds a green **Open project with generated tower in Orca** button. After automatic opening it is presented as an optional recovery action; otherwise it is the primary opening action.

When automatic opening is disabled, the green Open button follows the completion sentence directly without additional instructional text around it.

Outer ribs default to 5 mm for a fresh job. If automatic slicing fails, guided reference export retains and uses the rib size and all other options selected for that current job.

After successful completion, **Generate a tower for another project** resets the workflow and opens the source picker while preserving the most recent options. A customized output folder is retained for another project in the same source folder; choosing a project from a different folder defaults output to that new folder.

File selection is type-limited: the Original 3MF picker shows only `.3mf` files, and guided reference/final G-code selection accepts only `.gcode` files. Manually entered paths receive the same validation.

The slicer’s built-in prime tower is disabled with a plate-level override on the selected plate containing `IPT_ASSEMBLY`. The project-wide setting and all other plates retain their original prime-tower configuration.

The generator preserves every original object/component transform, including intentional negative Z placement used to flatten a model against the build plate. Automatic slicing is attempted for every project, including painted multicolor projects. Guided manual export is offered only after command-line slicing actually fails or crashes; macOS then reuses Orca if it is running or launches it as needed. The interrupted job retains every form selection, even if the wizard page is reopened, and the reference G-code picker starts in the original 3MF folder.

When guided recovery is needed, the wizard scrolls to and focuses the Reference G-code field and highlights its build action. Building from that reference export automatically opens the generated tower 3MF when the original Open-after setting was selected. Final-export verification remains optional.

The Original 3MF picker remembers the folder from the previous successful setup and starts there on the next use. It does not preselect the prior project file.

Generation logs are collapsed under “Generation log (troubleshooting)” by default; progress, next steps and actionable failures remain visible.

The Mac installer keeps the name Prime Tower Wizard.app and uses the stable Tower_Wizard installation folder. If it finds an existing wizard installation in the selected parent, it asks in Terminal before replacing it. Answering no leaves it unchanged. Approved replacements remove older installations once the new app is ready and update their Dock shortcuts. No installed-version backups are retained. Quit the running wizard before upgrading.

The default application path is `~/Applications/Tower_Wizard/Prime Tower Wizard.app` in your home folder. This is separate from the system `/Applications` folder. In Finder, use Go → Go to Folder to open the installation folder you selected.
