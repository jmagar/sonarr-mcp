# Sonarr MCP Server

This server implements TV series management capabilities for Sonarr PVR using the Model Context Protocol (MCP).

## Design Rationale
This MCP server was designed collaboratively to provide essential Sonarr functionality through a well-structured API. The tools focus on the most common use cases: browsing series, managing downloads, monitoring activity, and adding new shows. The server uses default quality profiles and root folders to simplify series addition while maintaining flexibility.

## Implemented Tools

### Core Management Tools
- **get_series_list** - Browse all TV series with filtering and statistics
- **get_series_details** - Get comprehensive information about specific series
- **search_series** - Find new TV shows to add from external databases
- **add_series** - Add new series with automatic defaults for quality and location
- **get_calendar** - View upcoming and recent episodes
- **get_queue** - Monitor active downloads and progress
- **get_history** - Review download and activity history
- **trigger_series_search** - Manually search for missing episodes
- **get_system_status** - Check Sonarr health and system information

### Resources
- **series_poster** - Access to series poster images (`sonarr://series/{series_id}/poster`)
- **episode_details** - Detailed episode information (`sonarr://episode/{episode_id}`)

## Quick Start

### Installation

```bash
# Clone the repository
git clone [repository-url]
cd sonarr-mcp

# Install dependencies
pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env with your Sonarr URL and API key
```

### Docker Deployment

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Start the services
docker-compose up -d

# View logs
docker-compose logs -f sonarr-mcp
```

### Configuration

Required environment variables:
- `SONARR_URL` - Your Sonarr instance URL (e.g., http://localhost:8989)
- `SONARR_API_KEY` - API key from Sonarr Settings > General

Optional configuration:
- `SONARR_MCP_HOST` - Host to bind to (default: 127.0.0.1)
- `SONARR_MCP_PORT` - Port to listen on (default: 9171)
- `LOG_LEVEL` - Logging level (default: INFO)

### Claude Desktop Configuration

To use this server with Claude Desktop, add the following to your Claude Desktop configuration file:

**MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sonarr-mcp": {
      "command": "python",
      "args": [
        "/absolute/path/to/sonarr-mcp/sonarr-mcp-server.py"
      ],
      "env": {
        "SONARR_API_KEY": "your-api-key-here",
        "SONARR_URL": "http://localhost:8989"
      }
    }
  }
}
```

**Cline Configuration for SSE Server:**

In `cline_mcp_settings.json` (if running as HTTP server):

```json
{
  "mcpServers": {
    "sonarr-mcp-sse": {
      "url": "http://localhost:9171/mcp",
      "disabled": false,
      "autoApprove": ["get_series_list", "get_calendar", "get_queue"],
      "timeout": 30
    }
  }
}
```

## Usage Examples

### Browse Your TV Collection
```
get_series_list(monitored=true)
```
Shows all monitored TV series with episode counts and missing episodes.

### Add a New TV Show
```
search_series("Breaking Bad")
# Find the TVDB ID from results
add_series(tvdb_id=81189, title="Breaking Bad")
```
Searches for the show and adds it with default quality and location settings.

### Check Upcoming Episodes
```
get_calendar(start="2024-01-01", end="2024-01-31")
```
Shows all episodes airing in January 2024.

### Monitor Downloads
```
get_queue()
```
Displays current download queue with progress information.

### Trigger Manual Search
```
trigger_series_search(series_id=123)
```
Forces Sonarr to search for missing episodes of a specific series.

## Troubleshooting

### Common Issues

1. **API key errors**
   - Verify your API key in Sonarr Settings > General
   - Ensure the API key is correctly set in your `.env` file
   - Check that the API key has proper permissions

2. **Connection issues (for HTTP server)**
   - Ensure the MCP server is running and listening on the correct host/port
   - Check firewalls or network configurations if accessing remotely
   - Verify the URL in client configuration matches the server's listening address

3. **Authentication errors to Sonarr API**
   - Verify Sonarr URL is accessible from where the MCP server runs
   - Check that Sonarr is running and responsive
   - Ensure no authentication requirements beyond API key

4. **Tool execution failures**
   - Check server logs for detailed error messages
   - Verify Sonarr API endpoints are accessible
   - Ensure sufficient permissions for series management operations

### Health Checks

The server provides health monitoring:
- Docker health checks test server responsiveness
- System status tool verifies Sonarr connectivity
- Comprehensive logging for troubleshooting

## FastMCP Implementation Notes

This server leverages FastMCP 2.0 features:
- **Streamable HTTP transport** for web-based clients
- **Comprehensive error handling** with detailed logging
- **Resource management** for poster images and episode details
- **Async operations** for optimal performance
- **Environment-based configuration** following FastMCP best practices

The implementation balances ease of use with powerful functionality, making TV series management accessible through natural language interactions while maintaining full API capabilities.
