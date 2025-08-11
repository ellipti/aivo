from __future__ import annotations

import time
from ...utils.logger import info, error

try:
    import MetaTrader5 as mt5  # type: ignore
    MT5_AVAILABLE = True
except Exception:
    MT5_AVAILABLE = False


class MT5Reconnect:
    def attempt(self) -> bool:
        if not MT5_AVAILABLE:
            error("mt5_module_missing")
            return False
        try:
            if not mt5.initialize():
                error("mt5.reconnect.failed")
                time.sleep(5)
                ok = mt5.initialize()
                if ok:
                    info("mt5.reconnected")
                return bool(ok)
            info("mt5.already_connected")
            return True
        except Exception as e:
            error("mt5.reconnect.exception", err=str(e))
            return False


