from typing import List, Optional

from pipask._vendor.pip._internal.utils import _log

# init_logging() must be called before any call to logging.getLogger()
# which happens at import of most modules.
_log.init_logging()
