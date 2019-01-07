from .frontend import StdioFrontend
from .tcpdialler import TcpDialler


frontend = StdioFrontend(TcpDialler)
frontend.run()