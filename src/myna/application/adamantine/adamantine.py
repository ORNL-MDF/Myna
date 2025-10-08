"""Define base subclass for shared functionality between all adamantine Myna apps"""

from pathlib import Path
from myna.core.app import MynaApp


class AdamantineApp(MynaApp):
    """Defines a Myna app that uses the adamantine simulation"""

    def __init__(self, name):
        super().__init__(name)
        self.path = str(Path(self.path) / "adamantine")

        # Parse app-specific arguments
        self.parse_known_args()
