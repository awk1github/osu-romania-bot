# 🇷🇴 osu!Romania Discord Bot

A Discord bot built for the **osu!Romania** community.

The bot contains server moderation functionalities, but I also added some osu! commands, allowing members to link their accounts, view profiles, recent scores, top plays and a server leaderboard.

---

## ✨ Features

### 🛡️ Moderation
- Kick members
- Ban / Unban members
- Timeout / Remove timeout
- Purge messages
- Warning system
- Clear warnings

### 🎮 osu! Integration
- `/link` — Link your osu! account
- `/profile` — View an osu! profile
- `/recent` — View a player's most recent play
- `/top` — Display a player's top plays
- `/leaderboard` — Server-wide linked player leaderboard

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
│   ├── moderation.py
│   └── warnings.py
│
├── osu/
│   ├── profile.py
│   ├── scores.py
│   └── leaderboard.py
│
├── utils/
│   ├── osu_api.py
│   ├── cache.py
│   ├── embeds.py
│   ├── osu_embed.py
│   └── score_embed.py
│
├── database/
│   ├── init_db.py
│   └── bot.db
│
├── .env
├── main.py
└── requirements.txt
```

---

## 📋 Slash Commands

### Moderation

| Command | Description |
|---------|-------------|
| `/purge` | Delete messages |
| `/kick` | Kick a member |
| `/ban` | Ban a member |
| `/unban` | Unban a member |
| `/timeout` | Timeout a member |
| `/untimeout` | Remove timeout |
| `/warn` | Warn a member |
| `/warnings` | View warnings |
| `/removewarn` | Remove one warning |
| `/clearwarnings` | Clear all warnings |

### osu!

| Command | Description |
|---------|-------------|
| `/link` | Link your osu! account |
| `/profile` | View an osu! profile |
| `/recent` | View recent play |
| `/top` | View top plays |
| `/leaderboard` | View the server leaderboard |

---

## 🔒 Security

The following files are ignored by Git:

- `.env`
- `.venv`
- `__pycache__/`
- SQLite database

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