# VPCF Editor

A tool for recoloring particle effects, compiling them, and packaging the result into a VPK archive.

---

## Download

| Platform | Link |
| --- | --- |
| Windows | [VPCF-Editor-Win.zip](https://github.com/h6rd/VPCF-Editor/releases/latest/download/VPCF-Editor-Win.zip) |

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
