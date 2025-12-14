from __future__ import annotations

import atexit
import warnings
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, List, Optional, Sequence, Union

import pandas as pd
import refinitiv.data as rd

warnings.filterwarnings("ignore", category=RuntimeWarning)

DateLike = Union[str, date, datetime]


@dataclass(frozen=True)
class RDLConfig:
    session_name: Optional[str] = None  # None => use sessions.default from config
    batch_size: int = 50
    keep_session_open: bool = True      # best for Streamlit
    verbose: bool = False


def _to_yyyy_mm_dd(d: DateLike) -> str:
    if isinstance(d, str):
        return d  # expect YYYY-MM-DD
    if isinstance(d, datetime):
        return d.date().strftime("%Y-%m-%d")
    if isinstance(d, date):
        return d.strftime("%Y-%m-%d")
    raise TypeError(f"Unsupported date type: {type(d)}")


def _as_list(x: Union[str, Iterable[str]]) -> List[str]:
    if isinstance(x, str):
        return [x]
    return list(x)


def _chunks(seq: Sequence[str], n: int) -> Iterable[List[str]]:
    for i in range(0, len(seq), n):
        yield list(seq[i : i + n])


class RefinitivLoader:
    """
    Thin wrapper around refinitiv.data that:
      - opens a platform session via config (rd.open_session)
      - batches requests
      - returns pandas DataFrames
    """

    def __init__(self, cfg: Optional[RDLConfig] = None):
        self.cfg = cfg or RDLConfig()
        self._opened = False

        # If Streamlit caches this loader (recommended), we keep the session open.
        # Ensure we close when the Python process exits.
        if self.cfg.keep_session_open:
            atexit.register(self.close)

    # ---------- session management ----------

    def open(self) -> None:
        if self._opened:
            return
        if self.cfg.verbose:
            print("[RefinitivLoader] opening session...")
        if self.cfg.session_name:
            rd.open_session(self.cfg.session_name)
        else:
            rd.open_session()
        self._opened = True

    def close(self) -> None:
        if not self._opened:
            return
        try:
            if self.cfg.verbose:
                print("[RefinitivLoader] closing session...")
            rd.close_session()
        except Exception:
            pass
        finally:
            self._opened = False

    def ensure_open(self) -> None:
        if not self._opened:
            self.open()

    def __enter__(self) -> "RefinitivLoader":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        # If you used `with RefinitivLoader() as rdl:`, close at end of block
        # (even if keep_session_open=True, "with" implies scoped usage)
        self.close()

    # ---------- core primitives ----------

    def get_snapshot(
        self,
        universe: Union[str, Iterable[str]],
        fields: Union[str, Iterable[str]],
    ) -> pd.DataFrame:
        self.ensure_open()

        universe_l = _as_list(universe)
        fields_l = _as_list(fields)

        frames = []
        for u in _chunks(universe_l, self.cfg.batch_size):
            frames.append(rd.get_data(universe=u, fields=fields_l))

        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def get_history(
        self,
        universe: Union[str, Iterable[str]],
        fields: Union[str, Iterable[str]],
        start: DateLike,
        end: DateLike,
        interval: str = "daily",
    ) -> pd.DataFrame:
        """
        Returns library output (often wide: Date index, columns by RIC).
        Batches universe if needed and concatenates columns (outer join on Date).
        """
        self.ensure_open()

        universe_l = _as_list(universe)
        fields_l = _as_list(fields)

        out: Optional[pd.DataFrame] = None
        for u in _chunks(universe_l, self.cfg.batch_size):
            df = rd.get_history(
                universe=u,
                fields=fields_l,
                interval=interval,
                start=_to_yyyy_mm_dd(start),
                end=_to_yyyy_mm_dd(end),
            )
            if out is None:
                out = df
            else:
                out = out.join(df, how="outer")

        return out if out is not None else pd.DataFrame()

    # ---------- convenience wrappers (optional) ----------

    def eq_snapshot(self, rics: Union[str, Iterable[str]]) -> pd.DataFrame:
        return self.get_snapshot(rics, ["TR.PriceClose", "TR.Volume", "TR.CompanyMarketCap"])

    def eq_history_close(self, rics: Union[str, Iterable[str]], start: DateLike, end: DateLike) -> pd.DataFrame:
        return self.get_history(rics, ["TR.PriceClose"], start=start, end=end, interval="daily")

    def fx_snapshot(self, fx_rics: Union[str, Iterable[str]]) -> pd.DataFrame:
        return self.get_snapshot(fx_rics, ["BID", "ASK"])

    def fx_history_mid(self, fx_rics: Union[str, Iterable[str]], start: DateLike, end: DateLike) -> pd.DataFrame:
        return self.get_history(fx_rics, ["MID"], start=start, end=end, interval="daily")

    def rates_history(self, rate_rics: Union[str, Iterable[str]], field: str, start: DateLike, end: DateLike) -> pd.DataFrame:
        return self.get_history(rate_rics, [field], start=start, end=end, interval="daily")
