# VPCF Editor

A tool for recoloring particle effects, compiling them, and packaging the result into a VPK archive.

---

## Download

| Platform | Link |
| --- | --- |
| Windows | [VPCF-Editor-Win.zip](https://github.com/h6rd/VPCF-Editor/releases/latest/download/VPCF-Editor-Win.zip) |
| Linux [`guide`](https://github.com/h6rd/VPCF-Editor#linux-usage) | [VPCF-Editor-Linux.zip](https://github.com/h6rd/VPCF-Editor/releases/latest/download/VPCF-Editor-Linux.zip) |

---

## Features

- Manual color editing for individual effect files
- Batch recolor to a single color while preserving original saturation and brightness
- Batch recolor to two random colors while preserving original saturation and brightness
- Automatic compilation of source assets
- Packaging of compiled files into a ready-to-use vpk

---

## Current Limitations

vtex (png) editing is not supported at this time.  
As a result, some effects may still show original details if they rely on vtex sprites.

---

## How to Use

1. Place your source effect files (vpcf) into the input folder next to the program.
2. Launch VPCF Editor.
3. Choose the desired color editing mode:
   - Manual per-file editing
   - Batch recolor to one color
   - Batch recolor to two random colors
4. The tool will process the files, compile them, and pack everything into a vpk.

Compiled `_c` files and the final VPK will appear in the compiled folder.

https://github.com/user-attachments/assets/cfecb8f2-1f02-4a41-98e7-f323fd8e4f8d


## Linux Usage

1. Install Wine
2. Open Steam, right-click Dota 2, go to `Properties` > `Compatibility` and select `Proton Experimental`. Wait for it to download
3. Restart Steam. `Right-click Dota 2` -> `DLC` and enable `Workshop Tools`
4. Once installed, run the VPCF-Editor script. After it copies the necessary dependency files, you can disable Proton compatibility in Steam for Dota 2 to return it to its normal state
The VPCF-Editor will now continue to work without requiring active Workshop Tools compatibility

### The method for using workshop tools on Linux was borrowed from [**Minify**](https://github.com/Egezenn/dota2-minify), thanks!


## TODO
- [x] vtex editor
- [ ] gradient recolor
