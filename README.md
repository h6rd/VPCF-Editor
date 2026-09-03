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
- Batch recoloring in 1, 2, 3 colors while preserving original saturation and brightness
- Texture recolor
- Automatic compilation of source assets
- Packaging of compiled files into a ready-to-use vpk

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

https://github.com/user-attachments/assets/0979bd3d-1fc0-4c9d-88ec-cafe7230b744

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
