from mcp.server.fastmcp import FastMCP

from releasepulse.retrieval import retrieve

server = FastMCP("ReleasePulse QA guidelines")


@server.tool()
def retrieve_qa_guidelines(query: str, limit: int = 3) -> list[dict]:
    """Retrieve bounded synthetic QA policies with document IDs and source excerpts."""
    return retrieve(query[:500], limit)


if __name__ == "__main__":
    server.run(transport="stdio")
