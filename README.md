# PyCAPGE  
**Python Classic Adventure Point-and-Click Game Engine**

<div align="center">
  <img src="tutorial/pycapge_logo_color.png" alt="PyCAPGE logo" width="400">
  <br><br>
  <a href="https://github.com/tijuinem/pycapge/actions"><img src="https://img.shields.io/github/actions/workflow/status/tijuinem/pycapge/python-app.yml?style=flat-square&label=Tests" alt="Tests Status"></a> <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square" alt="License GPLv3"></a> <img src="https://img.shields.io/badge/python-3.8%2B-blue?style=flat-square" alt="Python 3.8+"> <a href="https://doi.org/10.5281/zenodo.18183594"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.18183594.svg" alt="DOI"></a>
</div>

---

## Summary

**PyCAPGE** is an open-source game engine for creating classic point-and-click graphic adventure games using Python.

Unlike commercial engines that rely heavily on visual editors, PyCAPGE exposes its internal logic directly in code.

Designed for education, research, and digital preservation.

---

## Screenshots

<table align="center">
  <tr>
    <td><img src="tutorial/pyvapge%20panoramic%20street.jpg" width="400" alt="Panoramic Street"></td>
    <td><img src="tutorial/pyvapge%20parallax%20exampleu.jpg" width="400" alt="Parallax Example"></td>
  </tr>
  <tr>
    <td><img src="tutorial/pyvapge%20peace%20avenue.jpg" width="400" alt="Peace Avenue"></td>
    <td><img src="tutorial/pyvapge%20tawn%20hall.jpg" width="400" alt="Town Hall"></td>
  </tr>
</table>

---

## Project Structure

```
(root)
│
├── __pycache__/
├── backgrounds/
├── cursor/
├── fonts/
├── games/
├── hotspots/
├── items/
├── languages/
├── objects/
├── snd/
├── tutorial/
├── tests/
├── paper/
│
├── engine/
│   ├── __init__.py
│   ├── classes.py
│   └── resources.py
│
├── scenes/
│   ├── __init__.py
│   ├── scenes.py
│   ├── intro.py
│   ├── ending.py
│   └── variables.py
│
├── main.py
└── config.py
```

---

## Controls & Usage

### For Players

- **F1** – Help / View controls
- **F2** – Menu (Save / Load / Options)
- **F11** – Toggle fullscreen
- **Mouse Left Click** – Walk / Interact
- **Double Click** – Fast walk
- **Dialogue**
  - Click: Fast-forward
  - ESC: Skip

### For Developers

- **F3** – Toggle debug mode (hitboxes)
- **F4** – Show walkable areas (navigation mesh)

## Requirements

- Python 3.8+
- Pygame
- PyYAML

---

## Quick Installation

```bash
git clone https://github.com/tijuinem/pycapge.git
cd pycapge
pip install pygame pyyaml
python main.py
```

---

## Citation

```bibtex
@software{pycapge2025,
  author    = {Garbayo, Eduardo},
  title     = {PyCAPGE: A Python Engine for Classic Adventure Game Education},
  year      = {2025},
  publisher = {GitHub},
  journal   = {GitHub repository},
  url       = {https://github.com/tijuinem/pycapge}
}
```

---


## License

GPLv3 © 2025 Eduardo Garbayo "Garba" www.eduardogarbayo.com

### Games Created With PyCAPGE

Any game created using PyCAPGE is considered a **derivative work** of the engine. Therefore:

- Games **must** be released under **GPL-3.0-or-later**
- The **complete source code** must be made available
- **Closed-source or proprietary games are not permitted**

See the `LICENSE` file for full details.
