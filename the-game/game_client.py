# This example client just reads from the game server.
# Every received line is printed to standard output.
#
# You could also run netcat, which does the same:
#   nc -v maze.devbit.lan 1337
import asyncio

HOST = "maze.devbit.lan"
PORT = 1337


async def receive_maze():
    reader, writer = await asyncio.open_connection(HOST, PORT)
    while line := await reader.readline():
        print(line.decode(), end="")


asyncio.run(receive_maze())
