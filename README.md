# GCal2Discord - Google Calendar to Discord Sync Bot

This bot synchronizes events from a Google Calendar to a Discord server, creating scheduled voice channel or external events. It's designed to bridge the gap between your Google Calendar events and Discord, allowing for seamless transition from scheduled events to actual online meetings.

## Key Features

### Core Synchronization

- **Smart Event Sync**: Syncs events from Google Calendar to Discord as scheduled voice channel or external events
- **Intelligent Change Detection**: Only updates Discord events when actual changes are detected, reducing API calls
- **Automatic Event Management**: Creates, updates, and deletes Discord events based on Google Calendar changes
- **Event Recovery**: Ensures events accidentally deleted from Discord are recreated if they still exist in Google Calendar

### Advanced Filtering System

- **Comprehensive Event Filtering**: Filter events by title, description, location, creator, or attendees
- **Exclusion Rules**: Exclude specific events (e.g., private meetings) from syncing
- **Flexible Pattern Matching**: Support for contains, starts with, ends with, and exact match filters
- **Multiple Filter Types**: Combine different filter criteria for precise event selection

### Smart Event Processing  

- **HTML Link Conversion**: Automatically converts HTML links in event descriptions to readable text format
- **Timezone Intelligence**: Proper handling of all-day events with DST-aware timezone conversion
- **Event Type Detection**: Automatically determines Discord event type based on location
  - Events with "discord" in location → Voice Channel events
  - Other events → External events with location metadata

### Reliability

- **Rate Limiting Protection**: Built-in rate limiting with automatic retry logic
- **Pagination Support**: Handles calendars with hundreds of events
- **Enhanced Error Handling**: Comprehensive logging and graceful error recovery
- **Unicode Support**: Full UTF-8 support for international characters and emojis

## How It Works

1. **Event Discovery**: The bot regularly checks your specified Google Calendar for events
2. **Smart Filtering**: Events are filtered based on your configured criteria (title, description, location, etc.)
3. **Change Detection**: The bot compares event signatures to detect actual changes and avoid unnecessary updates
4. **Discord Integration**: For each qualifying event, it creates or updates a corresponding scheduled event in Discord:
   - **Voice Channel Events**: Events with "discord" in the location are linked to your specified Discord voice channel
   - **External Events**: Other events are created as external events with location metadata
5. **Periodic Updates**: As changes occur in Google Calendar (new events, updates, or deletions), the bot reflects these changes in Discord
6. **HTML Processing**: Event descriptions with HTML links are automatically converted to readable text format
7. **Timezone Handling**: All-day events are properly converted to your configured timezone with DST awareness

This integration allows teams to manage their schedule in Google Calendar while leveraging Discord's powerful voice chat features for their actual meetings, with advanced filtering to ensure only relevant events are synchronized.

## Event Types & Behavior

### Voice Channel Events

- **Trigger**: Events with "discord" (case-insensitive) anywhere in the location field
- **Behavior**: Creates a Discord voice channel event linked to your specified `DISCORD_CHANNEL_ID`
- **Usage**: Perfect for planned Discord voice meetings, gaming sessions, or team calls

### External Events  

- **Trigger**: All other events (without "discord" in location)
- **Behavior**: Creates a Discord external event with the event location as metadata
- **Usage**: Ideal for in-person meetings, external conferences, or general reminders

## Prerequisites

- Python 3.8+ (required for `zoneinfo` support)
- Google Calendar API credentials
- Discord bot token

## Quick Start

### Clone the repository

```bash
git clone https://github.com/rempairamore/GCal2Discord.git
cd GCal2Discord
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure the bot

1. Copy the example configuration: `cp var.py_example var.py`
2. Edit `var.py` with your credentials and preferences (see [Configuration](#configuration) below)
3. Set up Google Calendar API credentials (see [Google Calendar API Setup](#google-calendar-api-setup))
4. Run the bot: `python main.py`

## Configuration

The bot is configured through the `var.py` file. Copy `var.py_example` to `var.py` and customize the following settings:

### Basic Configuration

```python
# Google API credentials  
GOOGLE_CREDENTIALS_JSON = './key.json'
GOOGLE_CALENDAR_ID = 'your-calendar-id@group.calendar.google.com'

# Discord credentials
DISCORD_BOT_TOKEN = 'your-bot-token'
DISCORD_GUILD_ID = 'your-guild-id'  
DISCORD_CHANNEL_ID = 'your-voice-channel-id'

# Sync settings
SYNC_INTERVAL = 600  # Check for updates every 10 minutes
DAYS_IN_FUTURE = 10  # Sync events up to 10 days ahead
TIMEZONE = 'America/New_York'  # Your local timezone for all-day events
```

### Advanced Event Filtering

Control which events get synced with flexible filtering options:

```python
EVENT_FILTERS = {
    # Include events with these keywords in title
    'title_contains': ['meeting', 'discord', 'stream'],
    
    # Include events starting with these prefixes  
    'title_starts_with': ['[PUBLIC]', 'Team:', 'Event:'],
    
    # Include events ending with these suffixes
    'title_ends_with': [' - Discord', ' (Public)'],
    
    # Filter by description content
    'description_contains': ['discord', 'public event'],
    
    # Filter by location  
    'location_contains': ['discord', 'online', 'virtual'],
    
    # Filter by event creator
    'creator_email': ['admin@company.com'],
    
    # Filter by attendees
    'attendee_email': ['team@company.com'],
    
    # EXCLUDE events (takes precedence)
    'exclude_title_contains': ['private', 'personal'],
    'exclude_description_contains': ['internal only']
}
```

### Filtering Examples

**Sync only Discord-related events:**

```python
EVENT_FILTERS = {
    'title_contains': ['discord']
}
```

**Sync all events except private ones:**

```python  
EVENT_FILTERS = {
    'exclude_title_contains': ['private', 'personal']
}
```

**Sync events by specific creator:**

```python
EVENT_FILTERS = {
    'creator_email': ['events@company.com']
}
```

*Note: If `EVENT_FILTERS` is empty or undefined, ALL events will be synced.*

## Google Calendar API Setup

1. **Go to the [Google Cloud Console](https://console.cloud.google.com/)**

2. **Create a new project:**
    - Click on the project dropdown at the top of the page.
    - Click "New Project."
    - Enter a name for your project and click "Create."

3. **Enable the Google Calendar API:**
    - In the project dashboard, click on "Enable APIs and Services."
    - Search for "Google Calendar API" and click on it.
    - Click "Enable."

4. **Create credentials for the API:**
    - Go to the "Credentials" tab on the left sidebar.
    - Click "Create Credentials" and select "Service Account."
    - Enter a name for the service account and click "Create."
    - Assign a role to the service account (e.g., "Editor") and click "Continue."
    - Click "Done."

5. **Create a key for the service account:**
    - In the "Credentials" tab, click on the service account you created.
    - Go to the "Keys" section and click "Add Key" > "Create new key."
    - Select "JSON" and click "Create." A JSON file will be downloaded to your computer.

6. **Share your Google Calendar with the service account:**
    - Open Google Calendar.
    - Go to the "Settings and sharing" of the calendar you want to sync.
    - In the "Share with specific people" section, add the service account's email address (found in the JSON file) and provide appropriate permissions (e.g., "Make changes to events").

7. **Save the JSON credentials file:**
    - Save the JSON file in your project directory and update the `GOOGLE_CREDENTIALS_JSON` path in `var.py`.

## Obtaining Discord IDs and Token

To configure the bot, you'll need the Discord bot token, the guild ID (server ID), and the channel ID where the bot will post the events. Here’s how you can obtain them:

1. **Create a Discord Bot**

   - Go to the Discord Developer Portal.
   - Click on "New Application" and give it a name.
   - Go to the "Bot" tab on the left sidebar and click "Add Bot".
   - Click "Yes, do it!" to confirm.
   - Under the "TOKEN" section, click "Copy" to copy your bot token. Save this token as you'll need it for the DISCORD_BOT_TOKEN variable in var.py.

2. **Get Your Guild ID**

    Enable Developer Mode in Discord:
       - Go to your Discord app.
       - Click on the gear icon (User Settings) next to your username.
       - Go to "Advanced" and enable "Developer Mode".
    Right-click on your server icon in Discord and click "Copy ID". Save this ID as you'll need it for the DISCORD_GUILD_ID variable in var.py.

3. **Get Your Channel ID**

    In Discord, right-click on the channel where you want the bot to post events and click "Copy ID". Save this ID as you'll need it for the DISCORD_CHANNEL_ID variable in var.py.

### Create the var.py file

You can find a `var.py_example` file in the project with comprehensive configuration options. Copy and modify this file:

```bash
cp var.py_example var.py
```

Edit `var.py` with your credentials and preferences. See the [Configuration](#configuration) section above for detailed options.

**Basic Configuration:**

```python
# var.py - Basic setup
GOOGLE_CREDENTIALS_JSON = './key.json'
GOOGLE_CALENDAR_ID = 'your-google-calendar-id@group.calendar.google.com'
DISCORD_BOT_TOKEN = 'your-discord-bot-token'
DISCORD_GUILD_ID = 'your-discord-guild-id'
DISCORD_CHANNEL_ID = 'your-discord-channel-id'
TIMEZONE = 'America/New_York'  # Your timezone for all-day events
SYNC_INTERVAL = 600  # Sync every 10 minutes
DAYS_IN_FUTURE = 10  # Sync events up to 10 days ahead

# Optional: Add EVENT_FILTERS for selective sync (see Configuration section)
```

## Running the Bot

1. **Run the bot:**

    ```bash
    python main.py
    ```

## Logging & Monitoring

The bot provides comprehensive logging for monitoring and troubleshooting:

- **Detailed Operation Logs**: All sync operations, API calls, and filtering results are logged
- **Automatic Log Rotation**: When `event.log` exceeds 200 MB, it's compressed and archived
- **Rate Limit Tracking**: Logs rate limit hits and retry attempts  
- **Event Change Tracking**: Shows which events were created, updated, or skipped
- **Filter Results**: Reports how many events were filtered and synced

**Log Examples:**

```text
2026-02-05 10:30:00 Filtered 50 Google Calendar events down to 12 events for sync.
2026-02-05 10:30:05 Event Team Meeting unchanged, skipping update
2026-02-05 10:30:07 Event Discord Game Night has changed, updating on Discord  
2026-02-05 10:30:10 Rate limited, waiting 2.5 seconds before retry (attempt 1/3)
```

## Troubleshooting

### Common Issues

**Events not syncing:**

- Check your `EVENT_FILTERS` configuration - ensure it's not too restrictive
- Verify Google Calendar sharing permissions with the service account
- Check the logs for filter results: `tail -f event.log`

**Rate limiting errors:**

- The bot automatically handles rate limits with retries
- If persistent, consider increasing `SYNC_INTERVAL` to reduce API calls
- Check Discord bot permissions in your server

**Timezone issues:**

- Ensure `TIMEZONE` is set to a valid IANA timezone (e.g., 'America/New_York')
- The bot will log warnings for invalid timezone configurations
- All-day events use the configured timezone for DST calculation

**Missing dependencies:**

- Ensure Python 3.8+ for `zoneinfo` support
- Install all requirements: `pip install -r requirements.txt`
- The `tzdata` package provides timezone data for Windows systems

### Debug Tips

1. **Enable verbose logging**: Check `event.log` for detailed operation info
2. **Test filters**: Temporarily disable `EVENT_FILTERS` to sync all events
3. **Check permissions**: Verify Discord bot has "Manage Events" permission
4. **Validate config**: Ensure all IDs in `var.py` are correct

## Running as a systemd Service

To run the bot as a systemd service, follow these steps:

1. **Create a systemd service file:**

    Create a file named `google-calendar-discord-bot.service` in the `/etc/systemd/system/` directory with the following content:

    ```ini
    [Unit]
    Description=Google Calendar to Discord Sync Bot
    After=network.target

    [Service]
    User=yourusername
    WorkingDirectory=/path/to/your/project
    ExecStart=/usr/bin/python3 /path/to/your/project/main.py
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

    Replace `yourusername` with your system username and `/path/to/your/project` with the path to your project directory.

2. **Reload systemd and start the service:**

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl start google-calendar-discord-bot
    ```

3. **Enable the service to start on boot:**

    ```bash
    sudo systemctl enable google-calendar-discord-bot
    ```

## Upgrading from Earlier Versions

If you're upgrading from a previous version of GCal2Discord:

1. **Update dependencies**: `pip install -r requirements.txt` (adds `tzdata` for timezone support)
2. **Update configuration**: Compare your `var.py` with the new `var.py_example` for new options
3. **Add timezone setting**: Set `TIMEZONE` in your `var.py` for proper all-day event handling
4. **Optional filtering**: Add `EVENT_FILTERS` if you want selective sync (otherwise all events sync as before)
5. **Clear sync data** (optional): Delete `synced_events.json` to force a fresh sync with new signatures

### New Dependencies

- **tzdata**: Provides timezone database for Windows systems and timezone calculations
- **Python 3.8+**: Required for `zoneinfo` module (earlier versions used `pytz`)

## FAQ

**Q: Will my existing synced events be affected?**
A: No, existing events will be automatically updated with the new signature system. The bot maintains backward compatibility.

**Q: How do I sync only specific events?**
A: Use the `EVENT_FILTERS` configuration. For example, to sync only events with "Discord" in the title:

```python
EVENT_FILTERS = {'title_contains': ['discord']}
```

**Q: Can I use different Discord channels for different event types?**
A: Currently, voice channel events use the configured `DISCORD_CHANNEL_ID`, while external events don't tie to a specific channel. Multiple channel support may be added in future versions.

**Q: How does the HTML link conversion work?**
A: Event descriptions with HTML links like `<a href="https://zoom.us/j/123">Join Meeting</a>` are automatically converted to `https://zoom.us/j/123 (Join Meeting)` for better Discord formatting.

## License

This project is licensed under the  "**GNU GENERAL PUBLIC LICENSE - Version 3** (29 June 2007)" license.
