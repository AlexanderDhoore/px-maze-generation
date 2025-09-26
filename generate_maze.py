import pprint
from mazelib import Maze
from mazelib.generate.Prims import Prims
from mazelib.solve.BacktrackingSolver import BacktrackingSolver
import svgwrite

# This script generates a maze using mazelib:
# > https://github.com/john-science/mazelib
# It then outputs the maze as both a string and an SVG file.
# The string output is useful for maze-solving algorithms.
# The SVG file is intended for printing on large paper.
# Each square in the maze measures 10 cm by 10 cm.


def save_txt(maze):
    string = maze.tostring(True, False)
    with open("maze.txt", "w") as f:
        f.write(string)
    print("Wrote maze.txt")


def save_svg(maze):
    CELL = 10  # we'll map 1 unit = 1 cm
    N = maze.grid.shape[1]
    M = maze.grid.shape[0]

    dwg = svgwrite.Drawing("maze.svg", size=(f"{N*CELL}cm", f"{M*CELL}cm"))
    dwg.viewbox(0, 0, N * CELL, M * CELL)  # 0..130 in user units == 0..130 cm

    # white background
    dwg.add(dwg.rect((0, 0), (N * CELL, M * CELL), fill="white"))

    # one combined path for all black tiles
    p = dwg.path(fill="black", stroke="none", **{"shape-rendering": "crispEdges"})
    for x in range(N):
        for y in range(M):
            if (y, x) == maze.start:
                print("START")
            elif (y, x) == maze.end:
                print("END")
            elif maze.grid[y, x] == 1:
                x0, y0 = x * CELL, y * CELL
                p.push("M", x0, y0, "h", CELL, "v", CELL, "h", -CELL, "v", -CELL, "z")
    dwg.add(p)

    dwg.save()
    print("Wrote maze.svg")


def main():
    maze = Maze()
    maze.generator = Prims(4, 4)
    maze.generate()
    maze.generate_entrances()
    maze.solver = BacktrackingSolver()
    maze.generate_monte_carlo(100, 10, 0.25)

    print(maze)

    save_txt(maze)
    save_svg(maze)


if __name__ == "__main__":
    main()
