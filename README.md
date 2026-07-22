# 🇷🇴 osu!Romania Discord Bot

A Discord bot built for the **osu!Romania** community.

---

## Features

### 🎯 osu! Integration

- Link Discord accounts with osu! accounts using the official osu! OAuth API.
- Display detailed osu! profiles, recent plays, top plays, and server leaderboards.
- Automatic beatmap embeds when osu! beatmap links are shared.
- Supports the osu!standard game mode.

---

### 🏆 Achievement Tracking

- Automatically monitors linked players for new achievements.
- Announces:
  - New #1 personal bests.
  - New Top 5 plays.
  - Play PP milestones.
  - Total PP milestones.
  - Global rank milestones.
  - Romania rank milestones.
- Includes rich embeds with beatmap information, score details, PP gains, rank changes, and direct osu! links.
- Duplicate achievement detection prevents repeated announcements.

---

### 🛡️ Moderation

- Ban, unban, kick, timeout, and untimeout members.
- Bulk message deletion (purge).
- Complete warning system with support for adding, viewing, removing, and clearing warnings.
- Moderator action logging with consistent embed formatting.

---

## 🛠️ Built With

- Python 3.12
- discord.py 2.7
- SQLite
- osu! OAuth API v2
- aiohttp

---

## 📂 Project Structure

```
Discord Bot/
│
├── cogs/
│   ├── achievements.py
│   ├── moderation.py
│   └── server_settings.py
├── osu/
│   ├── leaderboard.py
│   ├── listeners.py
│   ├── osu.py
│   ├── profile.py
│   └── scores.py
│
├── utils/
│   ├── __init__.py
│   ├── beatmap_embed.py
│   ├── cache.py
│   ├── embeds.py
│   ├── osu_embed.py
│   ├── osu_api.py
│   ├── score_embed.py
│   └── server_embed.py
│
├── database/
│   ├── init_db.py
│   └── bot.db
│
├── .env
├── .gitignore
├── config.json
├── main.py
├── README.md
└── requirements.txt
```

---

## 📋 Slash Commands

### osu!

| Command | Description |
|---------|-------------|
| `/link` | Link your Discord account to your osu! account. |
| `/profile` | Display an osu! player's profile. |
| `/recent` | Show a player's most recent score. |
| `/top` | Display a player's top plays. |
| `/leaderboard` | View the server's osu! leaderboard. |

---

### Moderation

| Command | Description |
|---------|-------------|
| `/mod ban` | Ban a member from the server. |
| `/mod unban` | Unban a previously banned user. |
| `/mod kick` | Kick a member from the server. |
| `/mod timeout` | Timeout a member for a specified duration. |
| `/mod untimeout` | Remove a member's timeout. |
| `/mod purge` | Delete a specified number of messages. |

#### Warning Management

| Command | Description |
|---------|-------------|
| `/mod warn add` | Issue a warning to a member. |
| `/mod warn list` | View all warnings for a member. |
| `/mod warn remove` | Remove a warning by its ID. |
| `/mod warn clear` | Remove all warnings from a member. |

---

### Server Configuration

| Command | Description |
|---------|-------------|
| `/server achievements` | Configure the achievement announcement channel or disable announcements. |
| `/server autorole` | Configure the role automatically given to new members or disable autorole. |
| `/server welcome` | Configure the welcome message channel or disable welcome messages. |
| `/server leave` | Configure the leave message channel or disable leave messages. |

---

### Utility

| Command | Description |
|---------|-------------|
| `/testachievement` | Send a test achievement announcement (Administrator only). |

---

## 🔒 Security

The following files are ignored by Git:

- `.env`
- `.venv`
- `__pycache__/`
- `SQLite database`

Never share your Discord token or osu! client secret.

---

## 🤝 Contributing

Contributions, suggestions and bug reports are always welcome.

Feel free to open an issue or submit a pull request.

---

## 📄 License

This project is licensed under the MIT License.

---

<div align="center">

Made with ❤️ for the **osu!Romania** community.

</div>