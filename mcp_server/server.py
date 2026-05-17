import sys
from pathlib import Path

from fastmcp import FastMCP

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from mcp_server.tools.gmail_tool import send_market_report

mcp = FastMCP("MarketScoutMCP")


@mcp.tool()
def send_email_report(
    recipient: str,
    company: str,
    html_body: str
):

    return send_market_report(
        recipient=recipient,
        company=company,
        html_body=html_body
    )


if __name__ == "__main__":
    mcp.run()