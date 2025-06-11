#!/bin/bash

echo "Starting Sonarr MCP Server..."

# Check required environment variables
if [ -z "$SONARR_URL" ]; then
    echo "ERROR: SONARR_URL environment variable is required"
    exit 1
fi

if [ -z "$SONARR_API_KEY" ]; then
    echo "ERROR: SONARR_API_KEY environment variable is required"
    exit 1
fi

echo "Sonarr URL: $SONARR_URL"
echo "MCP Server will listen on: ${SONARR_MCP_HOST:-127.0.0.1}:${SONARR_MCP_PORT:-9171}"

# Test Sonarr connectivity
echo "Testing Sonarr connectivity..."
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "$SONARR_URL/api/v3/system/status" -H "X-Api-Key: $SONARR_API_KEY")

if [ "$HEALTH_CHECK" != "200" ]; then
    echo "WARNING: Cannot connect to Sonarr at $SONARR_URL (HTTP $HEALTH_CHECK)"
    echo "The MCP server will start anyway, but tools may not work until Sonarr is accessible"
else
    echo "Successfully connected to Sonarr"
fi

# Start the MCP server
echo "Starting MCP server..."
exec python sonarr-mcp-server.py 