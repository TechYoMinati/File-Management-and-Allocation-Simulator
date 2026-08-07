# File-Management-and-Allocation-Simulator
### OS Diploma Project (File-Management-&-Allocation-Simulator)

> 👀👇🖼️ **GUI Demo — how it looks shown below**
<img width="1919" height="1020" alt="Screenshot 2026-08-07 174604" src="https://github.com/user-attachments/assets/2ea38f32-fdcf-4cf2-bb73-64531828e734" />
<img width="1919" height="1018" alt="Screenshot 2026-08-07 174756" src="https://github.com/user-attachments/assets/6c35adde-d81c-4a48-83ac-e42e3ea15724" />

## 🗂️ File Management Simulator + File Allocation Simulator

An **Operating Systems educational project** — a GUI-based *"virtual disk"* that lets you create, edit and delete real files, and watch, **block-by-block**, how an Operating System physically stores them on disk using the three classic file allocation methods: **Contiguous**, **Linked**, and **Indexed** allocation.

**Language:** Python 3 · **GUI:** Tkinter (100% built-in, zero external dependencies) · **Domain:** Operating Systems — File System Implementation

---

## 📌 Table of Contents
- [What Is This Project? (The Overall Goal)](#-what-is-this-project-the-overall-goal)
- [Why Was It Built?](#-why-was-it-built)
- [What's New in v1.1.0](#-whats-new-in-v110)
- [Academic References & Where the Logic Comes From](#-academic-references--where-the-logic-comes-from)
- [The Core OS Concepts Implemented](#-the-core-os-concepts-implemented)
- [The Three Allocation Algorithms (Explained With Math)](#-the-three-allocation-algorithms-explained-with-math)
- [Reading the "Files on Disk" Panel (Bytes · Blocks · Length)](#-reading-the-files-on-disk-panel-bytes--blocks--length)
- [The Directory Entry, per Method](#-the-directory-entry-per-method)
- [The Activity Log Now Explains "Why This Many Blocks"](#-the-activity-log-now-explains-why-this-many-blocks)
- [How the Code Is Architected (Phase by Phase)](#-how-the-code-is-architected-phase-by-phase)
- [Every Feature in the GUI & What It Teaches](#-every-feature-in-the-gui--what-it-teaches)
- [The Extra Engineering: Sound Engine & Cursor FX](#-the-extra-engineering-sound-engine--cursor-fx)
- [How to Run It](#-how-to-run-it)
- [How to Build the Windows .EXE](#-how-to-build-the-windows-exe)
- [Explaining This Project in a Viva / To a Professor](#-explaining-this-project-in-a-viva--to-a-professor)

---

## 🎯 What Is This Project? (The Overall Goal)

When you save a file on your computer, the Operating System does **not** store it as one continuous piece. The disk is divided into small fixed-size units called **blocks**, and the OS must decide *which* blocks your file will occupy. This decision is made by a **file allocation method** — one of the most important topics in any Operating Systems course.

**The problem:** this process is completely invisible to a normal user. Students learn these algorithms only from static textbook diagrams.

**This simulator makes the invisible visible.** It behaves like a tiny real file system with a graphical file manager on top:

- You create a real virtual file (e.g. `report.txt`) and type actual content into it.
- A **live size meter** converts your typed bytes into required disk blocks in real time, as you type — and now shows the exact `ceil(size / payload)` formula it used.
- When you hit **Save**, you choose one of the 3 classic allocation algorithms, and the app animates the blocks being occupied one by one on a visual 64-block disk grid.
- You can **open, edit, delete** files like a normal file manager — and watch blocks get freed and fragmentation appear.
- A **Compare mode** shows how the same file would be stored by all three algorithms side by side.

> In one sentence: it is a **fully working miniature file system with X-ray vision**, built so that anyone — technical or not — can see what an OS does under the hood every time they press Ctrl+S.

---

## 💡 Why Was It Built?

- **Educational gap** — File allocation (Contiguous / Linked / Indexed) is taught theoretically in every OS syllabus, but students rarely get to *interact* with it. Static diagrams can't show fragmentation forming, blocks scattering, or an allocation failing in real time.
- **To connect theory to reality** — The simulator doesn't fake anything. It computes real byte sizes (UTF-8 encoded), real block counts, real pointer overhead, and real failure conditions (external fragmentation, index-block limits) exactly as described in OS textbooks.
- **To be demo-ready** — It runs anywhere Python runs, with zero pip installs (Tkinter ships with Python), and can be packaged into a single Windows `.exe` for lab demonstrations.

---

## 🆕 What's New in v1.1.0

This release aligns the simulator 1:1 with the standard textbook figures **4.11 (Contiguous)**, **4.12 (Linked)** and **4.13 (Indexed)** — the directory-entry diagrams and the "how many blocks" reasoning every OS course expects.

1. **New `Length` column in the *Files on Disk* panel.** The table now shows **Bytes · Blocks · Length · Method**. `Blocks` = total blocks physically occupied on disk (index block included); `Length` = the file's length in **data blocks** — the exact *"Length"* field the directory keeps in Figures 4.11 / 4.12.
2. **Live *Directory entry* preview.** Selecting a file shows precisely what the OS stores for it — and the fields correctly differ per method (Start + Length / Start + Last + chain / Index Block + table), mirroring the "directory" boxes drawn in the figures.
3. **The Activity Log now explains the arithmetic.** On every save it prints a short, examiner-friendly reason for *how many blocks* were occupied — e.g. `ceil(100 / 32) = 4 blocks`, plus the `+1 index block` rule for Indexed and the 4-byte next-pointer overhead for Linked.
4. **Upgraded size meter.** The live meter now displays the actual `ceil(size / payload)` formula and, for Indexed, spells out `+ 1 index block = N total`.
5. **Bigger Activity Log panel** so the full multi-line reasoning is visible without scrolling.

---

## 📚 Academic References & Where the Logic Comes From

The allocation logic is **not invented** for this project — it is a faithful implementation of the standard algorithms defined in classic Operating Systems literature.

| Source | What was taken from it |
| --- | --- |
| **Bharat V. Chawda — *Operating System Concepts*** (the "ATUL PRAKASHAN Book"), *FILE AND DISK MANAGEMENT* chapter | The exact definitions and behavior of Contiguous, Linked, and Indexed allocation: directory metadata per method (start+length / start+last / index block), pointer overhead in linked blocks, single-level index-block capacity limits, and external fragmentation behavior. |
| **Standard OS curriculum (Diploma/Degree CE syllabus)** — File Systems unit | Disk blocks, block size, free-space management, the directory as a metadata table, and internal vs. external fragmentation. The v1.1.0 *Length* column and directory-entry preview map directly onto the syllabus figures 4.11–4.13. |
| **Real file system behavior (FAT, Unix inodes)** | Linked allocation mirrors FAT-style chaining; Indexed allocation mirrors the Unix inode idea (one index block holds pointers to all data blocks). |
| **Python official documentation** | `tkinter` / `ttk` GUI toolkit, `math.ceil` for block rounding, `colorsys` for HSV→RGB neon animations, `ctypes` + `winmm.dll` for the Windows audio backend. |

> ⚠️ **Nothing is mocked:** the formulas, metadata structures, and failure messages match the textbook definitions 1:1, so the simulator can be verified line-by-line against *Operating System Concepts*.

---

## 🧠 The Core OS Concepts Implemented

| Concept | How the simulator implements it |
| --- | --- |
| **Disk blocks** | The virtual disk is a Python list of **64 blocks, each 32 bytes**. `None` = free, a filename = occupied. |
| **Directory** | A dictionary `files{}` acting as the directory table — it stores each file's metadata **per allocation method**, exactly like a real directory entry. The GUI now renders that entry live. |
| **Free-space management** | `free_blocks()` scans the disk and returns the free-space list, which the algorithms draw from. |
| **File size → block count** | Content is encoded to UTF-8 and converted to blocks with a ceiling division. Even an empty file takes 1 block — just like real file systems. |
| **File length (data blocks)** | The new `Length` column reports the length in *data* blocks — distinct from the total blocks occupied on disk. |
| **Pointer overhead** | In Linked allocation, every block sacrifices **4 bytes** for the "next block" pointer — so usable payload is only **28 bytes**. Real FS behavior, not a simplification. |
| **External fragmentation** | Contiguous allocation genuinely fails when no hole is big enough, even if total free space is sufficient — and the simulator tells you exactly that. |
| **Index block capacity** | A single-level index block of 32 bytes with 4-byte pointers holds only `32 / 4 = 8` pointers → max file = 8 data blocks. Enforced and explained. |
| **Block scattering** | Linked and Indexed allocation pick blocks in a randomized scattered order (`random.sample`), honestly simulating a real free-space list. |

---

## 🧮 The Three Allocation Algorithms (Explained With Math)

The disk constants used everywhere:

```
BLOCK_SIZE     = 32 bytes per block
POINTER_SIZE   = 4  bytes per block-pointer
LINKED_PAYLOAD = 28 bytes usable per linked block (32 - 4)
TOTAL_BLOCKS   = 64
```

### 1️⃣ Contiguous Allocation (First-Fit)
The file occupies **one continuous run** of blocks.
- **Blocks needed:** `ceil(size / 32)`
- **Search strategy:** first-fit — scan left to right, take the first hole big enough.
- **Directory stores:** *start block + length* (just two numbers — that's the beauty of it).
- ✅ **Pros:** fastest sequential and direct access — block *i* is simply `start + i`.
- ❌ **Cons:** suffers **external fragmentation** — a new file may fail to save even when enough *total* space is free. The simulator reproduces this failure honestly.

### 2️⃣ Linked Allocation (FAT-style chain)
The file is a **linked list** of blocks scattered anywhere on the disk.
- Each block reserves 4 bytes for the next-block pointer → usable payload = `32 - 4 = 28` bytes.
- **Blocks needed:** `ceil(size / 28)` — more blocks than contiguous for the same content, shown live.
- **Directory stores:** *start block + last block*; the full chain lives inside the blocks themselves.
- ✅ **Pros:** never suffers external fragmentation — any free block, anywhere, works.
- ❌ **Cons:** terrible direct access — to read block *i* you must walk the chain through *i* pointers; plus 12.5% of the disk is eaten by pointers.

### 3️⃣ Indexed Allocation (inode-style)
One dedicated **index block** holds a pointer table to all the file's data blocks.
- **Blocks needed:** `ceil(size / 32)` data blocks **+ 1** index block.
- **Capacity limit:** the index block holds only `32 / 4 = 8` pointers → max file = `8 × 32 = 256` bytes with a single-level index.
- **Directory stores:** only the **index block number**. The pointer table lives inside the index block.
- ✅ **Pros:** no external fragmentation and fast direct access.
- ❌ **Cons:** one whole block of overhead per file, and a hard-capped file size at a single index level.

### Live comparison the simulator makes visible
For the same **100-byte** file:

| Method | Calculation | Blocks used |
| --- | --- | --- |
| Contiguous | `ceil(100 / 32)` | **4** (must be adjacent) |
| Linked | `ceil(100 / 28)` | **4** (scattered, pointer overhead) |
| Indexed | `ceil(100 / 32) + 1` | **5** (4 data + 1 index, scattered) |

---

## 📋 Reading the "Files on Disk" Panel (Bytes · Blocks · Length)

The right-hand file table now carries four data columns that map directly onto a real OS directory entry:

| Column | Meaning |
| --- | --- |
| **Bytes** | The file's size in bytes (UTF-8 encoded content). |
| **Blocks** | **Total** disk blocks the file occupies right now — for Indexed this **includes the index block**. |
| **Length** | The file's length in **data blocks only** — the directory *"Length"* field from Figures 4.11 / 4.12. |
| **Method** | Which allocation algorithm stored the file. |

> Example: a small Indexed file shows `Blocks 5, Length 4` — the extra 1 is the index block. This makes the "index block is pure overhead" lesson unmistakable at a glance.

---

## 🗃️ The Directory Entry, per Method

Select any file and the **Directory entry** preview under the table shows exactly what that method's directory keeps — matching the figure boxes 1:1:

- **Contiguous** → `File Name · Start Block No. · Length`
- **Linked** → `File Name · Start Block No. · Last Block No. · Length · Chain (b → b → … → EOF)`
- **Indexed** → `File Name · Index Block No. · Index table [ … ] · Length (data blocks)`

This is the single clearest way to answer the classic viva question *"what does the directory actually store for each method?"*

---

## 🧾 The Activity Log Now Explains "Why This Many Blocks"

Every save narrates the arithmetic *before* it animates, so the reasoning is on screen:

```
Saving 'report.txt' with Indexed allocation ...
REASON ('report.txt' → Indexed):
     • File size            = 100 bytes
     • Block size           = 32 bytes (full block holds data)
     • Data blocks needed   = ceil(100 / 32) = 4 block(s)
     • + 1 INDEX block to hold the 4 pointer(s) → 4 + 1 = 5 block(s) total
     • Index block 24 → data blocks [1, 8, 3, 14]
     • Directory keeps: Index Block Number = 24
DONE: 'report.txt' saved. Blocks occupied on disk: [24, 1, 8, 3, 14]
Directory entry [Indexed]
  File Name        : report.txt
  Index Block No.  : 24
  Index table      : [1, 8, 3, 14]
  Length           : 4 data block(s)
```

The same treatment applies to Contiguous (one adjacent run) and Linked (28-byte payload + scattered chain).

---

## 🏗️ How the Code Is Architected (Phase by Phase)

The entire application lives in one heavily-commented Python file, divided into numbered **PHASES**. The key design decision: the **OS logic and the GUI are fully separated** (classic Model–View separation).

```
File_Management_&_Allocation_Simulator.py
│
├── PHASE 0  — Imports (tkinter, ttk, math, colorsys, random — all standard library)
│
├── PHASE 1  — VirtualDisk class  ← THE MODEL (pure OS logic, zero GUI code)
│               • blocks[] list, files{} directory, free-space helpers
│               • blocks_needed()  → the core ceil(size/payload) formula
│
├── PHASE 2  — The three allocation algorithms (inside VirtualDisk)
│               • find_contiguous()  — first-fit hole scan
│               • find_linked()      — scattered blocks + pointer chain
│               • find_indexed()     — index block + pointer table
│               • plan() / commit()  — two-step allocation
│               • delete_file() / reset()
│
├── PHASE 3  — The GUI (FileManagerApp class)  ← THE VIEW
│   ├── 3-SND  SoundFX     — synthesized keyboard/click sounds (persistent mixer)
│   ├── 3-FX   CursorFX    — glow trail, click ripples, spark micro-interactions
│   ├── 3-STYLE            — dark glassmorphism theme for all ttk widgets
│   ├── 3A     Menu bar    — File / Help / About
│   ├── 3B     Header      — animated RGB colour-cycling neon title
│   ├── 3C     Main body   — editor (left) + disk grid (center) + file list (right)
│   │           • Files-on-Disk table  (Bytes · Blocks · Length · Method)   ← v1.1.0
│   │           • Directory-entry preview per selected file                 ← v1.1.0
│   └── 3D     Activity log — terminal-style panel with per-save reasoning   ← v1.1.0
│
├── PHASE 4  — Live size meter (bytes typed → blocks needed, with ceil() formula)
│
├── PHASE 5  — Event handlers (Save / Open / Delete / Compare)
│               • _explain_alloc()     — builds the "why N blocks" reasoning   ← v1.1.0
│               • _dir_entry_text()     — builds the per-method directory entry ← v1.1.0
│               • _animate_allocation() — blocks fill ONE BY ONE
│               • on_compare()          — 3-panel side-by-side comparison
│
├── PHASE 6  — Drawing engine — renders the 64-block neon disk grid + file table
│
├── PHASE 7  — Built-in HELP system + About window
│
└── PHASE 8  — Program entry point
```

### Why the Plan → Commit two-step design matters
Real operating systems **validate before they write**. The simulator mirrors this:
- `plan(method, size)` asks the algorithm *"where would this file go?"* without touching the disk. On failure (fragmentation, capacity) the user gets the exact textbook reason and nothing is corrupted.
- `commit(name, content, method, blocks)` runs only after a successful plan — it occupies the blocks and writes the correct per-method directory metadata.

This atomic pattern is why the simulator never ends up in a broken half-saved state.

---

## 🖥️ Every Feature in the GUI & What It Teaches

| Feature | What the user does | What it teaches |
| --- | --- | --- |
| **File editor + live meter** | Types content; watches `X bytes → Y blocks` (with the `ceil()` formula) update per keystroke | The size→block conversion, and how block count depends on the algorithm (linked needs more!) |
| **Save with algorithm choice** | Picks Contiguous / Linked / Indexed, hits Save | Each algorithm's placement strategy, animated block-by-block |
| **Files-on-Disk table (Bytes · Blocks · Length)** | Reads the table | The difference between total blocks occupied and file *length* in data blocks |
| **Directory-entry preview** | Selects a file | Exactly what the directory stores for each method (fig. 4.11–4.13) |
| **Activity log reasoning** | Reads the log after a save | The full arithmetic of *why* that many blocks were used |
| **64-block disk grid** | Watches colored blocks appear/disappear | Disk state, scattering vs. contiguity, index blocks highlighted differently |
| **Open / Edit** | Reopens, edits, resaves | Files must be reallocated when they grow |
| **Delete** | Deletes files (single or multi-select) | Blocks return to the free list → holes → external fragmentation |
| **Compare mode** | One click on any file | Side-by-side 3-panel window with per-method block counts and metadata |
| **Help menu** | Opens the tabbed help window | A built-in mini-textbook explaining all three algorithms |
| **Reset disk** | Wipes everything | Start fresh experiments |

### 🔬 The killer demo for fragmentation (try this)
1. Fill the disk with several contiguous files.
2. Delete every second file — the grid now shows scattered small holes.
3. Try saving a large file with **Contiguous** → it fails with an *external fragmentation* message even though total free space is enough.
4. Save the exact same file with **Linked** → it succeeds instantly using the scattered holes.

That 30-second sequence demonstrates the single most important trade-off in file allocation, live.

---

## 🎨 The Extra Engineering: Sound Engine & Cursor FX

Beyond the OS logic, the project includes real systems-programming work purely for polish — all without a single external file or pip install.

### 🔊 SoundFX v2 — a persistent-stream audio mixer
- Keyboard "tick" and mouse "click" sounds are **synthesized in memory** at startup (sine + noise + exponential percussive decay) — no `.wav` files shipped.
- A daemon mixer thread keeps **one** audio stream open for the whole session and continuously feeds it PCM chunks (silence when idle), fixing rapid-retrigger cancellation, device sleep, and one-error-mutes-forever bugs.
- Cross-platform backends auto-detected: Windows `winmm.dll` via `ctypes`, Linux `pacat`/`aplay` pipes, macOS `afplay`.

### ✨ CursorFX — micro-interaction engine
- A click-through overlay canvas renders a subtle theme-colored glow trail, a ripple ring + sparks on click, a breathing pulse while holding, and a caret spark while typing.
- Runs on a single animation tick loop; effects fade out smoothly and are tuned to be easy on the eyes.

### 🌈 Visual theme
- Dark glassmorphism: layered glass panels on a deep space-blue background, neon cyan/green/pink/amber accents, and a live RGB colour-cycling title (HSV→RGB via `colorsys`).
- Consistent color-coding: every file gets its own neon color; free blocks, index blocks and chains are visually distinct.

---

## ▶️ How to Run It

**Requirements:** Python 3.x. That's it — Tkinter ships with Python; nothing to `pip install`.

```bash
git clone https://github.com/TechYoMinati/File-Management-and-Allocation-Simulator.git
cd File-Management-and-Allocation-Simulator
python File_Management_&_Allocation_Simulator.py
```

> On some minimal Linux distros you may need Tk once: `sudo apt install python3-tk`

---

## 📦 How to Build the Windows .EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "VirtualFileManager" File_Management_&_Allocation_Simulator.py
```

The standalone executable appears in the `dist/` folder — perfect for demonstrating on lab machines without Python installed.
## 👇📂 Here is that file & extension below which was used to make the py to exe by using the vscode these [EXTENSION](https://marketplace.visualstudio.com/items?itemName=zynx.py2exe)
File Management & Allocation Simulator
## 👀👇📂 And in this you can also see the Comments (#) for more clearance & explanation of backend phase wise parts given below:)
File Management & Allocation Simulator
## 🚀 Download Pre-built Release (No Setup Required)
Grab the latest pre-built version directly from the **Releases** page:)

👉 v1.1.0 — File Management & Allocation Simulator (Windows .exe + Source)

---

## 🎓 Explaining This Project in a Viva / To a Professor

A ready 60-second summary:

> *"I built a virtual file system in Python with a graphical file manager on top. The disk is modeled as 64 blocks of 32 bytes. When a user types content, the app computes the required blocks live using `ceil(bytes / payload)`, where the payload is 32 bytes for contiguous/indexed but only 28 for linked, because each linked block loses 4 bytes to its next-pointer — exactly as in Silberschatz's Operating System Concepts. On save, the chosen algorithm plans the placement first and commits only if it succeeds, so contiguous allocation genuinely fails under external fragmentation while linked succeeds with scattered blocks, and indexed enforces the 8-pointer single-level index limit. The file table shows Bytes, Blocks and Length so you can see total occupancy vs. data-block length, a directory-entry panel shows the real per-method metadata (start+length / start+last+chain / index block+table), and the activity log prints the block arithmetic for every save. A compare mode places the same file with all three algorithms side by side."*

Common viva questions this project answers **by demonstration**:

| Question | Show them |
| --- | --- |
| "What is external fragmentation?" | The fragmentation demo — contiguous fails, linked succeeds |
| "Why does linked allocation need more blocks?" | Toggle the method — the live meter changes from `ceil(n/32)` to `ceil(n/28)` |
| "What limits file size in indexed allocation?" | Type >256 bytes and save Indexed — the exact capacity-limit error appears |
| "What does the directory store?" | The **Directory entry** preview + Compare mode metadata panels |
| "What's the difference between blocks used and file length?" | The **Blocks** vs **Length** columns for an Indexed file |
| "How is the code organized?" | The PHASE comments — model (`VirtualDisk`) fully separated from view (`FileManagerApp`) |

---

## 🧾 Tech Stack Summary

| Layer | Technology | Why |
| --- | --- | --- |
| Core logic | Pure Python 3 (`math`, `random`) | Faithful, verifiable OS algorithms with no framework noise |
| GUI | Tkinter + ttk | Ships with Python — zero installation friction |
| Animations | `colorsys` HSV cycling + Tk `after()` loops | Neon RGB effects & block-by-block allocation without a game engine |
| Audio | `ctypes` + `winmm` / `pacat` / `aplay` / `afplay` | Synthesized, streamed sound with no asset files |
| Packaging | PyInstaller | One-file Windows executable |

---

## 👤 Author

**TechYoMinati** — Computer Engineering (Operating Systems Diploma Project)

> Built to make the invisible work of an operating system visible — one block at a time.
