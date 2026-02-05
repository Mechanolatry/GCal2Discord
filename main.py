import datetime
import requests
import google.auth
from googleapiclient.discovery import build
from discord import Intents
from discord.ext import tasks, commands
import var
import asyncio
import json
import os
import tarfile
import time
import re
from zoneinfo import ZoneInfo

# File paths for storing synchronized events and logs
SYNCED_EVENTS_FILE = 'synced_events.json'
EVENT_LOG_FILE = 'event.log'
LOG_SIZE_LIMIT = 200 * 1024 * 1024  # 200 MB

def load_synced_events():
    """
    Load the list of events that have been synchronized from the local JSON file.
    """
    if os.path.exists(SYNCED_EVENTS_FILE):
        with open(SYNCED_EVENTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"events": []}

def save_synced_events(synced_events):
    """
    Save the list of synchronized events to the local JSON file.
    """
    with open(SYNCED_EVENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(synced_events, f, indent=4, ensure_ascii=False)

def log_event(message):
    """
    Log messages with a timestamp to the event log file.
    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"{timestamp} {message}\n"
    with open(EVENT_LOG_FILE, 'a', encoding='utf-8') as log_file:
        log_file.write(log_message)
    check_log_size()

def check_log_size():
    """
    Check the size of the event log file and compress it if it exceeds the limit.
    """
    if os.path.exists(EVENT_LOG_FILE) and os.path.getsize(EVENT_LOG_FILE) > LOG_SIZE_LIMIT:
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        tar_filename = f"{timestamp}.tar.gz"
        with tarfile.open(tar_filename, "w:gz") as tar:
            tar.add(EVENT_LOG_FILE)
        os.remove(EVENT_LOG_FILE)
        log_event(f"Log file compressed to {tar_filename} and reset.")

def should_sync_event(event):
    """
    Determine if an event should be synchronized based on filtering criteria.
    Returns True if the event matches any of the configured filters.
    """
    # If no filters are configured, sync all events
    if not hasattr(var, 'EVENT_FILTERS') or not var.EVENT_FILTERS:
        return True
    
    event_title = event.get('summary', '').lower()
    event_description = event.get('description', '').lower()
    event_location = event.get('location', '').lower()
    
    filters = var.EVENT_FILTERS
    
    # Check title filters
    if 'title_contains' in filters:
        for keyword in filters['title_contains']:
            if keyword.lower() in event_title:
                return True
    
    if 'title_starts_with' in filters:
        for prefix in filters['title_starts_with']:
            if event_title.startswith(prefix.lower()):
                return True
    
    if 'title_ends_with' in filters:
        for suffix in filters['title_ends_with']:
            if event_title.endswith(suffix.lower()):
                return True
    
    # Check description filters
    if 'description_contains' in filters:
        for keyword in filters['description_contains']:
            if keyword.lower() in event_description:
                return True
    
    # Check location filters
    if 'location_contains' in filters:
        for keyword in filters['location_contains']:
            if keyword.lower() in event_location:
                return True
    
    # Check if event creator matches filter
    if 'creator_email' in filters:
        creator_email = event.get('creator', {}).get('email', '').lower()
        for email in filters['creator_email']:
            if email.lower() == creator_email:
                return True
    
    # Check for specific attendees
    if 'attendee_email' in filters:
        attendees = event.get('attendees', [])
        attendee_emails = [attendee.get('email', '').lower() for attendee in attendees]
        for filter_email in filters['attendee_email']:
            if filter_email.lower() in attendee_emails:
                return True
    
    # Check exclusion filters (events to NOT sync)
    if 'exclude_title_contains' in filters:
        for keyword in filters['exclude_title_contains']:
            if keyword.lower() in event_title:
                return False
    
    if 'exclude_description_contains' in filters:
        for keyword in filters['exclude_description_contains']:
            if keyword.lower() in event_description:
                return False
    
    # If we have filters but none matched, don't sync the event
    return False

def parse_html_links(text):
    """
    Parse HTML anchor tags in text and convert them to plain text format.
    Converts: <a href="https://example.com">Link Text</a>
    To: https://example.com (Link Text)
    """
   
    if not text:
        return text
    
    # Regular expression to match HTML anchor tags
    # Matches: <a href="URL">TEXT</a>
    link_pattern = r'<a\s+href="([^"]+)"[^>]*>([^<]+)</a>'
    
    def replace_link(match):
        url = match.group(1)
        link_text = match.group(2)
        return f"{url} ({link_text})"
    
    # Replace all HTML links with the new format
    converted_text = re.sub(link_pattern, replace_link, text, flags=re.IGNORECASE)
    
    return converted_text

# a function that takes an ISO 8601 datetime string in UTC and returns it converted to the specified timezone with DST handling
def convert_utc_to_timezone(utc_iso_string, target_timezone_str):
    """
    Convert an ISO 8601 datetime string to the specified timezone with DST handling.
    
    Args:
        utc_iso_string (str): ISO 8601 datetime string. If ends with 'Z' or has UTC offset, 
                             converts from UTC. If no timezone info, appends local offset only.
        target_timezone_str (str): Target timezone name (e.g., "America/New_York", "Europe/London")
    
    Returns:
        str: ISO 8601 datetime string in the target timezone with appropriate DST offset
        
    Examples:
        # With Z suffix - converts from UTC
        convert_utc_to_timezone("2026-07-15T18:00:00Z", "America/New_York")
        # Returns: "2026-07-15T14:00:00-04:00" (converted from UTC)
        
        # Without Z - keeps time, appends offset  
        convert_utc_to_timezone("2026-07-15T14:00:00", "America/New_York")
        # Returns: "2026-07-15T14:00:00-04:00" (same time + EDT offset)
    """
    try:
        # Determine target timezone first
        try:
            target_tz = ZoneInfo(target_timezone_str)
        except:
            # Fallback to UTC if target timezone is invalid
            log_event(f"Warning: Invalid timezone '{target_timezone_str}', using UTC")
            target_tz = datetime.timezone.utc
        
        # Check if the string has timezone information
        has_timezone_info = (utc_iso_string.endswith('Z') or 
                           utc_iso_string.endswith('+00:00') or 
                           '+' in utc_iso_string[-6:] or 
                           '-' in utc_iso_string[-6:])
        
        if has_timezone_info:
            # Handle strings with timezone info - convert from UTC
            if utc_iso_string.endswith('Z'):
                utc_dt = datetime.datetime.fromisoformat(utc_iso_string[:-1] + '+00:00')
            elif utc_iso_string.endswith('+00:00'):
                utc_dt = datetime.datetime.fromisoformat(utc_iso_string)
            else:
                utc_dt = datetime.datetime.fromisoformat(utc_iso_string)
            
            # Ensure the datetime is in UTC
            if utc_dt.tzinfo is None:
                utc_dt = utc_dt.replace(tzinfo=datetime.timezone.utc)
            elif utc_dt.tzinfo != datetime.timezone.utc:
                utc_dt = utc_dt.astimezone(datetime.timezone.utc)
            
            # Convert to target timezone
            target_dt = utc_dt.astimezone(target_tz)
            return target_dt.isoformat()
            
        else:
            # No timezone info - keep timestamp, append DST-aware offset
            naive_dt = datetime.datetime.fromisoformat(utc_iso_string)
            
            # Create a datetime in the target timezone to determine the offset
            localized_dt = naive_dt.replace(tzinfo=target_tz)
            
            # Return the same timestamp with the appropriate offset
            return localized_dt.isoformat()
        
    except Exception as e:
        # Fallback: return original string if conversion fails
        log_event(f"Warning: DateTime conversion failed for '{utc_iso_string}': {e}")
        return utc_iso_string



def get_event_signature(event):
    """
    Generate a signature/hash of an event's key properties for change detection.
    Returns a dictionary with the essential event data that Discord cares about.
    """
    # Get start and end times, handling all-day events
    start_time = event['start'].get('dateTime', event['start'].get('date')) # All-day events have 'date' instead of 'dateTime'
    end_time = event['end'].get('dateTime', event['end'].get('date')) # All-day events have 'date' instead of 'dateTime'
    
    if 'date' in event['start']:
        end_time = convert_utc_to_timezone(start_time + 'T23:59:59', var.TIMEZONE) # All-day event ends at 23:59:59
        start_time = convert_utc_to_timezone(start_time + 'T00:00:00', var.TIMEZONE) # All-day event starts at 00:00:00
        
    
    # Determine event type based on location
    event_location = event.get('location', '').lower()
    is_discord_event = 'discord' in event_location
    
    signature = {
        'title': event.get('summary', ''),
        'description': parse_html_links(event.get('description', '')),
        'start_time': start_time,
        'end_time': end_time,
        'location': event.get('location', ''),
        'is_discord_event': is_discord_event
    }
    
    return signature

def events_are_different(current_event, stored_signature):
    """
    Compare current event with stored signature to detect changes.
    Returns True if the events are different and need updating.
    """
    if not stored_signature:
        return True  # No previous data, consider it different
    
    current_signature = get_event_signature(current_event)
    
    # Compare all key fields
    for key in current_signature:
        if current_signature.get(key) != stored_signature.get(key):
            return True
    
    return False

def get_google_calendar_service():
    """
    Set up the Google Calendar API service using the provided credentials.
    """
    credentials, _ = google.auth.load_credentials_from_file(var.GOOGLE_CREDENTIALS_JSON)
    service = build('calendar', 'v3', credentials=credentials)
    return service

def get_upcoming_events(service):
    """
    Fetch upcoming events from Google Calendar within the specified time frame.
    Handles pagination to retrieve all events.
    """
    log_event(f"Requesting events from Google Calendar for the next {var.DAYS_IN_FUTURE} days.")
    now = datetime.datetime.utcnow()
    time_min = now.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
    time_max = (now + datetime.timedelta(days=var.DAYS_IN_FUTURE)).strftime('%Y-%m-%dT%H:%M:%S') + 'Z'

    all_events = []
    page_token = None
    page_count = 0
    
    while True:
        page_count += 1
        log_event(f"Fetching page {page_count} of events from Google Calendar.")
        
        # Prepare the request parameters
        request_params = {
            'calendarId': var.GOOGLE_CALENDAR_ID,
            'timeMin': time_min,
            'timeMax': time_max,
            'q': var.GOOGLE_FREETEXT_QUERY_STRING,
            'maxResults': 250,  # Increased from 100 for better efficiency
            'singleEvents': True,
            'orderBy': 'startTime'
        }
        
        # Add page token if we're fetching a subsequent page
        if page_token:
            request_params['pageToken'] = page_token
        
        # Make the API request
        events_result = service.events().list(**request_params).execute()
        
        # Get events from this page
        page_events = events_result.get('items', [])
        all_events.extend(page_events)
        
        log_event(f"Retrieved {len(page_events)} events from page {page_count}.")
        
        # Check if there are more pages
        page_token = events_result.get('nextPageToken')
        if not page_token:
            break
    
    log_event(f"Total events retrieved: {len(all_events)} across {page_count} page(s).")
    return all_events

def get_discord_events():
    """
    Fetch existing scheduled events from the Discord server.
    """
    log_event("Requesting events from Discord.")
    url = f"https://discord.com/api/v9/guilds/{var.DISCORD_GUILD_ID}/scheduled-events"
    headers = {
        "Authorization": f"Bot {var.DISCORD_BOT_TOKEN}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        log_event(f"Failed to fetch Discord events: {response.content}")
        return []

def create_or_update_discord_event(event, discord_event_id=None):
    """
    Create a new scheduled event on Discord or update an existing one.
    """
    if discord_event_id is None:
        # Creating a new event
        url = f"https://discord.com/api/v9/guilds/{var.DISCORD_GUILD_ID}/scheduled-events"
        method = requests.post
    else:
        # Updating an existing event
        url = f"https://discord.com/api/v9/guilds/{var.DISCORD_GUILD_ID}/scheduled-events/{discord_event_id}"
        method = requests.patch

    headers = {
        "Authorization": f"Bot {var.DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    # Get start and end times, handling all-day events
    start_time = event['start'].get('dateTime', event['start'].get('date')) # All-day events have 'date' instead of 'dateTime'
    end_time = event['end'].get('dateTime', event['end'].get('date')) # All-day events have 'date' instead of 'dateTime'

    if 'date' in event['start']:
        end_time = convert_utc_to_timezone(start_time + 'T23:59:59', var.TIMEZONE) # All-day event ends at 23:59:59
        start_time = convert_utc_to_timezone(start_time + 'T00:00:00', var.TIMEZONE) # All-day event starts at 00:00:00

    # Determine event type based on location
    event_location = event.get('location', '').lower()
    is_discord_event = 'discord' in event_location
    
    data = {
        "name": event['summary'],
        "description": parse_html_links(event.get('description', '')),
        "scheduled_start_time": start_time,
        "scheduled_end_time": end_time,
        "privacy_level": 2,
        "entity_type": 2 if is_discord_event else 3,  # 2 = Voice Channel, 3 = External
    }
    
    # Add required fields based on event type
    if is_discord_event:
        # Voice channel event
        data["channel_id"] = var.DISCORD_CHANNEL_ID
    else:
        # External event - requires entity_metadata with location
        data["entity_metadata"] = {
            "location": event.get('location', 'External Event')
        }

    response = method(url, json=data, headers=headers)
    
    # Handle rate limiting with retry logic
    max_retries = 3
    retry_count = 0
    
    while response.status_code == 429 and retry_count < max_retries:
        try:
            # Parse the rate limit response
            rate_limit_data = response.json()
            retry_after = rate_limit_data.get('retry_after', 5.0)
            
            log_event(f"Rate limited, waiting {retry_after} seconds before retry (attempt {retry_count + 1}/{max_retries})")
            time.sleep(retry_after + 0.5)  # Add small buffer
            
            # Retry the request
            response = method(url, json=data, headers=headers)
            retry_count += 1
            
        except (json.JSONDecodeError, KeyError):
            # Fallback if we can't parse the response
            log_event(f"Rate limited, waiting 5 seconds before retry (attempt {retry_count + 1}/{max_retries})")
            time.sleep(5.0)
            response = method(url, json=data, headers=headers)
            retry_count += 1
    
    # Always sleep between requests to prevent rapid-fire API calls
    time.sleep(2)
    
    if response.status_code in (200, 201):
        action = 'updated' if discord_event_id else 'created'
        log_event(f"Event {event['summary']} {action} on Discord")
        return response.json().get('id')
    elif response.status_code == 429:
        action = 'update' if discord_event_id else 'create'
        log_event(f"Failed to {action} event {event['summary']} on Discord after {max_retries} retries: Rate limited")
        return None
    else:
        action = 'update' if discord_event_id else 'create'
        log_event(f"Failed to {action} event {event['summary']} on Discord: {response.content}")
        return None

def delete_discord_event(event_id):
    """
    Delete a scheduled event from Discord using its event ID.
    """
    url = f"https://discord.com/api/v9/guilds/{var.DISCORD_GUILD_ID}/scheduled-events/{event_id}"
    headers = {
        "Authorization": f"Bot {var.DISCORD_BOT_TOKEN}"
    }
    response = requests.delete(url, headers=headers)
    
    # Handle rate limiting with retry logic
    max_retries = 3
    retry_count = 0
    
    while response.status_code == 429 and retry_count < max_retries:
        try:
            # Parse the rate limit response
            rate_limit_data = response.json()
            retry_after = rate_limit_data.get('retry_after', 5.0)
            
            log_event(f"Rate limited on delete, waiting {retry_after} seconds before retry (attempt {retry_count + 1}/{max_retries})")
            time.sleep(retry_after + 0.5)  # Add small buffer
            
            # Retry the request
            response = requests.delete(url, headers=headers)
            retry_count += 1
            
        except (json.JSONDecodeError, KeyError):
            # Fallback if we can't parse the response
            log_event(f"Rate limited on delete, waiting 5 seconds before retry (attempt {retry_count + 1}/{max_retries})")
            time.sleep(5.0)
            response = requests.delete(url, headers=headers)
            retry_count += 1
    
    # Always sleep between requests
    time.sleep(2)
    
    if response.status_code == 204:
        log_event(f"Event {event_id} deleted from Discord")
    elif response.status_code == 429:
        log_event(f"Failed to delete event {event_id} from Discord after {max_retries} retries: Rate limited")
    else:
        log_event(f"Failed to delete event {event_id} from Discord: {response.content}")

# Set up the Discord bot with the necessary intents
intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

synced_events = load_synced_events()

@bot.event
async def on_ready():
    """
    Event handler for when the bot is ready and connected to Discord.
    """
    log_event("Bot logged in and ready.")
    sync_events_loop.start()

@tasks.loop(seconds=var.SYNC_INTERVAL)
async def sync_events_loop():
    """
    Periodically synchronize events from Google Calendar to Discord.
    """
    try:
        service = get_google_calendar_service()
        events = get_upcoming_events(service)
        discord_events = get_discord_events()
        global synced_events

        # Filter events based on configured criteria
        filtered_events = [event for event in events if should_sync_event(event)]
        log_event(f"Filtered {len(events)} Google Calendar events down to {len(filtered_events)} events for sync.")
        
        # Create a set of current Discord event IDs for quick lookup
        discord_event_ids = {event['id'] for event in discord_events}

        for event in filtered_events:
            #time.sleep(3)  # Increased delay to prevent rate limiting
            event_id = event['id']
            current_signature = get_event_signature(event)
            event_data = {
                "date": event['start'].get('dateTime', event['start'].get('date')),
                "title": event['summary'],
                "channel": var.DISCORD_CHANNEL_ID,
                "notes": event.get('description', ''),
                "signature": current_signature  # Store signature for change detection
            }

            # Check if the event has already been synchronized
            if any(e["google_event_id"] == event_id for e in synced_events["events"]):
                for synced_event in synced_events["events"]:
                    if synced_event["google_event_id"] == event_id:
                        discord_event_id = synced_event["discord_event_id"]
                        stored_signature = synced_event.get("signature", {})
                        
                        if discord_event_id not in discord_event_ids:
                            # The event is missing on Discord, recreate it
                            log_event(f"Event {event['summary']} is missing on Discord, recreating")
                            discord_event_id = create_or_update_discord_event(event)
                            if discord_event_id:
                                synced_event["discord_event_id"] = discord_event_id
                                synced_event.update(event_data)
                                save_synced_events(synced_events)
                            time.sleep(3)  # Increased delay to prevent rate limiting
                        elif events_are_different(event, stored_signature):
                            # Event has changed, update it on Discord
                            log_event(f"Event {event['summary']} has changed, updating on Discord")
                            discord_event_id = create_or_update_discord_event(event, discord_event_id)
                            if discord_event_id:
                                synced_event.update(event_data)
                                save_synced_events(synced_events)
                            time.sleep(3)  # Increased delay to prevent rate limiting
                        else:
                            # Event hasn't changed, skip update
                            log_event(f"Event {event['summary']} unchanged, skipping update")
                        break
            else:
                # The event is new, create it on Discord
                discord_event_id = create_or_update_discord_event(event)
                if discord_event_id:
                    synced_events["events"].append({
                        "google_event_id": event_id,
                        "discord_event_id": discord_event_id,
                        **event_data
                    })
                    save_synced_events(synced_events)

        # Remove events from Discord that no longer exist in filtered Google Calendar events
        google_event_ids = {event['id'] for event in filtered_events}
        for synced_event in list(synced_events["events"]):
            #time.sleep(3)  # Increased delay to prevent rate limiting
            if synced_event["google_event_id"] not in google_event_ids:
                delete_discord_event(synced_event["discord_event_id"])
                synced_events["events"].remove(synced_event)
                save_synced_events(synced_events)
                time.sleep(3)  # Increased delay to prevent rate limiting

    except Exception as e:
        log_event(f"Error in sync_events_loop: {e}")

# Run the bot using the token from var.py
bot.run(var.DISCORD_BOT_TOKEN)
