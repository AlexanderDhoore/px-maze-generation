#!/usr/bin/env python3
import os

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|"  # use TCP for RTSP (no corruption)
    "fflags;nobuffer|"  # no buffering / low delay
    "flags;low_delay|"
)
import cv2
import argparse
import time
import sys
import numpy as np
from game_tcp import GameTcp
from frame_grabber import FrameGrabber

CORNERS = (  # calibration points
    ((330, 178), (504, 172), (685, 170), (861, 169), (1054, 173)),
    ((327, 284), (505, 279), (691, 277), (866, 275), (1065, 274)),
    ((325, 392), (507, 388), (692, 386), (872, 382), (1071, 375)),
    ((327, 502), (508, 502), (694, 499), (874, 492), (1076, 482)),
    ((330, 647), (510, 648), (697, 644), (877, 633), (1077, 619)),
)
WIDTHS = [5, 5, 5, 6]
HEIGHTS = [3, 3, 3, 4]

FRUITS = []
GHOSTS = []
TICK = time.monotonic()

MAZE = [
    "#############S#######",
    "#   #   #         # #",
    "# ### # # ######### #",
    "#     #             #",
    "# # # ########### ###",
    "# # #         # #   #",
    "### # ######### ### #",
    "#   #   # #       # #",
    "# ####### # # # #####",
    "#           # #     #",
    "# ##### ### ### # ###",
    "#   #     # #   #   #",
    "#############E#######",
]
assert len(MAZE) == sum(HEIGHTS)
assert len(MAZE[0]) == sum(WIDTHS)


def load_sprite(path):
    """
    Load Pacman sprite (fruit/ghost) from BGRA PNG file.
    """
    sprite = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if sprite is None:
        raise FileNotFoundError(f"Could not load sprite: {path}")
    if sprite.shape[2] != 4:
        raise Exception(f"Sprite must be RGBA. Got {sprite.shape}")
    return sprite


def warp_corner(idx, idy):
    """
    Warping is used to compensate for the camera barrel distortion.
    """
    for col, width in enumerate(WIDTHS):
        if idx <= width:
            break
        idx -= width
    for row, height in enumerate(HEIGHTS):
        if idy <= height:
            break
        idy -= height
    (mx1, my1) = CORNERS[row][col]
    (mx2, my2) = CORNERS[row][col + 1]
    (mx3, my3) = CORNERS[row + 1][col + 1]
    (mx4, my4) = CORNERS[row + 1][col]
    ratiox = idx / width
    ratioy = idy / height
    assert 0 <= ratiox <= 1
    assert 0 <= ratioy <= 1
    topx = mx1 * (1 - ratiox) + mx2 * ratiox
    botx = mx4 * (1 - ratiox) + mx3 * ratiox
    lefy = my1 * (1 - ratioy) + my4 * ratioy
    rigy = my2 * (1 - ratioy) + my3 * ratioy
    warpx = topx * (1 - ratioy) + botx * ratioy
    warpy = lefy * (1 - ratiox) + rigy * ratiox
    return warpx, warpy


def warp_sprite(sprite, idx, idy):
    """
    Warp BGRA sprite into its cell's ROI.
    """
    h, w = sprite.shape[:2]

    # Source square (pixel corners)
    src = np.array(
        ((0, 0), (w - 1, 0), (w - 1, h - 1), (0, h - 1)),
        dtype=np.float32,
    )

    # Destination quad corners for this cell
    p1 = warp_corner(idx, idy)
    p2 = warp_corner(idx + 1, idy)
    p3 = warp_corner(idx + 1, idy + 1)
    p4 = warp_corner(idx, idy + 1)

    dx12 = abs(p1[0] - p2[0])
    dx34 = abs(p3[0] - p4[0])
    dy14 = abs(p1[1] - p4[1])
    dy23 = abs(p2[1] - p3[1])

    shrink = 0.1
    p1 = p1[0] + shrink * dx12, p1[1] + shrink * dy14
    p2 = p2[0] - shrink * dx12, p2[1] + shrink * dy23
    p3 = p3[0] - shrink * dx34, p3[1] - shrink * dy23
    p4 = p4[0] + shrink * dx34, p4[1] - shrink * dy14
    dst = np.array((p1, p2, p3, p4), dtype=np.float32)

    # Homography to that quad
    M = cv2.getPerspectiveTransform(src, dst)

    # Tight integer bounding box around the quad
    minx = int(np.floor(dst[:, 0].min()))
    miny = int(np.floor(dst[:, 1].min()))
    maxx = int(np.ceil(dst[:, 0].max()))
    maxy = int(np.ceil(dst[:, 1].max()))
    w = maxx - minx
    h = maxy - miny

    # Translation so warp output starts at (0,0) of that ROI
    T = np.array([[1, 0, -minx], [0, 1, -miny], [0, 0, 1]], dtype=np.float32)

    # Pre-shifted homography for directly warping into (w,h)
    transform = T @ M

    warped = cv2.warpPerspective(
        sprite,
        transform,
        (w, h),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    return idx, idy, minx, miny, w, h, warped


def paste_sprite(frame, sprite):
    """
    Take pre-warped sprite and alpha-blend it into the frame.
    """
    idx, idy, x, y, w, h, warped = sprite

    # Split and blend region of interest
    pixels = warped[:, :, :3].astype(np.float32)  # (h, w, bgr)
    alpha = (warped[:, :, 3:4].astype(np.float32)) / 255.0  # (h, w, 1)

    roi = frame[y : y + h, x : x + w].astype(np.float32)
    frame[y : y + h, x : x + w] = (pixels * alpha + roi * (1.0 - alpha)).astype(
        np.uint8
    )


def draw_line(frame, p1, p2):
    cv2.line(frame, p1, p2, color=(0, 255, 0), thickness=1, lineType=cv2.LINE_AA)


def draw_grid(frame):
    """
    Draw the grid of lines, to see the calibration corners.
    """
    for row in range(len(CORNERS)):
        for col in range(len(CORNERS[row]) - 1):
            draw_line(frame, CORNERS[row][col], CORNERS[row][col + 1])
    for col in range(len(CORNERS[0])):
        for row in range(len(CORNERS) - 1):
            draw_line(frame, CORNERS[row][col], CORNERS[row + 1][col])


def iter_ghosts():
    for shift, ghost in enumerate(GHOSTS):
        count = len(ghost) * 2 - 2
        index = round(TICK + shift) % count
        if index >= len(ghost):
            index = count - index
        yield ghost[index]


def process_frame(frame):
    """
    Draw our Pacman game on the camera frame.
    """
    # draw_grid(frame)

    for fruit in FRUITS:
        paste_sprite(frame, fruit)

    for ghost in iter_ghosts():
        paste_sprite(frame, ghost)

    cv2.putText(
        frame,
        f"{round(TICK) % 100}",
        (1240, 700),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return frame


def setup_game():
    apple = load_sprite("../sprites/Apple.png")
    banana = load_sprite("../sprites/Banana.png")
    cherry = load_sprite("../sprites/Cherry.png")
    grapes = load_sprite("../sprites/Grapes.png")
    melon = load_sprite("../sprites/Melon.png")
    orange = load_sprite("../sprites/Orange.png")
    pear = load_sprite("../sprites/Pear.png")
    strawberry = load_sprite("../sprites/Strawberry.png")

    blinky = load_sprite("../sprites/Blinky.png")
    clyde = load_sprite("../sprites/Clyde.png")
    inky = load_sprite("../sprites/Inky.png")
    pinky = load_sprite("../sprites/Pinky.png")

    FRUITS.append(warp_sprite(apple, 2, 1))
    FRUITS.append(warp_sprite(banana, 2, 3))
    FRUITS.append(warp_sprite(cherry, 9, 11))
    FRUITS.append(warp_sprite(grapes, 13, 5))
    FRUITS.append(warp_sprite(melon, 13, 9))
    FRUITS.append(warp_sprite(orange, 17, 5))
    FRUITS.append(warp_sprite(pear, 19, 5))
    FRUITS.append(warp_sprite(strawberry, 19, 11))

    ghost1 = []
    ghost1.append(warp_sprite(blinky, 6, 3))
    ghost1.append(warp_sprite(blinky, 19, 1))
    GHOSTS.append(ghost1)

    ghost2 = []
    ghost2.append(warp_sprite(clyde, 3, 11))
    ghost2.append(warp_sprite(clyde, 5, 11))
    GHOSTS.append(ghost2)

    ghost3 = []
    ghost3.append(warp_sprite(inky, 17, 7))
    ghost3.append(warp_sprite(inky, 19, 9))
    GHOSTS.append(ghost3)

    ghost4 = []
    ghost4.append(warp_sprite(pinky, 15, 1))
    ghost4.append(warp_sprite(pinky, 17, 1))
    GHOSTS.append(ghost4)


def update_tick():
    global TICK
    next_tick = time.monotonic()
    period = next_tick - TICK
    changed = round(TICK) != round(next_tick)
    TICK = next_tick
    if changed:
        print(f"FPS: {1/period:.2f}")
    return changed


def send_maze(tcp: GameTcp):
    print("Send maze")

    grid = [list(row) for row in MAZE]

    for fruit in FRUITS:
        idx, idy = fruit[0], fruit[1]
        grid[idy][idx] = "F"

    for ghost in iter_ghosts():
        idx, idy = ghost[0], ghost[1]
        grid[idy][idx] = "G"

    message = "\n".join("".join(row) for row in grid) + "\n\n"
    tcp.send(message)


def main():
    parser = argparse.ArgumentParser(description="The Maze Game")
    parser.add_argument(
        "--url",
        help="RTSP/RTSPS URL",
        default="rtsp://10.1.0.1:7447/ZCdgeMlOQCPF0Jyp",
    )
    args = parser.parse_args()

    setup_game()

    tcp = GameTcp()
    tcp.start()

    grabber = FrameGrabber(args.url)
    grabber.start()

    cv2.namedWindow("window", cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.setWindowProperty("window", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    while True:
        frame = grabber.pop_frame()
        frame = process_frame(frame)
        cv2.imshow("window", frame)

        if update_tick():
            print("Frame:", frame.shape)
            send_maze(tcp)

        key = cv2.pollKey()
        if key == 27:  # Esc
            print("ESC")
            sys.exit(0)


if __name__ == "__main__":
    main()
