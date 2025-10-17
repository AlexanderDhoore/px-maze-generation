# Robotics Contest Mazes

This folder contains ready-to-use mazes for the **Squeak & Seek** robot challenge.

Each maze is provided in two synchronized formats:
- a machine-readable text grid (`maze.txt`) 
- and a printable vector drawing (`maze.svg`).

Both files describe the **same layout**.

```
maze01/
  ├─ maze.txt
  └─ maze.svg
maze02/
maze03/
...
```

## `maze.txt`

Plain-text grid, one character per cell:

* `#` = wall
* `S` = start
* `E` = end
* (space) = open corridor

Rows go **top → bottom** and columns **left → right**. There is exactly one `S` and one `E`.

This is the format you’ll likely load into your code to build the maze graph and plan a route.

For example:

```
#E#######
# # #   #
# # ### #
#       #
# # ### #
# #   # #
### # # #
#   # # #
###S#####
```

## `maze.svg`

Vector drawing of the same maze (black = walls, white = corridors).

It’s used for **printing**; each square is **10 cm × 10 cm** in the real world. You can rely on that scale, though expect small margins of error from printers.

The SVG is also handy for visualization or debugging.

For example:

![](maze04/maze.svg)

---

# The Game: live maze state over TCP

During competitions a camera watches the maze and a game engine overlays **fruits** (-10 seconds bonus) and **ghosts** (+10 seconds penalty). Your code can subscribe to a **live ASCII stream** of the current maze state.

## How to connect

* **Host:** `maze.devbit.lan`
    - Only available on `devbit` wifi / LAN.
* **Port:** `1337` (TCP)
* **Transport:** plain TCP (no TLS). One-way **server → client** broadcast.
* You may connect from your **robot** or from a **PC**. Any programming language will work.

Quick test with **netcat**:

```bash
nc -v maze.devbit.lan 1337
```

Or use the provided example client:

```bash
python3 the-game/game_client.py
```

## Message format

The server pushes **snapshots** of the maze at a steady rate (once per second). Each snapshot is:

* Exactly the same **rows × columns** as the corresponding `maze.txt`.
* **One line per row**, each terminated by `\n` (LF).
* A **blank line** (`\n`) after the last row marks the **end of the snapshot**.

Characters are the same as in `maze.txt` + fruit and ghosts:

* `#` = wall
* `S` = start (fixed)
* `E` = end (fixed)
* `F` = fruit **at its current cell**
* `G` = ghost **at its current cell**
* (space) = open corridor

**Example snapshot:**

```
#####################
# #F          #F#   S
# ### ######### # ###
#G    # #F      #   #
### # # ### ### # # #
#   #      G# #F#F# #
# #G# # # # # ##### #
E # # # # # # # G # #
######### ### ### # #
#F#F              G #
# # #G### ### ### # #
# F #   # #F    # # #
#####################

```

↑ Note the **blank line** after the last row.

## Consuming the stream

* Read **line-by-line** and buffer until you see a **blank line** → that block is one snapshot.
* Parse rows **top → bottom**, columns **left → right**.
* You do **not** need to acknowledge or send anything back.

## Timing & reliability

* The server broadcasts to all clients. If your client is **too slow**, you may **miss** a snapshot. Just process the next one.
* You can **reconnect** at any time. You’ll start receiving the latest state immediately.
* Multiple clients per team are OK (e.g., one for planning, one for telemetry).

## Typical workflow

1. Load the static `maze.txt` to build your maze graph (walls, S/E, geometry).
2. Subscribe to the TCP stream and, on each snapshot, **overlay** the dynamic entities (`F`, `G`).
3. Plan/rank routes that maximize fruit collection while avoiding ghosts and still reach `E` fastest.
4. Send waypoints/commands to your robot according to your own architecture.

**Happy path-finding!**
