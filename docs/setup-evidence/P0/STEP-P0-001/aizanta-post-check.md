# P0-001 Aizanta Post-Action Check

## Docker containers after P0-001
```text
aizanta-bot        Up 7 days (healthy)   8000/tcp
aizanta-nginx      Up 7 days (healthy)   100.94.104.22:80->80/tcp
aizanta-frontend   Up 7 days (healthy)   3000/tcp
aizanta-postgres   Up 7 days (healthy)   127.0.0.1:5432->5432/tcp
aizanta-redis      Up 7 days (healthy)   127.0.0.1:6379->6379/tcp
```

## Listening ports after P0-001
```text
127.0.0.1:6379       Redis (Aizanta)
100.94.104.22:80     nginx (Aizanta, Tailscale)
127.0.0.1:5432       PostgreSQL (Aizanta)
0.0.0.0:22           SSH
[::]:22              SSH
```

## Result
Aizanta remained healthy after creating the isolated `guinevere` user and limited sudoers rule.
