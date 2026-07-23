"""
================================================================================
FILE MANAGEMENT SIMULATOR + FILE ALLOCATION SIMULATOR
 (Operating Systems Diploma Project)
================================================================================
 A GUI "virtual disk" file manager that lets you:

   1. CREATE real virtual files (report.txt, notes.doc, data.csv ...)
   2. TYPE content into them -> the app calculates LIVE how many disk
      blocks the content needs (size in bytes / block size)
   3. SAVE the file using any of the 3 classic OS allocation algorithms:
         - Contiguous Allocation
         - Linked     Allocation
         - Indexed    Allocation
      ...and WATCH the blocks get occupied one-by-one in real simulated time.
   4. OPEN / EDIT / DELETE files like a real file manager.
   5. COMPARE how the SAME file would be stored by all three algorithms.
   6. Read the built-in HELP menu that teaches how everything works.

 Language  : Python 3
 GUI       : Tkinter (built into Python, nothing extra to install)
 Author    : TechYoMinati

 DESIGN    : Modern dark "glassmorphism" theme with neon accents and a live
             RGB colour-cycling (animated gradient) title + accents.
             CURSOR ANIMATION ENGINE (balanced mode - easy on the eyes):
               - moving the mouse leaves a subtle theme-coloured glow trail
               - clicking fires one soft ripple ring + a few gentle sparks
               - holding the button breathes a slow pulse under the cursor
               - releasing the button instantly stops and fades the effects
               - every clickable button also "press-flashes" in sync
             TYPING FX:
               - typing in any text field flashes a neon border glow that
                 fades back smoothly + pops a tiny spark at the caret
             SOUND FX (zero external files - synthesised at start-up):
               - soft mechanical keyboard "tick" on every real keystroke
               - snappy mouse "click" on every clickable control
               - powered by a PERSISTENT-STREAM MIXER: one audio stream
                 stays open for the whole session, so sounds are never
                 cancelled, never dropped, and the audio device never
                 falls asleep between keystrokes

 HOW TO RUN (inside VS Code):
     python file_allocation_simulator.py

 HOW TO MAKE THE .EXE (Windows):
     pip install pyinstaller
     pyinstaller --onefile --windowed --name "VirtualFileManager" file_allocation_simulator.py

================================================================================
 CODE MAP - the file is organised PHASE-WISE, top to bottom:
================================================================================
   PHASE 0       Imports (standard library only - no pip installs)
   PHASE 1       VirtualDisk        - the disk data model (pure OS logic)
   PHASE 2       The 3 allocation algorithms (contiguous / linked / indexed)
   PHASE 3       GUI theme constants + colour helpers
   PHASE 3-SND   SoundFX            - the persistent-stream sound engine
   PHASE 3-FX    CursorFX           - the cursor particle animation engine
   PHASE 3-STYLE ttk dark-theme styling
   PHASE 3A-3D   Menu bar, header, main body layout, activity log
   PHASE 4       Live size meter    (bytes typed -> blocks needed, real time)
   PHASE 5       Event handlers     (save / open / delete / compare ...)
   PHASE 6       Disk-grid drawing, stats and file table rendering
   PHASE 7-7B    Help system + About window
   PHASE 8       Program entry point

 Every phase begins with a banner comment explaining WHAT it does and WHY,
 so the code can be read (and explained to an examiner) top to bottom.
"""

# ==============================================================================
# PHASE 0 : IMPORT THE REQUIRED LIBRARIES
# ------------------------------------------------------------------------------
# tkinter    -> standard GUI toolkit shipped with Python
# ttk        -> themed widgets (tables, comboboxes, notebook tabs)
# messagebox -> ready-made popup dialogs
# math.ceil  -> to round UP bytes/block_size into whole blocks
# colorsys   -> HSV -> RGB conversion used for the neon RGB animations
# ==============================================================================
import tkinter as tk
from tkinter import ttk, messagebox
import math
import colorsys
import random
import time


# ==============================================================================
# PHASE 1 : THE VIRTUAL DISK DATA MODEL (pure OS logic - no GUI here)
# ------------------------------------------------------------------------------
# The disk is a list of blocks. Each block is either free (None) or owned by
# a file name. Every file also stores its CONTENT, so this behaves like a
# tiny real file system:
#
#   content size (bytes)  ->  blocks needed = ceil(bytes / BLOCK_SIZE)
#
# Example with BLOCK_SIZE = 32:
#   "Hello"            =   5 bytes -> 1 block
#   120 characters     = 120 bytes -> 4 blocks
# ==============================================================================
class VirtualDisk:
    BLOCK_SIZE = 32    # bytes per block (small on purpose so students SEE growth)
    POINTER_SIZE = 4   # bytes one block-pointer costs (like a real FS pointer)

    # LINKED  : every data block sacrifices POINTER_SIZE bytes to store the
    #           "next block" pointer -> usable payload = 32 - 4 = 28 bytes.
    LINKED_PAYLOAD = BLOCK_SIZE - POINTER_SIZE

    # INDEXED : ONE index block stores the pointer table. It can only hold
    #           BLOCK_SIZE / POINTER_SIZE = 8 pointers -> a file may have at
    #           most 8 data blocks with a single-level index (classic limit).
    INDEX_CAPACITY = BLOCK_SIZE // POINTER_SIZE

    def __init__(self, total_blocks=64):
        self.total_blocks = total_blocks
        # one slot per disk block: None = FREE, "name.txt" = OCCUPIED by file
        self.blocks = [None] * total_blocks
        # the "directory": every file's metadata + its actual text content
        self.files = {}

    # ----- helpers ------------------------------------------------------------
    def free_blocks(self):
        """List of all block numbers that are currently free."""
        return [i for i, owner in enumerate(self.blocks) if owner is None]

    def free_count(self):
        """How many blocks are still free on the disk."""
        return len(self.free_blocks())

    @staticmethod
    def blocks_needed(content, method="Contiguous"):
        """THE core formula: how many DATA blocks does this content occupy?
        Even an empty file occupies 1 block (like real file systems).

        METHOD MATTERS (this is real OS behaviour):
          - Contiguous / Indexed : a data block stores a full 32 bytes of
            data, so                blocks = ceil(size / 32)
          - Linked               : every data block LOSES 4 bytes to the
            embedded "next block" pointer, so only 28 bytes of each block
            hold data ->            blocks = ceil(size / 28)
        """
        size = len(content.encode("utf-8"))
        if method == "Linked":
            payload = VirtualDisk.LINKED_PAYLOAD      # 32 - 4 = 28 bytes
        else:
            payload = VirtualDisk.BLOCK_SIZE          # full 32 bytes
        return max(1, math.ceil(size / payload)), size

    # ==========================================================================
    # PHASE 2 : THE THREE ALLOCATION ALGORITHMS
    # ==========================================================================

    # --------------------------------------------------------------------------
    # ALGORITHM 1 : CONTIGUOUS ALLOCATION (first-fit)
    # --------------------------------------------------------------------------
    def find_contiguous(self, size):
        run_start, run_len = None, 0
        for i in range(self.total_blocks):
            if self.blocks[i] is None:
                if run_start is None:
                    run_start = i
                run_len += 1
                if run_len == size:  # found a hole big enough
                    return list(range(run_start, run_start + size)), None
            else:
                run_start, run_len = None, 0
        return None, ("No contiguous hole of that size exists "
                      "(external fragmentation).")

    # --------------------------------------------------------------------------
    # ALGORITHM 2 : LINKED ALLOCATION
    # --------------------------------------------------------------------------
    # CORE LOGIC (Silberschatz / real OS behaviour):
    #   - Each file is a LINKED LIST of disk blocks. The blocks may be
    #     SCATTERED ANYWHERE on the disk - they do NOT need to be adjacent.
    #   - Every data block reserves POINTER_SIZE bytes at its end that hold
    #     the address of the NEXT block in the chain (the last block stores
    #     an end-of-file marker, here None).
    #   - The DIRECTORY entry keeps only the START block and END block.
    #   - Because ANY free block can be used, linked allocation NEVER suffers
    #     external fragmentation - if enough free blocks exist, it succeeds.
    #
    # To demonstrate that honestly, we pick the free blocks in a SCATTERED
    # (random) order, exactly like a real FS grabbing whatever blocks the
    # free-space list hands out - NOT a neat contiguous-looking run.
    # --------------------------------------------------------------------------
    def find_linked(self, size):
        free = self.free_blocks()
        if len(free) < size:
            return None, (f"Need {size} free blocks "
                          f"({self.LINKED_PAYLOAD} data bytes each after the "
                          f"{self.POINTER_SIZE}-byte next-pointer), "
                          f"only {len(free)} left.")
        # scatter: grab blocks from anywhere on the disk (chain order = list
        # order: blocks[0] is the START of the chain, blocks[-1] the END)
        return random.sample(free, size), None

    # --------------------------------------------------------------------------
    # ALGORITHM 3 : INDEXED ALLOCATION
    # --------------------------------------------------------------------------
    # CORE LOGIC (Silberschatz / real OS behaviour):
    #   - ONE dedicated INDEX BLOCK holds a table of pointers to ALL of the
    #     file's data blocks (the i-th table entry -> the i-th data block).
    #   - The DIRECTORY entry points ONLY at the index block.
    #   - The data blocks themselves can be SCATTERED anywhere on the disk,
    #     so there is no external fragmentation, and direct access is fast:
    #     read the index block, then jump straight to data block i.
    #   - LIMITATION: a single-level index block can only hold
    #     BLOCK_SIZE / POINTER_SIZE = 8 pointers -> max file size of
    #     8 data blocks (real systems solve this with multi-level indexes).
    #
    # Returned list layout: [index_block, data0, data1, ...] - the FIRST
    # element is always the index block; data blocks are scattered.
    # --------------------------------------------------------------------------
    def find_indexed(self, size):
        if size > self.INDEX_CAPACITY:
            return None, (f"File needs {size} data blocks but one index "
                          f"block only holds {self.INDEX_CAPACITY} pointers "
                          f"({self.BLOCK_SIZE} B / {self.POINTER_SIZE} B per "
                          f"pointer). Max file size with a single-level "
                          f"index = {self.INDEX_CAPACITY * self.BLOCK_SIZE} "
                          f"bytes.")
        free = self.free_blocks()
        if len(free) < size + 1:  # +1 for the index block itself
            return None, (f"Indexed needs {size} data + 1 index block, "
                          f"only {len(free)} free.")
        # index block first, then SCATTERED data blocks (like a real FS)
        picked = random.sample(free, size + 1)
        return picked, None

    # --------------------------------------------------------------------------
    # PLAN : ask the chosen algorithm where the file WOULD go (no changes yet)
    # --------------------------------------------------------------------------
    def plan(self, method, size):
        if method == "Contiguous":
            return self.find_contiguous(size)
        if method == "Linked":
            return self.find_linked(size)
        return self.find_indexed(size)

    # --------------------------------------------------------------------------
    # COMMIT : actually occupy the planned blocks and register the file,
    #          storing the REAL per-algorithm metadata a directory would keep:
    #            Contiguous -> start block + length
    #            Linked     -> start block + end block + the pointer CHAIN
    #            Indexed    -> the index block + its pointer table
    # --------------------------------------------------------------------------
    def commit(self, name, content, method, blocks):
        for b in blocks:
            self.blocks[b] = name
        _, size_bytes = self.blocks_needed(content, method)

        entry = {
            "content": content,
            "size_bytes": size_bytes,
            "blocks": blocks,
            "method": method,
            "index_block": None,
            "start": None, "length": None,        # contiguous metadata
            "chain": None,                        # linked metadata
            "index_table": None,                  # indexed metadata
        }
        if method == "Contiguous":
            entry["start"] = blocks[0]
            entry["length"] = len(blocks)
        elif method == "Linked":
            # each block "points" to the next; the last points to EOF (None)
            entry["start"] = blocks[0]
            entry["chain"] = {blocks[i]: (blocks[i + 1] if i + 1 < len(blocks)
                                          else None)
                              for i in range(len(blocks))}
        else:  # Indexed
            entry["index_block"] = blocks[0]
            entry["index_table"] = blocks[1:]     # pointers stored inside it
        self.files[name] = entry

    # --------------------------------------------------------------------------
    # DELETE : free every block owned by the file, remove directory entry
    # --------------------------------------------------------------------------
    def delete_file(self, name):
        if name not in self.files:
            return False, f"No file named '{name}'."
        freed = self.files[name]["blocks"]
        for b in freed:
            self.blocks[b] = None
        del self.files[name]
        return True, f"'{name}' deleted - blocks {freed} are free again."

    # --------------------------------------------------------------------------
    # RESET the entire disk back to empty
    # --------------------------------------------------------------------------
    def reset(self):
        self.blocks = [None] * self.total_blocks
        self.files = {}


# ==============================================================================
# PHASE 3 : THE GRAPHICAL USER INTERFACE
# ------------------------------------------------------------------------------
# MODERN DARK GLASSMORPHISM look:
#   - deep space-blue background with layered "glass" panels
#   - neon cyan primary + neon green / pink / amber accents
#   - live RGB colour-cycling on the title & signature text
# Layout:
#   LEFT   : file editor (name + extension + content, live size meter)
#   CENTER : the disk grid canvas + usage stats
#   RIGHT  : file manager list + open/delete/compare buttons
#   BOTTOM : activity log (terminal style)
#   TOP    : menu bar + neon header
# ==============================================================================

# ----- the dark neon "glass" colour theme used everywhere ---------------------
C = {
    "bg":        "#070B14",   # deep space background
    "bg2":       "#0A101E",   # slightly lighter layer
    "glass":     "#0F1729",   # glass panel fill
    "glass2":    "#131D33",   # glass panel hover / inner fill
    "border":    "#1E2B47",   # subtle glass edge
    "borderhi":  "#2E4470",   # brighter glass edge (focus)

    "neon":      "#00F0FF",   # neon cyan   - primary
    "neon2":     "#00C2FF",   # deeper cyan - hover
    "green":     "#39FF88",   # neon green  - success / save
    "amber":     "#FFC24B",   # neon amber  - warning / compare
    "pink":      "#FF4FD8",   # neon pink   - highlights
    "red":       "#FF4D6D",   # neon red    - delete / errors

    "text":      "#E8F1FF",   # near-white text
    "muted":     "#8193B8",   # cool grey text
    "free":      "#0C1424",   # free block fill
    "freeline":  "#22304F",   # free block outline
}

# distinct neon colours assigned to files on the disk grid
FILE_COLORS = [
    "#00F0FF", "#39FF88", "#FF9F45", "#C77BFF", "#22D3EE",
    "#FF4D6D", "#F5E663", "#2DD4BF", "#FF4FD8", "#8B9BFF",
    "#A3E635", "#FB7185", "#38BDF8", "#E879F9", "#34D399",
]

EXTENSIONS = [".txt", ".doc", ".csv", ".py", ".html", ".md", ".log", ".json"]


def _hsv_hex(h, s=1.0, v=1.0):
    """Convert a hue (0..1) into a '#RRGGBB' colour - used by RGB animations."""
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"


# ==============================================================================
# PHASE 3-SND : THE SOUND ENGINE  (persistent-stream mixer)
# ------------------------------------------------------------------------------
# WHAT IT DOES (non-technical): plays a soft keyboard "tick" for every
# keystroke and a snappy "click" for every button press - with zero external
# sound files and zero pip installs. Both sounds are mathematically
# synthesised in memory when the app starts.
#
# WHY A PERSISTENT-STREAM MIXER (technical design rationale):
# A naive "play one .wav per event" approach fails in three well-known ways,
# so this engine is deliberately built around ONE always-open audio stream:
#
#   PROBLEM 1: one-shot async players (e.g. winsound SND_ASYNC) cancel the
#              currently playing sound on every new call -> fast typing
#              would randomly drop ticks mid-play.
#     SOLUTION: overlapping sounds are software-MIXED into one stream, so
#               nothing is ever cancelled.
#
#   PROBLEM 2: Windows suspends the audio endpoint after a short idle
#              period; a 45 ms tick can finish before the device wakes,
#              producing silence.
#     SOLUTION: a daemon MIXER THREAD keeps the stream open for the whole
#               session and feeds it small chunks (silence when idle), so
#               the audio device never sleeps.
#
#   PROBLEM 3: a single transient playback error must not mute the app.
#     SOLUTION: errors are retried; the engine only disables itself if the
#               audio backend is truly unavailable.
#
# BACKENDS (auto-detected at start-up, best first):
#   - Windows : winmm.dll waveOut* streaming via ctypes (built into Windows)
#   - Linux   : ONE persistent `pacat` / `aplay` process fed raw PCM
#   - macOS   : `afplay` per event (afplay cannot stream); overlapping
#               players are allowed so nothing is ever cancelled
# ==============================================================================
class SoundFX:
    RATE = 22050          # sample rate (Hz)
    CHUNK = 256           # frames per mixer chunk  (~12 ms -> snappy latency)
    N_BUF = 4             # rotating output buffers (Windows waveOut backend)

    def __init__(self):
        self.enabled = True
        self._backend = None           # "winmm" | "pipe" | "afplay" | None
        self._last_key = 0.0           # throttle for very fast typists
        self._last_click = 0.0         # throttle for double-fired presses
        self._voices = []              # active sounds: [pcm_array, position]
        self._pipe_proc = None
        self._pipe_t0 = 0.0
        self._pipe_sent = 0
        try:
            import threading
            self._lock = threading.Lock()
            # ---- synthesise both samples ONCE, straight into memory ----------
            #  key   -> soft high mechanical-keyboard "tick"
            #  click -> deeper, snappier mouse "click"
            self.key_pcm = self._synth(dur=0.06, freq=2400.0,
                                       noise=0.50, volume=0.38)
            self.click_pcm = self._synth(dur=0.08, freq=1100.0,
                                         noise=0.70, volume=0.55)
            self._pick_backend()
            if self._backend in ("winmm", "pipe"):
                threading.Thread(target=self._mixer_loop, daemon=True).start()
        except Exception:
            self.enabled = False

    # ----- synthesise one tiny percussive sample (sine + noise, fast decay) ---
    def _synth(self, dur, freq, noise, volume):
        import array
        n = int(self.RATE * dur)
        buf = array.array("h", bytes(2 * n))
        for i in range(n):
            t = i / self.RATE
            env = math.exp(-t * 70.0)                 # percussive decay
            tone = math.sin(math.tau * freq * t)
            hiss = random.uniform(-1.0, 1.0)
            s = (tone * (1.0 - noise) + hiss * noise) * env * volume
            buf[i] = int(max(-1.0, min(1.0, s)) * 32767)
        return buf

    # ----- pick the best available PERSISTENT-STREAM backend ------------------
    def _pick_backend(self):
        import sys, shutil
        if sys.platform.startswith("win"):
            try:
                self._init_winmm()                 # built-in, no pip needed
                self._backend = "winmm"
                return
            except Exception:
                pass
        for cmd, argv in (
            ("pacat", ["pacat", "--format=s16le", "--rate=22050",
                       "--channels=1", "--raw", "--latency-msec=40"]),
            ("aplay", ["aplay", "-q", "-t", "raw", "-f", "S16_LE",
                       "-r", "22050", "-c", "1", "-"]),
        ):
            if shutil.which(cmd):                  # Linux: one live pipe
                self._pipe_argv = argv
                self._backend = "pipe"
                return
        if shutil.which("afplay"):                 # macOS: per-event fallback
            self._init_afplay()
            self._backend = "afplay"
            return
        self.enabled = False                       # nothing available -> mute

    # ----- Windows: open ONE waveOut stream via winmm.dll (ctypes) ------------
    def _init_winmm(self):
        import ctypes

        class WAVEFORMATEX(ctypes.Structure):
            _fields_ = [("wFormatTag", ctypes.c_ushort),
                        ("nChannels", ctypes.c_ushort),
                        ("nSamplesPerSec", ctypes.c_uint),
                        ("nAvgBytesPerSec", ctypes.c_uint),
                        ("nBlockAlign", ctypes.c_ushort),
                        ("wBitsPerSample", ctypes.c_ushort),
                        ("cbSize", ctypes.c_ushort)]

        class WAVEHDR(ctypes.Structure):
            _fields_ = [("lpData", ctypes.c_void_p),
                        ("dwBufferLength", ctypes.c_uint),
                        ("dwBytesRecorded", ctypes.c_uint),
                        ("dwUser", ctypes.c_void_p),
                        ("dwFlags", ctypes.c_uint),
                        ("dwLoops", ctypes.c_uint),
                        ("lpNext", ctypes.c_void_p),
                        ("reserved", ctypes.c_void_p)]

        self._ct = ctypes
        winmm = ctypes.windll.winmm
        fmt = WAVEFORMATEX(1, 1, self.RATE, self.RATE * 2, 2, 16, 0)
        self._hwo = ctypes.c_void_p()
        res = winmm.waveOutOpen(ctypes.byref(self._hwo),
                                ctypes.c_uint(0xFFFFFFFF),   # WAVE_MAPPER
                                ctypes.byref(fmt), 0, 0, 0)
        if res != 0:
            raise OSError("waveOutOpen failed (%d)" % res)
        self._winmm = winmm
        self._bufs = []                            # rotating output buffers
        for _ in range(self.N_BUF):
            data = ctypes.create_string_buffer(self.CHUNK * 2)
            hdr = WAVEHDR()
            hdr.lpData = ctypes.cast(data, ctypes.c_void_p)
            hdr.dwBufferLength = self.CHUNK * 2
            self._bufs.append([data, hdr, False])  # False = never queued yet

    # ----- macOS fallback: write the two samples to tiny temp .wav files ------
    def _init_afplay(self):
        import tempfile, os, wave
        d = tempfile.gettempdir()
        self.key_wav = os.path.join(d, "vfm_key.wav")
        self.click_wav = os.path.join(d, "vfm_click.wav")
        for path, pcm in ((self.key_wav, self.key_pcm),
                          (self.click_wav, self.click_pcm)):
            with wave.open(path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(self.RATE)
                w.writeframes(pcm.tobytes())
        self._procs = []

    # ==========================================================================
    # THE MIXER LOOP (daemon thread) - the heart of the fix.
    # Runs for the app's whole lifetime, endlessly pushing ~12 ms chunks into
    # the ONE open audio stream. Idle = silence (keeps the device awake);
    # active = all live sounds summed together (nothing ever cancelled).
    # ==========================================================================
    def _mixer_loop(self):
        idx = 0
        fails = 0
        while self.enabled:
            try:
                chunk = self._mix_chunk()
                if self._backend == "winmm":
                    self._winmm_write(idx, chunk)
                    idx = (idx + 1) % self.N_BUF
                else:                              # "pipe" (Linux)
                    self._pipe_write(chunk)
                fails = 0
            except Exception:
                fails += 1                         # transient error: retry,
                if fails > 25:                     # only give up if the
                    self.enabled = False           # backend is truly dead
                    return
                time.sleep(0.1)

    # ----- sum every active voice into one 16-bit chunk (with clipping) -------
    def _mix_chunk(self):
        import array
        out = array.array("h", bytes(2 * self.CHUNK))
        with self._lock:
            if not self._voices:
                return out                         # pure silence chunk
            for i in range(self.CHUNK):
                acc = 0
                for v in self._voices:
                    p = v[1] + i
                    if p < len(v[0]):
                        acc += v[0][p]
                if acc > 32767:
                    acc = 32767
                elif acc < -32768:
                    acc = -32768
                out[i] = acc
            for v in self._voices:                 # advance, drop finished
                v[1] += self.CHUNK
            self._voices = [v for v in self._voices if v[1] < len(v[0])]
        return out

    # ----- Windows: queue a chunk into the next free rotating buffer ----------
    def _winmm_write(self, idx, chunk):
        ct = self._ct
        WHDR_DONE = 0x01
        data, hdr, queued = self._bufs[idx]
        if queued:                                 # wait for driver to finish
            while not (hdr.dwFlags & WHDR_DONE):
                time.sleep(0.002)
            self._winmm.waveOutUnprepareHeader(self._hwo, ct.byref(hdr),
                                               ct.sizeof(hdr))
        ct.memmove(data, chunk.tobytes(), self.CHUNK * 2)
        hdr.dwFlags = 0
        self._winmm.waveOutPrepareHeader(self._hwo, ct.byref(hdr),
                                         ct.sizeof(hdr))
        self._winmm.waveOutWrite(self._hwo, ct.byref(hdr), ct.sizeof(hdr))
        self._bufs[idx][2] = True

    # ----- Linux: feed ONE persistent player process, paced to real time ------
    def _pipe_write(self, chunk):
        import subprocess
        if self._pipe_proc is None or self._pipe_proc.poll() is not None:
            self._pipe_proc = subprocess.Popen(
                self._pipe_argv, stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._pipe_t0 = time.monotonic()
            self._pipe_sent = 0
        self._pipe_proc.stdin.write(chunk.tobytes())
        self._pipe_proc.stdin.flush()
        self._pipe_sent += self.CHUNK
        # stay only ~3 chunks ahead of real time -> latency stays tiny
        ahead = (self._pipe_sent / self.RATE
                 - (time.monotonic() - self._pipe_t0))
        lead = 3 * self.CHUNK / self.RATE
        if ahead > lead:
            time.sleep(ahead - lead)

    # ----- start one sound (mixed on top of whatever is already playing) ------
    def _trigger(self, pcm, wav_path):
        if not self.enabled:
            return
        try:
            if self._backend in ("winmm", "pipe"):
                with self._lock:
                    if len(self._voices) < 12:     # sane polyphony cap
                        self._voices.append([pcm, 0])
            elif self._backend == "afplay":
                import subprocess
                self._procs = [p for p in self._procs if p.poll() is None]
                if wav_path and len(self._procs) < 8:
                    self._procs.append(subprocess.Popen(
                        ["afplay", wav_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL))
        except Exception:
            pass                                   # NEVER mute permanently

    # public API ----------------------------------------------------------------
    def key(self):
        """Keyboard tick - throttled so ultra-fast typing can't spam audio."""
        now = time.monotonic()
        if now - self._last_key >= 0.03:
            self._last_key = now
            self._trigger(self.key_pcm, getattr(self, "key_wav", None))

    def click(self):
        """Mouse click snap - fired when a clickable control is pressed."""
        now = time.monotonic()
        if now - self._last_click >= 0.03:
            self._last_click = now
            self._trigger(self.click_pcm, getattr(self, "click_wav", None))


# ==============================================================================
# PHASE 3-FX : THE CURSOR ANIMATION ENGINE  (professional micro-interactions)
# ------------------------------------------------------------------------------
# A full-window PARTICLE OVERLAY that reacts to the mouse:
#
#   MOVE     -> a smooth neon "comet trail" of hue-cycling glow dots follows
#               the cursor, plus tiny drifting sparkles.
#   PRESS    -> a satisfying CLICK BURST: expanding neon ripple rings + a
#               radial spark explosion at the exact click point. While the
#               button is HELD DOWN a soft pulse ring keeps breathing under
#               the cursor (like a touch-and-hold effect).
#   RELEASE  -> the hold-pulse STOPS instantly and every remaining particle
#               fades out quickly with one last soft dissolve ring.
#
# HOW IT WORKS
#   - On Windows we create a border-less, always-on-top, CLICK-THROUGH
#     Toplevel window that exactly covers the app. Its background colour is a
#     "transparent key" colour, so only the drawn particles are visible and
#     all mouse clicks pass straight through to the real UI underneath.
#   - On systems without transparent windows (Linux/macOS) we gracefully fall
#     back to drawing the same effects on the big disk-grid canvas, so the
#     app never breaks.
#   - Everything runs on ONE ~60 fps `after()` loop; particle count is capped
#     so the UI always stays responsive.
# ==============================================================================
class CursorFX:
    TRANS_KEY = "#000001"     # the magic "invisible" colour of the overlay
    FRAME_MS = 16             # ~60 fps update loop
    MAX_PARTICLES = 70        # LOW cap -> subtle, smooth, easy on the eyes
    # BALANCED MODE: instead of a loud full-rainbow storm, all particles stay
    # inside the app's own neon cyan-blue palette, are smaller, fewer and
    # fade faster - a calm "glow" rather than a firework show.
    HUE_BASE = 0.52           # theme cyan
    HUE_SPAN = 0.10           # gentle drift between cyan and blue

    def __init__(self, root, fallback_canvas=None):
        self.root = root
        self.particles = []          # every live particle (dicts)
        self.hue = 0.0               # rolling hue -> rainbow trail
        self.mouse_down = False      # is the button currently held?
        self.last_xy = None          # last cursor position (root coords)
        self._pulse_clock = 0        # frames since last hold-pulse ring
        self._trail_gate = 0.0       # throttles trail spawning
        self.overlay = None
        self.canvas = None

        self._build_overlay(fallback_canvas)
        if self.canvas is None:
            return                   # no drawing surface -> FX disabled

        # global mouse hooks (add='+' keeps every existing widget binding)
        root.bind_all("<Motion>", self._on_motion, add="+")
        root.bind_all("<B1-Motion>", self._on_motion, add="+")
        root.bind_all("<ButtonPress-1>", self._on_press, add="+")
        root.bind_all("<ButtonRelease-1>", self._on_release, add="+")
        if self.overlay is not None:
            root.bind("<Configure>", lambda e: self._sync_geometry(), add="+")
            root.bind("<Unmap>", lambda e: self.overlay.withdraw(), add="+")
            root.bind("<Map>", lambda e: (self.overlay.deiconify(),
                                          self._sync_geometry()), add="+")
        self._tick()

    # ----- build the transparent click-through overlay (Windows) --------------
    def _build_overlay(self, fallback_canvas):
        try:
            ov = tk.Toplevel(self.root)
            ov.overrideredirect(True)              # no title bar / border
            ov.configure(bg=self.TRANS_KEY)
            ov.attributes("-transparentcolor", self.TRANS_KEY)  # Windows only
            ov.attributes("-topmost", True)
            cv = tk.Canvas(ov, bg=self.TRANS_KEY, highlightthickness=0, bd=0)
            cv.pack(fill="both", expand=True)
            self.overlay, self.canvas = ov, cv
            self._sync_geometry()
            self._make_click_through()             # clicks pass THROUGH it
        except Exception:
            # transparent windows unsupported -> fall back to disk canvas
            try:
                if self.overlay is not None:
                    self.overlay.destroy()
            except Exception:
                pass
            self.overlay = None
            self.canvas = fallback_canvas

    def _make_click_through(self):
        """Windows API: WS_EX_TRANSPARENT makes the overlay ignore ALL mouse
        input, so hovering / clicking passes straight through to the real
        widgets underneath - the overlay is purely visual."""
        try:
            import ctypes
            self.overlay.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.overlay.winfo_id())
            if not hwnd:
                hwnd = self.overlay.winfo_id()
            GWL_EXSTYLE, WS_EX_LAYERED, WS_EX_TRANSPARENT = -20, 0x80000, 0x20
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        except Exception:
            pass  # not on Windows - overlay may eat clicks, so drop it
    # NOTE: if click-through could not be applied the overlay is still
    # transparent-keyed, and particles are tiny + short-lived, so the UI
    # stays fully usable either way.

    # ----- keep the overlay glued exactly on top of the main window -----------
    def _sync_geometry(self):
        if self.overlay is None:
            return
        try:
            r = self.root
            self.overlay.geometry(
                f"{r.winfo_width()}x{r.winfo_height()}"
                f"+{r.winfo_rootx()}+{r.winfo_rooty()}")
            self.overlay.lift()
        except Exception:
            pass

    # ----- root-screen coords -> local canvas coords ---------------------------
    def _local(self, xr, yr):
        try:
            return (xr - self.canvas.winfo_rootx(),
                    yr - self.canvas.winfo_rooty())
        except Exception:
            return None

    def _inside(self, x, y):
        """Is the point (x, y) inside the drawing surface? (canvas coords)"""
        return (0 <= x <= self.canvas.winfo_width()
                and 0 <= y <= self.canvas.winfo_height())

    # ==========================================================================
    # PARTICLE SPAWNERS
    # ==========================================================================
    def _spawn(self, **p):
        """Add one particle (a dict of properties) - capped so the UI
        always stays responsive no matter how fast the user clicks."""
        if len(self.particles) < self.MAX_PARTICLES:
            self.particles.append(p)

    def _theme_hue(self, jitter=0.03):
        """A hue locked to the app's cyan-blue palette (never full rainbow)."""
        drift = math.sin(self.hue * math.tau) * self.HUE_SPAN * 0.5
        return self.HUE_BASE + drift + random.uniform(-jitter, jitter)

    # -- SUBTLE glow trail while the cursor moves (small, dim, fades fast) -----
    def _trail(self, x, y):
        self._spawn(kind="dot", x=x + random.uniform(-1, 1),
                    y=y + random.uniform(-1, 1),
                    vx=random.uniform(-0.3, 0.3),
                    vy=random.uniform(-0.3, 0.3),
                    r=random.uniform(1.4, 2.4),
                    life=0.55, decay=0.075,       # dim start + quick fade
                    hue=self._theme_hue())

    # -- click feedback: ONE clean ripple ring + a few gentle sparks ------------
    def _burst(self, x, y):
        self._spawn(kind="ring", x=x, y=y, r=4, grow=2.0,
                    life=0.8, decay=0.07, hue=self._theme_hue(0.0))
        n = 6                                     # just a light accent, not a bomb
        for i in range(n):
            a = (i / n) * math.tau + random.uniform(-0.2, 0.2)
            sp = random.uniform(1.4, 2.6)
            self._spawn(kind="spark", x=x, y=y,
                        vx=math.cos(a) * sp, vy=math.sin(a) * sp,
                        r=random.uniform(1.0, 1.8),
                        life=0.7, decay=0.08, grav=0.05,
                        hue=self._theme_hue(0.05))

    # -- very soft pulse ring while the button is HELD ---------------------------
    def _hold_pulse(self, x, y):
        self._spawn(kind="ring", x=x, y=y, r=5, grow=1.2,
                    life=0.6, decay=0.08, hue=self._theme_hue(0.0))

    # -- tiny spark above the text caret while TYPING (used by the app) ---------
    def type_spark(self, xr, yr):
        pos = self._local(xr, yr)
        if pos is None or not self._inside(*pos):
            return
        self._spawn(kind="spark", x=pos[0], y=pos[1],
                    vx=random.uniform(-0.6, 0.6),
                    vy=random.uniform(-1.2, -0.5),
                    r=random.uniform(1.0, 1.6),
                    life=0.6, decay=0.09, grav=0.03,
                    hue=self._theme_hue(0.05))

    # ==========================================================================
    # MOUSE EVENT HOOKS
    # ==========================================================================
    def _on_motion(self, e):
        pos = self._local(e.x_root, e.y_root)
        if pos is None:
            return
        x, y = pos
        if not self._inside(x, y):
            return
        self.last_xy = (x, y)
        now = time.monotonic()
        if now - self._trail_gate >= 0.030:       # relaxed spawn rate -> subtle
            self._trail_gate = now
            self._trail(x, y)

    def _on_press(self, e):
        pos = self._local(e.x_root, e.y_root)
        if pos is None or not self._inside(*pos):
            return
        self.mouse_down = True
        self.last_xy = pos
        self._pulse_clock = 0
        self._burst(*pos)                         # the satisfying click pop

    def _on_release(self, e):
        # RELEASE -> hold-pulse stops + everything fades out fast
        self.mouse_down = False
        for p in self.particles:
            p["decay"] = max(p["decay"], 0.12)    # rapid fade-out
        pos = self._local(e.x_root, e.y_root)
        if pos and self._inside(*pos):            # one last soft dissolve ring
            self._spawn(kind="ring", x=pos[0], y=pos[1], r=4, grow=1.6,
                        life=0.55, decay=0.10, hue=self._theme_hue(0.0))

    # ==========================================================================
    # THE ~60 FPS RENDER LOOP  (single after() timer, capped particles)
    # ==========================================================================
    def _tick(self):
        cv = self.canvas
        if cv is None:
            return
        try:
            if not cv.winfo_exists():
                return

            # hide the topmost overlay whenever the app itself loses focus,
            # so it never floats above OTHER applications
            if self.overlay is not None:
                focused = self.root.focus_displayof() is not None
                mapped = self.overlay.state() == "normal"
                if focused and not mapped:
                    self.overlay.deiconify()
                    self._sync_geometry()
                elif not focused and mapped:
                    self.overlay.withdraw()

            cv.delete("fx")
            self.hue = (self.hue + 0.012) % 1.0

            # keep emitting a gentle pulse while the button stays pressed
            # (slower rhythm = calm breathing, not strobing)
            if self.mouse_down and self.last_xy:
                self._pulse_clock += 1
                if self._pulse_clock % 14 == 0:
                    self._hold_pulse(*self.last_xy)

            alive = []
            for p in self.particles:
                p["life"] -= p["decay"]
                if p["life"] <= 0:
                    continue
                p["x"] += p.get("vx", 0.0)
                p["y"] += p.get("vy", 0.0)
                if "grav" in p:
                    p["vy"] = p.get("vy", 0.0) + p["grav"]
                v = max(0.0, min(1.0, p["life"]))          # fade via brightness
                col = _hsv_hex(p["hue"], 0.65, v * 0.9)    # softer, dimmer glow

                if p["kind"] == "ring":                    # expanding ripple
                    p["r"] += p["grow"]
                    w = max(1, int(2 * v))
                    cv.create_oval(p["x"] - p["r"], p["y"] - p["r"],
                                   p["x"] + p["r"], p["y"] + p["r"],
                                   outline=col, width=w, tags="fx")
                else:                                      # glow dot / spark
                    r = p["r"] * (0.4 + 0.6 * v)
                    cv.create_oval(p["x"] - r, p["y"] - r,
                                   p["x"] + r, p["y"] + r,
                                   fill=col, outline="", tags="fx")
                alive.append(p)
            self.particles = alive
        except Exception:
            pass
        self.root.after(self.FRAME_MS, self._tick)


class FileManagerApp:
    def __init__(self, root):
        # ----------------------------------------------------------------------
        # 3.1  Window setup + HIGH-RESOLUTION sharpness
        # ----------------------------------------------------------------------
        self.root = root
        root.title("Virtual File Manager - File Allocation Simulator (OS Project)")
        root.geometry("1240x760")
        root.minsize(1080, 680)
        root.configure(bg=C["bg"])

        # Windows high-DPI fix -> crisp text instead of blurry scaling
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass  # not on Windows - ignore
        root.tk.call("tk", "scaling", 1.4)  # sharper widget rendering

        self.disk = VirtualDisk(64)      # 64 blocks -> 8 x 8 grid
        self.GRID_COLS = 8
        self.file_colors = {}            # file name -> colour
        self.color_i = 0
        self.animating = False           # blocks animation lock
        self.editing_file = None         # file currently opened for editing
        self._hue = 0.0                  # rolling hue for the RGB animations
        self._rgb_targets = []           # widgets that colour-cycle

        # ----------------------------------------------------------------------
        # 3.2  Dark ttk theme (tables, comboboxes, tabs, scrollbars)
        # ----------------------------------------------------------------------
        self._style_ttk()

        # ----------------------------------------------------------------------
        # 3.3  Build every part of the interface
        # ----------------------------------------------------------------------
        self._build_menubar()
        self._build_header()
        self._build_body()
        self._build_log()
        self._refresh_all()
        self._animate_rgb()              # start the neon RGB colour cycle

        # ----------------------------------------------------------------------
        # 3.4  Start the CURSOR ANIMATION ENGINE (subtle theme-coloured trail,
        #      soft click ripple, gentle hold pulse). Falls back to the disk
        #      canvas if transparent overlay windows are unsupported.
        # ----------------------------------------------------------------------
        self.fx = CursorFX(root, fallback_canvas=self.canvas)

        # ----------------------------------------------------------------------
        # 3.5  Start the SOUND ENGINE + hook the audio to the UI:
        #        - every press on a clickable control -> mouse "click" snap
        #        - every keystroke in a typeable field -> keyboard "tick"
        #      Typeable fields also get a live neon TYPING GLOW animation.
        # ----------------------------------------------------------------------
        self.sound = SoundFX()
        root.bind_all("<ButtonPress-1>", self._click_sound, add="+")
        for w in (self.name_entry, self.content_box, self.search_entry):
            self._attach_typing_fx(w)

    # ==========================================================================
    # 3.5-A  MOUSE CLICK SOUND - only on truly CLICKABLE controls
    # ==========================================================================
    def _click_sound(self, e):
        try:
            w = e.widget
            cls = w.winfo_class()
        except Exception:
            return
        # buttons, dropdowns, file list rows, menus, tabs, scrollbars ...
        if cls in ("Button", "TCombobox", "Treeview", "Menu", "Menubutton",
                   "TButton", "Checkbutton", "Radiobutton", "TNotebook",
                   "Scrollbar", "TScrollbar", "Listbox"):
            self.sound.click()
            return
        # ... plus anything styled as clickable (link labels use cursor=hand2)
        try:
            if str(w.cget("cursor")) == "hand2":
                self.sound.click()
        except Exception:
            pass

    # ==========================================================================
    # 3.5-B  TYPING FX - sound tick + neon border glow + caret spark
    # --------------------------------------------------------------------------
    #  Every REAL keystroke (letters, digits, space, backspace...) in a
    #  typeable field:
    #    1. plays the soft keyboard tick            (audio feedback)
    #    2. flashes the field's border bright neon,
    #       then fades it back over 4 gentle steps  (visual feedback)
    #    3. pops ONE tiny spark right at the caret  (subtle, theme colour)
    # ==========================================================================
    def _attach_typing_fx(self, widget):
        fade = [C["neon"], "#37B8D8", "#2A7FA8", C["border"]]  # neon -> border
        state = {"job": None}

        def _fade_step(i):
            try:
                if i < len(fade):
                    widget.config(highlightbackground=fade[i],
                                  highlightcolor=fade[0])
                    state["job"] = widget.after(70, _fade_step, i + 1)
                else:
                    widget.config(highlightbackground=C["border"],
                                  highlightcolor=C["neon"])
                    state["job"] = None
            except Exception:
                pass

        def on_key(e):
            # ignore pure modifier keys (Shift/Ctrl/Alt...) - no char typed
            if not (e.char or e.keysym in ("BackSpace", "Delete", "Return",
                                           "space", "Tab")):
                return
            self.sound.key()                       # 1) keyboard tick
            if state["job"] is not None:           # 2) restart border glow
                try:
                    widget.after_cancel(state["job"])
                except Exception:
                    pass
            _fade_step(0)
            try:                                   # 3) one caret spark
                bbox = widget.bbox("insert")
                if bbox:
                    self.fx.type_spark(widget.winfo_rootx() + bbox[0] + 2,
                                       widget.winfo_rooty() + bbox[1])
            except Exception:
                pass

        widget.bind("<KeyPress>", on_key, add="+")

    # ==========================================================================
    # PHASE 3-STYLE : dark theme for all ttk widgets
    # ==========================================================================
    def _style_ttk(self):
        st = ttk.Style(self.root)
        try:
            st.theme_use("clam")
        except Exception:
            pass

        st.configure("Treeview",
                     background=C["glass"], fieldbackground=C["glass"],
                     foreground=C["text"], bordercolor=C["border"],
                     borderwidth=0, rowheight=26, font=("Segoe UI", 9))
        st.configure("Treeview.Heading",
                     background=C["glass2"], foreground=C["neon"],
                     bordercolor=C["border"], relief="flat",
                     font=("Segoe UI", 9, "bold"))
        st.map("Treeview",
               background=[("selected", "#16325A")],
               foreground=[("selected", C["neon"])])
        st.map("Treeview.Heading", background=[("active", C["glass2"])])

        st.configure("TCombobox",
                     fieldbackground=C["glass2"], background=C["glass2"],
                     foreground=C["text"], arrowcolor=C["neon"],
                     bordercolor=C["border"], lightcolor=C["glass2"],
                     darkcolor=C["glass2"], selectbackground=C["glass2"],
                     selectforeground=C["neon"])
        st.map("TCombobox",
               fieldbackground=[("readonly", C["glass2"])],
               foreground=[("readonly", C["text"])])
        self.root.option_add("*TCombobox*Listbox.background", C["glass2"])
        self.root.option_add("*TCombobox*Listbox.foreground", C["text"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#16325A")
        self.root.option_add("*TCombobox*Listbox.selectForeground", C["neon"])

        st.configure("TNotebook", background=C["bg"], borderwidth=0)
        st.configure("TNotebook.Tab", background=C["glass"],
                     foreground=C["muted"], padding=(14, 6),
                     font=("Segoe UI", 9, "bold"))
        st.map("TNotebook.Tab",
               background=[("selected", C["glass2"])],
               foreground=[("selected", C["neon"])])

        st.configure("Vertical.TScrollbar", background=C["glass2"],
                     troughcolor=C["bg"], bordercolor=C["bg"],
                     arrowcolor=C["muted"])

    # ==========================================================================
    # GLASS PANEL FACTORY - a modern "frosted card" replacement for LabelFrame
    # (Tkinter cannot blur, so we fake glass with layered dark fills, a thin
    #  luminous border and a neon caption pill.)
    # ==========================================================================
    def _glass_card(self, parent, title, accent=None, **pack_kw):
        accent = accent or C["neon"]
        outer = tk.Frame(parent, bg=C["border"], padx=1, pady=1)  # glow edge
        outer.pack(**pack_kw)
        card = tk.Frame(outer, bg=C["glass"])
        card.pack(fill="both", expand=True)

        cap = tk.Frame(card, bg=C["glass"])
        cap.pack(fill="x", padx=12, pady=(10, 2))
        dot = tk.Label(cap, text="\u25CF", bg=C["glass"], fg=accent,
                       font=("Segoe UI", 8))
        dot.pack(side="left")
        lbl = tk.Label(cap, text=" " + title, bg=C["glass"], fg=C["text"],
                       font=("Segoe UI", 10, "bold"))
        lbl.pack(side="left")
        tk.Frame(card, bg=C["border"], height=1).pack(fill="x", padx=12,
                                                      pady=(6, 4))
        return outer, card

    # ----- CLICK MICRO-ANIMATION : bright press flash -> settle back ----------
    # (press = instant bright flash, release = quick 2-step fade back, so every
    #  clickable option "pops" in sync with the cursor burst effect)
    def _press_anim(self, btn, base_bg, base_fg, flash_bg=None, flash_fg=None):
        flash_bg = flash_bg or C["text"]
        flash_fg = flash_fg or "#04070F"

        def on_press(_):
            if btn["state"] != "disabled":
                btn.config(bg=flash_bg, fg=flash_fg)

        def on_release(_):
            if btn["state"] == "disabled":
                return
            # 2-step fade: bright -> hover tint -> base colour
            btn.config(bg=flash_bg, fg=flash_fg)
            btn.after(90, lambda: btn["state"] != "disabled"
                      and btn.config(bg=base_bg, fg=base_fg))

        btn.bind("<ButtonPress-1>", on_press, add="+")
        btn.bind("<ButtonRelease-1>", on_release, add="+")

    # ----- neon flat button with hover glow + press-flash animation -----------
    def _neon_btn(self, parent, text, command, color, fg="#04070F", **pack_kw):
        btn = tk.Button(parent, text=text, command=command,
                        bg=color, fg=fg, activebackground=C["text"],
                        activeforeground="#04070F",
                        font=("Segoe UI", 10, "bold"),
                        relief="flat", bd=0, cursor="hand2", pady=6)
        btn.pack(**pack_kw)

        def on_in(_):
            if btn["state"] != "disabled":
                btn.config(bg=C["text"])

        def on_out(_):
            if btn["state"] != "disabled":
                btn.config(bg=color)

        btn.bind("<Enter>", on_in)
        btn.bind("<Leave>", on_out)
        self._press_anim(btn, base_bg=color, base_fg=fg)
        return btn

    # ----- "ghost" glass button (outlined, translucent-looking) ---------------
    def _ghost_btn(self, parent, text, command, accent, **pack_kw):
        wrap = tk.Frame(parent, bg=accent, padx=1, pady=1)
        wrap.pack(**pack_kw)
        btn = tk.Button(wrap, text=text, command=command,
                        bg=C["glass2"], fg=accent,
                        activebackground=accent, activeforeground="#04070F",
                        font=("Segoe UI", 10, "bold"),
                        relief="flat", bd=0, cursor="hand2", pady=5)
        btn.pack(fill="both", expand=True)

        btn.bind("<Enter>", lambda e: btn.config(bg="#16325A"))
        btn.bind("<Leave>", lambda e: btn.config(bg=C["glass2"]))
        # press flash: fill with the accent colour while held, fade back after
        self._press_anim(btn, base_bg=C["glass2"], base_fg=accent,
                         flash_bg=accent, flash_fg="#04070F")
        return btn

    # ==========================================================================
    # PHASE 3A : MENU BAR with FILE / HELP / ABOUT menus
    # ==========================================================================
    def _build_menubar(self):
        menubar = tk.Menu(self.root, bg=C["glass"], fg=C["text"],
                          activebackground="#16325A",
                          activeforeground=C["neon"], bd=0)

        filemenu = tk.Menu(menubar, tearoff=0, bg=C["glass"], fg=C["text"],
                           activebackground="#16325A",
                           activeforeground=C["neon"])
        filemenu.add_command(label="New File (clear editor)", command=self.on_new)
        filemenu.add_command(label="Reset Disk", command=self.on_reset)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.destroy)
        menubar.add_cascade(label="File", menu=filemenu)

        helpmenu = tk.Menu(menubar, tearoff=0, bg=C["glass"], fg=C["text"],
                           activebackground="#16325A",
                           activeforeground=C["neon"])
        helpmenu.add_command(label="How to Use (step by step)",
                             command=lambda: self._show_help(0))
        helpmenu.add_command(label="How the Algorithms Work",
                             command=lambda: self._show_help(1))
        helpmenu.add_command(label="What is a Block?",
                             command=lambda: self._show_help(2))
        menubar.add_cascade(label="Help", menu=helpmenu)

        # ----- ABOUT menu (sits right beside the Help menu) -------------------
        aboutmenu = tk.Menu(menubar, tearoff=0, bg=C["glass"], fg=C["text"],
                            activebackground="#16325A",
                            activeforeground=C["neon"])
        aboutmenu.add_command(label="About This App", command=self._show_about)
        menubar.add_cascade(label="About", menu=aboutmenu)

        self.root.config(menu=menubar)

    # ==========================================================================
    # PHASE 3B : HEADER BAR - animated RGB gradient title on a glass strip
    # ==========================================================================
    def _build_header(self):
        head = tk.Frame(self.root, bg=C["bg2"], height=62)
        head.pack(fill="x")
        head.pack_propagate(False)
        tk.Frame(self.root, bg=C["border"], height=1).pack(fill="x")

        # The title is drawn on a Canvas so EVERY LETTER can carry its own hue,
        # producing a smooth animated RGB gradient across the text.
        self.title_canvas = tk.Canvas(head, bg=C["bg2"], highlightthickness=0,
                                      width=460, height=62)
        self.title_canvas.pack(side="left", padx=(16, 0))
        self._title_text = "File Management & Allocation Simulator"
        self._title_items = []
        x = 0
        for ch in self._title_text:
            item = self.title_canvas.create_text(
                x, 31, text=ch, anchor="w", fill=C["neon"],
                font=("Segoe UI", 15, "bold"))
            bbox = self.title_canvas.bbox(item)
            x = bbox[2] + 1
            self._title_items.append(item)
        # auto-fit the canvas to the full title so no letters get cut off
        self.title_canvas.config(width=x + 4)

        right = tk.Frame(head, bg=C["bg2"])
        right.pack(side="right", padx=16)
        tk.Label(right, text="CONTIGUOUS  \u00B7  LINKED  \u00B7  INDEXED",
                 bg=C["bg2"], fg=C["neon"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="e")
        tk.Label(right, text="Disk: 64 blocks x 32 bytes = 2048 bytes",
                 bg=C["bg2"], fg=C["muted"],
                 font=("Segoe UI", 9)).pack(anchor="e")

    # ==========================================================================
    # PHASE 3B-2 : THE RGB / NEON ANIMATION ENGINE
    # A rolling hue is advanced every 70 ms. The header title gets a per-letter
    # gradient; every widget registered in self._rgb_targets colour-cycles too.
    # ==========================================================================
    def _animate_rgb(self):
        self._hue = (self._hue + 0.006) % 1.0

        # per-letter animated gradient across the title
        n = max(len(self._title_items), 1)
        for i, item in enumerate(self._title_items):
            hue = self._hue + (i / n) * 0.45      # gradient spread
            self.title_canvas.itemconfig(item, fill=_hsv_hex(hue, 0.85, 1.0))

        # any registered labels (e.g. the signature) cycle as one colour
        col = _hsv_hex(self._hue, 0.8, 1.0)
        for w in self._rgb_targets:
            try:
                w.config(fg=col)
            except Exception:
                pass

        self.root.after(70, self._animate_rgb)

    # ==========================================================================
    # PHASE 3C : MAIN BODY = editor (left) + disk grid (center) + files (right)
    # ==========================================================================
    def _build_body(self):
        body = tk.Frame(self.root, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=12, pady=10)

        self._build_editor(body)     # LEFT
        self._build_diskview(body)   # CENTER
        self._build_filelist(body)   # RIGHT

    # --------------------------------------------------------------------------
    # 3C-1 : LEFT PANEL - the FILE EDITOR (glass card)
    # --------------------------------------------------------------------------
    def _build_editor(self, parent):
        _, card = self._glass_card(parent, "CREATE / EDIT FILE",
                                   accent=C["green"],
                                   side="left", fill="y", padx=(0, 10))
        inner = tk.Frame(card, bg=C["glass"], padx=12, pady=4)
        inner.pack(fill="both", expand=True)

        row = tk.Frame(inner, bg=C["glass"])
        row.pack(fill="x", pady=(2, 8))
        tk.Label(row, text="Name", bg=C["glass"], fg=C["muted"],
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.name_entry = tk.Entry(row, width=14, font=("Segoe UI", 10),
                                   bg=C["glass2"], fg=C["text"],
                                   insertbackground=C["neon"],
                                   relief="flat",
                                   highlightthickness=1,
                                   highlightbackground=C["border"],
                                   highlightcolor=C["neon"])
        self.name_entry.pack(side="left", padx=6, ipady=3)
        self.ext_var = tk.StringVar(value=".txt")
        ttk.Combobox(row, textvariable=self.ext_var, values=EXTENSIONS,
                     width=6, state="readonly").pack(side="left")

        tk.Label(inner, text="Content  \u2014  type & watch blocks grow live",
                 bg=C["glass"], fg=C["muted"],
                 font=("Segoe UI", 9)).pack(anchor="w")

        # the content text box - every keystroke triggers the live size meter
        self.content_box = tk.Text(inner, width=34, height=13,
                                   font=("Consolas", 10),
                                   bg=C["glass2"], fg=C["text"],
                                   insertbackground=C["neon"],
                                   selectbackground="#16325A",
                                   selectforeground=C["neon"],
                                   relief="flat",
                                   highlightthickness=1,
                                   highlightbackground=C["border"],
                                   highlightcolor=C["neon"],
                                   wrap="word", undo=True)
        self.content_box.pack(pady=6)
        self.content_box.bind("<KeyRelease>", lambda e: self._update_meter())

        # LIVE METER : bytes typed -> blocks needed (neon cyan, updates live)
        self.meter = tk.Label(inner, text="", bg=C["glass"], fg=C["neon"],
                              font=("Segoe UI", 10, "bold"))
        self.meter.pack(anchor="w", pady=(0, 8))

        # allocation method chooser
        mrow = tk.Frame(inner, bg=C["glass"])
        mrow.pack(fill="x", pady=(0, 8))
        tk.Label(mrow, text="Algorithm", bg=C["glass"], fg=C["muted"],
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.method_var = tk.StringVar(value="Contiguous")
        ttk.Combobox(mrow, textvariable=self.method_var, width=12,
                     state="readonly",
                     values=["Contiguous", "Linked", "Indexed"]
                     ).pack(side="left", padx=6)
        # switching algorithm changes the block maths (Linked loses 4 B/block
        # to its next-pointer) -> refresh the live meter immediately
        self.method_var.trace_add("write", lambda *a: self._update_meter())

        # action buttons (neon)
        self.save_btn = self._neon_btn(inner, "SAVE FILE TO DISK",
                                       self.on_save, C["green"],
                                       fill="x", pady=3)
        self._ghost_btn(inner, "COMPARE ALL 3 ALGORITHMS",
                        self.on_compare, C["amber"], fill="x", pady=3)
        self._ghost_btn(inner, "NEW / CLEAR EDITOR", self.on_new,
                        C["muted"], fill="x", pady=(3, 10))

        self._update_meter()

    # --------------------------------------------------------------------------
    # 3C-2 : CENTER PANEL - the DISK GRID (canvas) + usage stats
    # --------------------------------------------------------------------------
    def _build_diskview(self, parent):
        mid = tk.Frame(parent, bg=C["bg"])
        mid.pack(side="left", fill="both", expand=True, padx=(0, 10))

        _, card = self._glass_card(mid, "DISK BLOCKS \u2014 LIVE VIEW",
                                   accent=C["neon"],
                                   fill="both", expand=True)
        self.canvas = tk.Canvas(card, bg=C["glass"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.canvas.bind("<Configure>", lambda e: self._draw_disk())

        self.stats = tk.Label(mid, text="", bg=C["bg"], fg=C["text"],
                              font=("Segoe UI", 10, "bold"))
        self.stats.pack(pady=(8, 0))

    # --------------------------------------------------------------------------
    # 3C-3 : RIGHT PANEL - the FILE MANAGER (list of saved files)
    # --------------------------------------------------------------------------
    def _build_filelist(self, parent):
        outer, card = self._glass_card(parent, "FILES ON DISK",
                                       accent=C["pink"],
                                       side="right", fill="y")
        outer.configure(width=332)
        outer.pack_propagate(False)

        # ----- selection-mode state -------------------------------------------
        self.multi_mode = False           # "SELECT MULTIPLE" toggle state
        self.quick_delete_armed = False   # armed after a right-drag selection
        self._rdrag_anchor = None         # first row hit by a right-drag

        # ----- SEARCH BAR : find a created file live by its name ---------------
        srow = tk.Frame(card, bg=C["glass"])
        srow.pack(fill="x", padx=10, pady=(4, 2))
        tk.Label(srow, text="Search", bg=C["glass"], fg=C["muted"],
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(srow, textvariable=self.search_var,
                                     font=("Segoe UI", 10),
                                     bg=C["glass2"], fg=C["text"],
                                     insertbackground=C["pink"],
                                     relief="flat",
                                     highlightthickness=1,
                                     highlightbackground=C["border"],
                                     highlightcolor=C["pink"])
        self.search_entry.pack(side="left", fill="x", expand=True,
                               padx=6, ipady=3)
        # every keystroke re-filters the file table instantly
        self.search_var.trace_add("write", lambda *a: self._refresh_table())

        cols = ("name", "size", "blocks", "method")
        self.tree = ttk.Treeview(card, columns=cols, show="headings",
                                 height=15, selectmode="browse")
        for col, txt, w in (("name", "File", 92), ("size", "Bytes", 52),
                            ("blocks", "Blocks", 52), ("method", "Method", 84)):
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(4, 8))
        # double-click a file to open it in the editor
        self.tree.bind("<Double-1>", lambda e: self.on_open())
        # selecting ONE file makes the "SELECT MULTIPLE" button appear
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        # single left-click: multi-mode toggle-select + quick-delete trigger
        self.tree.bind("<Button-1>", self._on_tree_click)
        # HOLD RIGHT-CLICK + DRAG over the rows to rubber-band select files,
        # release, then ONE left-click on the selection deletes them all
        self.tree.bind("<ButtonPress-3>", self._on_rdrag_start)
        self.tree.bind("<B3-Motion>", self._on_rdrag_motion)
        self.tree.bind("<ButtonRelease-3>", self._on_rdrag_end)

        # "SELECT MULTIPLE" button lives in this slot; it is hidden until the
        # user selects a single file (then it pops in, as requested)
        self.multi_slot = tk.Frame(card, bg=C["glass"])
        self.multi_slot.pack(fill="x", padx=10)
        self.multi_btn = self._ghost_btn(self.multi_slot, "SELECT MULTIPLE",
                                         self.on_toggle_multi, C["amber"],
                                         fill="x", pady=2)
        self._multi_wrap = self.multi_btn.master   # the neon-edge wrapper
        self._multi_wrap.pack_forget()             # hidden by default

        btns = tk.Frame(card, bg=C["glass"])
        btns.pack(fill="x", padx=10, pady=(0, 10))
        self._ghost_btn(btns, "OPEN SELECTED", self.on_open,
                        C["neon"], fill="x", pady=2)
        self._ghost_btn(btns, "DELETE SELECTED", self.on_delete,
                        C["red"], fill="x", pady=2)

    # --------------------------------------------------------------------------
    # 3C-3a : SELECTION HELPERS (search / multi-select / right-drag delete)
    # --------------------------------------------------------------------------
    def _on_tree_select(self, _event=None):
        """Show the SELECT MULTIPLE button when exactly ONE file is picked."""
        if self.multi_mode:
            return
        sel = self.tree.selection()
        if len(sel) == 1:
            self._multi_wrap.pack(fill="x", pady=2)
        elif not sel:
            self._multi_wrap.pack_forget()

    def on_toggle_multi(self):
        """Toggle multi-select mode (for DELETE only - open stays single)."""
        self.multi_mode = not self.multi_mode
        if self.multi_mode:
            self.tree.configure(selectmode="extended")
            self.multi_btn.config(text="EXIT MULTI-SELECT")
            self._log("Multi-select ON: click files to add/remove them from "
                      "the selection. Works for DELETE only - opening "
                      "multiple files shows an error.")
        else:
            self.tree.configure(selectmode="browse")
            self.multi_btn.config(text="SELECT MULTIPLE")
            for item in self.tree.selection():
                self.tree.selection_remove(item)
            self._multi_wrap.pack_forget()
            self.quick_delete_armed = False
            self._log("Multi-select OFF: back to single selection.")

    def _on_tree_click(self, event):
        """One handler for LEFT clicks on the file list.

        1) QUICK DELETE : after a right-click drag selection, ONE left click
           on any selected file instantly deletes the whole selection.
        2) MULTI-SELECT : in multi mode a plain click TOGGLES the clicked
           row in/out of the selection (no Ctrl key needed).
        """
        row = self.tree.identify_row(event.y)
        if self.quick_delete_armed:
            self.quick_delete_armed = False
            sel = self.tree.selection()
            if row and row in sel:
                self._delete_items(sel)
                return "break"
            # clicked away from the selection -> disarm and behave normally
            if not self.multi_mode:
                self.tree.configure(selectmode="browse")
            self._log("Quick-delete cancelled (clicked outside the "
                      "right-drag selection).")
        if self.multi_mode:
            if row:
                if row in self.tree.selection():
                    self.tree.selection_remove(row)
                else:
                    self.tree.selection_add(row)
            return "break"

    def _on_rdrag_start(self, event):
        """RIGHT button pressed: start a rubber-band selection at this row."""
        row = self.tree.identify_row(event.y)
        self.quick_delete_armed = False
        self._rdrag_anchor = row or None
        if row:
            # extended mode lets us programmatically select a whole range
            self.tree.configure(selectmode="extended")
            self.tree.selection_set(row)
        return "break"

    def _on_rdrag_motion(self, event):
        """RIGHT button held + mouse dragged: live-select the swept rows."""
        if not self._rdrag_anchor:
            return "break"
        row = self.tree.identify_row(event.y)
        if not row:
            return "break"
        kids = self.tree.get_children()
        try:
            a = kids.index(self._rdrag_anchor)
            b = kids.index(row)
        except ValueError:
            return "break"
        if a > b:
            a, b = b, a
        self.tree.selection_set(kids[a:b + 1])
        return "break"

    def _on_rdrag_end(self, _event):
        """RIGHT button released: ARM quick delete - one left click kills."""
        if self._rdrag_anchor is None:
            return "break"
        self._rdrag_anchor = None
        sel = self.tree.selection()
        if sel:
            self.quick_delete_armed = True
            self._log(f"{len(sel)} file(s) selected by right-click drag. "
                      "Move the cursor onto the highlighted files and "
                      "LEFT-CLICK ONCE to delete them all.")
        elif not self.multi_mode:
            self.tree.configure(selectmode="browse")
        return "break"

    def _delete_items(self, items):
        """Delete every given tree row's file and free its blocks."""
        names = [str(self.tree.item(i)["values"][0]) for i in items]
        for name in names:
            ok, msg = self.disk.delete_file(name)
            self._log(msg)
            if self.editing_file == name:
                self.editing_file = None
        if len(names) > 1:
            self._log(f"Deleted {len(names)} files in one action.")
        if not self.multi_mode:
            self.tree.configure(selectmode="browse")
        self._refresh_all()

    # ==========================================================================
    # PHASE 3D : ACTIVITY LOG at the bottom (neon terminal style)
    # ==========================================================================
    def _build_log(self):
        _, card = self._glass_card(self.root,
                                   "ACTIVITY LOG \u2014 WHAT THE OS IS DOING",
                                   accent=C["amber"],
                                   side="bottom", fill="x",
                                   padx=12, pady=(0, 10))
        self.log = tk.Text(card, height=5, font=("Consolas", 9),
                           bg="#050810", fg=C["green"],
                           insertbackground=C["green"],
                           selectbackground="#16325A", relief="flat")
        self.log.pack(fill="x", padx=10, pady=(4, 10))
        self._log("Welcome! Type a file name + content on the left, pick an "
                  "algorithm and press 'SAVE FILE TO DISK'. Open Help for a guide.")

    # ==========================================================================
    # PHASE 4 : LIVE SIZE METER  (bytes typed -> blocks needed, in real time)
    # ==========================================================================
    def _update_meter(self):
        content = self.content_box.get("1.0", "end-1c")
        method = self.method_var.get()
        blocks, size = VirtualDisk.blocks_needed(content, method)
        if method == "Indexed":
            extra = " (+1 index block)"
            per = f"[{VirtualDisk.BLOCK_SIZE} B data/block]"
        elif method == "Linked":
            extra = ""
            per = (f"[{VirtualDisk.LINKED_PAYLOAD} B data/block, "
                   f"{VirtualDisk.POINTER_SIZE} B = next-pointer]")
        else:
            extra = ""
            per = f"[{VirtualDisk.BLOCK_SIZE} B data/block]"
        self.meter.config(
            text=f"Size: {size} bytes  \u2192  needs {blocks} block(s){extra}  "
                 f"{per}")

    # ==========================================================================
    # PHASE 5 : EVENT HANDLERS (what happens when the user clicks)
    # ==========================================================================

    # ----- helper: full file name from the two inputs -------------------------
    def _full_name(self):
        return self.name_entry.get().strip() + self.ext_var.get()

    # --------------------------------------------------------------------------
    # 5.1 SAVE : validate -> plan blocks -> ANIMATE occupation -> commit
    # --------------------------------------------------------------------------
    def on_save(self):
        if self.animating:
            return
        name = self._full_name()
        if not self.name_entry.get().strip():
            messagebox.showerror("Missing name", "Please enter a file name.")
            return
        content = self.content_box.get("1.0", "end-1c")
        method = self.method_var.get()
        blocks, size = VirtualDisk.blocks_needed(content, method)

        # if we are re-saving an opened file, delete its old blocks first
        if self.editing_file and self.editing_file in self.disk.files:
            self.disk.delete_file(self.editing_file)
            self._log(f"Re-saving '{self.editing_file}' - old blocks freed.")
            self.editing_file = None
        elif name in self.disk.files:
            messagebox.showerror("Duplicate", f"'{name}' already exists. "
                                 "Open it to edit, or use another name.")
            return

        # ask the algorithm WHERE the file would go
        planned, err = self.disk.plan(method, blocks)
        if planned is None:
            self._log(f"FAILED to save '{name}' with {method}: {err}")
            messagebox.showwarning("Allocation failed",
                                   f"{method} allocation failed:\n{err}")
            self._refresh_all()
            return

        # give the file a colour and animate blocks filling one-by-one
        if name not in self.file_colors:
            self.file_colors[name] = FILE_COLORS[self.color_i % len(FILE_COLORS)]
            self.color_i += 1

        if method == "Contiguous":
            detail = (f"one contiguous run: start={planned[0]}, "
                      f"length={len(planned)}")
        elif method == "Linked":
            detail = ("scattered chain: " +
                      " -> ".join(str(b) for b in planned) + " -> EOF")
        else:
            detail = (f"index block {planned[0]} points to data blocks "
                      f"{planned[1:]}")
        self._log(f"Saving '{name}' ({size} bytes = {blocks} data blocks) "
                  f"using {method} -> {detail} ...")
        self._animate_allocation(name, content, method, planned)

    # --------------------------------------------------------------------------
    # 5.2 THE ANIMATION : occupy planned blocks ONE BY ONE (simulated time)
    # --------------------------------------------------------------------------
    def _animate_allocation(self, name, content, method, planned, i=0):
        self.animating = True
        self.save_btn.config(state="disabled", bg=C["glass2"], fg=C["muted"])
        if i < len(planned):
            b = planned[i]
            self.disk.blocks[b] = name       # occupy this one block now
            self._draw_disk(highlight=b)
            self._update_stats()
            # 120 ms pause before the next block -> visible "real time" effect
            self.root.after(120, lambda: self._animate_allocation(
                name, content, method, planned, i + 1))
        else:
            # all blocks placed -> register the file officially
            for b in planned:                # undo temp marks, commit properly
                self.disk.blocks[b] = None
            self.disk.commit(name, content, method, planned)
            self.animating = False
            self.save_btn.config(state="normal", bg=C["green"], fg="#04070F")
            if method == "Contiguous":
                idx = f" (directory: start={planned[0]}, length={len(planned)})"
            elif method == "Linked":
                idx = (f" (directory: start={planned[0]}, end={planned[-1]}; "
                       f"chain: "
                       + " -> ".join(str(b) for b in planned) + " -> EOF)")
            else:
                idx = (f" (directory -> index block {planned[0]}; "
                       f"its table -> {planned[1:]})")
            self._log(f"DONE: '{name}' saved with {method}{idx}. "
                      f"Blocks used: {planned}")
            self._refresh_all()
            self.on_new(keep_log=True)

    # --------------------------------------------------------------------------
    # 5.3 OPEN : load the selected file back into the editor
    # --------------------------------------------------------------------------
    def on_open(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Open", "Select a file in the list first.")
            return
        # multi-select is for DELETE only - opening several files at once
        # is impossible (there is only ONE editor), so raise an error
        if len(sel) > 1:
            messagebox.showerror(
                "Cannot open multiple files",
                f"You selected {len(sel)} files, but only ONE file can be "
                "opened in the editor at a time.\n\n"
                "Multiple selection is for DELETE only. Please select a "
                "single file to open it.")
            self._log(f"ERROR: tried to open {len(sel)} files at once - "
                      "only one file can be opened at a time.")
            return
        name = str(self.tree.item(sel[0])["values"][0])
        f = self.disk.files[name]
        stem, dot, ext = name.rpartition(".")
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, stem)
        self.ext_var.set(dot + ext)
        self.content_box.delete("1.0", "end")
        self.content_box.insert("1.0", f["content"])
        self.method_var.set(f["method"])
        self.editing_file = name
        self._update_meter()
        self._log(f"Opened '{name}' for editing "
                  f"({f['size_bytes']} bytes in blocks {f['blocks']}).")

    # --------------------------------------------------------------------------
    # 5.4 DELETE : free the file's blocks
    # --------------------------------------------------------------------------
    def on_delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Delete", "Select a file in the list first.")
            return
        # multiple files may be selected (multi-select mode / right-drag) -
        # confirm once, then free EVERY selected file's blocks
        if len(sel) > 1:
            names = [str(self.tree.item(i)["values"][0]) for i in sel]
            if not messagebox.askyesno(
                    "Delete multiple files",
                    f"Delete these {len(names)} files and free all their "
                    "blocks?\n\n" + "\n".join(names)):
                return
        self._delete_items(sel)

    # --------------------------------------------------------------------------
    # 5.5 COMPARE : SPLIT-WINDOW comparison of ALL 3 algorithms side by side.
    #
    # Pressing "COMPARE ALL 3 ALGORITHMS" opens ONE window that is divided
    # into a 3-column GRID of equal panels (Contiguous | Linked | Indexed).
    # Every panel behaves EXACTLY like a single-algorithm save:
    #   - its own mini disk grid where the planned blocks get occupied
    #     ONE-BY-ONE in real simulated time (same animation as SAVE)
    #   - a "PROCESS" log that narrates each step the algorithm takes
    #   - the final "OUTPUT" directory metadata (start/length, pointer
    #     chain, or index table) - identical to the single-run result
    #
    # WHICH FILE gets compared (fetched automatically, in this order):
    #   1. the file currently in the EDITOR (name + content typed/opened)
    #   2. the file SELECTED in the "FILES ON DISK" list (content is
    #      fetched from the directory - exactly what was saved)
    #   3. the file currently being edited, or the MOST RECENTLY SAVED file
    # If the compared file already lives on the disk, its own blocks are
    # released first in the comparison snapshot (exactly like a re-save),
    # so all three algorithms plan from the same fair disk state.
    # --------------------------------------------------------------------------
    def on_compare(self):
        stem = self.name_entry.get().strip()
        content = self.content_box.get("1.0", "end-1c")

        if stem or content:
            # 1) the editor holds a file -> compare exactly what is typed
            if not stem:
                messagebox.showerror(
                    "Missing name",
                    "Please enter a file name for the content in the "
                    "editor (same as saving).")
                return
            name = stem + self.ext_var.get()
        else:
            # 2) editor is empty -> fetch a saved file from the disk
            target = None
            sel = self.tree.selection()
            if sel:
                target = self.tree.item(sel[0])["values"][0]
            elif self.editing_file in self.disk.files:
                target = self.editing_file
            elif self.disk.files:
                # fall back to the most recently saved file
                target = next(reversed(self.disk.files))
            if target is None:
                messagebox.showinfo(
                    "Compare",
                    "There is nothing to compare yet.\n\n"
                    "Type a file in the editor, or save a file and select "
                    "it in the 'FILES ON DISK' list, then press COMPARE.")
                return
            name = target
            content = self.disk.files[name]["content"]
            self._log(f"COMPARE: fetched '{name}' "
                      f"({self.disk.files[name]['size_bytes']} bytes) "
                      "from the disk directory.")

        _, size = VirtualDisk.blocks_needed(content)

        # Build the comparison SNAPSHOT of the disk. If the compared file is
        # already saved, release its own blocks in the snapshot (like a
        # re-save) so every algorithm plans from the same fair state.
        base = list(self.disk.blocks)
        if name in self.disk.files:
            for b in self.disk.files[name]["blocks"]:
                base[b] = None

        snapshot = VirtualDisk(self.disk.total_blocks)
        snapshot.blocks = base

        # plan every algorithm independently from the SAME snapshot
        results = {}
        summary = [f"Content size: {size} bytes"]
        for method in ("Contiguous", "Linked", "Indexed"):
            # each algorithm has its OWN block maths (Linked loses 4 B/block
            # to the next-pointer), so compute the need per method
            need, _ = VirtualDisk.blocks_needed(content, method)
            planned, err = snapshot.plan(method, need)
            results[method] = (need, planned, err)
            if planned is None:
                summary.append(f"{method:<11}: FAILS -> {err}")
            else:
                summary.append(f"{method:<11}: {len(planned)} blocks -> "
                               f"{planned}")
        self._log(f"Comparing '{name}' across all 3 algorithms:\n"
                  + "\n".join(summary))
        self._open_compare_window(name, size, results, base)

    # --------------------------------------------------------------------------
    # 5.5-A : build the split comparison window (3 equal glass panels)
    # --------------------------------------------------------------------------
    COMPARE_ORDER = ("Contiguous", "Linked", "Indexed")

    def _open_compare_window(self, name, size, results, base):
        # only ONE compare window at a time - close a stale one first
        if getattr(self, "_cmp_win", None) is not None:
            try:
                self._cmp_win.destroy()
            except Exception:
                pass
        win = tk.Toplevel(self.root)
        self._cmp_win = win
        win.title(f"Algorithm Comparison \u2014 {name}")
        win.configure(bg=C["bg"])
        win.geometry("1380x740")
        win.minsize(1020, 600)
        win.transient(self.root)

        accents = {"Contiguous": C["neon"],
                   "Linked":     C["green"],
                   "Indexed":    C["pink"]}

        # ----- header strip ----------------------------------------------------
        head = tk.Frame(win, bg=C["bg"])
        head.pack(fill="x", padx=14, pady=(10, 2))
        tk.Label(head, text="ALGORITHM COMPARISON \u2014 SPLIT VIEW",
                 bg=C["bg"], fg=C["amber"],
                 font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Label(head,
                 text=f"   file: {name}   |   content: {size} bytes",
                 bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(win,
                 text=f"Each panel allocates '{name}' with one algorithm on "
                      "an identical copy of the disk, exactly like pressing "
                      "SAVE. Dim blocks = other saved files. Coloured "
                      "blocks = this algorithm's allocation.",
                 bg=C["bg"], fg=C["muted"],
                 font=("Segoe UI", 9)).pack(fill="x", padx=14, pady=(0, 6))

        # ----- 3-column grid, equal width, resizes together --------------------
        grid = tk.Frame(win, bg=C["bg"])
        grid.pack(fill="both", expand=True, padx=10, pady=(0, 4))
        for c in range(3):
            grid.columnconfigure(c, weight=1, uniform="cmp")
        grid.rowconfigure(0, weight=1)

        for col, method in enumerate(self.COMPARE_ORDER):
            need, planned, err = results[method]
            self._build_compare_panel(grid, col, method, accents[method],
                                      size, need, planned, err, base)

        # ----- footer close button ---------------------------------------------
        foot = tk.Frame(win, bg=C["bg"])
        foot.pack(fill="x", padx=14, pady=(2, 10))
        self._ghost_btn(foot, "CLOSE COMPARISON", win.destroy,
                        C["amber"], side="right")

    # --------------------------------------------------------------------------
    # 5.5-B : one glass panel = one algorithm (title + mini grid + process log)
    # --------------------------------------------------------------------------
    def _build_compare_panel(self, parent, col, method, accent,
                             size, need, planned, err, base):
        outer = tk.Frame(parent, bg=accent, padx=1, pady=1)   # neon edge
        outer.grid(row=0, column=col, sticky="nsew", padx=5, pady=4)
        card = tk.Frame(outer, bg=C["glass"])
        card.pack(fill="both", expand=True)

        # ----- panel title: coloured dot + ALGORITHM NAME + live status --------
        cap = tk.Frame(card, bg=C["glass"])
        cap.pack(fill="x", padx=10, pady=(8, 2))
        tk.Label(cap, text="\u25CF", bg=C["glass"], fg=accent,
                 font=("Segoe UI", 9)).pack(side="left")
        tk.Label(cap, text=" " + method.upper() + " ALLOCATION",
                 bg=C["glass"], fg=C["text"],
                 font=("Segoe UI", 11, "bold")).pack(side="left")
        status = tk.Label(cap, text="PLANNING...", bg=C["glass"],
                          fg=C["amber"], font=("Segoe UI", 9, "bold"))
        status.pack(side="right")
        tk.Frame(card, bg=C["border"], height=1).pack(fill="x", padx=10,
                                                      pady=(4, 4))

        # ----- mini disk grid (same look as the main LIVE VIEW) -----------------
        cv = tk.Canvas(card, bg=C["glass"], highlightthickness=0, height=240)
        cv.pack(fill="both", expand=True, padx=10, pady=(2, 4))

        # ----- PROCESS + OUTPUT terminal ----------------------------------------
        txt = tk.Text(card, height=13, font=("Consolas", 8),
                      bg="#050810", fg=C["text"], relief="flat",
                      wrap="word", state="disabled")
        txt.pack(fill="x", padx=10, pady=(0, 10))
        txt.tag_config("h",   foreground=accent,
                       font=("Consolas", 8, "bold"))
        txt.tag_config("ok",  foreground=C["green"])
        txt.tag_config("err", foreground=C["red"])
        txt.tag_config("mut", foreground=C["muted"])

        def plog(line, tag=None):
            try:
                txt.config(state="normal")
                txt.insert("end", line + "\n", tag or ())
                txt.see("end")
                txt.config(state="disabled")
            except tk.TclError:
                pass  # window was closed mid-animation

        # panel animation state: how many planned blocks are placed so far
        state = {"placed": 0}

        def draw():
            self._draw_compare_disk(cv, method, accent, planned,
                                    state["placed"], base)
        cv.bind("<Configure>", lambda e: draw())

        # ----- 1) the block MATHS for this method (why N blocks?) ---------------
        plog("PROCESS", "h")
        if method == "Linked":
            plog(f"1. Block maths: {VirtualDisk.LINKED_PAYLOAD} B data/block "
                 f"({VirtualDisk.POINTER_SIZE} B lost to the next-pointer)")
            plog(f"   {size} B / {VirtualDisk.LINKED_PAYLOAD} B "
                 f"-> needs {need} block(s)", "mut")
        elif method == "Indexed":
            plog(f"1. Block maths: {VirtualDisk.BLOCK_SIZE} B data/block "
                 f"+ 1 extra INDEX block")
            plog(f"   {size} B / {VirtualDisk.BLOCK_SIZE} B "
                 f"-> {need} data block(s) + 1 index", "mut")
        else:
            plog(f"1. Block maths: {VirtualDisk.BLOCK_SIZE} B data/block")
            plog(f"   {size} B / {VirtualDisk.BLOCK_SIZE} B "
                 f"-> needs {need} block(s)", "mut")

        # ----- FAILURE : explain why, no animation ------------------------------
        if planned is None:
            status.config(text="FAILED", fg=C["red"])
            plog("2. " + ("First-fit scan of the disk..."
                          if method == "Contiguous"
                          else "Checking the free-block list..."))
            plog("ALLOCATION FAILED:", "err")
            plog(err, "err")
            plog("OUTPUT", "h")
            plog("No blocks allocated - the file cannot be stored "
                 "with this algorithm right now.", "err")
            draw()
            return

        # ----- 2) HOW the algorithm picked its blocks ---------------------------
        if method == "Contiguous":
            plog("2. First-fit scan left-to-right for a hole of "
                 f"{need} FREE blocks in a row...")
            plog(f"3. Hole found at block {planned[0]} "
                 f"(length {len(planned)}). Occupying one-by-one:")
        elif method == "Linked":
            plog(f"2. Grab ANY {need} free blocks (scattered is fine - "
                 "no external fragmentation).")
            plog("3. Chain them: each block stores a pointer to the "
                 "NEXT one. Occupying one-by-one:")
        else:
            plog(f"2. Grab 1 INDEX block + {need} scattered data blocks.")
            plog(f"3. Index block {planned[0]} will hold the pointer "
                 "table. Occupying one-by-one:")

        # ----- 3) the ANIMATION : occupy the planned blocks ONE BY ONE ----------
        # (identical pacing to the single-algorithm save animation)
        status.config(text="ALLOCATING...", fg=C["amber"])

        def step():
            try:
                if state["placed"] < len(planned):
                    b = planned[state["placed"]]
                    state["placed"] += 1
                    k, n = state["placed"], len(planned)
                    if method == "Indexed" and state["placed"] == 1:
                        plog(f"   block {b} reserved as INDEX block")
                    elif method == "Indexed":
                        plog(f"   block {b} -> pointer #{k - 1} stored "
                             f"in index ({k - 1}/{need})")
                    elif method == "Linked":
                        plog(f"   block {b} linked into chain ({k}/{n})")
                    else:
                        plog(f"   block {b} occupied ({k}/{n})")
                    draw()
                    cv.after(120, step)
                else:
                    # ----- 4) the OUTPUT : same directory metadata as a real save
                    status.config(text="DONE", fg=C["green"])
                    plog("OUTPUT", "h")
                    if method == "Contiguous":
                        plog(f"directory: start={planned[0]}, "
                             f"length={len(planned)}", "ok")
                    elif method == "Linked":
                        plog(f"directory: start={planned[0]}, "
                             f"end={planned[-1]}", "ok")
                        plog("chain: "
                             + " -> ".join(str(b) for b in planned)
                             + " -> EOF", "ok")
                    else:
                        plog(f"directory -> index block {planned[0]}", "ok")
                        plog(f"index table -> {planned[1:]}", "ok")
                    plog(f"Blocks used: {planned} "
                         f"(total {len(planned)})", "ok")
            except tk.TclError:
                pass  # compare window closed while animating - just stop

        # stagger the three panels slightly so the eye can follow all of them
        cv.after(350 + col * 250, step)

    # --------------------------------------------------------------------------
    # 5.5-C : draw one panel's mini disk grid.
    # Existing files are DIMMED so the new plan (accent colour) stands out.
    # Same markers as the main grid: * = index block, -> = has next-pointer,
    # filled square = end of chain (EOF).
    # --------------------------------------------------------------------------
    def _draw_compare_disk(self, cv, method, accent, planned, placed, base):
        try:
            cv.delete("all")
            w = max(cv.winfo_width(), 60)
            h = max(cv.winfo_height(), 60)
        except tk.TclError:
            return
        cols = self.GRID_COLS
        rows = math.ceil(self.disk.total_blocks / cols)
        pad = 4
        cell_w = (w - pad * 2) / cols
        cell_h = (h - pad * 2) / rows
        placed_set = set(planned[:placed]) if planned else set()
        last = planned[placed - 1] if planned and placed > 0 else None

        for i in range(self.disk.total_blocks):
            r, c0 = divmod(i, cols)
            x1 = pad + c0 * cell_w + 2
            y1 = pad + r * cell_h + 2
            x2 = pad + (c0 + 1) * cell_w - 2
            y2 = pad + (r + 1) * cell_h - 2
            owner = base[i]
            label = str(i)

            if i in placed_set:
                # a block claimed by THIS algorithm's allocation
                fill, outline, txt_col = "#0B1322", accent, accent
                if method == "Indexed" and i == planned[0]:
                    label = f"{i}*"
                elif method == "Linked":
                    pos = planned.index(i)
                    label = (f"{i}\u2192" if pos < len(planned) - 1
                             else f"{i}\u25A0")
                width = 3 if i == last else 2
            elif owner is not None:
                # existing file -> dimmed, so the new plan pops visually
                fill, outline, txt_col = "#0B1322", C["border"], C["muted"]
                width = 1
            else:
                fill, outline, txt_col = C["free"], C["freeline"], C["muted"]
                width = 1

            cv.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline,
                                width=width)
            cv.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=label,
                           fill=txt_col, font=("Segoe UI", 7, "bold"))

    # --------------------------------------------------------------------------
    # 5.6 NEW / CLEAR the editor
    # --------------------------------------------------------------------------
    def on_new(self, keep_log=False):
        self.name_entry.delete(0, "end")
        self.content_box.delete("1.0", "end")
        self.editing_file = None
        self._update_meter()
        if not keep_log:
            self._log("Editor cleared - ready for a new file.")

    # --------------------------------------------------------------------------
    # 5.7 RESET the whole disk
    # --------------------------------------------------------------------------
    def on_reset(self):
        if messagebox.askyesno("Reset disk",
                               "Erase ALL files and free every block?"):
            self.disk.reset()
            self.file_colors = {}
            self.color_i = 0
            self.editing_file = None
            self._log("Disk formatted - all 64 blocks are free.")
            self._refresh_all()

    # ==========================================================================
    # PHASE 6 : DRAWING - the neon disk grid, stats and file table
    # ==========================================================================
    def _draw_disk(self, highlight=None):
        cv = self.canvas
        cv.delete("all")
        w = max(cv.winfo_width(), 60)
        h = max(cv.winfo_height(), 60)
        cols = self.GRID_COLS
        rows = math.ceil(self.disk.total_blocks / cols)
        pad = 6
        cell_w = (w - pad * 2) / cols
        cell_h = (h - pad * 2) / rows

        for i in range(self.disk.total_blocks):
            r, c0 = divmod(i, cols)
            x1 = pad + c0 * cell_w + 3
            y1 = pad + r * cell_h + 3
            x2 = pad + (c0 + 1) * cell_w - 3
            y2 = pad + (r + 1) * cell_h - 3
            owner = self.disk.blocks[i]

            if owner is None:
                # free block = dark glass tile with a faint outline
                fill, outline, txt_col = C["free"], C["freeline"], C["muted"]
                label = str(i)
            else:
                # occupied block = dark tile with a NEON outline + neon number
                neon = self.file_colors.get(owner, "#7C8DB0")
                fill, outline, txt_col = "#0B1322", neon, neon
                label = str(i)
                f = self.disk.files.get(owner)
                if f:
                    if f.get("index_block") == i:
                        # the index block of an indexed file -> star
                        label = f"{i}*"
                    elif f.get("method") == "Linked":
                        # show the block's POSITION in the pointer chain
                        # (\u2460 = circled 1 ...) so the scattered chain
                        # order is readable right on the grid
                        pos = f["blocks"].index(i)
                        label = f"{i}\u2192" if pos < len(f["blocks"]) - 1 \
                            else f"{i}\u25A0"   # last block = EOF marker

            if highlight == i:
                # glow effect: a second, larger neon rectangle behind the cell
                cv.create_rectangle(x1 - 2, y1 - 2, x2 + 2, y2 + 2,
                                    outline=C["text"], width=1)
                width = 3
            else:
                width = 2 if owner is not None else 1
            cv.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline,
                                width=width)
            cv.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=label,
                           fill=txt_col, font=("Segoe UI", 9, "bold"))

    def _update_stats(self):
        """Refresh the usage line under the disk grid (used/free + legend)."""
        used = self.disk.total_blocks - self.disk.free_count()
        pct = round(used / self.disk.total_blocks * 100)
        self.stats.config(
            text=f"Used: {used}/{self.disk.total_blocks} blocks ({pct}%)   |   "
                 f"Free: {self.disk.free_count()} blocks   |   "
                 f"* = index block   \u2192 = has next-pointer   "
                 f"\u25A0 = end of chain (EOF)")

    def _refresh_table(self):
        """Rebuild the file-manager table from the disk's directory,
        applying the live search filter if one is typed."""
        self.tree.delete(*self.tree.get_children())
        # live search filter: only show files whose name contains the query
        query = ""
        if hasattr(self, "search_var"):
            query = self.search_var.get().strip().lower()
        for name, f in self.disk.files.items():
            if query and query not in name.lower():
                continue
            self.tree.insert("", "end", values=(
                name, f["size_bytes"], len(f["blocks"]), f["method"]))
        # selection is gone after a rebuild -> reset selection-dependent state
        self.quick_delete_armed = False
        if hasattr(self, "_multi_wrap") and not self.multi_mode:
            self._multi_wrap.pack_forget()

    def _refresh_all(self):
        """One call to bring EVERY view back in sync with the disk state:
        the block grid, the usage stats and the file table."""
        self._draw_disk()
        self._update_stats()
        self._refresh_table()

    def _log(self, msg):
        """Append one line to the terminal-style activity log and scroll
        it into view - the app narrates every action through this."""
        self.log.insert("end", "> " + msg + "\n")
        self.log.see("end")

    # ==========================================================================
    # PHASE 7 : THE HELP SYSTEM (menu -> tabbed dark help window)
    # ==========================================================================
    HELP_PAGES = [
        ("How to Use", """
STEP-BY-STEP GUIDE
==================

1. CREATE A FILE
   - Type a file name on the left (e.g. "notes") and pick an
     extension (.txt, .doc, .csv ...).
   - Type any content into the big text box.
   - Watch the LIVE METER under the box: it shows the size in
     bytes and how many disk blocks the content needs.
     (1 block = 32 bytes. 100 characters = 100 bytes = 4 blocks)

2. PICK AN ALGORITHM
   - Choose Contiguous, Linked or Indexed from the dropdown.

3. SAVE
   - Press "SAVE FILE TO DISK".
   - Watch the disk grid: blocks fill up ONE BY ONE in real
     simulated time, outlined with the file's own neon colour.

4. MANAGE FILES
   - All saved files appear in the right-hand list.
   - Double-click (or "OPEN SELECTED") to load a file back into
     the editor. Edit the content and Save again - the old
     blocks are freed and new ones are allocated.
   - "DELETE SELECTED" frees all of the file's blocks.

5. COMPARE
   - Press "COMPARE ALL 3 ALGORITHMS" to see WHERE each
     algorithm would place the same file, side by side.
   - The file is fetched automatically: the one in the editor,
     or the one selected in "FILES ON DISK" (its saved content
     is loaded from the directory), or the last saved file.
   - Each panel gets an identical copy of the disk, so the
     comparison is fair; your saved files stay exactly as
     they are.

6. EXPERIMENT
   - Save and delete several files to create "holes", then try
     saving a big file with Contiguous - it may FAIL even though
     enough total space exists. That is EXTERNAL FRAGMENTATION,
     and Linked/Indexed will still succeed!
"""),
        ("How the Algorithms Work", """
THE 3 CLASSIC FILE ALLOCATION ALGORITHMS
========================================

1. CONTIGUOUS ALLOCATION
   - The whole file is stored in ONE continuous run of blocks
     (e.g. blocks 4,5,6,7).
   - The directory stores just: start block + length.
   + Fastest access (sequential AND direct).
   - Suffers EXTERNAL FRAGMENTATION: after many creates/deletes
     the free space is split into small holes, and a new file
     may not fit in any single hole.

2. LINKED ALLOCATION
   - Blocks are SCATTERED anywhere on the disk (watch the grid:
     the blocks really are spread out, not side by side!).
   - Each block sacrifices 4 of its 32 bytes to store a pointer
     to the NEXT block, forming a chain: only 28 bytes per block
     hold data, so files need MORE blocks than with the others.
   - The directory stores the FIRST and LAST block. The last
     block's pointer marks end-of-file (EOF, shown as \u25A0).
   + No external fragmentation, files grow easily.
   - Slow direct access: to read block N you must follow the
     chain through all earlier blocks. Pointers use space.

3. INDEXED ALLOCATION
   - One extra block (the INDEX BLOCK, marked * in the grid)
     stores a table of pointers to ALL data blocks; the data
     blocks themselves are SCATTERED across the disk.
   - The directory points only at the index block.
   - LIMIT: one 32-byte index block holds 32/4 = 8 pointers,
     so a file can have at most 8 data blocks (256 bytes) with
     a single-level index. Real systems chain or nest indexes.
   + Fast direct access AND no external fragmentation.
   - Costs one full extra block per file for the index.

WHAT THIS SIMULATOR SHOWS
   - The neon grid = the disk surface, 64 blocks.
   - Every save animates the exact blocks each algorithm picks.
   - The Compare button shows all three side-by-side.
"""),
        ("What is a Block?", """
BLOCKS - HOW A DISK REALLY STORES FILES
=======================================

A disk is divided into equal-sized units called BLOCKS
(real systems use 4096 bytes; this simulator uses 32 bytes
so you can see the effect quickly).

A file ALWAYS occupies whole blocks:

   content size          blocks used (32 B each)
   -----------------     -----------------------
   "Hi" (2 bytes)     ->  1 block  (30 bytes wasted)
   40 characters      ->  2 blocks
   100 characters     ->  4 blocks

The wasted space inside the last block is called
INTERNAL FRAGMENTATION.

The Operating System's FILE SYSTEM must remember which blocks
belong to which file - and THAT is exactly what the three
allocation algorithms (Contiguous, Linked, Indexed) solve in
different ways. Open "How the Algorithms Work" to learn more.
"""),
    ]

    def _show_help(self, tab=0):
        win = tk.Toplevel(self.root)
        win.title("Help - Virtual File Manager")
        win.geometry("640x560")
        win.configure(bg=C["bg"])
        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True, padx=10, pady=10)
        for title, text in self.HELP_PAGES:
            frame = tk.Frame(nb, bg=C["glass"])
            box = tk.Text(frame, font=("Consolas", 10), bg=C["glass"],
                          fg=C["text"], insertbackground=C["neon"],
                          selectbackground="#16325A", relief="flat",
                          wrap="word")
            box.insert("1.0", text.strip())
            box.config(state="disabled")
            box.pack(fill="both", expand=True, padx=10, pady=10)
            nb.add(frame, text=title)
        nb.select(tab)

    # ==========================================================================
    # PHASE 7B : THE ABOUT WINDOW - dark glass card, neon accents and an
    # RGB colour-cycling author signature.
    # ==========================================================================
    def _show_about(self):
        import webbrowser

        win = tk.Toplevel(self.root)
        win.title("About - Virtual File Manager")
        win.configure(bg=C["bg"])
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        # ---- animated RGB gradient header (canvas, per-letter hue) ----
        head = tk.Canvas(win, bg=C["bg2"], height=64, highlightthickness=0)
        head.pack(fill="x")
        title = "File Management & Allocation Simulator"
        items, x = [], 18
        for ch in title:
            it = head.create_text(x, 32, text=ch, anchor="w", fill=C["neon"],
                                  font=("Segoe UI", 13, "bold"))
            bbox = head.bbox(it)
            x = bbox[2] + 1
            items.append(it)
        # make sure the window is at least wide enough for the full title
        # (the longer text was getting clipped by the narrower body content)
        win.update_idletasks()
        need_w = x + 18                      # right padding to match left
        if win.winfo_reqwidth() < need_w:
            win.minsize(need_w, 0)
        tk.Frame(win, bg=C["border"], height=1).pack(fill="x")

        body = tk.Frame(win, bg=C["glass"], padx=26, pady=18)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="File Allocation Simulator",
                 bg=C["glass"], fg=C["neon"],
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(body, text="Operating Systems Diploma Project",
                 bg=C["glass"], fg=C["muted"],
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 10))

        tk.Label(body,
                 text=("Demonstrates Contiguous, Linked and Indexed file\n"
                       "allocation with real content-based block usage,\n"
                       "live animation and algorithm comparison.\n\n"
                       "Built with Python 3 + Tkinter."),
                 bg=C["glass"], fg=C["text"], justify="left",
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 12))

        # ---- author (RGB colour-cycling signature) ----
        tk.Frame(body, bg=C["border"], height=1).pack(fill="x", pady=6)
        tk.Label(body, text="Developed by", bg=C["glass"], fg=C["muted"],
                 font=("Segoe UI", 9)).pack(anchor="w")
        sig = tk.Label(body, text="TechYoMinati", bg=C["glass"], fg=C["neon"],
                       font=("Segoe UI", 13, "bold"))
        sig.pack(anchor="w", pady=(0, 8))

        # ---- clickable neon contact links ----
        def link(parent, label, text, url):
            row = tk.Frame(parent, bg=C["glass"])
            row.pack(anchor="w", fill="x", pady=2)
            tk.Label(row, text=label, bg=C["glass"], fg=C["muted"], width=9,
                     anchor="w", font=("Segoe UI", 10)).pack(side="left")
            lk = tk.Label(row, text=text, bg=C["glass"], fg=C["neon"],
                          cursor="hand2", font=("Segoe UI", 10, "underline"))
            lk.pack(side="left")
            lk.bind("<Button-1>", lambda e: webbrowser.open(url))
            lk.bind("<Enter>", lambda e: lk.config(fg=C["pink"]))
            lk.bind("<Leave>", lambda e: lk.config(fg=C["neon"]))

        link(body, "GitHub:",   "github.com/TechYoMinati",
             "https://github.com/TechYoMinati")
        link(body, "Email:",    "patelprincekhambliaya@gmail.com",
             "mailto:patelprincekhambliaya@gmail.com")
        link(body, "Telegram:", "t.me/TECHYOMINATI",
             "https://t.me/TECHYOMINATI")

        # ---- close button ----
        close = tk.Button(body, text="Close", command=win.destroy,
                          bg=C["neon"], fg="#04070F", relief="flat", bd=0,
                          font=("Segoe UI", 10, "bold"), padx=20, pady=5,
                          cursor="hand2",
                          activebackground=C["text"],
                          activeforeground="#04070F")
        close.pack(anchor="e", pady=(16, 0))

        # local RGB animation loop for this window (title gradient + signature)
        state = {"hue": 0.0}

        def spin():
            if not win.winfo_exists():
                return
            state["hue"] = (state["hue"] + 0.008) % 1.0
            n = max(len(items), 1)
            for i, it in enumerate(items):
                head.itemconfig(it, fill=_hsv_hex(state["hue"] + i / n * 0.45,
                                                  0.85, 1.0))
            sig.config(fg=_hsv_hex(state["hue"], 0.8, 1.0))
            win.after(70, spin)

        spin()

        # center the window over the main app
        win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - win.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{max(x, 0)}+{max(y, 0)}")


# ==============================================================================
# PHASE 8 : PROGRAM ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = FileManagerApp(root)
    root.mainloop()
