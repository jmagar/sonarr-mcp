"""
Sonarr MCP Server
Implements TV series management capabilities for Sonarr PVR
Built with FastMCP following best practices from gofastmcp.com
Transport: Streamable HTTP
"""

import os
import sys
import aiohttp
import asyncio
from fastmcp import FastMCP
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Logging setup for dual output
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_LEVEL_STR = os.getenv('LOG_LEVEL', 'INFO').upper()
NUMERIC_LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)
SCRIPT_DIR = Path(__file__).resolve().parent

# Define a base logger
logger = logging.getLogger("SonarrMCPServer") 
logger.setLevel(NUMERIC_LOG_LEVEL)
logger.propagate = False

# Console Handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(NUMERIC_LOG_LEVEL)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# File Handler with Rotation
log_file_name = f"{os.getenv('SONARR_NAME', 'sonarr').lower()}_mcp.log"
log_file_path = SCRIPT_DIR / log_file_name

file_handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
file_handler.setLevel(NUMERIC_LOG_LEVEL)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

logger.info(f"Logging initialized (console and file: {log_file_path}).")

# Log loaded environment variables
logger.info(f"SONARR_URL loaded: {os.getenv('SONARR_URL', 'Not Found')[:20]}...")
logger.info(f"SONARR_API_KEY loaded: {'****' if os.getenv('SONARR_API_KEY') else 'Not Found'}")
logger.info(f"SONARR_MCP_PORT set to: {os.getenv('SONARR_MCP_PORT', '4200')}")
logger.info(f"LOG_LEVEL set to: {os.getenv('LOG_LEVEL', 'INFO')}")

# Critical check for essential API credentials/URL
if not os.getenv('SONARR_URL') or not os.getenv('SONARR_API_KEY'):
    logger.error("SONARR_URL and SONARR_API_KEY must be set.")
    sys.exit(1)

# Configuration
SONARR_URL = os.getenv('SONARR_URL').rstrip('/')
SONARR_API_KEY = os.getenv('SONARR_API_KEY')
API_BASE = f"{SONARR_URL}/api/v3"

# Initialize server
mcp = FastMCP(
    name="Sonarr MCP Server",
    instructions="TV series management server for Sonarr PVR. Provides tools for managing TV shows, monitoring downloads, and organizing your television collection."
)

async def make_api_request(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make authenticated API request to Sonarr."""
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    headers = {
        "X-Api-Key": SONARR_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            if method.upper() == "GET":
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    return await response.json()
            elif method.upper() == "POST":
                async with session.post(url, headers=headers, json=data) as response:
                    response.raise_for_status()
                    return await response.json()
            elif method.upper() == "PUT":
                async with session.put(url, headers=headers, json=data) as response:
                    response.raise_for_status()
                    return await response.json()
            elif method.upper() == "DELETE":
                async with session.delete(url, headers=headers) as response:
                    response.raise_for_status()
                    return {"status": "deleted"}
    except aiohttp.ClientError as e:
        logger.error(f"API request failed: {e}")
        raise Exception(f"Sonarr API request failed: {str(e)}")

@mcp.tool()
async def get_series_list(monitored: Optional[bool] = None, include_season_images: Optional[bool] = False) -> Dict[str, Any]:
    """
    Retrieve all TV series in the Sonarr library with filtering options.
    
    Returns a summarized list of series with key information for easy browsing.
    """
    logger.info(f"Getting series list with monitored={monitored}, include_season_images={include_season_images}")
    
    try:
        # Get all series
        series_data = await make_api_request("series")
        
        # Filter by monitored status if specified
        if monitored is not None:
            series_data = [s for s in series_data if s.get('monitored') == monitored]
        
        # Process into human-readable format
        series_summary = []
        for series in series_data:
            summary = {
                "id": series.get("id"),
                "title": series.get("title"),
                "status": series.get("status"),
                "monitored": series.get("monitored"),
                "year": series.get("year"),
                "seasons": len(series.get("seasons", [])),
                "episodes": {
                    "total": series.get("statistics", {}).get("episodeCount", 0),
                    "available": series.get("statistics", {}).get("episodeFileCount", 0),
                    "missing": series.get("statistics", {}).get("episodeCount", 0) - series.get("statistics", {}).get("episodeFileCount", 0)
                },
                "quality_profile": series.get("qualityProfileId"),
                "path": series.get("path"),
                "network": series.get("network"),
                "genres": series.get("genres", [])[:3]  # Limit to first 3 genres
            }
            series_summary.append(summary)
        
        result = {
            "total_series": len(series_summary),
            "monitored_count": len([s for s in series_summary if s["monitored"]]),
            "series": series_summary
        }
        
        logger.debug(f"Retrieved {len(series_summary)} series")
        return {"status": "success", "data": result}
        
    except Exception as e:
        logger.error(f"Error in get_series_list: {e}", exc_info=True)
        return {"error": str(e)}

@mcp.tool()
async def get_series_details(series_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific TV series including seasons and episodes.
    
    Provides comprehensive series data for in-depth analysis.
    """
    logger.info(f"Getting details for series ID: {series_id}")
    
    try:
        series_data = await make_api_request(f"series/{series_id}")
        
        # Process into detailed but readable format
        details = {
            "basic_info": {
                "id": series_data.get("id"),
                "title": series_data.get("title"),
                "sort_title": series_data.get("sortTitle"),
                "status": series_data.get("status"),
                "overview": series_data.get("overview", "")[:500] + ("..." if len(series_data.get("overview", "")) > 500 else ""),
                "network": series_data.get("network"),
                "air_time": series_data.get("airTime"),
                "runtime": series_data.get("runtime"),
                "year": series_data.get("year"),
                "genres": series_data.get("genres", []),
                "certification": series_data.get("certification"),
                "imdb_id": series_data.get("imdbId"),
                "tvdb_id": series_data.get("tvdbId")
            },
            "monitoring": {
                "monitored": series_data.get("monitored"),
                "season_folder": series_data.get("seasonFolder"),
                "quality_profile_id": series_data.get("qualityProfileId"),
                "language_profile_id": series_data.get("languageProfileId")
            },
            "statistics": series_data.get("statistics", {}),
            "file_info": {
                "path": series_data.get("path"),
                "size_on_disk": series_data.get("statistics", {}).get("sizeOnDisk", 0)
            },
            "seasons": []
        }
        
        # Process seasons
        for season in series_data.get("seasons", []):
            season_info = {
                "season_number": season.get("seasonNumber"),
                "monitored": season.get("monitored"),
                "statistics": season.get("statistics", {})
            }
            details["seasons"].append(season_info)
        
        logger.debug(f"Retrieved details for series: {details['basic_info']['title']}")
        return {"status": "success", "data": details}
        
    except Exception as e:
        logger.error(f"Error in get_series_details: {e}", exc_info=True)
        return {"error": str(e)}

@mcp.tool()
async def search_series(term: str) -> Dict[str, Any]:
    """
    Search for new TV series to add to Sonarr using external databases.
    
    Search by series name or external ID (TVDB, IMDB).
    """
    logger.info(f"Searching for series with term: {term}")
    
    try:
        # URL encode the search term
        import urllib.parse
        encoded_term = urllib.parse.quote(term)
        
        search_results = await make_api_request(f"series/lookup?term={encoded_term}")
        
        # Process search results into readable format
        results = []
        for result in search_results[:10]:  # Limit to top 10 results
            series_info = {
                "title": result.get("title"),
                "year": result.get("year"),
                "tvdb_id": result.get("tvdbId"),
                "imdb_id": result.get("imdbId"),
                "overview": result.get("overview", "")[:300] + ("..." if len(result.get("overview", "")) > 300 else ""),
                "network": result.get("network"),
                "status": result.get("status"),
                "genres": result.get("genres", [])[:3],
                "runtime": result.get("runtime"),
                "seasons": len(result.get("seasons", [])),
                "images": result.get("images", [])
            }
            results.append(series_info)
        
        summary = {
            "search_term": term,
            "results_count": len(results),
            "results": results
        }
        
        logger.debug(f"Found {len(results)} series for term: {term}")
        return {"status": "success", "data": summary}
        
    except Exception as e:
        logger.error(f"Error in search_series: {e}", exc_info=True)
        return {"error": str(e)}

@mcp.tool()
async def add_series(tvdb_id: int, title: str, root_folder_path: Optional[str] = None, 
                    quality_profile_id: Optional[int] = None, monitored: Optional[bool] = True) -> Dict[str, Any]:
    """
    Add a new TV series to Sonarr with specified settings.
    
    Uses default root folder and quality profile if not specified.
    """
    logger.info(f"Adding series: {title} (TVDB ID: {tvdb_id})")
    
    try:
        # Get default root folder if not provided
        if root_folder_path is None:
            root_folders = await make_api_request("rootfolder")
            if not root_folders:
                return {"error": "No root folders configured in Sonarr"}
            root_folder_path = root_folders[0]["path"]
            logger.info(f"Using default root folder: {root_folder_path}")
        
        # Get default quality profile if not provided
        if quality_profile_id is None:
            quality_profiles = await make_api_request("qualityprofile")
            if not quality_profiles:
                return {"error": "No quality profiles configured in Sonarr"}
            quality_profile_id = quality_profiles[0]["id"]
            logger.info(f"Using default quality profile ID: {quality_profile_id}")
        
        # Get series info from lookup first
        search_results = await make_api_request(f"series/lookup?term=tvdb:{tvdb_id}")
        if not search_results:
            return {"error": f"Could not find series with TVDB ID: {tvdb_id}"}
        
        series_data = search_results[0]
        
        # Prepare series data for adding
        add_data = {
            "title": series_data.get("title", title),
            "qualityProfileId": quality_profile_id,
            "languageProfileId": 1,  # Default language profile
            "rootFolderPath": root_folder_path,
            "monitored": monitored,
            "addOptions": {
                "monitor": "all",
                "searchForMissingEpisodes": True
            },
            "tvdbId": tvdb_id,
            "titleSlug": series_data.get("titleSlug"),
            "images": series_data.get("images", []),
            "seasons": series_data.get("seasons", [])
        }
        
        # Add the series
        result = await make_api_request("series", method="POST", data=add_data)
        
        summary = {
            "added_series": {
                "id": result.get("id"),
                "title": result.get("title"),
                "tvdb_id": result.get("tvdbId"),
                "path": result.get("path"),
                "monitored": result.get("monitored"),
                "quality_profile_id": result.get("qualityProfileId"),
                "seasons": len(result.get("seasons", []))
            },
            "message": f"Successfully added '{result.get('title')}' to Sonarr"
        }
        
        logger.info(f"Successfully added series: {result.get('title')}")
        return {"status": "success", "data": summary}
        
    except Exception as e:
        logger.error(f"Error in add_series: {e}", exc_info=True)
        return {"error": str(e)}

@mcp.tool()
async def get_calendar(start: Optional[str] = None, end: Optional[str] = None, 
                      unmonitored: Optional[bool] = False) -> Dict[str, Any]:
    """
    Retrieve upcoming and recent episodes from the calendar.
    
    Dates should be in YYYY-MM-DD format. Defaults to 7 days back and 30 days forward.
    """
    logger.info(f"Getting calendar with start={start}, end={end}, unmonitored={unmonitored}")
    
    try:
        # Set default date range if not provided
        if start is None:
            start_date = datetime.now() - timedelta(days=7)
            start = start_date.strftime("%Y-%m-%d")
        if end is None:
            end_date = datetime.now() + timedelta(days=30)
            end = end_date.strftime("%Y-%m-%d")
        
        # Build query parameters
        params = f"start={start}&end={end}"
        if unmonitored:
            params += "&unmonitored=true"
        
        calendar_data = await make_api_request(f"calendar?{params}")
        
        # Process calendar data
        episodes = []
        for episode in calendar_data:
            episode_info = {
                "episode_id": episode.get("id"),
                "series_title": episode.get("series", {}).get("title"),
                "series_id": episode.get("seriesId"),
                "season_number": episode.get("seasonNumber"),
                "episode_number": episode.get("episodeNumber"),
                "title": episode.get("title"),
                "air_date": episode.get("airDate"),
                "air_date_utc": episode.get("airDateUtc"),
                "has_file": episode.get("hasFile"),
                "monitored": episode.get("monitored"),
                "overview": episode.get("overview", "")[:200] + ("..." if len(episode.get("overview", "")) > 200 else "")
            }
            episodes.append(episode_info)
        
        # Group by date for better organization
        episodes_by_date = {}
        for ep in episodes:
            air_date = ep["air_date"]
            if air_date not in episodes_by_date:
                episodes_by_date[air_date] = []
            episodes_by_date[air_date].append(ep)
        
        summary = {
            "date_range": f"{start} to {end}",
            "total_episodes": len(episodes),
            "episodes_with_files": len([ep for ep in episodes if ep["has_file"]]),
            "episodes_by_date": dict(sorted(episodes_by_date.items())),
            "all_episodes": episodes
        }
        
        logger.debug(f"Retrieved {len(episodes)} calendar episodes")
        return {"status": "success", "data": summary}
        
    except Exception as e:
        logger.error(f"Error in get_calendar: {e}", exc_info=True)
        return {"error": str(e)}

@mcp.tool()
async def get_queue(include_unknown_series_items: Optional[bool] = False) -> Dict[str, Any]:
    """
    View current download queue and activity.
    
    Shows active downloads with progress and status information.
    """
    logger.info(f"Getting queue with include_unknown_series_items={include_unknown_series_items}")
    
    try:
        params = ""
        if include_unknown_series_items:
            params = "?includeUnknownSeriesItems=true"
        
        queue_data = await make_api_request(f"queue{params}")
        
        # Process queue data
        queue_items = []
        for item in queue_data.get("records", []):
            queue_info = {
                "id": item.get("id"),
                "series_title": item.get("series", {}).get("title"),
                "episode_title": item.get("episode", {}).get("title"),
                "season_number": item.get("episode", {}).get("seasonNumber"),
                "episode_number": item.get("episode", {}).get("episodeNumber"),
                "quality": item.get("quality", {}).get("quality", {}).get("name"),
                "size": item.get("size", 0),
                "sizeleft": item.get("sizeleft", 0),
                "status": item.get("status"),
                "tracked_download_status": item.get("trackedDownloadStatus"),
                "download_client": item.get("downloadClient"),
                "output_path": item.get("outputPath"),
                "progress": round((1 - (item.get("sizeleft", 0) / max(item.get("size", 1), 1))) * 100, 2)
            }
            queue_items.append(queue_info)
        
        summary = {
            "total_items": len(queue_items),
            "active_downloads": len([item for item in queue_items if item["status"] in ["downloading", "queued"]]),
            "completed_items": len([item for item in queue_items if item["status"] == "completed"]),
            "queue": queue_items
        }
        
        logger.debug(f"Retrieved {len(queue_items)} queue items")
        return {"status": "success", "data": summary}
        
    except Exception as e:
        logger.error(f"Error in get_queue: {e}", exc_info=True)
        return {"error": str(e)}

@mcp.tool()
async def get_history(page: Optional[int] = 1, page_size: Optional[int] = 20, 
                     series_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Retrieve download and activity history.
    
    Shows recent downloads, searches, and other Sonarr activities.
    """
    logger.info(f"Getting history page={page}, page_size={page_size}, series_id={series_id}")
    
    try:
        params = f"page={page}&pageSize={page_size}&sortKey=date&sortDirection=descending"
        if series_id:
            params += f"&seriesId={series_id}"
        
        history_data = await make_api_request(f"history?{params}")
        
        # Process history data
        history_items = []
        for item in history_data.get("records", []):
            history_info = {
                "id": item.get("id"),
                "episode_id": item.get("episodeId"),
                "series_title": item.get("series", {}).get("title"),
                "episode_title": item.get("episode", {}).get("title"),
                "season_number": item.get("episode", {}).get("seasonNumber"),
                "episode_number": item.get("episode", {}).get("episodeNumber"),
                "quality": item.get("quality", {}).get("quality", {}).get("name"),
                "event_type": item.get("eventType"),
                "date": item.get("date"),
                "download_client": item.get("data", {}).get("downloadClient"),
                "source_title": item.get("sourceTitle")
            }
            history_items.append(history_info)
        
        summary = {
            "page": page,
            "page_size": page_size,
            "total_records": history_data.get("totalRecords", 0),
            "records_on_page": len(history_items),
            "history": history_items
        }
        
        logger.debug(f"Retrieved {len(history_items)} history items")
        return {"status": "success", "data": summary}
        
    except Exception as e:
        logger.error(f"Error in get_history: {e}", exc_info=True)
        return {"error": str(e)}

@mcp.tool()
async def trigger_series_search(series_id: int) -> Dict[str, Any]:
    """
    Manually trigger a search for missing episodes of a specific series.
    
    Initiates a search job for all missing monitored episodes.
    """
    logger.info(f"Triggering series search for series ID: {series_id}")
    
    try:
        command_data = {
            "name": "SeriesSearch",
            "seriesId": series_id
        }
        
        result = await make_api_request("command", method="POST", data=command_data)
        
        summary = {
            "command_id": result.get("id"),
            "command_name": result.get("name"),
            "series_id": series_id,
            "status": result.get("status"),
            "queued_at": result.get("queued"),
            "message": f"Search command queued for series ID {series_id}"
        }
        
        logger.info(f"Series search triggered successfully, command ID: {result.get('id')}")
        return {"status": "success", "data": summary}
        
    except Exception as e:
        logger.error(f"Error in trigger_series_search: {e}", exc_info=True)
        return {"error": str(e)}

@mcp.tool()
async def get_system_status() -> Dict[str, Any]:
    """
    Get Sonarr system information and health status.
    
    Provides system version, health checks, and operational status.
    """
    logger.info("Getting system status and health")
    
    try:
        # Get both system status and health in parallel
        status_task = make_api_request("system/status")
        health_task = make_api_request("health")
        
        status_data, health_data = await asyncio.gather(status_task, health_task)
        
        # Process system status
        system_info = {
            "version": status_data.get("version"),
            "build_time": status_data.get("buildTime"),
            "startup_path": status_data.get("startupPath"),
            "app_data": status_data.get("appData"),
            "os_name": status_data.get("osName"),
            "os_version": status_data.get("osVersion"),
            "is_debug": status_data.get("isDebug"),
            "is_production": status_data.get("isProduction"),
            "is_admin": status_data.get("isAdmin"),
            "is_user_interactive": status_data.get("isUserInteractive"),
            "branch": status_data.get("branch"),
            "authentication": status_data.get("authentication"),
            "migration_version": status_data.get("migrationVersion"),
            "url_base": status_data.get("urlBase"),
            "runtime_version": status_data.get("runtimeVersion")
        }
        
        # Process health data
        health_issues = []
        for issue in health_data:
            health_info = {
                "type": issue.get("type"),
                "message": issue.get("message"),
                "wiki_url": issue.get("wikiUrl")
            }
            health_issues.append(health_info)
        
        summary = {
            "system": system_info,
            "health": {
                "total_issues": len(health_issues),
                "issues": health_issues,
                "status": "healthy" if len(health_issues) == 0 else "has_issues"
            }
        }
        
        logger.debug(f"System status retrieved, version: {system_info['version']}, health issues: {len(health_issues)}")
        return {"status": "success", "data": summary}
        
    except Exception as e:
        logger.error(f"Error in get_system_status: {e}", exc_info=True)
        return {"error": str(e)}

# Resources
@mcp.resource("sonarr://series/{series_id}/poster")
async def get_series_poster(series_id: str) -> str:
    """Get series poster image URL or data."""
    try:
        series_data = await make_api_request(f"series/{series_id}")
        images = series_data.get("images", [])
        
        for image in images:
            if image.get("coverType") == "poster":
                return f"{SONARR_URL}{image.get('url')}"
        
        return f"No poster image found for series {series_id}"
    except Exception as e:
        logger.error(f"Error getting series poster: {e}")
        return f"Error retrieving poster: {str(e)}"

@mcp.resource("sonarr://episode/{episode_id}")
async def get_episode_details(episode_id: str) -> str:
    """Get detailed episode information including file paths and quality."""
    try:
        episode_data = await make_api_request(f"episode/{episode_id}")
        
        details = {
            "episode_info": {
                "id": episode_data.get("id"),
                "title": episode_data.get("title"),
                "season_number": episode_data.get("seasonNumber"),
                "episode_number": episode_data.get("episodeNumber"),
                "air_date": episode_data.get("airDate"),
                "overview": episode_data.get("overview"),
                "has_file": episode_data.get("hasFile"),
                "monitored": episode_data.get("monitored")
            },
            "series_info": {
                "series_id": episode_data.get("seriesId"),
                "series_title": episode_data.get("series", {}).get("title")
            }
        }
        
        # Add episode file information if available
        if episode_data.get("episodeFile"):
            file_info = episode_data["episodeFile"]
            details["file_info"] = {
                "file_id": file_info.get("id"),
                "relative_path": file_info.get("relativePath"),
                "path": file_info.get("path"),
                "size": file_info.get("size"),
                "quality": file_info.get("quality", {}).get("quality", {}).get("name"),
                "media_info": file_info.get("mediaInfo", {})
            }
        
        return json.dumps(details, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting episode details: {e}")
        return f"Error retrieving episode details: {str(e)}"

# Transport-specific configuration
if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=os.getenv("SONARR_MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("SONARR_MCP_PORT", "4200")),
        path="/mcp",
        log_level=os.getenv("SONARR_LOG_LEVEL", "debug"),
    ) 