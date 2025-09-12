"""
awg_file.py

Module for reading/writing Tektronix AWG520 file formats:

WFM files (.wfm):
  - Header:      'MAGIC 1000 \r\n'                   # identifies waveform file
  - Body:        '#<num_digits><num_bytes><data...>'   # length-prefixed binary block
      * <num_digits> = number of digits in <num_bytes>
      * <num_bytes>  = total byte count of following records
      * <data>      = for each sample: 4-byte little-endian float (analog) + 1-byte marker
  - Trailer:     'CLOCK <clock> \r\n'                # ASCII sample clock rate (Hz)

SEQ files (.seq):
  - Header:      'MAGIC 3002 \r\n'                   # identifies sequence file (2 channels)
  - Lines block: 'LINES <N>\r\n'                     # number of sequence entries
      * Each line: "<ch1.wfm>","<ch2.wfm>",<repeat>,<wait>,<goto>,<logic>\r\n
  - Optional jump tables:
      * TABLE_JUMP <16 comma-separated ints>\r\n
      * LOGIC_JUMP <4 comma-separated ints>\r\n
      * JUMP_MODE (LOGIC|TABLE|SOFTWARE)\r\n
      * JUMP_TIMING (SYNC|ASYNC)\r\n
      * STROBE <0|1>\r\n
"""
import logging
import struct
import time
from pathlib import Path
from typing import List, Optional, Tuple, Union

import numpy as np

# Maximum number of samples per waveform (hardware limit)
_WFM_MEMORY_LIMIT = 4_000_000  # 4M words as per AWG520 specification

logger = logging.getLogger("awg_file")


class AWGFile:
    """
    Writer for AWG520 .wfm and .seq files.

    Attributes:
      out_dir      Directory to write files into (cleared on init)
      timeres_ns   Sample resolution in nanoseconds
    """

    def __init__(
        self,
        ftype: str = "WFM",
        timeres_ns: int = 1,
        out_dir: Union[str, Path] = ".",
    ):
        """
        Initialize and clear output directory.

        Args:
          ftype:      "WFM" or "SEQ" (determines default behavior)
          timeres_ns: sample period in ns (affects CLOCK trailer)
          out_dir:    path where files will be written
        """
        self.ftype = ftype.upper()
        self.timeres_ns = timeres_ns
        self.out_dir = Path(out_dir)
        # ensure directory exists
        self.out_dir.mkdir(parents=True, exist_ok=True)

        # remove any existing waveform or sequence files
        for ext in ("*.wfm", "*.seq"):
            for old in self.out_dir.glob(ext):
                old.unlink()

        # Pre-built file headers
        self._wfm_header = b"MAGIC 1000 \r\n"
        self._seq_header = b"MAGIC 3002 \r\n"

        logger.info(
            f"AWGFile init: type={self.ftype}, timeres={self.timeres_ns} ns, dir={self.out_dir}"
        )

    def _make_trailer(self) -> bytes:
        """
        Build the CLOCK trailer based on sample resolution.

        Returns:
          b'CLOCK <value> \r\n' where <value> is ASCII float in Hz
        """
        # map from timeres to clock frequency (Hz)
        table = {
            1:   b"CLOCK 1.0000000000E+9\r\n",   # 1 ns -> 1 GHz
            5:   b"CLOCK 2.0000000000E+08\r\n",  # 5 ns -> 200 MHz
            10:  b"CLOCK 1.0000000000E+08\r\n",  # 10 ns -> 100 MHz
            25:  b"CLOCK 4.0000000000E+07\r\n",  # 25 ns -> 40 MHz
            100: b"CLOCK 1.0000000000E+07\r\n",  # 100 ns -> 10 MHz
        }
        try:
            return table[self.timeres_ns]
        except KeyError:
            raise ValueError(f"Unsupported timeres_ns: {self.timeres_ns}")

    def _make_binary_record(
        self, iq: np.ndarray, m: np.ndarray
    ) -> Tuple[int, int, bytes]:
        """
        Pack IQ data and marker array into binary format for WFM body.

        Args:
          iq:  1D float array of analog values in [-1.0,1.0]
          m:   1D int array of marker bits (0 or 1)

        Returns:
          num_bytes:     total bytes of binary payload
          record_size:   bytes per sample (always struct.calcsize('<fb'))
          record_bytes:  concatenated binary samples
        """
        n = len(iq)
        # pad waveform length to multiple of 4 samples
        if n % 4:
            pad = 4 - (n % 4)
            iq = np.concatenate([iq, np.zeros(pad, dtype=iq.dtype)])
            m  = np.concatenate([m,  np.zeros(pad, dtype=m.dtype)])
            n += pad

        if n >= _WFM_MEMORY_LIMIT:
            raise ValueError("Waveform memory limit exceeded")

        rec_size = struct.calcsize("<fb")  # 4-byte float + 1-byte marker
        total_bytes = n * rec_size

        buf = bytearray(total_bytes)
        for i in range(n):
            # analog I/Q data converted to 4 byte float, marker to 1 byte , both little-endian
            struct.pack_into('<fb', buf, i*rec_size, float(iq[i]), int(m[i]))

        return total_bytes, rec_size, bytes(buf)

    def write_waveform(
        self,
        iq: np.ndarray,
        marker: np.ndarray,
        name: str,
        channel: int = 1,
    ) -> Path:
        """
        Write a single .wfm file containing analog+marker data.

        Args:
          iq:      analog samples array
          marker:  marker bits array
          name:    base filename (no extension)
          channel: channel index (1 or 2)

        Returns:
          Path to the written .wfm file
        """
        fname = f"{name}_{channel}.wfm"
        out = self.out_dir / fname

        logger.info(f"Writing waveform '{out.name}'")
        with open(out, 'wb') as f:
            f.write(self._wfm_header)
            nbytes, _, payload = self._make_binary_record(iq, marker)
            # write length prefix '#<ndigits><nbytes>'
            prefix = f"#{len(str(nbytes))}{nbytes}".encode()
            f.write(prefix)
            f.write(payload)
            f.write(self._make_trailer())

        return out

    def write_sequence(
        self,
        entries: List[Tuple[str,str,int,int,int,int]],
        seq_name: str,
        table_jump: Optional[List[int]] = None,
        logic_jump: Optional[List[int]] = None,
        jump_mode: str = "SOFTWARE",
        jump_timing: str = "SYNC",
        strobe: int = 0,
    ) -> Path:
        """
        Write a .seq file describing waveform playback order and jumps.

        Args:
          entries:     list of tuples (wfm1, wfm2, repeat, wait, goto, logic)
          seq_name:    base filename (no extension)
          table_jump:  optional list of 16 jump targets
          logic_jump:  optional list of 4 logic on/off flags
          jump_mode:   JUMP_MODE enum
          jump_timing: JUMP_TIMING enum
          strobe:      0/1

        Returns:
          Path to the written .seq file
        """
        fname = f"{seq_name}.seq"
        out = self.out_dir / fname

        logger.info(f"Writing sequence '{out.name}'")
        with open(out, 'wb') as f:
            f.write(self._seq_header)
            f.write(f"LINES {len(entries)}\r\n".encode())

            # write each line: "ch1.wfm","ch2.wfm",repeat,wait,goto,logic\r\n
            for w1, w2, rpt, wait, goto, logic in entries:
                line = f'"{w1}","{w2}",{rpt},{wait},{goto},{logic}\r\n'
                f.write(line.encode())

            # optional tables
            if table_jump:
                f.write(("TABLE_JUMP " + ",".join(map(str,table_jump)) + "\r\n").encode())
            if logic_jump:
                f.write(("LOGIC_JUMP " + ",".join(map(str,logic_jump)) + "\r\n").encode())

            f.write(f"JUMP_MODE {jump_mode}\r\n".encode())
            f.write(f"JUMP_TIMING {jump_timing}\r\n".encode())
            f.write(f"STROBE {strobe}\r\n".encode())

        return out
