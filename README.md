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
