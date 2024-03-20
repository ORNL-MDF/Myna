"""main module for Myna workflow framework"""

import os

# Set environment variables on package import
os.environ["MYNA_INSTALL_PATH"] = os.path.sep.join(
    os.path.abspath(__file__).split(os.path.sep)[:-3]
)

os.environ["MYNA_INTERFACE_PATH"] = os.path.join(
    os.path.sep.join(os.path.abspath(__file__).split(os.path.sep)[:-3]), "interfaces"
)

# Submodules
import myna.metadata
import myna.components
import myna.files
import myna.workflow
import myna.utils
